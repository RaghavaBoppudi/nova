cat > CLAUDE.md << 'EOF'
# Jarvis - Local AI Voice Assistant

## What This Is
A fully local, privacy-first voice assistant running on M2 MacBook Air (16GB).
No cloud. No paid APIs. No data leaves the machine.

## Hard Rules
- All dependencies must be MIT or Apache 2.0 licensed. Check before suggesting any library.
- No OpenAI, Google Cloud, AWS, or any paid/cloud API
- No GPL-licensed libraries
- Python 3.11.9 only
- Do not modify .venv, .git, or any config outside src/

## Stack
- LLM: Ollama + Llama 3.1 8B
- STT: faster-whisper
- TTS: Piper TTS
- Calendar: EventKit via PyObjC
- Memory: SQLite (session) + ChromaDB (cross-session)
- Audio: sounddevice + PyAudio
- Orchestration: LangChain (minimal use)

## Project Structure
- src/ — all application code
- tests/ — one test file per src module
- docs/ — architecture notes

## Current Phase
Phase 1 — Local LLM core + basic math
EOF