import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http import models
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import CharacterTextSplitter

load_dotenv()

# 1. SETUP: Choose your endpoint
# For Localhost (Recommended for the Factory):
QDRANT_URL = "http://localhost:6333"
# For Cloud (Use your Endpoint from GCP if you prefer):
# QDRANT_URL = "https://3065e0df-0719-426e-a159-499b6a8ebae3.us-east4-0.gcp.cloud.qdrant.io"

COLLECTION_NAME = "factory_memory"

# Initialize Clients
client = QdrantClient(url=QDRANT_URL)
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    api_key=os.getenv("OPENROUTER_API_KEY") or "",
    base_url="https://openrouter.ai/api/v1"
)

def ingest_factory_files():
    # Define the files that make up your "Factory Brain"
    files_to_index = [
        "dispatcher.py",
        "/root/HEARTBEAT.md",
        "/root/ssh_agent_memory.json"
    ]

    # WIPE AND REBUILD: Ensure memory is a perfect mirror of current state
    if client.collection_exists(collection_name=COLLECTION_NAME):
        print(f"🧹 Wiping old memory collection: {COLLECTION_NAME}")
        client.delete_collection(collection_name=COLLECTION_NAME)
        
    print(f"🚀 Creating fresh collection: {COLLECTION_NAME}")
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE),
    )

    for file_path in files_to_index:
        if not os.path.exists(file_path):
            print(f"⚠️ Skipping {file_path}: File not found.")
            continue

        print(f"📖 Reading {file_path}...")
        loader = TextLoader(file_path)
        documents = loader.load()

        # Split text into manageable chunks
        text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        docs = text_splitter.split_documents(documents)

        # Generate embeddings and upsert
        print(f"🧠 Vectorizing and storing {len(docs)} chunks...")
        for i, doc in enumerate(docs):
            vector = embeddings.embed_query(doc.page_content)
            client.upsert(
                collection_name=COLLECTION_NAME,
                points=[
                    models.PointStruct(
                        id=hash(f"{file_path}_{i}") & 0xFFFFFFFFFFFFFFFF, # Generate a valid 64-bit int ID
                        vector=vector,
                        payload={"source": file_path, "content": doc.page_content}
                    )
                ]
            )

    print("\n✅ Factory memory ingestion complete! Your agent is now self-aware.")

if __name__ == "__main__":
    ingest_factory_files()
