from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, Text
from sqlalchemy.sql import func
from backend.database.connection import Base

class Site(Base):
    __tablename__ = "sites"
    
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(500), unique=True, nullable=False, index=True)
    name = Column(String(200))
    is_active = Column(Boolean, default=True)
    scan_frequency = Column(String(20), default="daily")  # daily, weekly, monthly
    last_scanned_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # SEO scores (cached)
    seo_score = Column(Float, default=0.0)
    performance_score = Column(Float, default=0.0)
    total_errors = Column(Integer, default=0)
    total_warnings = Column(Integer, default=0)
