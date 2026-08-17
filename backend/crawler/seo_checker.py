import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Tuple, Optional
import re
from datetime import datetime
from backend.config import settings

class SEOChecker:
    def __init__(self):
        self.timeout = settings.REQUEST_TIMEOUT
        self.user_agent = settings.USER_AGENT
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={'User-Agent': self.user_agent}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def check_page(self, url: str) -> Dict:
        """Comprehensive SEO check for a single page"""
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return self._create_error_response(url, "HTTP Error", f"Status: {response.status}")
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Get page content
                text = soup.get_text()
                word_count = len(re.findall(r'\w+', text))
                
                # Check meta tags
                title_tag = soup.find('title')
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
                
                # Check headings
                h1_tags = soup.find_all('h1')
                h2_tags = soup.find_all('h2')
                
                # Check links
                links = soup.find_all('a', href=True)
                internal_links = []
                external_links = []
                
                for link in links:
                    href = link['href']
                    if href.startswith('http') or href.startswith('//'):
                        if urlparse(url).netloc in href:
                            internal_links.append(href)
                        else:
                            external_links.append(href)
                    elif href.startswith('/') or href.startswith('#'):
                        internal_links.append(href)
                
                # Check images
                images = soup.find_all('img')
                images_without_alt = [img for img in images if not img.get('alt')]
                
                # Check canonical
                canonical = soup.find('link', attrs={'rel': 'canonical'})
                canonical_url = canonical.get('href') if canonical else None
                
                # Check robots meta
                robots = soup.find('meta', attrs={'name': 'robots'})
                noindex = 'noindex' in robots.get('content', '') if robots else False
                
                # Check schema.org markup
                schema_scripts = soup.find_all('script', attrs={'type': 'application/ld+json'})
                
                # Return comprehensive results
                return {
                    'url': url,
                    'status': 'success',
                    'title': title_tag.text.strip() if title_tag else None,
                    'meta_description': meta_desc.get('content', '').strip() if meta_desc else None,
                    'meta_keywords': meta_keywords.get('content', '').strip() if meta_keywords else None,
                    'word_count': word_count,
                    'h1_count': len(h1_tags),
                    'h2_count': len(h2_tags),
                    'internal_links_count': len(internal_links),
                    'external_links_count': len(external_links),
                    'images_count': len(images),
                    'images_without_alt': len(images_without_alt),
                    'canonical_url': canonical_url,
                    'noindex': noindex,
                    'has_schema': len(schema_scripts) > 0,
                    'errors': self._check_seo_issues(title_tag, meta_desc, h1_tags, links, images, noindex)
                }
                
        except asyncio.TimeoutError:
            return self._create_error_response(url, "Timeout", "Page load timeout")
        except Exception as e:
            return self._create_error_response(url, "Crawl Error", str(e))
    
    def _check_seo_issues(self, title, meta_desc, h1_tags, links, images, noindex) -> List[Dict]:
        """Check for SEO issues"""
        issues = []
        
        # Title checks
        if not title:
            issues.append({
                'type': 'missing_title',
                'severity': 'error',
                'description': 'Missing <title> tag'
            })
        elif len(title.text.strip()) < 30:
            issues.append({
                'type': 'title_too_short',
                'severity': 'warning',
                'description': f'Title is too short: {len(title.text.strip())} characters (< 30)'
            })
        elif len(title.text.strip()) > 60:
            issues.append({
                'type': 'title_too_long',
                'severity': 'warning',
                'description': f'Title is too long: {len(title.text.strip())} characters (> 60)'
            })
        
        # Meta description checks
        if not meta_desc:
            issues.append({
                'type': 'missing_description',
                'severity': 'error',
                'description': 'Missing meta description'
            })
        elif len(meta_desc.get('content', '').strip()) < 50:
            issues.append({
                'type': 'description_too_short',
                'severity': 'warning',
                'description': 'Meta description is too short (< 50 characters)'
            })
        elif len(meta_desc.get('content', '').strip()) > 160:
            issues.append({
                'type': 'description_too_long',
                'severity': 'warning',
                'description': 'Meta description is too long (> 160 characters)'
            })
        
        # H1 checks
        if not h1_tags:
            issues.append({
                'type': 'missing_h1',
                'severity': 'error',
                'description': 'Missing H1 heading'
            })
        elif len(h1_tags) > 1:
            issues.append({
                'type': 'multiple_h1',
                'severity': 'warning',
                'description': f'Multiple H1 tags found: {len(h1_tags)}'
            })
        
        # Link checks
        if len(links) == 0:
            issues.append({
                'type': 'no_links',
                'severity': 'warning',
                'description': 'No links found on page'
            })
        
        # Image alt checks
        if len(images) > 0 and len([img for img in images if not img.get('alt')]) > 0:
            issues.append({
                'type': 'missing_alt',
                'severity': 'warning',
                'description': f'{len([img for img in images if not img.get("alt")])} images missing alt text'
            })
        
        # Noindex check
        if noindex:
            issues.append({
                'type': 'noindex',
                'severity': 'error',
                'description': 'Page is marked noindex'
            })
        
        return issues
    
    def _create_error_response(self, url: str, error_type: str, message: str) -> Dict:
        return {
            'url': url,
            'status': 'error',
            'error_type': error_type,
            'error_message': message,
            'errors': [{
                'type': error_type.lower().replace(' ', '_'),
                'severity': 'error',
                'description': message
            }]
        }
