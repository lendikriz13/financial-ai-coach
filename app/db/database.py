from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Fallback to Railway DATABASE_URL from earlier
    DATABASE_URL = "postgresql://postgres:NKHEXyGCOlXQBkdmaaQWfIVcCkuwkjLV@tramway.proxy.rlwy.net:43075/railway"
    print("Using fallback DATABASE_URL")

print(f"Connecting to database: {DATABASE_URL[:20]}...")  # Only show first 20 chars for security

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()