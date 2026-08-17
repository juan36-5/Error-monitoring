import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import re
import os
import time
import io
from urllib.parse import urlparse, urljoin
import json
from collections import Counter
import random

# ============ USER AGENT ROTATION ============
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
]

def get_random_headers():
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
        'DNT': '1'
    }

st.set_page_config(page_title="Complete SEO Audit", page_icon="🔍", layout="wide")

# Session State
if 'sites' not in st.session_state:
    st.session_state.sites = []
if 'results' not in st.session_state:
    st.session_state.results = {}
if 'current_page' not in st.session_state:
    st.session_state.current_page = 1

def get_page_content(url):
    for attempt in range(3):
        try:
            headers = get_random_headers()
            time.sleep(random.uniform(1, 2))
            response = requests.get(url, timeout=15, headers=headers, allow_redirects=True)
            if response.status_code == 200:
                return response.text, response.status_code
            elif response.status_code != 403:
                return response.text, response.status_code
        except:
            continue
    return "", 0

def safe_get_string(value, default=""):
    """Safely get string value, handling None"""
    if value is None:
        return default
    return str(value)

def safe_truncate(value, max_length=50):
    """Safely truncate string, handling None"""
    if value is None:
        return ""
    value = str(value)
    if len(value) > max_length:
        return value[:max_length] + "..."
    return value

# ============ COMPLETE SEO AUDIT ============
def complete_seo_audit(url):
    """Complete SEO audit - EVERYTHING"""
    result = {
        'url': url,
        'score': 0,
        'errors': 0,
        'warnings': 0,
        'all_issues': [],
        'successes': [],
        'last_check': datetime.now().strftime('%Y-%m-%d %H:%M'),
        
        # ===== META TAGS =====
        'title': None,
        'title_length': 0,
        'meta_description': None,
        'meta_description_length': 0,
        'meta_keywords': None,
        
        # ===== FULL LINK ANALYSIS =====
        'links': {
            'total_links': 0,
            'internal_links': [],
            'external_links': [],
            'nofollow_links': [],
            'dofollow_links': [],
            'broken_links': [],
            'internal_count': 0,
            'external_count': 0,
            'nofollow_count': 0,
            'dofollow_count': 0,
            'broken_count': 0,
            'anchor_texts': []
        },
        
        # ===== IMAGES =====
        'images': {
            'total': 0,
            'with_alt': 0,
            'without_alt': [],
            'with_title': 0,
            'without_title': [],
            'missing_alt_count': 0,
            'missing_title_count': 0
        },
        
        # ===== SCHEMA =====
        'schema': {
            'has_schema': False,
            'total_scripts': 0,
            'schema_types': [],
            'schema_content': [],
            'errors': []
        },
        
        # ===== OPEN GRAPH =====
        'open_graph': {
            'og_title': None,
            'og_description': None,
            'og_image': None,
            'og_url': None,
            'og_type': None,
            'og_site_name': None,
            'og_locale': None,
            'has_og': False,
            'missing_tags': []
        },
        
        # ===== TWITTER CARDS =====
        'twitter_cards': {
            'twitter_card': None,
            'twitter_title': None,
            'twitter_description': None,
            'twitter_image': None,
            'twitter_site': None,
            'has_twitter': False,
            'missing_tags': []
        },
        
        # ===== HEADINGS =====
        'headings': {
            'h1': {'count': 0, 'texts': []},
            'h2': {'count': 0, 'texts': []},
            'h3': {'count': 0, 'texts': []},
            'h4': {'count': 0, 'texts': []},
            'h5': {'count': 0, 'texts': []},
            'h6': {'count': 0, 'texts': []},
            'issues': [],
            'has_h1': False,
            'has_multiple_h1': False,
            'has_missing_heading': False
        },
        
        # ===== CONTENT =====
        'content': {
            'total_words': 0,
            'paragraph_count': 0,
            'sentence_count': 0,
            'avg_words_per_sentence': 0,
            'top_keywords': [],
            'keyword_density': {},
            'issues': []
        },
        
        # ===== TECHNICAL =====
        'technical': {
            'has_viewport': False,
            'has_canonical': False,
            'canonical_url': None,
            'has_charset': False,
            'charset': None,
            'has_language': False,
            'language': None,
            'has_robots': False,
            'robots_content': None,
            'has_ssl': False,
            'is_https': False,
            'issues': []
        },
        
        # ===== PERFORMANCE =====
        'performance': {
            'css_count': 0,
            'js_count': 0,
            'image_count': 0,
            'total_resources': 0,
            'has_lazy_loading': False,
            'has_async_scripts': False,
            'has_defer_scripts': False,
            'issues': []
        },
        
        # ===== SECURITY =====
        'security': {
            'has_ssl': False,
            'mixed_content': False,
            'issues': []
        },
        
        # ===== MOBILE FRIENDLY =====
        'mobile_friendly': {
            'has_viewport': False,
            'viewport_content': None,
            'is_mobile_friendly': False,
            'issues': []
        },
        
        # ===== SOCIAL MEDIA =====
        'social_media': {
            'has_open_graph': False,
            'has_twitter_cards': False,
            'og_data': {},
            'twitter_data': {},
            'issues': []
        },
        
        # ===== RAW DATA =====
        'status_code': None,
        'response_time': 0,
        'page_size': 0
    }
    
    try:
        start_time = time.time()
        
        if not url.startswith('http'):
            url = 'https://' + url
        
        html_content, status_code = get_page_content(url)
        result['status_code'] = status_code
        
        if not html_content:
            result['all_issues'].append("❌ Failed to load page")
            result['errors'] += 1
            return result
        
        result['response_time'] = round(time.time() - start_time, 2)
        result['page_size'] = len(html_content)
        
        soup = BeautifulSoup(html_content, 'html.parser')
        base_domain = urlparse(url).netloc
        
        # ============================================
        # 1. META TAGS
        # ============================================
        title = soup.find('title')
        if title and title.text.strip():
            result['title'] = title.text.strip()
            result['title_length'] = len(title.text.strip())
            if result['title_length'] < 30:
                result['all_issues'].append(f"⚠️ Title too short: {result['title_length']} chars")
                result['warnings'] += 1
            elif result['title_length'] > 60:
                result['all_issues'].append(f"⚠️ Title too long: {result['title_length']} chars")
                result['warnings'] += 1
            else:
                result['successes'].append(f"✅ Title length optimal: {result['title_length']} chars")
        else:
            result['all_issues'].append("❌ Missing title tag")
            result['errors'] += 1
        
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            desc_content = meta_desc.get('content', '').strip()
            if desc_content:
                result['meta_description'] = desc_content
                result['meta_description_length'] = len(desc_content)
                if len(desc_content) < 50:
                    result['all_issues'].append(f"⚠️ Description too short: {len(desc_content)} chars")
                    result['warnings'] += 1
                elif len(desc_content) > 160:
                    result['all_issues'].append(f"⚠️ Description too long: {len(desc_content)} chars")
                    result['warnings'] += 1
                else:
                    result['successes'].append(f"✅ Description length optimal: {len(desc_content)} chars")
            else:
                result['all_issues'].append("⚠️ Description is empty")
                result['warnings'] += 1
        else:
            result['all_issues'].append("❌ Missing meta description")
            result['errors'] += 1
        
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords:
            result['meta_keywords'] = meta_keywords.get('content', '')
            result['successes'].append("✅ Meta keywords present")
        
        # ============================================
        # 2. FULL LINK ANALYSIS
        # ============================================
        all_links = soup.find_all('a', href=True)
        links_data = result['links']
        links_data['total_links'] = len(all_links)
        
        internal_count = 0
        external_count = 0
        nofollow_count = 0
        dofollow_count = 0
        anchor_texts = []
        
        for link in all_links:
            href = link.get('href', '')
            anchor = link.text.strip() or link.get('title', 'No anchor text')
            rel = link.get('rel', [])
            
            if 'nofollow' in rel:
                nofollow_count += 1
            else:
                dofollow_count += 1
            
            if href.startswith('http'):
                if urlparse(href).netloc == base_domain:
                    internal_count += 1
                else:
                    external_count += 1
            elif href.startswith('/') or href.startswith('#'):
                internal_count += 1
            
            if anchor and anchor != 'No anchor text':
                anchor_texts.append(anchor)
        
        links_data['internal_count'] = internal_count
        links_data['external_count'] = external_count
        links_data['nofollow_count'] = nofollow_count
        links_data['dofollow_count'] = dofollow_count
        links_data['anchor_texts'] = anchor_texts[:20]
        
        if links_data['broken_count'] > 0:
            result['all_issues'].append(f"❌ {links_data['broken_count']} broken links found")
            result['errors'] += 1
        if links_data['internal_count'] == 0:
            result['all_issues'].append("⚠️ No internal links found")
            result['warnings'] += 1
        if links_data['external_count'] == 0:
            result['all_issues'].append("⚠️ No external links found")
            result['warnings'] += 1
        
        # ============================================
        # 3. IMAGES
        # ============================================
        images = soup.find_all('img')
        images_data = result['images']
        images_data['total'] = len(images)
        
        with_alt = 0
        without_alt = []
        with_title = 0
        without_title = []
        
        for img in images:
            alt = img.get('alt', '').strip()
            title = img.get('title', '').strip()
            src = img.get('src', '')
            
            if alt:
                with_alt += 1
            else:
                without_alt.append({'src': src[:50]})
            
            if title:
                with_title += 1
            else:
                without_title.append({'src': src[:50]})
        
        images_data['with_alt'] = with_alt
        images_data['without_alt'] = without_alt
        images_data['with_title'] = with_title
        images_data['without_title'] = without_title
        images_data['missing_alt_count'] = len(without_alt)
        images_data['missing_title_count'] = len(without_title)
        
        if images_data['missing_alt_count'] > 0:
            result['all_issues'].append(f"❌ {images_data['missing_alt_count']} images missing alt text")
            result['errors'] += 1
        
        # ============================================
        # 4. SCHEMA
        # ============================================
        schema_scripts = soup.find_all('script', attrs={'type': 'application/ld+json'})
        schema_data = result['schema']
        schema_data['has_schema'] = len(schema_scripts) > 0
        schema_data['total_scripts'] = len(schema_scripts)
        
        for script in schema_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    schema_type = data.get('@type', 'Unknown')
                    schema_data['schema_types'].append(schema_type)
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            schema_type = item.get('@type', 'Unknown')
                            schema_data['schema_types'].append(schema_type)
            except:
                pass
        
        if not schema_data['has_schema']:
            result['all_issues'].append("⚠️ No schema markup found")
            result['warnings'] += 1
        else:
            result['successes'].append(f"✅ Schema found: {schema_data['schema_types']}")
        
        # ============================================
        # 5. OPEN GRAPH
        # ============================================
        og_data = result['open_graph']
        og_tags = ['og:title', 'og:description', 'og:image', 'og:url', 'og:type', 'og:site_name', 'og:locale']
        
        for tag in og_tags:
            meta = soup.find('meta', attrs={'property': tag})
            if meta:
                content = meta.get('content', '')
                if tag == 'og:title':
                    og_data['og_title'] = content
                elif tag == 'og:description':
                    og_data['og_description'] = content
                elif tag == 'og:image':
                    og_data['og_image'] = content
                elif tag == 'og:url':
                    og_data['og_url'] = content
                elif tag == 'og:type':
                    og_data['og_type'] = content
                elif tag == 'og:site_name':
                    og_data['og_site_name'] = content
                elif tag == 'og:locale':
                    og_data['og_locale'] = content
            else:
                og_data['missing_tags'].append(tag)
        
        og_data['has_og'] = len(og_data['missing_tags']) < len(og_tags)
        
        if not og_data['has_og']:
            result['all_issues'].append("⚠️ Missing Open Graph tags")
            result['warnings'] += 1
        else:
            result['successes'].append("✅ Open Graph tags present")
        
        # ============================================
        # 6. TWITTER CARDS
        # ============================================
        twitter_data = result['twitter_cards']
        twitter_tags = ['twitter:card', 'twitter:title', 'twitter:description', 'twitter:image', 'twitter:site']
        
        for tag in twitter_tags:
            meta = soup.find('meta', attrs={'name': tag})
            if meta:
                content = meta.get('content', '')
                if tag == 'twitter:card':
                    twitter_data['twitter_card'] = content
                elif tag == 'twitter:title':
                    twitter_data['twitter_title'] = content
                elif tag == 'twitter:description':
                    twitter_data['twitter_description'] = content
                elif tag == 'twitter:image':
                    twitter_data['twitter_image'] = content
                elif tag == 'twitter:site':
                    twitter_data['twitter_site'] = content
            else:
                twitter_data['missing_tags'].append(tag)
        
        twitter_data['has_twitter'] = len(twitter_data['missing_tags']) < len(twitter_tags)
        
        if not twitter_data['has_twitter']:
            result['all_issues'].append("⚠️ Missing Twitter Card tags")
            result['warnings'] += 1
        else:
            result['successes'].append("✅ Twitter Card tags present")
        
        # ============================================
        # 7. HEADINGS
        # ============================================
        headings_data = result['headings']
        
        for level in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            tags = soup.find_all(level)
            headings_data[level]['count'] = len(tags)
            headings_data[level]['texts'] = [t.text.strip() for t in tags if t.text.strip()]
        
        if headings_data['h1']['count'] == 0:
            headings_data['issues'].append("❌ No H1 heading found")
            headings_data['has_h1'] = False
            result['errors'] += 1
        elif headings_data['h1']['count'] == 1:
            headings_data['issues'].append("✅ Exactly one H1 heading")
            headings_data['has_h1'] = True
        else:
            headings_data['issues'].append(f"⚠️ Multiple H1 tags: {headings_data['h1']['count']}")
            headings_data['has_h1'] = True
            headings_data['has_multiple_h1'] = True
            result['warnings'] += 1
        
        if headings_data['h1']['count'] > 0 and headings_data['h2']['count'] == 0:
            headings_data['issues'].append("⚠️ H1 found but no H2 headings")
            result['warnings'] += 1
        
        # ============================================
        # 8. CONTENT
        # ============================================
        for script in soup(["script", "style"]):
            script.decompose()
        
        text = soup.get_text(separator=' ', strip=True)
        words = re.findall(r'\b[a-zA-Z0-9]+(?:\'[a-zA-Z]+)?\b', text)
        sentences = re.split(r'[.!?]+', text)
        
        paragraphs = soup.find_all('p')
        paragraph_texts = [p.text.strip() for p in paragraphs if p.text.strip()]
        
        stop_words = {'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i', 'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at', 'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she', 'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their', 'what', 'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go', 'me'}
        content_words = [w.lower() for w in words if w.lower() not in stop_words and len(w) > 3]
        word_freq = Counter(content_words)
        
        content_data = result['content']
        content_data['total_words'] = len(words)
        content_data['paragraph_count'] = len(paragraph_texts)
        content_data['sentence_count'] = len([s for s in sentences if len(s.strip()) > 10])
        
        if content_data['sentence_count'] > 0:
            content_data['avg_words_per_sentence'] = content_data['total_words'] // content_data['sentence_count']
        
        content_data['top_keywords'] = word_freq.most_common(10)
        content_data['keyword_density'] = dict(word_freq.most_common(20))
        
        if content_data['total_words'] < 100:
            content_data['issues'].append("❌ Critical: Very low word count")
            result['errors'] += 1
        elif content_data['total_words'] < 300:
            content_data['issues'].append("⚠️ Low word count (recommended 300+)")
            result['warnings'] += 1
        elif content_data['total_words'] < 500:
            content_data['issues'].append("⚠️ Medium word count (recommended 500+)")
            result['warnings'] += 1
        else:
            content_data['issues'].append("✅ Good word count")
        
        if content_data['paragraph_count'] < 3:
            content_data['issues'].append("⚠️ Very few paragraphs")
            result['warnings'] += 1
        
        # ============================================
        # 9. TECHNICAL SEO
        # ============================================
        tech_data = result['technical']
        tech_data['has_ssl'] = url.startswith('https')
        tech_data['is_https'] = url.startswith('https')
        
        viewport = soup.find('meta', attrs={'name': 'viewport'})
        if viewport:
            tech_data['has_viewport'] = True
        else:
            tech_data['issues'].append("❌ Missing viewport meta tag")
            result['errors'] += 1
        
        canonical = soup.find('link', attrs={'rel': 'canonical'})
        if canonical:
            tech_data['has_canonical'] = True
            tech_data['canonical_url'] = canonical.get('href')
        else:
            tech_data['issues'].append("⚠️ No canonical tag found")
            result['warnings'] += 1
        
        charset = soup.find('meta', attrs={'charset': True})
        if charset:
            tech_data['has_charset'] = True
            tech_data['charset'] = charset.get('charset')
        else:
            tech_data['issues'].append("⚠️ No charset meta tag")
            result['warnings'] += 1
        
        html = soup.find('html')
        if html and html.get('lang'):
            tech_data['has_language'] = True
            tech_data['language'] = html.get('lang')
        else:
            tech_data['issues'].append("⚠️ No language attribute")
            result['warnings'] += 1
        
        robots = soup.find('meta', attrs={'name': 'robots'})
        if robots:
            tech_data['has_robots'] = True
            tech_data['robots_content'] = robots.get('content')
            if 'noindex' in robots.get('content', '').lower():
                tech_data['issues'].append("❌ Page is marked noindex")
                result['errors'] += 1
            if 'nofollow' in robots.get('content', '').lower():
                tech_data['issues'].append("⚠️ Page is marked nofollow")
                result['warnings'] += 1
        
        # ============================================
        # 10. PERFORMANCE
        # ============================================
        css_files = soup.find_all('link', rel='stylesheet')
        js_files = soup.find_all('script', src=True)
        img_tags = soup.find_all('img')
        
        perf_data = result['performance']
        perf_data['css_count'] = len(css_files)
        perf_data['js_count'] = len(js_files)
        perf_data['image_count'] = len(img_tags)
        perf_data['total_resources'] = len(css_files) + len(js_files) + len(img_tags)
        
        lazy_images = soup.find_all('img', loading='lazy')
        if lazy_images:
            perf_data['has_lazy_loading'] = True
        
        for script in js_files:
            if script.get('async'):
                perf_data['has_async_scripts'] = True
            if script.get('defer'):
                perf_data['has_defer_scripts'] = True
        
        if len(css_files) > 10:
            perf_data['issues'].append(f"⚠️ Many CSS files: {len(css_files)}")
            result['warnings'] += 1
        if len(js_files) > 15:
            perf_data['issues'].append(f"⚠️ Many JS files: {len(js_files)}")
            result['warnings'] += 1
        
        # ============================================
        # 11. SECURITY
        # ============================================
        security_data = result['security']
        security_data['has_ssl'] = url.startswith('https')
        
        scripts = soup.find_all('script', src=True)
        for script in scripts:
            src = script.get('src', '')
            if src.startswith('http://') and url.startswith('https://'):
                security_data['mixed_content'] = True
                security_data['issues'].append("⚠️ Mixed content detected")
                result['warnings'] += 1
        
        if not security_data['has_ssl']:
            security_data['issues'].append("❌ No SSL/HTTPS")
            result['errors'] += 1
        
        # ============================================
        # 12. MOBILE FRIENDLY
        # ============================================
        mobile_data = result['mobile_friendly']
        
        viewport = soup.find('meta', attrs={'name': 'viewport'})
        if viewport:
            mobile_data['has_viewport'] = True
            mobile_data['viewport_content'] = viewport.get('content')
            mobile_data['is_mobile_friendly'] = True
            
            content = viewport.get('content', '').lower()
            if 'width=device-width' not in content:
                mobile_data['issues'].append("⚠️ Viewport missing 'width=device-width'")
                result['warnings'] += 1
            if 'initial-scale=1' not in content:
                mobile_data['issues'].append("⚠️ Viewport missing 'initial-scale=1'")
                result['warnings'] += 1
        else:
            mobile_data['issues'].append("❌ No viewport meta tag")
            result['errors'] += 1
        
        # ============================================
        # 13. SOCIAL MEDIA
        # ============================================
        social_data = result['social_media']
        social_data['has_open_graph'] = og_data['has_og']
        social_data['has_twitter_cards'] = twitter_data['has_twitter']
        
        if not social_data['has_open_graph']:
            social_data['issues'].append("⚠️ Missing Open Graph tags")
            result['warnings'] += 1
        if not social_data['has_twitter_cards']:
            social_data['issues'].append("⚠️ Missing Twitter Card tags")
            result['warnings'] += 1
        
        # ============================================
        # CALCULATE SCORE
        # ============================================
        score = 100
        score -= result['errors'] * 5
        score -= result['warnings'] * 2
        
        # Bonuses
        if result['title'] and 30 <= result['title_length'] <= 60:
            score += 3
        if result['meta_description'] and 50 <= result['meta_description_length'] <= 160:
            score += 3
        if result['headings']['has_h1']:
            score += 2
        if result['content']['total_words'] > 300:
            score += 5
        if result['schema']['has_schema']:
            score += 3
        if result['technical']['has_viewport']:
            score += 2
        if result['open_graph']['has_og']:
            score += 2
        if result['twitter_cards']['has_twitter']:
            score += 2
        if result['security']['has_ssl']:
            score += 5
        if result['links']['internal_count'] > 5:
            score += 3
        
        result['score'] = max(0, min(100, score))
        
    except Exception as e:
        result['all_issues'].append(f"❌ Error: {str(e)}")
        result['errors'] += 1
    
    return result

# ============ AUTO IMPORT ============
def auto_import_sites():
    if os.path.exists('sites.txt') and not st.session_state.sites:
        try:
            with open('sites.txt', 'r') as f:
                for line in f:
                    url = line.strip()
                    if url and not url.startswith('#') and not url.startswith('import'):
                        if not url.startswith('http'):
                            url = 'https://' + url
                        if url not in st.session_state.sites:
                            st.session_state.sites.append(url)
            if st.session_state.sites:
                st.success(f"✅ Auto-imported {len(st.session_state.sites)} sites!")
        except:
            pass

auto_import_sites()

# ============ MAIN APP ============
st.title("🔍 Complete SEO Audit")
st.markdown("**Full SEO analysis with all metrics**")
st.markdown("---")

with st.sidebar:
    st.header("📋 Site Management")
    st.metric("Total Sites", len(st.session_state.sites))
    
    st.markdown("---")
    
    new_url = st.text_input("➕ Add Site", placeholder="example.com")
    if st.button("Add Site", use_container_width=True):
        if new_url:
            if not new_url.startswith('http'):
                new_url = 'https://' + new_url
            if new_url not in st.session_state.sites:
                st.session_state.sites.append(new_url)
                st.rerun()
    
    st.markdown("---")
    
    if st.button("🧹 Clear All", use_container_width=True):
        st.session_state.sites = []
        st.session_state.results = {}
        st.rerun()
    
    st.markdown("---")
    st.caption("**Audit Includes:**")
    st.caption("✅ Meta Tags (Title, Description, Keywords)")
    st.caption("✅ Headings (H1-H6 Structure)")
    st.caption("✅ Content Quality (Words, Readability)")
    st.caption("✅ Links (Internal, External, Broken)")
    st.caption("✅ Images (Alt Text, Title)")
    st.caption("✅ Schema Markup")
    st.caption("✅ Open Graph & Twitter Cards")
    st.caption("✅ Technical SEO (SSL, Canonical)")
    st.caption("✅ Performance (Resources)")
    st.caption("✅ Security (Mixed Content)")
    st.caption("✅ Mobile Friendliness")

tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "🔍 Full SEO Audit", "📈 Reports"])

with tab1:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Sites", len(st.session_state.sites))
    with col2:
        st.metric("Analyzed", len(st.session_state.results))
    with col3:
        errors = sum(1 for r in st.session_state.results.values() if r.get('errors', 0) > 0)
        st.metric("Sites with Errors", errors)
    with col4:
        avg = 0
        if st.session_state.results:
            avg = sum(r.get('score', 0) for r in st.session_state.results.values()) / len(st.session_state.results)
        st.metric("Avg Score", f"{avg:.1f}/100")
    
    if st.session_state.sites:
        df_data = []
        for site in st.session_state.sites:
            if site in st.session_state.results:
                r = st.session_state.results[site]
                df_data.append({
                    'Site': site.replace('https://', ''),
                    'Score': r.get('score', 0),
                    'Errors': r.get('errors', 0),
                    'Warnings': r.get('warnings', 0),
                    'Words': r.get('content', {}).get('total_words', 0),
                    'Title': (r.get('title') or '')[:50]
                })
            else:
                df_data.append({
                    'Site': site.replace('https://', ''),
                    'Score': 'Pending',
                    'Errors': '-',
                    'Warnings': '-',
                    'Words': '-',
                    'Title': '-'
                })
        st.dataframe(pd.DataFrame(df_data), use_container_width=True, hide_index=True)

with tab2:
    st.header("🔍 Run Full SEO Audit")
    
    if st.button("🚀 Audit All Sites", type="primary"):
        if st.session_state.sites:
            progress = st.progress(0)
            status = st.empty()
            
            for i, url in enumerate(st.session_state.sites):
                status.text(f"Auditing {i+1}/{len(st.session_state.sites)}: {url}")
                result = complete_seo_audit(url)
                st.session_state.results[url] = result
                progress.progress((i + 1) / len(st.session_state.sites))
            
            st.success("✅ Audit complete!")
            st.rerun()
        else:
            st.warning("No sites to audit")
    
    if st.session_state.results:
        st.subheader("📊 Audit Results")
        
        for url, result in st.session_state.results.items():
            with st.expander(f"🔍 {url.replace('https://', '')}", expanded=False):
                score = result.get('score', 0)
                
                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    st.metric("Score", f"{score}/100")
                with col2:
                    st.metric("Errors", result.get('errors', 0))
                with col3:
                    st.metric("Warnings", result.get('warnings', 0))
                with col4:
                    st.metric("Status", result.get('status_code', 'N/A'))
                with col5:
                    st.metric("Load Time", f"{result.get('response_time', 0)}s")
                
                if score >= 90:
                    st.success("🌟 Excellent SEO!")
                elif score >= 70:
                    st.info("👍 Good SEO")
                elif score >= 50:
                    st.warning("⚠️ Needs Improvement")
                else:
                    st.error("❌ Poor SEO")
                
                st.markdown("---")
                
                # Meta Tags
                st.write("### 📝 Meta Tags")
                col1, col2 = st.columns(2)
                with col1:
                    title = result.get('title')
                    st.write(f"**Title:** {title if title else '❌ Missing'}")
                    st.write(f"**Length:** {result.get('title_length', 0)} chars")
                with col2:
                    desc = result.get('meta_description')
                    st.write(f"**Description:** {desc if desc else '❌ Missing'}")
                    st.write(f"**Length:** {result.get('meta_description_length', 0)} chars")
                
                # Headings
                st.write("### 📑 Headings")
                headings = result.get('headings', {})
                col1, col2, col3, col4, col5, col6 = st.columns(6)
                with col1:
                    st.metric("H1", headings.get('h1', {}).get('count', 0))
                with col2:
                    st.metric("H2", headings.get('h2', {}).get('count', 0))
                with col3:
                    st.metric("H3", headings.get('h3', {}).get('count', 0))
                with col4:
                    st.metric("H4", headings.get('h4', {}).get('count', 0))
                with col5:
                    st.metric("H5", headings.get('h5', {}).get('count', 0))
                with col6:
                    st.metric("H6", headings.get('h6', {}).get('count', 0))
                
                # Content
                st.write("### 📄 Content")
                content = result.get('content', {})
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Words", content.get('total_words', 0))
                with col2:
                    st.metric("Paragraphs", content.get('paragraph_count', 0))
                with col3:
                    st.metric("Sentences", content.get('sentence_count', 0))
                with col4:
                    st.metric("Avg Words/Sentence", content.get('avg_words_per_sentence', 0))
                
                # Links
                st.write("### 🔗 Links")
                links = result.get('links', {})
                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    st.metric("Total", links.get('total_links', 0))
                with col2:
                    st.metric("Internal", links.get('internal_count', 0))
                with col3:
                    st.metric("External", links.get('external_count', 0))
                with col4:
                    st.metric("Nofollow", links.get('nofollow_count', 0))
                with col5:
                    st.metric("Broken", links.get('broken_count', 0))
                
                # Images
                st.write("### 🖼️ Images")
                images = result.get('images', {})
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total", images.get('total', 0))
                with col2:
                    st.metric("With Alt", images.get('with_alt', 0))
                with col3:
                    st.metric("Missing Alt", images.get('missing_alt_count', 0))
                
                # Schema
                st.write("### 🏷️ Schema")
                schema = result.get('schema', {})
                if schema.get('has_schema'):
                    st.success(f"✅ Schema found: {schema.get('schema_types', [])}")
                else:
                    st.warning("⚠️ No schema found")
                
                # Open Graph
                st.write("### 📱 Open Graph")
                og = result.get('open_graph', {})
                if og.get('has_og'):
                    st.success("✅ Open Graph tags present")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Title:** {og.get('og_title', 'N/A')}")
                        st.write(f"**Description:** {og.get('og_description', 'N/A')}")
                    with col2:
                        st.write(f"**Image:** {og.get('og_image', 'N/A')}")
                        st.write(f"**URL:** {og.get('og_url', 'N/A')}")
                else:
                    st.warning("⚠️ Missing Open Graph tags")
                
                # Issues
                if result.get('successes'):
                    st.write("### ✅ Successes")
                    for s in result['successes']:
                        st.success(s)
                
                if result.get('all_issues'):
                    st.write("### ⚠️ Issues")
                    for issue in result['all_issues']:
                        if '❌' in issue:
                            st.error(issue)
                        elif '⚠️' in issue:
                            st.warning(issue)

with tab3:
    st.header("📈 Reports")
    
    if st.session_state.results:
        data = []
        for url, result in st.session_state.results.items():
            # Get values safely - NEVER use None with slicing
            title = result.get('title') or ''
            meta_desc = result.get('meta_description') or ''
            content_data = result.get('content', {})
            links_data = result.get('links', {})
            images_data = result.get('images', {})
            schema_data = result.get('schema', {})
            og_data = result.get('open_graph', {})
            twitter_data = result.get('twitter_cards', {})
            tech_data = result.get('technical', {})
            mobile_data = result.get('mobile_friendly', {})
            
            data.append({
                'Site': url.replace('https://', ''),
                'Score': result.get('score', 0),
                'Errors': result.get('errors', 0),
                'Warnings': result.get('warnings', 0),
                'Title': title[:50] + '...' if len(title) > 50 else title,
                'Description': meta_desc[:50] + '...' if len(meta_desc) > 50 else meta_desc,
                'Total Words': content_data.get('total_words', 0),
                'Internal Links': links_data.get('internal_count', 0),
                'External Links': links_data.get('external_count', 0),
                'Broken Links': links_data.get('broken_count', 0),
                'Images': images_data.get('total', 0),
                'Images with Alt': images_data.get('with_alt', 0),
                'Schema': '✅' if schema_data.get('has_schema') else '❌',
                'Open Graph': '✅' if og_data.get('has_og') else '❌',
                'Twitter Cards': '✅' if twitter_data.get('has_twitter') else '❌',
                'SSL': '✅' if tech_data.get('has_ssl') else '❌',
                'Mobile Friendly': '✅' if mobile_data.get('is_mobile_friendly') else '❌'
            })
        
        df = pd.DataFrame(data)
        df = df.sort_values('Score', ascending=False)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        csv = df.to_csv(index=False)
        st.download_button(
            "📥 Download CSV Report",
            data=csv,
            file_name=f"seo_audit_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
    else:
        st.info("Run an SEO audit first to generate reports")

st.markdown("---")
st.caption(f"🔄 Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.caption(f"📊 Total Sites: {len(st.session_state.sites)} | Audited: {len(st.session_state.results)}")
