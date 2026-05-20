from simpleeval import simple_eval
import re


def extract_expression(prompt: str) -> str | None:
    """
    Extract a math expression from natural language.
    Returns a evaluable expression string, or None if not found.
    """
    prompt = prompt.lower().strip()

    # Handle "X% of Y" explicitly
    percent_match = re.search(r'(\d+\.?\d*)\s*%\s*of\s*(\d+\.?\d*)', prompt)
    if percent_match:
        a, b = percent_match.group(1), percent_match.group(2)
        return f"({a} / 100) * {b}"

    # Extract longest numeric/operator sequence
    matches = re.findall(r'[\d\s\+\-\*\/\(\)\.\%]+', prompt)
    if not matches:
        return None

    expression = max(matches, key=len).strip()
    return expression or None


def calculate(prompt: str) -> str | None:
    """
    Calculate a math expression from natural language.
    Returns a formatted result string, or None if the prompt is not a math query.
    """
    expression = extract_expression(prompt)
    if not expression:
        return None

    try:
        result = simple_eval(expression)
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        return f"The answer is {result}"
    except Exception:
        return None