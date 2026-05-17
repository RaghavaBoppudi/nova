from src.math_handler import calculate
from src.calendar_handler import get_events_for_date, get_events_for_range, create_event, move_event, delete_events_for_range
from src.llm import ask
from src.memory import init_db, create_session, save_message, get_session_messages
from src.semantic_memory import store_memory, search_memory
from src.reminder_handler import get_reminders, create_reminder, complete_reminder, delete_reminder
from datetime import datetime
from src.notes_handler import get_notes, create_note, search_notes, delete_note
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
    "is_reminder": true or false,
    "is_math": true or false,
    "expression": "math expression using numbers and operators only, or null",
"intent": "get" or "get_range" or "create" or "move" or "delete_range" or "complete" or "delete" or "search" or "unknown",    "title": "event or reminder title or null",
    "date": "natural language date string exactly as spoken, or null",
    "end_date": "natural language end date or null",
    "time": "HH:MM 24hr format or null",
    "duration_minutes": number or 60,
    "is_notes": true or false
}}

Rules:
- is_math is true for any calculation, arithmetic, percentage, unit conversion
- is_reminder is true for reminders, to-do items, tasks
- is_calendar is true only for meetings, appointments, events with a specific time
- A question is either math OR calendar OR reminder, never more than one
- For is_math, put the expression in "expression" as numbers and operators only e.g. "25*25" or "(15/100)*200"
- "What date will it be in X weeks/days/months" is NOT calendar - it is a date calculation, set is_calendar false
- "What is today's date" or "what day is it" are NOT calendar and NOT math
- For create intent: extract title from command
- For date field: copy the date phrase exactly as spoken e.g. "this Sunday", "next Friday", "tomorrow"
- "I want to be free" or "clear my schedule" or "delete events" means delete_range with is_calendar true. These are NEVER reminders
- For queries about a date range or week or weekend: use get_range
- For reminder intent "complete": mark a reminder as done
- For reminder intent "delete": remove a reminder
- is_reminder is ONLY true when the user is explicitly asking NOVA to remind THEM of something
- Third-person statements like "Raman will do X" are NOT reminders
- "Remind me", "don't let me forget", "I need to remember" are reminder triggers
- is_notes is true for notes, memos, write this down, jot this down
- is_notes is ONLY true when creating, reading, searching or deleting notes"""

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
        
        # Override: free/clear = delete_range, never a reminder
        if any(k in prompt_lower for k in ["want to be free", "free up", "clear my", "no meetings"]):
            data["is_calendar"] = True
            data["is_reminder"] = False
            data["intent"] = "delete_range"
        
        # Override: "planned", "schedule", "agenda" = calendar get
        if any(k in prompt_lower for k in ["planned", "on my schedule", "on my agenda", "anything today", "anything tomorrow"]):
            data["is_calendar"] = True
            data["is_reminder"] = False
            data["is_notes"] = False
            data["intent"] = "get"

    except Exception as e:
        print(f"DEBUG classify failed: {repr(response)}")
        return None

    def resolve_date(date_raw: str) -> str:
        if not date_raw or date_raw.lower() in ["null", "none", ""]:
            return None
        if date_raw.lower() == "today":
            return datetime.now().strftime("%Y-%m-%d")
        if date_raw.lower() == "tomorrow":
            return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        parsed = parse_date(date_raw)
        return parsed if parsed else None

    # Handle math
    if data.get("is_math"):
        expression = data.get("expression") or prompt
        result = calculate(expression)
        if result:
            return result
        return ask(prompt, [], system_prompt="Answer this math question in one short sentence. Numbers only, no explanation.")

    # Handle reminders
    if data.get("is_reminder"):
        intent = data.get("intent", "get")
        title = data.get("title") or ""

        if intent == "get":
            return get_reminders()

        if intent == "create":
            date_raw = data.get("date")
            time_raw = data.get("time")

            from src.reminder_handler import resolve_time_of_day
            if date_raw:
                vague_time = resolve_time_of_day(date_raw)
                if vague_time:
                    time_raw = vague_time

            date_str = resolve_date(date_raw) if date_raw else None
            needs_date = not date_str
            needs_time = not time_raw

            if needs_date and needs_time:
                return {
                    "requires_reminder_info": True,
                    "missing": "both",
                    "title": title,
                    "message": f"When should I remind you to {title}? What date and time?"
                }
            if needs_date:
                return {
                    "requires_reminder_info": True,
                    "missing": "date",
                    "title": title,
                    "time": time_raw,
                    "message": f"What date should I remind you to {title}?"
                }
            if needs_time:
                return {
                    "requires_reminder_info": True,
                    "missing": "time",
                    "title": title,
                    "date": date_str,
                    "message": f"What time should I remind you to {title}?"
                }
            return create_reminder(title, date_str, time_raw)

        if intent == "complete":
            return complete_reminder(title)

        if intent == "delete":
            return delete_reminder(title)

        return get_reminders()

# Handle notes
    if data.get("is_notes"):
        intent = data.get("intent", "get")
        title = data.get("title") or ""

        # Force search intent if search keywords present
        if any(k in prompt.lower() for k in ["search", "find", "look for", "containing", "about"]):
            intent = "search"

        if intent == "get":
            return get_notes()

        if intent == "create":
            return create_note(title)

        if intent == "delete":
            return delete_note(title)

        if intent == "search":
            return search_notes(title) if title else get_notes()

        return get_notes()

    # Handle calendar
    if not data.get("is_calendar"):
        return None

    intent = data.get("intent", "get")

    if intent == "get":
        date_str = data.get("date")
        if not date_str or date_str.lower() in ["today", "null", None]:
            return get_events_for_date()
        resolved = resolve_date(date_str)
        return get_events_for_date(resolved) if resolved else get_events_for_date()

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
            start_str = resolve_date(data.get("date") or "today") or datetime.now().strftime("%Y-%m-%d")
            end_str = resolve_date(data.get("end_date") or data.get("date") or "today") or start_str
        return get_events_for_range(start_str, end_str)

    if intent == "create":
        title = data.get("title") or "New Event"
        time_raw = data.get("time")
        duration = data.get("duration_minutes") or 60
        date_raw = data.get("date")
        date_str = resolve_date(date_raw) if date_raw else None

        needs_date = not date_str
        needs_time = not time_raw

        if needs_date and needs_time:
            return {
                "requires_event_info": True,
                "missing": "both",
                "title": title,
                "duration": duration,
                "message": f"When should I schedule {title}? What date and time?"
            }
        if needs_date:
            return {
                "requires_event_info": True,
                "missing": "date",
                "title": title,
                "time": time_raw,
                "duration": duration,
                "message": f"What date should I schedule {title}?"
            }
        if needs_time:
            return {
                "requires_event_info": True,
                "missing": "time",
                "title": title,
                "date": date_str,
                "duration": duration,
                "message": f"What time should I schedule {title}?"
            }
        return create_event(title, date_str, time_raw, duration)

    if intent == "move":
        title = data.get("title") or ""
        date_raw = data.get("date")
        time_raw = data.get("time")
        date_str = resolve_date(date_raw) if date_raw else None

        needs_date = not date_str
        needs_time = not time_raw

        if needs_date and needs_time:
            return {
                "requires_event_info": True,
                "missing": "both",
                "title": title,
                "action": "move",
                "message": f"Where should I move {title}? What date and time?"
            }
        if needs_date:
            return {
                "requires_event_info": True,
                "missing": "date",
                "title": title,
                "time": time_raw,
                "action": "move",
                "message": f"What date should I move {title} to?"
            }
        if needs_time:
            return {
                "requires_event_info": True,
                "missing": "time",
                "title": title,
                "date": date_str,
                "action": "move",
                "message": f"What time should I move {title} to?"
            }
        return move_event(title, date_str, time_raw)

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
            start_str = resolve_date(data.get("date") or "today") or datetime.now().strftime("%Y-%m-%d")
            end_str = resolve_date(data.get("end_date") or data.get("date") or "today") or start_str

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

    if any(k in prompt_lower for k in ["what day is it", "what's today", "what is today", "today's date", "what date is it", "current date", "what time is it"]):
        response = datetime.now().strftime("Today is %A, %B %d, %Y.")
        save_message(session_id, "assistant", response)
        store_memory("assistant", response, session_id)
        return response

    date_calc_patterns = [
        r'what date.*(\d+)\s*(week|day|month|year)',
        r'(\d+)\s*(week|day|month|year)s?\s*from\s*(now|today)',
        r'what day.*\d{1,2}.*\d{4}',
        r'which day.*\d{1,2}.*\d{4}',
        r'what day of the week',
    ]

    if any(re.search(p, prompt_lower) for p in date_calc_patterns):
        from datetime import timedelta

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