import asyncio
import os
import sys

# Set explicit overrides for localhost execution
os.environ["DATABASE_URL"] = "postgresql+asyncpg://graphrag:graphrag@localhost:5432/graphrag"

sys.path.append(os.getcwd())

from sqlalchemy import select

from src.core.database.session import async_session_maker
from src.core.models.document import Document


async def main():
    doc_id = "doc_ef36052cc25b44cd" # CarbonioUserGuide.pdf
    print(f"Checking data for {doc_id}...")

    async with async_session_maker() as session:
        result = await session.execute(select(Document).where(Document.id == doc_id))
        document = result.scalars().first()

        if not document:
            print("Document not found!")
            return

        print(f"Summary: {len(document.summary)} chars")
        print(f"Keywords: {document.keywords}")
        print(f"Hashtags: {document.hashtags}")
        print(f"Metadata (from extraction): {document.metadata_}")

if __name__ == "__main__":
    asyncio.run(main())
