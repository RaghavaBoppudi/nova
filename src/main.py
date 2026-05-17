import sys
import signal
from src.stt import listen
from src.tts import speak
from src.router import route
from src.memory import init_db, create_session

SYSTEM_PROMPT = """You are NOVA, a voice assistant. Your responses will be spoken aloud.
Rules:
- Maximum 2 sentences. Hard limit. Never exceed this.
- If the answer needs more than 2 sentences, give the most important part only.
- No bullet points, no lists, no markdown.
- No filler words: no 'certainly', 'great question', 'of course', 'however'.
- Answer immediately. No preamble.
- Use imperial units (mph, miles, lb, Fahrenheit).
- For unknown prices or live data, say 'I don't have real-time data for that.'
- Never suggest the user ask Siri, Google, or Alexa."""

CONFIRM_WORDS = ["yes", "yeah", "yep", "yup", "sure", "ok", "okay", "go ahead",
                 "do it", "correct", "right", "affirmative", "delete", "remove",
                 "delete them", "delete it", "yes please", "go for it", "absolutely"]

DENY_WORDS = ["no", "nope", "cancel", "stop", "don't", "nevermind", "never mind",
              "abort", "wait", "hold on", "negative"]


def signal_handler(sig, frame):
    print("\nGoodbye.")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def is_confirmation(prompt: str) -> bool:
    prompt_lower = prompt.lower().strip().rstrip('.,!')
    for word in DENY_WORDS:
        if word in prompt_lower:
            return False
    for word in CONFIRM_WORDS:
        if word in prompt_lower:
            return True
    return False


def run():
    init_db()
    session_id = create_session()
    pending_action = None

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

        if pending_action:
            if is_confirmation(prompt):
                action_type = pending_action.get("type")
                if action_type == "delete_range":
                    from src.calendar_handler import delete_events_for_range
                    result = delete_events_for_range(
                        pending_action["start"],
                        pending_action["end"]
                    )
                    pending_action = None
                    print(f"NOVA: {result}")
                    speak(result)
                    continue
            else:
                pending_action = None
                response = "Cancelled. No events were deleted."
                print(f"NOVA: {response}")
                speak(response)
                continue

        result = route(prompt, session_id, system_prompt=SYSTEM_PROMPT)

        if isinstance(result, dict) and result.get("requires_confirmation"):
            pending_action = result
            response = result["message"]
        else:
            response = result

        print(f"NOVA: {response}")
        speak(response)


if __name__ == "__main__":
    run()
