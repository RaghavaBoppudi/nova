from src.math_handler import calculate
from src.calendar_handler import get_events_for_date, create_event, move_event
from src.llm import ask
from src.memory import init_db, create_session, save_message, get_session_messages
from src.semantic_memory import store_memory, search_memory
from datetime import datetime

init_db()


def is_calendar_query(prompt: str) -> bool:
    import re
    keywords = [
        "calendar", "schedule", "event", "meeting", "appointment",
        "today", "tomorrow", "what's on", "what is on my",
        "move", "reschedule", "create event", "add event", "book"
    ]
    prompt_lower = prompt.lower()
    return any(k in prompt_lower for k in keywords)


def is_math_query(prompt: str) -> bool:
    import re

    prompt_lower = prompt.lower().strip()

    math_intent_starters = [
        "what is", "what's", "calculate", "compute", "how much is",
        "how many", "solve", "evaluate"
    ]

    has_math_intent = any(prompt_lower.startswith(k) for k in math_intent_starters)
    if not has_math_intent:
        return False

    # Require complete expression - number OPERATOR number
    has_operator = bool(re.search(r'\d+\.?\d*\s*[\+\-\*\/]\s*\d+\.?\d*', prompt))
    has_percent = bool(re.search(r'\d+\.?\d*\s*%\s*of\s*\d+', prompt_lower))

    if not has_operator and not has_percent:
        return False

    result = calculate(prompt)
    return result is not None


def handle_calendar(prompt: str) -> str:
    prompt_lower = prompt.lower()

    if any(k in prompt_lower for k in ["move", "reschedule"]):
        return "I need more details to move an event. Please say: move [event name] to [date] at [time]"

    if any(k in prompt_lower for k in ["create", "add", "book", "schedule"]):
        return "I need more details to create an event. Please say: create [event name] on [date] at [time]"

    if "today" in prompt_lower:
        return get_events_for_date()

    if "tomorrow" in prompt_lower:
        from datetime import timedelta
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        return get_events_for_date(tomorrow)

    return get_events_for_date()


def route(prompt: str, session_id: int, system_prompt: str = "") -> str:
    save_message(session_id, "user", prompt)
    store_memory("user", prompt, session_id)

    if is_math_query(prompt):
        response = calculate(prompt)
        save_message(session_id, "assistant", response)
        store_memory("assistant", response, session_id)
        return response

    if is_calendar_query(prompt):
        response = handle_calendar(prompt)
        save_message(session_id, "assistant", response)
        store_memory("assistant", response, session_id)
        return response

    past_reference_keywords = ["remember", "last time",
                               "before", "earlier", "previously", "i told you", "i said"]
    use_memory = any(k in prompt.lower() for k in past_reference_keywords)

    context = get_session_messages(session_id)
    augmented_prompt = prompt

    if use_memory:
        memories = search_memory(prompt, n_results=3)
        if memories:
            memory_context = "Relevant context from past conversations:\n"
            for m in memories:
                memory_context += f"- {m['content']}\n"
            augmented_prompt = f"{memory_context}\nUser: {prompt}"

    response = ask(augmented_prompt, context[:-1], system_prompt=system_prompt)
    save_message(session_id, "assistant", response)
    store_memory("assistant", response, session_id)
    return response


if __name__ == "__main__":
    session_id = create_session()
    print(f"Session: {session_id}")

    tests = [
        "what is 15% of 340",
        "what's on my calendar today",
        "what is the speed of light",
    ]

    for t in tests:
        print(f"\nYou: {t}")
        response = route(t, session_id)
        print(f"NOVA: {response}")
