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

# --- INTERNAL IMPORTS ---
# 1. The Core Scoring Engine
from backend.app.hybrid_scoring import compute_per_word_scores
# 2. The New Modular Utility for Error Analysis
from backend.app.scoring_utils import generate_analysis_report

# --------------------
# LOGGING SETUP
# --------------------

class InMemoryHandler(logging.Handler):
    """
    Captures logs in a list to send back to the frontend.
    """
    def __init__(self):
        super().__init__()
        self.log_records = []

    def emit(self, record):
        try:
            msg = self.format(record)
            self.log_records.append({
                "level": record.levelname,
                "message": msg,
                "timestamp": record.created
            })
        except Exception:
            self.handleError(record)

# Configure Root Logger to print to Terminal (Standard Output)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)
app = FastAPI()

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
# Paths
# --------------------

ROOT_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(UPLOAD_DIR)), name="static")

# --------------------
# Constants & Data
# --------------------

LANG_MAP = {
    "english": "en", "en": "en",
    "hindi": "hi", "hi": "hi",
    "tamil": "ta", "ta": "ta",
    "telugu": "te", "te": "te",
    "kannada": "kn", "kn": "kn",
    "gujarati": "gu", "gu": "gu",
}

PASSAGE_BANK = {
    "en": [
        ("en_nature", "The forest was alive with the sounds of early morning. Sunlight filtered through the dense canopy of ancient oak trees, casting dappled shadows on the mossy ground below. Somewhere in the distance, a woodpecker hammered rhythmically against a hollow trunk, while squirrels chased each other spiraling up the rough bark. The air smelled of damp earth and pine needles, a refreshing scent that filled the lungs with every breath. A small stream meandered through the underbrush, its crystal-clear water bubbling over smooth gray stones. As I walked along the narrow path, the crunch of dry leaves under my boots was the only sign of my presence in this peaceful sanctuary. It was a perfect moment of solitude, away from the noise and chaos of the city, where time seemed to slow down and nature’s simple beauty took center stage."),
        ("en_tech", "In the rapidly evolving world of technology, artificial intelligence has become a cornerstone of modern innovation. From voice assistants that manage our daily schedules to complex algorithms that diagnose medical conditions, machines are learning to process information in ways that mimic human cognition. However, this progress brings ethical questions about privacy and the future of work. As automation takes over repetitive tasks, the demand for creative and emotional intelligence in the workforce is rising. We are entering an era where collaboration between humans and machines is not just a possibility, but a necessity. Understanding how these systems function is no longer reserved for computer scientists; it is becoming a fundamental skill for anyone navigating the digital landscape. The challenge lies in ensuring that these powerful tools are used to enhance human potential rather than replace it."),
    ],
    "hi": [
        ("hi_1", "आज का मौसम बहुत सुहाना है। बच्चे पार्क में खेल रहे हैं।"),
    ]
}

# --------------------
# Utilities
# --------------------

def detect_and_rename(filepath: Path) -> Path:
    """Checks header bytes to determine real extension (WebM vs WAV)."""
    with open(filepath, "rb") as f:
        header = f.read(4)

    new_path = filepath
    if header.startswith(b'\x1a\x45\xdf\xa3'):  # WEBM
        if filepath.suffix != ".webm":
            new_path = filepath.with_suffix(".webm")
            os.rename(filepath, new_path)
    elif header.startswith(b'RIFF'):  # WAV
        if filepath.suffix != ".wav":
            new_path = filepath.with_suffix(".wav")
            os.rename(filepath, new_path)
    
    return new_path

# --------------------
# API ENDPOINTS
# --------------------

@app.post("/process-audio/")
def process_audio(
    file: UploadFile = File(...),
    target_text: str = Form(...),
    language: str = Form("en")
):
    # 1. Attach Memory Logger
    memory_handler = InMemoryHandler()
    formatter = logging.Formatter('%(message)s')
    memory_handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.addHandler(memory_handler)
    
    start_time = time.time()
    raw_path = None
    clean_path = None

    try:
        logger.info(f"🚀 Request received. File: {file.filename}")
        
        iso_lang = LANG_MAP.get(language.lower().strip(), "en")
        logger.info(f"ℹ️  Language set to: {iso_lang}")

        # Save Raw
        raw_filename = f"raw_{int(time.time())}_{file.filename}"
        raw_path = UPLOAD_DIR / raw_filename
        with open(raw_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Format Check
        raw_path = detect_and_rename(raw_path)
        
        # Audio Processing
        logger.info("🔊 Decoding audio stream...")
        audio = AudioSegment.from_file(str(raw_path))
        
        duration_sec = audio.duration_seconds
        logger.info(f"⏱️  Audio Duration: {round(duration_sec, 2)}s")

        if audio.max_dBFS == -float("inf"):
            raise HTTPException(400, "Silent audio detected")
        if duration_sec < 0.5:
            raise HTTPException(400, "Audio too short (< 0.5s)")

        # Convert to 16kHz Mono WAV
        logger.info("🛠️  Transcoding to 16kHz Mono WAV...")
        clean_filename = f"clean_{int(time.time())}.wav"
        clean_path = UPLOAD_DIR / clean_filename
        
        audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
        audio.export(clean_path, format="wav")

        # Call Scoring Engine
        logger.info("🧠 Invoking Hybrid Scoring Engine...")
        result = compute_per_word_scores(
            target_text=target_text,
            lang_code=iso_lang,
            audio_path=str(clean_path)
        )
        logger.info("✨ Scoring calculation complete.")

        # ----------------------------------------
        # MODULAR ANALYSIS & METRICS
        # ----------------------------------------
        logger.info("📊 Generating Detailed Error Analysis...")
        
        # We use the separate utility function here to keep main.py clean
        metrics, error_report = generate_analysis_report(
            alignment=result.get("word_alignment", []),
            target_text=target_text,
            duration_sec=duration_sec
        )
        
        # Merge the detailed metrics back into the result object
        # IMPORTANT: Overwriting component scores with the robust calculation from utils
        result["detailed_metrics"] = metrics
        if "accuracy" in metrics:
            result["components"]["accuracy"] = metrics["accuracy"]
        if "fluency" in metrics:
            result["components"]["fluency"] = metrics["fluency"]
        
        # ----------------------------------------
        # RESPONSE
        # ----------------------------------------
        latency = round(time.time() - start_time, 2)
        logger.info(f"🏁 Process finished in {latency}s")

        return {
            "meta": {
                "latency_sec": latency,
                "language": iso_lang,
            },
            "target_text": target_text,
            "recognized_text": result.get("recognized_text", ""),
            "overall_score": result.get("overall_score", 0),
            "components": result.get("components", {}),
            "metrics": result.get("detailed_metrics", {}),
            "word_alignment": result.get("word_alignment", []),
            
            # This is the new field for the frontend tabs
            "error_analysis": error_report,
            
            # This allows the frontend to show the terminal logs
            "logs": memory_handler.log_records
        }

    except Exception as e:
        logger.error(f"🔥 Critical Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Processing Error: {str(e)}")

    finally:
        # Cleanup
        for p in [raw_path, clean_path]:
            if p and p.exists():
                try: os.remove(p)
                except: pass
        
        # Detach Logger
        root_logger.removeHandler(memory_handler)
        
@app.get("/get-passage/")
def get_passage(language: str = "en"):
    iso_lang = LANG_MAP.get(language.lower().strip(), "en")
    if iso_lang not in PASSAGE_BANK:
        iso_lang = "en"
    
    pid, passage = random.choice(PASSAGE_BANK[iso_lang])
    return {
        "language": iso_lang,
        "passage_id": pid,
        "passage": passage
    }