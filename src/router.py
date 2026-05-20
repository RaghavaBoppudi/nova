from src.math_handler import calculate
from src.calendar_handler import (
    get_events_for_date, get_events_for_range,
    create_event, move_event, delete_events_for_range, parse_date
)
from src.llm import ask
from src.memory import init_db, create_session, save_message, get_session_messages
from src.semantic_memory import store_memory, search_memory
from src.reminder_handler import (
    get_reminders, get_reminders_for_date, create_reminder,
    complete_reminder, delete_reminders_with_confirmation,
    execute_delete_reminders, execute_delete_reminders_for_date
)
from src.notes_handler import get_notes, create_note, search_notes, delete_note
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from src.clock_handler import get_time_in, is_midnight_in, get_time_difference
from src.unit_handler import convert
import json
import re

init_db()

# Keywords that indicate past-reference queries (trigger semantic memory search)
MEMORY_KEYWORDS = ["remember", "last time", "before", "earlier", "previously", "i told you", "i said"]

# Date calculation patterns handled directly without LLM
DATE_CALC_PATTERNS = [
    r'what date.*(\d+)\s*(week|day|month|year)',
    r'(\d+)\s*(week|day|month|year)s?\s*from\s*(now|today)',
    r'what day.*\d{1,2}.*\d{4}',
    r'which day.*\d{1,2}.*\d{4}',
    r'what day of the week',
]

# Today/current time queries handled directly without LLM
TODAY_KEYWORDS = [
    "what day is it", "what's today", "what is today", "today's date",
    "what date is it", "current date", "what time is it"
]


def _resolve_date(date_raw: str) -> str | None:
    """Resolve a natural language date string to YYYY-MM-DD, or None if unparseable."""
    if not date_raw or date_raw.lower() in ["null", "none", ""]:
        return None
    if date_raw.lower() == "today":
        return datetime.now().strftime("%Y-%m-%d")
    if date_raw.lower() == "tomorrow":
        return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    return parse_date(date_raw)


def _missing_info_response(requires_key: str, missing: str, title: str, **kwargs) -> dict:
    """Build a standardised missing-info response dict."""
    action = kwargs.get("action", "create")
    is_reminder = requires_key == "requires_reminder_info"

    verb = "remind you to" if is_reminder else ("schedule" if action == "create" else "move")

    messages = {
        "both": f"When should I {verb} {title}? What date and time?",
        "date": f"What date should I {verb} {title}?",
        "time": f"What time should I {verb} {title}?",
    }

    result = {requires_key: True, "missing": missing, "title": title, "message": messages[missing]}
    result.update(kwargs)
    return result


def _weekend_range() -> tuple[str, str]:
    """Return (saturday, sunday) as YYYY-MM-DD strings for this weekend."""
    today = datetime.now()
    days_to_saturday = (5 - today.weekday()) % 7
    saturday = today + timedelta(days=days_to_saturday)
    sunday = saturday + timedelta(days=1)
    return saturday.strftime("%Y-%m-%d"), sunday.strftime("%Y-%m-%d")


def _week_range() -> tuple[str, str]:
    """Return (today, end_of_week) as YYYY-MM-DD strings for this week."""
    today = datetime.now()
    end = today + timedelta(days=(6 - today.weekday()))
    return today.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def _apply_overrides(data: dict, prompt_lower: str) -> dict:
    """
    Apply keyword-based overrides to LLM classification data.
    These correct known misclassifications from the LLM.
    """
    # Fix tomorrow date extraction
    if "tomorrow" in prompt_lower and (data.get("date") or "").lower() != "tomorrow":
        data["date"] = "tomorrow"

    # free/clear = calendar delete_range
    if any(k in prompt_lower for k in ["want to be free", "free up", "clear my", "no meetings"]):
        data.update({"is_calendar": True, "is_reminder": False, "is_notes": False, "intent": "delete_range"})

    # planned/schedule/agenda = calendar get
    if any(k in prompt_lower for k in ["planned", "on my schedule", "on my agenda", "anything today", "anything tomorrow"]):
        data.update({"is_calendar": True, "is_reminder": False, "is_notes": False, "intent": "get"})

    # calendar search/unknown → get
    if data.get("is_calendar") and data.get("intent") in ["search", "unknown"]:
        data["intent"] = "get"

    # explicit note-taking phrases
    if any(k in prompt_lower for k in ["write a note", "make a note", "jot this down", "note to self", "note that"]):
        data.update({"is_notes": True, "is_calendar": False, "is_reminder": False, "intent": "create"})

    # delete all reminders for a date
    if any(k in prompt_lower for k in ["delete all reminders", "clear all reminders", "remove all reminders"]):
        data.update({"is_reminder": True, "is_calendar": False, "is_notes": False, "intent": "delete_range"})

    # reminder delete with no title → delete_range
    if data.get("is_reminder") and data.get("intent") == "delete" and not data.get("title"):
        data["intent"] = "delete_range"

    # "reminders" keyword in get-type query → reminder get
    if ("reminder" in prompt_lower or "reminders" in prompt_lower) and data.get("intent") in ["get", "get_range", "search", "unknown"]:
        data.update({"is_reminder": True, "is_calendar": False, "is_notes": False, "intent": "get"})

    # Override: physics/science questions are never math
    science_keywords = ["speed of", "velocity of", "distance to", "temperature of", 
                        "mass of", "weight of", "diameter of", "radius of"]
    if any(k in prompt_lower for k in science_keywords):
        data["is_math"] = False
        data["expression"] = None

    # Override: questions starting with "who", "what", "when", "where", "why", "how" 
    # that don't contain operators are never math
    question_words = ["who ", "what ", "when ", "where ", "why ", "how "]
    has_operator = any(op in prompt_lower for op in ['+', '-', '*', '/', '%', ' of '])
    if any(prompt_lower.startswith(w) for w in question_words) and not has_operator:
        data["is_math"] = False
        data["expression"] = None

    return data


def _handle_math(data: dict, prompt: str) -> str | None:
    """Handle math queries. Returns result string or None."""
    expression = data.get("expression") or prompt
    result = calculate(expression)
    if result:
        return result
    return result

def _handle_reminders(data: dict, prompt: str) -> str | dict:
    """Handle all reminder intents."""
    from src.reminder_handler import resolve_time_of_day
    intent = data.get("intent", "get")
    title = data.get("title") or ""

    if intent == "get":
        date_raw = data.get("date")
        if date_raw:
            date_str = _resolve_date(date_raw)
            if date_str:
                return get_reminders_for_date(date_str)
        return get_reminders()

    if intent == "create":
        date_raw = data.get("date")
        time_raw = data.get("time")

        if date_raw:
            vague_time = resolve_time_of_day(date_raw)
            if vague_time:
                time_raw = vague_time

        date_str = _resolve_date(date_raw) if date_raw else None

        if not date_str and not time_raw:
            return _missing_info_response("requires_reminder_info", "both", title)
        if not date_str:
            return _missing_info_response("requires_reminder_info", "date", title, time=time_raw)
        if not time_raw:
            return _missing_info_response("requires_reminder_info", "time", title, date=date_str)

        return create_reminder(title, date_str, time_raw)

    if intent == "complete":
        return complete_reminder(title)

    if intent == "delete":
        return delete_reminders_with_confirmation(title, data.get("requested_count"))

    if intent == "delete_range":
        date_str = _resolve_date(data.get("date")) or datetime.now().strftime("%Y-%m-%d")
        reminders = get_reminders_for_date(date_str)
        if "No reminders found" in reminders:
            return reminders
        return {
            "requires_confirmation": True,
            "type": "delete_reminders_date",
            "date": date_str,
            "message": f"I found: {reminders} Delete all of them?"
        }

    return get_reminders()


def _handle_notes(data: dict, prompt: str) -> str:
    """Handle all notes intents."""
    title = data.get("title") or ""
    intent = data.get("intent", "get")

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


def _handle_calendar(data: dict, prompt: str) -> str | dict | None:
    """Handle all calendar intents."""
    intent = data.get("intent", "get")
    prompt_lower = prompt.lower()

    if intent == "get":
        date_str = data.get("date")
        if not date_str or date_str.lower() in ["today", "null", None]:
            return get_events_for_date()
        resolved = _resolve_date(date_str)
        return get_events_for_date(resolved) if resolved else get_events_for_date()

    if intent == "get_range":
        if "this week" in prompt_lower:
            start_str, end_str = _week_range()
        elif "this weekend" in prompt_lower:
            start_str, end_str = _weekend_range()
        else:
            start_str = _resolve_date(data.get("date") or "today") or datetime.now().strftime("%Y-%m-%d")
            end_str = _resolve_date(data.get("end_date") or data.get("date") or "today") or start_str
        return get_events_for_range(start_str, end_str)

    if intent == "create":
        title = data.get("title") or "New Event"
        time_raw = data.get("time")
        duration = data.get("duration_minutes") or 60
        date_str = _resolve_date(data.get("date")) if data.get("date") else None

        if not date_str and not time_raw:
            return _missing_info_response("requires_event_info", "both", title, duration=duration)
        if not date_str:
            return _missing_info_response("requires_event_info", "date", title, time=time_raw, duration=duration)
        if not time_raw:
            return _missing_info_response("requires_event_info", "time", title, date=date_str, duration=duration)
        return create_event(title, date_str, time_raw, duration)

    if intent == "move":
        title = data.get("title") or ""
        time_raw = data.get("time")
        date_str = _resolve_date(data.get("date")) if data.get("date") else None

        if not date_str and not time_raw:
            return _missing_info_response("requires_event_info", "both", title, action="move")
        if not date_str:
            return _missing_info_response("requires_event_info", "date", title, time=time_raw, action="move")
        if not time_raw:
            return _missing_info_response("requires_event_info", "time", title, date=date_str, action="move")
        return move_event(title, date_str, time_raw)

    if intent == "delete_range":
        requested_count = data.get("requested_count")

        if "this week" in prompt_lower:
            start_str, end_str = _week_range()
        elif "this weekend" in prompt_lower:
            start_str, end_str = _weekend_range()
        else:
            start_str = _resolve_date(data.get("date") or "today") or datetime.now().strftime("%Y-%m-%d")
            end_str = _resolve_date(data.get("end_date") or data.get("date") or "today") or start_str

        events = get_events_for_range(start_str, end_str)
        if events == "No events found for that period":
            return "No events found to delete."

        event_list = [e.strip() for e in events.split(",") if e.strip()]
        count = len(event_list)

        if requested_count is not None and count != requested_count:
            msg = (
                f"I only found one event: {events} Delete it?"
                if count == 1
                else f"I found {count} events: {events} Delete all of them?"
            )
        else:
            msg = f"I found {count} event{'s' if count > 1 else ''}: {events} Delete {'all of them' if count > 1 else 'it'}?"

        return {
            "requires_confirmation": True,
            "type": "delete_range",
            "start": start_str,
            "end": end_str,
            "message": msg
        }

    return None



def classify_and_handle(prompt: str) -> str | dict | None:
    """
    Classify a prompt using the LLM and route to the appropriate handler.
    Returns a response string, a dict requiring further action, or None if unhandled.
    """

    # Strip leading filler words that confuse the classifier
    clean_prompt = re.sub(r'^(and|but|so|also|oh|well|hey|okay|ok|right)\s+', '', prompt, flags=re.IGNORECASE).strip()
    if not clean_prompt:
        clean_prompt = prompt
    
    # ── Classification prompt (DO NOT MODIFY) ──────────────────────────────────
    classification_prompt = f"""Classify this user command and extract data. Respond in JSON only.

Command: "{clean_prompt}"

Return exactly this JSON:
{{
    "is_calendar": true or false,
    "is_reminder": true or false,
    "is_math": true or false,
    "expression": "math expression using numbers and operators only, or null",
    "intent": "get" or "get_range" or "create" or "move" or "delete_range" or "complete" or "delete" or "search" or "unknown",
    "title": "event or reminder title or null",
    "date": "natural language date string exactly as spoken, or null",
    "end_date": "natural language end date or null",
    "time": "HH:MM 24hr format or null",
    "duration_minutes": number or 60,
    "is_notes": true or false,
    "requested_count": number or null
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
- is_notes is ONLY true when creating, reading, searching or deleting notes
- requested_count: if user says "delete both" set to 2, "delete all three" set to 3, otherwise null

Examples:
- "remind me to call mom tomorrow at 9am" → is_reminder: true, intent: create, title: "call mom", date: "tomorrow", time: "09:00"
- "what are my reminders" → is_reminder: true, intent: get
- "delete both call mom reminders" → is_reminder: true, intent: delete, title: "call mom", requested_count: 2
- "delete all reminders for tomorrow" → is_reminder: true, intent: delete_range, date: "tomorrow"
- "clear all my reminders for today" → is_reminder: true, intent: delete_range, date: "today"
- "set up a meeting on Friday at 3pm" → is_calendar: true, intent: create, title: "meeting", date: "this Friday", time: "15:00"
- "what is 15% of 200" → is_math: true, expression: "(15/100)*200"
- "create a note about the project" → is_notes: true, intent: create, title: "project"
- "delete all events this weekend" → is_calendar: true, intent: delete_range
- "what is on my calendar tomorrow" → is_calendar: true, intent: get, date: "tomorrow"
- "what's on my schedule today" → is_calendar: true, intent: get, date: "today"
- "do I have anything planned next Friday" → is_calendar: true, intent: get, date: "next Friday"
- "write a note to pick up Aadu tomorrow" → is_notes: true, intent: create, title: "pick up Aadu tomorrow"
- "jot this down" → is_notes: true, intent: create
- "make a note that" → is_notes: true, intent: create
- "note to self" → is_notes: true, intent: create
"""
    # ── End classification prompt ───────────────────────────────────────────────

    response = ask(
        classification_prompt, [],
        system_prompt="You are a JSON classifier. Return ONLY the exact JSON structure provided in the prompt. Do not create your own structure. No explanation. No markdown."
    )

    try:
        stripped = re.sub(r'```(?:json)?\s*', '', response).strip()
        json_match = re.search(r'\{.*\}', stripped, re.DOTALL)
        if not json_match:
            return None
        data = json.loads(json_match.group(0))
        data = _apply_overrides(data, prompt.lower())
    except Exception as e:
        print(f"Classification failed: {repr(e)}")
        return None

    if data.get("is_math"):
        return _handle_math(data, prompt)
    if data.get("is_reminder"):
        return _handle_reminders(data, prompt)
    if data.get("is_notes"):
        return _handle_notes(data, prompt)
    if data.get("is_calendar"):
        return _handle_calendar(data, prompt)

    return None


def _handle_date_calculation(prompt: str, prompt_lower: str) -> str | None:
    """Handle date arithmetic queries directly without LLM. Returns None if no match."""
    match = re.search(r'(\d+)\s*(week|day|month|year)s?\s*from\s*(now|today)', prompt_lower)
    if match:
        amount = int(match.group(1))
        unit = match.group(2)
        delta_map = {
            "week": timedelta(weeks=amount),
            "day": timedelta(days=amount),
            "month": relativedelta(months=amount),
            "year": relativedelta(years=amount),
        }
        target = datetime.now() + delta_map[unit]
        return target.strftime("That will be %A, %B %d, %Y.")

    date_match = re.search(r'([A-Za-z]+ \d{1,2},?\s*\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', prompt)
    if date_match:
        parsed = parse_date(date_match.group(1))
        if parsed:
            dt = datetime.strptime(parsed, "%Y-%m-%d")
            return dt.strftime("%B %d, %Y is a %A.")

    return None


def _save_and_return(session_id: int, response: str) -> str:
    """Save a response to memory and return it."""
    save_message(session_id, "assistant", response)
    store_memory("assistant", response, session_id)
    return response


def route(prompt: str, session_id: int, system_prompt: str = "") -> str | dict:
    """
    Main routing function. Classifies the prompt and returns a response
    or a dict requiring confirmation/additional info.
    """
    save_message(session_id, "user", prompt)
    store_memory("user", prompt, session_id)

    prompt_lower = prompt.lower()


    # Handle world clock queries directly
    clock_patterns = [
        r'what\s+(time|day)\s+is\s+it\s+in\s+(.+)',
        r'what\s+time\s+is\s+it\s+in\s+(.+)',
        r'is\s+it\s+midnight\s+in\s+(.+)',
        r'time\s+in\s+(.+)',
        r'(time\s+difference|how\s+many\s+hours).*(between|and)\s+(.+)\s+and\s+(.+)',
    ]

    for pattern in clock_patterns:
        match = re.search(pattern, prompt_lower)
        if match:
            if 'midnight' in prompt_lower:
                location = re.sub(r'.*(midnight\s+in\s+)', '', prompt_lower).strip()
                return _save_and_return(session_id, is_midnight_in(location))
            elif 'difference' in prompt_lower or 'how many hours' in prompt_lower:
                parts = re.split(r'\s+and\s+|\s+between\s+', prompt_lower)
                if len(parts) >= 2:
                    loc1 = parts[-2].strip()
                    loc2 = parts[-1].strip()
                    return _save_and_return(session_id, get_time_difference(loc1, loc2))
            else:
                location = re.sub(r'.*(time\s+is\s+it\s+in\s+|time\s+in\s+|day\s+is\s+it\s+in\s+)', '', prompt_lower).strip()
                location = re.sub(r'\?$', '', location).strip()
                return _save_and_return(session_id, get_time_in(location))

    # Handle unit conversions directly
    unit_pattern = re.search(
        r'convert\s+([\d.]+)\s+(\w[\w\s]*?)\s+to\s+(\w[\w\s]*?)$|'
        r'how\s+many\s+(\w[\w\s]*?)\s+in\s+([\d.]+)\s+(\w[\w\s]*?)$|'
        r'([\d.]+)\s+(\w[\w\s]*?)\s+in\s+(\w[\w\s]*?)$|'
        r'what\s+is\s+([\d.]+)\s+(\w[\w\s]*?)\s+in\s+(\w[\w\s]*?)$',
        prompt_lower
    )
    if unit_pattern:
        groups = unit_pattern.groups()
        # Pattern 1: "convert X unit to unit"
        if groups[0]:
            value, from_unit, to_unit = float(groups[0]), groups[1].strip(), groups[2].strip()
        # Pattern 2: "how many X in Y unit"
        elif groups[3]:
            to_unit, value, from_unit = groups[3].strip(), float(groups[4]), groups[5].strip()
        # Pattern 3: "X unit in unit"
        elif groups[6]:
            value, from_unit, to_unit = float(groups[6]), groups[7].strip(), groups[8].strip()
        # Pattern 4: "what is X unit in unit"
        elif groups[9]:
            value, from_unit, to_unit = float(groups[9]), groups[10].strip(), groups[11].strip()
        else:
            value, from_unit, to_unit = None, None, None

        if value is not None:
            result = convert(value, from_unit, to_unit)
            return _save_and_return(session_id, result)
            
    # Handle current date/time directly
    if any(k in prompt_lower for k in TODAY_KEYWORDS) and "tomorrow" not in prompt_lower and "yesterday" not in prompt_lower:
        return _save_and_return(session_id, datetime.now().strftime("Today is %A, %B %d, %Y."))

    # Handle date calculations directly
    if any(re.search(p, prompt_lower) for p in DATE_CALC_PATTERNS):
        result = _handle_date_calculation(prompt, prompt_lower)
        if result:
            return _save_and_return(session_id, result)
        # Fallback to LLM for complex date questions
        result = ask(prompt, [], system_prompt="Answer in one sentence. Give only the day of the week and date.")
        return _save_and_return(session_id, result)

    # Try classification routing
    result = classify_and_handle(prompt)
    if result is not None:
        if isinstance(result, dict):
            return result
        return _save_and_return(session_id, result)

    # General LLM with optional semantic memory context
    context = get_session_messages(session_id)
    augmented_prompt = prompt

    if any(k in prompt_lower for k in MEMORY_KEYWORDS):
        memories = search_memory(prompt, n_results=3)
        if memories:
            memory_context = "Relevant context from past conversations:\n" + \
                             "".join(f"- {m['content']}\n" for m in memories)
            augmented_prompt = f"{memory_context}\nUser: {prompt}"

    response = ask(augmented_prompt, context[:-1], system_prompt=system_prompt)
    return _save_and_return(session_id, response)