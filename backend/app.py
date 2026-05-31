from fastapi import FastAPI

app = FastAPI(
    title="Department API",
    description="API для управления подразделениями и сотрудниками",
    version="1.0.0",
    docs_url="/docs",      # Swagger UI
    redoc_url="/redoc",    # ReDoc
    openapi_url="/openapi.json"
)