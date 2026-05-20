import re
import threading
import sounddevice as sd
import numpy as np
from datetime import datetime
from kokoro_onnx import Kokoro

# Model configuration
MODEL_PATH = "models/tts/kokoro-v1.0.onnx"
VOICES_PATH = "models/tts/voices-v1.0.bin"
VOICE = "af_bella"

# Playback interrupt flag
_interrupt = threading.Event()

print("Loading Kokoro voice model...")
kokoro = Kokoro(MODEL_PATH, VOICES_PATH)
print("Kokoro ready.")


def interrupt():
    """Stop current TTS playback immediately."""
    _interrupt.set()
    sd.stop()


def _ordinal_suffix(day: int) -> str:
    """Return ordinal suffix for a day number."""
    if 11 <= day <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")


def clean_for_speech(text: str) -> str:
    """
    Clean and format text for natural spoken output.
    Strips markdown, converts dates/times/decimals to speakable form.
    """
    # Strip markdown formatting
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)   # bold
    text = re.sub(r'\*(.+?)\*', r'\1', text)         # italic
    text = re.sub(r'#{1,6}\s+', '', text)             # headers
    text = re.sub(r'[😊😀😂🤔👍🎉✅❌]', '', text)   # emojis

    # Normalize unicode spaces
    text = text.replace('\u202f', ' ').replace('\u00a0', ' ')

    # Convert ISO dates: 2026-05-15 → May 15th
    def format_iso_date(match):
        try:
            dt = datetime(int(match.group(1)), int(
                match.group(2)), int(match.group(3)))
            return dt.strftime(f"%B {dt.day}{_ordinal_suffix(dt.day)}")
        except Exception:
            return match.group(0)

    text = re.sub(r'(\d{4})-(\d{2})-(\d{2})', format_iso_date, text)

    # Convert short dates: 5/15/26 → May 15th
    def format_short_date(match):
        try:
            month, day, year = match.group(1), match.group(2), match.group(3)
            year_full = f"20{year}" if len(year) == 2 else year
            dt = datetime(int(year_full), int(month), int(day))
            return dt.strftime(f"%B {dt.day}{_ordinal_suffix(dt.day)}")
        except Exception:
            return match.group(0)

    text = re.sub(r'(\d{1,2})/(\d{1,2})/(\d{2,4})', format_short_date, text)

    # Convert times: 9:00:00 AM → 9 AM, 9:30:00 AM → 9:30 AM
    def format_time(match):
        hour, minute, period = match.group(1), match.group(2), match.group(5)
        return f"{hour} {period}" if minute == "00" else f"{hour}:{minute} {period}"

    text = re.sub(
        r'(\d{1,2}):(\d{2})(:(\d{2}))?\s*(AM|PM)',
        format_time,
        text,
        flags=re.IGNORECASE
    )

    # Convert decimals: 0.04 → zero point zero four
    digit_words = {
        '0': 'zero', '1': 'one', '2': 'two', '3': 'three', '4': 'four',
        '5': 'five', '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine'
    }

    def format_decimal(match):
        whole, decimal = match.group(0).split('.')
        spoken = ' '.join(digit_words[d] for d in decimal)
        return f"zero point {spoken}" if whole == '0' else f"{whole} point {spoken}"

    text = re.sub(r'\d+\.\d+', format_decimal, text)

# Convert large numbers with commas to speakable form
    def expand_large_number(match):
        num_str = match.group(0).replace(',', '')
        try:
            n = int(num_str)
            if n >= 1_000_000_000:
                billions = n // 1_000_000_000
                remainder = n % 1_000_000_000
                if remainder == 0:
                    return f"{billions} billion"
                millions = remainder // 1_000_000
                return f"{billions} billion {millions} million" if millions else f"{billions} billion"
            if n >= 1_000_000:
                millions = n // 1_000_000
                remainder = n % 1_000_000
                if remainder == 0:
                    return f"{millions} million"
                thousands = remainder // 1_000
                rest = remainder % 1_000
                parts = [f"{millions} million"]
                if thousands:
                    parts.append(f"{thousands} thousand")
                if rest:
                    parts.append(f"and {rest}")
                return ' '.join(parts)
            if n >= 1_000:
                thousands = n // 1_000
                rest = n % 1_000
                return f"{thousands} thousand {rest}" if rest else f"{thousands} thousand"
            return num_str
        except Exception:
            return match.group(0)

    text = re.sub(r'\b\d{1,3}(?:,\d{3})+\b', expand_large_number, text)

    # Expand common units to speakable form
    unit_expansions = [
        (r'\bm/s\b', 'meters per second'),
        (r'\bkm/h\b', 'kilometers per hour'),
        (r'\bmph\b', 'miles per hour'),
        (r'\bkm/s\b', 'kilometers per second'),
        (r'\bm/s²\b', 'meters per second squared'),
        (r'\bkg\b', 'kilograms'),
        (r'\blbs?\b', 'pounds'),
        (r'\bkm\b', 'kilometers'),
        (r'\bcm\b', 'centimeters'),
        (r'\bmm\b', 'millimeters'),
    ]
    for pattern, replacement in unit_expansions:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    return text


def speak(text: str, speed: float = 1.0) -> bool:
    """
    Convert text to speech and play it.
    Returns True if playback completed, False if interrupted.
    """
    _interrupt.clear()
    text = clean_for_speech(text)
    samples, sample_rate = kokoro.create(
        text, voice=VOICE, speed=speed, lang="en-us")
    sd.play(samples, samplerate=sample_rate)

    while sd.get_stream().active:
        if _interrupt.is_set():
            sd.stop()
            return False
        threading.Event().wait(0.05)

    return not _interrupt.is_set()


if __name__ == "__main__":
    speak("Hello, I am NOVA. Your local AI voice assistant. How can I help you today?")
