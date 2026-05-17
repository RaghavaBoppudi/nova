# NOVA - Neural Operations Voice Assistant

## What This Is
A fully local, privacy-focused voice assistant running on macOS.
All AI processing, memory, and personal data stays on device.

## Hard Rules
- All dependencies must be MIT or Apache 2.0 licensed. Check before suggesting any library.
- No OpenAI, Google Cloud, AWS, or any paid/cloud API
- No GPL-licensed libraries
- Python 3.11.9 only
- Do not modify .venv, .git, or any config outside src/

## Stack
- LLM: Ollama + Llama 3.1 8B
- STT: faster-whisper (Whisper Small)
- TTS: Kokoro ONNX
- Calendar: AppleScript via osascript
- Reminders: AppleScript via osascript
- Memory: SQLite (session) + ChromaDB (cross-session semantic)
- Audio: sounddevice + PyAudio
- Date parsing: dateparser + python-dateutil

## Project Structure
- src/ — all application code
- tests/ — one test file per src module
- docs/ — architecture notes
- models/ — local TTS model files (not committed to git)

## Current State
- Voice input with silence detection (no fixed duration)
- Voice output via Kokoro TTS
- Math and percentage calculations
- Apple Calendar — read, create, move, delete events
- Apple Reminders — read, create, complete, delete
- Conversational info collection (asks for missing date/time)
- Session memory (SQLite)
- Cross-session semantic memory (ChromaDB)
- Date/time calculations and natural language date parsing
- Tool routing via single LLM classification call

## Hardware Notes
- Mac may run in clamshell mode — built-in mic does not work in this mode
- Use AirPods or external microphone for audio input
- Default sample rate is 48000 Hz (not 16000) — always resample to 16000 for Whisper