import sounddevice as sd
from kokoro_onnx import Kokoro

MODEL_PATH = "models/tts/kokoro-v1.0.onnx"
VOICES_PATH = "models/tts/voices-v1.0.bin"
VOICE = "af_bella"

print("Loading Kokoro voice model...")
kokoro = Kokoro(MODEL_PATH, VOICES_PATH)
print("Kokoro ready.")


def speak(text: str, speed: float = 1.0):
    """
    Convert text to speech using Kokoro and play through default output device.
    """
    samples, sample_rate = kokoro.create(
        text, voice=VOICE, speed=speed, lang="en-us")
    sd.play(samples, samplerate=sample_rate)
    sd.wait()


if __name__ == "__main__":
    speak("Hello, I am NOVA, your local AI voice assistant. How can I help you today?")
