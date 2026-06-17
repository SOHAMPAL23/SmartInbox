"""
seed.py  — SmartInbox database seeder
Seeds the admin user (idempotent: updates if exists, skips if already set up).
Uses the application's existing AsyncSessionLocal and SQLAlchemy models.
"""
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Ensure the project root is on sys.path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# If running outside Docker, register 'Backend' folder as 'app' package
if (ROOT / "Backend").exists() and not (ROOT / "app").exists():
    import Backend
    sys.modules["app"] = Backend
    
    import importlib
    import pkgutil
    def _register_subpackages(backend_pkg_name: str, app_alias: str) -> None:
        try:
            pkg = importlib.import_module(backend_pkg_name)
            sys.modules[app_alias] = pkg
            pkg_path = getattr(pkg, "__path__", None)
            if pkg_path is not None:
                for finder, subname, ispkg in pkgutil.walk_packages(
                    path=pkg_path,
                    prefix=f"{backend_pkg_name}.",
                    onerror=lambda name: None,
                ):
                    try:
                        submod = importlib.import_module(subname)
                        alias = subname.replace(backend_pkg_name, app_alias, 1)
                        sys.modules[alias] = submod
                    except ImportError:
                        pass
        except Exception:
            pass
    _register_subpackages("Backend", "app")

# Now we can safely import from app
from app.database import AsyncSessionLocal, create_tables
from app.models.user import User, UserRole
from app.auth.password import hash_password

admin_password = hash_password("Admin@123")

async def seed_async():
    print("Database seeding started...")
    
    # 1. Ensure tables exist first
    print("Verifying database schema / creating tables...")
    await create_tables()
    
    # 2. Seed default admin user
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        stmt = select(User).where(User.email == "admin@smartinbox.com")
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user:
            user.hashed_password = admin_password
            user.role = UserRole.admin
            user.is_active = True
            print("Updated existing admin@smartinbox.com — password and admin role set.")
        else:
            new_user = User(
                email="admin@smartinbox.com",
                username="SuperAdmin",
                hashed_password=admin_password,
                role=UserRole.admin,
                is_active=True
            )
            session.add(new_user)
            print("Created new Admin! Email: admin@smartinbox.com | Password: Admin@123")
        
        await session.commit()
    print("Seed completed successfully.")

def seed():
    # Wait for database connection retries (essential for slow db container startup)
    max_retries = 10
    retry_delay = 3
    
    for attempt in range(1, max_retries + 1):
        try:
            asyncio.run(seed_async())
            break
        except Exception as e:
            print(f"Seed attempt {attempt}/{max_retries} failed: {e}")
            if attempt == max_retries:
                print("All seed attempts failed. Exiting.")
                sys.exit(1)
            print(f"Retrying in {retry_delay}s...")
            asyncio.run(asyncio.sleep(retry_delay))

if __name__ == "__main__":
    seed()
