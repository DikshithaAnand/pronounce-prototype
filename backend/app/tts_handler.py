import edge_tts
import tempfile
import os
import asyncio

# Voice Map for different languages
VOICE_MAP = {
    "en": "en-US-AriaNeural",
    "hi": "hi-IN-SwaraNeural",
    "ta": "ta-IN-PallaviNeural",
    "te": "te-IN-ShrutiNeural",
    "kn": "kn-IN-SapnaNeural",
    "gu": "gu-IN-DhwaniNeural"
}

async def generate_audio_file(text, lang="en"):
    """
    Generates a TTS audio file for the given text.
    Returns the path to the temporary file.
    """
    voice = VOICE_MAP.get(lang, "en-US-AriaNeural")
    communicate = edge_tts.Communicate(text, voice)
    
    # Create a temp file
    fd, path = tempfile.mkstemp(suffix=".mp3")
    os.close(fd) # Close the file descriptor so we can write to it
    
    await communicate.save(path)
    return path