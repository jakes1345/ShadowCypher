// ShadowCypher - Router Admin Panel
// ================================

// Auth state
let isAuthenticated = false;
let currentUser = null;
let killSwitchActive = false;
let has2FA = false;

// Boot sequence - runs on first load
function runBootSequence() {
  const overlay = document.getElementById('boot-overlay');
  if (!overlay) return;
  setTimeout(() => {
    overlay.classList.add('boot-done');
    setTimeout(() => overlay.remove(), 700);
  }, 2500);
}

// Security status (SECURE / COMPROMISED) from fail2ban + IDS
async function updateSecurityIndicator() {
  const el = document.getElementById('security-indicator');
  const dot = document.getElementById('security-indicator-dot');
  const text = document.getElementById('security-indicator-text');
  if (!el || !text) return;
  try {
    const [f2b, ids] = await Promise.all([
      fetch('/api/fail2ban').then(r => r.json()).catch(() => ({ jails: [] })),
      fetch('/api/intel/ids-alerts').then(r => r.json()).catch(() => ({ alerts: '' }))
    ]);
    const banned = (f2b.jails || []).some(j => (j.banned || 0) > 0);
    const hasAlerts = ids.alerts && ids.alerts.length > 5 && !ids.alerts.includes('No IDS alerts');
    const compromised = banned || hasAlerts;
    el.classList.toggle('secure', !compromised);
    el.classList.toggle('compromised', compromised);
    text.textContent = compromised ? 'COMPROMISED' : 'SECURE';
  } catch (_) {
    el.classList.add('secure');
    el.classList.remove('compromised');
    text.textContent = 'SECURE';
  }
}

// Auth functions
async function checkAuth() {
    try {
        const [statusRes, killRes] = await Promise.all([
            fetch('/api/auth/status'),
            fetch('/api/security/kill-switch')
        ]);
        const d = await statusRes.json();
        const kill = await killRes.json();
        killSwitchActive = !!kill?.active;
        isAuthenticated = d.authenticated;
        currentUser = d.user || null;
        has2FA = !!d.has2FA;
        if (!isAuthenticated) {
            document.getElementById('login-modal').style.display = 'flex';
        } else {
            document.getElementById('login-modal').style.display = 'none';
            initApp();
            updateSecurityIndicator();
        }
        updateKillSwitchUI();
    } catch (e) {
        console.log('Auth check failed', e);
        document.getElementById('login-modal').style.display = 'flex';
    }
}

async function doLogin() {
    const u = document.getElementById('login-username').value;
    const p = document.getElementById('login-password').value;
    const totp = document.getElementById('login-totp')?.value?.trim() || '';
    const err = document.getElementById('login-error');
    err.style.display = 'none';
    try {
        const body = { username: u, password: p };
        if (totp) body.totpCode = totp;
        const r = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        const d = await r.json();
        if (r.status === 429) {
            err.textContent = d.message || d.error || 'Too many attempts. Try again in 15 minutes.';
            err.style.display = 'block';
            return;
        }
        if (d.success) {
            isAuthenticated = true;
            currentUser = d.user;
            document.getElementById('login-modal').style.display = 'none';
            document.getElementById('login-totp-wrap')?.classList.remove('visible');
            initApp();
        } else if (d.require2FA) {
            document.getElementById('login-totp-wrap')?.classList.add('visible');
            err.textContent = d.error || 'Enter 2FA code';
            err.style.display = 'block';
        } else {
            err.textContent = d.error || 'Login failed';
            err.style.display = 'block';
        }
    } catch (e) {
        err.textContent = e.message?.includes('rate') ? 'Too many attempts. Try again later.' : 'Connection error';
        err.style.display = 'block';
    }
}

function updateKillSwitchUI() {
    const overlay = document.getElementById('kill-switch-overlay');
    if (!overlay) return;
    overlay.style.display = killSwitchActive ? 'flex' : 'none';
}

async function reverseKillSwitch() {
    const r = await api('/security/kill-switch/reverse', { method: 'POST' });
    if (r?.success) {
        killSwitchActive = false;
        updateKillSwitchUI();
        toast('Kill switch reversed', 'success');
    } else {
        toast(r?.error || 'Failed', 'error');
    }
}

async function activateKillSwitch() {
    if (!confirm('Activate Kill Switch? This will block ALL outbound traffic.')) return;
    const r = await api('/security/kill-switch', { method: 'POST' });
    if (r?.success) {
        killSwitchActive = true;
        updateKillSwitchUI();
        toast('Kill switch activated', 'warning');
    } else {
        toast(r?.error || 'Failed', 'error');
    }
}

async function setup2FA() {
    const r = await api('/auth/2fa/setup', { method: 'POST' });
    if (!r?.secret) { toast(r?.error || 'Failed', 'error'); return; }
    document.getElementById('2fa-qr').src = r.qrDataUrl;
    document.getElementById('2fa-secret').textContent = r.secret;
    document.getElementById('2fa-setup-modal').style.display = 'flex';
}

async function verify2FA() {
    const code = document.getElementById('2fa-verify-code').value.trim();
    if (!code) return toast('Enter code', 'error');
    const r = await api('/auth/2fa/verify', { method: 'POST', body: { code } });
    if (r?.success) {
        document.getElementById('2fa-setup-modal').style.display = 'none';
        toast('2FA enabled', 'success');
        document.getElementById('2fa-status')?.classList.add('enabled');
    } else {
        toast(r?.error || 'Invalid code', 'error');
    }
}

async function disable2FA() {
    const pw = prompt('Enter your password to disable 2FA:');
    if (!pw) return;
    const r = await api('/auth/2fa/disable', { method: 'POST', body: { password: pw } });
    if (r?.success) {
        toast('2FA disabled', 'success');
        document.getElementById('2fa-status')?.classList.remove('enabled');
    } else {
        toast(r?.error || 'Failed', 'error');
    }
}

async function logoutAll() {
    if (!confirm('Force logout all sessions?')) return;
    const r = await api('/auth/logout-all', { method: 'POST' });
    if (r?.success) {
        toast('All sessions logged out', 'success');
        isAuthenticated = false;
        document.getElementById('login-modal').style.display = 'flex';
    } else {
        toast('Failed', 'error');
    }
}

// Initialize app - called after successful login
function initApp() { 
    loadDash(); 
}

// Allow Enter key to login
document.addEventListener('keypress', function(e) {
    if (e.key === 'Enter' && document.getElementById('login-modal').style.display !== 'none') {
        doLogin();
    }
});


async function api(p, o = {}) { 
    try { 
        const r = await fetch('/api' + p, { ...o, headers: { ...(o.headers || {}), 'Content-Type': 'application/json' }, body: o.body ? JSON.stringify(o.body) : undefined });
        if (r.status === 401) {
            isAuthenticated = false;
            document.getElementById('login-modal').style.display = 'flex';
            return null;
        }
        return await r.json(); 
    } catch (e) { console.error(p, e); return null } 
}
function toast(m, t = 'info') { const c = document.getElementById('tc'), e = document.createElement('div'); e.className = 'toast ' + t; e.textContent = m; c.appendChild(e); setTimeout(() => e.remove(), 3000) }
function esc(s) { if (s == null) return ''; return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;') }
function escAttr(s) { if (s == null) return ''; return String(s).replace(/\\/g, '\\\\').replace(/'/g, "\\'") }


// Navigation
function go(id) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.getElementById('pg-' + id)?.classList.add('active');
    document.querySelector('[data-page="' + id + '"]')?.classList.add('active');
    const L = { ai: loadAi, hacking: loadHacking, intel: loadIntel, diagnostic: loadDiagnostic, dashboard: loadDash, network: loadNet, devices: loadDevicesPage, portforward: loadPortForward, firewall: loadFW, monitoring: loadMon, tools: loadTools, packages: loadPkgs, services: loadSvc, terminal: initTerm, files: () => loadFiles('/home/jack'), system: loadSys, logs: loadLogs };
    if (L[id]) L[id]()
}

// Dashboard
function setDashLoading(loading) {
    if (!loading) return;
    ['dash-ports-t','dash-conns-t','dash-pf-t','dash-fw-t','dash-arp-t'].forEach(id => {
        const el = document.getElementById(id); if (el) el.innerHTML = '<tr><td colspan="4" style="color:var(--t3)">Loading…</td></tr>';
    });
}
async function loadDash() {
    setDashLoading(true);
    const [ov, lat, disk, conns, wifi, devs, vpn, tor, dash] = await Promise.all([api('/overview'), api('/latency'), api('/disk'), api('/connections'), api('/wifi'), api('/devices'), api('/security/vpn-status'), api('/security/tor-status'), api('/router/dashboard')]);
    setDashLoading(false);
    if (ov) {
        document.getElementById('sb-host').textContent = ov.hostname;
        const sbText = document.getElementById('sb-status-text');
        const sbDot = document.getElementById('sb-status-dot');
        if (sbText) sbText.textContent = ov.publicIp && ov.publicIp !== 'N/A' ? 'Online' : 'Offline';
        if (sbDot) sbDot.style.background = ov.publicIp && ov.publicIp !== 'N/A' ? 'var(--green)' : 'var(--red)';
        document.getElementById('s-pip').textContent = ov.publicIp;
        document.getElementById('s-lip').textContent = ov.localIps[0]?.ip || 'N/A';
        document.getElementById('s-up').textContent = ov.uptime.replace('up ', '');
        document.getElementById('s-cpu').textContent = ov.cpuUsage + '%';
        document.getElementById('cpu-bar').style.width = ov.cpuUsage + '%';
        document.getElementById('s-mem').textContent = ov.usedMemPercent + '%';
        document.getElementById('mem-bar').style.width = ov.usedMemPercent + '%';
        const netVal = document.getElementById('router-internet-value');
        if (netVal) netVal.textContent = ov.publicIp && ov.publicIp !== 'N/A' ? ov.publicIp : 'Offline';
        const uptimeShort = document.getElementById('router-uptime-short');
        if (uptimeShort) uptimeShort.textContent = (ov.uptime || '').replace('up ', '') || '—';
    }
    if (conns) document.getElementById('s-conn').textContent = conns.length;
    if (wifi?.connected?.ssid) {
        const el = document.getElementById('router-wifi-ssid');
        if (el) el.textContent = wifi.connected.ssid !== 'N/A' ? wifi.connected.ssid : '—';
    }
    if (Array.isArray(devs)) {
        const el = document.getElementById('router-device-count');
        if (el) el.textContent = devs.length;
    }
    if (lat) document.getElementById('lat-body').innerHTML = lat.map(l => { const ms = parseFloat(l.ping); const c = isNaN(ms) ? 'lat-b' : ms < 15 ? 'lat-g' : ms < 50 ? 'lat-o' : 'lat-b'; return '<div class="lat-row"><span class="lat-n">' + esc(l.name) + '</span><span class="lat-v ' + c + '">' + esc(l.ping) + '</span></div>' }).join('');
    if (disk) document.getElementById('disk-body').innerHTML = disk.map(d => { const p = parseInt(d.pct) || 0; return '<div class="disk-row"><div class="disk-top"><span class="disk-n">' + esc(d.mount) + '</span><span class="disk-u">' + esc(d.used) + '/' + esc(d.size) + ' (' + esc(d.pct) + ')</span></div><div class="disk-bar"><div class="disk-bf" style="width:' + p + '%"></div></div></div>' }).join('');
    if (vpn || tor) {
        const wgEl = document.getElementById('ops-wg'), ovpnEl = document.getElementById('ops-ovpn'), tsEl = document.getElementById('ops-ts'), torEl = document.getElementById('ops-tor'), badgeEl = document.getElementById('ops-status-badge');
        const status = (v) => v ? '<span class="ops-ok">●</span> Active' : '<span class="ops-off">○</span> Off';
        if (wgEl) wgEl.innerHTML = vpn ? status(vpn.wireguard) : '—';
        if (ovpnEl) ovpnEl.innerHTML = vpn ? status(vpn.openvpn) : '—';
        if (tsEl) tsEl.innerHTML = vpn ? status(vpn.tailscale) : '—';
        if (torEl) torEl.innerHTML = tor ? (tor.connected ? '<span class="ops-ok">●</span> ' + (tor.exitIp || 'Active') : '<span class="ops-off">○</span> Off') : '—';
        if (badgeEl) {
            const active = [vpn?.wireguard, vpn?.openvpn, vpn?.tailscale, tor?.connected].filter(Boolean).length;
            badgeEl.textContent = active ? active + ' active' : '—';
        }
    }
    if (dash?.error) {
        ['dash-ports-t','dash-conns-t','dash-pf-t','dash-fw-t','dash-arp-t'].forEach(id => {
            const el = document.getElementById(id); if (el) el.innerHTML = '<tr><td colspan="4" style="color:var(--t3)">—</td></tr>';
        });
        const gwdns = document.getElementById('dash-gw-dns');
        if (gwdns) gwdns.innerHTML = '<div class="lat-row" style="color:var(--t3)">Router data unavailable</div>';
    } else if (dash && !dash.error) {
        const pc = document.getElementById('dash-ports-c'), pt = document.getElementById('dash-ports-t');
        const cc = document.getElementById('dash-conns-c'), ct = document.getElementById('dash-conns-t');
        const pfc = document.getElementById('dash-pf-c'), pft = document.getElementById('dash-pf-t');
        const fwc = document.getElementById('dash-fw-c'), fwt = document.getElementById('dash-fw-t');
        const gwdns = document.getElementById('dash-gw-dns');
        const ac = document.getElementById('dash-arp-c'), at = document.getElementById('dash-arp-t');
        if (pc) pc.textContent = (dash.ports || []).length;
        if (pt) pt.innerHTML = (dash.ports || []).slice(0, 20).map(p => '<tr><td style="color:var(--purple);font-weight:600">' + p.port + '</td><td>' + (p.proto || 'tcp') + '</td><td style="color:var(--green)">' + esc(p.service || '') + '</td><td>' + esc(p.process) + '</td></tr>').join('') || '<tr><td colspan="4" style="color:var(--t3)">None</td></tr>';
        if (cc) cc.textContent = (dash.connections || []).length;
        if (ct) ct.innerHTML = (dash.connections || []).slice(0, 25).map(c => '<tr><td style="color:' + (c.state === 'ESTAB' ? 'var(--green)' : 'var(--t3)') + ';font-weight:600">' + esc(c.state) + '</td><td>' + esc(c.local) + '</td><td>' + esc(c.remote) + '</td><td>' + esc(c.process) + '</td></tr>').join('') || '<tr><td colspan="4" style="color:var(--t3)">None</td></tr>';
        if (pfc) pfc.textContent = (dash.portForward || []).length;
        if (pft) pft.innerHTML = (dash.portForward || []).map(p => '<tr><td>' + p.extPort + '</td><td>' + esc(p.protocol) + '</td><td>→</td><td style="color:var(--cyan)">' + esc(p.intIp) + ':' + p.intPort + '</td></tr>').join('') || '<tr><td colspan="4" style="color:var(--t3)">None</td></tr>';
        if (fwc) fwc.textContent = (dash.firewall || []).length;
        if (fwt) fwt.innerHTML = (dash.firewall || []).slice(0, 15).map(r => '<tr><td>' + r.num + '</td><td style="color:' + (r.target === 'DROP' ? 'var(--red)' : r.target === 'ACCEPT' ? 'var(--green)' : 'var(--t2)') + ';font-weight:600">' + esc(r.target) + '</td><td>' + esc(r.protocol) + '</td><td>' + esc(r.source) + '</td></tr>').join('') || '<tr><td colspan="4" style="color:var(--t3)">None</td></tr>';
        if (gwdns) gwdns.innerHTML = '<div class="lat-row"><span class="lat-n">Gateway</span><span class="lat-v" style="color:var(--cyan)">' + esc(dash.gateway || 'N/A') + '</span></div>' + ((dash.dns || []).map((s, i) => '<div class="lat-row"><span class="lat-n">DNS ' + (i + 1) + '</span><span class="lat-v" style="color:var(--cyan)">' + esc(s) + '</span></div>').join('') || '<div class="lat-row"><span class="lat-n">DNS</span><span class="lat-v" style="color:var(--t3)">—</span></div>');
        if (ac) ac.textContent = (dash.arp || []).length;
        if (at) at.innerHTML = (dash.arp || []).slice(0, 20).map(a => '<tr><td style="color:var(--cyan)">' + esc(a.ip) + '</td><td>' + esc(a.mac) + '</td><td style="color:' + (a.state === 'REACHABLE' ? 'var(--green)' : 'var(--t3)') + '">' + esc(a.state) + '</td></tr>').join('') || '<tr><td colspan="3" style="color:var(--t3)">None</td></tr>';
    }
    drawCpu(); drawMem();
}

async function drawCpu() {
    const d = await api('/cpu-history'); if (!d || !d.length) return;
    const cv = document.getElementById('cpu-cv'); if (!cv) return;
    const ctx = cv.getContext('2d'); cv.width = cv.offsetWidth * 2; cv.height = 240;
    const w = cv.width, h = cv.height;
    ctx.clearRect(0, 0, w, h);
    ctx.strokeStyle = 'rgba(255,255,255,.04)'; ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) { const y = h * i / 4; ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke() }
    const g = ctx.createLinearGradient(0, 0, 0, h); g.addColorStop(0, 'rgba(255,165,0,.15)'); g.addColorStop(1, 'rgba(255,165,0,0)');
    ctx.fillStyle = g; ctx.beginPath(); ctx.moveTo(0, h);
    const s = w / Math.max(d.length - 1, 1);
    d.forEach((v, i) => ctx.lineTo(i * s, h - (v / 100) * h)); ctx.lineTo(w, h); ctx.closePath(); ctx.fill();
    ctx.strokeStyle = '#ffa500'; ctx.lineWidth = 2; ctx.lineJoin = 'round'; ctx.beginPath();
    d.forEach((v, i) => { const x = i * s, y = h - (v / 100) * h; i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y) }); ctx.stroke();
    document.getElementById('cpu-now').textContent = d[d.length - 1].toFixed(1) + '%'
}

async function drawMem() {
    const d = await api('/mem-history'); if (!d || !d.length) return;
    const cv = document.getElementById('mem-cv'); if (!cv) return;
    const ctx = cv.getContext('2d'); cv.width = cv.offsetWidth * 2; cv.height = 240;
    const w = cv.width, h = cv.height;
    ctx.clearRect(0, 0, w, h);
    ctx.strokeStyle = 'rgba(255,255,255,.04)'; ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) { const y = h * i / 4; ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke() }
    const g = ctx.createLinearGradient(0, 0, 0, h); g.addColorStop(0, 'rgba(0,191,255,.15)'); g.addColorStop(1, 'rgba(0,191,255,0)');
    ctx.fillStyle = g; ctx.beginPath(); ctx.moveTo(0, h);
    const s = w / Math.max(d.length - 1, 1);
    d.forEach((v, i) => ctx.lineTo(i * s, h - (v / 100) * h)); ctx.lineTo(w, h); ctx.closePath(); ctx.fill();
    ctx.strokeStyle = '#00bfff'; ctx.lineWidth = 2; ctx.lineJoin = 'round'; ctx.beginPath();
    d.forEach((v, i) => { const x = i * s, y = h - (v / 100) * h; i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y) }); ctx.stroke();
    document.getElementById('mem-now').textContent = d[d.length - 1].toFixed(1) + '%'
}

// Network
async function loadNet() {
    const [wifi, devs, dns, ifs, routes, arp] = await Promise.all([api('/wifi'), api('/devices'), api('/dns'), api('/interfaces'), api('/routes'), api('/arp')]);
    if (wifi?.connected) { const c = wifi.connected; document.getElementById('wifi-info').innerHTML = '<div class="wifi-info"><div class="ws"><span class="wsl">SSID</span><span class="wsv">' + c.ssid + '</span></div><div class="ws"><span class="wsl">Frequency</span><span class="wsv">' + c.frequency + '</span></div></div>' }
    if (wifi?.nearby) { document.getElementById('wn-c').textContent = wifi.nearby.length; document.getElementById('wn-t').innerHTML = wifi.nearby.map(n => '<tr><td style="color:var(--cyan)">' + (esc(n.ssid) || 'Hidden') + '</td><td>' + esc(n.signal) + '</td><td>' + esc(n.security) + '</td><td>' + esc(n.channel) + '</td><td><button class="abtn success" onclick="wifiConnect(\'' + escAttr(n.ssid) + '\')">Connect</button></td></tr>').join('') }
    if (devs) { const dc = document.getElementById('dv-c'); const dt = document.getElementById('dv-t'); if (dc) dc.textContent = devs.length; if (dt) dt.innerHTML = devs.map(d => '<tr><td style="color:var(--cyan)">' + esc(d.ip) + '</td><td>' + (d.mac || 'N/A') + '</td><td>' + esc(d.hostname) + '</td><td style="color:var(--green)">' + esc(d.status) + '</td></tr>').join('') }
    if (ifs) document.getElementById('if-t').innerHTML = ifs.map(i => '<tr><td style="color:var(--cyan)">' + i.name + '</td><td style="color:' + (i.state === 'UP' ? 'var(--green)' : 'var(--red)') + '"><b>' + i.state + '</b></td><td>' + i.addresses + '</td></tr>').join('');
    if (routes) document.getElementById('rt-body').innerHTML = '<pre class="to" style="margin:0 14px 14px">' + routes.routes.join('\n') + '</pre>';
    if (dns) document.getElementById('dns-body').innerHTML = dns.servers.length ? dns.servers.map(s => '<div class="lat-row"><span class="lat-n">Nameserver</span><span class="lat-v" style="color:var(--cyan)">' + s + '</span></div>').join('') : '<div style="padding:14px 18px;color:var(--t3)">No DNS servers</div>';
    if (arp) document.getElementById('arp-t').innerHTML = arp.map(a => '<tr><td style="color:var(--cyan)">' + a.ip + '</td><td>' + a.mac + '</td><td style="color:' + (a.state === 'REACHABLE' ? 'var(--green)' : 'var(--t3)') + '">' + a.state + '</td></tr>').join('');
}

async function wifiConnect(ssid) { const pw = prompt('Password for "' + ssid + '":'); if (pw === null) return; const r = await api('/wifi/connect', { method: 'POST', body: { ssid, password: pw } }); toast(r?.success ? 'Connected to ' + ssid : r?.output || 'Failed', r?.success ? 'success' : 'error'); loadNet() }
async function scanDev() { toast('Scanning...', 'info'); await api('/devices/scan', { method: 'POST' }); setTimeout(() => { loadNet(); loadDevicesPage(); }, 2000) }

// Devices
async function loadDevicesPage() {
    const geo = document.getElementById('dv-geo-enrich')?.checked;
    const devs = await api('/devices' + (geo ? '?enrich=geo' : '')) || [];
    const countEl = document.getElementById('dv-c-page');
    const tableEl = document.getElementById('dv-t-page');
    if (!tableEl) return;
    if (countEl) countEl.textContent = Array.isArray(devs) ? devs.length : 0;
    const loc = (d) => (d.country || d.city) ? esc([d.city, d.country].filter(Boolean).join(', ')) : '—';
    tableEl.innerHTML = devs.length ? devs.map(d => '<tr><td style="color:var(--cyan)">' + esc(d.ip) + '</td><td>' + esc(d.mac || 'N/A') + '</td><td>' + esc(d.hostname) + '</td><td style="color:var(--green)">' + esc(d.status) + '</td><td style="font-size:11px;color:var(--t3)">' + loc(d) + '</td></tr>').join('') : '<tr><td colspan="5" style="color:var(--t3);padding:14px 18px">No devices on network</td></tr>';
}

// Port Forwarding
async function loadPortForward() {
    const r = await api('/portforward');
    const list = Array.isArray(r) ? r : [];
    const countEl = document.getElementById('pf-c');
    const tableEl = document.getElementById('pf-t');
    if (countEl) countEl.textContent = list.length;
    if (!tableEl) return;
    tableEl.innerHTML = list.length ? list.map(x => '<tr><td>' + x.extPort + '</td><td style="color:var(--cyan)">' + esc(x.intIp) + '</td><td>' + x.intPort + '</td><td>' + esc(x.protocol) + '</td><td><button class="abtn danger" onclick="deletePortForward(' + x.num + ')">Remove</button></td></tr>').join('') : '<tr><td colspan="5" style="color:var(--t3);padding:14px 18px">No port forwarding rules</td></tr>';
}

async function addPortForward() {
    const extPort = document.getElementById('pf-ext-port')?.value?.trim();
    const intIp = document.getElementById('pf-int-ip')?.value?.trim();
    const intPort = document.getElementById('pf-int-port')?.value?.trim();
    const protocol = document.getElementById('pf-protocol')?.value || 'tcp';
    if (!extPort || !intIp || !intPort) return toast('Fill all fields', 'error');
    const r = await api('/portforward', { method: 'POST', body: { extPort: parseInt(extPort, 10), intIp, intPort: parseInt(intPort, 10), protocol } });
    if (r?.success) { toast('Rule added', 'success'); loadPortForward(); } else toast(r?.error || 'Failed', 'error');
}

async function deletePortForward(num) { const r = await api('/portforward/' + num, { method: 'DELETE' }); if (r?.success) { toast('Rule removed', 'success'); loadPortForward(); } else toast('Failed', 'error'); }

// Firewall
async function loadFW() {
    const [fw, ports, conns] = await Promise.all([api('/firewall'), api('/ports'), api('/connections')]);
    if (Array.isArray(fw)) { document.getElementById('fw-c').textContent = fw.length; document.getElementById('fw-t').innerHTML = fw.length ? fw.map(r => { const tc = r.target === 'DROP' ? 'var(--red)' : r.target === 'ACCEPT' ? 'var(--green)' : 'var(--t2)'; return '<tr><td>' + r.num + '</td><td style="color:' + tc + ';font-weight:700">' + esc(r.target) + '</td><td>' + esc(r.protocol) + '</td><td style="color:var(--cyan)">' + esc(r.source) + '</td><td>' + esc(r.destination) + '</td><td><button class="abtn danger" onclick="fwDel(' + r.num + ')">X</button></td></tr>' }).join('') : '<tr><td colspan="6" style="color:var(--t3);padding:14px 18px">No rules</td></tr>' }
    if (Array.isArray(ports)) { document.getElementById('pt-c').textContent = ports.length; document.getElementById('pt-t').innerHTML = ports.map(p => '<tr><td style="color:var(--purple);font-weight:600">' + p.port + '</td><td style="color:var(--green)">' + esc(p.service) + '</td><td>' + esc(p.address) + '</td><td>' + esc(p.process) + '</td></tr>').join('') }
    if (Array.isArray(conns)) { document.getElementById('cn-c').textContent = conns.length; document.getElementById('cn-t').innerHTML = conns.slice(0, 60).map(c => '<tr><td style="color:' + (c.state === 'ESTAB' ? 'var(--green)' : 'var(--t3)') + ';font-weight:600">' + esc(c.state) + '</td><td>' + esc(c.local) + '</td><td>' + esc(c.remote) + '</td><td>' + esc(c.process) + '</td></tr>').join('') }
}

async function fwBlock() { const ip = document.getElementById('fw-ip').value.trim(); if (!ip) return toast('Enter IP', 'error'); const r = await api('/firewall/block-ip', { method: 'POST', body: { ip } }); toast(r?.success ? 'Blocked ' + ip : 'Failed', r?.success ? 'success' : 'error'); loadFW() }
async function fwOpen() { const p = document.getElementById('fw-port').value.trim(), pr = document.getElementById('fw-pr').value; if (!p) return toast('Enter port', 'error'); await api('/firewall/open-port', { method: 'POST', body: { port: p, protocol: pr } }); toast('Opened ' + p, 'success'); loadFW() }
async function fwDel(n) { const r = await api('/firewall/delete-rule', { method: 'POST', body: { ruleNum: n } }); toast(r?.success ? 'Deleted' : 'Failed', r?.success ? 'success' : 'error'); loadFW() }

async function wifiDisconnect() { const r = await api('/wifi/disconnect', { method: 'POST' }); toast(r?.success ? 'Disconnected' : 'Failed', r?.success ? 'success' : 'error'); loadNet(); }

async function runSpeedTestFromHome() { toast('Running speed test...', 'info'); const r = await api('/speedtest', { method: 'POST' }); if (r?.mbps) toast('Download: ' + r.mbps + ' Mbps', 'success'); loadDash(); }

async function sysPower(a) { if (!confirm(a.toUpperCase() + ' the system?')) return; const r = await api('/power/' + a, { method: 'POST' }); if (r?.success) toast('System ' + a + ' sent', 'success'); }

function fbUp() { const parts = currentDir.split('/'); if (parts.length > 1) { parts.pop(); loadFiles(parts.join('/') || '/'); } }

function toggleVoiceInput() { toast('Voice input not yet available', 'info'); }

function openIntelConfig() { document.getElementById('intel-config-modal').style.display = 'flex'; }

async function saveIntelConfig() {
  const body = {
    hibpApiKey: document.getElementById('intel-hibp-key').value.trim() || undefined,
    otxApiKey: document.getElementById('intel-otx-key').value.trim() || undefined,
    abuseChAuthKey: document.getElementById('intel-abusech-key').value.trim() || undefined
  };
  const r = await api('/intel/config', { method: 'POST', body });
  if (r?.success) { toast('Saved', 'success'); document.getElementById('intel-config-modal').style.display = 'none'; }
  else toast('Failed', 'error');
}

async function runSniff() { const iface = document.getElementById('sniff-iface').value; const out = document.getElementById('intel-sniff-out'); const stat = document.getElementById('intel-status'); out.textContent = 'Intercepting on ' + (iface || 'any') + '...'; stat.textContent = 'Active'; stat.className = 'badge br'; const r = await api('/intel/sniff', { method: 'POST', body: { iface } }); out.textContent = r?.output || 'No traffic.'; stat.textContent = 'Passive'; stat.className = 'badge br'; }

async function runWifiRecon() { const out = document.getElementById('intel-wifi-out'); out.textContent = 'Scanning...'; const r = await api('/intel/wifi-recon'); out.textContent = (r?.interface ? 'Interface: ' + r.interface + '\n\n' : '') + (r?.output || 'No networks found.'); }

async function runOnionFetch() { const url = document.getElementById('onion-url').value.trim(); if (!url) return toast('URL required', 'error'); const out = document.getElementById('intel-onion-out'); out.textContent = 'Connecting via Tor...'; const r = await api('/intel/onion-fetch', { method: 'POST', body: { url } }); out.textContent = r?.data || r?.error || 'No response'; }

async function loadIdsAlerts() { const b = document.getElementById('ids-body'); b.textContent = 'Loading...'; const r = await api('/intel/ids-alerts'); b.innerHTML = '<pre style="font-size:10px;color:var(--red);white-space:pre-wrap">' + (r?.alerts || 'No alerts') + '</pre>'; }

async function addCron() { const s = document.getElementById('cron-sched').value, c = document.getElementById('cron-cmd').value; if (!s || !c) return toast('Schedule and command required', 'error'); const r = await api('/cron/add', { method: 'POST', body: { schedule: s, command: c } }); toast(r?.success ? 'Added' : 'Failed', r?.success ? 'success' : 'error'); loadSys(); }

async function fwUnblock() { const ip = document.getElementById('fw-ip').value.trim(); if (!ip) return toast('Enter IP', 'error'); const r = await api('/firewall/unblock-ip', { method: 'POST', body: { ip } }); toast(r?.success ? 'Unblocked ' + ip : 'Failed', r?.success ? 'success' : 'error'); loadFW(); }

async function fwClose() { const p = document.getElementById('fw-port').value.trim(), pr = document.getElementById('fw-pr').value; if (!p) return toast('Enter port', 'error'); await api('/firewall/close-port', { method: 'POST', body: { port: p, protocol: pr } }); toast('Closed ' + p, 'success'); loadFW(); }

// Monitoring
async function loadMon() {
    const [bw, procs, temps, usb] = await Promise.all([api('/bandwidth'), api('/processes'), api('/temperatures'), api('/usb')]);
    if (bw) { const i = Object.entries(bw).filter(([n]) => !n.startsWith('veth') && n !== 'docker0'); document.getElementById('bw-body').innerHTML = i.map(([n, s]) => '<div class="bw-row"><div class="bw-label">' + n + '</div><div class="bw-stats"><div class="bw-stat"><span class="bw-sl">Down</span><span class="bw-sv bw-rx">' + s.rxRate + '</span></div><div class="bw-stat"><span class="bw-sl">Up</span><span class="bw-sv bw-tx">' + s.txRate + '</span></div></div></div>').join('') }
    if (procs) document.getElementById('proc-t').innerHTML = procs.map(p => '<tr><td>' + p.pid + '</td><td>' + p.user + '</td><td style="color:' + (parseFloat(p.cpu) > 20 ? 'var(--red)' : 'var(--t2)') + '">' + p.cpu + '%</td><td>' + p.mem + '%</td><td style="font-size:9px;max-width:300px;overflow:hidden;text-overflow:ellipsis">' + p.command + '</td><td><button class="abtn danger" onclick="killProc(' + p.pid + ')">X</button></td></tr>').join('');
    if (temps) document.getElementById('temp-body').innerHTML = temps.length ? temps.map(t => '<div class="temp-row"><span class="temp-l">' + t.label + '</span><span class="temp-v">' + t.temp + 'C</span></div>').join('') : '<div style="padding:14px 18px;color:var(--t3)">No sensors</div>';
    if (usb) document.getElementById('usb-t').innerHTML = usb.length ? usb.map(u => '<tr><td style="color:var(--purple)">' + u.id + '</td><td>' + u.name + '</td></tr>').join('') : '<tr><td colspan="2" style="color:var(--t3);padding:14px 18px">None</td></tr>';
}

async function killProc(pid) { if (!confirm('Kill PID ' + pid + '?')) return; const r = await api('/processes/kill', { method: 'POST', body: { pid } }); toast(r?.success ? 'Killed ' + pid : 'Failed', r?.success ? 'success' : 'error'); loadMon() }

// Tools
async function loadTools() { tool('ping'); tool('dns'); tool('portcheck'); tool('iplookup'); tool('curl') }
async function tool(t) {
    const el = document.getElementById('o-' + t); if (el) { el.textContent = 'Running...'; el.style.color = 'var(--cyan)' }
    let body = {};
    if (t === 'ping') body = { host: document.getElementById('t-ping').value };
    else if (t === 'dns') body = { host: document.getElementById('t-dns').value };
    else if (t === 'portcheck') body = { host: document.getElementById('t-pc-h').value, port: document.getElementById('t-pc-p').value };
    else if (t === 'iplookup') body = { ip: document.getElementById('t-iplookup').value };
    else if (t === 'curl') body = { url: document.getElementById('t-curl').value };
    const r = await api('/tools/' + t, { method: 'POST', body }); if (el) { el.style.color = 'var(--t2)'; el.textContent = r?.output || 'No output' }
}

async function speedTest() { const el = document.getElementById('o-speed'); el.textContent = 'Testing...'; el.style.color = 'var(--cyan)'; const r = await api('/speedtest', { method: 'POST' }); el.style.color = 'var(--green)'; el.textContent = r ? 'Download: ' + r.mbps + ' Mbps' : 'Failed' }

// Services
async function loadSvc() {
    const [mc, dk, ts, svcs] = await Promise.all([api('/minecraft'), api('/docker'), api('/tailscale'), api('/services')]);
    if (mc) { const b = document.getElementById('mc-b'); b.className = 'badge ' + (mc.running ? 'bg' : 'br'); b.textContent = mc.running ? 'ONLINE' : 'OFFLINE'; let h = '<div class="mc-info"><h3 style="color:' + (mc.running ? 'var(--green)' : 'var(--red)') + '">' + (mc.running ? 'Server Running' : 'Offline') + '</h3><p>Port ' + mc.port + '</p></div>'; if (mc.players.length) h += mc.players.map(p => '<span class="mc-p"><span class="sd"></span>' + p + '</span>').join(''); document.getElementById('mc-body').innerHTML = h }
    if (dk?.containers) { document.getElementById('dk-c').textContent = dk.containers.length; document.getElementById('dk-t').innerHTML = dk.containers.length ? dk.containers.map(c => '<tr><td style="color:var(--cyan)">' + esc(c.name) + '</td><td style="font-size:10px">' + esc(c.image) + '</td><td style="color:' + (c.status.includes('Up') ? 'var(--green)' : 'var(--red)') + '">' + esc(c.status) + '</td><td><button class="abtn success" onclick="dkAct(\'' + escAttr(c.name) + '\',\'start\')">></button> <button class="abtn danger" onclick="dkAct(\'' + escAttr(c.name) + '\',\'stop\')">[]</button></td></tr>').join('') : '<tr><td colspan="4" style="color:var(--t3);padding:14px 18px">No containers</td></tr>' }
    if (ts?.peers) document.getElementById('ts-t').innerHTML = ts.peers.length ? ts.peers.map(p => '<tr><td style="color:var(--cyan)">' + esc(p.ip) + '</td><td>' + esc(p.hostname) + '</td><td style="color:var(--green)">' + esc(p.status) + '</td></tr>').join('') : '<tr><td colspan="3" style="color:var(--t3);padding:14px 18px">No peers</td></tr>';
    if (Array.isArray(svcs)) document.getElementById('svc-t').innerHTML = svcs.map(s => '<tr><td style="color:var(--cyan);font-size:10px">' + esc(s.name) + '</td><td style="color:' + (s.active === 'active' ? 'var(--green)' : s.active === 'failed' ? 'var(--red)' : 'var(--t3)') + '">' + esc(s.active) + '</td></tr>').join('');
}

async function dkAct(n, a) { const r = await api('/docker/action', { method: 'POST', body: { name: n, action: a } }); toast(r?.success ? a + ' ' + n : 'Failed', r?.success ? 'success' : 'error'); loadSvc() }

// Terminal
let termWs = null, termInited = false;
function initTerm() {
    if (termInited) return; termInited = true;
    const out = document.getElementById('term-output');
    termWs = new WebSocket('ws://' + location.host + '/ws/terminal');
    termWs.onmessage = e => { out.textContent += e.data; out.scrollTop = out.scrollHeight };
    termWs.onclose = () => { out.textContent += '\n[Connection closed]\n'; termInited = false };
}
function termSend() { const inp = document.getElementById('term-input'); const cmd = inp.value; const out = document.getElementById('term-output'); out.textContent += '$ ' + cmd + '\n'; if (termWs?.readyState === 1) termWs.send(cmd); inp.value = '' }

// Files
let currentDir = '/home/jack';
async function loadFiles(dir) {
    currentDir = dir; document.getElementById('fb-path').textContent = dir;
    const r = await api('/files?path=' + encodeURIComponent(dir)); if (!r) return;
    document.getElementById('fb-t').innerHTML = r.files.map(f => {
        const pathEsc = escAttr(dir + '/' + f.name), nameEsc = esc(f.name);
        if (f.isDir) return '<tr><td><span style="cursor:pointer;color:var(--cyan)" onclick="loadFiles(\'' + pathEsc + '\')">D ' + nameEsc + '</span></td><td>-</td><td>' + esc(f.modified) + '</td><td>' + esc(f.permissions) + '</td></tr>';
        return '<tr><td>F ' + nameEsc + '</td><td>' + esc(f.size) + '</td><td>' + esc(f.modified) + '</td><td>' + esc(f.permissions) + '</td></tr>'
    }).join('')
}

// System
async function loadSys() {
    const [sys, users, startup] = await Promise.all([api('/system'), api('/users'), api('/startup')]);
    if (sys) { document.getElementById('sys-host').textContent = sys.hostinfo; document.getElementById('sys-gpu').textContent = sys.gpu; document.getElementById('sys-pci').textContent = sys.pci; document.getElementById('sys-cron').textContent = sys.cron; document.getElementById('sys-mod').textContent = sys.modules }
    if (users) document.getElementById('usr-t').innerHTML = users.users.map(u => '<tr><td style="color:var(--cyan)">' + u.name + '</td><td>' + u.uid + '</td><td>' + u.home + '</td><td>' + u.shell + '</td></tr>').join('');
    if (startup) document.getElementById('start-t').innerHTML = startup.map(s => '<tr><td style="color:var(--cyan);font-size:10px">' + s.name + '</td><td style="color:var(--green)">' + s.state + '</td></tr>').join('');
    const sb = document.getElementById('2fa-status');
    if (sb) { sb.textContent = has2FA ? '2FA: On' : '2FA: Off'; sb.classList.toggle('enabled', has2FA); sb.classList.toggle('bg', has2FA); sb.classList.toggle('bo', !has2FA); }
}

// Logs
async function loadLogs() { const t = document.getElementById('log-type')?.value || 'syslog', n = document.getElementById('log-n')?.value || 50; const el = document.getElementById('log-area'); el.textContent = 'Loading...'; const r = await api('/logs?type=' + t + '&lines=' + n); el.textContent = r?.lines?.join('\n') || 'No logs'; el.scrollTop = el.scrollHeight }

// Packages
async function loadPkgs() { const u = await api('/packages/upgradable'); if (u) { document.getElementById('up-c').textContent = u.length + ' Updates'; document.getElementById('up-body').textContent = u.length ? u.join(', ') : 'All packages up to date.' } }
async function pkgSearch() { const q = document.getElementById('pkg-q').value; if (!q) return; document.getElementById('pkg-t').innerHTML = '<tr><td colspan="3">Searching...</td></tr>'; const r = await api('/packages/search', { method: 'POST', body: { query: q } }); const list = Array.isArray(r) ? r : []; document.getElementById('pkg-t').innerHTML = list.map(p => '<tr><td style="color:var(--cyan)">' + esc(p.name) + '</td><td>' + esc(p.desc) + '</td><td><button class="abtn success" onclick="pkgAct(\'' + escAttr(p.name) + '\',\'install\')">Install</button></td></tr>').join('') || '<tr><td colspan="3">No packages found</td></tr>'; }
async function pkgAct(n, a) { toast(a + ' ' + n + '...', 'info'); const r = await api('/packages/' + a, { method: 'POST', body: { name: n } }); toast(r?.success ? 'Done' : 'Failed', r?.success ? 'success' : 'error'); loadPkgs() }

// AI
async function loadAi() {
    const c = await api('/ai/config');
    const assistantName = c?.assistantName || 'jarvis';
    const titleEl = document.getElementById('ai-assistant-title');
    if (titleEl) titleEl.textContent = assistantName === 'jarvis' ? 'JARVIS' : assistantName === 'friday' ? 'FRIDAY' : 'Assistant';
    const greetingEl = document.getElementById('ai-greeting');
    if (greetingEl) greetingEl.textContent = 'Ready. Add your API key in Config to start.';
    if (!c?.hasKey) toast('Add your API key in Config.', 'warning');
}

function openAiSettings() { document.getElementById('ai-config-modal').style.display = 'flex'; }
async function saveAiConfig() {
    const k = document.getElementById('ai-key').value.trim();
    const p = document.getElementById('ai-provider').value;
    const a = document.getElementById('ai-assistant').value;
    const body = { provider: p, assistantName: a };
    if (k) body.apiKey = k;
    const r = await api('/ai/config', { method: 'POST', body });
    if (r?.success) { toast('Saved', 'success'); document.getElementById('ai-config-modal').style.display = 'none'; }
    else toast('Failed', 'error');
}

async function aiSend(voiceText) {
    const inp = document.getElementById('ai-input');
    const q = (voiceText != null ? voiceText : inp?.value?.trim() || '').trim();
    const chat = document.getElementById('ai-chat');
    if (!q) return;
    if (inp) inp.value = '';
    const um = document.createElement('div'); um.className = 'msg user'; um.textContent = q; chat.appendChild(um);
    const am = document.createElement('div'); am.className = 'msg ai'; am.textContent = 'One moment...'; chat.appendChild(am);
    chat.scrollTop = chat.scrollHeight;
    const r = await api('/ai/chat', { method: 'POST', body: { messages: [{ role: 'user', content: q }] } });
    if (r?.reply) { am.textContent = r.reply; } else { am.textContent = 'Error. Check API key.'; }
    chat.scrollTop = chat.scrollHeight;
}

// Hacking
function loadHacking() { }
async function loadIntel() {
    loadIdsAlerts();
    loadThreatIntel();
    loadFail2ban();
}
async function loadFail2ban() {
    const el = document.getElementById('intel-f2b-body');
    if (!el) return;
    el.textContent = 'Loading…';
    try {
        const r = await api('/fail2ban');
        if (!r || r.error) { el.innerHTML = '<span style="color:var(--t3)">' + (r?.error || 'Not available') + '</span>'; return; }
        const jails = r.jails || [];
        if (jails.length === 0) { el.innerHTML = '<span style="color:var(--t3)">No jails or fail2ban not running</span>'; return; }
        let html = '<table style="width:100%;font-size:12px"><tr><th style="color:var(--cyan)">Jail</th><th>Banned</th><th>Total</th></tr>';
        jails.forEach(j => {
            const banned = j.banned || 0;
            const color = banned > 0 ? 'var(--red)' : 'var(--green)';
            html += '<tr><td>' + esc(j.name) + '</td><td style="color:' + color + ';font-weight:600">' + banned + '</td><td>' + (j.total || 0) + '</td></tr>';
        });
        html += '</table>';
        el.innerHTML = html;
    } catch (e) { el.innerHTML = '<span style="color:var(--red)">' + esc(e.message) + '</span>'; }
}

// Diagnostic
async function loadDiagnostic() {
    runDiagnostic();
}

async function runDiagnostic() {
    const statusEl = document.getElementById('diag-status');
    const toolsEl = document.getElementById('diag-tools');
    statusEl.innerHTML = '<span style="color:var(--cyan)">Running diagnostic...</span>';
    
    try {
        const r = await api('/diagnostic');
        
        // Status
        let statusHtml = '<table style="width:100%;font-size:12px">';
        for (const [key, val] of Object.entries(r)) {
            if (key === 'recentLogs') continue;
            const color = val.status === 'ok' ? 'var(--green)' : 'var(--red)';
            const icon = val.status === 'ok' ? '✓' : '✗';
            statusHtml += '<tr><td style="padding:4px;color:var(--cyan)">' + key + '</td><td style="color:' + color + '">' + icon + ' ' + (val.message || val.status) + '</td></tr>';
        }
        statusHtml += '</table>';
        statusEl.innerHTML = statusHtml;
        
        // Tools
        let toolsHtml = '<table style="width:100%;font-size:12px">';
        const toolNames = ['nmap', 'nikto', 'sqlmap', 'proxychains', 'tshark', 'tcpdump'];
        for (const t of toolNames) {
            const val = r[t] || {};
            const color = val.status === 'ok' ? 'var(--green)' : 'var(--orange)';
            const icon = val.status === 'ok' ? '✓' : '⚠';
            toolsHtml += '<tr><td style="padding:4px;color:var(--cyan)">' + t + '</td><td style="color:' + color + '">' + icon + ' ' + (val.status === 'ok' ? 'Installed' : 'NOT FOUND - install with: sudo apt install ' + t) + '</td></tr>';
        }
        toolsHtml += '</table>';
        toolsEl.innerHTML = toolsHtml;
        
        // Load logs
        loadAppLogs();
        
    } catch (e) {
        statusEl.innerHTML = '<span style="color:var(--red)">Error: ' + e.message + '</span>';
    }
}

async function loadAppLogs() {
    const logsEl = document.getElementById('diag-logs');
    logsEl.innerHTML = 'Loading logs...';
    try {
        const r = await api('/logs/app');
        if (r.logs && r.logs.length) {
            logsEl.innerHTML = r.logs.map(l => '<div style="padding:2px 0;border-bottom:1px solid #222">' + l + '</div>').join('');
        } else {
            logsEl.innerHTML = '<span style="color:var(--t3)">No logs yet</span>';
        }
    } catch (e) {
        logsEl.innerHTML = '<span style="color:var(--red)">Error: ' + e.message + '</span>';
    }
}

async function runPT(tool) {
    const t = document.getElementById('pt-target').value.trim(); if (!t) return toast('Target required', 'error');
    const out = document.getElementById('pt-out'), stat = document.getElementById('pt-status');
    out.textContent = '[+] Running ' + tool + ' on ' + t + '...';
    stat.textContent = 'Running...'; stat.className = 'badge br';
    const r = await api('/pentest', { method: 'POST', body: { tool, target: t } });
    out.textContent = r?.output || 'No output';
    stat.textContent = 'Ready'; stat.className = 'badge bo';
}

async function toggleShadowMode() {
    const sw = document.getElementById('shadow-toggle'), stat = document.getElementById('shadow-status');
    const r = await api('/hacking/shadow-mode', { method: 'POST', body: { enabled: sw.checked } });
    if (r?.success) { stat.textContent = sw.checked ? 'SHADOW: ON' : 'SHADOW: OFF'; stat.style.color = sw.checked ? 'var(--red)' : 'var(--t3)'; }
}

async function loadThreatIntel() {
    const b = document.getElementById('intel-threat-body');
    b.textContent = 'Fetching...';
    try {
        const r = await api('/intel/threat-feed');
        if (!r) { b.innerHTML = '<span style="color:var(--t3)">No data</span>'; return; }
        const samples = r.samples || [];
        let html = '<div style="color:var(--cyan);font-weight:600;margin-bottom:8px">' + esc(r.source || 'Threat feed') + ' — ' + (r.count || 0) + ' IPs</div>';
        if (samples.length) {
            html += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:4px;font-size:10px;color:var(--red)">';
            samples.slice(0, 25).forEach(ip => { html += '<span>' + esc(ip) + '</span>'; });
            html += '</div>';
        } else html += '<span style="color:var(--t3)">No samples</span>';
        b.innerHTML = html;
    } catch (e) { b.innerHTML = '<span style="color:var(--red)">' + esc(e.message) + '</span>'; }
}
async function checkLeak() { const email = document.getElementById('leak-email').value.trim(); if (!email) return toast('Email required', 'error'); const b = document.getElementById('intel-leak-body'); b.textContent = 'Checking...'; const r = await api('/intel/check-leak', { method: 'POST', body: { email } }); b.innerHTML = r?.breached ? '<b style="color:var(--red)">Breaches found!</b>' : '<b style="color:var(--green)">No breaches found</b>'; }

async function fetchOtxPulses() {
  const b = document.getElementById('intel-otx-body');
  b.textContent = 'Fetching OTX pulses...';
  try {
    const r = await api('/intel/otx');
    if (r?.error) { b.innerHTML = '<span style="color:var(--red)">' + esc(r.error) + '</span>'; return; }
    if (!r?.pulses?.length) { b.innerHTML = '<span style="color:var(--t3)">No pulses found. Subscribe to pulses at otx.alienvault.com</span>'; return; }
    b.innerHTML = r.pulses.map(p => '<div style="margin-bottom:8px;padding:6px;background:#111;border-left:3px solid var(--cyan)"><b style="color:var(--cyan)">' + esc(p.name) + '</b><br><span style="font-size:10px;color:var(--t3)">' + esc(p.author) + ' · ' + (p.indicator_count || 0) + ' IOCs</span><br>' + esc((p.description || '').slice(0, 100)) + '</div>').join('');
  } catch (e) { b.innerHTML = '<span style="color:var(--red)">' + esc(e.message) + '</span>'; }
}

async function checkMalwareBazaar() {
  const hash = document.getElementById('intel-mb-hash').value.trim();
  if (!hash) return toast('Hash required', 'error');
  const b = document.getElementById('intel-mb-body');
  b.textContent = 'Checking MalwareBazaar...';
  try {
    const r = await api('/intel/malwarebazaar', { method: 'POST', body: { hash } });
    if (r?.error) { b.innerHTML = '<span style="color:var(--red)">' + esc(r.error) + '</span>'; return; }
    if (r?.found) {
      b.innerHTML = '<span style="color:var(--red)">⚠ MALWARE DETECTED</span><br><b>' + esc(r.malware || 'Unknown') + '</b><br>SHA256: ' + esc(r.sha256 || hash) + '<br>Tags: ' + (r.tags || []).join(', ') + '<br>First seen: ' + esc(r.first_seen);
    } else {
      b.innerHTML = '<span style="color:var(--green)">Hash not in MalwareBazaar</span><br>' + esc(r?.message || 'No match');
    }
  } catch (e) { b.innerHTML = '<span style="color:var(--red)">' + esc(e.message) + '</span>'; }
}

async function checkUrlhaus() {
  const url = document.getElementById('intel-urlhaus-url').value.trim();
  if (!url) return toast('URL required', 'error');
  const b = document.getElementById('intel-urlhaus-body');
  b.textContent = 'Checking URLhaus...';
  try {
    const r = await api('/intel/urlhaus', { method: 'POST', body: { url } });
    if (r?.error) { b.innerHTML = '<span style="color:var(--red)">' + esc(r.error) + '</span>'; return; }
    if (r?.threat) {
      b.innerHTML = '<span style="color:var(--red)">⚠ MALWARE URL</span><br>Status: ' + esc(r.url_status) + '<br>Threat: ' + esc(r.threat_type) + '<br>Tags: ' + (r.tags || []).join(', ') + '<br><a href="' + esc(r.urlhaus_reference) + '" target="_blank" style="color:var(--cyan)">View in URLhaus</a>';
    } else {
      b.innerHTML = '<span style="color:var(--green)">URL not in URLhaus</span><br>' + esc(r?.message || 'No match');
    }
  } catch (e) { b.innerHTML = '<span style="color:var(--red)">' + esc(e.message) + '</span>'; }
}
async function runDNSBench() { const o = document.getElementById('o-dns-bench'); o.textContent = 'Benchmarking...'; const r = await api('/dns/benchmark'); o.textContent = r.map(s => s.name + ': ' + s.latency).join('\n'); }
async function runAudit() { const o = document.getElementById('o-audit'); o.textContent = 'Auditing...'; const r = await api('/audit/network'); o.textContent = 'Gateway: ' + r.gateway + '\n\n' + r.scan_results; }

// Refresh
async function refreshAll() { toast('Refreshing...', 'info'); const a = document.querySelector('.nav-item.active')?.dataset.page || 'dashboard'; go(a) }

// Init
runBootSequence();
checkAuth();

// Security indicator - poll periodically (endpoints are unauthenticated)
setInterval(updateSecurityIndicator, 30000);
setTimeout(updateSecurityIndicator, 3500);

// Auto-refresh
setInterval(async () => {
    const a = document.querySelector('.nav-item.active')?.dataset.page || 'dashboard';
    if (a === 'dashboard') { drawCpu(); drawMem(); const o = await api('/overview'); if (o) { document.getElementById('s-cpu').textContent = o.cpuUsage + '%'; document.getElementById('cpu-bar').style.width = o.cpuUsage + '%'; document.getElementById('s-mem').textContent = o.usedMemPercent + '%'; document.getElementById('mem-bar').style.width = o.usedMemPercent + '%' } }
}, 5000);
