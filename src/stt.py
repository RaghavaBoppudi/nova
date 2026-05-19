import numpy as np
import sounddevice as sd
import tempfile
import wave
from faster_whisper import WhisperModel

print("Loading Whisper model...")
model = WhisperModel("small", device="cpu", compute_type="int8")
print("Whisper model ready.")

SAMPLE_RATE = 48000
WHISPER_RATE = 16000
CHANNELS = 1
SILENCE_THRESHOLD = 800      # higher = less sensitive to background noise
SILENCE_DURATION = 1.5       # seconds of silence before stopping
MAX_DURATION = 15             # hard cap
MIN_DURATION = 2.0            # minimum recording before silence detection kicks in
MIN_AMPLITUDE = 300           # minimum amplitude to bother transcribing

# Global flag — set True while NOVA is speaking to prevent feedback loop
nova_speaking = False


def record_until_silence() -> np.ndarray:
    print("Listening... speak now.")
    device = sd.query_devices(kind='input')

    chunk_size = int(SAMPLE_RATE * 0.1)
    audio_chunks = []
    silent_chunks = 0
    max_silent_chunks = int(SILENCE_DURATION / 0.1)
    max_chunks = int(MAX_DURATION / 0.1)
    min_chunks = int(MIN_DURATION / 0.1)
    started_speaking = False

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS,
                        dtype='int16', device=device['name'],
                        blocksize=chunk_size) as stream:
        while len(audio_chunks) < max_chunks:
            chunk, _ = stream.read(chunk_size)
            amplitude = np.max(np.abs(chunk))
            audio_chunks.append(chunk.copy())

            # Ignore input while NOVA is speaking
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
    ratio = WHISPER_RATE / SAMPLE_RATE
    target_length = int(len(audio) * ratio)
    resampled = np.interp(
        np.linspace(0, len(audio), target_length),
        np.arange(len(audio)),
        audio.flatten()
    ).astype(np.int16)
    return resampled


def transcribe(audio: np.ndarray) -> str:
    # Reject recordings that are pure silence/noise
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

        # Reject low confidence transcriptions
        if info.language_probability < 0.7:
            return ""

        text = " ".join([s.text for s in segments]).strip()
        return text


def listen(duration: int = 5) -> str:
    audio = record_until_silence()
    return transcribe(audio)


if __name__ == "__main__":
    print("Say something...")
    text = listen()
    print(f"You said: {text}")