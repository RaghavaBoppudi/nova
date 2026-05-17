import subprocess
from datetime import datetime


def run_applescript(script: str) -> str:
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True,
        timeout=15
    )
    return result.stdout.strip()


def get_notes(folder: str = "Notes") -> str:
    script = f'''tell application "Notes"
    set output to ""
    tell folder "{folder}"
        repeat with n in every note
            set output to output & (name of n) & ", "
        end repeat
    end tell
    return output
end tell'''
    result = run_applescript(script)
    if not result:
        return f"No notes found in {folder}."
    return result


def create_note(title: str, body: str = "", folder: str = "Notes") -> str:
    safe_body = body.replace('"', '\\"')
    safe_title = title.replace('"', '\\"')
    content = safe_body if safe_body else safe_title
    script = f'''tell application "Notes"
    tell folder "{folder}"
        make new note with properties {{name:"{safe_title}", body:"{content}"}}
    end tell
end tell
return "Note created: {safe_title}"'''
    return run_applescript(script)


def search_notes(query: str, folder: str = "Notes") -> str:
    safe_query = query.replace('"', '\\"')
    script = f'''tell application "Notes"
    set output to ""
    tell folder "{folder}"
        repeat with n in every note
            if (name of n contains "{safe_query}") or (body of n contains "{safe_query}") then
                set output to output & (name of n) & ", "
            end if
        end repeat
    end tell
    return output
end tell'''
    result = run_applescript(script)
    if not result:
        return f"No notes found matching '{query}'."
    return f"Found: {result}"


def delete_note(title: str, folder: str = "Notes") -> str:
    script = f'''tell application "Notes"
    tell folder "{folder}"
        set targetName to ""
        repeat with n in every note
            if name of n contains "{title}" then
                set targetName to name of n
                exit repeat
            end if
        end repeat
        if targetName is not "" then
            delete (first note whose name is targetName)
            return "Deleted note: " & targetName
        end if
    end tell
end tell
return "Note not found: {title}"'''
    return run_applescript(script)


if __name__ == "__main__":
    print(create_note("Test Note", "This is a test note created by NOVA."))
    print(get_notes())
    print(search_notes("Test"))
    print(delete_note("Test Note"))
    print(get_notes())
