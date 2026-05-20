# NOVA — Neural Operations Voice Assistant

A privacy-focused AI voice assistant built for macOS. Your personal data never leaves your device. No subscriptions. No telemetry.

> "What if your assistant actually knew you, remembered everything you told it, ran entirely on your device, and you could trust it completely?"

## What NOVA Can Do Right Now

- **Voice in, voice out** — speak naturally, NOVA responds in a human voice
- **Apple Calendar** — read your schedule, create, move, and delete events by voice
- **Apple Reminders** — create, read, complete, and delete reminders by voice
- **Apple Notes** — create, search, and delete notes by voice
- **Math** — calculations and percentage queries handled instantly
- **Date intelligence** — understands "next Friday", "this Sunday", "2 weeks from now", "what day was May 12 1928"
- **Conversational flow** — if you say "set up a meeting on Friday", NOVA asks what time. Missing info is always requested, never assumed.
- **Session memory** — remembers what you said earlier in the conversation
- **Cross-session memory** — remembers things you've told it across sessions using semantic search
- **Interrupt** — press Enter while NOVA is speaking to stop it and ask something new

## Privacy

NOVA is built with privacy as a core principle. Here is exactly what stays on your device and what doesn't:

**Always local — never leaves your Mac:**
- Your calendar, reminders, and notes data
- Your conversation history (SQLite)
- Your long-term memory (ChromaDB)
- Voice processing (Whisper STT, Kokoro TTS)

**Goes to Groq's servers:**
- The text of what you say out loud — for LLM inference only
- Groq explicitly states they do not train on or log API data
- No personal data, calendar contents, or memory is ever sent

**Want fully offline?** Set `NOVA_BACKEND=local` in your `.env` file to use a local Ollama model instead. Response times will be slower but nothing leaves your device.

## A Note on Expectations

NOVA is a one-person passion project, built in spare time alongside a full-time job in data engineering. It is not as capable as Siri, Google Assistant, or Alexa. Those are products built by thousands of engineers with billions in funding. NOVA is not competing with them.

What NOVA offers is different: your personal data never leaves your device, the code is fully open for anyone to read and verify, and it gets smarter the more you use it through local memory. If that trade-off resonates with you, NOVA might be worth trying.

## Requirements

- macOS 13+
- Apple Silicon recommended (M1/M2/M3)
- 16GB RAM minimum
- Python 3.11.9
- Homebrew
- A free Groq API key (or Ollama for fully local operation)

## Installation

### 1. Install Homebrew
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. Install pyenv and Python 3.11.9
```bash
brew install pyenv
pyenv install 3.11.9
```

### 3. Clone the repo
```bash
git clone https://github.com/raghavaboppudi/nova.git
cd nova
pyenv local 3.11.9
```

### 4. Set up Python environment
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 5. Download voice model
```bash
mkdir -p models/tts
cd models/tts
wget https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
wget https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
cd ../..
```

### 6. Configure environment
```bash
cp .env.example .env
```
Add your Groq API key to `.env`:
GROQ_API_KEY=your_key_here

Get a free key at [console.groq.com](https://console.groq.com) — no credit card required.

### 7. Set PYTHONPATH and run
```bash
export PYTHONPATH="/path/to/nova"
python src/main.py
```

## Architecture

| Component | Tool |
|---|---|
| LLM | Groq API — llama-3.1-8b-instant (cloud, fast) |
| LLM fallback | Ollama + Gemma 3 4B (local, private) |
| Speech to Text | faster-whisper — Whisper Small (local) |
| Text to Speech | Kokoro ONNX — af_bella voice (local) |
| Calendar | AppleScript via osascript |
| Reminders | AppleScript via osascript |
| Notes | AppleScript via osascript |
| Session Memory | SQLite (local) |
| Semantic Memory | ChromaDB + sentence-transformers (local) |
| Date Parsing | dateparser + python-dateutil |
| Tool Routing | Single LLM classification call |

## Known Limitations

- LLM may hallucinate on obscure factual queries
- macOS only — no Windows or Linux support currently
- Built-in mic does not work in clamshell mode — use AirPods or external mic
- Groq free tier: 14,400 requests/day, 30/minute

## Future Improvements

- [ ] Alarms and countdown timers
- [ ] World clock and timezone queries
- [ ] Unit and currency conversions
- [ ] Wake word detection ("Hey NOVA")
- [ ] Self-hosted SearXNG for real-time web search
- [ ] Install script for one-command setup
- [ ] Configurable model selection via UI

## Status

Active development. Pre-beta. Not yet ready for general use.

## License

MIT — see [LICENSE](LICENSE)