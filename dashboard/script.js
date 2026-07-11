// Templates for adding dummy memories via the dashboard button
const dummyMemoriesPool = [
    { title: "Vibe Check", content: "Current system vibes are extremely optimal and flow state is maintained.", type: "log", source: "user" },
    { title: "Quantum Encryption Idea", content: "Research post-quantum secure log storage algorithms for next sprint release.", type: "idea", source: "manual" },
    { title: "CSS Glow Border Bug", content: "Memory card glowing border triggers slight layouts shifts in Safari. Fix box-sizing.", type: "bug", source: "system" },
    { title: "Octizen Core Engine v0.2 Blueprint", content: "Incorporate semantic vector retrieval using sentence transformers for long-term memory retrieval.", type: "idea", source: "system" },
    { title: "Binaural Beats Integration", content: "Drafting ambient noise engine matching user memory focus states.", type: "idea", source: "manual" },
    { title: "API Performance Peak", content: "Response times checked: POST requests average 3.2ms, GET requests average 1.8ms.", type: "log", source: "system" },
    { title: "User Feedback Loop", content: "Internal testers highlighted that glassmorphism dark theme layout makes the stream easier to monitor.", type: "idea", source: "user" },
    { title: "Coffee Reserves Alert", content: "Critical level of workspace caffeine detected. Order dark roast refills.", type: "bug", source: "manual" }
];

// Templates for adding dummy logs via the dashboard button
const dummyLogsPool = [
    { message: "User triggered 'Add Dummy Memory' via dashboard button", level: "INFO" },
    { message: "Submitting POST request to /api/memories...", level: "DEBUG" },
    { message: "Successfully saved memory record to SQLite DB", level: "INFO" },
    { message: "Warning: High frequency database poll request interval detected", level: "WARNING" },
    { message: "Memory consolidation daemon successfully booted in background", level: "INFO" },
    { message: "Heartbeat ping: Latency check to SQLite ok (0.4ms)", level: "DEBUG" },
    { message: "Dashboard UI state synced without browser page reload", level: "INFO" },
    { message: "System memory cleanup freed 8.4MB of dangling connections", level: "DEBUG" },
    { message: "Error reading config file fallback (handled automatically)", level: "WARNING" }
];

// Formatting helper: converts UTC ISO 8601 string to a clean local date-time string
function formatTimestamp(isoString) {
    try {
        const date = new Date(isoString);
        if (isNaN(date.getTime())) return isoString;
        
        const pad = (num) => String(num).padStart(2, '0');
        
        const yyyy = date.getFullYear();
        const mm = pad(date.getMonth() + 1);
        const dd = pad(date.getDate());
        const hh = pad(date.getHours());
        const min = pad(date.getMinutes());
        const sec = pad(date.getSeconds());
        
        return `${yyyy}-${mm}-${dd} ${hh}:${min}:${sec}`;
    } catch (e) {
        return isoString;
    }
}

// State cache to avoid re-rendering DOM elements if the data hasn't changed
let lastMemoriesJson = "";
let lastLogsJson = "";

// Fetch data from FastAPI backend and render updates
async function updateDashboard() {
    try {
        const [memoriesResponse, logsResponse] = await Promise.all([
            fetch('/api/memories'),
            fetch('/api/logs')
        ]);
        
        if (!memoriesResponse.ok || !logsResponse.ok) {
            throw new Error("HTTP error retrieving dashboard data");
        }
        
        const memories = await memoriesResponse.json();
        const logs = await logsResponse.json();
        
        // Update stats
        document.getElementById('memory-count').textContent = memories.length;
        document.getElementById('log-count').textContent = logs.length;
        
        // Check and render memories if payload has changed
        const memoriesJson = JSON.stringify(memories);
        if (memoriesJson !== lastMemoriesJson) {
            lastMemoriesJson = memoriesJson;
            renderMemories(memories);
        }
        
        // Check and render logs if payload has changed
        const logsJson = JSON.stringify(logs);
        if (logsJson !== lastLogsJson) {
            lastLogsJson = logsJson;
            renderLogs(logs);
        }
        
    } catch (error) {
        console.error("Dashboard update failed:", error);
    }
}

// Render Memories to DOM
function renderMemories(memories) {
    const feed = document.getElementById('memories-feed');
    if (memories.length === 0) {
        feed.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">💭</span>
                <p>No memories found. Click 'Add Dummy Memory' to seed one!</p>
            </div>
        `;
        return;
    }
    
    feed.innerHTML = memories.map(memory => `
        <div class="memory-card type-${memory.type || 'general'}" id="memory-${memory.id}">
            <div class="memory-header">
                <h4 class="memory-title">${escapeHTML(memory.title)}</h4>
                <span class="memory-type-badge">${escapeHTML(memory.type)}</span>
            </div>
            <p class="memory-content">${escapeHTML(memory.content)}</p>
            <div class="memory-footer">
                <div class="memory-meta">
                    <span class="memory-source">
                        <strong>Source:</strong> ${escapeHTML(memory.source)}
                    </span>
                    <span class="memory-date">
                        <strong>Created:</strong> ${formatTimestamp(memory.created_at)}
                    </span>
                </div>
                <button onclick="deleteMemory(${memory.id})" class="delete-btn" title="Delete Memory">
                    <svg class="delete-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
                </button>
            </div>
        </div>
    `).join('');
}

// Render Logs to DOM
function renderLogs(logs) {
    const stream = document.getElementById('logs-stream');
    if (logs.length === 0) {
        stream.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">📂</span>
                <p>No log entries found. Click 'Add Dummy Log' to seed one!</p>
            </div>
        `;
        return;
    }
    
    stream.innerHTML = logs.map(log => `
        <div class="log-row level-${escapeHTML(log.level)}">
            <span class="log-time">[${formatTimestamp(log.created_at)}]</span>
            <span class="log-level">${escapeHTML(log.level)}</span>
            <span class="log-message">${escapeHTML(log.message)}</span>
        </div>
    `).join('');
}

// Safe string escaping for HTML injection to prevent XSS
function escapeHTML(str) {
    if (!str) return '';
    return str.replace(/[&<>'"]/g, 
        tag => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        }[tag] || tag)
    );
}

// Call API to create a dummy memory
async function createDummyMemory() {
    const randomIndex = Math.floor(Math.random() * dummyMemoriesPool.length);
    const payload = dummyMemoriesPool[randomIndex];
    
    try {
        const response = await fetch('/api/memories', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        if (response.ok) {
            // Instantly pull updates
            updateDashboard();
        } else {
            console.error("Failed to add dummy memory");
        }
    } catch (e) {
        console.error("Error calling POST /api/memories:", e);
    }
}

// Call API to create a dummy log
async function createDummyLog() {
    const randomIndex = Math.floor(Math.random() * dummyLogsPool.length);
    const payload = dummyLogsPool[randomIndex];
    
    try {
        const response = await fetch('/api/logs', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        if (response.ok) {
            // Instantly pull updates
            updateDashboard();
        } else {
            console.error("Failed to add dummy log");
        }
    } catch (e) {
        console.error("Error calling POST /api/logs:", e);
    }
}

// Call API to delete a memory
async function deleteMemory(memoryId) {
    if (!confirm("Are you sure you want to delete this memory?")) return;
    
    try {
        const response = await fetch(`/api/memories/${memoryId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            // Remove card from DOM instantly or wait for next tick
            const card = document.getElementById(`memory-${memoryId}`);
            if (card) {
                card.style.opacity = '0';
                card.style.transform = 'translateY(10px)';
                setTimeout(() => updateDashboard(), 150);
            } else {
                updateDashboard();
            }
        } else {
            console.error(`Failed to delete memory with id ${memoryId}`);
        }
    } catch (e) {
        console.error("Error calling DELETE /api/memories:", e);
    }
}

// Initialize application
document.addEventListener('DOMContentLoaded', () => {
    // Wire up sidebar action buttons
    document.getElementById('add-dummy-memory-btn').addEventListener('click', createDummyMemory);
    document.getElementById('add-dummy-log-btn').addEventListener('click', createDummyLog);

    // Initial fetch on page load
    updateDashboard();

    // Auto-refresh: poll every 1 second — picks up GPIO button presses automatically
    setInterval(updateDashboard, 1000);
});
