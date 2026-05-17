from simpleeval import simple_eval
import re

def extract_expression(prompt: str) -> str | None:
    """
    Extract a math expression from natural language.
    Returns the expression string or None if not found.
    """
    prompt = prompt.lower().strip()

    # Handle "X% of Y" pattern explicitly
    percent_match = re.search(r'(\d+\.?\d*)\s*%\s*of\s*(\d+\.?\d*)', prompt)
    if percent_match:
        a, b = percent_match.group(1), percent_match.group(2)
        return f"({a} / 100) * {b}"

    # Direct expression pattern
    pattern = r'[\d\s\+\-\*\/\(\)\.\%]+'
    matches = re.findall(pattern, prompt)

    if not matches:
        return None

    expression = max(matches, key=len).strip()
    return expression if expression else None


def calculate(prompt: str) -> str | None:
    """
    Attempt to calculate a math expression from a natural language prompt.
    Returns result string if successful, None if not a math query.
    """
    expression = extract_expression(prompt)

    if not expression:
        return None

    try:
        result = simple_eval(expression)
        # Clean up floating point where unnecessary
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        return f"The answer is {result}"
    except:
        return None


if __name__ == "__main__":
    tests = [
        "what is 2 + 2",
        "calculate 10 * 5",
        "what is 15% of 200",
        "how much is 100 / 4",
        "what is (10 + 5) * 2",
        "what is the capital of France"
    ]

    for t in tests:
        print(f"Input: {t}")
        print(f"Output: {calculate(t)}")
        print()
