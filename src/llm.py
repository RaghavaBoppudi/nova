import json
import os
import time
import subprocess
from dotenv import load_dotenv
from groq import Groq, RateLimitError, APITimeoutError, APIConnectionError, APIStatusError

load_dotenv()

BACKEND = os.getenv("NOVA_BACKEND", "groq")
GROQ_MODEL = os.getenv("NOVA_MODEL", "llama-3.3-70b-versatile")
OLLAMA_MODEL = os.getenv("NOVA_OLLAMA_MODEL", "gemma3:4b")

MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds between retries
REQUEST_TIMEOUT = 10  # seconds before giving up on a request

groq_client = Groq()


def _ask_groq(prompt: str, context: list, system_prompt: str) -> str:
    """
    Send a prompt to Groq with retry logic and timeout handling.
    Falls back to Ollama if all retries fail.
    """
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages += context + [{"role": "user", "content": prompt}]

    for attempt in range(MAX_RETRIES):
        try:
            response = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                temperature=0.3,
                max_tokens=120,
                timeout=REQUEST_TIMEOUT
            )
            content = response.choices[0].message.content

            # Check for empty or whitespace-only response
            if not content or not content.strip():
                raise ValueError("Empty response from Groq")

            from src.guardrails import check_output
            status, fallback = check_output(content)
            if status == "error":
                return fallback

            return content

        except RateLimitError:
            if attempt < MAX_RETRIES - 1:
                wait = RETRY_DELAY * (attempt + 1)
                print(f"Groq rate limit hit. Waiting {wait}s before retry {attempt + 2}/{MAX_RETRIES}...")
                time.sleep(wait)
            else:
                print("Groq rate limit exceeded. Falling back to local model.")
                return _ask_ollama(prompt, context, system_prompt)

        except APITimeoutError:
            if attempt < MAX_RETRIES - 1:
                print(f"Groq timeout. Retry {attempt + 2}/{MAX_RETRIES}...")
            else:
                print("Groq timed out. Falling back to local model.")
                return _ask_ollama(prompt, context, system_prompt)

        except APIConnectionError:
            if attempt < MAX_RETRIES - 1:
                print(f"Groq connection error. Retry {attempt + 2}/{MAX_RETRIES}...")
                time.sleep(RETRY_DELAY)
            else:
                print("Groq unreachable. Falling back to local model.")
                return _ask_ollama(prompt, context, system_prompt)

        except APIStatusError as e:
            print(f"Groq API error {e.status_code}. Falling back to local model.")
            return _ask_ollama(prompt, context, system_prompt)

        except ValueError as e:
            print(f"Groq returned invalid response: {e}. Falling back to local model.")
            return _ask_ollama(prompt, context, system_prompt)

        except Exception as e:
            print(f"Unexpected Groq error: {repr(e)}. Falling back to local model.")
            return _ask_ollama(prompt, context, system_prompt)

    return _ask_ollama(prompt, context, system_prompt)


def _ask_ollama(prompt: str, context: list, system_prompt: str) -> str:
    """Send a prompt to local Ollama. Last resort fallback."""
    messages = []
    if system_prompt:
        messages.append({
            "role": "user",
            "content": f"[System instructions: {system_prompt}]\n\nAcknowledge these instructions briefly."
        })
        messages.append({"role": "assistant", "content": "Understood."})
    messages += context + [{"role": "user", "content": prompt}]

    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 120}
    })

    try:
        result = subprocess.run(
            ["curl", "-s", "-X", "POST", "http://localhost:11434/api/chat",
             "-H", "Content-Type: application/json", "-d", payload],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0 or not result.stdout:
            return "I'm having trouble connecting to the language model right now."
        return json.loads(result.stdout)["message"]["content"]
    except subprocess.TimeoutExpired:
        return "The local model took too long to respond."
    except (json.JSONDecodeError, KeyError):
        return "I received an unexpected response from the language model."
    except Exception as e:
        return f"I encountered an error: {repr(e)}"


def ask(prompt: str, context: list = [], system_prompt: str = "") -> str:
    """
    Send a prompt to the configured LLM backend and return the response.

    Args:
        prompt: The user message
        context: Previous message dicts with role and content
        system_prompt: Optional system instruction

    Returns:
        The model's response as a string
    """
    if BACKEND == "groq":
        return _ask_groq(prompt, context, system_prompt)
    return _ask_ollama(prompt, context, system_prompt)


if __name__ == "__main__":
    print(ask("respond in one sentence: what is the capital of France"))