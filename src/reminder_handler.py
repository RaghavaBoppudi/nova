import subprocess
from datetime import datetime


def run_applescript(script: str) -> str:
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True,
        timeout=15
    )
    return result.stdout.strip()


def resolve_time_of_day(phrase: str) -> str | None:
    """Convert vague time phrases to HH:MM."""
    phrase = phrase.lower()
    if "tonight" in phrase or "this evening" in phrase:
        return None  # Ask for specific time
    if "this morning" in phrase:
        return "09:00"
    if "this afternoon" in phrase:
        return "14:00"
    if "noon" in phrase or "midday" in phrase:
        return "12:00"
    if "midnight" in phrase:
        return "00:00"
    return None


def get_reminders(list_name: str = "Reminders") -> str:
    script = f'''tell application "Reminders"
    set output to ""
    tell list "{list_name}"
        repeat with r in (every reminder whose completed is false)
            set output to output & (name of r) & ", "
        end repeat
    end tell
    return output
end tell'''
    result = run_applescript(script)
    if not result:
        return f"No reminders found in {list_name}."
    return result


def create_reminder(title: str, due_date_str: str = None, due_time_str: str = None, list_name: str = "Reminders") -> str:
    if due_date_str and due_time_str:
        dt = datetime.strptime(f"{due_date_str} {due_time_str}", "%Y-%m-%d %H:%M")
        apple_datetime = dt.strftime("%B %d, %Y %I:%M:%S %p")
        script = f'''tell application "Reminders"
    tell list "{list_name}"
        set dueDate to date "{apple_datetime}"
        make new reminder with properties {{name:"{title}", due date:dueDate}}
    end tell
end tell
return "Reminder created: {title}"'''
    elif due_date_str:
        dt = datetime.strptime(due_date_str, "%Y-%m-%d")
        apple_date = dt.strftime("%B %d, %Y")
        script = f'''tell application "Reminders"
    tell list "{list_name}"
        set dueDate to date "{apple_date}"
        make new reminder with properties {{name:"{title}", due date:dueDate}}
    end tell
end tell
return "Reminder created: {title}"'''
    else:
        script = f'''tell application "Reminders"
    tell list "{list_name}"
        make new reminder with properties {{name:"{title}"}}
    end tell
end tell
return "Reminder created: {title}"'''
    return run_applescript(script)


def complete_reminder(title: str, list_name: str = "Reminders") -> str:
    script = f'''tell application "Reminders"
    tell list "{list_name}"
        repeat with r in every reminder
            set rName to name of r
            set searchTitle to "{title}"
            if rName contains searchTitle or searchTitle contains rName then
                set completed of r to true
                return "Completed: " & rName
            end if
        end repeat
    end tell
end tell
return "Reminder not found: {title}"'''
    return run_applescript(script)


def delete_reminder(title: str, list_name: str = "Reminders") -> str:
    script = f'''tell application "Reminders"
    tell list "{list_name}"
        set targetName to ""
        repeat with r in every reminder
            set rName to name of r
            if rName contains "{title}" or "{title}" contains rName then
                set targetName to rName
                exit repeat
            end if
        end repeat
        if targetName is not "" then
            delete (first reminder whose name is targetName)
            return "Deleted: " & targetName
        end if
    end tell
end tell
return "Reminder not found: {title}"'''
    return run_applescript(script)


if __name__ == "__main__":
    print(create_reminder("Test reminder"))
    print(get_reminders())
    print(complete_reminder("Test reminder"))
    print(get_reminders())