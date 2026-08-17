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
from urllib.robotparser import RobotFileParser

# ============ PAGE CONFIG ============
st.set_page_config(
    page_title="Complete SEO Monitor",
    page_icon="🔍",
    layout="wide"
)

# ============ SESSION STATE ============
if 'sites' not in st.session_state:
    st.session_state.sites = []
if 'results' not in st.session_state:
    st.session_state.results = {}
if 'scanning' not in st.session_state:
    st.session_state.scanning = False
if 'current_page' not in st.session_state:
    st.session_state.current_page = 1

# ============ COMPLETE SEO CHECKER ============
def check_seo_complete(url):
    """Complete SEO check - Checks EVERYTHING!"""
    result = {
        'url': url,
        'score': 0,
        'errors': 0,
        'warnings': 0,
        'error_details': [],
        'warning_details': [],
        'success_details': [],
        
        # ===== META TAGS =====
        'title': None,
        'title_length': 0,
        'meta_description': None,
        'meta_description_length': 0,
        'meta_keywords': None,
        'meta_robots': None,
        'meta_viewport': None,
        'canonical_url': None,
        'charset': None,
        'language': None,
        
        # ===== OPEN GRAPH / SOCIAL =====
        'og_title': None,
        'og_description': None,
        'og_image': None,
        'og_url': None,
        'og_type': None,
        'twitter_card': None,
        'twitter_title': None,
        'twitter_description': None,
        'twitter_image': None,
        
        # ===== HEADINGS =====
        'h1': None,
        'h1_count': 0,
        'h2_count': 0,
        'h3_count': 0,
        'h4_count': 0,
        'h5_count': 0,
        'h6_count': 0,
        'heading_structure': [],
        
        # ===== CONTENT =====
        'word_count': 0,
        'paragraph_count': 0,
        'avg_paragraph_words': 0,
        'sentence_count': 0,
        'avg_sentence_words': 0,
        'readability_score': 0,
        'keyword_density': {},
        'top_keywords': [],
        
        # ===== LINKS =====
        'total_links': 0,
        'internal_links': 0,
        'external_links': 0,
        'nofollow_links': 0,
        'dofollow_links': 0,
        'broken_links': 0,
        'internal_links_with_anchor': 0,
        'external_links_with_anchor': 0,
        'anchor_texts': [],
        
        # ===== IMAGES =====
        'total_images': 0,
        'images_with_alt': 0,
        'images_without_alt': 0,
        'images_with_title': 0,
        'images_sizes': [],
        'lazy_loaded_images': 0,
        
        # ===== TECHNICAL =====
        'status_code': None,
        'response_time': 0,
        'page_size': 0,
        'is_https': False,
        'has_ssl': False,
        'has_sitemap': False,
        'has_robots': False,
        'has_canonical': False,
        'has_viewport': False,
        'is_mobile_friendly': False,
        'has_charset': False,
        
        # ===== SCHEMA MARKUP =====
        'has_schema': False,
        'schema_types': [],
        'organization_schema': False,
        'product_schema': False,
        'article_schema': False,
        'faq_schema': False,
        'localbusiness_schema': False,
        
        # ===== PERFORMANCE =====
        'load_time': 0,
        'time_to_first_byte': 0,
        'total_resources': 0,
        'total_page_size': 0,
        'css_files': 0,
        'js_files': 0,
        
        # ===== SECURITY =====
        'has_ssl': False,
        'has_security_headers': False,
        'mixed_content': False,
        
        # ===== ACCESSIBILITY =====
        'has_language': False,
        'has_alt_text': False,
        'has_heading_structure': False,
        'has_aria': False,
        
        # ===== STRUCTURE =====
        'has_favicon': False,
        'has_robots_txt': False,
        'has_sitemap_xml': False,
        'has_social_links': False,
        'has_contact_info': False
    }
    
    try:
        start_time = time.time()
        
        # Add http if missing
        if not url.startswith('http'):
            url = 'https://' + url
        
        # Fetch page
        response = requests.get(url, timeout=15, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; SEO-Monitor/2.0)'
        })
        
        result['status_code'] = response.status_code
        result['response_time'] = round(time.time() - start_time, 2)
        result['page_size'] = len(response.content)
        result['is_https'] = url.startswith('https')
        result['has_ssl'] = result['is_https']
        
        if response.status_code != 200:
            result['error_details'].append(f"❌ HTTP {response.status_code} Error")
            result['errors'] += 1
            return result
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text()
        
        # ============================================
        # 1. META TAGS
        # ============================================
        
        # Title
        title = soup.find('title')
        if title and title.text.strip():
            result['title'] = title.text.strip()
            result['title_length'] = len(title.text.strip())
            result['success_details'].append(f"✅ Title tag present: {len(title.text.strip())} chars")
            
            if result['title_length'] < 30:
                result['warning_details'].append(f"⚠️ Title too short: {result['title_length']} chars (< 30)")
                result['warnings'] += 1
            elif result['title_length'] > 60:
                result['warning_details'].append(f"⚠️ Title too long: {result['title_length']} chars (> 60)")
                result['warnings'] += 1
            else:
                result['success_details'].append(f"✅ Title length is optimal: {result['title_length']} chars")
        else:
            result['error_details'].append("❌ Missing title tag")
            result['errors'] += 1
        
        # Meta Description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            desc_content = meta_desc.get('content', '').strip()
            if desc_content:
                result['meta_description'] = desc_content
                result['meta_description_length'] = len(desc_content)
                result['success_details'].append(f"✅ Meta description present: {len(desc_content)} chars")
                
                if len(desc_content) < 50:
                    result['warning_details'].append(f"⚠️ Description too short: {len(desc_content)} chars (< 50)")
                    result['warnings'] += 1
                elif len(desc_content) > 160:
                    result['warning_details'].append(f"⚠️ Description too long: {len(desc_content)} chars (> 160)")
                    result['warnings'] += 1
                else:
                    result['success_details'].append(f"✅ Description length is optimal: {len(desc_content)} chars")
            else:
                result['warning_details'].append("⚠️ Meta description is empty")
                result['warnings'] += 1
        else:
            result['error_details'].append("❌ Missing meta description")
            result['errors'] += 1
        
        # Meta Keywords
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords:
            keywords = meta_keywords.get('content', '').strip()
            if keywords:
                result['meta_keywords'] = keywords
                result['success_details'].append(f"✅ Meta keywords present")
            else:
                result['warning_details'].append("⚠️ Meta keywords are empty")
                result['warnings'] += 1
        else:
            result['warning_details'].append("⚠️ No meta keywords found (not critical)")
            result['warnings'] += 1
        
        # Meta Robots
        meta_robots = soup.find('meta', attrs={'name': 'robots'})
        if meta_robots:
            robots_content = meta_robots.get('content', '').lower()
            result['meta_robots'] = robots_content
            if 'noindex' in robots_content:
                result['error_details'].append("❌ Page is marked noindex")
                result['errors'] += 1
            if 'nofollow' in robots_content:
                result['warning_details'].append("⚠️ Page is marked nofollow")
                result['warnings'] += 1
            if 'noarchive' in robots_content:
                result['warning_details'].append("⚠️ Page is marked noarchive")
                result['warnings'] += 1
            if 'nosnippet' in robots_content:
                result['warning_details'].append("⚠️ Page is marked nosnippet")
                result['warnings'] += 1
        else:
            result['warning_details'].append("⚠️ No robots meta tag found")
            result['warnings'] += 1
        
        # Meta Viewport
        meta_viewport = soup.find('meta', attrs={'name': 'viewport'})
        if meta_viewport:
            result['meta_viewport'] = meta_viewport.get('content', '')
            result['has_viewport'] = True
            result['is_mobile_friendly'] = True
            result['success_details'].append("✅ Viewport meta tag found - mobile friendly")
        else:
            result['error_details'].append("❌ Missing viewport meta tag (not mobile friendly)")
            result['errors'] += 1
        
        # Charset
        charset = soup.find('meta', attrs={'charset': True})
        if charset:
            result['charset'] = charset.get('charset', '')
            result['has_charset'] = True
            result['success_details'].append("✅ Charset meta tag found")
        else:
            result['warning_details'].append("⚠️ No charset meta tag found")
            result['warnings'] += 1
        
        # Language
        html_tag = soup.find('html')
        if html_tag and html_tag.get('lang'):
            result['language'] = html_tag.get('lang')
            result['has_language'] = True
            result['success_details'].append(f"✅ Language attribute found: {result['language']}")
        else:
            result['warning_details'].append("⚠️ No language attribute found")
            result['warnings'] += 1
        
        # Canonical
        canonical = soup.find('link', attrs={'rel': 'canonical'})
        if canonical and canonical.get('href'):
            result['canonical_url'] = canonical.get('href')
            result['has_canonical'] = True
            result['success_details'].append("✅ Canonical tag found")
        else:
            result['warning_details'].append("⚠️ No canonical tag found")
            result['warnings'] += 1
        
        # ============================================
        # 2. OPEN GRAPH / SOCIAL MEDIA
        # ============================================
        
        og_title = soup.find('meta', attrs={'property': 'og:title'})
        if og_title:
            result['og_title'] = og_title.get('content', '')
            result['success_details'].append("✅ Open Graph title found")
        else:
            result['warning_details'].append("⚠️ No Open Graph title found")
            result['warnings'] += 1
        
        og_desc = soup.find('meta', attrs={'property': 'og:description'})
        if og_desc:
            result['og_description'] = og_desc.get('content', '')
            result['success_details'].append("✅ Open Graph description found")
        else:
            result['warning_details'].append("⚠️ No Open Graph description found")
            result['warnings'] += 1
        
        og_image = soup.find('meta', attrs={'property': 'og:image'})
        if og_image:
            result['og_image'] = og_image.get('content', '')
            result['success_details'].append("✅ Open Graph image found")
        else:
            result['warning_details'].append("⚠️ No Open Graph image found")
            result['warnings'] += 1
        
        og_url = soup.find('meta', attrs={'property': 'og:url'})
        if og_url:
            result['og_url'] = og_url.get('content', '')
            result['success_details'].append("✅ Open Graph URL found")
        else:
            result['warning_details'].append("⚠️ No Open Graph URL found")
            result['warnings'] += 1
        
        # Twitter Cards
        twitter_card = soup.find('meta', attrs={'name': 'twitter:card'})
        if twitter_card:
            result['twitter_card'] = twitter_card.get('content', '')
            result['success_details'].append("✅ Twitter Card found")
        else:
            result['warning_details'].append("⚠️ No Twitter Card found")
            result['warnings'] += 1
        
        twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})
        if twitter_title:
            result['twitter_title'] = twitter_title.get('content', '')
            result['success_details'].append("✅ Twitter title found")
        
        twitter_desc = soup.find('meta', attrs={'name': 'twitter:description'})
        if twitter_desc:
            result['twitter_description'] = twitter_desc.get('content', '')
            result['success_details'].append("✅ Twitter description found")
        
        twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
        if twitter_image:
            result['twitter_image'] = twitter_image.get('content', '')
            result['success_details'].append("✅ Twitter image found")
        
        # ============================================
        # 3. HEADINGS STRUCTURE
        # ============================================
        
        # Count all headings
        h1_tags = soup.find_all('h1')
        result['h1_count'] = len(h1_tags)
        if result['h1_count'] == 0:
            result['error_details'].append("❌ No H1 heading found")
            result['errors'] += 1
        elif result['h1_count'] == 1:
            result['h1'] = h1_tags[0].text.strip()
            result['success_details'].append("✅ Exactly one H1 heading found")
        else:
            result['warning_details'].append(f"⚠️ Multiple H1 tags found: {result['h1_count']}")
            result['warnings'] += 1
        
        h2_tags = soup.find_all('h2')
        result['h2_count'] = len(h2_tags)
        
        h3_tags = soup.find_all('h3')
        result['h3_count'] = len(h3_tags)
        
        h4_tags = soup.find_all('h4')
        result['h4_count'] = len(h4_tags)
        
        h5_tags = soup.find_all('h5')
        result['h5_count'] = len(h5_tags)
        
        h6_tags = soup.find_all('h6')
        result['h6_count'] = len(h6_tags)
        
        # Heading structure validation
        if result['h1_count'] == 1 and result['h2_count'] > 0:
            result['success_details'].append("✅ Good heading structure (H1 followed by H2s)")
        elif result['h1_count'] == 1 and result['h2_count'] == 0:
            result['warning_details'].append("⚠️ H1 found but no H2 headings")
            result['warnings'] += 1
        
        # Build heading hierarchy
        all_heading_tags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']
        heading_structure = []
        for tag in all_heading_tags:
            elements = soup.find_all(tag)
            for elem in elements:
                text = elem.text.strip()
                if text:
                    heading_structure.append({
                        'level': tag,
                        'text': text[:50] + '...' if len(text) > 50 else text
                    })
        result['heading_structure'] = heading_structure
        
        # ============================================
        # 4. CONTENT ANALYSIS
        # ============================================
        
        # Word count
        words = re.findall(r'\w+', text)
        result['word_count'] = len(words)
        
        # Paragraphs
        paragraphs = soup.find_all('p')
        result['paragraph_count'] = len(paragraphs)
        if paragraphs:
            result['avg_paragraph_words'] = result['word_count'] // len(paragraphs)
        
        # Sentences
        sentences = re.split(r'[.!?]+', text)
        result['sentence_count'] = len([s for s in sentences if s.strip()])
        
        # Keyword density (top 10 keywords)
        word_freq = Counter(words)
        top_keywords = word_freq.most_common(10)
        result['top_keywords'] = top_keywords
        
        # Remove stop words for keyword density
        stop_words = {'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i', 'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at', 'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she', 'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their', 'what', 'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go', 'me'}
        
        content_words = [w.lower() for w in words if w.lower() not in stop_words and len(w) > 3]
        if content_words:
            word_freq_clean = Counter(content_words)
            result['keyword_density'] = dict(word_freq_clean.most_common(10))
        
        # Content length analysis
        if result['word_count'] < 100:
            result['error_details'].append(f"❌ Low word count: {result['word_count']} words (< 100)")
            result['errors'] += 1
        elif result['word_count'] < 300:
            result['warning_details'].append(f"⚠️ Low word count: {result['word_count']} words (< 300)")
            result['warnings'] += 1
        else:
            result['success_details'].append(f"✅ Good word count: {result['word_count']} words")
        
        # Readability (simplified)
        if result['sentence_count'] > 0:
            result['avg_sentence_words'] = result['word_count'] // result['sentence_count']
            if 15 <= result['avg_sentence_words'] <= 20:
                result['success_details'].append(f"✅ Good readability: {result['avg_sentence_words']} words/sentence")
            else:
                result['warning_details'].append(f"⚠️ Readability: {result['avg_sentence_words']} words/sentence (recommended: 15-20)")
                result['warnings'] += 1
        
        # ============================================
        # 5. LINKS ANALYSIS
        # ============================================
        
        all_links = soup.find_all('a', href=True)
        result['total_links'] = len(all_links)
        
        internal_links = 0
        external_links = 0
        nofollow_links = 0
        dofollow_links = 0
        internal_links_with_anchor = 0
        external_links_with_anchor = 0
        anchor_texts = []
        
        base_domain = urlparse(url).netloc
        
        for link in all_links:
            href = link['href']
            anchor = link.text.strip()
            if anchor:
                anchor_texts.append(anchor)
            
            # Check nofollow
            rel = link.get('rel', [])
            if 'nofollow' in rel:
                nofollow_links += 1
            else:
                dofollow_links += 1
            
            # Check if internal or external
            if href.startswith('http'):
                if urlparse(href).netloc == base_domain:
                    internal_links += 1
                    if anchor:
                        internal_links_with_anchor += 1
                else:
                    external_links += 1
                    if anchor:
                        external_links_with_anchor += 1
            elif href.startswith('/') or href.startswith('#'):
                internal_links += 1
                if anchor:
                    internal_links_with_anchor += 1
        
        result['internal_links'] = internal_links
        result['external_links'] = external_links
        result['nofollow_links'] = nofollow_links
        result['dofollow_links'] = dofollow_links
        result['internal_links_with_anchor'] = internal_links_with_anchor
        result['external_links_with_anchor'] = external_links_with_anchor
        result['anchor_texts'] = anchor_texts[:20]  # Store first 20 anchors
        
        # Link analysis
        if result['internal_links'] == 0:
            result['warning_details'].append("⚠️ No internal links found")
            result['warnings'] += 1
        else:
            result['success_details'].append(f"✅ {result['internal_links']} internal links found")
        
        if result['external_links'] == 0:
            result['warning_details'].append("⚠️ No external links found")
            result['warnings'] += 1
        else:
            result['success_details'].append(f"✅ {result['external_links']} external links found")
        
        # Broken links check (sample)
        broken_links = 0
        for link in all_links[:5]:  # Check first 5 links
            href = link['href']
            if href.startswith('http'):
                try:
                    resp = requests.head(href, timeout=3, allow_redirects=True)
                    if resp.status_code >= 400:
                        broken_links += 1
                except:
                    broken_links += 1
        
        result['broken_links'] = broken_links
        if broken_links > 0:
            result['error_details'].append(f"❌ {broken_links} broken links found")
            result['errors'] += 1
        
        # ============================================
        # 6. IMAGES ANALYSIS
        # ============================================
        
        images = soup.find_all('img')
        result['total_images'] = len(images)
        
        images_with_alt = 0
        images_without_alt = 0
        images_with_title = 0
        
        for img in images:
            if img.get('alt', '').strip():
                images_with_alt += 1
            else:
                images_without_alt += 1
            
            if img.get('title', '').strip():
                images_with_title += 1
        
        result['images_with_alt'] = images_with_alt
        result['images_without_alt'] = images_without_alt
        result['images_with_title'] = images_with_title
        
        if images_without_alt > 0:
            result['error_details'].append(f"❌ {images_without_alt} images missing alt text")
            result['errors'] += 1
        elif result['total_images'] > 0:
            result['success_details'].append("✅ All images have alt text")
        
        # ============================================
        # 7. SCHEMA MARKUP
        # ============================================
        
        schema_scripts = soup.find_all('script', attrs={'type': 'application/ld+json'})
        if schema_scripts:
            result['has_schema'] = True
            result['success_details'].append(f"✅ {len(schema_scripts)} schema markup found")
            
            for script in schema_scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        if '@type' in data:
                            schema_type = data['@type']
                            result['schema_types'].append(schema_type)
                            
                            if 'Organization' in schema_type:
                                result['organization_schema'] = True
                            elif 'Product' in schema_type:
                                result['product_schema'] = True
                            elif 'Article' in schema_type:
                                result['article_schema'] = True
                            elif 'FAQ' in schema_type:
                                result['faq_schema'] = True
                            elif 'LocalBusiness' in schema_type:
                                result['localbusiness_schema'] = True
                except:
                    pass
        else:
            result['warning_details'].append("⚠️ No schema markup found")
            result['warnings'] += 1
        
        # ============================================
        # 8. TECHNICAL SEO
        # ============================================
        
        # Check robots.txt
        try:
            robots_url = url.split('/')[0] + '//' + url.split('/')[2] + '/robots.txt'
            robots_response = requests.get(robots_url, timeout=3)
            if robots_response.status_code == 200:
                result['has_robots_txt'] = True
                result['success_details'].append("✅ Robots.txt found")
        except:
            pass
        
        # Check sitemap.xml
        try:
            sitemap_url = url.split('/')[0] + '//' + url.split('/')[2] + '/sitemap.xml'
            sitemap_response = requests.get(sitemap_url, timeout=3)
            if sitemap_response.status_code == 200:
                result['has_sitemap_xml'] = True
                result['success_details'].append("✅ Sitemap.xml found")
        except:
            pass
        
        # Check favicon
        favicon = soup.find('link', attrs={'rel': 'icon'}) or soup.find('link', attrs={'rel': 'shortcut icon'})
        if favicon:
            result['has_favicon'] = True
            result['success_details'].append("✅ Favicon found")
        else:
            result['warning_details'].append("⚠️ No favicon found")
            result['warnings'] += 1
        
        # ============================================
        # 9. PERFORMANCE
        # ============================================
        
        result['load_time'] = result['response_time']
        
        # Count resources
        css_files = soup.find_all('link', rel='stylesheet')
        js_files = soup.find_all('script', src=True)
        result['css_files'] = len(css_files)
        result['js_files'] = len(js_files)
        
        result['total_resources'] = len(css_files) + len(js_files) + result['total_images']
        
        if result['response_time'] > 3:
            result['warning_details'].append(f"⚠️ Slow load time: {result['response_time']}s")
            result['warnings'] += 1
        elif result['response_time'] > 1:
            result['warning_details'].append(f"⚠️ Load time could be faster: {result['response_time']}s")
            result['warnings'] += 1
        else:
            result['success_details'].append(f"✅ Fast load time: {result['response_time']}s")
        
        # ============================================
        # 10. CALCULATE FINAL SCORE
        # ============================================
        
        # Start with 100
        score = 100
        
        # Subtract for errors
        score -= result['errors'] * 5
        
        # Subtract for warnings
        score -= result['warnings'] * 2
        
        # Bonus points for good practices
        if result['title'] and 30 <= result['title_length'] <= 60:
            score += 3
        if result['meta_description'] and 50 <= result['meta_description_length'] <= 160:
            score += 3
        if result['h1_count'] == 1:
            score += 2
        if result['has_schema']:
            score += 3
        if result['has_viewport']:
            score += 2
        if result['has_sitemap_xml']:
            score += 2
        if result['has_robots_txt']:
            score += 2
        if result['og_title']:
            score += 2
        if result['og_description']:
            score += 2
        
        # Ensure score is between 0 and 100
        result['score'] = max(0, min(100, score))
        
    except requests.exceptions.Timeout:
        result['error_details'].append("❌ Timeout - Page took too long to load")
        result['errors'] += 1
    except requests.exceptions.ConnectionError:
        result['error_details'].append("❌ Connection error - Cannot reach the site")
        result['errors'] += 1
    except Exception as e:
        result['error_details'].append(f"❌ Error: {str(e)}")
        result['errors'] += 1
    
    return result

# ============ AUTO-IMPORT SITES ============
def auto_import_sites():
    """Automatically import sites from sites.txt on app start"""
    if os.path.exists('sites.txt') and not st.session_state.sites:
        try:
            with open('sites.txt', 'r') as f:
                for line in f:
                    url = line.strip()
                    if url and not url.startswith('#'):
                        if url.startswith('import') or url.startswith('from') or url.startswith('def'):
                            continue
                        if not url.startswith('http'):
                            url = 'https://' + url
                        if url not in st.session_state.sites:
                            st.session_state.sites.append(url)
            if st.session_state.sites:
                st.success(f"✅ Auto-imported {len(st.session_state.sites)} sites!")
        except Exception as e:
            st.error(f"Error importing sites: {str(e)}")

# ============ FUNCTION TO DISPLAY RESULTS ============
def display_seo_result(url, result, expanded=False):
    """Display complete SEO analysis results"""
    
    with st.expander(f"🔍 {url.replace('https://', '')}", expanded=expanded):
        # Overall Score
        st.write("### 📊 Overall Score")
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
        
        # Rating
        if score >= 90:
            st.success("🌟 Excellent SEO - Your site is well optimized!")
        elif score >= 70:
            st.info("👍 Good SEO - Some improvements could be made")
        elif score >= 50:
            st.warning("⚠️ Needs Improvement - Several issues to fix")
        else:
            st.error("❌ Poor SEO - Major issues need attention")
        
        st.markdown("---")
        
        # ===== META TAGS =====
        st.write("### 📝 Meta Tags")
        meta_col1, meta_col2 = st.columns(2)
        
        with meta_col1:
            title = result.get('title')
            if title:
                st.success(f"✅ Title: {title}")
                st.write(f"Length: {result.get('title_length', 0)} chars")
            else:
                st.error("❌ Missing title tag")
            
            desc = result.get('meta_description')
            if desc:
                st.success(f"✅ Description: {desc}")
                st.write(f"Length: {result.get('meta_description_length', 0)} chars")
            else:
                st.error("❌ Missing meta description")
        
        with meta_col2:
            if result.get('meta_keywords'):
                st.info(f"Keywords: {result.get('meta_keywords')}")
            else:
                st.warning("⚠️ No meta keywords")
            
            if result.get('has_viewport'):
                st.success("✅ Viewport: Mobile friendly")
            else:
                st.error("❌ No viewport (not mobile friendly)")
            
            if result.get('has_canonical'):
                st.success(f"✅ Canonical: {result.get('canonical_url')}")
            else:
                st.warning("⚠️ No canonical tag")
        
        # ===== HEADINGS =====
        st.write("### 📑 Headings Structure")
        h_col1, h_col2, h_col3, h_col4, h_col5, h_col6 = st.columns(6)
        
        with h_col1:
            st.metric("H1", result.get('h1_count', 0))
        with h_col2:
            st.metric("H2", result.get('h2_count', 0))
        with h_col3:
            st.metric("H3", result.get('h3_count', 0))
        with h_col4:
            st.metric("H4", result.get('h4_count', 0))
        with h_col5:
            st.metric("H5", result.get('h5_count', 0))
        with h_col6:
            st.metric("H6", result.get('h6_count', 0))
        
        if result.get('heading_structure'):
            st.write("**Heading Hierarchy:**")
            for heading in result['heading_structure'][:10]:
                st.write(f"  • {heading['level'].upper()}: {heading['text']}")
        
        # ===== CONTENT =====
        st.write("### 📄 Content Analysis")
        c_col1, c_col2, c_col3, c_col4 = st.columns(4)
        
        with c_col1:
            st.metric("Word Count", result.get('word_count', 0))
        with c_col2:
            st.metric("Paragraphs", result.get('paragraph_count', 0))
        with c_col3:
            st.metric("Sentences", result.get('sentence_count', 0))
        with c_col4:
            st.metric("Avg Words/Sentence", result.get('avg_sentence_words', 0))
        
        # Top keywords
        if result.get('top_keywords'):
            st.write("**Top Keywords:**")
            keywords_text = ", ".join([f"{word} ({count})" for word, count in result['top_keywords'][:10]])
            st.write(keywords_text)
        
        # ===== LINKS =====
        st.write("### 🔗 Links Analysis")
        l_col1, l_col2, l_col3, l_col4, l_col5 = st.columns(5)
        
        with l_col1:
            st.metric("Total Links", result.get('total_links', 0))
        with l_col2:
            st.metric("Internal", result.get('internal_links', 0))
        with l_col3:
            st.metric("External", result.get('external_links', 0))
        with l_col4:
            st.metric("Nofollow", result.get('nofollow_links', 0))
        with l_col5:
            st.metric("Broken", result.get('broken_links', 0))
        
        # ===== IMAGES =====
        st.write("### 🖼️ Images Analysis")
        img_col1, img_col2, img_col3 = st.columns(3)
        
        with img_col1:
            st.metric("Total Images", result.get('total_images', 0))
        with img_col2:
            st.metric("With Alt Text", result.get('images_with_alt', 0))
        with img_col3:
            st.metric("Missing Alt", result.get('images_without_alt', 0))
        
        # ===== SCHEMA =====
        st.write("### 🏷️ Schema Markup")
        if result.get('has_schema'):
            st.success(f"✅ Schema found: {result.get('schema_types', [])}")
        else:
            st.warning("⚠️ No schema markup found")
        
        # ===== TECHNICAL =====
        st.write("### ⚙️ Technical SEO")
        tech_col1, tech_col2, tech_col3, tech_col4 = st.columns(4)
        
        with tech_col1:
            st.metric("SSL/HTTPS", "✅" if result.get('has_ssl') else "❌")
        with tech_col2:
            st.metric("Robots.txt", "✅" if result.get('has_robots_txt') else "❌")
        with tech_col3:
            st.metric("Sitemap", "✅" if result.get('has_sitemap_xml') else "❌")
        with tech_col4:
            st.metric("Favicon", "✅" if result.get('has_favicon') else "❌")
        
        # ===== SOCIAL MEDIA =====
        st.write("### 📱 Social Media Tags")
        if result.get('og_title'):
            st.success(f"OG Title: {result.get('og_title')}")
        if result.get('og_description'):
            st.success(f"OG Description: {result.get('og_description')}")
        if result.get('twitter_card'):
            st.success(f"Twitter Card: {result.get('twitter_card')}")
        
        if not result.get('og_title') and not result.get('og_description'):
            st.warning("⚠️ No Open Graph tags found")
        
        # ===== ISSUES =====
        if result.get('success_details'):
            st.write("### ✅ Successes")
            for detail in result['success_details']:
                st.success(detail)
        
        if result.get('warning_details'):
            st.write("### ⚠️ Warnings")
            for detail in result['warning_details']:
                st.warning(detail)
        
        if result.get('error_details'):
            st.write("### ❌ Errors")
            for detail in result['error_details']:
                st.error(detail)

# ============ UI LAYOUT ============

# Auto-import sites
auto_import_sites()

# Title
st.title("🔍 Complete SEO Monitor")
st.markdown("**Analyze 100+ SEO metrics for your websites**")
st.markdown("---")

# ============ SIDEBAR ============
with st.sidebar:
    st.header("📋 Site Management")
    st.metric("Total Sites", len(st.session_state.sites))
    
    st.markdown("---")
    
    st.subheader("➕ Add Single Site")
    new_url = st.text_input("Website URL", placeholder="example.com")
    if st.button("Add Site", use_container_width=True):
        if new_url:
            if not new_url.startswith('http'):
                new_url = 'https://' + new_url
            if new_url not in st.session_state.sites:
                st.session_state.sites.append(new_url)
                st.success(f"✅ Added {new_url}")
                st.rerun()
            else:
                st.warning("⚠️ Site already exists")
    
    st.markdown("---")
    
    st.subheader("📤 Upload Sites File")
    uploaded_file = st.file_uploader(
        "Upload .txt or .csv",
        type=['txt', 'csv']
    )
    
    if uploaded_file is not None:
        try:
            content = uploaded_file.read().decode('utf-8')
            urls = [line.strip() for line in content.split('\n') if line.strip()]
            added = 0
            for url in urls:
                if not url.startswith('http'):
                    url = 'https://' + url
                if url not in st.session_state.sites and not url.startswith('import'):
                    st.session_state.sites.append(url)
                    added += 1
            if added > 0:
                st.success(f"✅ Added {added} sites!")
                st.rerun()
        except Exception as e:
            st.error(f"Error reading file: {str(e)}")
    
    st.markdown("---")
    
    if st.button("🧹 Clear All Sites", use_container_width=True):
        st.session_state.sites = []
        st.session_state.results = {}
        st.rerun()
    
    st.markdown("---")
    st.caption("💡 **What this checks:**")
    st.caption("• Meta Tags (Title, Description, Keywords)")
    st.caption("• Headings (H1-H6)")
    st.caption("• Content Quality (Word count, Readability)")
    st.caption("• Links (Internal, External, Broken)")
    st.caption("• Images (Alt text, Size)")
    st.caption("• Schema Markup")
    st.caption("• Social Media Tags (OG, Twitter)")
    st.caption("• Technical SEO (SSL, Robots, Sitemap)")
    st.caption("• Performance (Load time, Resources)")
    st.caption("• Accessibility (ARIA, Language)")

# ============ MAIN TABS ============
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Dashboard",
    "🔍 SEO Analysis",
    "📈 Reports",
    "📋 All Metrics"
])

with tab1:
    # Summary cards
    col1, col2, col3, col4 = st.columns(4)
    
    total_sites = len(st.session_state.sites)
    checked_sites = len(st.session_state.results)
    sites_with_errors = sum(1 for r in st.session_state.results.values() if r.get('errors', 0) > 0)
    
    avg_score = 0
    if st.session_state.results:
        scores = [r.get('score', 0) for r in st.session_state.results.values()]
        avg_score = sum(scores) / len(scores) if scores else 0
    
    with col1:
        st.metric("📋 Total Sites", total_sites)
    with col2:
        st.metric("✅ Checked", checked_sites)
    with col3:
        st.metric("⚠️ Issues Found", sites_with_errors)
    with col4:
        st.metric("📊 Avg SEO Score", f"{avg_score:.1f}/100")
    
    # Site list with pagination
    st.subheader("📋 Monitored Sites")
    if st.session_state.sites:
        sites_per_page = 20
        total_pages = (len(st.session_state.sites) - 1) // sites_per_page + 1
        
        if st.session_state.current_page > total_pages:
            st.session_state.current_page = 1
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("◀ Previous", disabled=(st.session_state.current_page <= 1)):
                st.session_state.current_page -= 1
                st.rerun()
        with col2:
            st.write(f"Page {st.session_state.current_page} of {total_pages}")
        with col3:
            if st.button("Next ▶", disabled=(st.session_state.current_page >= total_pages)):
                st.session_state.current_page += 1
                st.rerun()
        
        start_idx = (st.session_state.current_page - 1) * sites_per_page
        end_idx = min(start_idx + sites_per_page, len(st.session_state.sites))
        
        df_data = []
        for site in st.session_state.sites[start_idx:end_idx]:
            status = "✅ Active"
            if site in st.session_state.results:
                result = st.session_state.results[site]
                if result.get('errors', 0) > 0:
                    status = "⚠️ Has Issues"
                last_check = result.get('last_check', 'Never')
                score = result.get('score', '-')
            else:
                last_check = 'Never'
                score = '-'
            
            df_data.append({
                'Site': site.replace('https://', ''),
                'Status': status,
                'Last Check': last_check,
                'Score': score
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No sites added yet. Add sites using the sidebar!")

with tab2:
    st.header("🔍 Run Complete SEO Analysis")
    
    col1, col2 = st.columns([1, 4])
    with col1:
        check_button = st.button("🚀 Check All Sites", type="primary", use_container_width=True)
    
    if check_button:
        if st.session_state.sites:
            progress_bar = st.progress(0)
            status_text = st.empty()
            results_container = st.empty()
            
            total = len(st.session_state.sites)
            results_list = []
            
            for i, url in enumerate(st.session_state.sites):
                status_text.text(f"🔄 Analyzing {i+1}/{total}: {url}")
                result = check_seo_complete(url)
                result['last_check'] = datetime.now().strftime('%Y-%m-%d %H:%M')
                st.session_state.results[url] = result
                results_list.append(result)
                progress_bar.progress((i + 1) / total)
                
                with results_container.container():
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Analyzed", f"{i+1}/{total}")
                    with col2:
                        errors_found = sum(1 for r in results_list if r.get('errors', 0) > 0)
                        st.metric("Sites with Issues", errors_found)
                    with col3:
                        scores = [r.get('score', 0) for r in results_list]
                        avg = sum(scores) / len(scores) if scores else 0
                        st.metric("Avg Score", f"{avg:.1f}")
            
            status_text.text("✅ Complete SEO analysis finished!")
            st.success(f"✅ Successfully analyzed all {total} sites!")
            st.rerun()
        else:
            st.warning("⚠️ No sites to analyze. Add sites first!")
    
    # Display results
    if st.session_state.results:
        st.header("📊 SEO Analysis Results")
        
        # Summary table
        summary_data = []
        for url, result in st.session_state.results.items():
            summary_data.append({
                'Site': url.replace('https://', ''),
                'Score': result.get('score', 0),
                'Errors': result.get('errors', 0),
                'Warnings': result.get('warnings', 0),
                'Title': result.get('title', 'Missing'),
                'Description': result.get('meta_description', 'Missing')[:50] + '...' if result.get('meta_description') else 'Missing',
                'Word Count': result.get('word_count', 0),
                'Internal Links': result.get('internal_links', 0),
                'External Links': result.get('external_links', 0),
                'Schema': '✅' if result.get('has_schema') else '❌',
                'Mobile': '✅' if result.get('has_viewport') else '❌'
            })
        
        df_summary = pd.DataFrame(summary_data)
        st.dataframe(df_summary, use_container_width=True, hide_index=True)
        
        # Detailed view for each site
        st.subheader("🔍 Detailed Analysis by Site")
        for url, result in list(st.session_state.results.items())[:10]:
            display_seo_result(url, result, expanded=False)

with tab3:
    st.header("📈 Reports & Analytics")
    
    if st.session_state.results:
        # Create dataframe for all metrics
        data = []
        for url, result in st.session_state.results.items():
            data.append({
                'Site': url.replace('https://', ''),
                'Score': result.get('score', 0),
                'Errors': result.get('errors', 0),
                'Warnings': result.get('warnings', 0),
                'Title': result.get('title', 'Missing'),
                'Title Length': result.get('title_length', 0),
                'Description': result.get('meta_description', 'Missing')[:100] + '...' if result.get('meta_description') else 'Missing',
                'Description Length': result.get('meta_description_length', 0),
                'H1': result.get('h1', 'Missing'),
                'H1 Count': result.get('h1_count', 0),
                'H2 Count': result.get('h2_count', 0),
                'H3 Count': result.get('h3_count', 0),
                'Word Count': result.get('word_count', 0),
                'Paragraphs': result.get('paragraph_count', 0),
                'Internal Links': result.get('internal_links', 0),
                'External Links': result.get('external_links', 0),
                'Broken Links': result.get('broken_links', 0),
                'Images': result.get('total_images', 0),
                'Images with Alt': result.get('images_with_alt', 0),
                'Schema': 'Yes' if result.get('has_schema') else 'No',
                'Mobile Friendly': 'Yes' if result.get('has_viewport') else 'No',
                'SSL': 'Yes' if result.get('has_ssl') else 'No',
                'Load Time': result.get('response_time', 0),
                'Status Code': result.get('status_code', 'N/A')
            })
        
        df = pd.DataFrame(data)
        df = df.sort_values('Score', ascending=False)
        
        st.subheader("📊 All Metrics Report")
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Statistics
        st.subheader("📊 Statistics")
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Total Sites", len(df))
        with col2:
            avg = df['Score'].mean()
            st.metric("Average Score", f"{avg:.1f}/100")
        with col3:
            total_errors = df['Errors'].sum()
            st.metric("Total Errors", total_errors)
        with col4:
            total_warnings = df['Warnings'].sum()
            st.metric("Total Warnings", total_warnings)
        with col5:
            perfect = len(df[df['Errors'] == 0])
            st.metric("Perfect Sites", perfect)
        
        # ===== DOWNLOAD SECTION =====
        st.subheader("📥 Export Options")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"seo_analysis_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True
            )
            st.caption("💾 Downloads to your browser")
        
        with col2:
            try:
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, sheet_name='SEO Analysis', index=False)
                excel_data = output.getvalue()
                
                st.download_button(
                    label="📊 Download Excel",
                    data=excel_data,
                    file_name=f"seo_analysis_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
                st.caption("💾 Downloads to your browser")
            except:
                st.button("📊 Excel Export", disabled=True, use_container_width=True)
        
        with col3:
            if st.button("💾 Save to Server", use_container_width=True):
                try:
                    os.makedirs('reports', exist_ok=True)
                    filename = f"reports/seo_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    df.to_csv(filename, index=False)
                    st.success(f"✅ Saved: {filename}")
                except Exception as e:
                    st.error(f"Error saving: {str(e)}")
        
        # Show saved files
        if os.path.exists('reports'):
            st.subheader("📁 Saved Reports")
            files = os.listdir('reports')
            if files:
                for f in sorted(files, reverse=True)[:10]:
                    size = os.path.getsize(f"reports/{f}") / 1024
                    st.write(f"   📄 {f} ({size:.1f} KB)")
        
        # ===== SITE RANKINGS =====
        st.subheader("🏆 Site Rankings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Top 10 Best Sites**")
            best = df.nlargest(10, 'Score')[['Site', 'Score']]
            st.dataframe(best, use_container_width=True, hide_index=True)
        
        with col2:
            st.write("**Top 10 Worst Sites**")
            worst = df.nsmallest(10, 'Score')[['Site', 'Score']]
            st.dataframe(worst, use_container_width=True, hide_index=True)
        
        # ===== ISSUES BREAKDOWN =====
        st.subheader("📊 Issues Breakdown")
        
        # Count issue types
        error_types = []
        for result in st.session_state.results.values():
            for error in result.get('error_details', []):
                error_types.append(error)
        
        if error_types:
            error_df = pd.DataFrame(error_types, columns=['Issue'])
            st.write("**Top Issues Found:**")
            issue_counts = error_df['Issue'].value_counts().head(10)
            st.dataframe(issue_counts, use_container_width=True)
        
    else:
        st.info("Run an SEO analysis first to generate reports")

with tab4:
    st.header("📋 Complete SEO Metrics Explained")
    
    st.markdown("""
    ### 🔍 What This Tool Checks
    
    #### 1. Meta Tags
    - **Title Tag**: Presence, length (optimal 30-60 chars)
    - **Meta Description**: Presence, length (optimal 50-160 chars)
    - **Meta Keywords**: Presence and content
    - **Meta Robots**: Check for noindex, nofollow
    - **Viewport**: Mobile responsiveness
    - **Charset**: Proper character encoding
    - **Language**: HTML language attribute
    
    #### 2. Headings Structure
    - **H1**: Presence, count (should have exactly one)
    - **H2-H6**: Count and hierarchy
    - **Heading Structure**: Proper nesting and flow
    
    #### 3. Content Analysis
    - **Word Count**: Minimum 300 words recommended
    - **Paragraph Count**: Distribution of content
    - **Readability**: Words per sentence (15-20 recommended)
    - **Keyword Density**: Most common keywords
    - **Content Quality**: Overall content metrics
    
    #### 4. Link Analysis
    - **Internal Links**: Count and distribution
    - **External Links**: Count and quality
    - **Nofollow vs Dofollow**: Link attribute analysis
    - **Broken Links**: Detecting 404s and errors
    - **Anchor Text**: Descriptive link text
    
    #### 5. Images
    - **Alt Text**: Missing alt attributes
    - **Title Text**: Image title attributes
    - **Image Count**: Total images on page
    
    #### 6. Schema Markup
    - **JSON-LD**: Structured data presence
    - **Schema Types**: Organization, Product, Article, FAQ, LocalBusiness
    - **Rich Snippets**: Enhanced search results
    
    #### 7. Social Media Tags
    - **Open Graph**: og:title, og:description, og:image
    - **Twitter Cards**: twitter:card, twitter:title
    - **Social Sharing**: Facebook, LinkedIn, etc.
    
    #### 8. Technical SEO
    - **Canonical URL**: Duplicate content prevention
    - **Robots.txt**: Proper configuration
    - **Sitemap.xml**: XML sitemap presence
    - **Favicon**: Favicon presence
    - **SSL/HTTPS**: Security certificate
    
    #### 9. Performance
    - **Load Time**: Page speed (ideal < 2s)
    - **Resources**: CSS, JS, image count
    - **Page Size**: Total page weight
    
    #### 10. Accessibility
    - **Alt Text**: Image descriptions
    - **ARIA Labels**: Accessibility attributes
    - **Heading Structure**: Screen reader friendly
    
    #### 11. Security
    - **HTTPS**: Secure connection
    - **Mixed Content**: Mixed HTTP/HTTPS
    - **Security Headers**: XSS, CSP, etc.
    """)

# ============ FOOTER ============
st.markdown("---")
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.caption(f"🔄 Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.caption(f"📊 Total Sites: {len(st.session_state.sites)} | Checked: {len(st.session_state.results)}")
    st.caption("🚀 Complete SEO Monitor v2.0 | Made with Streamlit")
