from src.math_handler import calculate


def test_basic_arithmetic():
    assert calculate("what is 2 + 2") == "The answer is 4"
    assert calculate("calculate 10 * 5") == "The answer is 50"
    assert calculate("how much is 100 / 4") == "The answer is 25"


def test_percentage():
    assert calculate("what is 15% of 200") == "The answer is 30"


def test_brackets():
    assert calculate("what is (10 + 5) * 2") == "The answer is 30"


def test_non_math():
    assert calculate("what is the capital of France") is None


if __name__ == "__main__":
    test_basic_arithmetic()
    test_percentage()
    test_brackets()
    test_non_math()
    print("All tests passed.")
