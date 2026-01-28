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
from fastapi.responses import FileResponse

# --- INTERNAL IMPORTS ---
# 1. Model Loader (for pre-loading)
from backend.app.model_loader import get_model
# 2. The Core Scoring Engine
from backend.app.hybrid_scoring import compute_per_word_scores
# 3. The New Modular Utility for Error Analysis
from backend.app.scoring_utils import generate_analysis_report
# 4. Database Modules (Supabase)
from backend.app.db.client import get_supabase_client  # <--- NEW: To connect on startup
from backend.app.db.repo import save_attempt         # <--- NEW: To save data
# 5 audio validation
from backend.app.audio_validator import validate_audio
# 6 tts
from backend.app.tts_handler import generate_audio_file 
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

# --------------------
# LIFESPAN (STARTUP OPTIMIZATION)
# --------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    This function runs BEFORE the API starts accepting requests.
    We use it to 'warm up' the system:
    1. Load the heavy AI Model (Whisper)
    2. Establish the Database Connection (Supabase)
    """
    logger.info("🚀 Starting up Pronounce AI Backend...")
    
    # --- 1. Load AI Model ---
    try:
        logger.info("⏳ Pre-loading Whisper Model... (This may take a few seconds)")
        get_model() # Triggers global loading
        logger.info("✅ Whisper Model loaded and ready!")
    except Exception as e:
        logger.error(f"❌ Failed to load AI model: {e}")

    # --- 2. Connect to Database ---
    try:
        logger.info("⏳ Connecting to Supabase Database...")
        client = get_supabase_client() # Triggers connection
        if client:
            logger.info("✅ Supabase Connection Established!")
        else:
            logger.warning("⚠️ Supabase Client returned None (Check .env keys)")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Database: {e}")
    
    yield  # API runs here
    
    logger.info("🛑 Shutting down application...")

# Initialize FastAPI with the lifespan handler
app = FastAPI(lifespan=lifespan)

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
    language: str = Form("en"),
    user_id: str = Form("Guest_User")
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
        #AUDIO PROCESSING
        logger.info("🔊 Decoding audio stream...")
        audio = AudioSegment.from_file(str(raw_path))
        
        # Convert to 16kHz Mono WAV
        logger.info("🛠️  Transcoding to 16kHz Mono WAV...")
        clean_filename = f"clean_{int(time.time())}.wav"
        clean_path = UPLOAD_DIR / clean_filename
        
        audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
        audio.export(clean_path, format="wav")
        
        duration_sec = audio.duration_seconds
        logger.info(f"⏱️  Audio Duration: {round(duration_sec, 2)}s")

        # 3. VALIDATION (Run on the CLEAN WAV)
        # Moved this AFTER conversion to avoid WebM bugs
        logger.info("🛡️ Running Audio Quality Checks...")
        is_valid, error_msg = validate_audio(str(clean_path)) # <--- Check clean_path
        
        if not is_valid:
            logger.warning(f"❌ Audio Rejected: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)

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
        
        metrics, error_report = generate_analysis_report(
            alignment=result.get("word_alignment", []),
            target_text=target_text,
            duration_sec=duration_sec
        )
        
        # Merge metrics back into result
        result["detailed_metrics"] = metrics
        if "accuracy" in metrics:
            result["components"]["accuracy"] = metrics["accuracy"]
        if "fluency" in metrics:
            result["components"]["fluency"] = metrics["fluency"]
        
        # ----------------------------------------
        # SAVE TO SUPABASE (Phase 1 Integration)
        # ----------------------------------------
        logger.info("☁️ Uploading results to Supabase...")
        try:
            # We hardcode 'Guest_User' until Authentication (Phase 3) is built
            save_attempt(
                user_name=user_id, 
                target_text=target_text,
                metrics=metrics,
                error_report=error_report
            )
            logger.info("✅ Data saved to cloud successfully!")
        except Exception as e:
            logger.error(f"⚠️ Could not save to Supabase: {e}")

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
            "error_analysis": error_report,
            "logs": memory_handler.log_records
        }

    # 1. CATCH VALIDATION ERRORS (The 400s we raised intentionally)
    except HTTPException as he:
        # Just re-raise it so FastAPI sends the 400 to the frontend
        raise he
        
    # 2. CATCH REAL CRASHES (The 500s)
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
    
@app.get("/tts/")
async def get_tts(text: str, language: str = "en"):
    """
    Returns an MP3 file of the text spoken in the requested language.
    """
    try:
        # Generate the file
        output_path = await generate_audio_file(text, language)
        
        # Return it as a downloadable file
        return FileResponse(output_path, media_type="audio/mpeg", filename=f"tts_{text}.mp3")
    except Exception as e:
        logger.error(f"TTS Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))