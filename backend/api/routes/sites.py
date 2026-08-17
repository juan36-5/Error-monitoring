from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, HttpUrl
from datetime import datetime

from backend.database.connection import get_db
from backend.models.site import Site
from backend.models.scan import Scan
from backend.models.error import SEOError

router = APIRouter()

class SiteCreate(BaseModel):
    url: HttpUrl
    name: Optional[str] = None
    scan_frequency: str = "daily"

class SiteUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    scan_frequency: Optional[str] = None

class SiteResponse(BaseModel):
    id: int
    url: str
    name: Optional[str]
    is_active: bool
    scan_frequency: str
    seo_score: float
    total_errors: int
    last_scanned_at: Optional[datetime]
    created_at: datetime

@router.post("/", response_model=SiteResponse)
def create_site(site_data: SiteCreate, db: Session = Depends(get_db)):
    """Add a new site to monitor"""
    # Check if site exists
    existing = db.query(Site).filter(Site.url == str(site_data.url)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Site already exists")
    
    # Create site
    new_site = Site(
        url=str(site_data.url),
        name=site_data.name or str(site_data.url),
        scan_frequency=site_data.scan_frequency
    )
    db.add(new_site)
    db.commit()
    db.refresh(new_site)
    return new_site

@router.get("/", response_model=List[SiteResponse])
def get_sites(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """Get all sites"""
    query = db.query(Site)
    if is_active is not None:
        query = query.filter(Site.is_active == is_active)
    return query.offset(skip).limit(limit).all()

@router.get("/{site_id}", response_model=SiteResponse)
def get_site(site_id: int, db: Session = Depends(get_db)):
    """Get site details"""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    return site

@router.put("/{site_id}", response_model=SiteResponse)
def update_site(site_id: int, site_data: SiteUpdate, db: Session = Depends(get_db)):
    """Update site settings"""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    for field, value in site_data.dict(exclude_unset=True).items():
        setattr(site, field, value)
    
    db.commit()
    db.refresh(site)
    return site

@router.delete("/{site_id}")
def delete_s
