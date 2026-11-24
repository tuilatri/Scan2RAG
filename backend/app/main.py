"""FastAPI Application Entrypoint for Scan2RAG."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.document_endpoints import router as doc_router
from app.api.qa_endpoints import router as qa_router

app = FastAPI(
    title="Scan2RAG Legal Intelligence API",
    description="Vietnamese Legal & Military Medical Document Intelligence RAG API",
    version="0.2.0",
)

# CORS Middleware for future Frontend React integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(qa_router)
app.include_router(doc_router)


@app.get("/")
def root():
    return {
        "message": "Welcome to Scan2RAG Legal Intelligence API",
        "docs_url": "/docs",
        "health_url": "/api/v1/health",
    }
