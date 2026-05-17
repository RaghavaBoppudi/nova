import subprocess
import json

def ask(prompt: str, context: list = []) -> str:
    """
    Send a prompt to the local Ollama LLM and return the response.
    context: list of previous {"role": "user"/"assistant", "content": "..."} dicts
    """
    messages = context + [{"role": "user", "content": prompt}]
    
    payload = json.dumps({
        "model": "llama3.1:8b",
        "messages": messages,
        "stream": False
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
