import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import re
import urllib.parse

# Page config
st.set_page_config(
    page_title="SEO Monitor",
    page_icon="🔍",
    layout="wide"
)

# Title
st.title("🔍 SEO Monitor Dashboard")
st.markdown("---")

# Initialize session state
if 'sites' not in st.session_state:
    st.session_state.sites = []
if 'results' not in st.session_state:
    st.session_state.results = {}

# Sidebar
with st.sidebar:
    st.header("📋 Add New Site")
    new_url = st.text_input("Website URL", placeholder="https://example.com")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ Add Site", use_container_width=True):
            if new_url and new_url not in st.session_state.sites:
                # Clean URL
                if not new_url.startswith('http'):
                    new_url = 'https://' + new_url
                st.session_state.sites.append(new_url)
                st.success(f"Added {new_url}")
                st.rerun()
    with col2:
        if st.button("🗑️ Clear All", use_container_width=True):
            st.session_state.sites = []
            st.session_state.results = {}
            st.rerun()
    
    st.markdown("---")
    st.caption(f"📊 Total Sites: {len(st.session_state.sites)}")
    
    # Export option
    if st.session_state.results:
        st.download_button(
            label="📥 Export Report",
            data=create_csv_report(st.session_state.results),
            file_name=f"seo_report_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True
        )

# Main tabs
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "🔍 SEO Checker", "📈 Reports"])

with tab1:
    # Summary cards
    col1, col2, col3, col4 = st.columns(4)
    
    total_sites = len(st.session_state.sites)
    checked_sites = len(st.session_state.results)
    sites_with_errors = sum(1 for r in st.session_state.results.values() if r.get('errors', 0) > 0)
    
    avg_score = 0
    if st.session_state.results:
        scores = [r.get('score', 0) for r in st.session_state.results.values()]
        avg_score = sum(scores) / len(scores)
    
    with col1:
        st.metric("📋 Total Sites", total_sites)
    with col2:
        st.metric("✅ Checked", checked_sites)
    with col3:
        st.metric("⚠️ Issues Found", sites_with_errors)
    with col4:
        st.metric("📊 Avg SEO Score", f"{avg_score:.1f}/100")
    
    # Site list
    st.subheader("📋 Monitored Sites")
    if st.session_state.sites:
        df_data = []
        for site in st.session_state.sites:
            status = "✅ Active"
            if site in st.session_state.results:
                result = st.session_state.results[site]
                if result.get('errors', 0) > 0:
                    status = "⚠️ Has Issues"
                last_check = result.get('last_check', 'Never')
            else:
                last_check = 'Never'
            
            df_data.append({
                'Site': site,
                'Status': status,
                'Last Check': last_check,
                'Score': st.session_state.results.get(site, {}).get('score', '-')
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No sites added yet. Add a site using the sidebar!")

with tab2:
    st.header("🔍 Check SEO for Your Sites")
    
    # Check all button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🚀 Check All", type="primary", use_container_width=True):
            if st.session_state.sites:
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i, url in enumerate(st.session_state.sites):
                    status_text.text(f"🔄 Checking: {url}")
                    
                    # Perform SEO check
                    result = check_seo(url)
                    result['last_check'] = datetime.now().strftime('%Y-%m-%d %H:%M')
                    st.session_state.results[url] = result
                    
                    progress_bar.progress((i + 1) / len(st.session_state.sites))
                
                status_text.text("✅ All sites checked!")
                st.success("✅ All sites checked successfully!")
                st.rerun()
            else:
                st.warning("⚠️ No sites to check. Add some first!")
    
    # Display results
    if st.session_state.results:
        st.subheader("📊 SEO Results")
        
        for url, result in st.session_state.results.items():
            with st.expander(f"🔍 {url}", expanded=False):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**Score:** {result.get('score', 0)}/100")
                    st.write(f"**Title:** {result.get('title', '❌ Missing')}")
                    st.write(f"**Description:** {result.get('description', '❌ Missing')[:100]}...")
                    st.write(f"**Word Count:** {result.get('word_count', 0)}")
                    st.write(f"**Last Check:** {result.get('last_check', 'Never')}")
                
                with col2:
                    if result.get('errors', 0) > 0:
                        st.error(f"⚠️ {result.get('errors', 0)} issues found")
                    else:
                        st.success("✅ No issues found")
                
                if result.get('error_details'):
                    st.write("**Issues Found:**")
                    for detail in result.get('error_details', []):
                        st.warning(f"• {detail}")

with tab3:
    st.header("📈 SEO Reports")
    
    if st.session_state.results:
        # Create summary dataframe
        data = []
        for url, result in st.session_state.results.items():
            data.append({
                'Site': url,
                'Score': result.get('score', 0),
                'Title': result.get('title', 'Missing'),
                'Description': '✅' if result.get('description') else '❌',
                'H1 Tag': '✅' if result.get('h1') else '❌',
                'Images with Alt': f"{result.get('images_with_alt', 0)}/{result.get('total_images', 0)}",
                'Word Count': result.get('word_count', 0),
                'Issues': result.get('errors', 0)
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Show statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Sites Checked", len(df))
        with col2:
            avg_score = df['Score'].mean()
            st.metric("Average Score", f"{avg_score:.1f}/100")
        with col3:
            total_issues = df['Issues'].sum()
            st.metric("Total Issues Found", total_issues)
    else:
        st.info("Run a scan first to generate reports")

# Footer
st.markdown("---")
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.caption(f"🔄 Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.caption("🚀 SEO Monitor v1.0 | Made with Streamlit")

# Helper Functions
def check_seo(url):
    """Check SEO for a single URL"""
    result = {
        'url': url,
        'score': 0,
        'errors': 0,
        'error_details': [],
        'title': None,
        'description': None,
        'h1': None,
        'word_count': 0,
        'total_images': 0,
        'images_with_alt': 0,
        'last_check': datetime.now().strftime('%Y-%m-%d %H:%M')
    }
    
    try:
        # Add http if missing
        if not url.startswith('http'):
            url = 'https://' + url
        
        # Fetch page
        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; SEO-Monitor/1.0)'
        })
        
        if response.status_code != 200:
            result['error_details'].append(f"❌ HTTP {response.status_code} Error")
            result['errors'] += 1
            return result
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check title
        title = soup.find('title')
        if title and title.text.strip():
            result['title'] = title.text.strip()
            result['score'] += 25
            # Title length check
            title_len = len(title.text.strip())
            if title_len < 30:
                result['error_details'].append(f"⚠️ Title too short: {title_len} chars (< 30)")
                result['errors'] += 1
            elif title_len > 60:
                result['error_details'].append(f"⚠️ Title too long: {title_len} chars (> 60)")
                result['errors'] += 1
        else:
            result['error_details'].append("❌ Missing title tag")
            result['errors'] += 1
        
        # Check meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content', '').strip():
            result['description'] = meta_desc.get('content', '').strip()
            result['score'] += 25
            desc_len = len(meta_desc.get('content', '').strip())
            if desc_len < 50:
                result['error_details'].append(f"⚠️ Description too short: {desc_len} chars (< 50)")
                result['errors'] += 1
            elif desc_len > 160:
                result['error_details'].append(f"⚠️ Description too long: {desc_len} chars (> 160)")
                result['errors'] += 1
        else:
            result['error_details'].append("❌ Missing meta description")
            result['errors'] += 1
        
        # Check H1
        h1 = soup.find('h1')
        if h1 and h1.text.strip():
            result['h1'] = h1.text.strip()
            result['score'] += 15
        else:
            result['error_details'].append("⚠️ No H1 heading found")
            result['errors'] += 1
        
        # Check multiple H1
        h1s = soup.find_all('h1')
        if len(h1s) > 1:
            result['error_details'].append(f"⚠️ Multiple H1 tags found: {len(h1s)}")
            result['errors'] += 1
        
        # Check word count
        text = soup.get_text()
        words = len(re.findall(r'\w+', text))
        result['word_count'] = words
        if words > 300:
            result['score'] += 20
        elif words > 100:
            result['score'] += 10
        else:
            result['error_details'].append(f"⚠️ Low word count: {words} words (< 100)")
            result['errors'] += 1
        
        # Check images
        images = soup.find_all('img')
        result['total_images'] = len(images)
        images_without_alt = [img for img in images if not img.get('alt')]
        result['images_with_alt'] = len(images) - len(images_without_alt)
        
        if images_without_alt:
            result['error_details'].append(f"⚠️ {len(images_without_alt)} images missing alt text")
            result['errors'] += 1
        elif images:
            result['score'] += 10
        
        # Check links
        links = soup.find_all('a', href=True)
        if links:
            result['score'] += 5
            # Check for broken links (basic)
            broken_links = 0
            for link in links[:5]:  # Check first 5 links only to avoid timeout
                href = link['href']
                if href.startswith('http'):
                    try:
                        resp = requests.head(href, timeout=3, allow_redirects=True)
                        if resp.status_code >= 400:
                            broken_links += 1
                    except:
                        broken_links += 1
            if broken_links > 0:
                result['error_details'].append(f"⚠️ {broken_links} broken links found")
                result['errors'] += 1
        else:
            result['error_details'].append("⚠️ No links found on page")
            result['errors'] += 1
        
        # Check for schema markup
        schema = soup.find('script', attrs={'type': 'application/ld+json'})
        if schema:
            result['score'] += 5
        
        # Check viewport meta
        viewport = soup.find('meta', attrs={'name': 'viewport'})
        if viewport:
            result['score'] += 5
        else:
            result['error_details'].append("⚠️ Missing viewport meta tag (not mobile-friendly)")
            result['errors'] += 1
        
        # Check canonical
        canonical = soup.find('link', attrs={'rel': 'canonical'})
        if not canonical:
            result['error_details'].append("⚠️ No canonical tag found")
            result['errors'] += 1
        
        # Calculate final score (max 100)
        result['score'] = min(result['score'], 100)
        
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

def create_csv_report(results):
    """Create CSV report from results"""
    data = []
    for url, result in results.items():
        data.append({
            'URL': url,
            'Score': result.get('score', 0),
            'Title': result.get('title', 'Missing'),
            'Description': result.get('description', 'Missing'),
            'Word Count': result.get('word_count', 0),
            'Errors': result.get('errors', 0),
            'Issues': '; '.join(result.get('error_details', []))
        })
    df = pd.DataFrame(data)
    return df.to_csv(index=False)
