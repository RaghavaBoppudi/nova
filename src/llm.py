import subprocess
import json


def ask(prompt: str, context: list = [], system_prompt: str = "") -> str:
    """
    Send a prompt to the local Ollama LLM and return the response.
    context: list of previous {"role": "user"/"assistant", "content": "..."} dicts
    """
    messages = context + [{"role": "user", "content": prompt}]

    payload = json.dumps({
        "model": "gemma3:4b",
        "messages": messages,
        "stream": False,
        "system": system_prompt,
        "options": {
            "temperature": 0.3,
        }
    })

    result = subprocess.run(
        ["curl", "-s", "-X", "POST", "http://localhost:11434/api/chat",
         "-H", "Content-Type: application/json",
         "-d", payload],
        capture_output=True, text=True
    )

    response = json.loads(result.stdout)
    return response["message"]["content"]


if __name__ == "__main__":
    print(ask("respond in one sentence: what is the capital of France"))
