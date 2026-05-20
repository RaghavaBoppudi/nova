import subprocess
from datetime import datetime

DEFAULT_LIST = "Reminders"


def run_applescript(script: str) -> str:
    """Run an AppleScript and return stdout, stripped."""
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True,
        timeout=15
    )
    return result.stdout.strip()


def resolve_time_of_day(phrase: str) -> str | None:
    """
    Convert vague time-of-day phrases to HH:MM.
    Returns None if the phrase requires asking for a specific time.
    """
    phrase = phrase.lower()
    if "tonight" in phrase or "this evening" in phrase:
        return None
    if "this morning" in phrase:
        return "09:00"
    if "this afternoon" in phrase:
        return "14:00"
    if "noon" in phrase or "midday" in phrase:
        return "12:00"
    if "midnight" in phrase:
        return "00:00"
    return None


def get_reminders(list_name: str = DEFAULT_LIST) -> str:
    """Return all incomplete reminders in a list."""
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
    return result if result else f"No reminders found in {list_name}."


def get_reminders_for_date(date_str: str, list_name: str = DEFAULT_LIST) -> str:
    """Return all incomplete reminders due on a specific date (YYYY-MM-DD)."""
    apple_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %d, %Y")
    script = f'''tell application "Reminders"
    set output to ""
    tell list "{list_name}"
        repeat with r in (every reminder whose completed is false)
            set dDate to due date of r
            if dDate is not missing value then
                if short date string of dDate is short date string of date "{apple_date}" then
                    set output to output & (name of r) & ", "
                end if
            end if
        end repeat
    end tell
    return output
end tell'''
    result = run_applescript(script)
    return result if result else f"No reminders found for {apple_date}."


def find_matching_reminders(title: str, list_name: str = DEFAULT_LIST) -> list:
    """Return names of all incomplete reminders matching title (case-insensitive substring)."""
    script = f'''tell application "Reminders"
    set output to ""
    tell list "{list_name}"
        repeat with r in (every reminder whose completed is false)
            set rName to name of r
            if rName contains "{title}" or "{title}" contains rName then
                set output to output & rName & "|"
            end if
        end repeat
    end tell
    return output
end tell'''
    result = run_applescript(script)
    return [r for r in result.split("|") if r.strip()] if result else []


def create_reminder(title: str, due_date_str: str = None, due_time_str: str = None, list_name: str = DEFAULT_LIST) -> str:
    """
    Create a new reminder.
    due_date_str: YYYY-MM-DD or None
    due_time_str: HH:MM or None
    """
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
        apple_date = datetime.strptime(due_date_str, "%Y-%m-%d").strftime("%B %d, %Y")
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


def complete_reminder(title: str, list_name: str = DEFAULT_LIST) -> str:
    """Mark the first reminder matching title as complete."""
    script = f'''tell application "Reminders"
    tell list "{list_name}"
        repeat with r in every reminder
            set rName to name of r
            if rName contains "{title}" or "{title}" contains rName then
                set completed of r to true
                return "Completed: " & rName
            end if
        end repeat
    end tell
end tell
return "Reminder not found: {title}"'''
    return run_applescript(script)


def delete_single_reminder(title: str, list_name: str = DEFAULT_LIST) -> bool:
    """Delete the first reminder matching title. Returns True if deleted."""
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
            return "deleted"
        end if
    end tell
end tell
return "not found"'''
    return run_applescript(script) == "deleted"


def delete_reminder(title: str, list_name: str = DEFAULT_LIST) -> str:
    """Delete all reminders matching title."""
    deleted = 0
    while delete_single_reminder(title, list_name):
        deleted += 1

    if deleted == 0:
        return f"Reminder not found: {title}"
    if deleted == 1:
        return f"Deleted: {title}"
    return f"Deleted {deleted} reminders named {title}"


def delete_reminders_with_confirmation(title: str, requested_count: int = None, list_name: str = DEFAULT_LIST) -> dict | str:
    """
    Find matching reminders and return a confirmation dict.
    If requested_count doesn't match found count, the message explains the discrepancy.
    """
    matches = find_matching_reminders(title, list_name)

    if not matches:
        return f"No reminders found matching '{title}'."

    count = len(matches)
    names = ", ".join(matches)

    if requested_count is not None and count != requested_count:
        msg = (
            f"I only found one reminder called {matches[0]}. Delete it?"
            if count == 1
            else f"I found {count} reminders: {names}. Delete all of them?"
        )
    else:
        msg = f"I found {count} reminder{'s' if count > 1 else ''}: {names}. Delete {'all of them' if count > 1 else 'it'}?"

    return {
        "requires_confirmation": True,
        "type": "delete_reminders",
        "title": title,
        "list_name": list_name,
        "message": msg
    }


def execute_delete_reminders(title: str, list_name: str = DEFAULT_LIST) -> str:
    """Delete all reminders matching title after confirmation."""
    deleted = 0
    while delete_single_reminder(title, list_name):
        deleted += 1

    if deleted == 0:
        return "No reminders found to delete."
    if deleted == 1:
        return f"Deleted: {title}"
    return f"Deleted {deleted} reminders."


def execute_delete_reminders_for_date(date_str: str, list_name: str = DEFAULT_LIST) -> str:
    """Delete all reminders due on a specific date after confirmation."""
    apple_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %d, %Y")
    deleted = 0

    while True:
        script = f'''tell application "Reminders"
    tell list "{list_name}"
        set targetName to ""
        repeat with r in (every reminder whose completed is false)
            set dDate to due date of r
            if dDate is not missing value then
                if short date string of dDate is short date string of date "{apple_date}" then
                    set targetName to name of r
                    exit repeat
                end if
            end if
        end repeat
        if targetName is not "" then
            delete (first reminder whose name is targetName)
            return "deleted"
        end if
    end tell
end tell
return "done"'''
        if run_applescript(script) == "deleted":
            deleted += 1
        else:
            break

    if deleted == 0:
        return "No reminders found to delete."
    return f"Deleted {deleted} reminder{'s' if deleted > 1 else ''}."