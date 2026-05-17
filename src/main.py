import sys
import signal
from src.stt import listen
from src.tts import speak
from src.router import route
from src.memory import init_db, create_session

SYSTEM_PROMPT = """You are NOVA, a voice assistant.
Always respond in 1-2 sentences maximum, no exceptions.
No filler, no preamble, no bullet points.
Give the direct answer only.
Always use imperial units by default (mph, miles, lb, Fahrenheit).
For prices, default to USD.
If asked about current prices or live data, say you don't have real-time information and suggest checking online."""


def signal_handler(sig, frame):
    print("\nGoodbye.")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def run():
    init_db()
    session_id = create_session()
    print("NOVA is ready. Press Ctrl+C to quit.")
    speak("Hello, I am NOVA. How can I help you?")

    while True:
        input("\nPress Enter to speak...")
        print("Listening...")
        prompt = listen(duration=5)

        if not prompt:
            speak("I didn't catch that. Please try again.")
            continue

        print(f"You: {prompt}")
        response = route(prompt, session_id, system_prompt=SYSTEM_PROMPT)
        print(f"NOVA: {response}")
        speak(response)


if __name__ == "__main__":
    run()
