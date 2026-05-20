import subprocess

DEFAULT_FOLDER = "Notes"


def run_applescript(script: str) -> str:
    """Run an AppleScript and return stdout, stripped."""
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True,
        timeout=15
    )
    return result.stdout.strip()


def get_notes(folder: str = DEFAULT_FOLDER) -> str:
    """Return names of all notes in a folder."""
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
    return result if result else f"No notes found in {folder}."


def create_note(title: str, body: str = "", folder: str = DEFAULT_FOLDER) -> str:
    """Create a new note with a title and optional body."""
    safe_title = title.replace('"', '\\"')
    safe_body = body.replace('"', '\\"')
    content = safe_body if safe_body else safe_title
    script = f'''tell application "Notes"
    tell folder "{folder}"
        make new note with properties {{name:"{safe_title}", body:"{content}"}}
    end tell
end tell
return "Note created: {safe_title}"'''
    return run_applescript(script)


def search_notes(query: str, folder: str = DEFAULT_FOLDER) -> str:
    """Search notes by title or body content. Returns matching note names."""
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
    return f"Found: {result}" if result else f"No notes found matching '{query}'."


def delete_note(title: str, folder: str = DEFAULT_FOLDER) -> str:
    """Delete the first note whose name contains title."""
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