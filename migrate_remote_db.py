import sys
import asyncio
import os

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from dotenv import load_dotenv

load_dotenv(override=True)

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("DATABASE_URL not found in environment.")
    exit(1)

# Normalize database URL protocol to asyncpg for async connection
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Clean query parameters for asyncpg compatibility
if "postgresql+asyncpg://" in DATABASE_URL:
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
    try:
        parsed = urlparse(DATABASE_URL)
        query_params = parse_qs(parsed.query)
        if "sslmode" in query_params:
            sslmode_val = query_params.pop("sslmode")[0]
            if sslmode_val in ("require", "verify-ca", "verify-full"):
                query_params["ssl"] = ["require"]
        query_params.pop("channel_binding", None)
        new_query = urlencode(query_params, doseq=True)
        DATABASE_URL = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))
    except Exception:
        pass

async def migrate():
    print(f"Connecting to {DATABASE_URL.split('@')[-1]}...")
    engine = create_async_engine(DATABASE_URL)
    
    new_columns = [
        ("spam_type", "VARCHAR(50)"),
        ("spam_type_confidence", "FLOAT"),
        ("spam_type_explanation", "VARCHAR(500)"),
        ("ai_spam_score", "FLOAT"),
        ("traditional_spam_score", "FLOAT"),
        ("ham_score", "FLOAT"),
        ("threat_level", "VARCHAR(20)"),
        ("ai_generated_probability", "FLOAT"),
        ("phishing_probability", "FLOAT"),
        ("ml_model_score", "FLOAT"),
        ("groq_semantic_score", "FLOAT"),
        ("heuristic_score", "FLOAT"),
        ("detected_categories", "JSON"),
        ("reasoning", "VARCHAR(1000)"),
        ("recommended_action", "VARCHAR(500)"),
        ("groq_available", "BOOLEAN")
    ]
    
    async with engine.begin() as conn:
        # Check current columns
        result = await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'predictions'"))
        existing_columns = [row[0] for row in result.fetchall()]
        
        for col_name, col_type in new_columns:
            if col_name not in existing_columns:
                print(f"Adding column {col_name}...")
                try:
                    await conn.execute(text(f"ALTER TABLE predictions ADD COLUMN {col_name} {col_type}"))
                except Exception as e:
                    print(f"Failed to add {col_name}: {e}")
            else:
                print(f"Column {col_name} already exists.")
    
    print("Migration complete.")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(migrate())
