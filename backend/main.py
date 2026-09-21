"""
TheraScout FastAPI backend — the "FastAPI backend" box in the Application
& Orchestration layer of the architecture diagram.

This is a thin layer: it does not run any agent logic itself. It starts
and polls the Step Functions execution that does the real work.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import scan

app = FastAPI(
    title="TheraScout API",
    description="AI-Powered Therapeutic Opportunity Intelligence",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten before any real deployment
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scan.router, prefix="/scan", tags=["scan"])


@app.get("/health")
def health():
    return {"status": "ok"}
