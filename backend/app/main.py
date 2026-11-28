"""FastAPI Application Entrypoint for Scan2RAG."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.document_endpoints import router as doc_router
from app.api.ocr_endpoints import router as ocr_router
from app.api.qa_endpoints import router as qa_router
from app.core.rate_limit import RateLimitMiddleware

app = FastAPI(
    title="Scan2RAG Legal Intelligence API",
    description="Vietnamese Legal & Military Medical Document Intelligence RAG API",
    version="0.4.0",
)

# CORS Middleware configured via CORS_ORIGINS env (no wildcard with credentials)
_raw_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173",
)
_allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitMiddleware)

app.include_router(qa_router)
app.include_router(doc_router)
app.include_router(ocr_router)


@app.get("/")
def root():
    return {
        "message": "Welcome to Scan2RAG Legal Intelligence API",
        "docs_url": "/docs",
        "health_url": "/api/v1/health",
    }
