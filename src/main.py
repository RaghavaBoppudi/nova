import sys
import signal
import re
import threading
import select
from src.stt import listen
from src.tts import speak, interrupt
from src.router import route
from src.memory import init_db, create_session
from src.guardrails import check_input, check_output
from dotenv import load_dotenv
load_dotenv()

SYSTEM_PROMPT = """You are NOVA, a voice assistant. Your responses will be spoken aloud.
Rules:
- Maximum 2 sentences. Hard limit. Never exceed this.
- If the answer needs more than 2 sentences, give the most important part only.
- No bullet points, no lists, no markdown, no bold, no asterisks, no URLs.
- No filler words: no 'certainly', 'great question', 'of course', 'however'.
- No follow up questions. Never ask if the user wants to know more.
- Answer immediately. No preamble.
- Use the units the user asks for. If no units specified, use whatever is most commonly understood for that measurement.
- For unknown prices or live data, say 'I don't have real-time data for that.'
- Never suggest the user ask Siri, Google, or Alexa.
- Never use emojis.
- Never use markdown formatting of any kind.
- Always include units when giving measurements or speeds. - Never give a bare number as an answer. Always include context and units. "343 meters per second" not "343"."""


CONFIRM_WORDS = ["yes", "yeah", "yep", "yup", "sure", "ok", "okay", "go ahead",
                 "do it", "correct", "right", "affirmative", "delete", "remove",
                 "delete them", "delete it", "yes please", "go for it", "absolutely"]

DENY_WORDS = ["no", "nope", "cancel", "stop", "don't", "nevermind", "never mind",
              "abort", "wait", "hold on", "negative"]

_speaking = threading.Event()


def signal_handler(sig, frame):
    print("\nGoodbye.")
    speak("Goodbye.")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def is_confirmation(prompt: str) -> bool:
    """Return True if prompt is an affirmative response, False if negative."""
    prompt_lower = prompt.lower().strip().rstrip('.,!')
    for word in DENY_WORDS:
        if word in prompt_lower:
            return False
    for word in CONFIRM_WORDS:
        if word in prompt_lower:
            return True
    return False


def extract_time(prompt_lower: str) -> str | None:
    """Extract a time expression from text and return HH:MM, or None."""
    match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)', prompt_lower)
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2)) if match.group(2) else 0
    meridiem = match.group(3).replace('.', '')
    if meridiem == 'pm' and hour != 12:
        hour += 12
    elif meridiem == 'am' and hour == 12:
        hour = 0
    return f"{hour:02d}:{minute:02d}"


def handle_missing_info(pending: dict, prompt: str, prompt_lower: str):
    """
    Collect missing date or time info for a pending event or reminder creation.
    Returns (result, None) when complete, or (None, follow_up_question) when still missing info.
    """
    from src.calendar_handler import parse_date, create_event, move_event
    from src.reminder_handler import create_reminder

    missing = pending.get("missing")
    title = pending.get("title", "")
    action = pending.get("action", "create")
    is_reminder = pending.get("type") == "reminder"

    def action_label():
        if is_reminder:
            return "remind you to"
        return "schedule" if action == "create" else "move"

    def execute(date_str, time_str):
        if is_reminder:
            return create_reminder(title, date_str, time_str)
        if action == "move":
            return move_event(title, date_str, time_str)
        return create_event(title, date_str, time_str, pending.get("duration", 60))

    if missing == "both":
        time_str = extract_time(prompt_lower)
        date_str = parse_date(prompt)
        if date_str and time_str:
            return execute(date_str, time_str), None
        if date_str:
            pending["missing"] = "time"
            pending["date"] = date_str
            return None, f"What time should I {action_label()} {title}?"
        if time_str:
            pending["missing"] = "date"
            pending["time"] = time_str
            return None, f"What date should I {action_label()} {title}?"
        return None, "I didn't catch that. What date and time?"

    if missing == "time":
        time_str = extract_time(prompt_lower)
        if time_str:
            return execute(pending.get("date"), time_str), None
        return None, "I didn't catch the time. What time?"

    if missing == "date":
        date_str = parse_date(prompt)
        if date_str:
            return execute(date_str, pending.get("time")), None
        return None, "I didn't catch the date. What date?"

    return None, "Something went wrong. Please try again."


def _speak_thread(text: str):
    speak(text)
    _speaking.clear()


def speak_interruptible(text: str) -> threading.Thread:
    """Speak text in a background thread. Returns the thread."""
    _speaking.set()
    t = threading.Thread(target=_speak_thread, args=(text,), daemon=True)
    t.start()
    return t


def wait_for_enter_or_finish(speak_thread: threading.Thread) -> bool:
    """
    Wait for TTS to finish or Enter key press.
    Returns True if interrupted, False if finished naturally.
    """
    while speak_thread.is_alive():
        if sys.stdin in select.select([sys.stdin], [], [], 0.1)[0]:
            sys.stdin.readline()
            interrupt()
            speak_thread.join()
            return True
    return False


def handle_result(result, pending_action, pending_info, session_id):
    """
    Process a route result and update pending state.
    Returns (response_text, updated_pending_action, updated_pending_info).
    """
    if isinstance(result, dict) and result.get("requires_confirmation"):
        return result["message"], result, pending_info
    if isinstance(result, dict) and result.get("requires_event_info"):
        info = {**result, "type": "event", "action": result.get("action", "create")}
        return result["message"], pending_action, info
    if isinstance(result, dict) and result.get("requires_reminder_info"):
        info = {**result, "type": "reminder"}
        return result["message"], pending_action, info
    return result, pending_action, pending_info


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
            speak("Pardon?")
            continue

        # Reject transcriptions that are too short or garbled
        if len(prompt.split()) < 2:
            speak("Pardon?")
            continue

        print(f"You: {prompt}")
        prompt_lower = prompt.lower().strip()

        # Guardrails — check input before any routing
        guard_status, guard_response = check_input(prompt)
        if guard_status == "crisis":
            print(f"NOVA: {guard_response}")
            t = speak_interruptible(guard_response)
            wait_for_enter_or_finish(t)
            continue
        if guard_status == "distress":
            print(f"NOVA: {guard_response}")
            t = speak_interruptible(guard_response)
            wait_for_enter_or_finish(t)
            continue
        if guard_status == "block":
            print(f"NOVA: {guard_response}")
            t = speak_interruptible(guard_response)
            wait_for_enter_or_finish(t)
            continue

        # Handle pending confirmation (delete operations)
        if pending_action:
            if is_confirmation(prompt):
                action_type = pending_action.get("type")
                result = None

                if action_type == "delete_range":
                    from src.calendar_handler import delete_events_for_range
                    result = delete_events_for_range(
                        pending_action["start"],
                        pending_action["end"]
                    )
                elif action_type == "delete_reminders":
                    from src.reminder_handler import execute_delete_reminders
                    result = execute_delete_reminders(
                        pending_action["title"],
                        pending_action.get("list_name", "Reminders")
                    )
                elif action_type == "delete_reminders_date":
                    from src.reminder_handler import execute_delete_reminders_for_date
                    result = execute_delete_reminders_for_date(pending_action["date"])

                pending_action = None
                if result:
                    print(f"NOVA: {result}")
                    t = speak_interruptible(result)
                    wait_for_enter_or_finish(t)
            else:
                pending_action = None
                response = "Cancelled."
                print(f"NOVA: {response}")
                t = speak_interruptible(response)
                wait_for_enter_or_finish(t)
            continue

        # Handle pending missing info (date/time collection)
        if pending_info:
            if any(w in prompt_lower for w in ["no", "cancel", "stop", "nevermind", "never mind", "abort"]):
                pending_info = None
                response = "Cancelled."
                print(f"NOVA: {response}")
                t = speak_interruptible(response)
                wait_for_enter_or_finish(t)
                continue
            result, follow_up = handle_missing_info(pending_info, prompt, prompt_lower)

        # Handle pending missing info (date/time collection)
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
        response, pending_action, pending_info = handle_result(
            result, pending_action, pending_info, session_id
        )

        print(f"NOVA: {response}")
        t = speak_interruptible(response)
        interrupted = wait_for_enter_or_finish(t)

        # If interrupted, immediately listen for next command
        if interrupted:
            print("Listening...")
            prompt = listen()
            if not prompt:
                continue
            print(f"You: {prompt}")
            result = route(prompt, session_id, system_prompt=SYSTEM_PROMPT)
            response, pending_action, pending_info = handle_result(
                result, pending_action, pending_info, session_id
            )
            print(f"NOVA: {response}")
            t = speak_interruptible(response)
            wait_for_enter_or_finish(t)


if __name__ == "__main__":
    run()