from src.llm import ask


def test_single_turn():
    response = ask("what is 10 plus 5? one sentence only")
    print(f"Single turn: {response}")


def test_multi_turn():
    context = []

    r1 = ask("my name is Raghav. one sentence acknowledgement only.", context)
    print(f"Turn 1: {r1}")
    context.append(
        {"role": "user", "content": "my name is Raghav. one sentence acknowledgement only."})
    context.append({"role": "assistant", "content": r1})

    r2 = ask("what is my name?", context)
    print(f"Turn 2: {r2}")


if __name__ == "__main__":
    test_single_turn()
    test_multi_turn()
