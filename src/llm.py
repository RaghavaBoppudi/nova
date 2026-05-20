import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

# Backend selection — set NOVA_BACKEND=local to use Ollama instead
BACKEND = os.getenv("NOVA_BACKEND", "groq")
GROQ_MODEL = os.getenv("NOVA_MODEL", "llama-3.3-70b-versatile")
OLLAMA_MODEL = os.getenv("NOVA_OLLAMA_MODEL", "gemma3:4b")

# Groq client — reads GROQ_API_KEY from environment
groq_client = Groq()


def _ask_groq(prompt: str, context: list, system_prompt: str) -> str:
    """Send a prompt to Groq and return the response."""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages += context + [{"role": "user", "content": prompt}]

    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=0.3,
        max_tokens=120
    )
    return response.choices[0].message.content


def _ask_ollama(prompt: str, context: list, system_prompt: str) -> str:
    """Send a prompt to local Ollama and return the response."""
    import json
    import subprocess

    messages = []
    if system_prompt:
        messages.append({"role": "user", "content": f"[System instructions: {system_prompt}]\n\nAcknowledge these instructions briefly."})
        messages.append({"role": "assistant", "content": "Understood."})
    messages += context + [{"role": "user", "content": prompt}]

    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 120}
    })

    result = subprocess.run(
        ["curl", "-s", "-X", "POST", "http://localhost:11434/api/chat",
         "-H", "Content-Type: application/json", "-d", payload],
        capture_output=True, text=True
    )

    if result.returncode != 0 or not result.stdout:
        return "I'm having trouble connecting to the language model. Is Ollama running?"

    try:
        return json.loads(result.stdout)["message"]["content"]
    except (json.JSONDecodeError, KeyError):
        return "I received an unexpected response from the language model."


def ask(prompt: str, context: list = [], system_prompt: str = "") -> str:
    """
    Send a prompt to the configured LLM backend and return the response.

    Args:
        prompt: The user message
        context: Previous {"role": ..., "content": ...} message dicts
        system_prompt: Optional system instruction

    Returns:
        The model's response as a string
    """
    try:
        if BACKEND == "groq":
            return _ask_groq(prompt, context, system_prompt)
        return _ask_ollama(prompt, context, system_prompt)
    except Exception as e:
        return f"I encountered an error: {repr(e)}"


if __name__ == "__main__":
    print(ask("respond in one sentence: what is the capital of France"))