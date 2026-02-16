import os
import logging
import chromadb
from dotenv import load_dotenv
from fastapi import FastAPI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

load_dotenv()
MODEL_NAME = os.getenv("MODEL_NAME", "tinyllama")
HOST = os.getenv("HOST", "http://host.docker.internal:11434")
USE_MOCK_LLM = os.getenv("USE_MOCK_LLM", "0") == "1"

logging.info(f"Using model: {MODEL_NAME}")
logging.info(f"Mock mode: {USE_MOCK_LLM}")

# Only import Ollama in production mode
if not USE_MOCK_LLM:
    import ollama
    ollama_client = ollama.Client(host=HOST)

app = FastAPI()
chroma = chromadb.PersistentClient(path="./db")
collection = chroma.get_or_create_collection("docs")

@app.post("/query")
def query(q: str):
    results = collection.query(query_texts=[q], n_results=1)
    context = results["documents"][0][0] if results["documents"] else ""

    # Check if mock mode is enabled
    if USE_MOCK_LLM:
        # Return retrieved context directly (deterministic!)
        return {"answer": context}
    else:
        # Use real LLM (production mode)
        answer = ollama_client.generate(
            model=MODEL_NAME,
            prompt=f"Context:\n{context}\n\nQuestion: {q}\n\nAnswer clearly and concisely:"
        )
        return {"answer": answer["response"]}


@app.post("/add")
def add_knowledge(text: str):
    """Add new content to the knowledge base dynamically."""
    try:
        logging.info(f"/add received new text (id will be generated)")
        
        # Generate a unique ID for this document
        import uuid
        doc_id = str(uuid.uuid4())

        # Add the text to Chroma collection
        collection.add(documents=[text], ids=[doc_id])

        return {
            "status": "success",
            "message": "Content added to knowledge base",
            "id": doc_id
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
    

@app.get("/health")
def health():
    return {"status": "ok"}
