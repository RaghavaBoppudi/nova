import re
import dateparser
import subprocess
from datetime import datetime, timedelta

# Calendars to read from and write to
LOCAL_CALENDARS = ["Home", "Work"]

WEEKDAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']


def run_applescript(script: str) -> str:
    """Run an AppleScript and return stdout, stripped."""
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True,
        timeout=15
    )
    return result.stdout.strip()


def format_date_naturally(date_str: str) -> str:
    """Convert YYYY-MM-DD to a natural spoken phrase like 'tomorrow' or 'next Friday'."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    delta = (dt.date() - datetime.now().date()).days

    if delta == 0:
        return "today"
    elif delta == 1:
        return "tomorrow"
    elif delta == -1:
        return "yesterday"
    elif 2 <= delta <= 6:
        return f"this {dt.strftime('%A')}"
    elif 7 <= delta <= 13:
        return f"next {dt.strftime('%A')}"
    else:
        return dt.strftime("%B %d")


def _weekday_offset(day_name: str, min_days_ahead: int = 0) -> int:
    """
    Calculate days until the next occurrence of a weekday.
    min_days_ahead: minimum days ahead (1 = next occurrence must be tomorrow or later)
    """
    target = WEEKDAYS.index(day_name)
    today = datetime.now().weekday()
    days_ahead = (target - today + 7) % 7
    if days_ahead <= min_days_ahead:
        days_ahead += 7
    return days_ahead


def parse_date(date_string: str) -> str | None:
    """
    Parse a natural language date string to YYYY-MM-DD.
    Handles 'next [weekday]', 'this [weekday]', and general date phrases.
    Returns None if parsing fails.
    """
    lower = date_string.lower()

    # Handle "next [weekday]"
    match = re.search(r'next\s+([a-z]+)', lower)
    if match and match.group(1) in WEEKDAYS:
        days = _weekday_offset(match.group(1), min_days_ahead=1)
        return (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

    # Handle "this [weekday]"
    match = re.search(r'this\s+([a-z]+)', lower)
    if match and match.group(1) in WEEKDAYS:
        days = _weekday_offset(match.group(1), min_days_ahead=0)
        return (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

    # Fallback to dateparser
    parsed = dateparser.parse(date_string, settings={
        'PREFER_DATES_FROM': 'future',
        'RETURN_AS_TIMEZONE_AWARE': False,
        'DATE_ORDER': 'MDY',
        'PREFER_DAY_OF_MONTH': 'first',
    }, languages=['en'])

    return parsed.strftime("%Y-%m-%d") if parsed else None


def get_events_for_date(date_str: str = None) -> str:
    """Return all events on a given date (defaults to today)."""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    dt = datetime.strptime(date_str, "%Y-%m-%d")
    apple_date = dt.strftime("%B %d, %Y")
    results = []

    for cal_name in LOCAL_CALENDARS:
        script = f'''tell application "Calendar"
    tell calendar "{cal_name}"
        set targetDate to date "{apple_date}"
        set time of targetDate to 0
        set endDate to targetDate + 1 * days
        set eventList to ""
        repeat with e in every event
            set eStart to start date of e
            if eStart >= targetDate and eStart < endDate then
                set eventList to eventList & (summary of e) & " at " & (time string of eStart) & ", "
            end if
        end repeat
        return eventList
    end tell
end tell'''
        result = run_applescript(script)
        if result:
            results.append(result)

    if not results:
        return f"No events found for {format_date_naturally(date_str)}"
    return " ".join(results)


def get_events_for_range(start_date_str: str, end_date_str: str) -> str:
    """Return all events between two dates inclusive."""
    apple_start = datetime.strptime(start_date_str, "%Y-%m-%d").strftime("%B %d, %Y")
    apple_end = datetime.strptime(end_date_str, "%Y-%m-%d").strftime("%B %d, %Y")
    results = []

    for cal_name in LOCAL_CALENDARS:
        script = f'''tell application "Calendar"
    tell calendar "{cal_name}"
        set startDate to date "{apple_start}"
        set time of startDate to 0
        set endDate to date "{apple_end}"
        set time of endDate to 86399
        set eventList to ""
        repeat with e in every event
            set eStart to start date of e
            if eStart >= startDate and eStart <= endDate then
                set eventList to eventList & (summary of e) & " on " & (short date string of eStart) & " at " & (time string of eStart) & ", "
            end if
        end repeat
        return eventList
    end tell
end tell'''
        result = run_applescript(script)
        if result:
            results.append(result)

    return " ".join(results) if results else "No events found for that period"


def create_event(title: str, date_str: str, time_str: str, duration_minutes: int = 60, calendar_name: str = "Home") -> str:
    """Create a new calendar event."""
    dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    apple_datetime = dt.strftime("%B %d, %Y %I:%M:%S %p")
    script = f'''tell application "Calendar"
    tell calendar "{calendar_name}"
        set startDate to date "{apple_datetime}"
        set endDate to startDate + {duration_minutes} * minutes
        make new event with properties {{summary:"{title}", start date:startDate, end date:endDate}}
    end tell
end tell
return "Event created: {title}"'''
    return run_applescript(script)


def move_event(title: str, new_date_str: str, new_time_str: str) -> str:
    """Move an existing event to a new date and time, preserving duration."""
    dt = datetime.strptime(f"{new_date_str} {new_time_str}", "%Y-%m-%d %H:%M")
    apple_datetime = dt.strftime("%B %d, %Y %I:%M:%S %p")

    for cal_name in LOCAL_CALENDARS:
        script = f'''tell application "Calendar"
    tell calendar "{cal_name}"
        repeat with e in every event
            if summary of e is "{title}" then
                set dur to (end date of e) - (start date of e)
                set newStart to date "{apple_datetime}"
                set end date of e to (newStart + dur)
                set start date of e to newStart
                return "Moved: {title} to {new_date_str} at {new_time_str}"
            end if
        end repeat
    end tell
end tell
return ""'''
        result = run_applescript(script)
        if result.startswith("Moved"):
            return result

    return f"Event not found: {title}"


def delete_events_for_range(start_date_str: str, end_date_str: str) -> str:
    """Delete all events between two dates inclusive."""
    apple_start = datetime.strptime(start_date_str, "%Y-%m-%d").strftime("%B %d, %Y")
    apple_end = datetime.strptime(end_date_str, "%Y-%m-%d").strftime("%B %d, %Y")
    total_deleted = 0

    for cal_name in LOCAL_CALENDARS:
        script = f'''tell application "Calendar"
    tell calendar "{cal_name}"
        set startDate to date "{apple_start}"
        set time of startDate to 0
        set endDate to date "{apple_end}"
        set time of endDate to 86399
        set toDelete to {{}}
        repeat with e in every event
            set eStart to start date of e
            if eStart >= startDate and eStart <= endDate then
                set end of toDelete to uid of e
            end if
        end repeat
        repeat with eUID in toDelete
            set targetEvent to first event whose uid is eUID
            delete targetEvent
        end repeat
        return count of toDelete
    end tell
end tell'''
        result = run_applescript(script)
        try:
            total_deleted += int(result)
        except Exception:
            pass

    if total_deleted == 0:
        return "No events found to delete."
    return f"Deleted {total_deleted} event{'s' if total_deleted != 1 else ''}."