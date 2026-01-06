import asyncio
import os
import sys

# Set explicit overrides for localhost execution matched to docker-compose ports
os.environ["DATABASE_URL"] = "postgresql+asyncpg://graphrag:graphrag@localhost:5432/graphrag"
os.environ["CELERY_BROKER_URL"] = "redis://localhost:6379/1"
os.environ["CELERY_RESULT_BACKEND"] = "redis://localhost:6379/2"

sys.path.append(os.getcwd())

from sqlalchemy import select

from src.api.config import settings
from src.core.database.session import async_session_maker
from src.core.intelligence.document_summarizer import get_document_summarizer
from src.core.models.chunk import Chunk
from src.core.models.document import Document
from src.workers.tasks import process_communities


async def main():
    doc_id = "doc_ef36052cc25b44cd"
    print(f"Regenerating for {doc_id}...")

    # Ensure keys are loaded (Settings does this via .env, but we log to be sure)
    print(f"OpenAI Key present: {bool(settings.openai_api_key)}")

    async with async_session_maker() as session:
        result = await session.execute(select(Document).where(Document.id == doc_id))
        document = result.scalars().first()

        if not document:
            print("Document not found!")
            return

        print(f"Loaded {document.filename}. Fetching chunks...")
        # Correct field is 'index'
        chunk_result = await session.execute(select(Chunk).where(Chunk.document_id == doc_id).order_by(Chunk.index))
        chunks = chunk_result.scalars().all()

        if not chunks:
            print("No chunks found!")
            return

        print(f"Found {len(chunks)} chunks. Generating summary with LLM...")

        summarizer = get_document_summarizer()
        chunk_texts = [c.content for c in chunks]

        enrichment = await summarizer.extract_summary(
            chunks=chunk_texts,
            document_title=document.filename
        )

        print(f"Summary generated: {max(0, len(enrichment['summary']))} chars")
        print(f"Keywords: {enrichment['keywords']}")

        document.summary = enrichment["summary"]
        document.document_type = enrichment["document_type"]
        document.hashtags = enrichment["hashtags"]
        document.keywords = enrichment["keywords"]

        # Merge new metadata
        current_meta = document.metadata_ or {}
        current_meta.update({
             "categories": enrichment.get("categories", ["general"]),
             "processing_method": "ocr", # Assuming standard pipeline
             "conversion_pipeline": "amber_v2_regenerated"
        })
        document.metadata_ = current_meta

        await session.commit()
        print("Document updated in DB.")

        # Trigger Communities
        print(f"Triggering community detection for tenant {document.tenant_id}...")
        try:
             process_communities.delay(document.tenant_id)
             print("Community detection triggered successfully.")
        except Exception as e:
             print(f"Failed to trigger communities: {e}")

if __name__ == "__main__":
    asyncio.run(main())
