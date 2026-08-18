import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import re
import os
import time
import json
from urllib.parse import urlparse
from collections import Counter
import random
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="Complete SEO Audit + Optimization", page_icon="🔍", layout="wide")

# ============ USER AGENTS ============
def get_random_headers():
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (Linux; Android 11; SM-G960F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Mobile Safari/537.36',
    ]
    return {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
    }

# ============ SESSION STATE ============
if 'sites' not in st.session_state:
    st.session_state.sites = []
if 'results' not in st.session_state:
    st.session_state.results = {}
if 'initialized' not in st.session_state:
    st.session_state.initialized = False

# ============ GET PAGE CONTENT ============
def get_page_content(url):
    if not url.startswith('http'):
        url = 'https://' + url
    
    for attempt in range(5):
        try:
            headers = get_random_headers()
            response = requests.get(url, timeout=30, headers=headers, allow_redirects=True, verify=False)
            if response.status_code == 200 and len(response.text) > 500:
                return response.text, response.status_code
        except:
            time.sleep(random.uniform(1, 3))
            continue
    return "", 0

# ============ CHECK IF IMAGE IS CONTENT IMAGE ============
def is_content_image(img):
    """Check if an image is a content image (not icon/logo/button)"""
    
    # Get image attributes
    src = img.get('src', '').lower()
    alt = img.get('alt', '').lower()
    cls = img.get('class', [])
    if isinstance(cls, str):
        cls = [cls]
    cls_str = ' '.join(cls).lower()
    width = img.get('width', '')
    height = img.get('height', '')
    
    # Skip if it's an icon (small images)
    try:
        if width and int(width) < 50:
            return False
        if height and int(height) < 50:
            return False
    except:
        pass
    
    # Skip icon file types
    icon_patterns = ['icon', 'logo-small', 'favicon', 'svg', 'social', 'share', 'btn', 'button', 'arrow', 'banner-small']
    for pattern in icon_patterns:
        if pattern in src or pattern in cls_str:
            return False
    
    # Skip common icon classes
    icon_classes = ['icon', 'fa-', 'fas', 'far', 'fab', 'glyphicon', 'material-icons', 'svg-icon', 'social-icon']
    for cls_name in icon_classes:
        if cls_name in cls_str:
            return False
    
    # Check if alt text indicates it's an icon
    icon_alt_patterns = ['icon', 'logo', 'button', 'btn', 'share', 'social', 'arrow', 'menu', 'hamburger']
    for pattern in icon_alt_patterns:
        if pattern in alt:
            return False
    
    # Check if it's a logo
    if 'logo' in src or 'logo' in alt or 'logo' in cls_str:
        return False
    
    # Check if it's in a content area (article, main, section)
    parent = img.parent
    for _ in range(3):  # Check up to 3 levels up
        if parent:
            parent_name = parent.name if parent.name else ''
            parent_class = ' '.join(parent.get('class', [])).lower() if parent.get('class') else ''
            if 'article' in parent_name or 'content' in parent_name or 'post' in parent_name:
                return True
            if 'article' in parent_class or 'content' in parent_class or 'post' in parent_class:
                return True
            parent = parent.parent
        else:
            break
    
    # If image has meaningful alt text (longer than 3 chars) and not in header/footer
    if len(alt) > 3:
        # Check if not in header/footer
        parent = img.parent
        for _ in range(3):
            if parent:
                parent_name = parent.name if parent.name else ''
                parent_class = ' '.join(parent.get('class', [])).lower() if parent.get('class') else ''
                if 'header' in parent_name or 'footer' in parent_name or 'nav' in parent_name:
                    return False
                if 'header' in parent_class or 'footer' in parent_class or 'nav' in parent_class:
                    return False
                parent = parent.parent
            else:
                break
        return True
    
    # Default: if it's in a paragraph, it's likely content
    parent = img.parent
    for _ in range(3):
        if parent and parent.name == 'p':
            return True
        if parent:
            parent = parent.parent
        else:
            break
    
    return False

# ============ COMPLETE SEO AUDIT ============
def complete_seo_audit(url):
    result = {
        'url': url,
        'score': 0,
        'errors': [],
        'warnings': [],
        'successes': [],
        'optimizations': [],
        'last_check': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'is_accessible': False,
        'status_code': None,
        'response_time': 0,
        'page_size': 0,
        'title': '',
        'title_length': 0,
        'meta_description': '',
        'meta_description_length': 0,
        'meta_keywords': '',
        'h1_count': 0,
        'h1_text': '',
        'h2_count': 0,
        'h3_count': 0,
        'h4_count': 0,
        'h5_count': 0,
        'h6_count': 0,
        'total_words': 0,
        'paragraph_count': 0,
        'sentence_count': 0,
        'top_keywords': [],
        'readability_score': 0,
        'total_links': 0,
        'internal_links': 0,
        'external_links': 0,
        'nofollow_links': 0,
        'broken_links': [],
        'broken_links_count': 0,
        'anchor_texts': [],
        'total_images': 0,
        'content_images': 0,
        'icon_images': 0,
        'images_with_alt': 0,
        'images_without_alt': 0,
        'content_images_with_alt': 0,
        'content_images_without_alt': 0,
        'missing_alt_list': [],
        'has_schema': False,
        'schema_types': [],
        'has_og': False,
        'og_title': '',
        'og_description': '',
        'og_image': '',
        'og_url': '',
        'has_twitter': False,
        'twitter_card': '',
        'twitter_title': '',
        'twitter_description': '',
        'has_ssl': False,
        'has_viewport': False,
        'has_canonical': False,
        'canonical_url': '',
        'has_language': False,
        'language': '',
        'has_robots': False,
        'robots_content': '',
        'has_sitemap': False,
        'css_count': 0,
        'js_count': 0,
        'has_lazy_loading': False,
        'has_compression': False,
        'has_mixed_content': False,
        'is_mobile_friendly': False,
        'meta_score': 0,
        'content_score': 0,
        'link_score': 0,
        'image_score': 0,
        'technical_score': 0,
        'severity': []
    }
    
    try:
        start_time = time.time()
        html_content, status_code = get_page_content(url)
        result['status_code'] = status_code
        
        if not html_content or len(html_content) < 100:
            result['errors'].append(f"Failed to load page - Status: {status_code}")
            return result
        
        result['response_time'] = round(time.time() - start_time, 2)
        result['page_size'] = len(html_content)
        result['is_accessible'] = True
        result['has_ssl'] = url.startswith('https')
        
        soup = BeautifulSoup(html_content, 'html.parser')
        base_domain = urlparse(url).netloc
        
        # ===== META TAGS =====
        title = soup.find('title')
        if title and title.text.strip():
            result['title'] = title.text.strip()
            result['title_length'] = len(title.text.strip())
            result['successes'].append(f"Title: {result['title_length']} chars")
            
            if 30 <= result['title_length'] <= 60:
                result['successes'].append("Title length is optimal (30-60 chars)")
                result['meta_score'] += 15
            elif result['title_length'] < 30:
                result['warnings'].append(f"Title too short: {result['title_length']} chars (recommend 30-60)")
                result['optimizations'].append("Increase title length to 30-60 characters")
            else:
                result['warnings'].append(f"Title too long: {result['title_length']} chars (recommend 30-60)")
                result['optimizations'].append("Shorten title to 30-60 characters")
        else:
            result['errors'].append("Missing title tag")
            result['optimizations'].append("Add a title tag with primary keywords")
        
        # Meta Description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content', '').strip():
            result['meta_description'] = meta_desc.get('content').strip()
            result['meta_description_length'] = len(result['meta_description'])
            result['successes'].append(f"Description: {result['meta_description_length']} chars")
            
            if 50 <= result['meta_description_length'] <= 160:
                result['successes'].append("Description length is optimal (50-160 chars)")
                result['meta_score'] += 15
            elif result['meta_description_length'] < 50:
                result['warnings'].append(f"Description too short: {result['meta_description_length']} chars")
                result['optimizations'].append("Expand description to 50-160 characters")
            else:
                result['warnings'].append(f"Description too long: {result['meta_description_length']} chars")
                result['optimizations'].append("Shorten description to 50-160 characters")
        else:
            result['errors'].append("Missing meta description")
            result['optimizations'].append("Add a meta description with key information")
        
        # ===== HEADINGS =====
        h1_tags = soup.find_all('h1')
        result['h1_count'] = len(h1_tags)
        if h1_tags and h1_tags[0].text.strip():
            result['h1_text'] = h1_tags[0].text.strip()
        
        if result['h1_count'] == 1:
            result['successes'].append(f"Single H1: {result['h1_text'][:50]}")
            result['content_score'] += 10
        elif result['h1_count'] == 0:
            result['errors'].append("No H1 heading found")
            result['optimizations'].append("Add an H1 heading with primary keyword")
        else:
            result['warnings'].append(f"Multiple H1 tags: {result['h1_count']} found")
            result['optimizations'].append("Use only one H1 tag per page")
        
        result['h2_count'] = len(soup.find_all('h2'))
        result['h3_count'] = len(soup.find_all('h3'))
        result['h4_count'] = len(soup.find_all('h4'))
        result['h5_count'] = len(soup.find_all('h5'))
        result['h6_count'] = len(soup.find_all('h6'))
        
        if result['h2_count'] > 0:
            result['successes'].append(f"{result['h2_count']} H2 headings found")
        else:
            result['warnings'].append("No H2 headings found")
            result['optimizations'].append("Add H2 headings to structure content")
        
        # ===== CONTENT =====
        for script in soup(["script", "style"]):
            script.decompose()
        
        text = soup.get_text(separator=' ', strip=True)
        words = re.findall(r'\b[a-zA-Z0-9]+(?:\'[a-zA-Z]+)?\b', text)
        result['total_words'] = len(words)
        
        paragraphs = soup.find_all('p')
        result['paragraph_count'] = len(paragraphs)
        
        sentences = re.split(r'[.!?]+', text)
        result['sentence_count'] = len([s for s in sentences if len(s.strip()) > 10])
        
        if result['total_words'] > 300:
            result['successes'].append(f"Good content: {result['total_words']} words")
            result['content_score'] += 15
            if result['total_words'] > 1000:
                result['successes'].append("Excellent content length (1000+ words)")
                result['content_score'] += 5
        elif result['total_words'] > 100:
            result['warnings'].append(f"Thin content: {result['total_words']} words (recommend 300+)")
            result['optimizations'].append("Add more content, aim for 300+ words")
        else:
            result['errors'].append(f"Very thin content: {result['total_words']} words")
            result['optimizations'].append("Significantly expand content to 300+ words")
        
        # Readability
        if result['sentence_count'] > 0 and result['total_words'] > 0:
            avg_words_per_sentence = result['total_words'] / result['sentence_count']
            if 10 <= avg_words_per_sentence <= 20:
                result['successes'].append("Good readability")
                result['readability_score'] = 85
            elif avg_words_per_sentence < 10:
                result['warnings'].append("Sentences may be too short")
                result['readability_score'] = 60
            else:
                result['warnings'].append("Sentences may be too long")
                result['readability_score'] = 50
                result['optimizations'].append("Break up long sentences for better readability")
        
        # Top Keywords
        stop_words = {'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i', 'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at', 'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she', 'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their', 'what', 'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go', 'me', 'when', 'can', 'like', 'just', 'know', 'see', 'your', 'our', 'them', 'than', 'then', 'now', 'look', 'come', 'think', 'also', 'back', 'after', 'use', 'two', 'how', 'our', 'well', 'way', 'even', 'new', 'want', 'because', 'any', 'these', 'give', 'day', 'most', 'us'}
        content_words = [w.lower() for w in words if w.lower() not in stop_words and len(w) > 3]
        word_freq = Counter(content_words)
        result['top_keywords'] = word_freq.most_common(10)
        
        # ===== LINKS =====
        all_links = soup.find_all('a', href=True)
        result['total_links'] = len(all_links)
        
        internal = 0
        external = 0
        nofollow = 0
        anchor_texts = []
        
        for link in all_links:
            href = link.get('href', '')
            rel = link.get('rel', [])
            anchor = link.text.strip()
            
            if anchor:
                anchor_texts.append({
                    'text': anchor[:50],
                    'url': href[:100]
                })
            
            if 'nofollow' in rel:
                nofollow += 1
            
            if href:
                if href.startswith('http'):
                    if urlparse(href).netloc == base_domain:
                        internal += 1
                    else:
                        external += 1
                elif href.startswith('/') or href.startswith('#'):
                    internal += 1
                elif href.startswith('//'):
                    if urlparse('https:' + href).netloc == base_domain:
                        internal += 1
                    else:
                        external += 1
        
        result['internal_links'] = internal
        result['external_links'] = external
        result['nofollow_links'] = nofollow
        result['anchor_texts'] = anchor_texts[:20]
        
        if result['total_links'] > 0:
            result['successes'].append(f"{result['total_links']} links found")
            result['link_score'] += 10
        else:
            result['warnings'].append("No links found")
            result['optimizations'].append("Add internal and external links")
        
        if internal > 5:
            result['successes'].append(f"Good internal linking: {internal} links")
            result['link_score'] += 5
        else:
            result['warnings'].append(f"Few internal links: {internal}")
            result['optimizations'].append("Add more internal links to other pages")
        
        # Broken Links
        if all_links:
            broken_urls = []
            for link in all_links[:15]:
                href = link.get('href', '')
                if href and href.startswith('http'):
                    try:
                        resp = requests.head(href, timeout=5, allow_redirects=True, verify=False)
                        if resp.status_code >= 400:
                            broken_urls.append({'url': href[:80], 'status': resp.status_code})
                    except:
                        broken_urls.append({'url': href[:80], 'status': 'Error'})
            
            result['broken_links'] = broken_urls
            result['broken_links_count'] = len(broken_urls)
            
            if result['broken_links_count'] > 0:
                result['errors'].append(f"{result['broken_links_count']} broken links found")
                result['optimizations'].append("Fix broken links by updating or removing them")
                result['link_score'] -= 10
            else:
                result['successes'].append("No broken links detected")
        
        # ===== IMAGES - FIXED: Only count content images =====
        all_images = soup.find_all('img')
        result['total_images'] = len(all_images)
        
        content_images = []
        icon_images = []
        content_with_alt = 0
        content_without_alt = 0
        all_with_alt = 0
        all_without_alt = 0
        missing_alt_list = []
        
        for img in all_images:
            alt = img.get('alt', '').strip()
            
            # Count all images with/without alt
            if alt:
                all_with_alt += 1
            else:
                all_without_alt += 1
            
            # Check if it's a content image
            if is_content_image(img):
                content_images.append(img)
                if alt:
                    content_with_alt += 1
                else:
                    content_without_alt += 1
                    src = img.get('src', '')
                    if src:
                        missing_alt_list.append(f"Content image missing alt: {src[:60]}")
            else:
                icon_images.append(img)
        
        result['content_images'] = len(content_images)
        result['icon_images'] = len(icon_images)
        result['images_with_alt'] = all_with_alt
        result['images_without_alt'] = all_without_alt
        result['content_images_with_alt'] = content_with_alt
        result['content_images_without_alt'] = content_without_alt
        result['missing_alt_list'] = missing_alt_list[:10]
        
        # Image SEO scoring (based on CONTENT images only)
        if result['content_images'] > 0:
            alt_percentage = (content_with_alt / result['content_images']) * 100
            if alt_percentage == 100:
                result['successes'].append(f"All {result['content_images']} content images have alt text")
                result['image_score'] += 20
            elif alt_percentage >= 80:
                result['successes'].append(f"{content_with_alt}/{result['content_images']} content images have alt text")
                result['image_score'] += 15
                result['warnings'].append(f"{content_without_alt} content images missing alt text")
                result['optimizations'].append("Add alt text to content images")
            else:
                result['warnings'].append(f"Only {content_with_alt}/{result['content_images']} content images have alt text")
                result['optimizations'].append("Add alt text to all content images")
                result['image_score'] += 5
        else:
            result['successes'].append("No content images found (or all are icons)")
            result['image_score'] += 10
        
        # Warn about too many icon images
        if result['icon_images'] > 20:
            result['warnings'].append(f"{result['icon_images']} icon images detected - consider using CSS/icon fonts instead")
            result['optimizations'].append("Replace decorative icons with CSS or SVG sprites")
        
        # ===== SCHEMA =====
        schema_scripts = soup.find_all('script', attrs={'type': 'application/ld+json'})
        if schema_scripts:
            result['has_schema'] = True
            schema_types = []
            for script in schema_scripts:
                try:
                    if script.string:
                        data = json.loads(script.string)
                        if isinstance(data, dict):
                            schema_type = data.get('@type', '')
                            if schema_type:
                                schema_types.append(schema_type)
                        elif isinstance(data, list):
                            for item in data:
                                if isinstance(item, dict):
                                    schema_type = item.get('@type', '')
                                    if schema_type:
                                        schema_types.append(schema_type)
                except:
                    pass
            
            result['schema_types'] = list(set(schema_types))[:5]
            if result['schema_types']:
                result['successes'].append(f"Schema found: {', '.join(result['schema_types'])}")
                result['technical_score'] += 10
        else:
            result['warnings'].append("No schema markup found")
            result['optimizations'].append("Add schema markup for better rich snippets")
        
        # ===== OPEN GRAPH =====
        og_title = soup.find('meta', attrs={'property': 'og:title'})
        og_desc = soup.find('meta', attrs={'property': 'og:description'})
        og_image = soup.find('meta', attrs={'property': 'og:image'})
        og_url = soup.find('meta', attrs={'property': 'og:url'})
        
        if og_title or og_desc or og_image:
            result['has_og'] = True
            result['og_title'] = og_title.get('content', '') if og_title else ''
            result['og_description'] = og_desc.get('content', '') if og_desc else ''
            result['og_image'] = og_image.get('content', '') if og_image else ''
            result['og_url'] = og_url.get('content', '') if og_url else ''
            result['successes'].append("Open Graph tags present")
            result['technical_score'] += 10
        else:
            result['warnings'].append("Missing Open Graph tags")
            result['optimizations'].append("Add Open Graph tags for social sharing")
        
        # ===== TWITTER CARDS =====
        twitter_card = soup.find('meta', attrs={'name': 'twitter:card'})
        twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})
        twitter_desc = soup.find('meta', attrs={'name': 'twitter:description'})
        
        if twitter_card:
            result['has_twitter'] = True
            result['twitter_card'] = twitter_card.get('content', '')
            result['twitter_title'] = twitter_title.get('content', '') if twitter_title else ''
            result['twitter_description'] = twitter_desc.get('content', '') if twitter_desc else ''
            result['successes'].append("Twitter Card tags present")
            result['technical_score'] += 5
        else:
            result['warnings'].append("Missing Twitter Card tags")
            result['optimizations'].append("Add Twitter Cards for better sharing")
        
        # ===== TECHNICAL =====
        viewport = soup.find('meta', attrs={'name': 'viewport'})
        if viewport:
            result['has_viewport'] = True
            result['is_mobile_friendly'] = True
            result['successes'].append("Viewport found - mobile friendly")
            result['technical_score'] += 10
        else:
            result['errors'].append("Missing viewport meta tag")
            result['optimizations'].append("Add viewport meta tag for mobile responsiveness")
        
        canonical = soup.find('link', attrs={'rel': 'canonical'})
        if canonical:
            result['has_canonical'] = True
            result['canonical_url'] = canonical.get('href', '')
            result['successes'].append("Canonical tag found")
            result['technical_score'] += 5
        else:
            result['warnings'].append("No canonical tag found")
            result['optimizations'].append("Add canonical tag to avoid duplicate content")
        
        html_tag = soup.find('html')
        if html_tag and html_tag.get('lang'):
            result['has_language'] = True
            result['language'] = html_tag.get('lang')
            result['successes'].append(f"Language: {result['language']}")
            result['technical_score'] += 5
        else:
            result['warnings'].append("No language attribute")
            result['optimizations'].append("Add lang attribute to html tag")
        
        robots = soup.find('meta', attrs={'name': 'robots'})
        if robots:
            result['has_robots'] = True
            result['robots_content'] = robots.get('content', '')
            result['successes'].append(f"Robots: {result['robots_content']}")
        
        # ===== PERFORMANCE =====
        result['css_count'] = len(soup.find_all('link', rel='stylesheet'))
        result['js_count'] = len(soup.find_all('script', src=True))
        
        lazy_images = soup.find_all('img', loading='lazy')
        if lazy_images:
            result['has_lazy_loading'] = True
            result['successes'].append("Lazy loading enabled")
        else:
            result['warnings'].append("No lazy loading detected")
            result['optimizations'].append("Implement lazy loading for images")
        
        # ===== SECURITY =====
        scripts = soup.find_all('script', src=True)
        for script in scripts:
            src = script.get('src', '')
            if src.startswith('http://') and url.startswith('https://'):
                result['has_mixed_content'] = True
                result['errors'].append("Mixed content detected")
                result['optimizations'].append("Update mixed content to HTTPS")
                break
        
        if result['has_ssl']:
            result['successes'].append("SSL/HTTPS enabled")
            result['technical_score'] += 10
        else:
            result['errors'].append("No SSL certificate")
            result['optimizations'].append("Install SSL certificate for HTTPS")
        
        # ===== FINAL SCORE =====
        result['meta_score'] = min(100, result['meta_score'])
        result['content_score'] = min(100, result['content_score'] + (10 if result['total_words'] > 500 else 0))
        result['link_score'] = min(100, result['link_score'] + (5 if result['internal_links'] > 10 else 0))
        result['image_score'] = min(100, result['image_score'])
        result['technical_score'] = min(100, result['technical_score'])
        
        total_score = (
            result['meta_score'] * 0.25 +
            result['content_score'] * 0.20 +
            result['link_score'] * 0.15 +
            result['image_score'] * 0.10 +
            result['technical_score'] * 0.30
        )
        
        result['score'] = round(total_score, 0)
        
        # ===== SEVERITY =====
        if len(result['errors']) > 5:
            result['severity'].append("CRITICAL: Many errors need immediate attention")
        elif len(result['errors']) > 2:
            result['severity'].append("WARNING: Fix errors to improve SEO")
        
        if result['score'] < 50:
            result['severity'].append("POOR: Significant optimization needed")
        elif result['score'] < 70:
            result['severity'].append("AVERAGE: Some optimization needed")
        elif result['score'] < 85:
            result['severity'].append("GOOD: Minor improvements possible")
        else:
            result['severity'].append("EXCELLENT: Well optimized!")
        
    except Exception as e:
        result['errors'].append(f"Error: {str(e)}")
    
    return result

# ============ AUTO IMPORT SITES ============
def auto_import_sites():
    if not os.path.exists('sites.txt'):
        with open('sites.txt', 'w') as f:
            f.write("https://google.com\n")
            f.write("https://github.com\n")
            f.write("https://wikipedia.org\n")
            f.write("https://stackoverflow.com\n")
            f.write("https://bbc.com\n")
    
    if not st.session_state.initialized:
        try:
            with open('sites.txt', 'r') as f:
                for line in f:
                    url = line.strip()
                    if url and not url.startswith('#'):
                        if not url.startswith('http'):
                            url = 'https://' + url
                        if url not in st.session_state.sites:
                            st.session_state.sites.append(url)
            st.session_state.initialized = True
        except:
            pass

auto_import_sites()

# ============ MAIN APP ============
st.title("🔍 Complete SEO Audit + Optimization Checker")
st.markdown("**Full SEO analysis with optimization suggestions**")
st.markdown("---")

with st.sidebar:
    st.header("📋 Site Management")
    st.metric("Total Sites", len(st.session_state.sites))
    st.metric("Audited", len(st.session_state.results))
    st.markdown("---")
    
    new_url = st.text_input("➕ Add Site", placeholder="example.com")
    if st.button("Add Site", use_container_width=True):
        if new_url:
            if not new_url.startswith('http'):
                new_url = 'https://' + new_url
            if new_url not in st.session_state.sites:
                st.session_state.sites.append(new_url)
                with open('sites.txt', 'a') as f:
                    f.write(f"\n{new_url}")
                st.rerun()
    
    if st.button("🧹 Clear All", use_container_width=True):
        st.session_state.sites = []
        st.session_state.results = {}
        st.rerun()

tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🔍 Full SEO Audit", "⚡ Optimization Checker", "📈 Reports"])

with tab1:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Sites", len(st.session_state.sites))
    with col2:
        st.metric("Analyzed", len(st.session_state.results))
    with col3:
        total_errors = sum(len(r.get('errors', [])) for r in st.session_state.results.values())
        st.metric("Total Issues", total_errors)
    with col4:
        avg = 0
        if st.session_state.results:
            avg = sum(r.get('score', 0) for r in st.session_state.results.values()) / len(st.session_state.results)
        st.metric("Avg Score", f"{avg:.1f}/100")
    
    if st.session_state.results:
        df_data = []
        for site, r in st.session_state.results.items():
            df_data.append({
                'Site': site.replace('https://', '')[:30],
                'Score': r.get('score', 0),
                'Errors': len(r.get('errors', [])),
                'Warnings': len(r.get('warnings', [])),
                'Words': r.get('total_words', 0),
                'Content Images': r.get('content_images', 0),
                'Title': r.get('title', '')[:30],
                'Status': '✅' if r.get('is_accessible') else '❌'
            })
        st.dataframe(pd.DataFrame(df_data), use_container_width=True, hide_index=True)

with tab2:
    st.header("🔍 Run Full SEO Audit")
    if st.button("🚀 Audit All Sites", type="primary"):
        if st.session_state.sites:
            progress = st.progress(0)
            status = st.empty()
            total = len(st.session_state.sites)
            for i, url in enumerate(st.session_state.sites):
                status.text(f"Auditing {i+1}/{total}: {url}")
                result = complete_seo_audit(url)
                st.session_state.results[url] = result
                progress.progress((i + 1) / total)
                time.sleep(0.5)
            st.success("✅ Audit complete!")
            st.rerun()
        else:
            st.warning("No sites to audit")
    
    if st.session_state.results:
        for url, result in st.session_state.results.items():
            with st.expander(f"🔍 {url.replace('https://', '')}", expanded=False):
                if not result.get('is_accessible'):
                    st.error(f"❌ Failed to load: {result.get('errors', ['Unknown'])[0]}")
                    continue
                
                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    st.metric("Score", f"{result.get('score', 0)}/100")
                with col2:
                    st.metric("Errors", len(result.get('errors', [])))
                with col3:
                    st.metric("Warnings", len(result.get('warnings', [])))
                with col4:
                    st.metric("Status", result.get('status_code', 'N/A'))
                with col5:
                    st.metric("Load Time", f"{result.get('response_time', 0)}s")
                
                st.markdown("---")
                st.write("### 📝 Meta Tags")
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Title:** {result.get('title', '')}")
                    st.write(f"**Title Length:** {result.get('title_length', 0)} chars")
                with col2:
                    st.write(f"**Description:** {result.get('meta_description', '')}")
                    st.write(f"**Description Length:** {result.get('meta_description_length', 0)} chars")
                
                st.markdown("---")
                st.write("### 📑 Headings")
                col1, col2, col3, col4, col5, col6 = st.columns(6)
                with col1: st.metric("H1", result.get('h1_count', 0))
                with col2: st.metric("H2", result.get('h2_count', 0))
                with col3: st.metric("H3", result.get('h3_count', 0))
                with col4: st.metric("H4", result.get('h4_count', 0))
                with col5: st.metric("H5", result.get('h5_count', 0))
                with col6: st.metric("H6", result.get('h6_count', 0))
                
                st.markdown("---")
                st.write("### 📄 Content")
                col1, col2, col3 = st.columns(3)
                with col1: st.metric("Words", result.get('total_words', 0))
                with col2: st.metric("Paragraphs", result.get('paragraph_count', 0))
                with col3: st.metric("Readability", f"{result.get('readability_score', 0)}%")
                
                if result.get('top_keywords'):
                    st.write("**Top Keywords:**")
                    keywords_str = ", ".join([f"{word} ({count})" for word, count in result['top_keywords'][:5]])
                    st.write(keywords_str)
                
                st.markdown("---")
                st.write("### 🔗 Links")
                col1, col2, col3, col4, col5 = st.columns(5)
                with col1: st.metric("Total", result.get('total_links', 0))
                with col2: st.metric("Internal", result.get('internal_links', 0))
                with col3: st.metric("External", result.get('external_links', 0))
                with col4: st.metric("Nofollow", result.get('nofollow_links', 0))
                with col5: st.metric("Broken", result.get('broken_links_count', 0))
                
                if result.get('broken_links'):
                    st.warning("⚠️ Broken Links:")
                    for bl in result['broken_links'][:5]:
                        st.write(f"- {bl['url']} (Status: {bl['status']})")
                
                st.markdown("---")
                st.write("### 🖼️ Images")
                col1, col2, col3, col4 = st.columns(4)
                with col1: st.metric("Total Images", result.get('total_images', 0))
                with col2: st.metric("Content Images", result.get('content_images', 0))
                with col3: st.metric("Icon Images", result.get('icon_images', 0))
                with col4: st.metric("Content with Alt", f"{result.get('content_images_with_alt', 0)}/{result.get('content_images', 0)}")
                
                if result.get('missing_alt_list'):
                    st.warning("⚠️ Content images missing alt text:")
                    for img in result['missing_alt_list'][:5]:
                        st.write(f"- {img}")
                
                st.markdown("---")
                st.write("### 🏷️ Schema & Social")
                col1, col2 = st.columns(2)
                with col1:
                    if result.get('has_schema'):
                        st.success(f"✅ Schema: {', '.join(result.get('schema_types', []))}")
                    else:
                        st.warning("⚠️ No schema")
                with col2:
                    if result.get('has_og'):
                        st.success("✅ Open Graph")
                    else:
                        st.warning("⚠️ No OG tags")

with tab3:
    st.header("⚡ Optimization Checker")
    st.markdown("**Find issues that need optimization and get actionable suggestions**")
    
    if st.session_state.results:
        for url, result in st.session_state.results.items():
            if result.get('is_accessible'):
                with st.expander(f"🔧 {url.replace('https://', '')}", expanded=True):
                    score = result.get('score', 0)
                    
                    if score >= 85:
                        st.success(f"⭐ EXCELLENT: {score}/100")
                    elif score >= 70:
                        st.success(f"🟢 GOOD: {score}/100")
                    elif score >= 50:
                        st.warning(f"🟡 AVERAGE: {score}/100")
                    else:
                        st.error(f"🔴 POOR: {score}/100")
                    
                    st.markdown("---")
                    
                    if result.get('severity'):
                        for s in result['severity']:
                            st.write(f"**{s}**")
                    
                    st.markdown("---")
                    
                    if result.get('errors'):
                        st.error("### ❌ Critical Issues To Fix")
                        for err in result['errors'][:10]:
                            st.write(f"- {err}")
                    
                    if result.get('warnings'):
                        st.warning("### ⚠️ Warnings To Address")
                        for warn in result['warnings'][:10]:
                            st.write(f"- {warn}")
                    
                    if result.get('optimizations'):
                        st.info("### 📝 Optimization Suggestions")
                        for opt in result['optimizations'][:10]:
                            st.write(f"- {opt}")
                    
                    st.markdown("---")
                    st.write("### 📊 Score Breakdown")
                    col1, col2, col3, col4, col5 = st.columns(5)
                    with col1:
                        st.metric("Meta", f"{result.get('meta_score', 0)}%")
                    with col2:
                        st.metric("Content", f"{result.get('content_score', 0)}%")
                    with col3:
                        st.metric("Links", f"{result.get('link_score', 0)}%")
                    with col4:
                        st.metric("Images", f"{result.get('image_score', 0)}%")
                    with col5:
                        st.metric("Technical", f"{result.get('technical_score', 0)}%")
    else:
        st.info("Run an SEO audit first to get optimization suggestions")

with tab4:
    st.header("📈 Reports")
    
    if st.session_state.results:
        data = []
        for url, result in st.session_state.results.items():
            data.append({
                'Site': url.replace('https://', ''),
                'Score': result.get('score', 0),
                'Errors': len(result.get('errors', [])),
                'Warnings': len(result.get('warnings', [])),
                'Meta Score': result.get('meta_score', 0),
                'Content Score': result.get('content_score', 0),
                'Link Score': result.get('link_score', 0),
                'Image Score': result.get('image_score', 0),
                'Technical Score': result.get('technical_score', 0),
                'Words': result.get('total_words', 0),
                'Title': result.get('title', '')[:40],
                'Internal Links': result.get('internal_links', 0),
                'External Links': result.get('external_links', 0),
                'Broken Links': result.get('broken_links_count', 0),
                'Total Images': result.get('total_images', 0),
                'Content Images': result.get('content_images', 0),
                'Icon Images': result.get('icon_images', 0),
                'Content Images with Alt': result.get('content_images_with_alt', 0),
                'Schema': '✅' if result.get('has_schema') else '❌',
                'OG Tags': '✅' if result.get('has_og') else '❌',
                'Mobile Friendly': '✅' if result.get('is_mobile_friendly') else '❌',
                'SSL': '✅' if result.get('has_ssl') else '❌',
                'Accessible': '✅' if result.get('is_accessible') else '❌'
            })
        
        df = pd.DataFrame(data)
        df = df.sort_values('Score', ascending=False)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        col1, col2 = st.columns(2)
        with col1:
            csv = df.to_csv(index=False)
            st.download_button(
                "📥 Download Full SEO Report (CSV)",
                data=csv,
                file_name=f"seo_audit_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            st.write("**📊 Summary Statistics:**")
            st.write(f"- Total Sites: {len(df)}")
            st.write(f"- Average Score: {df['Score'].mean():.1f}/100")
            st.write(f"- Sites with Errors: {df[df['Errors'] > 0].shape[0]}")
            st.write(f"- Average Words: {df['Words'].mean():.0f}")
            st.write(f"- Total Broken Links: {df['Broken Links'].sum()}")
            st.write(f"- Total Content Images: {df['Content Images'].sum()}")
    else:
        st.info("Run an SEO audit first to generate reports")

st.markdown("---")
st.caption(f"🔄 Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.caption(f"📊 Total Sites: {len(st.session_state.sites)} | Audited: {len(st.session_state.results)}")
st.caption("🚀 Complete SEO Audit + Optimization Checker | All 50+ Metrics")
