import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from sqlalchemy import select

from src.core.database.session import async_session_maker
from src.core.models.document import Document


async def main():
    print("Searching for CarbonioUserGuide.pdf...")
    async with async_session_maker() as session:
        result = await session.execute(select(Document).where(Document.filename.ilike("%Carbonio%")))
        docs = result.scalars().all()

        if not docs:
            print("No document found matching 'Carbonio'")
            return

        for doc in docs:
            print(f"FOUND_ID: {doc.id}")
            print(f"Filename: {doc.filename}")
            print(f"Status: {doc.status}")

if __name__ == "__main__":
    asyncio.run(main())
