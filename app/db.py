# app/db.py
import os
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Use env var in Docker; fallback to local SQLite when running outside
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

# Pre-ping avoids stale connection errors when DB restarts
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db(retries: int = 20, delay: float = 1.0):
    """
    Initializes DB schema by creating tables from SQLAlchemy models.
    Retries to handle the case where Postgres isn't ready yet.
    """
    # Lazy import to avoid circular imports (Base is defined above)
    try:
        import app.model  # noqa: F401
        import app.order_model
    except Exception as e:
        print(f"Warning: could not import app.model yet: {e}")

    for i in range(retries):
        try:
            Base.metadata.create_all(bind=engine)
            print("DB initialized")
            return
        except Exception as e:
            print(f"DB init attempt {i+1}/{retries} failed: {e}")
            time.sleep(delay)
    raise RuntimeError("Could not initialize DB after retries.")
