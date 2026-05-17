import sounddevice as sd
import numpy as np
import tempfile
import wave
from faster_whisper import WhisperModel

SAMPLE_RATE = 48000
WHISPER_RATE = 16000
CHANNELS = 1

print("Loading model...")
model = WhisperModel("small", device="cpu", compute_type="int8")

print("Recording for 5 seconds... speak now.")
audio = sd.rec(
    int(5 * SAMPLE_RATE),
    samplerate=SAMPLE_RATE,
    channels=CHANNELS,
    dtype='int16'
)
sd.wait()
print("Done recording.")

# Resample
ratio = WHISPER_RATE / SAMPLE_RATE
target_length = int(len(audio) * ratio)
resampled = np.interp(
    np.linspace(0, len(audio), target_length),
    np.arange(len(audio)),
    audio.flatten()
).astype(np.int16)

print(f"Max amplitude before resample: {np.max(np.abs(audio))}")
print(f"Max amplitude after resample: {np.max(np.abs(resampled))}")

with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
    wav_path = f.name
    with wave.open(wav_path, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(WHISPER_RATE)
        wf.writeframes(resampled.tobytes())
    
    print(f"WAV saved to: {wav_path}")
    segments, info = model.transcribe(wav_path, beam_size=5)
    segments = list(segments)
    print(f"Detected language: {info.language} (probability: {info.language_probability:.2f})")
    print(f"Number of segments: {len(segments)}")
    for s in segments:
        print(f"Segment: '{s.text}'")
