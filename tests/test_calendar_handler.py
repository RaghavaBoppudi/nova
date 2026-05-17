from src.calendar_handler import create_event, get_events_for_date, move_event


def test_create_event():
    result = create_event('NOVA Calendar Test',
                          '2026-05-15', '10:00', 30, 'Home')
    assert 'created' in result.lower()
    print(f"Create: {result}")


def test_get_events():
    result = get_events_for_date('2026-05-15')
    assert 'NOVA Calendar Test' in result
    print(f"Get: {result}")


def test_move_event():
    result = move_event('NOVA Calendar Test', '2026-05-15', '14:00')
    assert 'Moved' in result
    print(f"Move: {result}")


if __name__ == "__main__":
    test_create_event()
    test_get_events()
    test_move_event()
    print("\nAll calendar tests passed.")
