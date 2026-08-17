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
import ssl

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

st.set_page_config(
    page_title="Complete SEO Audit", 
    page_icon="🔍", 
    layout="wide"
)

# Session State
if 'sites' not in st.session_state:
    st.session_state.sites = []
if 'results' not in st.session_state:
    st.session_state.results = {}
if 'current_page' not in st.session_state:
    st.session_state.current_page = 1

def get_page_content(url):
    """Get page content with multiple fallback methods"""
    
    # Try multiple approaches
    for attempt in range(3):
        try:
            # Rotate user agents
            headers = get_random_headers()
            
            # Add random delay
            time.sleep(random.uniform(1, 3))
            
            # Try with verify=False for SSL issues
            response = requests.get(
                url, 
                timeout=20, 
                headers=headers, 
                allow_redirects=True,
                verify=False
            )
            
            if response.status_code == 200:
                return response.text, response.status_code
            
            # If 403, try with different headers
            if response.status_code == 403:
                headers = get_random_headers()
                headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                response = requests.get(url, timeout=20, headers=headers, verify=False)
                if response.status_code == 200:
                    return response.text, response.status_code
                continue
                
            return response.text, response.status_code
            
        except requests.exceptions.SSLError:
            # Try without SSL verification
            try:
                response = requests.get(url, timeout=20, headers=get_random_headers(), verify=False)
                if response.status_code == 200:
                    return response.text, response.status_code
            except:
                continue
        except requests.exceptions.Timeout:
            continue
        except requests.exceptions.ConnectionError:
            continue
        except Exception:
            continue
    
    return "", 0

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
        'title': 'N/A',
        'title_length': 0,
        'meta_description': 'N/A',
        'meta_description_length': 0,
        'meta_keywords': 'N/A',
        
        # ===== HEADINGS =====
        'h1_count': 0,
        'h2_count': 0,
        'h3_count': 0,
        'h4_count': 0,
        'h5_count': 0,
        'h6_count': 0,
        'h1_texts': [],
        
        # ===== CONTENT =====
        'total_words': 0,
        'paragraph_count': 0,
        'sentence_count': 0,
        
        # ===== LINKS =====
        'total_links': 0,
        'internal_links': 0,
        'external_links': 0,
        'nofollow_links': 0,
        'broken_links': 0,
        
        # ===== IMAGES =====
        'total_images': 0,
        'images_with_alt': 0,
        'images_without_alt': 0,
        
        # ===== SCHEMA =====
        'has_schema': False,
        'schema_types': [],
        
        # ===== OPEN GRAPH =====
        'has_og': False,
        'og_title': 'N/A',
        'og_description': 'N/A',
        'og_image': 'N/A',
        
        # ===== TWITTER CARDS =====
        'has_twitter': False,
        'twitter_card': 'N/A',
        'twitter_title': 'N/A',
        
        # ===== TECHNICAL =====
        'has_ssl': False,
        'has_viewport': False,
        'has_canonical': False,
        'canonical_url': 'N/A',
        'has_language': False,
        'language': 'N/A',
        'has_robots': False,
        
        # ===== PERFORMANCE =====
        'css_count': 0,
        'js_count': 0,
        'has_lazy_loading': False,
        
        # ===== SECURITY =====
        'has_mixed_content': False,
        
        # ===== MOBILE =====
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
        # 2. HEADINGS
        # ============================================
        h1_tags = soup.find_all('h1')
        result['h1_count'] = len(h1_tags)
        result['h1_texts'] = [h.text.strip() for h in h1_tags if h.text.strip()]
        
        if result['h1_count'] == 0:
            result['all_issues'].append("❌ No H1 heading found")
            result['errors'] += 1
        elif result['h1_count'] == 1:
            result['successes'].append("✅ Exactly one H1 heading")
        else:
            result['all_issues'].append(f"⚠️ Multiple H1 tags: {result['h1_count']}")
            result['warnings'] += 1
        
        result['h2_count'] = len(soup.find_all('h2'))
        result['h3_count'] = len(soup.find_all('h3'))
        result['h4_count'] = len(soup.find_all('h4'))
        result['h5_count'] = len(soup.find_all('h5'))
        result['h6_count'] = len(soup.find_all('h6'))
        
        # ============================================
        # 3. CONTENT
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
        
        if result['total_words'] < 100:
            result['all_issues'].append(f"❌ Very low word count: {result['total_words']} words")
            result['errors'] += 1
        elif result['total_words'] < 300:
            result['all_issues'].append(f"⚠️ Low word count: {result['total_words']} words")
            result['warnings'] += 1
        else:
            result['successes'].append(f"✅ Good word count: {result['total_words']} words")
        
        # ============================================
        # 4. LINKS
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
                else:
                    external += 1
            elif href.startswith('/') or href.startswith('#'):
                internal += 1
        
        result['internal_links'] = internal
        result['external_links'] = external
        result['nofollow_links'] = nofollow
        
        if result['internal_links'] == 0:
            result['all_issues'].append("⚠️ No internal links found")
            result['warnings'] += 1
        if result['external_links'] == 0:
            result['all_issues'].append("⚠️ No external links found")
            result['warnings'] += 1
        
        # Broken links check
        broken = 0
        for link in all_links[:10]:
            href = link.get('href', '')
            if href.startswith('http'):
                try:
                    resp = requests.head(href, timeout=3, allow_redirects=True)
                    if resp.status_code >= 400:
                        broken += 1
                except:
                    broken += 1
        
        result['broken_links'] = broken
        if broken > 0:
            result['all_issues'].append(f"❌ {broken} broken links found")
            result['errors'] += 1
        
        # ============================================
        # 5. IMAGES
        # ============================================
        images = soup.find_all('img')
        result['total_images'] = len(images)
        
        with_alt = 0
        without_alt = 0
        
        for img in images:
            if img.get('alt', '').strip():
                with_alt += 1
            else:
                without_alt += 1
        
        result['images_with_alt'] = with_alt
        result['images_without_alt'] = without_alt
        
        if without_alt > 0:
            result['all_issues'].append(f"❌ {without_alt} images missing alt text")
            result['errors'] += 1
        
        # ============================================
        # 6. SCHEMA
        # ============================================
        schema_scripts = soup.find_all('script', attrs={'type': 'application/ld+json'})
        if schema_scripts:
            result['has_schema'] = True
            for script in schema_scripts[:3]:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        schema_type = data.get('@type', 'Unknown')
                        result['schema_types'].append(schema_type)
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict):
                                schema_type = item.get('@type', 'Unknown')
                                result['schema_types'].append(schema_type)
                except:
                    pass
            result['successes'].append(f"✅ Schema found: {result['schema_types'][:3]}")
        else:
            result['all_issues'].append("⚠️ No schema markup found")
            result['warnings'] += 1
        
        # ============================================
        # 7. OPEN GRAPH
        # ============================================
        og_title = soup.find('meta', attrs={'property': 'og:title'})
        og_desc = soup.find('meta', attrs={'property': 'og:description'})
        og_image = soup.find('meta', attrs={'property': 'og:image'})
        
        if og_title or og_desc or og_image:
            result['has_og'] = True
            result['og_title'] = og_title.get('content', 'N/A') if og_title else 'N/A'
            result['og_description'] = og_desc.get('content', 'N/A') if og_desc else 'N/A'
            result['og_image'] = og_image.get('content', 'N/A') if og_image else 'N/A'
            result['successes'].append("✅ Open Graph tags present")
        else:
            result['all_issues'].append("⚠️ Missing Open Graph tags")
            result['warnings'] += 1
        
        # ============================================
        # 8. TWITTER CARDS
        # ============================================
        twitter_card = soup.find('meta', attrs={'name': 'twitter:card'})
        twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})
        
        if twitter_card or twitter_title:
            result['has_twitter'] = True
            result['twitter_card'] = twitter_card.get('content', 'N/A') if twitter_card else 'N/A'
            result['twitter_title'] = twitter_title.get('content', 'N/A') if twitter_title else 'N/A'
            result['successes'].append("✅ Twitter Card tags present")
        else:
            result['all_issues'].append("⚠️ Missing Twitter Card tags")
            result['warnings'] += 1
        
        # ============================================
        # 9. TECHNICAL SEO
        # ============================================
        viewport = soup.find('meta', attrs={'name': 'viewport'})
        if viewport:
            result['has_viewport'] = True
            result['is_mobile_friendly'] = True
            result['successes'].append("✅ Viewport found - mobile friendly")
        else:
            result['all_issues'].append("❌ Missing viewport meta tag")
            result['errors'] += 1
        
        canonical = soup.find('link', attrs={'rel': 'canonical'})
        if canonical:
            result['has_canonical'] = True
            result['canonical_url'] = canonical.get('href', 'N/A')
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
            if 'noindex' in robots.get('content', '').lower():
                result['all_issues'].append("❌ Page is marked noindex")
                result['errors'] += 1
            if 'nofollow' in robots.get('content', '').lower():
                result['all_issues'].append("⚠️ Page is marked nofollow")
                result['warnings'] += 1
        
        # ============================================
        # 10. PERFORMANCE
        # ============================================
        result['css_count'] = len(soup.find_all('link', rel='stylesheet'))
        result['js_count'] = len(soup.find_all('script', src=True))
        
        lazy_images = soup.find_all('img', loading='lazy')
        if lazy_images:
            result['has_lazy_loading'] = True
            result['successes'].append("✅ Lazy loading enabled")
        
        # ============================================
        # 11. SECURITY
        # ============================================
        scripts = soup.find_all('script', src=True)
        for script in scripts:
            src = script.get('src', '')
            if src.startswith('http://') and url.startswith('https://'):
                result['has_mixed_content'] = True
                break
        
        if result['has_mixed_content']:
            result['all_issues'].append("⚠️ Mixed content detected")
            result['warnings'] += 1
        
        # ============================================
        # CALCULATE SCORE
        # ============================================
        score = 100
        score -= result['errors'] * 5
        score -= result['warnings'] * 2
        
        # Bonuses
        if result['title'] != 'N/A' and 30 <= result['title_length'] <= 60:
            score += 3
        if result['meta_description'] != 'N/A' and 50 <= result['meta_description_length'] <= 160:
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
        if result['images_with_alt'] > 0 and result['images_without_alt'] == 0:
            score += 2
        
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
                    'Title': r.get('title', 'N/A')[:50],
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
                    st.write(f"**Title:** {result.get('title', 'N/A')}")
                    st.write(f"**Length:** {result.get('title_length', 0)} chars")
                with col2:
                    st.write(f"**Description:** {result.get('meta_description', 'N/A')}")
                    st.write(f"**Length:** {result.get('meta_description_length', 0)} chars")
                
                # Headings
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
                
                # Content
                st.write("### 📄 Content")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Words", result.get('total_words', 0))
                with col2:
                    st.metric("Paragraphs", result.get('paragraph_count', 0))
                with col3:
                    st.metric("Sentences", result.get('sentence_count', 0))
                
                # Links
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
                
                # Images
                st.write("### 🖼️ Images")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total", result.get('total_images', 0))
                with col2:
                    st.metric("With Alt", result.get('images_with_alt', 0))
                with col3:
                    st.metric("Missing Alt", result.get('images_without_alt', 0))
                
                # Schema
                st.write("### 🏷️ Schema")
                if result.get('has_schema'):
                    st.success(f"✅ Schema found: {result.get('schema_types', [])}")
                else:
                    st.warning("⚠️ No schema found")
                
                # Open Graph
                st.write("### 📱 Open Graph")
                if result.get('has_og'):
                    st.success("✅ Open Graph tags present")
                    st.write(f"**Title:** {result.get('og_title', 'N/A')}")
                    st.write(f"**Description:** {result.get('og_description', 'N/A')[:100]}")
                else:
                    st.warning("⚠️ Missing Open Graph tags")
                
                # Twitter Cards
                st.write("### 🐦 Twitter Cards")
                if result.get('has_twitter'):
                    st.success("✅ Twitter Card tags present")
                    st.write(f"**Card:** {result.get('twitter_card', 'N/A')}")
                    st.write(f"**Title:** {result.get('twitter_title', 'N/A')}")
                else:
                    st.warning("⚠️ Missing Twitter Card tags")
                
                # Technical
                st.write("### ⚙️ Technical SEO")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("SSL", "✅" if result.get('has_ssl') else "❌")
                with col2:
                    st.metric("Viewport", "✅" if result.get('has_viewport') else "❌")
                with col3:
                    st.metric("Canonical", "✅" if result.get('has_canonical') else "❌")
                with col4:
                    st.metric("Language", result.get('language', 'N/A'))
                
                # Performance
                st.write("### 🚀 Performance")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("CSS Files", result.get('css_count', 0))
                with col2:
                    st.metric("JS Files", result.get('js_count', 0))
                with col3:
                    st.metric("Lazy Loading", "✅" if result.get('has_lazy_loading') else "❌")
                
                # Security
                st.write("### 🔒 Security")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("SSL", "✅" if result.get('has_ssl') else "❌")
                with col2:
                    st.metric("Mixed Content", "⚠️" if result.get('has_mixed_content') else "✅")
                
                # Mobile
                st.write("### 📱 Mobile Friendly")
                if result.get('is_mobile_friendly'):
                    st.success("✅ Mobile friendly")
                else:
                    st.error("❌ Not mobile friendly")
                
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
            data.append({
                'Site': url.replace('https://', ''),
                'Score': result.get('score', 0),
                'Errors': result.get('errors', 0),
                'Warnings': result.get('warnings', 0),
                'Title': result.get('title', 'N/A')[:50],
                'Description': result.get('meta_description', 'N/A')[:50],
                'Total Words': result.get('total_words', 0),
                'Internal Links': result.get('internal_links', 0),
                'External Links': result.get('external_links', 0),
                'Broken Links': result.get('broken_links', 0),
                'Images with Alt': result.get('images_with_alt', 0),
                'Schema': '✅' if result.get('has_schema') else '❌',
                'Open Graph': '✅' if result.get('has_og') else '❌',
                'Twitter Cards': '✅' if result.get('has_twitter') else '❌',
                'SSL': '✅' if result.get('has_ssl') else '❌',
                'Mobile Friendly': '✅' if result.get('is_mobile_friendly') else '❌',
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
    st.caption("🚀 Complete SEO Audit | All Metrics Included")
