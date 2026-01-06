import asyncio
import io
import os
import sys

# Set explicit overrides for localhost execution
os.environ["DATABASE_URL"] = "postgresql+asyncpg://graphrag:graphrag@localhost:5432/graphrag"
os.environ["MINIO_HOST"] = "localhost"
os.environ["MINIO_secure"] = "False"
os.environ["MINIO_ROOT_USER"] = "minioadmin"
os.environ["MINIO_ROOT_PASSWORD"] = "minioadmin"

sys.path.append(os.getcwd())

from sqlalchemy import select

from src.core.database.session import async_session_maker
from src.core.models.document import Document
from src.core.storage.minio_client import MinIOClient

try:
    from pypdf import PdfReader
except ImportError:
    print("pypdf not found. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pypdf"])
    from pypdf import PdfReader

async def main():
    doc_id = "doc_ef36052cc25b44cd"
    print(f"Populating metadata for {doc_id}...")

    # 1. Get Doc from DB
    async with async_session_maker() as session:
        result = await session.execute(select(Document).where(Document.id == doc_id))
        document = result.scalars().first()

        if not document:
            print("Document not found!")
            return

        print(f"Loaded {document.filename}. Fetching file from MinIO...")

        # 2. Get File from MinIO
        storage = MinIOClient()
        try:
            # We need the key. Usually 'documents/{id}/{filename}' or just 'documents/{filename}'?
            # Ingestion uses: key = f"{tenant_id}/{document_id}/{filename}" ??
            # Let's check ingestion.py or file listing.
            # Using list_objects to find it if unsure, but IngestionService usually stores it.
            # We don't have the key stored in Document model explicitly?
            # Document model doesn't have 'storage_key'.
            # But ingestion usually uses `f"{document.tenant_id}/{document.id}/{document.filename}"` standard path.

            # Let's try standard path
            file_key = f"{document.tenant_id}/{document.id}/{document.filename}"
            print(f"Trying key: {file_key}")

            # MinIOClient.get_file returns bytes or stream?
            # It usually returns bytes directly or response.
            # Let's check MinIOClient code if needed, but assuming bytes for now or BytesIO.
            # Actually, MinIOClient wrapper might return object.
            # I will check `src/core/storage/minio_client.py` if this fails.

            # Assuming get_object returns data.
            response = storage.client.get_object(storage.bucket_name, file_key)
            file_data = response.read()
            response.close()
            response.release_conn()

            print(f"Downloaded {len(file_data)} bytes.")

            # 3. Extract Metadata
            pdf_stream = io.BytesIO(file_data)
            reader = PdfReader(pdf_stream)

            meta = reader.metadata
            page_count = len(reader.pages)

            extracted_metadata = {
                "page_count": page_count,
                "author": meta.get("/Author", ""),
                "creation_date": meta.get("/CreationDate", ""),
                "producer": meta.get("/Producer", ""),
                "title": meta.get("/Title", "")
            }

            print(f"Extracted Metadata: {extracted_metadata}")

            # 4. Update DB
            document.metadata_ = extracted_metadata
            await session.commit()
            print("Database updated.")

        except Exception as e:
            print(f"Failed to fetch/parse file: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
