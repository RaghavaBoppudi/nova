import sys
import signal
import re
import threading
from src.stt import listen
from src.tts import speak, interrupt
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

# Global flag — is NOVA currently speaking?
_speaking = threading.Event()


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


def extract_time(prompt_lower: str) -> str | None:
    time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)', prompt_lower)
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2)) if time_match.group(2) else 0
        meridiem = time_match.group(3).replace('.', '')
        if meridiem == 'pm' and hour != 12:
            hour += 12
        elif meridiem == 'am' and hour == 12:
            hour = 0
        return f"{hour:02d}:{minute:02d}"
    return None


def handle_missing_info(pending: dict, prompt: str, prompt_lower: str):
    from src.calendar_handler import parse_date
    from src.reminder_handler import create_reminder
    from src.calendar_handler import create_event, move_event

    missing = pending.get("missing")
    title = pending.get("title", "")
    action = pending.get("action", "create")
    is_reminder = pending.get("type") == "reminder"

    if missing == "both":
        time_str = extract_time(prompt_lower)
        date_str = parse_date(prompt)
        if date_str and time_str:
            if is_reminder:
                result = create_reminder(title, date_str, time_str)
            elif action == "move":
                result = move_event(title, date_str, time_str)
            else:
                result = create_event(title, date_str, time_str, pending.get("duration", 60))
            return result, None
        elif date_str:
            pending["missing"] = "time"
            pending["date"] = date_str
            return None, f"What time should I {'remind you to' if is_reminder else 'schedule' if action == 'create' else 'move'} {title}?"
        elif time_str:
            pending["missing"] = "date"
            pending["time"] = time_str
            return None, f"What date should I {'remind you to' if is_reminder else 'schedule' if action == 'create' else 'move'} {title}?"
        else:
            return None, "I didn't catch that. What date and time?"

    elif missing == "time":
        time_str = extract_time(prompt_lower)
        if time_str:
            date_str = pending.get("date")
            if is_reminder:
                result = create_reminder(title, date_str, time_str)
            elif action == "move":
                result = move_event(title, date_str, time_str)
            else:
                result = create_event(title, date_str, time_str, pending.get("duration", 60))
            return result, None
        return None, "I didn't catch the time. What time?"

    elif missing == "date":
        date_str = parse_date(prompt)
        if date_str:
            time_str = pending.get("time")
            if is_reminder:
                result = create_reminder(title, date_str, time_str)
            elif action == "move":
                result = move_event(title, date_str, time_str)
            else:
                result = create_event(title, date_str, time_str, pending.get("duration", 60))
            return result, None
        return None, "I didn't catch the date. What date?"

    return None, "Something went wrong. Please try again."


def speak_interruptible(text: str):
    """Speak in a background thread. Enter key interrupts."""
    _speaking.set()
    t = threading.Thread(target=_speak_thread, args=(text,), daemon=True)
    t.start()
    return t


def _speak_thread(text: str):
    speak(text)
    _speaking.clear()


def wait_for_enter_or_finish(speak_thread: threading.Thread) -> bool:
    """
    Wait for either:
    - TTS to finish naturally → return False (not interrupted)
    - User presses Enter → interrupt TTS → return True (interrupted)
    """
    import select

    while speak_thread.is_alive():
        # Check if Enter was pressed (non-blocking)
        if sys.stdin in select.select([sys.stdin], [], [], 0.1)[0]:
            sys.stdin.readline()  # consume the Enter
            interrupt()
            speak_thread.join()
            return True
    return False


def run():
    init_db()
    session_id = create_session()
    pending_action = None
    pending_info = None

    print("NOVA is ready.")
    print("Press Enter to speak. Press Enter again while NOVA is talking to interrupt.")
    speak("Hello, I am NOVA. How can I help you?")

    while True:
        input("\nPress Enter to speak...")
        print("Listening...")
        prompt = listen()

        if not prompt:
            speak("I didn't catch that. Please try again.")
            continue

        print(f"You: {prompt}")
        prompt_lower = prompt.lower().strip()

        # Handle pending calendar delete confirmation
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
                    t = speak_interruptible(result)
                    wait_for_enter_or_finish(t)
                    continue
            else:
                pending_action = None
                response = "Cancelled."
                print(f"NOVA: {response}")
                t = speak_interruptible(response)
                wait_for_enter_or_finish(t)
                continue

        # Handle pending missing info
        if pending_info:
            result, follow_up = handle_missing_info(pending_info, prompt, prompt_lower)
            if result:
                pending_info = None
                print(f"NOVA: {result}")
                t = speak_interruptible(result)
                wait_for_enter_or_finish(t)
            else:
                print(f"NOVA: {follow_up}")
                t = speak_interruptible(follow_up)
                wait_for_enter_or_finish(t)
            continue

        # Normal routing
        result = route(prompt, session_id, system_prompt=SYSTEM_PROMPT)

        if isinstance(result, dict) and result.get("requires_confirmation"):
            pending_action = result
            response = result["message"]
        elif isinstance(result, dict) and result.get("requires_event_info"):
            pending_info = {**result, "type": "event", "action": result.get("action", "create")}
            response = result["message"]
        elif isinstance(result, dict) and result.get("requires_reminder_info"):
            pending_info = {**result, "type": "reminder"}
            response = result["message"]
        else:
            response = result

        print(f"NOVA: {response}")
        t = speak_interruptible(response)
        interrupted = wait_for_enter_or_finish(t)

        # If interrupted, immediately start listening
        if interrupted:
            print("Listening...")
            prompt = listen()
            if not prompt:
                continue
            print(f"You: {prompt}")
            prompt_lower = prompt.lower().strip()

            result = route(prompt, session_id, system_prompt=SYSTEM_PROMPT)

            if isinstance(result, dict) and result.get("requires_confirmation"):
                pending_action = result
                response = result["message"]
            elif isinstance(result, dict) and result.get("requires_event_info"):
                pending_info = {**result, "type": "event", "action": result.get("action", "create")}
                response = result["message"]
            elif isinstance(result, dict) and result.get("requires_reminder_info"):
                pending_info = {**result, "type": "reminder"}
                response = result["message"]
            else:
                response = result

            print(f"NOVA: {response}")
            t = speak_interruptible(response)
            wait_for_enter_or_finish(t)


if __name__ == "__main__":
    run()