# main.py
import sys
import os
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from router import build_v1_router
from db import engine, Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting application...")
    Base.metadata.create_all(bind=engine)
    yield
    print("👋 Shutting down...")

app = FastAPI(
    title="Department API",
    description="API for managing departments and employees",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(build_v1_router())

@app.get("/")
async def root():
    return {
        "message": "Department API is running",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("APP_HOST", "127.0.0.1")
    port = int(os.getenv("APP_PORT", "8000"))
    debug = os.getenv("DEBUG", "False").lower() == "true"
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )