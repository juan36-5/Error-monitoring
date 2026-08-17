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
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ============ USER AGENT ROTATION ============
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1'
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
        'DNT': '1',
        'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"'
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
    """Get page content with multiple fallback methods"""
    methods = ['standard', 'firefox', 'mobile', 'no_verify']
    
    for method in methods:
        for attempt in range(2):
            try:
                headers = get_random_headers()
                
                if method == 'firefox':
                    headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0'
                elif method == 'mobile':
                    headers['User-Agent'] = 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1'
                
                time.sleep(random.uniform(1, 2))
                
                if method == 'no_verify':
                    response = requests.get(url, timeout=20, headers=headers, allow_redirects=True, verify=False)
                else:
                    response = requests.get(url, timeout=20, headers=headers, allow_redirects=True)
                
                if response.status_code == 200:
                    return response.text, response.status_code
                elif response.status_code == 403:
                    continue
                else:
                    return response.text, response.status_code
                    
            except:
                continue
    
    return "", 0

# ============ ANALYZE ANCHOR TEXTS ============
def analyze_anchor_texts(soup):
    """Complete anchor text analysis"""
    all_links = soup.find_all('a', href=True)
    
    anchor_data = {
        'total_anchors': len(all_links),
        'anchors_with_text': 0,
        'empty_anchors': 0,
        'anchor_texts': [],
        'anchor_text_lengths': [],
        'common_anchor_words': [],
        'nofollow_anchors': 0,
        'dofollow_anchors': 0,
        'external_anchor_texts': [],
        'internal_anchor_texts': [],
        'anchor_text_density': {}
    }
    
    anchor_texts = []
    for link in all_links:
        anchor = link.text.strip()
        rel = link.get('rel', [])
        href = link.get('href', '')
        
        if anchor:
            anchor_data['anchors_with_text'] += 1
            anchor_texts.append(anchor)
            anchor_data['anchor_text_lengths'].append(len(anchor))
            
            # Check if external
            if href.startswith('http'):
                if urlparse(href).netloc != urlparse(link.base_url).netloc if hasattr(link, 'base_url') else False:
                    anchor_data['external_anchor_texts'].append(anchor)
                else:
                    anchor_data['internal_anchor_texts'].append(anchor)
        else:
            anchor_data['empty_anchors'] += 1
        
        if 'nofollow' in rel:
            anchor_data['nofollow_anchors'] += 1
        else:
            anchor_data['dofollow_anchors'] += 1
    
    anchor_data['anchor_texts'] = anchor_texts[:20]  # First 20 anchors
    
    # Common anchor words
    all_words = ' '.join(anchor_texts).split()
    word_freq = Counter([w.lower() for w in all_words if len(w) > 3])
    anchor_data['common_anchor_words'] = word_freq.most_common(10)
    anchor_data['anchor_text_density'] = dict(word_freq.most_common(20))
    
    return anchor_data

# ============ ANALYZE BROKEN LINKS ============
def analyze_broken_links(soup, max_check=20):
    """Complete broken link analysis"""
    all_links = soup.find_all('a', href=True)
    
    broken_data = {
        'total_checked': 0,
        'broken_links': [],
        'working_links': 0,
        'broken_count': 0,
        'broken_percentage': 0,
        'broken_status_codes': {}
    }
    
    checked = 0
    for link in all_links[:max_check]:
        href = link.get('href', '')
        if href.startswith('http://') or href.startswith('https://'):
            checked += 1
            try:
                resp = requests.head(href, timeout=3, allow_redirects=True)
                if resp.status_code >= 400:
                    broken_data['broken_links'].append({
                        'href': href,
                        'status': resp.status_code,
                        'anchor': link.text.strip()[:50] if link.text.strip() else '(empty)',
                        'title': link.get('title', '')
                    })
                    broken_data['broken_count'] += 1
                    status_key = str(resp.status_code)
                    if status_key not in broken_data['broken_status_codes']:
                        broken_data['broken_status_codes'][status_key] = 0
                    broken_data['broken_status_codes'][status_key] += 1
                else:
                    broken_data['working_links'] += 1
            except:
                broken_data['broken_links'].append({
                    'href': href,
                    'status': 'Error',
                    'anchor': link.text.strip()[:50] if link.text.strip() else '(empty)',
                    'title': link.get('title', '')
                })
                broken_data['broken_count'] += 1
    
    broken_data['total_checked'] = checked
    if checked > 0:
        broken_data['broken_percentage'] = round((broken_data['broken_count'] / checked) * 100, 2)
    
    return broken_data

# ============ ANALYZE IMAGES COMPLETE ============
def analyze_images_complete(soup):
    """Complete image analysis with all details"""
    images = soup.find_all('img')
    
    images_data = {
        'total': len(images),
        'with_alt': 0,
        'without_alt': [],
        'with_title': 0,
        'without_title': [],
        'with_width': 0,
        'with_height': 0,
        'lazy_loaded': 0,
        'missing_alt_count': 0,
        'missing_title_count': 0,
        'alt_texts': [],
        'image_sources': [],
        'image_details': []
    }
    
    for img in images:
        alt = img.get('alt', '').strip()
        title = img.get('title', '').strip()
        src = img.get('src', '')
        width = img.get('width', '')
        height = img.get('height', '')
        loading = img.get('loading', '')
        
        img_detail = {
            'src': src[:100],
            'alt': alt[:100] if alt else '',
            'title': title[:100] if title else '',
            'width': width,
            'height': height,
            'loading': loading
        }
        images_data['image_details'].append(img_detail)
        
        if alt:
            images_data['with_alt'] += 1
            images_data['alt_texts'].append(alt)
        else:
            images_data['without_alt'].append({'src': src[:100], 'alt': alt})
        
        if title:
            images_data['with_title'] += 1
        else:
            images_data['without_title'].append({'src': src[:100], 'title': title})
        
        if width:
            images_data['with_width'] += 1
        if height:
            images_data['with_height'] += 1
        if loading == 'lazy':
            images_data['lazy_loaded'] += 1
        
        images_data['image_sources'].append(src[:100])
    
    images_data['missing_alt_count'] = len(images_data['without_alt'])
    images_data['missing_title_count'] = len(images_data['without_title'])
    
    return images_data

# ============ ANALYZE SCHEMA COMPLETE ============
def analyze_schema_complete(soup):
    """Complete schema markup analysis"""
    schema_scripts = soup.find_all('script', attrs={'type': 'application/ld+json'})
    
    schema_data = {
        'has_schema': len(schema_scripts) > 0,
        'total_scripts': len(schema_scripts),
        'schema_types': [],
        'schema_content': [],
        'errors': [],
        'schemas_by_type': {},
        'organization_schema': False,
        'product_schema': False,
        'article_schema': False,
        'faq_schema': False,
        'localbusiness_schema': False,
        'breadcrumb_schema': False,
        'review_schema': False,
        'event_schema': False,
        'person_schema': False
    }
    
    for script in schema_scripts:
        try:
            data = json.loads(script.string)
            if isinstance(data, dict):
                schema_type = data.get('@type', 'Unknown')
                if schema_type not in schema_data['schemas_by_type']:
                    schema_data['schemas_by_type'][schema_type] = 0
                schema_data['schemas_by_type'][schema_type] += 1
                schema_data['schema_types'].append(schema_type)
                schema_data['schema_content'].append({
                    'type': schema_type,
                    'data': json.dumps(data, indent=2)[:500]
                })
                
                # Check specific schema types
                if 'Organization' in schema_type:
                    schema_data['organization_schema'] = True
                elif 'Product' in schema_type:
                    schema_data['product_schema'] = True
                elif 'Article' in schema_type or 'NewsArticle' in schema_type:
                    schema_data['article_schema'] = True
                elif 'FAQ' in schema_type:
                    schema_data['faq_schema'] = True
                elif 'LocalBusiness' in schema_type:
                    schema_data['localbusiness_schema'] = True
                elif 'Breadcrumb' in schema_type:
                    schema_data['breadcrumb_schema'] = True
                elif 'Review' in schema_type:
                    schema_data['review_schema'] = True
                elif 'Event' in schema_type:
                    schema_data['event_schema'] = True
                elif 'Person' in schema_type:
                    schema_data['person_schema'] = True
                    
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        schema_type = item.get('@type', 'Unknown')
                        if schema_type not in schema_data['schemas_by_type']:
                            schema_data['schemas_by_type'][schema_type] = 0
                        schema_data['schemas_by_type'][schema_type] += 1
                        schema_data['schema_types'].append(schema_type)
        except Exception as e:
            schema_data['errors'].append(str(e))
    
    return schema_data

# ============ ANALYZE OPEN GRAPH COMPLETE ============
def analyze_open_graph_complete(soup):
    """Complete Open Graph analysis"""
    og_data = {
        'og_title': None,
        'og_description': None,
        'og_image': None,
        'og_url': None,
        'og_type': None,
        'og_site_name': None,
        'og_locale': None,
        'og_updated_time': None,
        'og_published_time': None,
        'og_audio': None,
        'og_video': None,
        'og_determiner': None,
        'has_og': False,
        'missing_tags': [],
        'all_og_tags': {}
    }
    
    og_tags = {
        'og:title': 'og_title',
        'og:description': 'og_description',
        'og:image': 'og_image',
        'og:url': 'og_url',
        'og:type': 'og_type',
        'og:site_name': 'og_site_name',
        'og:locale': 'og_locale',
        'og:updated_time': 'og_updated_time',
        'og:published_time': 'og_published_time',
        'og:audio': 'og_audio',
        'og:video': 'og_video',
        'og:determiner': 'og_determiner'
    }
    
    for tag, key in og_tags.items():
        meta = soup.find('meta', attrs={'property': tag})
        if meta:
            content = meta.get('content', '')
            og_data[key] = content
            og_data['all_og_tags'][tag] = content
        else:
            og_data['missing_tags'].append(tag)
    
    og_data['has_og'] = len(og_data['missing_tags']) < len(og_tags) - 3  # Allow some missing
    
    return og_data

# ============ ANALYZE TWITTER CARDS COMPLETE ============
def analyze_twitter_cards_complete(soup):
    """Complete Twitter Card analysis"""
    twitter_data = {
        'twitter_card': None,
        'twitter_title': None,
        'twitter_description': None,
        'twitter_image': None,
        'twitter_site': None,
        'twitter_creator': None,
        'twitter_image_alt': None,
        'twitter_app_name': None,
        'twitter_app_id': None,
        'twitter_app_url': None,
        'has_twitter': False,
        'missing_tags': [],
        'all_twitter_tags': {}
    }
    
    twitter_tags = {
        'twitter:card': 'twitter_card',
        'twitter:title': 'twitter_title',
        'twitter:description': 'twitter_description',
        'twitter:image': 'twitter_image',
        'twitter:site': 'twitter_site',
        'twitter:creator': 'twitter_creator',
        'twitter:image:alt': 'twitter_image_alt',
        'twitter:app:name': 'twitter_app_name',
        'twitter:app:id': 'twitter_app_id',
        'twitter:app:url': 'twitter_app_url'
    }
    
    for tag, key in twitter_tags.items():
        meta = soup.find('meta', attrs={'name': tag})
        if meta:
            content = meta.get('content', '')
            twitter_data[key] = content
            twitter_data['all_twitter_tags'][tag] = content
        else:
            twitter_data['missing_tags'].append(tag)
    
    twitter_data['has_twitter'] = len(twitter_data['missing_tags']) < len(twitter_tags) - 3
    
    return twitter_data

# ============ COMPLETE HEADING ANALYSIS ============
def analyze_headings_complete(soup):
    """Complete heading structure analysis"""
    headings = {
        'h1': {'tags': soup.find_all('h1'), 'count': 0, 'texts': [], 'lengths': []},
        'h2': {'tags': soup.find_all('h2'), 'count': 0, 'texts': [], 'lengths': []},
        'h3': {'tags': soup.find_all('h3'), 'count': 0, 'texts': [], 'lengths': []},
        'h4': {'tags': soup.find_all('h4'), 'count': 0, 'texts': [], 'lengths': []},
        'h5': {'tags': soup.find_all('h5'), 'count': 0, 'texts': [], 'lengths': []},
        'h6': {'tags': soup.find_all('h6'), 'count': 0, 'texts': [], 'lengths': []},
        'issues': [],
        'has_h1': False,
        'has_multiple_h1': False,
        'has_missing_heading': False,
        'heading_hierarchy': [],
        'total_headings': 0
    }
    
    for level in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
        tags = headings[level]['tags']
        headings[level]['count'] = len(tags)
        headings[level]['texts'] = [t.text.strip() for t in tags if t.text.strip()]
        headings[level]['lengths'] = [len(t.text.strip()) for t in tags if t.text.strip()]
        headings['total_headings'] += len(tags)
    
    # Check H1
    if headings['h1']['count'] == 0:
        headings['issues'].append("❌ No H1 heading found")
        headings['has_h1'] = False
    elif headings['h1']['count'] == 1:
        headings['issues'].append("✅ Exactly one H1 heading")
        headings['has_h1'] = True
    else:
        headings['issues'].append(f"⚠️ Multiple H1 tags: {headings['h1']['count']}")
        headings['has_h1'] = True
        headings['has_multiple_h1'] = True
    
    # Check H1 length
    if headings['h1']['count'] == 1 and headings['h1']['lengths']:
        h1_len = headings['h1']['lengths'][0]
        if h1_len < 20:
            headings['issues'].append(f"⚠️ H1 too short: {h1_len} chars")
        elif h1_len > 70:
            headings['issues'].append(f"⚠️ H1 too long: {h1_len} chars")
    
    # Check heading hierarchy
    if headings['h1']['count'] > 0 and headings['h2']['count'] == 0:
        headings['issues'].append("⚠️ H1 found but no H2 headings")
    
    if headings['h2']['count'] > 0 and headings['h3']['count'] == 0:
        headings['issues'].append("⚠️ H2 found but no H3 headings")
    
    # Build heading hierarchy
    for level in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
        for text in headings[level]['texts'][:10]:
            headings['heading_hierarchy'].append(f"{level.upper()}: {text[:100]}")
    
    return headings

# ============ COMPLETE CONTENT ANALYSIS ============
def analyze_content_complete(soup):
    """Complete content quality analysis"""
    for script in soup(["script", "style"]):
        script.decompose()
    
    text = soup.get_text(separator=' ', strip=True)
    words = re.findall(r'\b[a-zA-Z0-9]+(?:\'[a-zA-Z]+)?\b', text)
    sentences = re.split(r'[.!?]+', text)
    
    paragraphs = soup.find_all('p')
    paragraph_texts = [p.text.strip() for p in paragraphs if p.text.strip()]
    paragraph_lengths = [len(p.text.strip()) for p in paragraphs if p.text.strip()]
    
    stop_words = {'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i', 'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at', 'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she', 'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their', 'what', 'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go', 'me'}
    content_words = [w.lower() for w in words if w.lower() not in stop_words and len(w) > 3]
    word_freq = Counter(content_words)
    
    content_data = {
        'total_words': len(words),
        'unique_words': len(set([w.lower() for w in words])),
        'paragraph_count': len(paragraph_texts),
        'paragraph_lengths': paragraph_lengths,
        'avg_paragraph_length': sum(paragraph_lengths) / len(paragraph_lengths) if paragraph_lengths else 0,
        'sentence_count': len([s for s in sentences if len(s.strip()) > 10]),
        'avg_words_per_sentence': len(words) // len([s for s in sentences if len(s.strip()) > 10]) if len([s for s in sentences if len(s.strip()) > 10]) > 0 else 0,
        'top_keywords': word_freq.most_common(20),
        'keyword_density': dict(word_freq.most_common(30)),
        'issues': [],
        'readability_score': 0
    }
    
    # Readability score
    if content_data['sentence_count'] > 0 and content_data['total_words'] > 0:
        avg_sentence_length = content_data['total_words'] / content_data['sentence_count']
        if avg_sentence_length < 10:
            content_data['readability_score'] = 90
        elif avg_sentence_length < 15:
            content_data['readability_score'] = 80
        elif avg_sentence_length < 20:
            content_data['readability_score'] = 70
        elif avg_sentence_length < 25:
            content_data['readability_score'] = 60
        elif avg_sentence_length < 30:
            content_data['readability_score'] = 50
        else:
            content_data['readability_score'] = 40
    
    # Content quality scoring
    if content_data['total_words'] < 100:
        content_data['issues'].append("❌ Critical: Very low word count (< 100)")
    elif content_data['total_words'] < 300:
        content_data['issues'].append("⚠️ Low word count (100-300, recommended 300+)")
    elif content_data['total_words'] < 500:
        content_data['issues'].append("⚠️ Medium word count (300-500, recommended 500+)")
    elif content_data['total_words'] < 800:
        content_data['issues'].append("✅ Good word count (500-800)")
    else:
        content_data['issues'].append("✅ Excellent word count (800+)")
    
    if content_data['paragraph_count'] < 3:
        content_data['issues'].append("⚠️ Very few paragraphs (< 3)")
    
    return content_data

# ============ COMPLETE TECHNICAL ANALYSIS ============
def analyze_technical_complete(soup, url, response_time, page_size, status_code):
    """Complete technical SEO analysis"""
    tech_data = {
        'has_viewport': False,
        'viewport_content': None,
        'has_canonical': False,
        'canonical_url': None,
        'has_charset': False,
        'charset': None,
        'has_language': False,
        'language': None,
        'has_robots': False,
        'robots_content': None,
        'has_ssl': url.startswith('https'),
        'is_https': url.startswith('https'),
        'status_code': status_code,
        'response_time': response_time,
        'page_size': page_size,
        'page_size_kb': round(page_size / 1024, 2) if page_size else 0,
        'has_sitemap': False,
        'sitemap_url': None,
        'has_robots_txt': False,
        'robots_txt_content': None,
        'has_favicon': False,
        'favicon_url': None,
        'has_hreflang': False,
        'hreflang_tags': [],
        'issues': [],
        'good_practices': []
    }
    
    # Viewport
    viewport = soup.find('meta', attrs={'name': 'viewport'})
    if viewport:
        tech_data['has_viewport'] = True
        tech_data['viewport_content'] = viewport.get('content')
        tech_data['good_practices'].append("✅ Viewport meta tag found")
    else:
        tech_data['issues'].append("❌ Missing viewport meta tag")
    
    # Canonical
    canonical = soup.find('link', attrs={'rel': 'canonical'})
    if canonical and canonical.get('href'):
        tech_data['has_canonical'] = True
        tech_data['canonical_url'] = canonical.get('href')
        tech_data['good_practices'].append(f"✅ Canonical tag found: {tech_data['canonical_url'][:100]}")
    else:
        tech_data['issues'].append("⚠️ No canonical tag found")
    
    # Charset
    charset = soup.find('meta', attrs={'charset': True})
    if charset:
        tech_data['has_charset'] = True
        tech_data['charset'] = charset.get('charset')
        tech_data['good_practices'].append(f"✅ Charset found: {tech_data['charset']}")
    else:
        tech_data['issues'].append("⚠️ No charset meta tag")
    
    # Language
    html = soup.find('html')
    if html and html.get('lang'):
        tech_data['has_language'] = True
        tech_data['language'] = html.get('lang')
        tech_data['good_practices'].append(f"✅ Language attribute: {tech_data['language']}")
    else:
        tech_data['issues'].append("⚠️ No language attribute")
    
    # Robots
    robots = soup.find('meta', attrs={'name': 'robots'})
    if robots:
        tech_data['has_robots'] = True
        tech_data['robots_content'] = robots.get('content')
        content_lower = robots.get('content', '').lower()
        if 'noindex' in content_lower:
            tech_data['issues'].append("❌ Page is marked noindex")
        if 'nofollow' in content_lower:
            tech_data['issues'].append("⚠️ Page is marked nofollow")
    else:
        tech_data['good_practices'].append("✅ No robots meta restrictions")
    
    # SSL
    if tech_data['has_ssl']:
        tech_data['good_practices'].append("✅ SSL/HTTPS enabled")
    else:
        tech_data['issues'].append("❌ No SSL/HTTPS")
    
    # Favicon
    favicon = soup.find('link', attrs={'rel': 'icon'}) or soup.find('link', attrs={'rel': 'shortcut icon'})
    if favicon:
        tech_data['has_favicon'] = True
        tech_data['favicon_url'] = favicon.get('href')
        tech_data['good_practices'].append("✅ Favicon found")
    else:
        tech_data['issues'].append("⚠️ No favicon found")
    
    # Hreflang
    hreflang_tags = soup.find_all('link', attrs={'rel': 'alternate', 'hreflang': True})
    if hreflang_tags:
        tech_data['has_hreflang'] = True
        for tag in hreflang_tags:
            tech_data['hreflang_tags'].append({
                'hreflang': tag.get('hreflang'),
                'href': tag.get('href')
            })
        tech_data['good_practices'].append(f"✅ Hreflang tags found: {len(hreflang_tags)}")
    
    # Check robots.txt
    try:
        base_url = url.split('/')[0] + '//' + url.split('/')[2]
        robots_url = base_url + '/robots.txt'
        robots_response = requests.get(robots_url, timeout=3)
        if robots_response.status_code == 200:
            tech_data['has_robots_txt'] = True
            tech_data['robots_txt_content'] = robots_response.text[:500]
            tech_data['good_practices'].append("✅ Robots.txt found")
    except:
        pass
    
    # Check sitemap.xml
    try:
        base_url = url.split('/')[0] + '//' + url.split('/')[2]
        sitemap_url = base_url + '/sitemap.xml'
        sitemap_response = requests.get(sitemap_url, timeout=3)
        if sitemap_response.status_code == 200:
            tech_data['has_sitemap'] = True
            tech_data['sitemap_url'] = sitemap_url
            tech_data['good_practices'].append("✅ Sitemap.xml found")
    except:
        pass
    
    return tech_data

# ============ COMPLETE PERFORMANCE ANALYSIS ============
def analyze_performance_complete(soup):
    """Complete performance analysis"""
    css_files = soup.find_all('link', rel='stylesheet')
    js_files = soup.find_all('script', src=True)
    images = soup.find_all('img')
    
    perf_data = {
        'css_count': len(css_files),
        'css_files': [],
        'js_count': len(js_files),
        'js_files': [],
        'image_count': len(images),
        'total_resources': len(css_files) + len(js_files) + len(images),
        'has_lazy_loading': False,
        'lazy_loaded_images': 0,
        'has_async_scripts': False,
        'async_scripts': 0,
        'has_defer_scripts': False,
        'defer_scripts': 0,
        'inline_css': 0,
        'external_css': 0,
        'inline_js': 0,
        'external_js': 0,
        'issues': [],
        'good_practices': []
    }
    
    for css in css_files:
        href = css.get('href', '')
        if href:
            if href.startswith('http'):
                perf_data['external_css'] += 1
            else:
                perf_data['inline_css'] += 1
            perf_data['css_files'].append(href[:100])
    
    for js in js_files:
        src = js.get('src', '')
        if src:
            if src.startswith('http'):
                perf_data['external_js'] += 1
            else:
                perf_data['inline_js'] += 1
            perf_data['js_files'].append(src[:100])
            
            if js.get('async'):
                perf_data['has_async_scripts'] = True
                perf_data['async_scripts'] += 1
            if js.get('defer'):
                perf_data['has_defer_scripts'] = True
                perf_data['defer_scripts'] += 1
    
    for img in images:
        if img.get('loading') == 'lazy':
            perf_data['has_lazy_loading'] = True
            perf_data['lazy_loaded_images'] += 1
    
    if len(css_files) > 5:
        perf_data['issues'].append(f"⚠️ Many CSS files: {len(css_files)} (recommend < 5)")
    else:
        perf_data['good_practices'].append(f"✅ CSS files: {len(css_files)}")
    
    if len(js_files) > 10:
        perf_data['issues'].append(f"⚠️ Many JS files: {len(js_files)} (recommend < 10)")
    else:
        perf_data['good_practices'].append(f"✅ JS files: {len(js_files)}")
    
    if perf_data['has_lazy_loading']:
        perf_data['good_practices'].append(f"✅ Lazy loading enabled for {perf_data['lazy_loaded_images']} images")
    else:
        perf_data['issues'].append("⚠️ No lazy loading detected")
    
    return perf_data

# ============ COMPLETE SECURITY ANALYSIS ============
def analyze_security_complete(soup, url):
    """Complete security analysis"""
    security_data = {
        'has_ssl': url.startswith('https'),
        'mixed_content': False,
        'mixed_content_resources': [],
        'issues': [],
        'good_practices': []
    }
    
    if security_data['has_ssl']:
        security_data['good_practices'].append("✅ SSL/HTTPS enabled")
    else:
        security_data['issues'].append("❌ No SSL/HTTPS")
    
    # Check mixed content
    scripts = soup.find_all('script', src=True)
    for script in scripts:
        src = script.get('src', '')
        if src.startswith('http://') and url.startswith('https://'):
            security_data['mixed_content'] = True
            security_data['mixed_content_resources'].append(src)
            security_data['issues'].append(f"⚠️ Mixed content: {src[:100]}")
    
    styles = soup.find_all('link', rel='stylesheet')
    for style in styles:
        href = style.get('href', '')
        if href.startswith('http://') and url.startswith('https://'):
            security_data['mixed_content'] = True
            security_data['mixed_content_resources'].append(href)
            security_data['issues'].append(f"⚠️ Mixed content: {href[:100]}")
    
    images = soup.find_all('img', src=True)
    for img in images:
        src = img.get('src', '')
        if src.startswith('http://') and url.startswith('https://'):
            security_data['mixed_content'] = True
            security_data['mixed_content_resources'].append(src)
            security_data['issues'].append(f"⚠️ Mixed content: {src[:100]}")
    
    if not security_data['mixed_content'] and security_data['has_ssl']:
        security_data['good_practices'].append("✅ No mixed content detected")
    
    return security_data

# ============ COMPLETE MOBILE ANALYSIS ============
def analyze_mobile_complete(soup):
    """Complete mobile friendly analysis"""
    mobile_data = {
        'has_viewport': False,
        'viewport_content': None,
        'is_mobile_friendly': False,
        'viewport_issues': [],
        'issues': [],
        'good_practices': []
    }
    
    viewport = soup.find('meta', attrs={'name': 'viewport'})
    if viewport:
        mobile_data['has_viewport'] = True
        mobile_data['viewport_content'] = viewport.get('content')
        mobile_data['is_mobile_friendly'] = True
        mobile_data['good_practices'].append("✅ Viewport meta tag found")
        
        content = viewport.get('content', '').lower()
        if 'width=device-width' not in content:
            mobile_data['viewport_issues'].append("⚠️ Viewport missing 'width=device-width'")
            mobile_data['issues'].append("⚠️ Viewport missing 'width=device-width'")
        if 'initial-scale=1' not in content:
            mobile_data['viewport_issues'].append("⚠️ Viewport missing 'initial-scale=1'")
            mobile_data['issues'].append("⚠️ Viewport missing 'initial-scale=1'")
    else:
        mobile_data['issues'].append("❌ No viewport meta tag (not mobile friendly)")
    
    return mobile_data

# ============ COMPLETE SOCIAL MEDIA ANALYSIS ============
def analyze_social_media_complete(og_data, twitter_data):
    """Complete social media analysis"""
    social_data = {
        'has_open_graph': og_data.get('has_og', False),
        'has_twitter_cards': twitter_data.get('has_twitter', False),
        'og_title': og_data.get('og_title'),
        'og_description': og_data.get('og_description'),
        'og_image': og_data.get('og_image'),
        'twitter_card': twitter_data.get('twitter_card'),
        'twitter_title': twitter_data.get('twitter_title'),
        'twitter_description': twitter_data.get('twitter_description'),
        'twitter_image': twitter_data.get('twitter_image'),
        'issues': [],
        'good_practices': []
    }
    
    if social_data['has_open_graph']:
        social_data['good_practices'].append("✅ Open Graph tags present")
    else:
        social_data['issues'].append("⚠️ Missing Open Graph tags")
    
    if social_data['has_twitter_cards']:
        social_data['good_practices'].append("✅ Twitter Card tags present")
    else:
        social_data['issues'].append("⚠️ Missing Twitter Card tags")
    
    return social_data

# ============ COMPLETE SEO AUDIT ============
def complete_seo_audit(url):
    """Complete SEO audit with ALL metrics"""
    result = {
        'url': url,
        'score': 0,
        'errors': 0,
        'warnings': 0,
        'all_issues': [],
        'successes': [],
        'last_check': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'is_accessible': False,
        'error_message': None,
        'status_code': None,
        'response_time': 0,
        'page_size': 0,
        
        # ===== META TAGS =====
        'title': None,
        'title_length': 0,
        'meta_description': None,
        'meta_description_length': 0,
        'meta_keywords': None,
        
        # ===== ANCHOR TEXTS =====
        'anchor_texts': {
            'total_anchors': 0,
            'anchors_with_text': 0,
            'empty_anchors': 0,
            'anchor_texts': [],
            'common_anchor_words': [],
            'nofollow_anchors': 0,
            'dofollow_anchors': 0
        },
        
        # ===== BROKEN LINKS =====
        'broken_links': {
            'total_checked': 0,
            'broken_count': 0,
            'broken_percentage': 0,
            'broken_links': [],
            'broken_status_codes': {}
        },
        
        # ===== LINKS =====
        'links': {
            'total_links': 0,
            'internal_count': 0,
            'external_count': 0,
            'nofollow_count': 0,
            'dofollow_count': 0,
            'internal_links': [],
            'external_links': []
        },
        
        # ===== IMAGES =====
        'images': {
            'total': 0,
            'with_alt': 0,
            'missing_alt_count': 0,
            'with_title': 0,
            'missing_title_count': 0,
            'lazy_loaded': 0,
            'without_alt': [],
            'without_title': [],
            'alt_texts': []
        },
        
        # ===== SCHEMA =====
        'schema': {
            'has_schema': False,
            'total_scripts': 0,
            'schema_types': [],
            'schemas_by_type': {},
            'organization_schema': False,
            'product_schema': False,
            'article_schema': False,
            'faq_schema': False,
            'localbusiness_schema': False,
            'breadcrumb_schema': False,
            'review_schema': False
        },
        
        # ===== OPEN GRAPH =====
        'open_graph': {
            'has_og': False,
            'og_title': None,
            'og_description': None,
            'og_image': None,
            'og_url': None,
            'og_type': None,
            'og_site_name': None,
            'missing_tags': []
        },
        
        # ===== TWITTER CARDS =====
        'twitter_cards': {
            'has_twitter': False,
            'twitter_card': None,
            'twitter_title': None,
            'twitter_description': None,
            'twitter_image': None,
            'twitter_site': None,
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
            'has_h1': False,
            'total_headings': 0,
            'heading_hierarchy': [],
            'issues': []
        },
        
        # ===== CONTENT =====
        'content': {
            'total_words': 0,
            'unique_words': 0,
            'paragraph_count': 0,
            'avg_paragraph_length': 0,
            'sentence_count': 0,
            'avg_words_per_sentence': 0,
            'top_keywords': [],
            'keyword_density': {},
            'readability_score': 0,
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
            'has_favicon': False,
            'has_hreflang': False,
            'hreflang_tags': [],
            'has_robots_txt': False,
            'has_sitemap': False,
            'sitemap_url': None,
            'issues': [],
            'good_practices': []
        },
        
        # ===== PERFORMANCE =====
        'performance': {
            'css_count': 0,
            'js_count': 0,
            'image_count': 0,
            'total_resources': 0,
            'has_lazy_loading': False,
            'lazy_loaded_images': 0,
            'has_async_scripts': False,
            'async_scripts': 0,
            'has_defer_scripts': False,
            'defer_scripts': 0,
            'issues': [],
            'good_practices': []
        },
        
        # ===== SECURITY =====
        'security': {
            'has_ssl': False,
            'mixed_content': False,
            'mixed_content_resources': [],
            'issues': [],
            'good_practices': []
        },
        
        # ===== MOBILE FRIENDLY =====
        'mobile_friendly': {
            'has_viewport': False,
            'is_mobile_friendly': False,
            'viewport_content': None,
            'issues': [],
            'good_practices': []
        },
        
        # ===== SOCIAL MEDIA =====
        'social_media': {
            'has_open_graph': False,
            'has_twitter_cards': False,
            'og_title': None,
            'og_description': None,
            'og_image': None,
            'twitter_card': None,
            'twitter_title': None,
            'twitter_description': None,
            'issues': [],
            'good_practices': []
        }
    }
    
    try:
        start_time = time.time()
        
        if not url.startswith('http'):
            url = 'https://' + url
        
        html_content, status_code = get_page_content(url)
        result['status_code'] = status_code
        
        if not html_content:
            result['error_message'] = f"Failed to load page (Status: {status_code})"
            result['all_issues'].append(f"❌ Failed to load page - Status: {status_code}")
            result['errors'] += 1
            result['is_accessible'] = False
            return result
        
        result['response_time'] = round(time.time() - start_time, 2)
        result['page_size'] = len(html_content)
        result['is_accessible'] = True
        
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
        # 2. ANCHOR TEXTS ANALYSIS
        # ============================================
        anchor_data = analyze_anchor_texts(soup)
        result['anchor_texts'] = anchor_data
        
        if anchor_data['empty_anchors'] > 0:
            result['all_issues'].append(f"⚠️ {anchor_data['empty_anchors']} empty anchor texts")
            result['warnings'] += 1
        
        # ============================================
        # 3. BROKEN LINKS ANALYSIS
        # ============================================
        broken_data = analyze_broken_links(soup)
        result['broken_links'] = broken_data
        
        if broken_data['broken_count'] > 0:
            result['all_issues'].append(f"❌ {broken_data['broken_count']} broken links found")
            result['errors'] += 1
        
        # ============================================
        # 4. FULL LINK ANALYSIS
        # ============================================
        all_links = soup.find_all('a', href=True)
        links_data = result['links']
        links_data['total_links'] = len(all_links)
        
        internal_count = 0
        external_count = 0
        nofollow_count = 0
        
        for link in all_links:
            href = link.get('href', '')
            rel = link.get('rel', [])
            anchor = link.text.strip() or link.get('title', 'No anchor')
            
            if 'nofollow' in rel:
                nofollow_count += 1
            
            if href.startswith('http'):
                if urlparse(href).netloc == base_domain:
                    internal_count += 1
                    links_data['internal_links'].append({'href': href[:100], 'anchor': anchor[:50]})
                else:
                    external_count += 1
                    links_data['external_links'].append({'href': href[:100], 'anchor': anchor[:50]})
            elif href.startswith('/') or href.startswith('#'):
                internal_count += 1
                links_data['internal_links'].append({'href': href[:100], 'anchor': anchor[:50]})
        
        links_data['internal_count'] = internal_count
        links_data['external_count'] = external_count
        links_data['nofollow_count'] = nofollow_count
        links_data['dofollow_count'] = len(all_links) - nofollow_count
        
        if links_data['internal_count'] == 0:
            result['all_issues'].append("⚠️ No internal links found")
            result['warnings'] += 1
        if links_data['external_count'] == 0:
            result['all_issues'].append("⚠️ No external links found")
            result['warnings'] += 1
        
        # ============================================
        # 5. IMAGES COMPLETE ANALYSIS
        # ============================================
        images_data = analyze_images_complete(soup)
        result['images'] = images_data
        
        if images_data['missing_alt_count'] > 0:
            result['all_issues'].append(f"❌ {images_data['missing_alt_count']} images missing alt text")
            result['errors'] += 1
        
        # ============================================
        # 6. SCHEMA COMPLETE ANALYSIS
        # ============================================
        schema_data = analyze_schema_complete(soup)
        result['schema'] = schema_data
        
        if not schema_data['has_schema']:
            result['all_issues'].append("⚠️ No schema markup found")
            result['warnings'] += 1
        else:
            result['successes'].append(f"✅ Schema found: {schema_data['schema_types'][:3]}")
        
        # ============================================
        # 7. OPEN GRAPH COMPLETE ANALYSIS
        # ============================================
        og_data = analyze_open_graph_complete(soup)
        result['open_graph'] = og_data
        
        if not og_data['has_og']:
            result['all_issues'].append("⚠️ Missing Open Graph tags")
            result['warnings'] += 1
        else:
            result['successes'].append("✅ Open Graph tags present")
        
        # ============================================
        # 8. TWITTER CARDS COMPLETE ANALYSIS
        # ============================================
        twitter_data = analyze_twitter_cards_complete(soup)
        result['twitter_cards'] = twitter_data
        
        if not twitter_data['has_twitter']:
            result['all_issues'].append("⚠️ Missing Twitter Card tags")
            result['warnings'] += 1
        else:
            result['successes'].append("✅ Twitter Card tags present")
        
        # ============================================
        # 9. HEADINGS COMPLETE ANALYSIS
        # ============================================
        headings_data = analyze_headings_complete(soup)
        result['headings'] = headings_data
        
        for issue in headings_data['issues']:
            if '❌' in issue:
                result['all_issues'].append(issue)
                result['errors'] += 1
            elif '⚠️' in issue:
                result['all_issues'].append(issue)
                result['warnings'] += 1
            else:
                result['successes'].append(issue)
        
        # ============================================
        # 10. CONTENT COMPLETE ANALYSIS
        # ============================================
        content_data = analyze_content_complete(soup)
        result['content'] = content_data
        
        for issue in content_data['issues']:
            if '❌' in issue:
                result['all_issues'].append(issue)
                result['errors'] += 1
            elif '⚠️' in issue:
                result['all_issues'].append(issue)
                result['warnings'] += 1
            else:
                result['successes'].append(issue)
        
        # ============================================
        # 11. TECHNICAL COMPLETE ANALYSIS
        # ============================================
        tech_data = analyze_technical_complete(soup, url, result['response_time'], result['page_size'], result['status_code'])
        result['technical'] = tech_data
        
        for issue in tech_data['issues']:
            if '❌' in issue:
                result['all_issues'].append(issue)
                result['errors'] += 1
            elif '⚠️' in issue:
                result['all_issues'].append(issue)
                result['warnings'] += 1
            else:
                result['successes'].append(issue)
        
        for practice in tech_data['good_practices']:
            if '✅' in practice:
                result['successes'].append(practice)
        
        # ============================================
        # 12. PERFORMANCE COMPLETE ANALYSIS
        # ============================================
        perf_data = analyze_performance_complete(soup)
        result['performance'] = perf_data
        
        for issue in perf_data['issues']:
            if '⚠️' in issue:
                result['all_issues'].append(issue)
                result['warnings'] += 1
        
        for practice in perf_data['good_practices']:
            if '✅' in practice:
                result['successes'].append(practice)
        
        # ============================================
        # 13. SECURITY COMPLETE ANALYSIS
        # ============================================
        security_data = analyze_security_complete(soup, url)
        result['security'] = security_data
        
        for issue in security_data['issues']:
            if '❌' in issue:
                result['all_issues'].append(issue)
                result['errors'] += 1
            elif '⚠️' in issue:
                result['all_issues'].append(issue)
                result['warnings'] += 1
        
        for practice in security_data['good_practices']:
            if '✅' in practice:
                result['successes'].append(practice)
        
        # ============================================
        # 14. MOBILE COMPLETE ANALYSIS
        # ============================================
        mobile_data = analyze_mobile_complete(soup)
        result['mobile_friendly'] = mobile_data
        
        for issue in mobile_data['issues']:
            if '❌' in issue:
                result['all_issues'].append(issue)
                result['errors'] += 1
            elif '⚠️' in issue:
                result['all_issues'].append(issue)
                result['warnings'] += 1
        
        for practice in mobile_data['good_practices']:
            if '✅' in practice:
                result['successes'].append(practice)
        
        # ============================================
        # 15. SOCIAL MEDIA COMPLETE ANALYSIS
        # ============================================
        social_data = analyze_social_media_complete(og_data, twitter_data)
        result['social_media'] = social_data
        
        for issue in social_data['issues']:
            if '⚠️' in issue:
                result['all_issues'].append(issue)
                result['warnings'] += 1
        
        for practice in social_data['good_practices']:
            if '✅' in practice:
                result['successes'].append(practice)
        
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
        if result['images']['with_alt'] > 0 and result['images']['total'] > 0:
            alt_percentage = (result['images']['with_alt'] / result['images']['total']) * 100
            if alt_percentage >= 90:
                score += 3
        
        result['score'] = max(0, min(100, score))
        
    except Exception as e:
        result['error_message'] = str(e)
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
st.markdown("**Full SEO analysis with ALL metrics**")
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
    st.caption("**SEO Metrics Checked:**")
    st.caption("✅ Meta Title & Description")
    st.caption("✅ Meta Keywords")
    st.caption("✅ Anchor Texts Analysis")
    st.caption("✅ Broken Links")
    st.caption("✅ Internal/External Links")
    st.caption("✅ Images (Alt Text, Title)")
    st.caption("✅ Schema Markup")
    st.caption("✅ Open Graph Tags")
    st.caption("✅ Twitter Cards")
    st.caption("✅ Headings (H1-H6)")
    st.caption("✅ Content Quality")
    st.caption("✅ Technical SEO")
    st.caption("✅ Performance")
    st.caption("✅ Security")
    st.caption("✅ Mobile Friendly")

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
                    'Title': (r.get('title') or '')[:50],
                    'Status': '✅ OK' if r.get('is_accessible') else '❌ Failed'
                })
            else:
                df_data.append({
                    'Site': site.replace('https://', ''),
                    'Score': 'Pending',
                    'Errors': '-',
                    'Warnings': '-',
                    'Words': '-',
                    'Title': '-',
                    'Status': '⏳ Pending'
                })
        st.dataframe(pd.DataFrame(df_data), use_container_width=True, hide_index=True)

with tab2:
    st.header("🔍 Run Full SEO Audit")
    
    if st.button("🚀 Audit All Sites", type="primary"):
        if st.session_state.sites:
            progress = st.progress(0)
            status = st.empty()
            
            total = len(st.session_state.sites)
            successful = 0
            failed = 0
            
            for i, url in enumerate(st.session_state.sites):
                status.text(f"Auditing {i+1}/{total}: {url}")
                result = complete_seo_audit(url)
                st.session_state.results[url] = result
                if result.get('is_accessible'):
                    successful += 1
                else:
                    failed += 1
                progress.progress((i + 1) / total)
            
            st.success(f"✅ Audit complete! {successful} successful, {failed} failed")
            st.rerun()
        else:
            st.warning("No sites to audit")
    
    if st.session_state.results:
        st.subheader("📊 Audit Results")
        
        for url, result in st.session_state.results.items():
            with st.expander(f"🔍 {url.replace('https://', '')}", expanded=False):
                if not result.get('is_accessible'):
                    st.error(f"❌ Failed to analyze: {result.get('error_message', 'Unknown error')}")
                    continue
                
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
                
                # Anchor Texts
                st.write("### 🔗 Anchor Texts")
                anchor = result.get('anchor_texts', {})
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total", anchor.get('total_anchors', 0))
                with col2:
                    st.metric("With Text", anchor.get('anchors_with_text', 0))
                with col3:
                    st.metric("Empty", anchor.get('empty_anchors', 0))
                with col4:
                    st.metric("Nofollow", anchor.get('nofollow_anchors', 0))
                
                if anchor.get('common_anchor_words'):
                    st.write("**Common Anchor Words:**")
                    st.write(", ".join([f"{w} ({c})" for w, c in anchor['common_anchor_words'][:5]]))
                
                # Broken Links
                st.write("### 💔 Broken Links")
                broken = result.get('broken_links', {})
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Checked", broken.get('total_checked', 0))
                with col2:
                    st.metric("Broken", broken.get('broken_count', 0))
                with col3:
                    st.metric("Percentage", f"{broken.get('broken_percentage', 0)}%")
                
                if broken.get('broken_links'):
                    st.write("**Broken Links:**")
                    for link in broken['broken_links'][:5]:
                        st.warning(f"• {link.get('href')} (Status: {link.get('status')})")
                
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
                    st.metric("Dofollow", links.get('dofollow_count', 0))
                
                # Images
                st.write("### 🖼️ Images")
                images = result.get('images', {})
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total", images.get('total', 0))
                with col2:
                    st.metric("With Alt", images.get('with_alt', 0))
                with col3:
                    st.metric("Missing Alt", images.get('missing_alt_count', 0))
                with col4:
                    st.metric("Lazy Loaded", images.get('lazy_loaded', 0))
                
                # Schema
                st.write("### 🏷️ Schema Markup")
                schema = result.get('schema', {})
                if schema.get('has_schema'):
                    st.success(f"✅ Schema found: {schema.get('schema_types', [])[:3]}")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Organization", "✅" if schema.get('organization_schema') else "❌")
                    with col2:
                        st.metric("Product", "✅" if schema.get('product_schema') else "❌")
                    with col3:
                        st.metric("Article", "✅" if schema.get('article_schema') else "❌")
                    with col4:
                        st.metric("FAQ", "✅" if schema.get('faq_schema') else "❌")
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
                        st.write(f"**Description:** {og.get('og_description', 'N/A')[:100]}")
                    with col2:
                        st.write(f"**Image:** {og.get('og_image', 'N/A')}")
                        st.write(f"**URL:** {og.get('og_url', 'N/A')}")
                else:
                    st.warning("⚠️ Missing Open Graph tags")
                
                # Twitter Cards
                st.write("### 🐦 Twitter Cards")
                twitter = result.get('twitter_cards', {})
                if twitter.get('has_twitter'):
                    st.success("✅ Twitter Card tags present")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Card:** {twitter.get('twitter_card', 'N/A')}")
                        st.write(f"**Title:** {twitter.get('twitter_title', 'N/A')}")
                    with col2:
                        st.write(f"**Description:** {twitter.get('twitter_description', 'N/A')[:100]}")
                        st.write(f"**Image:** {twitter.get('twitter_image', 'N/A')}")
                else:
                    st.warning("⚠️ Missing Twitter Card tags")
                
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
                
                if headings.get('heading_hierarchy'):
                    st.write("**Heading Hierarchy:**")
                    for h in headings['heading_hierarchy'][:5]:
                        st.write(f"• {h}")
                
                # Content
                st.write("### 📄 Content")
                content = result.get('content', {})
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Words", content.get('total_words', 0))
                with col2:
                    st.metric("Unique", content.get('unique_words', 0))
                with col3:
                    st.metric("Paragraphs", content.get('paragraph_count', 0))
                with col4:
                    st.metric("Readability", content.get('readability_score', 0))
                
                st.write(f"**Avg Words/Sentence:** {content.get('avg_words_per_sentence', 0)}")
                
                if content.get('top_keywords'):
                    st.write("**Top Keywords:**")
                    st.write(", ".join([f"{w} ({c})" for w, c in content['top_keywords'][:5]]))
                
                # Technical
                st.write("### ⚙️ Technical SEO")
                tech = result.get('technical', {})
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("SSL", "✅" if tech.get('has_ssl') else "❌")
                with col2:
                    st.metric("Viewport", "✅" if tech.get('has_viewport') else "❌")
                with col3:
                    st.metric("Canonical", "✅" if tech.get('has_canonical') else "❌")
                with col4:
                    st.metric("Language", tech.get('language', '❌'))
                
                # Performance
                st.write("### 🚀 Performance")
                perf = result.get('performance', {})
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("CSS", perf.get('css_count', 0))
                with col2:
                    st.metric("JS", perf.get('js_count', 0))
                with col3:
                    st.metric("Images", perf.get('image_count', 0))
                with col4:
                    st.metric("Total Resources", perf.get('total_resources', 0))
                
                if perf.get('has_lazy_loading'):
                    st.success(f"✅ Lazy loading enabled ({perf.get('lazy_loaded_images', 0)} images)")
                else:
                    st.warning("⚠️ No lazy loading detected")
                
                # Security
                st.write("### 🔒 Security")
                security = result.get('security', {})
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("SSL", "✅" if security.get('has_ssl') else "❌")
                with col2:
                    st.metric("Mixed Content", "⚠️" if security.get('mixed_content') else "✅")
                
                # Mobile
                st.write("### 📱 Mobile Friendly")
                mobile = result.get('mobile_friendly', {})
                if mobile.get('is_mobile_friendly'):
                    st.success("✅ Mobile friendly")
                else:
                    st.error("❌ Not mobile friendly")
                
                # Social Media
                st.write("### 🌐 Social Media")
                social = result.get('social_media', {})
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Open Graph", "✅" if social.get('has_open_graph') else "❌")
                with col2:
                    st.metric("Twitter Cards", "✅" if social.get('has_twitter_cards') else "❌")
                
                # Issues
                if result.get('successes'):
                    st.write("### ✅ Successes")
                    for s in result['successes'][:10]:
                        st.success(s)
                
                if result.get('all_issues'):
                    st.write("### ⚠️ Issues")
                    for issue in result['all_issues'][:10]:
                        if '❌' in issue:
                            st.error(issue)
                        elif '⚠️' in issue:
                            st.warning(issue)

with tab3:
    st.header("📈 Reports")
    
    if st.session_state.results:
        data = []
        for url, result in st.session_state.results.items():
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
            anchor_data = result.get('anchor_texts', {})
            broken_data = result.get('broken_links', {})
            security_data = result.get('security', {})
            perf_data = result.get('performance', {})
            
            data.append({
                'Site': url.replace('https://', ''),
                'Score': result.get('score', 0),
                'Errors': result.get('errors', 0),
                'Warnings': result.get('warnings', 0),
                'Title': title[:50] + '...' if len(title) > 50 else (title if title else 'N/A'),
                'Description': meta_desc[:50] + '...' if len(meta_desc) > 50 else (meta_desc if meta_desc else 'N/A'),
                'Total Words': content_data.get('total_words', 0),
                'Internal Links': links_data.get('internal_count', 0),
                'External Links': links_data.get('external_count', 0),
                'Broken Links': broken_data.get('broken_count', 0),
                'Images': images_data.get('total', 0),
                'Images with Alt': images_data.get('with_alt', 0),
                'Empty Anchors': anchor_data.get('empty_anchors', 0),
                'Schema': '✅' if schema_data.get('has_schema') else '❌',
                'Open Graph': '✅' if og_data.get('has_og') else '❌',
                'Twitter Cards': '✅' if twitter_data.get('has_twitter') else '❌',
                'SSL': '✅' if tech_data.get('has_ssl') else '❌',
                'Mobile Friendly': '✅' if mobile_data.get('is_mobile_friendly') else '❌',
                'Mixed Content': '⚠️' if security_data.get('mixed_content') else '✅',
                'Lazy Loading': '✅' if perf_data.get('has_lazy_loading') else '❌',
                'Accessible': '✅' if result.get('is_accessible') else '❌'
            })
        
        df = pd.DataFrame(data)
        df = df.sort_values('Score', ascending=False)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        csv = df.to_csv(index=False)
        st.download_button(
            "📥 Download Full SEO Report (CSV)",
            data=csv,
            file_name=f"seo_audit_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.info("Run an SEO audit first to generate reports")

st.markdown("---")
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.caption(f"🔄 Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.caption(f"📊 Total Sites: {len(st.session_state.sites)} | Audited: {len(st.session_state.results)}")
    st.caption("🚀 Complete SEO Audit v3.0 | All Metrics Included")
