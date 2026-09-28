"""
FastAPI application for Brand AI-Readiness & Engagement Auditor.
Provides REST endpoints for running audits, retrieving reports, and system health checks.
"""

from __future__ import annotations
import os
import sys
import datetime
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

# Ensure root in sys.path
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from server.schemas import AuditRequest, AuditResponse, HealthResponse
from server.services.audit_service import audit_service

app = FastAPI(
    title="WebVerity API",
    description="WebVerity is an evidence-driven website intelligence platform analyzing AI Discoverability, Machine Readability, Structured Data, Entity Clarity, Freshness, and On-Site Engagement.",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json"
)

# Configure CORS for local frontend development and production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permits localhost:5173 and any dev origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Returns server health status, version, and component availability.
    """
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        services={
            "crawler": "ready",
            "orchestrator": "ready",
            "skills": "ready",
            "api": "ready"
        }
    )


@app.post(
    "/api/audit",
    response_model=AuditResponse,
    status_code=status.HTTP_200_OK,
    tags=["Audit"],
    summary="Execute Website Investigation"
)
async def run_audit(request: AuditRequest):
    """
    Executes an end-to-end WebVerity AI Readiness & Website Intelligence audit for the target URL.
    Coordinates bounded crawl, 4 specialized domain skills, and finding synthesis.
    """
    if not request.url or not request.url.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A target website URL must be provided."
        )

    try:
        response = await audit_service.execute_audit(request)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audit execution encountered an unhandled error: {str(e)}"
        )


@app.get(
    "/api/audit/{audit_id}",
    response_model=AuditResponse,
    tags=["Audit"],
    summary="Get Audit Report by ID"
)
async def get_audit(audit_id: str):
    """
    Retrieves previously executed audit results by unique audit ID.
    """
    audit = audit_service.get_audit(audit_id)
    if not audit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit report with ID '{audit_id}' not found."
        )
    return audit


@app.get(
    "/api/audit/{audit_id}/report",
    response_class=PlainTextResponse,
    tags=["Audit"],
    summary="Get Markdown Report"
)
async def get_audit_markdown(audit_id: str):
    """
    Retrieves human-readable GitHub-flavored markdown report for a specific audit.
    """
    audit = audit_service.get_audit(audit_id)
    if not audit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit report with ID '{audit_id}' not found."
        )
    return audit.markdown_report or "# No Markdown Report Available"


# Serve static frontend build if present (for unified production deployment)
_dist_dir = os.path.join(_ROOT, "frontend", "dist")
if os.path.isdir(_dist_dir):
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=_dist_dir, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)
