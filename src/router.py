from src.math_handler import calculate
from src.calendar_handler import get_events_for_date, get_events_for_range, create_event, move_event, delete_events_for_range
from src.llm import ask
from src.memory import init_db, create_session, save_message, get_session_messages
from src.semantic_memory import store_memory, search_memory
from datetime import datetime
import re

init_db()


def classify_and_handle(prompt: str) -> str | dict | None:
    import json
    from src.calendar_handler import parse_date
    from datetime import timedelta

    classification_prompt = f"""Classify this user command and extract data. Respond in JSON only.

Command: "{prompt}"

Return exactly this JSON:
{{
    "is_calendar": true or false,
    "is_math": true or false,
    "expression": "math expression using numbers and operators only, or null",
    "intent": "get" or "get_range" or "create" or "move" or "delete_range" or "unknown",
    "title": "event title or null",
    "date": "natural language date string exactly as spoken, or null",
    "end_date": "natural language end date or null",
    "time": "HH:MM 24hr format or null",
    "duration_minutes": number or 60
}}

Rules:
- is_math is true for any calculation, arithmetic, percentage, unit conversion
- is_calendar is true only for scheduling, events, meetings, appointments
- A question is either math OR calendar, never both
- For is_math, put the expression in "expression" as numbers and operators only e.g. "25*25" or "(15/100)*200"
- "What date will it be in X weeks/days/months" is NOT calendar - it is a date calculation, set is_calendar false
- "What is today's date" or "what day is it" are NOT calendar and NOT math
- For create intent: extract title from command
- For date field: copy the date phrase exactly as spoken e.g. "this Sunday", "next Friday", "tomorrow"
- "I want to be free" or "clear my schedule" or "delete events" means delete_range
- For queries about a date range or week or weekend: use get_range"""

    response = ask(classification_prompt, [], system_prompt="You are a JSON classifier. Return only valid JSON. No explanation.")

    try:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if not json_match:
            return None
        clean = json_match.group(0)
        data = json.loads(clean)

        prompt_lower = prompt.lower()
        if "tomorrow" in prompt_lower and data.get("date", "").lower() != "tomorrow":
            data["date"] = "tomorrow"

    except Exception as e:
        print(f"DEBUG classify failed: {repr(response)}")
        return None

    if data.get("is_math"):
        expression = data.get("expression") or prompt
        result = calculate(expression)
        if result:
            return result
        return ask(prompt, [], system_prompt="Answer this math question in one short sentence. Numbers only, no explanation.")

    if not data.get("is_calendar"):
        return None

    intent = data.get("intent", "get")

    def resolve_date(date_raw: str) -> str:
        if not date_raw or date_raw.lower() in ["null", "none", ""]:
            return datetime.now().strftime("%Y-%m-%d")
        if date_raw.lower() == "today":
            return datetime.now().strftime("%Y-%m-%d")
        if date_raw.lower() == "tomorrow":
            return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        parsed = parse_date(date_raw)
        return parsed if parsed else datetime.now().strftime("%Y-%m-%d")

    if intent == "get":
        date_str = data.get("date")
        if not date_str or date_str.lower() in ["today", "null", None]:
            return get_events_for_date()
        return get_events_for_date(resolve_date(date_str))

    if intent == "get_range":
        prompt_lower = prompt.lower()
        if "this week" in prompt_lower:
            today = datetime.now()
            start_str = today.strftime("%Y-%m-%d")
            end_str = (today + timedelta(days=(6 - today.weekday()))).strftime("%Y-%m-%d")
        elif "this weekend" in prompt_lower:
            today = datetime.now()
            days_to_saturday = (5 - today.weekday()) % 7
            saturday = today + timedelta(days=days_to_saturday)
            end_str = (saturday + timedelta(days=1)).strftime("%Y-%m-%d")
            start_str = saturday.strftime("%Y-%m-%d")
        else:
            start_str = resolve_date(data.get("date") or "today")
            end_str = resolve_date(data.get("end_date") or data.get("date") or "today")
        return get_events_for_range(start_str, end_str)

    if intent == "create":
        title = data.get("title") or "New Event"
        time_str = data.get("time") or "09:00"
        duration = data.get("duration_minutes") or 60
        date_raw = data.get("date") or "today"
        date_str = resolve_date(date_raw)
        return create_event(title, date_str, time_str, duration)

    if intent == "move":
        title = data.get("title") or ""
        date_raw = data.get("date") or "today"
        time_str = data.get("time") or "09:00"
        date_str = resolve_date(date_raw)
        return move_event(title, date_str, time_str)

    if intent == "delete_range":
        prompt_lower = prompt.lower()
        if "this week" in prompt_lower:
            today = datetime.now()
            start_str = today.strftime("%Y-%m-%d")
            end_str = (today + timedelta(days=(6 - today.weekday()))).strftime("%Y-%m-%d")
        elif "this weekend" in prompt_lower:
            today = datetime.now()
            days_to_saturday = (5 - today.weekday()) % 7
            saturday = today + timedelta(days=days_to_saturday)
            end_str = (saturday + timedelta(days=1)).strftime("%Y-%m-%d")
            start_str = saturday.strftime("%Y-%m-%d")
        else:
            start_str = resolve_date(data.get("date") or "today")
            end_str = resolve_date(data.get("end_date") or data.get("date") or "today")

        events = get_events_for_range(start_str, end_str)
        if events == "No events found for that period":
            return "No events found to delete."

        return {
            "requires_confirmation": True,
            "type": "delete_range",
            "start": start_str,
            "end": end_str,
            "message": f"I found: {events} Delete all of them?"
        }

    return None


def route(prompt: str, session_id: int, system_prompt: str = "") -> str | dict:
    save_message(session_id, "user", prompt)
    store_memory("user", prompt, session_id)

    prompt_lower = prompt.lower()

    # Handle date/time queries directly
    if any(k in prompt_lower for k in ["what day is it", "what's today", "what is today", "today's date", "what date is it", "current date", "what time is it"]):
        response = datetime.now().strftime("Today is %A, %B %d, %Y.")
        save_message(session_id, "assistant", response)
        store_memory("assistant", response, session_id)
        return response

    # Handle date calculation queries directly
    date_calc_patterns = [
        r'what date.*(\d+)\s*(week|day|month|year)',
        r'(\d+)\s*(week|day|month|year)s?\s*from\s*(now|today)',
        r'what day.*\d{1,2}.*\d{4}',
        r'which day.*\d{1,2}.*\d{4}',
        r'what day of the week',
    ]

    if any(re.search(p, prompt_lower) for p in date_calc_patterns):
        from datetime import timedelta

        # Handle "X weeks/days/months from now"
        match = re.search(r'(\d+)\s*(week|day|month|year)s?\s*from\s*(now|today)', prompt_lower)
        if match:
            amount = int(match.group(1))
            unit = match.group(2)
            if unit == "week":
                target = datetime.now() + timedelta(weeks=amount)
            elif unit == "day":
                target = datetime.now() + timedelta(days=amount)
            elif unit == "month":
                from dateutil.relativedelta import relativedelta
                target = datetime.now() + relativedelta(months=amount)
            elif unit == "year":
                from dateutil.relativedelta import relativedelta
                target = datetime.now() + relativedelta(years=amount)
            response = target.strftime("That will be %A, %B %d, %Y.")
            save_message(session_id, "assistant", response)
            store_memory("assistant", response, session_id)
            return response

        # Handle "what day is [specific date]"
        from src.calendar_handler import parse_date
        date_match = re.search(r'([A-Za-z]+ \d{1,2},?\s*\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', prompt)
        if date_match:
            date_str = date_match.group(1)
            parsed = parse_date(date_str)
            if parsed:
                dt = datetime.strptime(parsed, "%Y-%m-%d")
                response = dt.strftime("%B %d, %Y is a %A.")
                save_message(session_id, "assistant", response)
                store_memory("assistant", response, session_id)
                return response

        # Fallback to LLM for complex date questions
        response = ask(prompt, [], system_prompt="Answer in one sentence. Give only the day of the week and date.")
        save_message(session_id, "assistant", response)
        store_memory("assistant", response, session_id)
        return response

    result = classify_and_handle(prompt)
    if result is not None:
        if isinstance(result, dict):
            return result
        save_message(session_id, "assistant", result)
        store_memory("assistant", result, session_id)
        return result

    past_reference_keywords = ["remember", "last time", "before", "earlier", "previously", "i told you", "i said"]
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