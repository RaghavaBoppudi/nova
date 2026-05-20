# NOVA - Neural Operations Voice Assistant

## What This Is
A privacy-focused voice assistant running on macOS.
All personal data stays on device. LLM inference uses Groq's cloud API by default,
with a local Ollama fallback available for fully offline operation.

## Hard Rules
- All dependencies must be MIT or Apache 2.0 licensed. Check before suggesting any library.
- No OpenAI, Google Cloud, AWS, or any paid/cloud API (Groq is the approved exception)
- No GPL-licensed libraries
- Python 3.11.9 only
- Do not modify .venv, .git, or any config outside src/
- Never commit .env or API keys

## Stack
- LLM: Groq API (llama-3.1-8b-instant) — fallback: Ollama + Gemma 3 4B
- STT: faster-whisper (Whisper Small, runs locally)
- TTS: Kokoro ONNX (af_bella voice, runs locally)
- Calendar: AppleScript via osascript
- Reminders: AppleScript via osascript
- Notes: AppleScript via osascript
- Memory: SQLite (session) + ChromaDB (cross-session semantic)
- Audio: sounddevice + PyAudio
- Date parsing: dateparser + python-dateutil

## Project Structure
- src/ — all application code
- tests/ — one test file per src module
- docs/ — architecture notes
- models/ — local TTS model files (not committed to git)

## Environment Variables
- GROQ_API_KEY — required for Groq backend (default)
- NOVA_BACKEND=local — switch to Ollama instead of Groq
- NOVA_MODEL — override Groq model (default: llama-3.1-8b-instant)
- NOVA_OLLAMA_MODEL — override Ollama model (default: gemma3:4b)

## Current State
- Voice input with silence detection
- Voice output via Kokoro TTS with interrupt support
- Math and percentage calculations
- Apple Calendar — read, create, move, delete events
- Apple Reminders — read, create, complete, delete, delete by date
- Apple Notes — read, create, search, delete
- Conversational info collection (asks for missing date/time)
- Session memory (SQLite)
- Cross-session semantic memory (ChromaDB)
- Date/time calculations and natural language date parsing
- Tool routing via single LLM classification call
- Natural number/unit speech formatting

## Hardware Notes
- Mac may run in clamshell mode — built-in mic does not work in this mode
- Use AirPods or external microphone for audio input
- Default sample rate is 48000 Hz (not 16000) — always resample to 16000 for Whisper