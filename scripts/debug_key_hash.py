import asyncio
import sys
import os
from sqlalchemy import select

# Add src to pythonpath
sys.path.append(os.getcwd())

from src.api.deps import _async_session_maker
from src.core.models.api_key import ApiKey
from src.shared.security import hash_api_key
from src.api.config import settings

async def main():
    try:
        # 1. Print current settings
        print(f"DEBUG: SECRET_KEY loaded = {settings.secret_key[:5]}...{settings.secret_key[-5:]}")
        
        target_key = "amber-dev-key-2024"
        computed_hash = hash_api_key(target_key)
        print(f"DEBUG: Computed hash for '{target_key}' = {computed_hash}")
        
        async with _async_session_maker() as session:
            # 2. Get the Development Key from DB
            query = select(ApiKey).where(ApiKey.name == "Development Key")
            result = await session.execute(query)
            key_record = result.scalars().first()
            
            if not key_record:
                print("ERROR: Key 'Development Key' NOT FOUND in DB.")
                return

            print(f"DEBUG: DB Key found. ID={key_record.id}")
            print(f"DEBUG: DB Stored Hash = {key_record.hashed_key}")
            
            if computed_hash == key_record.hashed_key:
                print("\nSUCCESS: Hashes MATCH. The key should work.")
            else:
                print("\nFAILURE: Hashes DO NOT MATCH.")
                print("Possible causes:")
                print("1. SECRET_KEY changed since key creation.")
                print("2. The key in DB was created from a different raw string.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
