import sounddevice as sd
import numpy as np
import tempfile
import wave
from faster_whisper import WhisperModel

print("Loading Whisper model...")
model = WhisperModel("small", device="cpu", compute_type="int8")
print("Whisper model ready.")

SAMPLE_RATE = 48000  # Match macOS default
WHISPER_RATE = 16000  # Whisper expects 16000
CHANNELS = 1

def record_audio(duration: int = 5) -> np.ndarray:
    print(f"Recording for {duration} seconds... speak now.")
    audio = sd.rec(
        int(duration * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype='int16'
    )
    sd.wait()
    print("Recording complete.")
    return audio

def resample(audio: np.ndarray) -> np.ndarray:
    """Downsample from 48000 to 16000 Hz."""
    ratio = WHISPER_RATE / SAMPLE_RATE
    target_length = int(len(audio) * ratio)
    resampled = np.interp(
        np.linspace(0, len(audio), target_length),
        np.arange(len(audio)),
        audio.flatten()
    ).astype(np.int16)
    return resampled

def transcribe(audio: np.ndarray) -> str:
    audio = resample(audio)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        with wave.open(f.name, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(WHISPER_RATE)
            wf.writeframes(audio.tobytes())
        segments, _ = model.transcribe(f.name)
        text = " ".join([s.text for s in segments]).strip()
        return text

def listen(duration: int = 5) -> str:
    audio = record_audio(duration)
    return transcribe(audio)

if __name__ == "__main__":
    print("Say something after the prompt...")
    text = listen(duration=5)
    print(f"You said: {text}")
