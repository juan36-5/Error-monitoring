from celery import Task, shared_task
from sqlalchemy.orm import Session
from datetime import datetime
import asyncio
from typing import List, Dict
from backend.tasks.celery_app import celery_app
from backend.database.connection import SessionLocal
from backend.models.site import Site
from backend.models.scan import Scan
from backend.models.error import SEOError
from backend.crawler.seo_checker import SEOChecker
from backend.crawler.link_checker import LinkChecker
from backend.telegram.bot import TelegramNotifier
import logging

logger = logging.getLogger(__name__)

class ScanTask(Task):
    _session = None
    
    @property
    def db(self):
        if self._session is None:
            self._session = SessionLocal()
        return self._session
    
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        if self._session:
            self._session.close()

@celery_app.task(base=ScanTask, bind=True)
def scan_website(self, site_id: int, deep_scan: bool = False):
    """Scan a single website"""
    logger.info(f"Starting scan for site_id: {site_id}")
    
    # Get site
    site = self.db.query(Site).filter(Site.id == site_id).first()
    if not site:
        logger.error(f"Site {site_id} not found")
        return {"error": "Site not found"}
    
    # Create scan record
    scan = Scan(
        site_id=site_id,
        started_at=datetime.utcnow(),
        status="running"
    )
    self.db.add(scan)
    self.db.commit()
    
    try:
        # Run scan
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(self._perform_scan(site.url, deep_scan))
        loop.close()
        
        # Save results
        self._save_scan_results(scan, results, site)
        
        # Send Telegram notifications
        telegram = TelegramNotifier()
        errors = len(results.get('errors', []))
        if errors > 0:
            asyncio.create_task(telegram.send_alert(site.url, results))
        elif errors == 0:
            asyncio.create_task(telegram.send_success_notification(site.url))
        
        # Update site
        site.last_scanned_at = datetime.utcnow()
        site.seo_score = results.get('score', 0)
        site.total_errors = errors
        self.db.commit()
        
        return {"status": "completed", "site_id": site_id, "errors": errors}
        
    except Exception as e:
        logger.error(f"Scan failed for site {site_id}: {str(e)}")
        scan.status = "failed"
        self.db.commit()
        return {"status": "failed", "error": str(e)}

async def _perform_scan(self, url: str, deep_scan: bool = False) -> Dict:
    """Perform the actual scan"""
    async with SEOChecker() as checker:
        # Check homepage
        home_result = await checker.check_page(url)
        
        # For deep scan, find and check all pages
        if deep_scan:
            all_pages = await self._discover_pages(url)
            page_results = await asyncio.gather(
                *[checker.check_page(page_url) for page_url in all_pages]
            )
        else:
            page_results = [home_result]
        
        # Compile results
        return self._compile_results(url, page_results)

async def _discover_pages(self, base_url: str) -> List[str]:
    """Discover all pages on a site"""
    # This would be more sophisticated in production
    # For now, just return the homepage
    return [base_url]

def _compile_results(self, url: str, page_results: List[Dict]) -> Dict:
    """Compile scan results"""
    all_errors = []
    total_score = 0
    
    for result in page_results:
        if result.get('status') == 'error':
            all_errors.append({
                'url': result.get('url', url),
                'errors': result.get('errors', [])
            })
        else:
            errors = result.get('errors', [])
            if errors:
                all_errors.append({
                    'url': result.get('url', url),
                    'errors': errors
                })
            # Calculate score (basic)
            score = 100 - (len(errors) * 5)
            total_score += max(0, score)
    
    avg_score = total_score / len(page_results) if page_results else 0
    
    return {
        'url': url,
        'score': avg_score,
        'pages_scanned': len(page_results),
        'errors': all_errors,
        'total_errors': sum(len(item['errors']) for item in all_errors)
    }

def _save_scan_results(self, scan: Scan, results: Dict, site: Site):
    """Save scan results to database"""
    scan.completed_at = datetime.utcnow()
    scan.status = "completed"
    scan.total_pages = results.get('pages_scanned', 0)
    scan.pages_with_errors = len(results.get('errors', []))
    
    # Save errors
    for error_item in results.get('errors', []):
        for error in error_item.get('errors', []):
            seo_error = SEOError(
                scan_id=scan.id,
                site_id=site.id,
                page_url=error_item.get('url', site.url),
                error_type=error.get('type', 'unknown'),
                severity=error.get('severity', 'warning'),
                description=error.get('description', '')
            )
            self.db.add(seo_error)
    
    self.db.commit()

@celery_app.task
def scan_all_sites(frequency: str = "daily"):
    """Scan all active sites based on frequency"""
    db = SessionLocal()
    try:
        sites = db.query(Site).filter(
            Site.is_active == True,
            Site.scan_frequency == frequency
        ).all()
        
        for site in sites:
            scan_website.delay(site.id)
        
        return {"status": "scheduled", "total_sites": len(sites)}
    finally:
        db.close()
