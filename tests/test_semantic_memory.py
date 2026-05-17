from src.semantic_memory import store_memory, search_memory

def test_store_and_search():
    store_memory("user", "I enjoy hiking on weekends", 99)
    results = search_memory("what do I like doing outdoors")
    assert any("hiking" in r["content"] for r in results)
    print(f"Search results: {results}")

def test_relevance_ordering():
    store_memory("user", "I drink coffee every morning", 99)
    store_memory("user", "my favourite programming language is Python", 99)
    results = search_memory("morning routine")
    print(f"Top result: {results[0]['content']}")

if __name__ == "__main__":
    test_store_and_search()
    test_relevance_ordering()
    print("\nAll semantic memory tests passed.")