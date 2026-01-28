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
from backend.app.db.repo import (
    save_attempt, 
    fetch_dashboard_stats, 
    fetch_progress_history, 
    fetch_error_distribution,
    fetch_difficulty_stats
)
# 5 audio validation
from backend.app.audio_validator import validate_audio
# 6 tts
from backend.app.tts_handler import generate_audio_file 
from backend.app.helper_wordcloud import fetch_word_analysis
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
    "en-US": {
        "easy": [
            ("en_e1", "The big brown dog ran to the park. He loves to play with the red ball."),
            ("en_e2", "I have a cat named Luna. She sleeps on my bed all day long."),
            ("en_e3", "The sun is very hot today. We should eat some cold ice cream."),
            ("en_e4", "My school is near my house. I walk there with my best friend every morning."),
            ("en_e5", "It is raining outside now. I need my umbrella and my yellow boots."),
        ],
        "medium": [
            ("en_m1", "The weekend is finally here, and I am so excited to go hiking with my friends. We packed our bags with tasty snacks, water, and extra clothes just in case it rains. The trail leads up a high mountain where we hope to see beautiful birds and maybe even a deer. After the long hike, we plan to have a big picnic near the river."),
            ("en_m2", "Cooking dinner can be a really fun activity if you have the right ingredients ready. First, you need to chop the fresh vegetables and heat up the pan with some olive oil. When the onions turn golden brown, you can add the spices and the main dish to the pot. The delicious smell of fresh food filling the kitchen makes everyone in the family hungry."),
            ("en_m3", "Gardening is a hobby that requires patience and a lot of dedication. You must plant the seeds at the right time of year and water them consistently every single day. Watching a tiny green sprout grow into a tall, flowering plant gives you a wonderful sense of accomplishment. It reminds us that good things take time and care to grow properly."),
        ],
        "hard": [
            ("en_h1", "The Amazon rainforest, often referred to as the 'lungs of the Earth,' plays a critical role in regulating the global climate. It covers approximately forty percent of the South American continent and houses an incredibly diverse ecosystem that includes millions of species of insects, plants, birds, and other forms of life, many of which are still unrecorded by science. This vast canopy of greenery absorbs massive amounts of carbon dioxide from the atmosphere, helping to mitigate the effects of climate change. However, rapid deforestation driven by agricultural expansion and illegal logging poses a severe threat to this delicate balance. If the forest continues to disappear at the current alarming rate, the consequences for global weather patterns and biodiversity could be irreversible, leading to a loss of natural resources that future generations might never be able to recover."),
            ("en_h2", "The exploration of Mars has been a focal point of space agencies for decades, driven by the possibility that the Red Planet may have once harbored microbial life. Robotic rovers, such as Perseverance and Curiosity, have been tirelessly traversing the Martian surface, analyzing soil samples and capturing high-resolution images of the desolate landscape. These sophisticated machines are equipped with advanced scientific instruments designed to detect organic compounds and signs of ancient water flow. The data returned suggests that billions of years ago, Mars was a warmer, wetter world with river valleys and lake beds, much like Earth. Understanding why Mars lost its atmosphere and dried up is crucial, not only for piecing together the history of our solar system but also for preparing for future human missions where astronauts will have to survive in its harsh, unforgiving environment."),
            ("en_h3", "Artificial Intelligence has rapidly evolved from a theoretical concept into a powerful tool that permeates nearly every aspect of modern society. By mimicking cognitive functions such as learning and problem-solving, AI systems can diagnose diseases with remarkable accuracy, optimize complex logistics networks, and even generate creative works of art. However, this technological leap brings with it significant ethical questions regarding privacy, algorithmic bias, and the potential displacement of jobs in various industries. As we integrate these intelligent systems further into our daily lives, it becomes imperative to establish robust regulations and ethical guidelines. Balancing innovation with social responsibility will be the defining challenge of the twenty-first century, ensuring that the benefits of artificial intelligence are shared equitably across all of humanity."),
        ]
    }
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
    user_id: str = Form("Guest_User"),
    difficulty: str = Form("easy")
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
                error_report=error_report,
                difficulty=difficulty
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
def get_passage(language: str = "en", difficulty: str = "easy"):
    # Normalize language code
    iso_lang = LANG_MAP.get(language.lower().strip(), "en-US")
    
    # Default to 'easy' if invalid difficulty provided
    valid_difficulties = ["easy", "medium", "hard"]
    if difficulty not in valid_difficulties:
        difficulty = "easy"

    # Fetch passage list
    lang_data = PASSAGE_BANK.get(iso_lang, PASSAGE_BANK["en-US"])
    passages = lang_data.get(difficulty, lang_data["easy"])
    
    # Pick a random one
    data = random.choice(passages)
    
    return {
        "language": iso_lang,
        "difficulty": difficulty,
        "passage_id": data[0],
        "passage": data[1]
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



# --- UPDATED ENDPOINT ---
@app.get("/analytics/{user_id}")
async def get_analytics(user_id: str):
    """
    Endpoint for the Dashboard to fetch user history.
    Aggregates stats, charts, and error distribution.
    """
    try:
        # Fetch all components (now including the new word analysis)
        stats = fetch_dashboard_stats(user_id)
        history = fetch_progress_history(user_id)
        errors = fetch_error_distribution(user_id)
        difficulty_data = fetch_difficulty_stats(user_id)
        
        # --- CALL THE NEW FUNCTION HERE ---
        word_data = fetch_word_analysis(user_id) 

        return {
            "status": "success",
            "stats": stats,            # {avg_wpm, avg_accuracy, total_attempts}
            "history": history,        # List of attempts for Line Chart
            "errors": errors,          # General pie chart data
            "difficulty_analysis": difficulty_data,
            "word_analysis": word_data # <--- NEW KEY FOR ROW 4
        }
    except Exception as e:
        # logger.error(f"Analytics Error: {e}") # Uncomment if you have logger setup
        print(f"Analytics Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch analytics")