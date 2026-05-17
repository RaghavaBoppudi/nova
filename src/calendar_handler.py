import dateparser
import subprocess
from datetime import datetime

LOCAL_CALENDARS = ["Home", "Work"]


def run_applescript(script: str) -> str:
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True,
        timeout=15
    )
    return result.stdout.strip()


def format_date_naturally(date_str: str) -> str:
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    today = datetime.now().date()
    delta = (dt.date() - today).days

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


def parse_date(date_string: str) -> str | None:
    import re
    from datetime import timedelta

    weekdays = ['monday', 'tuesday', 'wednesday',
                'thursday', 'friday', 'saturday', 'sunday']

    # Handle "next [weekday]"
    match = re.search(r'next\s+([a-z]+)', date_string.lower())
    if match:
        day_name = match.group(1).strip()
        if day_name in weekdays:
            target = weekdays.index(day_name)
            today = datetime.now().weekday()
            days_ahead = (target - today + 7) % 7
            if days_ahead <= 1:
                days_ahead += 7
            result = datetime.now() + timedelta(days=days_ahead)
            return result.strftime("%Y-%m-%d")

    # Handle "this [weekday]"
    match = re.search(r'this\s+([a-z]+)', date_string.lower())
    if match:
        day_name = match.group(1).strip()
        if day_name in weekdays:
            target = weekdays.index(day_name)
            today = datetime.now().weekday()
            days_ahead = (target - today + 7) % 7
            if days_ahead == 0:
                days_ahead = 7
            result = datetime.now() + timedelta(days=days_ahead)
            return result.strftime("%Y-%m-%d")

    parsed = dateparser.parse(date_string, settings={
        'PREFER_DATES_FROM': 'future',
        'RETURN_AS_TIMEZONE_AWARE': False,
        'DATE_ORDER': 'MDY',
        'PREFER_DAY_OF_MONTH': 'first',
    }, languages=['en'])
    if parsed is None:
        return None
    return parsed.strftime("%Y-%m-%d")


def get_events_for_date(date_str: str = None) -> str:
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
        natural = format_date_naturally(date_str)
        return f"No events found for {natural}"
    return " ".join(results)


def get_events_for_range(start_date_str: str, end_date_str: str) -> str:
    start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date_str, "%Y-%m-%d")
    apple_start = start_dt.strftime("%B %d, %Y")
    apple_end = end_dt.strftime("%B %d, %Y")

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

    if not results:
        return "No events found for that period"
    return " ".join(results)


def create_event(title: str, date_str: str, time_str: str, duration_minutes: int = 60, calendar_name: str = "Home") -> str:
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
    start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date_str, "%Y-%m-%d")
    apple_start = start_dt.strftime("%B %d, %Y")
    apple_end = end_dt.strftime("%B %d, %Y")

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
        except:
            pass

    if total_deleted == 0:
        return "No events found to delete."
    return f"Deleted {total_deleted} event{'s' if total_deleted != 1 else ''}."


if __name__ == "__main__":
    print("Today's events:")
    print(get_events_for_date())