import numpy as np
import sounddevice as sd
import tempfile
import wave
from faster_whisper import WhisperModel

# Audio configuration
SAMPLE_RATE = 48000       # macOS default input sample rate
WHISPER_RATE = 16000      # Whisper expects 16kHz
CHANNELS = 1              # Mono input

# Silence detection tuning
# Amplitude threshold — raise if too sensitive to background noise
SILENCE_THRESHOLD = 800
SILENCE_DURATION = 1.5    # Seconds of silence before stopping recording
MAX_DURATION = 15         # Hard cap on recording length in seconds
MIN_DURATION = 2.0        # Minimum recording before silence detection activates
MIN_AMPLITUDE = 300       # Reject recordings below this amplitude (pure noise)

# Set to True externally while NOVA is speaking to prevent mic feedback
nova_speaking = False

print("Loading Whisper model...")
model = WhisperModel("small", device="cpu", compute_type="int8")
print("Whisper model ready.")


def record_until_silence() -> np.ndarray:
    """Record audio from default input device until silence is detected."""
    print("Listening... speak now.")
    device = sd.query_devices(kind='input')

    chunk_size = int(SAMPLE_RATE * 0.1)  # 100ms chunks
    audio_chunks = []
    silent_chunks = 0
    max_silent_chunks = int(SILENCE_DURATION / 0.1)
    max_chunks = int(MAX_DURATION / 0.1)
    min_chunks = int(MIN_DURATION / 0.1)
    started_speaking = False

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype='int16',
        device=device['name'],
        blocksize=chunk_size
    ) as stream:
        while len(audio_chunks) < max_chunks:
            chunk, _ = stream.read(chunk_size)
            amplitude = np.max(np.abs(chunk))
            audio_chunks.append(chunk.copy())

            if nova_speaking:
                continue

            if amplitude > SILENCE_THRESHOLD:
                started_speaking = True
                silent_chunks = 0
            elif started_speaking and len(audio_chunks) >= min_chunks:
                silent_chunks += 1
                if silent_chunks >= max_silent_chunks:
                    break

    print("Recording complete.")
    return np.concatenate(audio_chunks)


def resample(audio: np.ndarray) -> np.ndarray:
    """Downsample from SAMPLE_RATE to WHISPER_RATE."""
    ratio = WHISPER_RATE / SAMPLE_RATE
    target_length = int(len(audio) * ratio)
    return np.interp(
        np.linspace(0, len(audio), target_length),
        np.arange(len(audio)),
        audio.flatten()
    ).astype(np.int16)


def transcribe(audio: np.ndarray) -> str:
    """Transcribe audio to text using Whisper. Returns empty string if audio is noise."""
    if np.max(np.abs(audio)) < MIN_AMPLITUDE:
        return ""

    audio = resample(audio)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        with wave.open(f.name, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(WHISPER_RATE)
            wf.writeframes(audio.tobytes())

        segments, info = model.transcribe(f.name, language="en")

        if info.language_probability < 0.7:
            return ""

        return " ".join([s.text for s in segments]).strip()


def listen() -> str:
    """Record from mic and return transcribed text."""
    audio = record_until_silence()
    return transcribe(audio)


if __name__ == "__main__":
    print("Say something...")
    print(f"You said: {listen()}")
