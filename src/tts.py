import re
import sounddevice as sd
import numpy as np
import wave
import io
from datetime import datetime
from kokoro_onnx import Kokoro

MODEL_PATH = "models/tts/kokoro-v1.0.onnx"
VOICES_PATH = "models/tts/voices-v1.0.bin"
VOICE = "af_bella"

print("Loading Kokoro voice model...")
kokoro = Kokoro(MODEL_PATH, VOICES_PATH)
print("Kokoro ready.")


def clean_for_speech(text: str) -> str:
    # Normalize unicode spaces
    text = text.replace('\u202f', ' ').replace('\u00a0', ' ')

    # Convert 2026-05-15 -> May 15th
    def format_iso_date(match):
        try:
            dt = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            suffix = "th" if 11 <= dt.day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(dt.day % 10, "th")
            return dt.strftime(f"%B {dt.day}{suffix}")
        except:
            return match.group(0)

    text = re.sub(r'(\d{4})-(\d{2})-(\d{2})', format_iso_date, text)

    # Convert 5/15/26 -> May 15th
    def format_short_date(match):
        try:
            month, day, year = match.group(1), match.group(2), match.group(3)
            year_full = f"20{year}" if len(year) == 2 else year
            dt = datetime(int(year_full), int(month), int(day))
            suffix = "th" if 11 <= dt.day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(dt.day % 10, "th")
            return dt.strftime(f"%B {dt.day}{suffix}")
        except:
            return match.group(0)

    text = re.sub(r'(\d{1,2})/(\d{1,2})/(\d{2,4})', format_short_date, text)

    # Convert 9:00:00 AM -> 9 AM, 9:30:00 AM -> 9:30 AM
    def format_time(match):
        hour = match.group(1)
        minute = match.group(2)
        period = match.group(5)
        if minute == "00":
            return f"{hour} {period}"
        return f"{hour}:{minute} {period}"

    text = re.sub(
        r'(\d{1,2}):(\d{2})(:(\d{2}))?\s*(AM|PM)',
        format_time,
        text,
        flags=re.IGNORECASE
    )

    # Convert decimals like 0.04 to natural speech
    def format_decimal(match):
        number_str = match.group(0)
        parts = number_str.split('.')
        whole = parts[0]
        decimal = parts[1]
        
        digit_words = {
            '0': 'zero', '1': 'one', '2': 'two', '3': 'three',
            '4': 'four', '5': 'five', '6': 'six', '7': 'seven',
            '8': 'eight', '9': 'nine'
        }
        
        decimal_spoken = ' '.join(digit_words[d] for d in decimal)
        
        if whole == '0':
            return f"zero point {decimal_spoken}"
        return f"{whole} point {decimal_spoken}"

    text = re.sub(r'\d+\.\d+', format_decimal, text)

    return text


def speak(text: str, speed: float = 1.0):
    text = clean_for_speech(text)
    samples, sample_rate = kokoro.create(text, voice=VOICE, speed=speed, lang="en-us")
    sd.play(samples, samplerate=sample_rate)
    sd.wait()


if __name__ == "__main__":
    speak("Hello, I am NOVA. Your local AI voice assistant. How can I help you today?")