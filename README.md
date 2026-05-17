# NOVA — Neural Operations and Voice Assistant

A fully local, privacy-first AI voice assistant built for macOS. No cloud. No subscriptions. No data leaves your machine.

## Features
- Voice input via push-to-talk (Whisper STT)
- Natural voice output (Kokoro TTS)
- Conversational memory across sessions
- Apple Calendar read, create, and move events
- Math and unit conversion
- Powered by Llama 3.1 8B running locally via Ollama

## Privacy
All processing happens on-device. No API keys, no cloud services, no telemetry.

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

## Status
Currently in active development. Beta release soon.

## License
MIT — see [LICENSE](LICENSE)