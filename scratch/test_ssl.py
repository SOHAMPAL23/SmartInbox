import asyncio
import os
import sys
import ssl
from dotenv import load_dotenv
import asyncpg

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

load_dotenv(override=True)
url = os.environ.get("DATABASE_URL")

async def test_conn(ssl_val):
    print(f"Testing connection with ssl={ssl_val}...")
    try:
        # We need to parse URL or pass ssl parameter
        # If url has ssl query params, parse them out first
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        query_params.pop("ssl", None)
        query_params.pop("sslmode", None)
        query_params.pop("channel_binding", None)
        new_query = urlencode(query_params, doseq=True)
        clean_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))
        
        # Connect using the clean url (without ssl query params) and explicit ssl param
        clean_url_dsn = clean_url.replace("postgresql+asyncpg://", "postgresql://", 1)
        if "?" in clean_url_dsn:
            clean_url_dsn += "&options=endpoint=ep-wispy-art-am4uaiuc"
        else:
            clean_url_dsn += "?options=endpoint=ep-wispy-art-am4uaiuc"
        conn = await asyncpg.connect(clean_url_dsn, ssl=ssl_val, timeout=30)
        print("Success!")
        await conn.close()
        return True
    except Exception as e:
        print(f"Failed: {repr(e)}")
        return False

async def main():
    print(f"Database URL: {url.split('@')[-1] if url else 'None'}")
    
    # Test 1: ssl=True
    await test_conn(True)
    
    # Test 2: ssl="require"
    await test_conn("require")
    
    # Test 3: ssl context with CERT_NONE (no verification)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    await test_conn(ctx)

if __name__ == "__main__":
    asyncio.run(main())
