import chromadb
from sentence_transformers import SentenceTransformer
from datetime import datetime

CHROMA_PATH = "nova_chroma"
COLLECTION_NAME = "nova_memories"

print("Loading embedding model...")
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
print("Embedding model ready.")

client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_or_create_collection(COLLECTION_NAME)

def store_memory(role: str, content: str, session_id: int):
    embedding = embedding_model.encode(content).tolist()
    doc_id = f"{session_id}_{datetime.now().timestamp()}"
    collection.add(
        ids=[doc_id],
        embeddings=[embedding],
        documents=[content],
        metadatas=[{
            "role": role,
            "session_id": str(session_id),
            "timestamp": datetime.now().isoformat()
        }]
    )

def search_memory(query: str, n_results: int = 5) -> list:
    embedding = embedding_model.encode(query).tolist()
    results = collection.query(
        query_embeddings=[embedding],
        n_results=n_results
    )
    memories = []
    for i, doc in enumerate(results["documents"][0]):
        memories.append({
            "content": doc,
            "role": results["metadatas"][0][i]["role"],
            "timestamp": results["metadatas"][0][i]["timestamp"]
        })
    return memories

if __name__ == "__main__":
    print("Semantic memory module ready.")