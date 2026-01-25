from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from pydub import AudioSegment
import os
import time
import shutil
import random
import logging
from contextlib import asynccontextmanager

from backend.app.db.attempt_repo import save_practice_attempt
from backend.app.db.error_repo import save_word_errors

from backend.app.model_loader import get_model
from backend.app.hybrid_scoring import compute_per_word_scores
from backend.app.scoring_utils import generate_analysis_report

from backend.app.api.users import router as users_router
from backend.app.api.passage import router as passage_router
from backend.app.api.attempts import router as attempts_router
from backend.app.api.errors import router as errors_router


# --------------------
# LOGGING SETUP
# --------------------

class InMemoryHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.log_records = []

    def emit(self, record):
        self.log_records.append({
            "level": record.levelname,
            "message": record.getMessage(),
            "timestamp": record.created
        })


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger(__name__)


# --------------------
# LIFESPAN
# --------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting Pronounce Backend...")
    try:
        logger.info("⏳ Loading Whisper model...")
        get_model()
        logger.info("✅ Model loaded")
    except Exception as e:
        logger.error(f"❌ Model load failed: {e}")
    yield
    logger.info("🛑 Shutting down backend")


# --------------------
# FASTAPI APP
# --------------------

app = FastAPI(
    title="Pronounce Backend",
    version="1.0.0",
    lifespan=lifespan
)


# --------------------
# ROUTERS
# --------------------

app.include_router(users_router)
app.include_router(passage_router)
app.include_router(attempts_router)
app.include_router(errors_router)


# --------------------
# CORS
# --------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------
# FILE PATHS
# --------------------

ROOT_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(UPLOAD_DIR)), name="static")


# --------------------
# CONSTANTS
# --------------------

LANG_MAP = {
    "en": "en", "english": "en",
    "hi": "hi", "hindi": "hi",
    "ta": "ta", "tamil": "ta",
    "te": "te", "telugu": "te",
    "kn": "kn", "kannada": "kn",
    "gu": "gu", "gujarati": "gu",
}

PASSAGE_BANK = {
    "en": [
        ("p1", "The forest was alive with the sounds of early morning."),
        ("p2", "Artificial intelligence is transforming modern technology."),
    ],
    "hi": [
        ("p3", "आज का मौसम बहुत सुहाना है।")
    ]
}


# --------------------
# UTILITIES
# --------------------

def detect_and_rename(path: Path) -> Path:
    with open(path, "rb") as f:
        header = f.read(4)

    if header.startswith(b"\x1a\x45\xdf\xa3") and path.suffix != ".webm":
        new = path.with_suffix(".webm")
        os.rename(path, new)
        return new

    if header.startswith(b"RIFF") and path.suffix != ".wav":
        new = path.with_suffix(".wav")
        os.rename(path, new)
        return new

    return path


# --------------------
# API ENDPOINTS
# --------------------

@app.post("/process-audio/")
def process_audio(
    file: UploadFile = File(...),
    target_text: str = Form(...),
    language: str = Form("en"),
):
    memory_handler = InMemoryHandler()
    logging.getLogger().addHandler(memory_handler)

    raw_path = None
    clean_path = None
    start_time = time.time()

    try:
        lang = LANG_MAP.get(language.lower(), "en")

        raw_path = UPLOAD_DIR / f"raw_{int(time.time())}_{file.filename}"
        with open(raw_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        raw_path = detect_and_rename(raw_path)

        audio = AudioSegment.from_file(raw_path)
        duration = audio.duration_seconds

        if duration < 0.5:
            raise HTTPException(status_code=400, detail="Audio too short")

        clean_path = UPLOAD_DIR / f"clean_{int(time.time())}.wav"
        audio.set_frame_rate(16000).set_channels(1).export(clean_path, format="wav")

        result = compute_per_word_scores(
            target_text=target_text,
            lang_code=lang,
            audio_path=str(clean_path)
        )

        metrics, errors = generate_analysis_report(
            alignment=result.get("word_alignment", []),
            target_text=target_text,
            duration_sec=duration
        )

        attempt_id = save_practice_attempt(
            user_id=1,
            passage_text=target_text,
            metrics=metrics,
            components=result.get("components", {})
        )

        save_word_errors(
            attempt_id=attempt_id,
            error_list=errors
        )

        latency = round(time.time() - start_time, 2)

        return {
            "meta": {"latency": latency, "language": lang},
            "components": result.get("components", {}),
            "metrics": metrics,
            "word_alignment": result.get("word_alignment", []),
            "error_analysis": errors,
            "logs": memory_handler.log_records,
        }

    except Exception as e:
        logger.exception("Processing failed")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        for p in [raw_path, clean_path]:
            if p and p.exists():
                try:
                    os.remove(p)
                except:
                    pass
        logging.getLogger().removeHandler(memory_handler)


@app.get("/get-passage/")
def get_passage(language: str = "en"):
    lang = LANG_MAP.get(language.lower(), "en")
    pid, passage = random.choice(PASSAGE_BANK.get(lang, PASSAGE_BANK["en"]))
    return {"passage_id": pid, "language": lang, "passage": passage}
