from src.memory import init_db, create_session, save_message, get_session_messages, get_recent_messages
import os


def test_session_memory():
    init_db()
    session_id = create_session()
    assert isinstance(session_id, int)
    print(f"Session created: {session_id}")


def test_save_and_retrieve():
    init_db()
    session_id = create_session()
    save_message(session_id, "user", "my name is Raghav")
    save_message(session_id, "assistant", "Nice to meet you Raghav")
    messages = get_session_messages(session_id)
    assert len(messages) == 2
    assert messages[0]["content"] == "my name is Raghav"
    assert messages[1]["role"] == "assistant"
    print(f"Messages retrieved: {messages}")


def test_cross_session_recent():
    init_db()
    recent = get_recent_messages(limit=10)
    assert isinstance(recent, list)
    print(f"Recent messages count: {len(recent)}")


if __name__ == "__main__":
    test_session_memory()
    test_save_and_retrieve()
    test_cross_session_recent()
    print("\nAll memory tests passed.")
