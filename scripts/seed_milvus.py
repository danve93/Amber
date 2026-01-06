import asyncio
import logging
import os
import uuid

from src.api.config import settings
from src.core.providers.factory import ProviderFactory
from src.core.services.embeddings import EmbeddingService
from src.core.vector_store.milvus import MilvusConfig, MilvusVectorStore

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample chunks about GraphRAG
SAMPLE_CHUNKS = [
    {
        "content": "GraphRAG is a retrieval-augmented generation system that combines knowledge graphs with vector similarity search. This hybrid approach significantly improves answer quality for complex queries involving reasoning across multiple documents.",
        "document_id": "doc_sample_01",
    },
    {
        "content": "Unlike standard RAG, which retrieves chunks based solely on semantic similarity, GraphRAG extracts entities and relationships to form a graph. This allows the system to traverse connections and find relevant information that might be semantically distant but structurally related.",
        "document_id": "doc_sample_01",
    },
    {
        "content": "Amber is the codename for this hybrid system. It uses Milvus for vector storage and Neo4j for graph storage. The architecture is designed to be modular, supporting various LLM providers like OpenAI and Anthropic.",
        "document_id": "doc_sample_02",
    },
    {
        "content": "The ingestion pipeline consists of several stages: document parsing, chunking, entity extraction, and embedding generation. Each stage is observable and emits metrics for monitoring system health.",
        "document_id": "doc_sample_02",
    }
]

async def seed_milvus():
    print(f"Seeding Milvus at {settings.db.milvus_host}:{settings.db.milvus_port}")

    # 1. Initialize Services
    # Note: We need API key for embeddings
    api_key = os.getenv("OPENAI_API_KEY") or settings.openai_api_key
    if not api_key:
        print("WARNING: No OPENAI_API_KEY found. Using dummy embeddings? No, EmbeddingService requires a provider.")
        # We can use local provider if configured, but let's try to load from factory
        print("Attempting to use configured provider...")

    factory = ProviderFactory(openai_api_key=api_key)
    embedding_service = EmbeddingService(provider=factory.get_embedding_provider())

    milvus_config = MilvusConfig(
        host=settings.db.milvus_host,
        port=settings.db.milvus_port,
        collection_name="document_chunks"
    )
    vector_store = MilvusVectorStore(milvus_config)

    try:
        # 2. Generate Embeddings
        print(f"Generating embeddings for {len(SAMPLE_CHUNKS)} chunks...")

        texts = [c["content"] for c in SAMPLE_CHUNKS]
        # embed_texts returns (embeddings, stats)
        embeddings, stats = await embedding_service.embed_texts(texts, show_progress=True)

        # 3. Upsert to Milvus
        print("Upserting to Milvus...")

        chunks_to_upsert = []
        for i, chunk in enumerate(SAMPLE_CHUNKS):
            if not embeddings[i]:
                print(f"Warning: Empty embedding for chunk {i}")
                continue

            chunks_to_upsert.append({
                "chunk_id": f"chunk_{uuid.uuid4().hex[:16]}",
                "document_id": chunk["document_id"],
                "tenant_id": settings.tenant_id,  # Use default tenant
                "content": chunk["content"],
                "embedding": embeddings[i]
            })

        if chunks_to_upsert:
            await vector_store.upsert_chunks(chunks_to_upsert)
            print(f"✅ Seeding complete! Inserted {len(chunks_to_upsert)} chunks.")
        else:
            print("❌ No chunks to upsert.")

    except Exception as e:
        print(f"❌ Seeding failed: {e}")
        # Print factory info to help debug
        print(f"Provider: {embedding_service.provider.provider_name}")

    finally:
        await vector_store.disconnect()

if __name__ == "__main__":
    asyncio.run(seed_milvus())
