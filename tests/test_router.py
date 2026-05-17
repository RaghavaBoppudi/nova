from src.router import route
from src.memory import create_session

def test_math_routing():
    session_id = create_session()
    response = route("what is 20% of 500", session_id)
    assert "100" in response
    print(f"Math: {response}")

def test_calendar_routing():
    session_id = create_session()
    response = route("what's on my calendar today", session_id)
    assert response is not None
    print(f"Calendar: {response}")

def test_llm_routing():
    session_id = create_session()
    response = route("what is the capital of Japan", session_id)
    assert "Tokyo" in response
    print(f"LLM: {response}")

def test_conversational_context():
    session_id = create_session()
    route("my favourite color is blue", session_id)
    response = route("what is my favourite color", session_id)
    assert "blue" in response.lower()
    print(f"Context: {response}")

if __name__ == "__main__":
    test_math_routing()
    test_calendar_routing()
    test_llm_routing()
    test_conversational_context()
    print("\nAll router tests passed.")