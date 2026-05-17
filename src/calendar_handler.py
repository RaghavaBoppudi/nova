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
        return f"No events found for {date_str}"
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


if __name__ == "__main__":
    print("Today's events:")
    print(get_events_for_date())
