# N.O.V.A. - Neural Operations Voice Assistant

I built N.O.V.A. as a side project while working full-time as a data engineer. The idea was simple: what if your voice assistant actually knew you, remembered what you told it, and didn't send your personal data to a corporation? This is my attempt at that.

It's not Siri. It's not trying to be. Siri has thousands of engineers and billions in funding behind it. N.O.V.A. has me, some free APIs, and weekends.

## What it can do

- Talk to it, it talks back. Speak naturally, no special commands needed.
- Manage your Apple Calendar by voice. Read, create, move, delete events.
- Manage your Apple Reminders by voice. Create, read, complete, delete.
- Manage your Apple Notes by voice. Create, search, delete.
- Do math. Calculations, percentages, unit conversions.
- Understand dates like "next Friday", "this Sunday", "2 weeks from now", or even "what day was May 12 1928".
- Ask for missing info. If you say "set up a meeting on Friday" without a time, it asks you for one.
- Remember things. It keeps track of your conversation and remembers things you've told it across sessions.
- Interrupt it. Press Enter while it's talking to stop it and ask something new.

## Privacy

I built this with Privacy being the main focus. Here's exactly what stays on your Mac and what doesn't.

Stays on your device: your calendar, reminders, notes, conversation history, long-term memory, and all voice processing (speech to text and text to speech).

Goes to Groq's servers: the text of what you say out loud, for the purpose of generating a response. That's it.
Groq's privacy policy confirms they don't train on or log API data. You can read it yourself at [console.groq.com/docs/your-data](https://console.groq.com/docs/your-data).

If you want fully offline operation, set `NOVA_BACKEND=local` in your `.env` file. It'll use a local Ollama model instead. Slower, but nothing leaves your device at all.

## Honest expectations

This is a passion project. It will sometimes mishear you, occasionally give wrong answers, and has rough edges. I'm fixing things as I go. If you try it and find bugs, open an issue. If you want to contribute, pull requests are welcome.

## Requirements

- macOS 13 or later
- Apple Silicon recommended (M1/M2/M3)
- 16GB RAM minimum
- Python 3.11.9
- Homebrew
- A free Groq API key from [console.groq.com](https://console.groq.com) (no credit card needed)

## Installation

**1. Install Homebrew**
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**2. Install pyenv and Python 3.11.9**
```bash
brew install pyenv
pyenv install 3.11.9
```

**3. Clone the repo**
```bash
git clone https://github.com/raghavaboppudi/nova.git
cd nova
pyenv local 3.11.9
```

**4. Set up your Python environment**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**5. Download the voice model**
```bash
mkdir -p models/tts
cd models/tts
wget https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
wget https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
cd ../..
```

**6. Add your API key**
```bash
cp .env.example .env
```
Open `.env` and add your Groq API key:

GROQ_API_KEY=your_key_here

**7. Run it**
```bash
export PYTHONPATH="/path/to/nova"
python src/main.py
```

## How it works

| Part | What's used |
|---|---|
| Language model | Groq API with llama-3.3-70b-versatile |
| Local fallback | Ollama with Gemma 3 4B |
| Speech to text | faster-whisper (runs locally) |
| Text to speech | Kokoro ONNX, af_bella voice (runs locally) |
| Calendar / Reminders / Notes | AppleScript |
| Conversation memory | SQLite |
| Long-term memory | ChromaDB + sentence-transformers |
| Date parsing | dateparser + python-dateutil |

## Known issues

- The LLM can get factual questions wrong sometimes. Treat general knowledge answers as a starting point, not gospel.
- macOS only for now.
- Built-in mic doesn't work in clamshell mode. Use AirPods or an external mic.
- Groq free tier is capped at 1,000 requests per day on the 70B model.

## What's coming

- Alarms and timers
- World clock and timezone support
- Unit and currency conversions
- Wake word so you don't have to press a button
- Web search for real-time information
- A proper install script
- Model selection without touching config files

## License

MIT. See [LICENSE](LICENSE).