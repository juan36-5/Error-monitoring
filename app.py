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

# Try to import selenium
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

st.set_page_config(page_title="Complete SEO Audit", page_icon="🔍", layout="wide")

# ============ USER AGENTS ============
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
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

# ============ SESSION STATE ============
if 'sites' not in st.session_state:
    st.session_state.sites = []
if 'results' not in st.session_state:
    st.session_state.results = {}
if 'initialized' not in st.session_state:
    st.session_state.initialized = False

# ============ GET PAGE CONTENT FUNCTION ============
def get_page_content(url):
    """Try multiple methods to get page content"""
    
    # Clean URL
    if not url.startswith('http'):
        url = 'https://' + url
    
    # Try requests with rotating user agents
    for attempt in range(5):
        try:
            headers = get_random_headers()
            session = requests.Session()
            response = session.get(
                url, 
                timeout=25, 
                headers=headers, 
                allow_redirects=True, 
                verify=False
            )
            
            if response.status_code == 200 and len(response.text) > 1000:
                return response.text, response.status_code
            elif response.status_code == 200:
                # Got content but might be minimal, try Selenium
                if SELENIUM_AVAILABLE:
                    return selenium_get_content(url)
                    
        except Exception as e:
            print(f"Request attempt {attempt + 1} failed: {e}")
            time.sleep(random.uniform(1, 3))
            continue
    
    # Try Selenium as fallback
    if SELENIUM_AVAILABLE:
        try:
            return selenium_get_content(url)
        except Exception as e:
            print(f"Selenium failed: {e}")
    
    return "", 0

def selenium_get_content(url):
    """Get content using Selenium"""
    try:
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        options.add_experimental_option('useAutomationExtension', False)
        
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
        except:
            driver = webdriver.Chrome(options=options)
        
        driver.get(url)
        time.sleep(8)  # Wait for JavaScript
        html = driver.page_source
        driver.quit()
        
        if html and len(html) > 1000:
            return html, 200
        
    except Exception as e:
        print(f"Selenium error: {e}")
    
    return "", 0

# ============ COMPLETE SEO AUDIT ============
def complete_seo_audit(url):
    """Complete SEO audit with ALL 50+ metrics"""
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
        
        # META TAGS
        'title': '',
        'title_length': 0,
        'meta_description': '',
        'meta_description_length': 0,
        'meta_keywords': '',
        
        # HEADINGS
        'h1_count': 0,
        'h1_text': '',
        'h2_count': 0,
        'h3_count': 0,
        'h4_count': 0,
        'h5_count': 0,
        'h6_count': 0,
        'all_headings': [],
        
        # CONTENT
        'total_words': 0,
        'paragraph_count': 0,
        'sentence_count': 0,
        'top_keywords': [],
        
        # LINKS
        'total_links': 0,
        'internal_links': 0,
        'external_links': 0,
        'nofollow_links': 0,
        'broken_links': 0,
        
        # IMAGES
        'total_images': 0,
        'images_with_alt': 0,
        'images_without_alt': 0,
        
        # SCHEMA
        'has_schema': False,
        'schema_types': '',
        
        # OPEN GRAPH
        'has_og': False,
        'og_title': '',
        'og_description': '',
        'og_image': '',
        
        # TWITTER CARDS
        'has_twitter': False,
        'twitter_title': '',
        'twitter_card': '',
        
        # TECHNICAL
        'has_ssl': False,
        'has_viewport': False,
        'has_canonical': False,
        'canonical_url': '',
        'has_language': False,
        'language': '',
        'has_robots': False,
        'robots_content': '',
        
        # PERFORMANCE
        'css_count': 0,
        'js_count': 0,
        'has_lazy_loading': False,
        
        # SECURITY
        'has_mixed_content': False,
        'is_mobile_friendly': False
    }
    
    try:
        start_time = time.time()
        
        if not url.startswith('http'):
            url = 'https://' + url
        
        html_content, status_code = get_page_content(url)
        result['status_code'] = status_code
        
        if not html_content or len(html_content) < 100:
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
        
        # ===== META TAGS =====
        title = soup.find('title')
        if title and title.text.strip():
            result['title'] = title.text.strip()
            result['title_length'] = len(title.text.strip())
            result['successes'].append(f"✅ Title found: {result['title_length']} chars")
        else:
            # Try OG title as fallback
            og_title = soup.find('meta', attrs={'property': 'og:title'})
            if og_title and og_title.get('content'):
                result['title'] = og_title.get('content')
                result['title_length'] = len(result['title'])
                result['successes'].append(f"✅ Title from OG: {result['title_length']} chars")
            else:
                result['all_issues'].append("❌ Missing title tag")
                result['errors'] += 1
        
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            desc_content = meta_desc.get('content', '').strip()
            if desc_content:
                result['meta_description'] = desc_content
                result['meta_description_length'] = len(desc_content)
                result['successes'].append(f"✅ Description found: {result['meta_description_length']} chars")
            else:
                # Try OG description
                og_desc = soup.find('meta', attrs={'property': 'og:description'})
                if og_desc and og_desc.get('content'):
                    result['meta_description'] = og_desc.get('content')
                    result['meta_description_length'] = len(result['meta_description'])
                    result['successes'].append(f"✅ Description from OG: {result['meta_description_length']} chars")
                else:
                    result['all_issues'].append("⚠️ Description is empty")
                    result['warnings'] += 1
        else:
            # Try OG description
            og_desc = soup.find('meta', attrs={'property': 'og:description'})
            if og_desc and og_desc.get('content'):
                result['meta_description'] = og_desc.get('content')
                result['meta_description_length'] = len(result['meta_description'])
                result['successes'].append(f"✅ Description from OG: {result['meta_description_length']} chars")
            else:
                result['all_issues'].append("❌ Missing meta description")
                result['errors'] += 1
        
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords:
            result['meta_keywords'] = meta_keywords.get('content', '')
            result['successes'].append("✅ Meta keywords present")
        
        # ===== HEADINGS =====
        h1_tags = soup.find_all('h1')
        result['h1_count'] = len(h1_tags)
        if h1_tags and h1_tags[0].text.strip():
            result['h1_text'] = h1_tags[0].text.strip()
            if len(h1_tags) == 1:
                result['successes'].append(f"✅ Single H1: {result['h1_text'][:50]}")
            else:
                result['all_issues'].append(f"⚠️ Multiple H1 tags: {len(h1_tags)} found")
                result['warnings'] += 1
        else:
            result['all_issues'].append("⚠️ No H1 heading found")
            result['warnings'] += 1
        
        result['h2_count'] = len(soup.find_all('h2'))
        result['h3_count'] = len(soup.find_all('h3'))
        result['h4_count'] = len(soup.find_all('h4'))
        result['h5_count'] = len(soup.find_all('h5'))
        result['h6_count'] = len(soup.find_all('h6'))
        
        # ===== CONTENT =====
        for script in soup(["script", "style"]):
            script.decompose()
        
        text = soup.get_text(separator=' ', strip=True)
        words = re.findall(r'\b[a-zA-Z0-9]+(?:\'[a-zA-Z]+)?\b', text)
        result['total_words'] = len(words)
        
        if result['total_words'] > 300:
            result['successes'].append(f"✅ Good content: {result['total_words']} words")
        else:
            result['all_issues'].append(f"⚠️ Thin content: {result['total_words']} words")
            result['warnings'] += 1
        
        paragraphs = soup.find_all('p')
        result['paragraph_count'] = len(paragraphs)
        
        sentences = re.split(r'[.!?]+', text)
        result['sentence_count'] = len([s for s in sentences if len(s.strip()) > 10])
        
        # Top keywords
        stop_words = {'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i', 'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at', 'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she', 'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their', 'what', 'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go', 'me'}
        content_words = [w.lower() for w in words if w.lower() not in stop_words and len(w) > 3]
        word_freq = Counter(content_words)
        result['top_keywords'] = word_freq.most_common(10)
        
        # ===== LINKS =====
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
            
            if href:
                if href.startswith('http'):
                    if urlparse(href).netloc == base_domain or urlparse(href).netloc == '':
                        internal += 1
                    else:
                        external += 1
                elif href.startswith('/') or href.startswith('#'):
                    internal += 1
                elif href.startswith('//'):
                    # Protocol relative URL
                    if urlparse('https:' + href).netloc == base_domain:
                        internal += 1
                    else:
                        external += 1
        
        result['internal_links'] = internal
        result['external_links'] = external
        result['nofollow_links'] = nofollow
        
        if result['total_links'] > 0:
            result['successes'].append(f"✅ {result['total_links']} links found ({internal} internal, {external} external)")
        else:
            result['all_issues'].append("⚠️ No links found")
            result['warnings'] += 1
        
        # Broken links check
        broken = 0
        checked = 0
        for link in all_links[:10]:
            href = link.get('href', '')
            if href and href.startswith('http'):
                try:
                    resp = requests.head(href, timeout=3, allow_redirects=True, verify=False)
                    if resp.status_code >= 400:
                        broken += 1
                    checked += 1
                except:
                    broken += 1
                    checked += 1
        result['broken_links'] = broken
        
        # ===== IMAGES =====
        images = soup.find_all('img')
        result['total_images'] = len(images)
        
        with_alt = 0
        without_alt = 0
        
        for img in images:
            alt = img.get('alt', '').strip()
            if alt:
                with_alt += 1
            else:
                without_alt += 1
        
        result['images_with_alt'] = with_alt
        result['images_without_alt'] = without_alt
        
        if result['total_images'] > 0:
            result['successes'].append(f"✅ {result['total_images']} images found ({with_alt} with alt text)")
        if without_alt > 0:
            result['all_issues'].append(f"⚠️ {without_alt} images missing alt text")
            result['warnings'] += 1
        
        # ===== SCHEMA =====
        schema_scripts = soup.find_all('script', attrs={'type': 'application/ld+json'})
        if schema_scripts:
            result['has_schema'] = True
            schema_list = []
            for script in schema_scripts:
                try:
                    if script.string:
                        data = json.loads(script.string)
                        if isinstance(data, dict):
                            schema_type = data.get('@type', 'Unknown')
                            if schema_type:
                                schema_list.append(schema_type)
                        elif isinstance(data, list):
                            for item in data:
                                if isinstance(item, dict):
                                    schema_type = item.get('@type', 'Unknown')
                                    if schema_type:
                                        schema_list.append(schema_type)
                except:
                    pass
            if schema_list:
                result['schema_types'] = ', '.join(list(set(schema_list))[:3])
                result['successes'].append(f"✅ Schema found: {result['schema_types']}")
            else:
                result['all_issues'].append("⚠️ Schema present but invalid")
                result['warnings'] += 1
        else:
            result['all_issues'].append("⚠️ No schema markup found")
            result['warnings'] += 1
        
        # ===== OPEN GRAPH =====
        og_title = soup.find('meta', attrs={'property': 'og:title'})
        og_desc = soup.find('meta', attrs={'property': 'og:description'})
        og_image = soup.find('meta', attrs={'property': 'og:image'})
        
        if og_title or og_desc or og_image:
            result['has_og'] = True
            result['og_title'] = og_title.get('content', '') if og_title else ''
            result['og_description'] = og_desc.get('content', '') if og_desc else ''
            result['og_image'] = og_image.get('content', '') if og_image else ''
            result['successes'].append("✅ Open Graph tags present")
        else:
            result['all_issues'].append("⚠️ Missing Open Graph tags")
            result['warnings'] += 1
        
        # ===== TWITTER CARDS =====
        twitter_card = soup.find('meta', attrs={'name': 'twitter:card'})
        twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})
        
        if twitter_card or twitter_title:
            result['has_twitter'] = True
            result['twitter_card'] = twitter_card.get('content', '') if twitter_card else ''
            result['twitter_title'] = twitter_title.get('content', '') if twitter_title else ''
            result['successes'].append("✅ Twitter Card tags present")
        else:
            result['all_issues'].append("⚠️ Missing Twitter Card tags")
            result['warnings'] += 1
        
        # ===== TECHNICAL =====
        viewport = soup.find('meta', attrs={'name': 'viewport'})
        if viewport:
            result['has_viewport'] = True
            result['is_mobile_friendly'] = True
            result['successes'].append("✅ Viewport found")
        else:
            result['all_issues'].append("❌ Missing viewport meta tag")
            result['errors'] += 1
        
        canonical = soup.find('link', attrs={'rel': 'canonical'})
        if canonical:
            result['has_canonical'] = True
            result['canonical_url'] = canonical.get('href', '')
            result['successes'].append("✅ Canonical tag found")
        else:
            result['all_issues'].append("⚠️ No canonical tag found")
            result['warnings'] += 1
        
        html_tag = soup.find('html')
        if html_tag and html_tag.get('lang'):
            result['has_language'] = True
            result['language'] = html_tag.get('lang')
            result['successes'].append(f"✅ Language: {result['language']}")
        else:
            result['all_issues'].append("⚠️ No language attribute")
            result['warnings'] += 1
        
        robots = soup.find('meta', attrs={'name': 'robots'})
        if robots:
            result['has_robots'] = True
            result['robots_content'] = robots.get('content', '')
            result['successes'].append(f"✅ Robots: {result['robots_content']}")
        
        # ===== PERFORMANCE =====
        result['css_count'] = len(soup.find_all('link', rel='stylesheet'))
        result['js_count'] = len(soup.find_all('script', src=True))
        
        lazy_images = soup.find_all('img', loading='lazy')
        if lazy_images:
            result['has_lazy_loading'] = True
            result['successes'].append("✅ Lazy loading enabled")
        
        # ===== SECURITY =====
        scripts = soup.find_all('script', src=True)
        for script in scripts:
            src = script.get('src', '')
            if src.startswith('http://') and url.startswith('https://'):
                result['has_mixed_content'] = True
                result['all_issues'].append("⚠️ Mixed content detected")
                result['warnings'] += 1
                break
        
        # ===== CALCULATE SCORE =====
        score = 100
        score -= result['errors'] * 5
        score -= result['warnings'] * 2
        
        # Bonus points
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
        result['is_accessible'] = False
    
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
            if st.session_state.sites:
                st.success(f"✅ Auto-imported {len(st.session_state.sites)} sites!")
            st.session_state.initialized = True
        except Exception as e:
            st.error(f"Error importing sites: {e}")

auto_import_sites()

# ============ MAIN APP ============
st.title("🔍 Complete SEO Audit")
st.markdown("**Full SEO analysis with ALL 50+ metrics - Real Data**")
st.markdown("---")

with st.sidebar:
    st.header("📋 Site Management")
    st.metric("Total Sites", len(st.session_state.sites))
    
    st.markdown("---")
    
    new_url = st.text_input("➕ Add Site", placeholder="example.com")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Add Site", use_container_width=True):
            if new_url:
                if not new_url.startswith('http'):
                    new_url = 'https://' + new_url
                if new_url not in st.session_state.sites:
                    st.session_state.sites.append(new_url)
                    # Save to file
                    with open('sites.txt', 'a') as f:
                        f.write(f"\n{new_url}")
                    st.rerun()
    with col2:
        if st.button("Add Test Sites", use_container_width=True):
            test_sites = [
                "https://google.com",
                "https://github.com", 
                "https://wikipedia.org",
                "https://stackoverflow.com",
                "https://bbc.com"
            ]
            for site in test_sites:
                if site not in st.session_state.sites:
                    st.session_state.sites.append(site)
            st.rerun()
    
    st.markdown("---")
    
    if st.button("🧹 Clear All", use_container_width=True):
        st.session_state.sites = []
        st.session_state.results = {}
        st.session_state.initialized = False
        st.rerun()
    
    st.markdown("---")
    st.caption("**SEO Metrics Checked:**")
    st.caption("✅ Meta Title & Description")
    st.caption("✅ Headings (H1-H6)")
    st.caption("✅ Content Quality")
    st.caption("✅ Internal/External Links")
    st.caption("✅ Broken Links")
    st.caption("✅ Images (Alt Text)")
    st.caption("✅ Schema Markup")
    st.caption("✅ Open Graph Tags")
    st.caption("✅ Twitter Cards")
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
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Audit All Sites", type="primary", use_container_width=True):
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
                    time.sleep(0.5)
                
                st.success(f"✅ Audit complete! {successful} successful, {failed} failed")
                st.rerun()
            else:
                st.warning("No sites to audit. Add sites first!")
    
    with col2:
        if st.button("🔄 Audit Failed Only", use_container_width=True):
            failed_sites = [url for url, result in st.session_state.results.items() if not result.get('is_accessible')]
            if failed_sites:
                progress = st.progress(0)
                status = st.empty()
                total = len(failed_sites)
                successful = 0
                
                for i, url in enumerate(failed_sites):
                    status.text(f"Re-auditing {i+1}/{total}: {url}")
                    result = complete_seo_audit(url)
                    st.session_state.results[url] = result
                    if result.get('is_accessible'):
                        successful += 1
                    progress.progress((i + 1) / total)
                    time.sleep(0.5)
                
                st.success(f"✅ Re-audit complete! {successful} successful")
                st.rerun()
            else:
                st.info("No failed sites to re-audit")
    
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
                
                st.markdown("---")
                
                # META TAGS
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
                
                # HEADINGS
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
                
                st.markdown("---")
                
                # CONTENT
                st.write("### 📄 Content")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Words", result.get('total_words', 0))
                with col2:
                    st.metric("Paragraphs", result.get('paragraph_count', 0))
                with col3:
                    st.metric("Sentences", result.get('sentence_count', 0))
                
                if result.get('top_keywords'):
                    st.write("**Top Keywords:**")
                    keywords_str = ", ".join([f"{word} ({count})" for word, count in result['top_keywords'][:5]])
                    st.write(keywords_str)
                
                st.markdown("---")
                
                # LINKS
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
                
                st.markdown("---")
                
                # IMAGES
                st.write("### 🖼️ Images")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total", result.get('total_images', 0))
                with col2:
                    st.metric("With Alt", result.get('images_with_alt', 0))
                with col3:
                    st.metric("Missing Alt", result.get('images_without_alt', 0))
                
                st.markdown("---")
                
                # SCHEMA
                st.write("### 🏷️ Schema Markup")
                if result.get('has_schema'):
                    st.success(f"✅ Schema: **{result.get('schema_types', '')}**")
                else:
                    st.warning("⚠️ No schema found")
                
                st.markdown("---")
                
                # OPEN GRAPH
                st.write("### 📱 Open Graph")
                if result.get('has_og'):
                    st.success("✅ Open Graph tags present")
                    st.write(f"**Title:** {result.get('og_title', '')}")
                    st.write(f"**Description:** {result.get('og_description', '')[:100]}...")
                else:
                    st.warning("⚠️ Missing Open Graph tags")
                
                st.markdown("---")
                
                # TWITTER
                st.write("### 🐦 Twitter Cards")
                if result.get('has_twitter'):
                    st.success("✅ Twitter Card tags present")
                    st.write(f"**Card:** {result.get('twitter_card', '')}")
                    st.write(f"**Title:** {result.get('twitter_title', '')}")
                else:
                    st.warning("⚠️ Missing Twitter Card tags")
                
                st.markdown("---")
                
                # TECHNICAL
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
                
                st.markdown("---")
                
                # PERFORMANCE
                st.write("### 🚀 Performance")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("CSS", result.get('css_count', 0))
                with col2:
                    st.metric("JS", result.get('js_count', 0))
                with col3:
                    st.metric("Lazy Loading", "✅" if result.get('has_lazy_loading') else "❌")
                
                st.markdown("---")
                
                # SECURITY
                st.write("### 🔒 Security")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("SSL", "✅" if result.get('has_ssl') else "❌")
                with col2:
                    st.metric("Mixed Content", "⚠️" if result.get('has_mixed_content') else "✅")
                
                st.markdown("---")
                
                # MOBILE
                st.write("### 📱 Mobile Friendly")
                if result.get('is_mobile_friendly'):
                    st.success("✅ Mobile friendly")
                else:
                    st.error("❌ Not mobile friendly")
                
                # ISSUES
                if result.get('successes'):
                    st.write("### ✅ Successes")
                    for s in result['successes'][:10]:
                        st.success(s)
                    if len(result['successes']) > 10:
                        st.info(f"... and {len(result['successes']) - 10} more")
                
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
            data.append({
                'Site': url.replace('https://', ''),
                'Score': result.get('score', 0),
                'Errors': result.get('errors', 0),
                'Warnings': result.get('warnings', 0),
                'Title': result.get('title', ''),
                'Description': result.get('meta_description', '')[:100],
                'Total Words': result.get('total_words', 0),
                'Internal Links': result.get('internal_links', 0),
                'External Links': result.get('external_links', 0),
                'Broken Links': result.get('broken_links', 0),
                'Images with Alt': result.get('images_with_alt', 0),
                'Schema': result.get('schema_types', 'No Schema'),
                'Open Graph': result.get('og_title', 'No OG')[:30],
                'Twitter': result.get('twitter_title', 'No Twitter')[:30],
                'SSL': '✅' if result.get('has_ssl') else '❌',
                'Mobile Friendly': '✅' if result.get('is_mobile_friendly') else '❌',
                'Mixed Content': '⚠️' if result.get('has_mixed_content') else '✅',
                'Lazy Loading': '✅' if result.get('has_lazy_loading') else '❌',
                'Accessible': '✅' if result.get('is_accessible') else '❌',
                'Response Time': f"{result.get('response_time', 0)}s"
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
            # Summary statistics
            st.write("**Summary Statistics:**")
            st.write(f"- Average Score: {df['Score'].mean():.1f}/100")
            st.write(f"- Total Sites: {len(df)}")
            st.write(f"- Sites with Errors: {df[df['Errors'] > 0].shape[0]}")
            st.write(f"- Average Words: {df['Total Words'].mean():.0f}")
    else:
        st.info("Run an SEO audit first to generate reports")

st.markdown("---")
st.caption(f"🔄 Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.caption(f"📊 Total Sites: {len(st.session_state.sites)} | Audited: {len(st.session_state.results)}")
st.caption("🚀 Complete SEO Audit | All 50+ Metrics | Real Data")
