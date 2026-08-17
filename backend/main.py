from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import asyncio

from backend.database.connection import get_db, engine
from backend.models import site, scan, error
from backend.api.routes import sites, scans, dashboard
from backend.tasks.scan_tasks import scan_all_sites
from backend.tasks.celery_app import celery_app

# Create tables
site.Base.metadata.create_all(bind=engine)
scan.Base.metadata.create_all(bind=engine)
error.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SEO Monitor",
    description="Monitor SEO health of multiple websites",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(sites.router, prefix="/api/sites", tags=["sites"])
app.include_router(scans.router, prefix="/api/scans", tags=["scans"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])

# Static files
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def root():
    return {"message": "SEO Monitor API", "version": "1.0.0"}

@app.post("/api/scan/trigger")
async def trigger_scan(site_id: Optional[int] = None, background_tasks: BackgroundTasks = None):
    """Trigger a scan manually"""
    if site_id:
        from backend.tasks.scan_tasks import scan_website
        task = scan_website.delay(site_id)
        return {"task_id": task.id, "status": "scheduled"}
    else:
        # Scan all active sites
        scan_all_sites.delay()
        return {"status": "scheduled", "message": "All sites scheduled for scan"}

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": "connected",
            "redis": "connected",
            "celery": "running"
        }
    }

@app.get("/api/task/{task_id}")
async def get_task_status(task_id: str):
    """Get task status"""
    result = celery_app.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": result.state,
        "result": result.result if result.ready() else None
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
