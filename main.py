from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv

from app.db.database import get_db, engine
from app.db import models
from app.api import telegram_webhook, financial_api

# Load environment variables
load_dotenv()

# Create database tables
models.Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="Financial AI Coach",
    description="AI-powered financial coaching and analysis system",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/")
async def root():
    return {"message": "Financial AI Coach API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "financial-ai-coach"}

# Include API routes
app.include_router(telegram_webhook.router, prefix="/webhook", tags=["telegram"])
app.include_router(financial_api.router, prefix="/api", tags=["financial"])

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)