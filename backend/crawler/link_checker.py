import aiohttp
import asyncio
from typing import List, Dict, Set
from urllib.parse import urlparse, urljoin
from backend.config import settings

class LinkChecker:
    def __init__(self, max_concurrent=20):
        self.max_concurrent = max_concurrent
        self.timeout = settings.REQUEST_TIMEOUT
    
    async def check_broken_links(self, urls: List[str]) -> Dict[str, Dict]:
        """Check multiple URLs for broken links"""
        results = {}
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def check_url(session, url):
            async with semaphore:
                try:
                    async with session.head(url, allow_redirects=True) as response:
                        if response.status >= 400:
                            return url, {'status': response.status, 'error': True}
                        return url, {'status': response.status, 'error': False}
                except:
                    return url, {'status': 0, 'error': True, 'error_message': 'Connection error'}
        
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={'User-Agent': settings.USER_AGENT}
        ) as session:
            tasks = [check_url(session, url) for url in urls]
            results_list = await asyncio.gather(*tasks)
            
            for url, result in results_list:
                results[url] = result
        
        return results
