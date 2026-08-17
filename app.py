import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import re
import os
import time
import io
import base64

# ============ PAGE CONFIG - MUST BE FIRST ============
st.set_page_config(
    page_title="SEO Monitor - 50 Sites",
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

# ============ SEO CHECKER FUNCTION ============
def check_seo(url):
    """Check SEO for a single URL - Returns REAL data from the website"""
    result = {
        'url': url,
        'score': 0,
        'errors': 0,
        'error_details': [],
        'title': None,
        'description': None,
        'description_length': 0,
        'h1': None,
        'word_count': 0,
        'total_images': 0,
        'images_with_alt': 0,
        'last_check': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'status_code': None,
        'response_time': None,
        'internal_links': 0,
        'external_links': 0
    }
    
    try:
        start_time = time.time()
        
        # Add http if missing
        if not url.startswith('http'):
            url = 'https://' + url
        
        # Fetch page
        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; SEO-Monitor/1.0)'
        })
        
        result['status_code'] = response.status_code
        result['response_time'] = round(time.time() - start_time, 2)
        
        if response.status_code != 200:
            result['error_details'].append(f"❌ HTTP {response.status_code} Error")
            result['errors'] += 1
            return result
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # ====== CHECK TITLE ======
        title = soup.find('title')
        if title and title.text.strip():
            result['title'] = title.text.strip()
            result['score'] += 25
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
        
        # ====== CHECK META DESCRIPTION ======
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            desc_content = meta_desc.get('content', '').strip()
            if desc_content:
                result['description'] = desc_content
                result['description_length'] = len(desc_content)
                result['score'] += 25
                
                if len(desc_content) < 50:
                    result['error_details'].append(f"⚠️ Description too short: {len(desc_content)} chars (< 50)")
                    result['errors'] += 1
                elif len(desc_content) > 160:
                    result['error_details'].append(f"⚠️ Description too long: {len(desc_content)} chars (> 160)")
                    result['errors'] += 1
            else:
                result['error_details'].append("❌ Meta description is empty")
                result['errors'] += 1
        else:
            result['error_details'].append("❌ Missing meta description")
            result['errors'] += 1
        
        # ====== CHECK H1 ======
        h1 = soup.find('h1')
        if h1 and h1.text.strip():
            result['h1'] = h1.text.strip()
            result['score'] += 15
        else:
            result['error_details'].append("⚠️ No H1 heading found")
            result['errors'] += 1
        
        # ====== CHECK MULTIPLE H1 ======
        h1s = soup.find_all('h1')
        if len(h1s) > 1:
            result['error_details'].append(f"⚠️ Multiple H1 tags found: {len(h1s)}")
            result['errors'] += 1
        
        # ====== CHECK WORD COUNT ======
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
        
        # ====== CHECK IMAGES ======
        images = soup.find_all('img')
        result['total_images'] = len(images)
        images_without_alt = [img for img in images if not img.get('alt')]
        result['images_with_alt'] = len(images) - len(images_without_alt)
        
        if images_without_alt:
            result['error_details'].append(f"⚠️ {len(images_without_alt)} images missing alt text")
            result['errors'] += 1
        elif images:
            result['score'] += 10
        
        # ====== CHECK LINKS ======
        links = soup.find_all('a', href=True)
        internal_links = 0
        external_links = 0
        
        for link in links:
            href = link['href']
            if href.startswith('http'):
                if urlparse(href).netloc == urlparse(url).netloc:
                    internal_links += 1
                else:
                    external_links += 1
            elif href.startswith('/') or href.startswith('#'):
                internal_links += 1
        
        result['internal_links'] = internal_links
        result['external_links'] = external_links
        
        if links:
            result['score'] += 5
            
            # Check for broken links (sample)
            broken_links = 0
            for link in links[:3]:
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
        
        # ====== CHECK SCHEMA MARKUP ======
        schema = soup.find('script', attrs={'type': 'application/ld+json'})
        if schema:
            result['score'] += 5
        
        # ====== CHECK VIEWPORT ======
        viewport = soup.find('meta', attrs={'name': 'viewport'})
        if viewport:
            result['score'] += 5
        else:
            result['error_details'].append("⚠️ Missing viewport meta tag")
            result['errors'] += 1
        
        # ====== CHECK CANONICAL ======
        canonical = soup.find('link', attrs={'rel': 'canonical'})
        if not canonical:
            result['error_details'].append("⚠️ No canonical tag found")
            result['errors'] += 1
        
        # ====== CHECK ROBOTS META ======
        robots = soup.find('meta', attrs={'name': 'robots'})
        if robots:
            robots_content = robots.get('content', '').lower()
            if 'noindex' in robots_content:
                result['error_details'].append("⚠️ Page is marked noindex")
                result['errors'] += 1
            if 'nofollow' in robots_content:
                result['error_details'].append("⚠️ Page is marked nofollow")
                result['errors'] += 1
        else:
            result['error_details'].append("⚠️ No robots meta tag found")
            result['errors'] += 1
        
        # Calculate final score
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

# ============ AUTO-IMPORT SITES ============
def auto_import_sites():
    """Automatically import sites from sites.txt on app start"""
    if os.path.exists('sites.txt') and not st.session_state.sites:
        try:
            with open('sites.txt', 'r') as f:
                for line in f:
                    url = line.strip()
                    if url and not url.startswith('#'):
                        # Skip if it looks like Python code
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

auto_import_sites()

# ============ TITLE ============
st.title("🔍 SEO Monitor Dashboard")
st.markdown("---")

# ============ SIDEBAR ============
with st.sidebar:
    st.header("📋 Site Management")
    st.metric("Total Sites", len(st.session_state.sites))
    
    st.markdown("---")
    
    # Add single site
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
    
    # Upload sites file
    st.subheader("📤 Upload Sites File")
    uploaded_file = st.file_uploader(
        "Upload sites.txt or .csv",
        type=['txt', 'csv'],
        help="Upload a file with one URL per line"
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
    
    # Clear All button
    if st.button("🧹 Clear All Sites", use_container_width=True):
        st.session_state.sites = []
        st.session_state.results = {}
        st.rerun()
    
    st.markdown("---")
    st.caption("💡 Tip: Add sites.txt to your project folder for auto-import")

# ============ MAIN TABS ============
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
        # Pagination
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
    st.header("🔍 Check SEO for Your Sites")
    
    # Check all button
    col1, col2 = st.columns([1, 4])
    with col1:
        check_button = st.button("🚀 Check All Sites", type="primary", use_container_width=True)
    
    if check_button:
        if st.session_state.sites:
            st.session_state.scanning = True
            progress_bar = st.progress(0)
            status_text = st.empty()
            results_container = st.empty()
            
            total = len(st.session_state.sites)
            results_list = []
            
            for i, url in enumerate(st.session_state.sites):
                status_text.text(f"🔄 Checking {i+1}/{total}: {url}")
                result = check_seo(url)
                result['last_check'] = datetime.now().strftime('%Y-%m-%d %H:%M')
                st.session_state.results[url] = result
                results_list.append(result)
                progress_bar.progress((i + 1) / total)
                
                # Show live stats
                with results_container.container():
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Checked", f"{i+1}/{total}")
                    with col2:
                        errors_found = sum(1 for r in results_list if r.get('errors', 0) > 0)
                        st.metric("Sites with Issues", errors_found)
                    with col3:
                        scores = [r.get('score', 0) for r in results_list]
                        avg = sum(scores) / len(scores) if scores else 0
                        st.metric("Avg Score", f"{avg:.1f}")
            
            status_text.text("✅ All sites checked!")
            st.success(f"✅ Successfully checked all {total} sites!")
            st.session_state.scanning = False
            st.rerun()
        else:
            st.warning("⚠️ No sites to check. Add sites first!")
    
    # Show results with REAL meta descriptions
    if st.session_state.results:
        st.subheader("📊 Detailed SEO Results")
        
        # Create dataframe
        results_data = []
        for url, result in st.session_state.results.items():
            desc = result.get('description')
            results_data.append({
                'Site': url.replace('https://', ''),
                'Score': result.get('score', 0),
                'Title': result.get('title', '❌ Missing'),
                'Description': desc if desc else '❌ Missing',
                'Desc Length': result.get('description_length', 0),
                'Word Count': result.get('word_count', 0),
                'Errors': result.get('errors', 0)
            })
        
        df_results = pd.DataFrame(results_data)
        st.dataframe(df_results, use_container_width=True, hide_index=True)
        
        # Show detailed view for each site
        st.subheader("🔍 Detailed View by Site")
        
        # Create a selectbox to choose which site to view
        site_options = [url.replace('https://', '') for url in st.session_state.results.keys()]
        selected_site = st.selectbox("Select a site to view details:", site_options)
        
        if selected_site:
            # Find the full URL
            full_url = 'https://' + selected_site
            if full_url in st.session_state.results:
                result = st.session_state.results[full_url]
                
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.write(f"**Score:** {result.get('score', 0)}/100")
                    st.write(f"**Title:** {result.get('title', '❌ Missing')}")
                    
                    # Display REAL meta description
                    description = result.get('description')
                    if description:
                        st.write("**Meta Description:**")
                        st.info(f"📝 {description}")
                        st.write(f"**Length:** {len(description)} characters")
                    else:
                        st.error("❌ No meta description found")
                    
                    st.write(f"**Word Count:** {result.get('word_count', 0)}")
                    st.write(f"**H1 Heading:** {result.get('h1', '❌ Missing')}")
                    st.write(f"**Internal Links:** {result.get('internal_links', 0)}")
                    st.write(f"**External Links:** {result.get('external_links', 0)}")
                    st.write(f"**Status Code:** {result.get('status_code', 'N/A')}")
                    st.write(f"**Response Time:** {result.get('response_time', 0)}s")
                
                with col2:
                    if result.get('errors', 0) > 0:
                        st.error(f"⚠️ {result.get('errors', 0)} issues found")
                    else:
                        st.success("✅ No issues found")
                    
                    st.write(f"**Images:** {result.get('images_with_alt', 0)}/{result.get('total_images', 0)} have alt text")
                    
                    # Rating
                    score = result.get('score', 0)
                    if score >= 90:
                        st.success("🌟 Excellent SEO")
                    elif score >= 70:
                        st.info("👍 Good SEO")
                    elif score >= 50:
                        st.warning("⚠️ Needs Improvement")
                    else:
                        st.error("❌ Poor SEO")
                
                if result.get('error_details'):
                    st.write("**Issues Found:**")
                    for detail in result.get('error_details', []):
                        st.warning(f"• {detail}")
            else:
                st.warning("Site not found in results")

with tab3:
    st.header("📈 SEO Reports")
    if st.session_state.results:
        # Create dataframe
        data = []
        for url, result in st.session_state.results.items():
            desc = result.get('description')
            data.append({
                'Site': url.replace('https://', ''),
                'Score': result.get('score', 0),
                'Title': result.get('title', 'Missing'),
                'Description': desc[:100] + '...' if desc and len(desc) > 100 else (desc if desc else 'Missing'),
                'Description Length': result.get('description_length', 0),
                'H1 Tag': '✅' if result.get('h1') else '❌',
                'Word Count': result.get('word_count', 0),
                'Issues': result.get('errors', 0),
                'Issues Details': '; '.join(result.get('error_details', []))[:200] if result.get('error_details') else 'None'
            })
        
        df = pd.DataFrame(data)
        df = df.sort_values('Score', ascending=False)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Statistics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Sites", len(df))
        with col2:
            avg = df['Score'].mean()
            st.metric("Average Score", f"{avg:.1f}/100")
        with col3:
            total_issues = df['Issues'].sum()
            st.metric("Total Issues", total_issues)
        with col4:
            perfect = len(df[df['Issues'] == 0])
            st.metric("Perfect Sites", perfect)
        
        # ====== DOWNLOAD SECTION ======
        st.subheader("📥 Export Options")
        
        col1, col2, col3 = st.columns(3)
        
        # Option 1: Download CSV
        with col1:
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"seo_report_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True
            )
            st.caption("💾 Downloads to your browser")
        
        # Option 2: Download Excel
        with col2:
            try:
                # Create Excel file in memory
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, sheet_name='SEO Report', index=False)
                excel_data = output.getvalue()
                
                st.download_button(
                    label="📊 Download Excel",
                    data=excel_data,
                    file_name=f"seo_report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
                st.caption("💾 Downloads to your browser")
            except:
                st.button("📊 Excel Export", disabled=True, use_container_width=True)
                st.caption("⚠️ Install openpyxl for Excel export")
        
        # Option 3: Save to Server
        with col3:
            if st.button("💾 Save to Server", use_container_width=True):
                try:
                    # Create reports folder
                    os.makedirs('reports', exist_ok=True)
                    filename = f"reports/seo_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    df.to_csv(filename, index=False)
                    st.success(f"✅ Saved: {filename}")
                except Exception as e:
                    st.error(f"Error saving: {str(e)}")
            st.caption("💾 Saves to server folder")
        
        # Show saved files
        if os.path.exists('reports'):
            st.subheader("📁 Saved Reports on Server")
            files = os.listdir('reports')
            if files:
                for f in sorted(files, reverse=True)[:10]:
                    file_size = os.path.getsize(f"reports/{f}")
                    size_kb = file_size / 1024
                    st.write(f"   📄 {f} ({size_kb:.1f} KB)")
                
                # Download saved file
                if files:
                    latest_file = sorted(files, reverse=True)[0]
                    with open(f"reports/{latest_file}", 'r') as f:
                        csv_data = f.read()
                    st.download_button(
                        label=f"📥 Download Latest: {latest_file}",
                        data=csv_data,
                        file_name=latest_file,
                        mime="text/csv",
                        use_container_width=True
                    )
            else:
                st.write("No saved reports yet")
        
        # Worst performers
        st.subheader("⚠️ Sites Needing Attention")
        worst_sites = df[df['Issues'] > 0].head(10)
        if not worst_sites.empty:
            st.dataframe(worst_sites[['Site', 'Score', 'Issues']], use_container_width=True)
        else:
            st.success("🎉 No sites with issues found!")
        
        # Best performers
        st.subheader("🌟 Top Performing Sites")
        best_sites = df[df['Issues'] == 0].head(10)
        if not best_sites.empty:
            st.dataframe(best_sites[['Site', 'Score']], use_container_width=True)
        else:
            st.info("No perfect sites yet. Keep improving!")
    else:
        st.info("Run a scan first to generate reports")

# ============ FOOTER ============
st.markdown("---")
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.caption(f"🔄 Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.caption(f"📊 Total Sites: {len(st.session_state.sites)} | Checked: {len(st.session_state.results)}")
    st.caption("🚀 SEO Monitor v1.0 | Made with Streamlit")

# ============ HELPER FUNCTION FOR URLPARSER ============
from urllib.parse import urlparse
