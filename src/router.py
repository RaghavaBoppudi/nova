from src.math_handler import calculate
from src.calendar_handler import get_events_for_date, create_event, move_event
from src.llm import ask
from src.memory import init_db, create_session, save_message, get_session_messages
from src.semantic_memory import store_memory, search_memory
from datetime import datetime
import re

# Initialize DB on import
init_db()

def is_calendar_query(prompt: str) -> bool:
    keywords = [
        "calendar", "schedule", "event", "meeting", "appointment",
        "today", "tomorrow", "what's on", "what is on", "move",
        "reschedule", "create event", "add event", "book"
    ]
    prompt_lower = prompt.lower()
    return any(k in prompt_lower for k in keywords)

def is_math_query(prompt: str) -> bool:
    result = calculate(prompt)
    return result is not None

def handle_calendar(prompt: str) -> str:
    prompt_lower = prompt.lower()

    # Move/reschedule
    if any(k in prompt_lower for k in ["move", "reschedule"]):
        return "I need more details to move an event. Please say: move [event name] to [date] at [time]"

    # Create event
    if any(k in prompt_lower for k in ["create", "add", "book", "schedule"]):
        return "I need more details to create an event. Please say: create [event name] on [date] at [time]"

    # Get today's events
    if "today" in prompt_lower:
        return get_events_for_date()

    # Get tomorrow's events
    if "tomorrow" in prompt_lower:
        from datetime import timedelta
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        return get_events_for_date(tomorrow)

    # Default to today
    return get_events_for_date()

def route(prompt: str, session_id: int) -> str:
    # Save user message
    save_message(session_id, "user", prompt)
    store_memory("user", prompt, session_id)

    # Math
    if is_math_query(prompt):
        response = calculate(prompt)
        save_message(session_id, "assistant", response)
        store_memory("assistant", response, session_id)
        return response

    # Calendar
    if is_calendar_query(prompt):
        response = handle_calendar(prompt)
        save_message(session_id, "assistant", response)
        store_memory("assistant", response, session_id)
        return response

    # General LLM with session context
    context = get_session_messages(session_id)
    # Also pull relevant semantic memories
    memories = search_memory(prompt, n_results=3)
    memory_context = ""
    if memories:
        memory_context = "Relevant context from past conversations:\n"
        for m in memories:
            memory_context += f"- {m['content']}\n"

    augmented_prompt = f"{memory_context}\nUser: {prompt}" if memory_context else prompt
    response = ask(augmented_prompt, context[:-1])

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