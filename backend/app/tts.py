from gtts import gTTS
from uuid import uuid4
from pathlib import Path
from pydub import AudioSegment


def synthesize_tts(text: str, lang="hi", out_path: str = None):
    """
    Generates a WAV file (not MP3) because pronunciation scoring
    requires PCM WAV input for Whisper.
    """

    if out_path is None:
        filename = f"tts_{uuid4().hex}.wav"
        out_path = Path("uploads") / filename
    else:
        out_path = Path(out_path)

    # Generate MP3 temporarily
    temp_mp3 = out_path.with_suffix(".mp3")
    tts = gTTS(text=text, lang=lang)
    tts.save(temp_mp3)

    # Convert MP3 → WAV
    audio = AudioSegment.from_mp3(temp_mp3)
    audio = audio.set_frame_rate(16000).set_channels(1)
    audio.export(out_path, format="wav")

    # Remove temp MP3
    temp_mp3.unlink(missing_ok=True)

    return out_path
