const API_BASE = '/api';
let currentPage = 1;
let totalPages = 1;
let trendChart = null;
let errorTypeChart = null;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    loadDashboard();
    loadSites();
    setInterval(refreshData, 30000); // Refresh every 30 seconds
});

async function loadDashboard() {
    try {
        const response = await fetch(`${API_BASE}/dashboard/summary`);
        const data = await response.json();
        
        document.getElementById('totalSites').textContent = data.total_sites;
        document.getElementById('sitesWithErrors').textContent = data.sites_with_errors;
        document.getElementById('avgScore').textContent = data.average_seo_score.toFixed(1);
        document.getElementById('recentScans').textContent = data.recent_scans_24h;
        
        // Load charts
        loadTrendChart();
        loadErrorTypes();
    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

async function loadTrendChart() {
    try {
        const response = await fetch(`${API_BASE}/dashboard/trend?days=30`);
        const data = await response.json();
        
        if (trendChart) {
            trendChart.destroy();
        }
        
        const ctx = document.getElementById('trendChart').getContext('2d');
        trendChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.dates,
                datasets: [{
                    label: 'Average SEO Score',
                    data: data.scores,
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        min: 0,
                        max: 100,
                        grid: {
                            color: '#e2e8f0'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error loading trend chart:', error);
    }
}

async function loadErrorTypes() {
    try {
        const response = await fetch(`${API_BASE}/dashboard/error-types`);
        const data = await response.json();
        
        if (errorTypeChart) {
            errorTypeChart.destroy();
        }
        
        const ctx = document.getElementById('errorTypeChart').getContext('2d');
        errorTypeChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: data.labels,
                datasets: [{
                    data: data.values,
                    backgroundColor: [
                        '#fc8181',
                        '#f6ad55',
                        '#ecc94b',
                        '#68d391',
                        '#63b3ed',
                        '#9f7aea'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error loading error types:', error);
    }
}

async function loadSites(page = 1) {
    try {
        const search = document.getElementById('searchInput').value;
        const filter = document.getElementById('filterStatus').value;
        
        let url = `${API_BASE}/sites/?skip=${(page-1)*20}&limit=20`;
        
        const response = await fetch(url);
        const sites = await response.json();
        
        // Get total count for pagination
        const countResponse = await fetch(`${API_BASE}/sites/?limit=1`);
        const allSites = await countResponse.json();
        totalPages = Math.ceil(allSites.length / 20);
        
        renderSites(sites, page);
        renderPagination(page);
    } catch (error) {
        console.error('Error loading sites:', error);
    }
}

function renderSites(sites, page) {
    const tbody = document.getElementById('sitesList');
    tbody.innerHTML = '';
    
    sites.forEach(site => {
        const tr = document.createElement('tr');
        
        // Status badge
        let statusClass = 'status-active';
        let statusText = 'Active';
        if (!site.is_active) {
            statusClass = 'status-inactive';
            statusText = 'Inactive';
        } else if (site.total_errors > 0) {
            statusClass = 'status-error';
            statusText = 'Has Errors';
        }
        
        // Score color
        let scoreClass = 'score-high';
        if (site.seo_score < 60) scoreClass = 'score-low';
        else if (site.seo_score < 80) scoreClass = 'score-medium';
        
        tr.innerHTML = `
            <td>
                <strong>${site.name}</strong>
                <br>
                <small style="color: #718096;">${site.url}</small>
            </td>
            <td><span class="status-badge ${statusClass}">${statusText}</span></td>
            <td><span class="${scoreClass}">${site.seo_score.toFixed(1)}</span></td>
            <td>${site.total_errors}</td>
            <td>${site.last_scanned_at ? new Date(site.last_scanned_at).toLocaleString() : 'Never'}</td>
            <td>
                <div class="actions">
                    <button onclick="scanSite(${site.id})" class="btn-secondary">Scan</button>
                    <button onclick="deleteSite(${site.id})" class="btn-danger">Delete</button>
                </div>
            </td>
        `;
        
        tbody.appendChild(tr);
    });
}

function renderPagination(currentPage) {
    const pagination = document.getElementById('pagination');
    pagination.innerHTML = '';
    
    for (let i = 1; i <= totalPages; i++) {
        const btn = document.createElement('button');
        btn.textContent = i;
        btn.className = i === currentPage ? 'active' : '';
        btn.onclick = () => loadSites(i);
        pagination.appendChild(btn);
    }
}

function filterSites() {
    loadSites(1);
}

function refreshData() {
    loadDashboard();
    loadSites(currentPage);
}

async function triggerScan() {
    try {
        const response = await fetch(`${API_BASE}/scan/trigger`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        const data = await response.json();
        alert('Scan scheduled for all active sites!');
        refreshData();
    } catch (error) {
        console.error('Error triggering scan:', error);
        alert('Failed to trigger scan');
    }
}

async function scanSite(siteId) {
    try {
        const response = await fetch(`${API_BASE}/scan/trigger?site_id=${siteId}`, {
            method: 'POST'
        });
        const data = await response.json();
        alert('Site scan scheduled!');
        refreshData();
    } catch (error) {
        console.error('Error scanning site:', error);
        alert('Failed to scan site');
    }
}

async function deleteSite(siteId) {
    if (!confirm('Are you sure you want to delete this site?')) return;
    
    try {
        await fetch(`${API_BASE}/sites/${siteId}`, {
            method: 'DELETE'
        });
        refreshData();
    } catch (error) {
        console.error('Error deleting site:', error);
        alert('Failed to delete site');
    }
}

function openModal() {
    document.getElementById('addSiteModal').style.display = 'block';
}

function closeModal() {
    document.getElementById('addSiteModal').style.display = 'none';
}

async function submitSite(event) {
    event.preventDefault();
    
    const data = {
        url: document.getElementById('siteUrl').value,
        name: document.getElementById('siteName').value,
        scan_frequency: document.getElementById('scanFrequency').value
    };
    
    try {
        const response = await fetch(`${API_BASE}/sites/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            closeModal();
            refreshData();
            alert('Site added successfully!');
        } else {
            const error = await response.json();
            alert('Failed to add site: ' + error.detail);
        }
    } catch (error) {
        console.error('Error adding site:', error);
        alert('Failed to add site');
    }
}

// Click outside modal to close
window.onclick = function(event) {
    const modal = document.getElementById('addSiteModal');
    if (event.target === modal) {
        closeModal();
    }
}
