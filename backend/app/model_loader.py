from faster_whisper import WhisperModel
import torch

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

_model = None

def get_model():
    global _model

    if _model is None:
        # CHANGED: 'medium' -> 'base.en' for faster response time
        # You can use 'tiny.en' for maximum speed (but slightly less accurate)
        model_size = "base.en" 
        
        print(f"Loading FasterWhisper model: {model_size} on {DEVICE}...")
        
        _model = WhisperModel(
            model_size,
            device=DEVICE,
            compute_type="int8" if DEVICE == "cpu" else "float16"
        )

        print("FasterWhisper model loaded successfully.")

    return _model