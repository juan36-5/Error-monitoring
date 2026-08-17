from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from backend.database.connection import Base

class SEOError(Base):
    __tablename__ = "seo_errors"
    
    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("scans.id", ondelete="CASCADE"))
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="CASCADE"))
    page_url = Column(String(500))
    
    # Error details
    error_type = Column(String(50))  # meta_title, meta_description, broken_link, etc.
    severity = Column(String(20))  # error, warning, info
    description = Column(Text)
    is_resolved = Column(Boolean, default=False)
    
    created_at = Column(DateTime, server_default=func.now())
    
    scan = relationship("Scan", backref="errors")
    site = relationship("Site", backref="errors")
