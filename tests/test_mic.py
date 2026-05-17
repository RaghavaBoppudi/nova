import sounddevice as sd
import numpy as np

SAMPLE_RATE = 48000
DURATION = 5

print("Recording for 5 seconds... speak now.")
audio = sd.rec(
    int(DURATION * SAMPLE_RATE),
    samplerate=SAMPLE_RATE,
    channels=1,
    dtype='int16'
)
sd.wait()

max_amplitude = np.max(np.abs(audio))
print(f"Max amplitude detected: {max_amplitude}")

if max_amplitude < 100:
    print("WARNING: No audio detected. Mic may not be capturing.")
else:
    print("Audio captured successfully.")
