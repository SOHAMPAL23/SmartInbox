import asyncio
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv(".env")

async def check():
    url = os.getenv("DATABASE_URL")
    # Convert async to sync for easy checking
    sync_url = url.replace("postgresql+asyncpg://", "postgresql://")
    engine = create_engine(sync_url)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT id, status, error FROM jobs ORDER BY created_at DESC LIMIT 5"))
        for row in result:
            print(row)

if __name__ == "__main__":
    import sys
    # Add project root to path
    sys.path.append(os.getcwd())
    try:
        url = os.getenv("DATABASE_URL")
        sync_url = url.replace("postgresql+asyncpg://", "postgresql://").replace("?ssl=require", "?sslmode=require")
        engine = create_engine(sync_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, status, error FROM jobs ORDER BY created_at DESC LIMIT 5"))
            for row in result:
                print(row)
    except Exception as e:
        print(f"Error: {e}")
