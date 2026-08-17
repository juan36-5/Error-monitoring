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
            time.sleep(random.uniform(0.5, 1.5))
            response = requests.get(url, timeout=25, headers=headers, allow_redirects=True, verify=False)
            if response.status_code == 200:
                return response.text, response.status_code
            elif response.status_code != 403:
                return response.text, response.status_code
        except:
            continue
    return "", 0

# ============ COMPLETE SEO AUDIT WITH REAL DATA ============
def complete_seo_audit(url):
    """Complete SEO audit with ALL 50+ metrics - SHOWING REAL DATA"""
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
        
        # ===== META TAGS - REAL DATA =====
        'title': '',
        'title_length': 0,
        'meta_description': '',
        'meta_description_length': 0,
        'meta_keywords': '',
        
        # ===== HEADINGS - REAL DATA =====
        'h1_count': 0,
        'h1_text': '',
        'h2_count': 0,
        'h3_count': 0,
        'h4_count': 0,
        'h5_count': 0,
        'h6_count': 0,
        'all_headings': [],
        
        # ===== CONTENT - REAL DATA =====
        'total_words': 0,
        'paragraph_count': 0,
        'sentence_count': 0,
        'top_keywords': [],
        'keyword_density': {},
        
        # ===== LINKS - REAL DATA =====
        'total_links': 0,
        'internal_links': 0,
        'external_links': 0,
        'nofollow_links': 0,
        'broken_links': 0,
        'internal_link_urls': [],
        'external_link_urls': [],
        
        # ===== ANCHOR TEXTS - REAL DATA =====
        'anchor_texts': [],
        'empty_anchors': 0,
        
        # ===== IMAGES - REAL DATA =====
        'total_images': 0,
        'images_with_alt': 0,
        'images_without_alt': 0,
        'alt_texts': [],
        
        # ===== SCHEMA - REAL DATA =====
        'has_schema': False,
        'schema_types': '',
        'schema_type_list': [],
        
        # ===== OPEN GRAPH - REAL DATA =====
        'has_og': False,
        'og_title': '',
        'og_description': '',
        'og_image': '',
        'og_url': '',
        'og_type': '',
        
        # ===== TWITTER CARDS - REAL DATA =====
        'has_twitter': False,
        'twitter_card': '',
        'twitter_title': '',
        'twitter_description': '',
        'twitter_image': '',
        'twitter_site': '',
        
        # ===== TECHNICAL - REAL DATA =====
        'has_ssl': False,
        'has_viewport': False,
        'viewport_content': '',
        'has_canonical': False,
        'canonical_url': '',
        'has_language': False,
        'language': '',
        'has_robots': False,
        'robots_content': '',
        'has_favicon': False,
        'favicon_url': '',
        
        # ===== PERFORMANCE - REAL DATA =====
        'css_count': 0,
        'js_count': 0,
        'has_lazy_loading': False,
        
        # ===== SECURITY - REAL DATA =====
        'has_mixed_content': False,
        
        # ===== MOBILE - REAL DATA =====
        'is_mobile_friendly': False
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
        result['has_ssl'] = url.startswith('https')
        
        soup = BeautifulSoup(html_content, 'html.parser')
        base_domain = urlparse(url).netloc
        
        # ============================================
        # 1. META TAGS - GET REAL DATA
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
        # 2. HEADINGS - GET REAL DATA
        # ============================================
        h1_tags = soup.find_all('h1')
        result['h1_count'] = len(h1_tags)
        if h1_tags and h1_tags[0].text.strip():
            result['h1_text'] = h1_tags[0].text.strip()
        
        result['h2_count'] = len(soup.find_all('h2'))
        result['h3_count'] = len(soup.find_all('h3'))
        result['h4_count'] = len(soup.find_all('h4'))
        result['h5_count'] = len(soup.find_all('h5'))
        result['h6_count'] = len(soup.find_all('h6'))
        
        # All headings - REAL TEXT
        for level in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            tags = soup.find_all(level)
            for tag in tags:
                text = tag.text.strip()
                if text:
                    result['all_headings'].append(f"{level.upper()}: {text}")
        
        if result['h1_count'] == 0:
            result['all_issues'].append("❌ No H1 heading found")
            result['errors'] += 1
        elif result['h1_count'] == 1:
            result['successes'].append("✅ Exactly one H1 heading")
        else:
            result['all_issues'].append(f"⚠️ Multiple H1 tags: {result['h1_count']}")
            result['warnings'] += 1
        
        # ============================================
        # 3. CONTENT - GET REAL DATA
        # ============================================
        for script in soup(["script", "style"]):
            script.decompose()
        
        text = soup.get_text(separator=' ', strip=True)
        words = re.findall(r'\b[a-zA-Z0-9]+(?:\'[a-zA-Z]+)?\b', text)
        result['total_words'] = len(words)
        
        paragraphs = soup.find_all('p')
        result['paragraph_count'] = len(paragraphs)
        
        sentences = re.split(r'[.!?]+', text)
        result['sentence_count'] = len([s for s in sentences if len(s.strip()) > 10])
        
        # Top keywords - REAL DATA
        stop_words = {'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i', 'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at', 'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she', 'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their', 'what', 'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go', 'me'}
        content_words = [w.lower() for w in words if w.lower() not in stop_words and len(w) > 3]
        word_freq = Counter(content_words)
        result['top_keywords'] = word_freq.most_common(10)
        result['keyword_density'] = dict(word_freq.most_common(20))
        
        if result['total_words'] < 100:
            result['all_issues'].append(f"❌ Very low word count: {result['total_words']} words")
            result['errors'] += 1
        elif result['total_words'] < 300:
            result['all_issues'].append(f"⚠️ Low word count: {result['total_words']} words")
            result['warnings'] += 1
        else:
            result['successes'].append(f"✅ Good word count: {result['total_words']} words")
        
        # ============================================
        # 4. LINKS - GET REAL DATA
        # ============================================
        all_links = soup.find_all('a', href=True)
        result['total_links'] = len(all_links)
        
        internal = 0
        external = 0
        nofollow = 0
        
        for link in all_links:
            href = link.get('href', '')
            rel = link.get('rel', [])
            
            if 'nofollow' in rel:
                nofollow += 1
            
            if href.startswith('http'):
                if urlparse(href).netloc == base_domain:
                    internal += 1
                    if len(result['internal_link_urls']) < 10:
                        result['internal_link_urls'].append(href[:150])
                else:
                    external += 1
                    if len(result['external_link_urls']) < 10:
                        result['external_link_urls'].append(href[:150])
            elif href.startswith('/') or href.startswith('#'):
                internal += 1
                if len(result['internal_link_urls']) < 10:
                    result['internal_link_urls'].append(href[:150])
        
        result['internal_links'] = internal
        result['external_links'] = external
        result['nofollow_links'] = nofollow
        
        # Broken links check
        broken = 0
        for link in all_links[:15]:
            href = link.get('href', '')
            if href.startswith('http'):
                try:
                    resp = requests.head(href, timeout=3, allow_redirects=True)
                    if resp.status_code >= 400:
                        broken += 1
                except:
                    broken += 1
        result['broken_links'] = broken
        
        # ============================================
        # 5. ANCHOR TEXTS - GET REAL DATA
        # ============================================
        for link in all_links:
            anchor = link.text.strip()
            if anchor:
                if len(result['anchor_texts']) < 20:
                    result['anchor_texts'].append(anchor[:100])
            else:
                result['empty_anchors'] += 1
        
        # ============================================
        # 6. IMAGES - GET REAL DATA
        # ============================================
        images = soup.find_all('img')
        result['total_images'] = len(images)
        
        with_alt = 0
        without_alt = 0
        
        for img in images:
            alt = img.get('alt', '').strip()
            if alt:
                with_alt += 1
                if len(result['alt_texts']) < 10:
                    result['alt_texts'].append(alt[:100])
            else:
                without_alt += 1
        
        result['images_with_alt'] = with_alt
        result['images_without_alt'] = without_alt
        
        # ============================================
        # 7. SCHEMA - GET REAL DATA (NOT JUST TRUE/FALSE)
        # ============================================
        schema_scripts = soup.find_all('script', attrs={'type': 'application/ld+json'})
        if schema_scripts:
            result['has_schema'] = True
            schema_type_list = []
            for script in schema_scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        schema_type = data.get('@type', 'Unknown')
                        if schema_type not in schema_type_list:
                            schema_type_list.append(schema_type)
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict):
                                schema_type = item.get('@type', 'Unknown')
                                if schema_type not in schema_type_list:
                                    schema_type_list.append(schema_type)
                except:
                    pass
            result['schema_type_list'] = schema_type_list
            result['schema_types'] = ', '.join(schema_type_list) if schema_type_list else 'Schema found'
            result['successes'].append(f"✅ Schema found: {result['schema_types']}")
        else:
            result['has_schema'] = False
            result['schema_types'] = 'No schema'
            result['all_issues'].append("⚠️ No schema markup found")
            result['warnings'] += 1
        
        # ============================================
        # 8. OPEN GRAPH - GET REAL DATA (NOT JUST TRUE/FALSE)
        # ============================================
        og_title = soup.find('meta', attrs={'property': 'og:title'})
        og_desc = soup.find('meta', attrs={'property': 'og:description'})
        og_image = soup.find('meta', attrs={'property': 'og:image'})
        og_url = soup.find('meta', attrs={'property': 'og:url'})
        og_type = soup.find('meta', attrs={'property': 'og:type'})
        
        if og_title or og_desc or og_image:
            result['has_og'] = True
            result['og_title'] = og_title.get('content', '') if og_title else ''
            result['og_description'] = og_desc.get('content', '') if og_desc else ''
            result['og_image'] = og_image.get('content', '') if og_image else ''
            result['og_url'] = og_url.get('content', '') if og_url else ''
            result['og_type'] = og_type.get('content', '') if og_type else ''
            result['successes'].append("✅ Open Graph tags present")
        else:
            result['has_og'] = False
            result['all_issues'].append("⚠️ Missing Open Graph tags")
            result['warnings'] += 1
        
        # ============================================
        # 9. TWITTER CARDS - GET REAL DATA (NOT JUST TRUE/FALSE)
        # ============================================
        twitter_card = soup.find('meta', attrs={'name': 'twitter:card'})
        twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})
        twitter_desc = soup.find('meta', attrs={'name': 'twitter:description'})
        twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
        twitter_site = soup.find('meta', attrs={'name': 'twitter:site'})
        
        if twitter_card or twitter_title:
            result['has_twitter'] = True
            result['twitter_card'] = twitter_card.get('content', '') if twitter_card else ''
            result['twitter_title'] = twitter_title.get('content', '') if twitter_title else ''
            result['twitter_description'] = twitter_desc.get('content', '') if twitter_desc else ''
            result['twitter_image'] = twitter_image.get('content', '') if twitter_image else ''
            result['twitter_site'] = twitter_site.get('content', '') if twitter_site else ''
            result['successes'].append("✅ Twitter Card tags present")
        else:
            result['has_twitter'] = False
            result['all_issues'].append("⚠️ Missing Twitter Card tags")
            result['warnings'] += 1
        
        # ============================================
        # 10. TECHNICAL - GET REAL DATA
        # ============================================
        viewport = soup.find('meta', attrs={'name': 'viewport'})
        if viewport:
            result['has_viewport'] = True
            result['viewport_content'] = viewport.get('content', '')
            result['is_mobile_friendly'] = True
            result['successes'].append("✅ Viewport found - mobile friendly")
        else:
            result['all_issues'].append("❌ Missing viewport meta tag")
            result['errors'] += 1
        
        canonical = soup.find('link', attrs={'rel': 'canonical'})
        if canonical and canonical.get('href'):
            result['has_canonical'] = True
            result['canonical_url'] = canonical.get('href')
            result['successes'].append("✅ Canonical tag found")
        else:
            result['all_issues'].append("⚠️ No canonical tag found")
            result['warnings'] += 1
        
        html = soup.find('html')
        if html and html.get('lang'):
            result['has_language'] = True
            result['language'] = html.get('lang')
            result['successes'].append(f"✅ Language attribute: {result['language']}")
        else:
            result['all_issues'].append("⚠️ No language attribute")
            result['warnings'] += 1
        
        robots = soup.find('meta', attrs={'name': 'robots'})
        if robots:
            result['has_robots'] = True
            result['robots_content'] = robots.get('content', '')
            if 'noindex' in robots.get('content', '').lower():
                result['all_issues'].append("❌ Page is marked noindex")
                result['errors'] += 1
            if 'nofollow' in robots.get('content', '').lower():
                result['all_issues'].append("⚠️ Page is marked nofollow")
                result['warnings'] += 1
        
        favicon = soup.find('link', attrs={'rel': 'icon'}) or soup.find('link', attrs={'rel': 'shortcut icon'})
        if favicon:
            result['has_favicon'] = True
            result['favicon_url'] = favicon.get('href', '')
            result['successes'].append("✅ Favicon found")
        else:
            result['all_issues'].append("⚠️ No favicon found")
            result['warnings'] += 1
        
        # ============================================
        # 11. PERFORMANCE - GET REAL DATA
        # ============================================
        result['css_count'] = len(soup.find_all('link', rel='stylesheet'))
        result['js_count'] = len(soup.find_all('script', src=True))
        
        lazy_images = soup.find_all('img', loading='lazy')
        if lazy_images:
            result['has_lazy_loading'] = True
            result['successes'].append("✅ Lazy loading enabled")
        
        # ============================================
        # 12. SECURITY - GET REAL DATA
        # ============================================
        scripts = soup.find_all('script', src=True)
        for script in scripts:
            src = script.get('src', '')
            if src.startswith('http://') and url.startswith('https://'):
                result['has_mixed_content'] = True
                break
        
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
        if result['h1_count'] == 1:
            score += 2
        if result['total_words'] > 300:
            score += 5
        if result['has_schema']:
            score += 3
        if result['has_viewport']:
            score += 2
        if result['has_og']:
            score += 2
        if result['has_twitter']:
            score += 2
        if result['has_ssl']:
            score += 5
        if result['internal_links'] > 5:
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
st.markdown("**Full SEO analysis with REAL DATA**")
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
                    'Words': r.get('total_words', 0),
                    'Title': r.get('title', '')[:50],
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
                
                # ===== META TAGS - REAL DATA =====
                st.write("### 📝 Meta Tags")
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Title:** {result.get('title', '')}")
                    st.write(f"**Title Length:** {result.get('title_length', 0)} chars")
                with col2:
                    st.write(f"**Description:** {result.get('meta_description', '')}")
                    st.write(f"**Description Length:** {result.get('meta_description_length', 0)} chars")
                st.write(f"**Keywords:** {result.get('meta_keywords', '')}")
                
                st.markdown("---")
                
                # ===== HEADINGS - REAL DATA =====
                st.write("### 📑 Headings")
                col1, col2, col3, col4, col5, col6 = st.columns(6)
                with col1:
                    st.metric("H1", result.get('h1_count', 0))
                with col2:
                    st.metric("H2", result.get('h2_count', 0))
                with col3:
                    st.metric("H3", result.get('h3_count', 0))
                with col4:
                    st.metric("H4", result.get('h4_count', 0))
                with col5:
                    st.metric("H5", result.get('h5_count', 0))
                with col6:
                    st.metric("H6", result.get('h6_count', 0))
                
                if result.get('h1_text'):
                    st.write(f"**H1 Text:** {result['h1_text']}")
                
                if result.get('all_headings'):
                    st.write("**All Headings:**")
                    for heading in result['all_headings'][:5]:
                        st.write(f"• {heading}")
                
                st.markdown("---")
                
                # ===== CONTENT - REAL DATA =====
                st.write("### 📄 Content")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Words", result.get('total_words', 0))
                with col2:
                    st.metric("Paragraphs", result.get('paragraph_count', 0))
                with col3:
                    st.metric("Sentences", result.get('sentence_count', 0))
                
                if result.get('top_keywords'):
                    st.write("**Top Keywords:**")
                    keywords = ", ".join([f"{w} ({c})" for w, c in result['top_keywords'][:5]])
                    st.write(keywords)
                
                st.markdown("---")
                
                # ===== LINKS - REAL DATA =====
                st.write("### 🔗 Links")
                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    st.metric("Total", result.get('total_links', 0))
                with col2:
                    st.metric("Internal", result.get('internal_links', 0))
                with col3:
                    st.metric("External", result.get('external_links', 0))
                with col4:
                    st.metric("Nofollow", result.get('nofollow_links', 0))
                with col5:
                    st.metric("Broken", result.get('broken_links', 0))
                
                if result.get('internal_link_urls'):
                    st.write("**Sample Internal Links:**")
                    for link in result['internal_link_urls'][:3]:
                        st.write(f"• {link}")
                
                if result.get('external_link_urls'):
                    st.write("**Sample External Links:**")
                    for link in result['external_link_urls'][:3]:
                        st.write(f"• {link}")
                
                st.markdown("---")
                
                # ===== ANCHOR TEXTS - REAL DATA =====
                st.write("### 🔗 Anchor Texts")
                st.metric("Empty Anchors", result.get('empty_anchors', 0))
                
                if result.get('anchor_texts'):
                    st.write("**Sample Anchor Texts:**")
                    for anchor in result['anchor_texts'][:5]:
                        st.write(f"• {anchor}")
                
                st.markdown("---")
                
                # ===== IMAGES - REAL DATA =====
                st.write("### 🖼️ Images")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total", result.get('total_images', 0))
                with col2:
                    st.metric("With Alt", result.get('images_with_alt', 0))
                with col3:
                    st.metric("Missing Alt", result.get('images_without_alt', 0))
                
                if result.get('alt_texts'):
                    st.write("**Sample Alt Texts:**")
                    for alt in result['alt_texts'][:3]:
                        st.write(f"• {alt}")
                
                st.markdown("---")
                
                # ===== SCHEMA - REAL DATA (NOT JUST ✅/❌) =====
                st.write("### 🏷️ Schema Markup")
                if result.get('has_schema'):
                    st.success(f"✅ Schema found: **{result.get('schema_types', '')}**")
                else:
                    st.warning("⚠️ No schema found")
                
                st.markdown("---")
                
                # ===== OPEN GRAPH - REAL DATA (NOT JUST ✅/❌) =====
                st.write("### 📱 Open Graph")
                if result.get('has_og'):
                    st.success("✅ Open Graph tags present")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Title:** {result.get('og_title', '')}")
                        st.write(f"**Description:** {result.get('og_description', '')}")
                    with col2:
                        st.write(f"**Image:** {result.get('og_image', '')}")
                        st.write(f"**URL:** {result.get('og_url', '')}")
                else:
                    st.warning("⚠️ Missing Open Graph tags")
                
                st.markdown("---")
                
                # ===== TWITTER CARDS - REAL DATA (NOT JUST ✅/❌) =====
                st.write("### 🐦 Twitter Cards")
                if result.get('has_twitter'):
                    st.success("✅ Twitter Card tags present")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Card:** {result.get('twitter_card', '')}")
                        st.write(f"**Title:** {result.get('twitter_title', '')}")
                    with col2:
                        st.write(f"**Description:** {result.get('twitter_description', '')}")
                        st.write(f"**Image:** {result.get('twitter_image', '')}")
                else:
                    st.warning("⚠️ Missing Twitter Card tags")
                
                st.markdown("---")
                
                # ===== TECHNICAL - REAL DATA =====
                st.write("### ⚙️ Technical SEO")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("SSL", "✅" if result.get('has_ssl') else "❌")
                with col2:
                    st.metric("Viewport", "✅" if result.get('has_viewport') else "❌")
                with col3:
                    st.metric("Canonical", "✅" if result.get('has_canonical') else "❌")
                with col4:
                    st.metric("Language", result.get('language', '❌'))
                
                if result.get('viewport_content'):
                    st.write(f"**Viewport:** {result.get('viewport_content', '')}")
                if result.get('canonical_url'):
                    st.write(f"**Canonical URL:** {result.get('canonical_url', '')}")
                if result.get('robots_content'):
                    st.write(f"**Robots:** {result.get('robots_content', '')}")
                
                st.markdown("---")
                
                # ===== PERFORMANCE =====
                st.write("### 🚀 Performance")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("CSS", result.get('css_count', 0))
                with col2:
                    st.metric("JS", result.get('js_count', 0))
                with col3:
                    st.metric("Lazy Loading", "✅" if result.get('has_lazy_loading') else "❌")
                
                st.markdown("---")
                
                # ===== SECURITY =====
                st.write("### 🔒 Security")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("SSL", "✅" if result.get('has_ssl') else "❌")
                with col2:
                    st.metric("Mixed Content", "⚠️" if result.get('has_mixed_content') else "✅")
                
                st.markdown("---")
                
                # ===== MOBILE =====
                st.write("### 📱 Mobile Friendly")
                if result.get('is_mobile_friendly'):
                    st.success("✅ Mobile friendly")
                else:
                    st.error("❌ Not mobile friendly")
                
                st.markdown("---")
                
                # ===== ISSUES =====
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
            data.append({
                'Site': url.replace('https://', ''),
                'Score': result.get('score', 0),
                'Errors': result.get('errors', 0),
                'Warnings': result.get('warnings', 0),
                'Title': result.get('title', ''),
                'Description': result.get('meta_description', ''),
                'Total Words': result.get('total_words', 0),
                'Internal Links': result.get('internal_links', 0),
                'External Links': result.get('external_links', 0),
                'Broken Links': result.get('broken_links', 0),
                'Images with Alt': result.get('images_with_alt', 0),
                'Schema': result.get('schema_types', 'No Schema'),
                'Open Graph': 'OG: ' + result.get('og_title', '')[:30] if result.get('has_og') else 'No OG',
                'Twitter': 'TW: ' + result.get('twitter_title', '')[:30] if result.get('has_twitter') else 'No Twitter',
                'SSL': '✅' if result.get('has_ssl') else '❌',
                'Mobile Friendly': '✅' if result.get('is_mobile_friendly') else '❌',
                'Mixed Content': '⚠️' if result.get('has_mixed_content') else '✅',
                'Lazy Loading': '✅' if result.get('has_lazy_loading') else '❌',
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
    st.caption("🚀 Complete SEO Audit | REAL DATA")
