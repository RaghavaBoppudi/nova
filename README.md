# NOVA — Neural Operations Voice Assistant

A privacy-focused AI voice assistant built for macOS. Runs entirely on your device. No subscriptions. No telemetry. No data leaves your machine.

## What NOVA Can Do Right Now

- **Voice in, voice out** — speak naturally, NOVA responds in a human voice
- **Apple Calendar** — read your schedule, create events, move events, delete events, all by voice
- **Apple Reminders** — create, read, complete, and delete reminders by voice
- **Math** — calculations and percentage queries handled instantly without the LLM
- **Date intelligence** — understands "next Friday", "this Sunday", "2 weeks from now", "what day was May 12 1928"
- **Conversational flow** — if you say "set up a meeting on Friday", NOVA asks what time. Missing info is always requested, never assumed.
- **Session memory** — remembers what you said earlier in the conversation
- **Cross-session memory** — remembers things you've told it across sessions using semantic search

## Privacy

All processing happens on your Mac. The LLM runs locally via Ollama. Your voice never leaves your device. Your calendar and reminder data is read directly via AppleScript — no cloud sync required. Conversations are stored in a local SQLite database.

NOVA does not connect to the internet for any of its current features.

## A Note on Expectations

NOVA is a one-person passion project, built in spare time alongside a full-time job in data engineering. It is not as capable as Siri, Google Assistant, or Alexa. Those are products built by thousands of engineers with billions in funding. NOVA is not competing with them.

What NOVA offers is different: everything runs on your device, nothing is sent to a server, and the code is fully open for anyone to read and verify. If that trade-off — capability for privacy and transparency — resonates with you, NOVA might be worth trying.

If you need a fully-featured voice assistant, use Siri. If you want one you can trust completely, NOVA is here.

## Known Limitations

- Llama 3.1 8B can hallucinate on obscure factual queries — treat general knowledge answers as approximate
- macOS only — no Windows or Linux support currently
- Built-in mic does not work in clamshell mode — use AirPods or external mic
- Response time is 5-10 seconds on M2 — will improve with faster hardware

## Future Improvements

- Notes — create and search Apple Notes by voice
- Alarms — set and manage alarms by voice
- Wake word detection ("Hey NOVA") to replace push-to-talk
- Self-hosted web search via SearXNG for real-time information
- Natural language reminders with full context ("remind me about this when I get home")
- Statistical modeling and advanced math
- Install script for one-command setup
- Expanded platform support

## Requirements

- macOS 13+
- Apple Silicon recommended (M1/M2/M3)
- 16GB RAM minimum
- Python 3.11.9
- Ollama
- Homebrew

## Installation

### 1. Install Homebrew and Ollama
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install ollama
brew services start ollama
ollama pull llama3.1:8b
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

### 6. Run NOVA
```bash
export PYTHONPATH="/path/to/nova"
python src/main.py
```

## Architecture

| Component | Tool |
|---|---|
| LLM | Ollama + Llama 3.1 8B (local) |
| Speech to Text | faster-whisper (Whisper Small, local) |
| Text to Speech | Kokoro ONNX — af_bella voice (local) |
| Calendar | AppleScript via osascript |
| Reminders | AppleScript via osascript |
| Session Memory | SQLite |
| Semantic Memory | ChromaDB + sentence-transformers |
| Date Parsing | dateparser + python-dateutil |
| Tool Routing | Single LLM classification call |

## Status

Active development. Pre-beta. Not yet ready for general use.

## License

MIT — see [LICENSE](LICENSE)