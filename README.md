# NOVA : Neural Operations Voice Assistant

A fully local, privacy-first AI voice assistant built for macOS. No cloud. No subscriptions. No data leaves your machine.

## Features
- Voice input via push-to-talk (Whisper STT)
- Natural voice output (Kokoro TTS - af_bella)
- Conversational memory within sessions (SQLite)
- Cross-session semantic memory (ChromaDB)
- Apple Calendar — read, create, and move events
- Math and percentage calculations
- Intelligent tool routing — automatically decides between math, calendar, and LLM
- Powered by Llama 3.1 8B running locally via Ollama

## Privacy
All processing happens on-device. No API keys, no cloud services, no telemetry. Your conversations are stored locally in SQLite and ChromaDB databases that never leave your machine.

## Requirements
- macOS 13+
- Apple Silicon recommended (M1/M2/M3)
- 16GB RAM minimum
- Python 3.11.9
- Ollama

## Installation

### 1. Clone the repo
```bash
git clone https://github.com/raghavaboppudi/nova.git
cd nova
```

### 2. Set up Python environment
```bash
pyenv local 3.11.9
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Install and start Ollama
```bash
brew install ollama
brew services start ollama
ollama pull llama3.1:8b
```

### 4. Download voice model
```bash
mkdir -p models/tts
cd models/tts
wget https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
wget https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
cd ../..
```

### 5. Run NOVA
```bash
python src/main.py
```

## Architecture
- **STT**: faster-whisper (Whisper Small, runs locally)
- **LLM**: Ollama + Llama 3.1 8B
- **TTS**: Kokoro ONNX (af_bella voice)
- **Calendar**: AppleScript via osascript
- **Session Memory**: SQLite
- **Semantic Memory**: ChromaDB + sentence-transformers
- **Tool Router**: keyword + math detection with LLM fallback

## Known Limitations
- Factual queries rely on Llama 3.1 8B which showed signed of hallucination on obscure topics
- Real-time data (prices, news) not yet supported - coming post-beta with search integration
- Built and tested on macOS only — other platforms not supported

## Roadmap
- Web search integration via Brave Search API
- Self-hosted private search via SearXNG post-beta
- Wake word detection ("Hey NOVA") to replace push-to-talk
- Statistical modeling and advanced math
- Expanded calendar parsing for natural language dates ("next Tuesday at 3")
- Beta release and community feedback

## Status
Currently in active development. Beta release coming soon.

## License
MIT — see [LICENSE](LICENSE)