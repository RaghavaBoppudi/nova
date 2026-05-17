import re
import threading
import sounddevice as sd
import numpy as np
from datetime import datetime
from kokoro_onnx import Kokoro

MODEL_PATH = "models/tts/kokoro-v1.0.onnx"
VOICES_PATH = "models/tts/voices-v1.0.bin"
VOICE = "af_bella"

print("Loading Kokoro voice model...")
kokoro = Kokoro(MODEL_PATH, VOICES_PATH)
print("Kokoro ready.")

# Global interrupt flag
_interrupt = threading.Event()


def interrupt():
    """Call this to stop current playback."""
    _interrupt.set()
    sd.stop()


def clean_for_speech(text: str) -> str:
    text = text.replace('\u202f', ' ').replace('\u00a0', ' ')

    def format_iso_date(match):
        try:
            dt = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            suffix = "th" if 11 <= dt.day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(dt.day % 10, "th")
            return dt.strftime(f"%B {dt.day}{suffix}")
        except:
            return match.group(0)

    text = re.sub(r'(\d{4})-(\d{2})-(\d{2})', format_iso_date, text)

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


def speak(text: str, speed: float = 1.0) -> bool:
    """
    Speak text. Returns True if completed, False if interrupted.
    """
    _interrupt.clear()
    text = clean_for_speech(text)
    samples, sample_rate = kokoro.create(text, voice=VOICE, speed=speed, lang="en-us")
    sd.play(samples, samplerate=sample_rate)

    # Wait for playback to finish or interrupt
    while sd.get_stream().active:
        if _interrupt.is_set():
            sd.stop()
            return False
        threading.Event().wait(0.05)

    return not _interrupt.is_set()


if __name__ == "__main__":
    speak("Hello, I am NOVA. Your local AI voice assistant. How can I help you today?")