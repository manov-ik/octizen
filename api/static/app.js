const PAGE_TITLES = {
    'device': 'Device Status',
    'logs': 'Logs Check',
    'queue': 'Task Queue',
    'wifi': 'Wi-Fi Setup'
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

        // ── 4. Wi-Fi View ────────────────────────────────────────────────────
        if (document.getElementById('tab-wifi').classList.contains('active')) {
            // Scanned airwave networks
            const scanRes = await fetch('/wifi/scan');
            if (scanRes.ok) {
                const scan = await scanRes.json();
                const container = document.getElementById('scan-container');
                container.innerHTML = scan.length === 0
                    ? '<tr><td colspan="4" class="state-placeholder">No Wi-Fi signals found.</td></tr>'
                    : scan.map(n => `
                        <tr style="cursor: pointer;" onclick="selectSsid('${n.ssid}')">
                            <td style="font-weight: 500;">${n.ssid}</td>
                            <td>${n.signal}%</td>
                            <td style="color: var(--text-light);">${n.security || 'Open'}</td>
                            <td style="text-align: right;"><span class="badge badge-green" style="font-size: 0.75rem;">Select</span></td>
                        </tr>
                    `).join('');
            }

            // Saved network configurations
            const savedRes = await fetch('/wifi/saved');
            if (savedRes.ok) {
                const saved = await savedRes.json();
                const container = document.getElementById('saved-container');
                container.innerHTML = saved.length === 0
                    ? '<tr><td colspan="3" class="state-placeholder">No saved credentials.</td></tr>'
                    : saved.map(s => `
                        <tr>
                            <td style="font-weight: 500;">${s.ssid}</td>
                            <td>${s.priority}</td>
                            <td style="text-align: right;">
                                <button onclick="deleteWifiCredential('${s.ssid}')" style="background: none; border: none; color: var(--red-text); font-weight: 600; cursor: pointer; font-size: 0.85rem;">Delete</button>
                            </td>
                        </tr>
                    `).join('');
            }
        }
    } catch (error) {
        console.error('Error fetching dashboard updates:', error);
    }
}

// Populate SSID input field when a scanned row is clicked
function selectSsid(ssid) {
    document.getElementById('wifi-ssid').value = ssid;
    document.getElementById('wifi-password').focus();
}

// POST new credentials to the API
async function saveWifiCredential(event) {
    event.preventDefault();
    const ssid = document.getElementById('wifi-ssid').value;
    const password = document.getElementById('wifi-password').value;
    const priority = parseInt(document.getElementById('wifi-priority').value) || 0;

    try {
        const res = await fetch('/wifi/saved', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ssid, password, priority })
        });
        if (res.ok) {
            // Reset form
            document.getElementById('wifi-ssid').value = '';
            document.getElementById('wifi-password').value = '';
            document.getElementById('wifi-priority').value = '0';
            alert(`Wi-Fi credentials saved for ${ssid}. Connection check initiated!`);
            updateData();
        } else {
            alert('Failed to save Wi-Fi configuration.');
        }
    } catch (err) {
        console.error('Error saving Wi-Fi:', err);
    }
}

// DELETE credentials from database
async function deleteWifiCredential(ssid) {
    if (!confirm(`Are you sure you want to delete saved credentials for ${ssid}?`)) {
        return;
    }

    try {
        const res = await fetch(`/wifi/saved/${encodeURIComponent(ssid)}`, {
            method: 'DELETE'
        });
        if (res.ok) {
            updateData();
        } else {
            alert('Failed to delete Wi-Fi network.');
        }
    } catch (err) {
        console.error('Error deleting Wi-Fi:', err);
    }
}

// Toggle password field visibility
function togglePasswordVisibility() {
    const passwordField = document.getElementById('wifi-password');
    if (passwordField.type === 'password') {
        passwordField.type = 'text';
    } else {
        passwordField.type = 'password';
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
