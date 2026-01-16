<!-- Copilot / AI agent instructions for the pronounce-prototype repo -->
# Copilot Instructions — pronounce-prototype

These notes are minimal, actionable, and tailored so an AI coding agent can be productive immediately.

1) Big picture
- Backend: `backend/app` — FastAPI server (`main.py`) exposing `POST /process-audio/`.
- Frontend: `frontend/app.py` — Streamlit UI that calls the backend and plays TTS.
- Audio flow: upload → raw file saved (`raw_<ts>`) → extension fix → `clean_<ts>.wav` (16k, mono, 16-bit) → transcription (FasterWhisper) → hybrid scoring.
- Scoring: `hybrid_scoring.py` (word align + fuzzy matching) relies on `transcribe_with_words` (word timestamps) and `scoring.py` helpers.

2) Key files to read (examples)
- `backend/app/main.py` — endpoint, file save/rename logic, audio pre-checks, uses `compute_per_word_scores`.
- `backend/app/transcribe.py` — main transcription logic, language-specific prompts, retries for transliteration issues, returns `{'text', 'words'}`.
- `backend/app/model_loader.py` — loads `faster_whisper.WhisperModel` with `MODEL_SIZE = 'medium'` and `compute_type='int8'`; device auto-detected (`cuda`/`cpu`).
- `backend/app/hybrid_scoring.py` — aligns target ↔ recognized words, thresholds: correct >= 80, perfect >= 90 when computing `reading_accuracy`.
- `backend/app/scoring.py` — text normalization, tokenization, WER and detailed alignment helpers.
- `backend/app/tts.py` — uses `gTTS` to create MP3 then converts to 16k WAV for downstream processing.

3) Run / dev workflow (what actually works here)
- Create and activate Python venv (Windows example):
  - `python -m venv .venv`
  - `.\.venv\Scripts\activate`
- Install deps: `pip install -r requirements.txt`.
- Ensure `ffmpeg` is installed and on `PATH` (Windows: extract to `C:\ffmpeg\bin` and add to PATH). `pydub` expects ffmpeg for conversions.
- Run backend (uvicorn):
  - `.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000`
- Run frontend (Streamlit):
  - `cd frontend`
  - `streamlit run app.py`

4) API contract / important runtime details
- Endpoint: `POST /process-audio/` accepts a multipart form with fields: `file` (UploadFile), `target_text` (Form), `language` (Form, default `hi`).
- The backend writes files to `backend/app/uploads/` (served at `/static`).
- Important behavior: audio is NOT normalized for volume — do not introduce global normalization unless you update downstream checks in `main.py`.
- All exported WAVs are resampled to 16 kHz, mono, 16-bit (see `main.py` export and `tts.py`).

5) Model / performance notes (important for edits)
- `model_loader.py` uses `faster_whisper.WhisperModel(MODEL_SIZE, compute_type='int8')` to balance speed & memory.
- Use `get_model()` to reuse the loaded model — avoid reloading inside request handlers.
- The transcription call in `transcribe_with_words` uses `word_timestamps=True` and `initial_prompt` to bias output to native script for Indic languages. If modifying transcription behavior, preserve the `initial_prompt` logic for Indic languages.

6) Project-specific scoring conventions (do not change lightly)
- In `hybrid_scoring.py`: fuzzy substitution uses `difflib.SequenceMatcher().ratio()` → score = ratio*100. Thresholds:
  - `status = 'correct'` if score >= 80
  - `perfect_matches` counted as `total_score >= 90` for `reading_accuracy`.
- `scoring.normalize_text()` performs Unicode NFKC, removes zero-width chars, strips punctuation (keeps letters/marks/numbers). Use this helper when you compare texts.

7) Patterns and conventions for agents
- Keep public API stable: prefer changes inside `backend/app/*` helper functions over changing route signatures in `main.py`.
- Use existing helper functions: `get_model()`, `transcribe_with_words()`, `compute_per_word_scores()`, `normalize_text()` rather than reimplementing behavior.
- File naming: raw inputs use prefix `raw_`, cleaned export uses `clean_`, TTS outputs use `tts_` filenames — tests and frontend expect these conventions.

8) Integration points / external deps
- `faster_whisper` (WhisperModel), `torch` (device detect), `pydub` and `ffmpeg` (audio I/O and conversion), `gTTS` (TTS), `jiwer` (WER). See `requirements.txt` for exact versions.
- Static files served by FastAPI: `app.mount('/static', StaticFiles(directory=str(UPLOAD_DIR)))` — uploaded/generated audio may be referenced by the frontend using `/static/<filename>`.

9) Safe changes & examples
- To change transcription prompts for a language, update `SCRIPT_PROMPTS` in `transcribe.py` (preserve language keys like `hi`, `ta`, `kn`, etc.).
- To change matching thresholds, update constants in `hybrid_scoring.py` and ensure downstream code that calculates `reading_accuracy` still matches expectations.

10) What an agent should NOT do
- Do not reload or reinitialize the model per request. Use `model_loader.get_model()`.
- Do not change the endpoint signature without updating `frontend/app.py`.

If anything here is unclear or you'd like more examples (unit/test harness, or more detailed architecture notes), tell me which area to expand (transcription, scoring math, or dev/run steps) and I'll iterate.
