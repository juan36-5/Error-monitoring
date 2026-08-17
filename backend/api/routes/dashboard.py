from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from typing import Dict, List

from backend.database.connection import get_db
from backend.models.site import Site
from backend.models.scan import Scan
from backend.models.error import SEOError

router = APIRouter()

@router.get("/summary")
def get_dashboard_summary(db: Session = Depends(get_db)):
    """Get dashboard summary statistics"""
    total_sites = db.query(Site).count()
    active_sites = db.query(Site).filter(Site.is_active == True).count()
    
    # Sites with errors
    sites_with_errors = db.query(SEOError.site_id).distinct().count()
    
    # Recent scans
    last_24h = datetime.utcnow() - timedelta(hours=24)
    recent_scans = db.query(Scan).filter(Scan.started_at >= last_24h).count()
    
    # Average SEO score
    avg_score = db.query(func.avg(Site.seo_score)).filter(Site.seo_score > 0).scalar() or 0
    
    return {
        "total_sites": total_sites,
        "active_sites": active_sites,
        "sites_with_errors": sites_with_errors,
        "recent_scans_24h": recent_scans,
        "average_seo_score": round(float(avg_score), 1)
    }

@router.get("/error-types")
def get_error_types(db: Session = Depends(get_db)):
    """Get error type distribution"""
    error_types = db.query(
        SEOError.error_type,
        func.count(SEOError.id).label('count')
    ).group_by(SEOError.error_type).all()
    
    return {
        "labels": [e.error_type for e in error_types],
        "values": [e.count for e in error_types]
    }

@router.get("/trend")
def get_trend_data(days: int = 30, db: Session = Depends(get_db)):
    """Get SEO score trend"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get latest scan for each day
    trend_data = db.query(
        func.date(Scan.completed_at).label('date'),
        func.avg(Site.seo_score).label('avg_score')
    ).join(Site).filter(
        Scan.completed_at >= start_date,
        Scan.status == 'completed'
    ).group_by('date').order_by('date').all()
    
    return {
        "dates": [str(row.date) for row in trend_data],
        "scores": [float(row.avg_score) for row in trend_data]
    }
