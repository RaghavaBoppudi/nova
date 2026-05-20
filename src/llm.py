import json
import os
import subprocess

# Model can be overridden via environment variable
# e.g. NOVA_MODEL=llama3.1:8b python src/main.py
MODEL = os.getenv("NOVA_MODEL", "gemma3:4b")


def ask(prompt: str, context: list = [], system_prompt: str = "") -> str:
    """
    Send a prompt to the local Ollama LLM and return the response.

    Args:
        prompt: The user message to send
        context: List of previous {"role": "user"/"assistant", "content": "..."} dicts
        system_prompt: Optional system instruction to guide model behaviour

    Returns:
        The model's response as a string
    """
    messages = []

    # Gemma 3 ignores the system field in Ollama's API
    # Injecting as first message pair works reliably instead
    if system_prompt:
        messages.append({"role": "user", "content": f"[System instructions: {system_prompt}]\n\nAcknowledge these instructions briefly."})
        messages.append({"role": "assistant", "content": "Understood."})

    messages += context + [{"role": "user", "content": prompt}]

    payload = json.dumps({
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "system": system_prompt,
        "options": {
            "temperature": 0.3,
            "num_predict": 120
        }
    })

    result = subprocess.run(
        [
            "curl", "-s", "-X", "POST",
            "http://localhost:11434/api/chat",
            "-H", "Content-Type: application/json",
            "-d", payload
        ],
        capture_output=True,
        text=True
    )

    if result.returncode != 0 or not result.stdout:
        return "I'm having trouble connecting to the language model. Is Ollama running?"

    try:
        response = json.loads(result.stdout)
        return response["message"]["content"]
    except (json.JSONDecodeError, KeyError):
        return "I received an unexpected response from the language model."


if __name__ == "__main__":
    print(ask("respond in one sentence: what is the capital of France"))