// Page state tracking
const PAGE_TITLES = {
    'device': 'Device Status',
    'logs': 'Logs Check',
    'queue': 'Task Queue'
};

// Switching Views (Tabs)
function switchTab(tabName) {
    // Toggle active classes in Sidebar Navigation
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));
    
    // Add active classes
    const activeBtn = Array.from(document.querySelectorAll('.nav-item')).find(btn => 
        btn.textContent.includes(PAGE_TITLES[tabName] || tabName)
    );
    if (activeBtn) activeBtn.classList.add('active');
    
    document.getElementById(`tab-${tabName}`).classList.add('active');
    
    // Update top bar page title
    document.getElementById('page-title').textContent = PAGE_TITLES[tabName] || tabName;

    // Immediately trigger update to avoid screen lag
    updateData();
}

// Data Polling Loop
async function updateData() {
    try {
        // ── 1. Global / Device Uptime ────────────────────────────────────────
        const healthRes = await fetch('/health');
        if (healthRes.ok) {
            const health = await healthRes.json();
            document.getElementById('device-uptime').textContent = health.uptime;
            document.getElementById('device-db').textContent = health.database === 'connected' ? 'Connected' : 'Error';
            
            // Connection status badge
            const connBadge = document.getElementById('connection-badge');
            if (health.database === 'connected') {
                connBadge.textContent = 'Connected';
                connBadge.className = 'badge badge-green';
            } else {
                connBadge.textContent = 'DB Offline';
                connBadge.className = 'badge';
                connBadge.style.backgroundColor = 'var(--red-bg)';
                connBadge.style.color = 'var(--red-text)';
            }
            document.getElementById('device-version').textContent = health.version || '0.1.0';
        }

        // ── 2. Logs View ─────────────────────────────────────────────────────
        if (document.getElementById('tab-logs').classList.contains('active')) {
            const logsRes = await fetch('/logs?limit=50');
            if (logsRes.ok) {
                const logs = await logsRes.json();
                const container = document.getElementById('logs-container');
                container.innerHTML = logs.length === 0
                    ? '<tr><td colspan="2" class="state-placeholder">No events logged yet.</td></tr>'
                    : logs.map(l => `
                        <tr>
                            <td style="color: var(--text-light); width: 120px;">${formatTime(l.created_at)}</td>
                            <td style="font-weight: 500;">${l.event}</td>
                        </tr>
                    `).join('');
            }
        }

        // ── 3. Queue View ────────────────────────────────────────────────────
        if (document.getElementById('tab-queue').classList.contains('active')) {
            // Task statistics counts
            const statsRes = await fetch('/queue/stats');
            if (statsRes.ok) {
                const stats = await statsRes.json();
                document.getElementById('q-pending').textContent = stats.pending || 0;
                document.getElementById('q-processing').textContent = stats.processing || 0;
                document.getElementById('q-failed').textContent = stats.failed || 0;
            }

            // Pending Queue Items
            const queueRes = await fetch('/queue?limit=25');
            if (queueRes.ok) {
                const pending = await queueRes.json();
                const container = document.getElementById('queue-container');
                container.innerHTML = pending.length === 0
                    ? '<tr><td colspan="5" class="state-placeholder">No pending tasks.</td></tr>'
                    : pending.map(t => `
                        <tr>
                            <td style="color: var(--text-light);">${t.id}</td>
                            <td style="font-weight: 500;">${t.task_type}</td>
                            <td><span class="badge" style="background-color: var(--blue-bg); color: var(--blue-text);">${t.status}</span></td>
                            <td>${t.priority}</td>
                            <td>${t.retry_count}</td>
                        </tr>
                    `).join('');
            }
        }
    } catch (error) {
        console.error('Error fetching dashboard updates:', error);
    }
}

// Format SQLite ISO strings for neat rendering
function formatTime(isoString) {
    try {
        const date = new Date(isoString);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch (e) {
        return isoString;
    }
}

// Initial pull & scheduling
updateData();
setInterval(updateData, 2000);
