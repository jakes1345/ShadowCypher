// ShadowCypher - Router Admin Panel with Mr. Robot Aesthetic
// ============================================================

const express = require('express');
const { exec, spawn } = require('child_process');
const path = require('path');
const os = require('os');
const fs = require('fs');
const http = require('http');
const WebSocket = require('ws');
const session = require('express-session');
const crypto = require('crypto');
const rateLimit = require('express-rate-limit');
const { OTP } = require('otplib');
const otp = new OTP();
const QRCode = require('qrcode');

const app = express();
const PORT = 3000;

// Middleware
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname, 'public')));

let shadowMode = false;

// Minecraft server path
const MC_DIR = '/home/jack/Documents/curseforge/minecraft/Instances/Cobblemon Plus+ The Top Pokemon Adventure in Cobblemon - Fully Optimized - Pokemon Z-A -  Cobblemon 1.7.3 - Pokemon Academy/server';

const server = http.createServer(app);

// ========================
// AUTHENTICATION SYSTEM
// ========================
const USERS_FILE = path.join(__dirname, 'users.json');

function loadUsers() {
    try {
        if (fs.existsSync(USERS_FILE)) {
            return JSON.parse(fs.readFileSync(USERS_FILE, 'utf8'));
        }
    } catch (e) {}
    // Default admin - CHANGE IMMEDIATELY!
    const bcrypt = require('bcryptjs');
    const defaultUsers = [{ username: 'admin', password: bcrypt.hashSync('shadow', 10), role: 'admin' }];
    fs.writeFileSync(USERS_FILE, JSON.stringify(defaultUsers, null, 2));
    return defaultUsers;
}

function saveUsers(users) {
    fs.writeFileSync(USERS_FILE, JSON.stringify(users, null, 2));
}

// Session config - MemoryStore with clearAll for force logout (avoids store.on errors)
const sessionStore = new session.MemoryStore();
sessionStore.clearAll = (cb) => sessionStore.clear(cb);

function getSessionSecret() {
    const secretFile = path.join(__dirname, '.session-secret');
    try {
        if (fs.existsSync(secretFile)) return fs.readFileSync(secretFile, 'utf8').trim();
    } catch (e) {}
    const secret = crypto.randomBytes(32).toString('hex');
    fs.writeFileSync(secretFile, secret, { mode: 0o600 });
    return secret;
}

app.use(session({
    secret: getSessionSecret(),
    store: sessionStore,
    resave: false,
    saveUninitialized: false,
    rolling: true,
    cookie: { secure: false, httpOnly: true, maxAge: 24 * 60 * 60 * 1000 }
}));

// ═══════════ LOGGING ═══════════
const LOG_FILE = path.join(__dirname, 'activity.log');

function log(msg, type = 'INFO') {
    const timestamp = new Date().toISOString();
    const logLine = `[${timestamp}] [${type}] ${msg}\n`;
    try { fs.appendFileSync(LOG_FILE, logLine); } catch(e) {}
    console.log(logLine.trim());
}

app.use((req, res, next) => {
    const start = Date.now();
    res.on('finish', () => {
        const duration = Date.now() - start;
        if (res.statusCode >= 400) {
            log(`${req.method} ${req.path} -> ${res.statusCode} (${duration}ms)`, 'ERROR');
        }
    });
    next();
});

// Security headers (HSTS, X-Frame-Options, X-Content-Type-Options, CSP)
app.use((req, res, next) => {
    res.setHeader('Strict-Transport-Security', 'max-age=31536000; includeSubDomains; preload');
    res.setHeader('X-Frame-Options', 'SAMEORIGIN');
    res.setHeader('X-Content-Type-Options', 'nosniff');
    res.setHeader('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self' ws: wss:; frame-ancestors 'self'");
    next();
});

function requireAuth(req, res, next) {
    if (req.session && req.session.user) {
        return next();
    }
    return res.status(401).json({ error: 'Unauthorized', requireLogin: true });
}

// Login rate limit: 5 attempts per 15 min per IP
const loginLimiter = rateLimit({
    windowMs: 15 * 60 * 1000,
    max: 5,
    message: { error: 'Too many login attempts. Try again in 15 minutes.' },
    standardHeaders: true,
    legacyHeaders: false
});

// Auth routes
app.post('/api/auth/login', loginLimiter, async (req, res) => {
    const { username, password, totpCode } = req.body;
    if (!username || !password) {
        return res.status(400).json({ error: 'Username and password required' });
    }
    const bcrypt = require('bcryptjs');
    const users = loadUsers();
    const user = users.find(u => u.username === username);
    if (!user || !bcrypt.compareSync(password, user.password)) {
        return res.status(401).json({ error: 'Invalid credentials' });
    }
    // Require TOTP if user has 2FA enabled
    if (user.totpSecret) {
        if (!totpCode || typeof totpCode !== 'string') {
            return res.status(401).json({ error: '2FA code required', require2FA: true });
        }
        try {
            const valid = otp.verifySync({ secret: user.totpSecret, token: totpCode.trim() });
            if (!valid) {
                return res.status(401).json({ error: 'Invalid 2FA code', require2FA: true });
            }
        } catch (e) {
            return res.status(401).json({ error: 'Invalid 2FA code', require2FA: true });
        }
    }
    req.session.user = { username: user.username, role: user.role };
    res.json({ success: true, user: { username: user.username, role: user.role } });
});

app.post('/api/auth/logout', (req, res) => {
    req.session.destroy();
    res.json({ success: true });
});

app.post('/api/auth/change-password', requireAuth, async (req, res) => {
    const bcrypt = require('bcryptjs');
    const { currentPassword, newPassword } = req.body;
    if (!currentPassword || !newPassword) {
        return res.status(400).json({ error: 'Current and new password required' });
    }
    if (newPassword.length < 4) {
        return res.status(400).json({ error: 'Password must be at least 4 characters' });
    }
    const users = loadUsers();
    const userIndex = users.findIndex(u => u.username === req.session.user.username);
    if (userIndex === -1) {
        return res.status(404).json({ error: 'User not found' });
    }
    if (!bcrypt.compareSync(currentPassword, users[userIndex].password)) {
        return res.status(401).json({ error: 'Current password incorrect' });
    }
    users[userIndex].password = bcrypt.hashSync(newPassword, 10);
    saveUsers(users);
    res.json({ success: true });
});

// 2FA setup - returns secret + QR data URL, stores secret in session until verified
app.post('/api/auth/2fa/setup', requireAuth, async (req, res) => {
    try {
        const secret = otp.generateSecret();
        req.session.totpSetupSecret = secret;
        const otpauth = otp.generateURI({ issuer: 'ShadowCypher', label: req.session.user.username, secret });
        const qrDataUrl = await QRCode.toDataURL(otpauth);
        res.json({ secret, qrDataUrl });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

// 2FA verify - validates code and enables 2FA (persists secret from setup)
app.post('/api/auth/2fa/verify', requireAuth, async (req, res) => {
    const { code } = req.body;
    if (!code) return res.status(400).json({ error: 'Code required' });
    const secret = req.session.totpSetupSecret;
    if (!secret) return res.status(400).json({ error: 'Run 2FA setup first' });
    try {
        const valid = otp.verifySync({ secret, token: String(code).trim() });
        if (!valid) return res.status(401).json({ error: 'Invalid code' });
        const users = loadUsers();
        const userIndex = users.findIndex(u => u.username === req.session.user.username);
        if (userIndex === -1) return res.status(404).json({ error: 'User not found' });
        users[userIndex].totpSecret = secret;
        saveUsers(users);
        delete req.session.totpSetupSecret;
        res.json({ success: true });
    } catch (e) {
        res.status(401).json({ error: 'Invalid code' });
    }
});

// 2FA disable
app.post('/api/auth/2fa/disable', requireAuth, async (req, res) => {
    const { password } = req.body;
    if (!password) return res.status(400).json({ error: 'Password required' });
    const bcrypt = require('bcryptjs');
    const users = loadUsers();
    const userIndex = users.findIndex(u => u.username === req.session.user.username);
    if (userIndex === -1) return res.status(404).json({ error: 'User not found' });
    if (!bcrypt.compareSync(password, users[userIndex].password)) {
        return res.status(401).json({ error: 'Invalid password' });
    }
    delete users[userIndex].totpSecret;
    saveUsers(users);
    res.json({ success: true });
});

// Auth status - include 2FA info
app.get('/api/auth/status', (req, res) => {
    if (req.session && req.session.user) {
        const users = loadUsers();
        const user = users.find(u => u.username === req.session.user.username);
        res.json({
            authenticated: true,
            user: req.session.user,
            has2FA: !!(user && user.totpSecret)
        });
    } else {
        res.json({ authenticated: false });
    }
});

// Force logout all sessions
app.post('/api/auth/logout-all', requireAuth, (req, res) => {
    sessionStore.clearAll(() => {
        res.json({ success: true });
    });
});

// ========================
// KILL SWITCH
// ========================
const KILL_SWITCH_FILE = path.join(__dirname, '.kill-switch');

function isKillSwitchActive() {
    try {
        return fs.existsSync(KILL_SWITCH_FILE);
    } catch (e) { return false; }
}

function setKillSwitchState(active) {
    if (active) {
        fs.writeFileSync(KILL_SWITCH_FILE, '1', { mode: 0o600 });
    } else if (fs.existsSync(KILL_SWITCH_FILE)) {
        fs.unlinkSync(KILL_SWITCH_FILE);
    }
}

app.get('/api/security/kill-switch', (req, res) => {
    res.json({ active: isKillSwitchActive() });
});

app.post('/api/security/kill-switch', requireAuth, async (req, res) => {
    try {
        await run('sudo iptables -N SHADOW_KILL 2>/dev/null || true');
        await run('sudo iptables -F SHADOW_KILL');
        await run('sudo iptables -A SHADOW_KILL -o lo -j RETURN');  // allow loopback so server can respond
        await run('sudo iptables -A SHADOW_KILL -j DROP');
        const outCheck = await run('sudo iptables -C OUTPUT -j SHADOW_KILL 2>/dev/null || echo "not found"');
        if (outCheck === 'not found') {
            await run('sudo iptables -I OUTPUT 1 -j SHADOW_KILL');
        }
        setKillSwitchState(true);
        log('Kill switch ACTIVATED - outbound blocked', 'SECURITY');
        res.json({ success: true, active: true });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

app.post('/api/security/kill-switch/reverse', requireAuth, async (req, res) => {
    try {
        await run('sudo iptables -D OUTPUT -j SHADOW_KILL 2>/dev/null || true');
        await run('sudo iptables -F SHADOW_KILL 2>/dev/null || true');
        await run('sudo iptables -X SHADOW_KILL 2>/dev/null || true');
        setKillSwitchState(false);
        log('Kill switch REVERSED - outbound restored', 'SECURITY');
        res.json({ success: true, active: false });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

// ========================
// ROUTER INTEGRATION
// ========================
const ROUTER_CONFIG_FILE = path.join(__dirname, 'router_config.json');

function getRouterConfig() {
    try {
        if (fs.existsSync(ROUTER_CONFIG_FILE)) {
            return JSON.parse(fs.readFileSync(ROUTER_CONFIG_FILE, 'utf8'));
        }
    } catch (e) {}
    return { type: 'local', host: '', username: '', password: '', apiKey: '' };
}

function saveRouterConfig(config) {
    fs.writeFileSync(ROUTER_CONFIG_FILE, JSON.stringify(config, null, 2));
}

function runSSH(cmd, routerConfig) {
    return new Promise((resolve, reject) => {
        const sshCmd = `sshpass -p '${routerConfig.password}' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 ${routerConfig.username}@${routerConfig.host} "${cmd}"`;
        exec(sshCmd, { timeout: 30000 }, (err, stdout, stderr) => {
            if (err && !stdout) return reject(err);
            resolve((stdout || stderr || '').trim());
        });
    });
}

// Dynamic network helpers (no hardcoded wlo1/192.168.1)
async function getPrimaryIface() {
    try {
        const o = await run('ip route | grep default | head -1');
        const m = o.match(/dev\s+(\S+)/);
        return m ? m[1] : null;
    } catch (_) { return null; }
}
async function getWirelessIface() {
    try {
        const iw = await run('iw dev 2>/dev/null | grep Interface | awk \'{print $2}\' | head -1');
        if (iw && iw.trim()) return iw.trim();
        const nm = await run('nmcli -t -f DEVICE,TYPE device status 2>/dev/null | grep wifi | head -1 | cut -d: -f1');
        return (nm && nm.trim()) ? nm.trim() : null;
    } catch (_) { return null; }
}
async function getScanSubnet() {
    try {
        const o = await run('ip route | grep default | head -1');
        const dev = o.match(/dev\s+(\S+)/)?.[1];
        if (!dev) return '192.168.1.0/24';
        const addr = await run(`ip -4 addr show dev ${dev} 2>/dev/null | grep inet`);
        const m = addr.match(/inet\s+(\d+\.\d+\.\d+\.\d+)\/(\d+)/);
        if (m) return m[1] + '/' + m[2];
        const gw = o.match(/(\d+\.\d+\.\d+)\.\d+/)?.[1];
        return gw ? gw + '.0/24' : '192.168.1.0/24';
    } catch (_) { return '192.168.1.0/24'; }
}
async function getDefaultGateway() {
    try {
        const o = await run('ip route | grep default | head -1');
        const m = o.match(/via\s+(\d+\.\d+\.\d+\.\d+)/);
        return m ? m[1] : '192.168.1.1';
    } catch (_) { return '192.168.1.1'; }
}

// Router config endpoints
app.get('/api/router/config', (req, res) => {
    const config = getRouterConfig();
    // Don't send password
    res.json({ 
        type: config.type, 
        host: config.host, 
        username: config.username, 
        hasPassword: !!config.password,
        apiKey: config.apiKey ? '***set***' : ''
    });
});

app.post('/api/router/config', requireAuth, (req, res) => {
    const { type, host, username, password, apiKey } = req.body;
    const config = getRouterConfig();
    if (type) config.type = type;
    if (host) config.host = host;
    if (username) config.username = username;
    if (password) config.password = password;
    if (apiKey) config.apiKey = apiKey;
    saveRouterConfig(config);
    res.json({ success: true });
});

// Router status based on type
app.get('/api/router/status', async (req, res) => {
    const config = getRouterConfig();
    
    if (config.type === 'local') {
        // Local machine acting as router
        try {
            const gw = await run('ip route | grep default | awk \'{print $3}\'');
            const iface = await run('ip route | grep default | awk \'{print $5}\'');
            res.json({ 
                type: 'local', 
                gateway: gw.trim(), 
                interface: iface.trim(),
                mode: 'This machine'
            });
        } catch (e) {
            res.json({ type: 'local', error: e.message });
        }
    } else if (config.type === 'openwrt') {
        // OpenWrt router via SSH
        try {
            const [uptime, load, mem] = await Promise.all([
                runSSH('cat /proc/uptime', config),
                runSSH('cat /proc/loadavg', config),
                runSSH('free -m | grep Mem', config)
            ]);
            res.json({ 
                type: 'openwrt', 
                host: config.host,
                uptime: uptime.split(' ')[0],
                load: load.split(' ').slice(0,3).join(' '),
                memory: mem
            });
        } catch (e) {
            res.json({ type: 'openwrt', error: e.message });
        }
    } else if (config.type === 'pfsense') {
        // pfSense via API
        try {
            const [status, wan] = await Promise.all([
                runSSH('pfctl -si', config),
                runSSH('ifconfig | grep -A1 em0', config)
            ]);
            res.json({ type: 'pfsense', status: status.substring(0, 500), wan: wan.substring(0, 200) });
        } catch (e) {
            res.json({ type: 'pfsense', error: e.message });
        }
    } else {
        res.json({ type: 'none', message: 'No router configured' });
    }
});

// Router port forwarding (local or remote)
app.get('/api/router/portforward', async (req, res) => {
    const config = getRouterConfig();
    
    try {
        if (config.type === 'local') {
            const o = await run('sudo iptables -t nat -L PREROUTING -n -v --line-numbers 2>/dev/null||echo ""');
            const rules = [];
            for (const l of o.split('\n').slice(2)) {
                const m = l.match(/^\s*(\d+).*DNAT\s+(tcp|udp).*dpt:(\d+)\s+to:([\d.]+):(\d+)/);
                if (m) rules.push({ num: m[1], protocol: m[2], extPort: m[3], intIp: m[4], intPort: m[5], source: 'local' });
            }
            res.json({ source: 'local', rules });
        } else if (config.type === 'openwrt') {
            const o = await runSSH('uci show firewall', config);
            res.json({ source: 'openwrt', config: o });
        }
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

app.post('/api/router/portforward', requireAuth, async (req, res) => {
    const config = getRouterConfig();
    const { extPort, intIp, intPort, protocol = 'tcp' } = req.body;
    
    const port = parseInt(extPort, 10);
    const intP = parseInt(intPort, 10);
    
    if (!port || port < 1 || port > 65535 || !intP || intP < 1 || intP > 65535) {
        return res.status(400).json({ error: 'Invalid ports' });
    }
    if (!/^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(intIp)) {
        return res.status(400).json({ error: 'Invalid internal IP' });
    }

    try {
        if (config.type === 'local') {
            const prot = protocol === 'udp' ? 'udp' : 'tcp';
            await run(`sudo iptables -t nat -A PREROUTING -p ${prot} --dport ${port} -j DNAT --to-destination ${intIp}:${intP}`);
            await run(`sudo iptables -A FORWARD -p ${prot} -d ${intIp} --dport ${intP} -j ACCEPT 2>/dev/null||true`);
            res.json({ success: true, source: 'local' });
        } else if (config.type === 'openwrt') {
            const name = `portfwd_${port}`;
            await runSSH(`uci add firewall redirect`, config);
            await runSSH(`uci set firewall.${name}=redirect`, config);
            await runSSH(`uci set firewall.${name}.target='DNAT'`, config);
            await runSSH(`uci set firewall.${name}.src='wan'`, config);
            await runSSH(`uci set firewall.${name}.dest='lan'`, config);
            await runSSH(`uci set firewall.${name}.proto='${protocol}'`, config);
            await runSSH(`uci set firewall.${name}.src_dport='${port}'`, config);
            await runSSH(`uci set firewall.${name}.dest_ip='${intIp}'`, config);
            await runSSH(`uci set firewall.${name}.dest_port='${intP}'`, config);
            await runSSH('uci commit firewall && /etc/init.d/firewall reload', config);
            res.json({ success: true, source: 'openwrt' });
        }
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

// Router firewall rules
app.get('/api/router/firewall', async (req, res) => {
    const config = getRouterConfig();
    
    try {
        if (config.type === 'local') {
            const o = await run('sudo iptables -L INPUT -n --line-numbers 2>/dev/null||echo ""');
            const rules = [];
            for (const l of o.split('\n').slice(2)) {
                const p = l.trim().split(/\s+/);
                if (p.length >= 5) {
                    rules.push({ num: p[0], target: p[1], protocol: p[2], source: p[4], destination: p[5] || '*' });
                }
            }
            res.json({ source: 'local', rules });
        } else if (config.type === 'openwrt') {
            const o = await runSSH('iptables -L INPUT -n --line-numbers', config);
            res.json({ source: 'openwrt', rules: o });
        }
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

app.post('/api/router/firewall/block-ip', requireAuth, async (req, res) => {
    const config = getRouterConfig();
    const { ip } = req.body;
    
    if (!ip) return res.status(400).json({ error: 'No IP' });
    
    try {
        if (config.type === 'local') {
            await run(`sudo iptables -I INPUT -s ${ip} -j DROP`);
        } else if (config.type === 'openwrt') {
            await runSSH(`uci add firewall rule`, config);
            await runSSH(`uci set firewall.@rule[-1].name='Block-${ip}'`, config);
            await runSSH(`uci set firewall.@rule[-1].src='wan'`, config);
            await runSSH(`uci set firewall.@rule[-1].dest_ip='${ip}'`, config);
            await runSSH(`uci set firewall.@rule[-1].target='DROP'`, config);
            await runSSH('uci commit firewall', config);
        }
        res.json({ success: true });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

// ========================
// WEBSOCKET TERMINAL
// ========================
const wss = new WebSocket.Server({ server, path: '/ws/terminal' });

wss.on('connection', (ws) => {
    const shell = spawn('bash', [], { env: { ...process.env, TERM: 'xterm-256color' } });
    shell.stdout.on('data', d => ws.send(d.toString()));
    shell.stderr.on('data', d => ws.send(d.toString()));
    ws.on('message', msg => shell.stdin.write((Buffer.isBuffer(msg) ? msg.toString() : msg) + '\n'));
    ws.on('close', () => shell.kill());
    shell.on('exit', () => ws.close());
});

// Utility functions
function run(cmd) {
    return new Promise((resolve, reject) => {
        exec(cmd, { timeout: 30000, maxBuffer: 5242880 }, (err, stdout) => {
            if (err && !stdout) return reject(err);
            resolve((stdout || '').trim());
        });
    });
}

function fmt(b) { 
    if (b >= 1073741824) return (b / 1073741824).toFixed(2) + ' GB'; 
    if (b >= 1048576) return (b / 1048576).toFixed(1) + ' MB'; 
    if (b >= 1024) return (b / 1024).toFixed(0) + ' KB'; 
    return b + ' B'; 
}

function fmtR(r) { 
    if (r >= 1048576) return (r / 1048576).toFixed(1) + ' MB/s'; 
    if (r >= 1024) return (r / 1024).toFixed(1) + ' KB/s'; 
    return r.toFixed(0) + ' B/s'; 
}

// CPU tracking
const cpuHist = []; 
let prevCpu = getCpu();
function getCpu() { 
    const c = os.cpus(); 
    let i = 0, t = 0; 
    for (const u of c) { 
        for (const k in u.times) t += u.times[k]; 
        i += u.times.idle; 
    } 
    return { idle: i / c.length, total: t / c.length }; 
}
setInterval(() => { 
    const c = getCpu(); 
    const u = c.total - prevCpu.total > 0 ? ((1 - (c.idle - prevCpu.idle) / (c.total - prevCpu.total)) * 100) : 0; 
    cpuHist.push(parseFloat(u.toFixed(1))); 
    if (cpuHist.length > 120) cpuHist.shift(); 
    prevCpu = c; 
}, 2000);

// Bandwidth tracking
let prevBw = {}, prevBwT = Date.now();
function readDev() { 
    const r = {}; 
    try {
        for (const l of fs.readFileSync('/proc/net/dev', 'utf8').split('\n').slice(2)) { 
            const p = l.trim().split(/[\s:]+/); 
            if (p.length >= 10 && p[0] !== 'lo') r[p[0]] = { rx: parseInt(p[1]), tx: parseInt(p[9]) }; 
        }
    } catch(e) {}
    return r; 
}
prevBw = readDev();

// ========================
// API ROUTES
// ========================

// Overview
app.get('/api/overview', async (req, res) => {
    try {
        const [pub, up, host, load, cpu, kern] = await Promise.all([
            run('curl -4 -s --max-time 4 ifconfig.me 2>/dev/null||echo N/A'),
            run('uptime -p'),
            run('hostname'),
            run('cat /proc/loadavg'),
            run('lscpu 2>/dev/null|grep "Model name"|head -1|sed "s/.*: *//"'),
            run('uname -r')
        ]);
        const ifaces = os.networkInterfaces(), lips = []; 
        for (const [n, a] of Object.entries(ifaces)) 
            for (const x of a) if (!x.internal && x.family === 'IPv4') lips.push({ interface: n, ip: x.address, mac: x.mac });
        const lp = load.split(' '), cu = cpuHist.length > 0 ? cpuHist[cpuHist.length - 1] : 0;
        res.json({
            publicIp: pub, localIps: lips, hostname: host, uptime: up, cpuModel: cpu, cpuUsage: cu.toFixed(0), kernelVersion: kern, 
            load: { m1: lp[0], m5: lp[1], m15: lp[2] },
            totalMem: (os.totalmem() / 1073741824).toFixed(1) + ' GB', freeMem: (os.freemem() / 1073741824).toFixed(1) + ' GB', usedMemPercent: ((1 - os.freemem() / os.totalmem()) * 100).toFixed(0),
            cpus: os.cpus().length, platform: os.platform(), arch: os.arch()
        });
    } catch (e) { res.status(500).json({ error: e.message }) }
});

app.get('/api/cpu-history', (_, res) => res.json(cpuHist));

// MAC Vendor Lookup for device identification
const MAC_VENDORS = {
    // Apple
    'A4:83:E7': 'Apple', 'F0:18:98': 'Apple', '3C:06:30': 'Apple', '60:F8:1D': 'Apple', '68:A8:6D': 'Apple',
    'F0:DB:E2': 'Apple', 'DC:2B:2A': 'Apple', 'E8:80:2E': 'Apple', 'B8:17:C2': 'Apple', '20:C9:D0': 'Apple',
    // Samsung
    'B8:5A:73': 'Samsung', '8C:F5:A3': 'Samsung', '9C:02:98': 'Samsung', 'D0:17:C2': 'Samsung', '78:25:AD': 'Samsung',
    '00:1A:8A': 'Samsung', 'A8:06:00': 'Samsung', 'E4:12:1D': 'Samsung', '00:07:AB': 'Samsung', '30:CD:A7': 'Samsung',
    // Google
    'F4:F5:D8': 'Google', '94:EB:2C': 'Google', '54:60:09': 'Google', '00:1A:11': 'Google', 'F4:F5:E8': 'Google',
    // Amazon
    '0C:47:C9': 'Amazon', '34:D2:70': 'Amazon', '38:F7:3D': 'Amazon', '50:DC:E7': 'Amazon', 'A0:02:DC': 'Amazon',
    '68:37:E9': 'Amazon', '68:54:FD': 'Amazon', '50:5B:C2': 'Amazon', 'F0:27:2D': 'Amazon', '00:FC:8B': 'Amazon',
    // Microsoft
    '3C:83:75': 'Microsoft', 'B4:0E:DE': 'Microsoft', '28:18:78': 'Microsoft', 'DC:B4:C4': 'Microsoft', '7C:1E:52': 'Microsoft',
    // Intel
    '3C:A9:F4': 'Intel', '00:1E:67': 'Intel', '00:1F:3B': 'Intel', '00:22:FA': 'Intel', '00:24:D7': 'Intel',
    '00:26:C6': 'Intel', '00:26:C7': 'Intel', 'DC:53:7C': 'Intel', '48:45:20': 'Intel', 'AC:7B:A1': 'Intel',
    // Dell
    '18:03:73': 'Dell', '18:A9:9B': 'Dell', '18:66:DA': 'Dell', '18:DB:F2': 'Dell', '20:47:47': 'Dell',
    '24:6E:96': 'Dell', '34:17:EB': 'Dell', '44:A8:42': 'Dell', '48:4D:7E': 'Dell', '50:9A:4C': 'Dell',
    // HP
    '00:1E:0B': 'HP', '00:1F:29': 'HP', '00:21:5A': 'HP', '00:22:64': 'HP', '00:24:81': 'HP',
    '00:25:B3': 'HP', '00:26:55': 'HP', '00:30:C1': 'HP', '18:A9:05': 'HP', '38:63:BB': 'HP',
    // Cisco
    '00:17:DF': 'Cisco', '00:1B:2B': 'Cisco', '00:1C:10': 'Cisco', '00:1D:45': 'Cisco', '00:1E:13': 'Cisco',
    '00:1F:6E': 'Cisco', '00:22:55': 'Cisco', '00:23:04': 'Cisco', '00:23:5A': 'Cisco', '00:24:14': 'Cisco',
    // NETGEAR
    '20:0C:C8': 'NETGEAR', '28:C6:8E': 'NETGEAR', '2C:B0:5D': 'NETGEAR', '30:46:9A': 'NETGEAR', '44:94:FC': 'NETGEAR',
    '6C:B0:CE': 'NETGEAR', '84:1B:5E': 'NETGEAR', '9C:3D:CF': 'NETGEAR', 'A0:21:B7': 'NETGEAR', 'A4:2B:B0': 'NETGEAR',
    // TP-Link
    '14:CC:20': 'TP-Link', '14:CF:92': 'TP-Link', '18:A6:F7': 'TP-Link', '1C:FA:68': 'TP-Link', '30:B5:C2': 'TP-Link',
    '50:3E:AA': 'TP-Link', '54:C8:0F': 'TP-Link', '5C:63:BF': 'TP-Link', '60:E3:27': 'TP-Link', '64:66:B3': 'TP-Link',
    // Raspberry Pi
    'B8:27:EB': 'Raspberry Pi', 'DC:A6:32': 'Raspberry Pi', 'E4:5F:01': 'Raspberry Pi', '28:CD:C1': 'Raspberry Pi',
    // NVIDIA
    '00:1E:75': 'NVIDIA', '00:25:00': 'NVIDIA', '00:26:DA': 'NVIDIA', '00:4E:AF': 'NVIDIA', '48:B0:2D': 'NVIDIA',
    // Roku
    '2C:E4:09': 'Roku', '3C:A7:3B': 'Roku', '84:EA:ED': 'Roku', '88:DE:A9': 'Roku', 'AC:3A:7A': 'Roku',
    // Amazon Echo/Spot
    '00:FC:8B': 'Amazon Echo', '34:D2:70': 'Amazon Echo', '38:F7:3D': 'Amazon Echo', '50:DC:E7': 'Amazon Echo',
    // Apple TV
    'A4:5E:60': 'Apple TV', '9C:20:7B': 'Apple TV', 'B8:09:8A': 'Apple TV', 'C8:69:CD': 'Apple TV',
    // Chromecast
    '00:1A:11': 'Chromecast', 'F4:F5:D8': 'Chromecast', 'F4:F5:E8': 'Chromecast', '94:EB:2C': 'Chromecast',
    // PlayStation
    '00:04:4B': 'PlayStation', '00:19:C5': 'PlayStation', '00:19:D5': 'PlayStation', '00:1D:D8': 'PlayStation',
    '00:1F:A4': 'PlayStation', '00:1F:A7': 'PlayStation', '00:24:8D': 'PlayStation', '00:26:AB': 'PlayStation',
    // Xbox
    '00:0D:3A': 'Xbox', '00:15:5D': 'Xbox', '00:17:AB': 'Xbox', '00:1D:D8': 'Xbox', '00:22:48': 'Xbox',
    // Nintendo
    '00:19:1D': 'Nintendo', '00:19:FD': 'Nintendo', '00:1B:7A': 'Nintendo', '00:1B:EA': 'Nintendo', '00:1C:BE': 'Nintendo',
    '00:1D:BC': 'Nintendo', '00:1E:35': 'Nintendo', '00:1F:32': 'Nintendo', '00:1F:C5': 'Nintendo', '00:21:47': 'Nintendo',
    // Smart TVs - LG
    '00:1E:75': 'LG TV', '00:22:A7': 'LG TV', '00:24:83': 'LG TV', '00:25:E9': 'LG TV', '00:26:E2': 'LG TV',
    // Smart TVs - Samsung
    '00:07:AB': 'Samsung TV', '00:1A:8A': 'Samsung TV', '00:21:D1': 'Samsung TV', '00:21:D2': 'Samsung TV',
    '00:23:99': 'Samsung TV', '00:23:D6': 'Samsung TV', '00:23:D7': 'Samsung TV', '00:24:54': 'Samsung TV',
    // Smart TVs - Sony
    '00:04:1F': 'Sony TV', '00:13:A9': 'Sony TV', '00:18:13': 'Sony TV', '00:1D:28': 'Sony TV', '00:1E:45': 'Sony TV',
    // Smart TVs - Vizio
    '00:1E:C2': 'Vizio TV', '00:1F:74': 'Vizio TV', '00:24:5A': 'Vizio TV', '00:26:F2': 'Vizio TV',
    // Smart Things/Gateway
    '00:12:FB': 'SmartThings', '00:17:88': 'SmartThings', '00:1D:6F': 'SmartThings', '00:26:5D': 'SmartThings',
    // Hue Bridge
    '00:17:88': 'Philips Hue', 'EC:B5:FA': 'Philips Hue', '00:1B:63': 'Philips Hue',
    // Sonos
    '00:0E:58': 'Sonos', '00:15:11': 'Sonos', '00:1A:D2': 'Sonos', '00:1B:2D': 'Sonos', '00:1E:58': 'Sonos',
    '00:1F:33': 'Sonos', '00:1F:5F': 'Sonos', '00:21:E8': 'Sonos', '00:22:4C': 'Sonos',
    // Nest
    '18:B4:57': 'Nest', '64:16:66': 'Nest', '64:B7:08': 'Nest', '94:94:26': 'Nest',
    // Ring
    '00:1D:DF': 'Ring', '2C:E4:09': 'Ring', '84:EA:ED': 'Ring', '8C:C8:CD': 'Ring',
    // August Lock
    '18:0B:52': 'August', '18:0E:95': 'August', '70:5A:0F': 'August', '84:2B:2B': 'August',
    // Yale Lock
    '00:0B:98': 'Yale', '00:12:1A': 'Yale', '00:17:6D': 'Yale',
    // Honeywell
    '00:1E:2A': 'Honeywell', '00:1F:3F': 'Honeywell', '00:24:A3': 'Honeywell',
    // Ecobee
    '10:91:34': 'Ecobee', '18:B4:30': 'Ecobee', '30:8D:99': 'Ecobee',
    // Philips Hue
    '00:17:88': 'Philips Hue', 'EC:B5:FA': 'Philips Hue',
    // Lutron
    '00:1D:6F': 'Lutron', '00:23:99': 'Lutron',
    // Smart Plugs
    '50:C7:BF': 'Smart Plug', 'B4:E8:42': 'Smart Plug', 'C0:C1:C0': 'Smart Plug', 'EC1A:59': 'Smart Plug',
    // Unknown common
    '00:1A:2B': 'Unknown', '00:1D:E1': 'Unknown', '00:22:AA': 'Unknown'
};

// Device type inference based on vendor and hostname
function getDeviceInfo(mac, hostname) {
    if (!mac) return { type: 'Unknown', vendor: 'Unknown', icon: '❓' };
    
    const macPrefix = mac.substring(0, 8).toUpperCase();
    const vendor = MAC_VENDORS[macPrefix] || 'Unknown';
    
    const h = (hostname || '').toLowerCase();
    
    // Smart home / IoT detection
    if (h.includes('echo') || h.includes('alexa') || vendor === 'Amazon Echo') return { type: 'Smart Speaker', vendor, icon: '🔊' };
    if (h.includes('chromecast') || vendor === 'Chromecast') return { type: 'Smart TV', vendor, icon: '📺' };
    if (h.includes('roku') || vendor === 'Roku') return { type: 'Streaming', vendor, icon: '📺' };
    if (h.includes('apple-tv') || h.includes('appletv') || vendor === 'Apple TV') return { type: 'Streaming', vendor, icon: '🍎' };
    if (h.includes('nest') || vendor === 'Nest') return { type: 'Smart Thermostat', vendor, icon: '🌡️' };
    if (h.includes('ring') || vendor === 'Ring') return { type: 'Smart Camera', vendor, icon: '🔔' };
    if (h.includes('hue') || vendor === 'Philips Hue') return { type: 'Smart Light', vendor, icon: '💡' };
    if (h.includes('sonos') || vendor === 'Sonos') return { type: 'Smart Speaker', vendor, icon: '🔊' };
    if (h.includes('ecobee') || vendor === 'Ecobee') return { type: 'Smart Thermostat', vendor, icon: '🌡️' };
    if (h.includes('august') || vendor === 'August') return { type: 'Smart Lock', vendor, icon: '🔒' };
    if (h.includes('yale') || vendor === 'Yale') return { type: 'Smart Lock', vendor, icon: '🔒' };
    if (h.includes('smartthings') || vendor === 'SmartThings') return { type: 'Smart Hub', vendor, icon: '🏠' };
    if (h.includes('hue') || vendor === 'Philips Hue') return { type: 'Smart Light', vendor, icon: '💡' };
    if (h.includes('plug') || h.includes('outlet') || vendor === 'Smart Plug') return { type: 'Smart Plug', icon: '🔌' };
    if (vendor === 'Amazon' && (h.includes('fire') || h.includes('stick'))) return { type: 'Streaming', vendor, icon: '📺' };
    
    // Phone detection
    if (vendor === 'Apple' && (h.includes('iphone') || h.includes('ipad') || h.includes('ios'))) return { type: 'Mobile', vendor, icon: '📱' };
    if (vendor === 'Samsung' && (h.includes('galaxy') || h.includes('samsung'))) return { type: 'Mobile', vendor, icon: '📱' };
    if (vendor === 'Google' && (h.includes('pixel') || h.includes('android'))) return { type: 'Mobile', vendor, icon: '📱' };
    if (vendor === 'Apple' || vendor === 'Samsung' || vendor === 'Google') return { type: 'Mobile', vendor, icon: '📱' };
    
    // Computer detection
    if (vendor === 'Apple' && (h.includes('mac') || h.includes('imac') || h.includes('macbook'))) return { type: 'Computer', vendor, icon: '💻' };
    if (vendor === 'Dell' || vendor === 'HP' || vendor === 'Lenovo' || vendor === 'ASUS' || vendor === 'Acer') return { type: 'Computer', vendor, icon: '🖥️' };
    if (vendor === 'Microsoft' && h.includes('surface')) return { type: 'Computer', vendor, icon: '💻' };
    if (h.includes('desktop') || h.includes('pc') || h.includes('workstation')) return { type: 'Computer', vendor, icon: '🖥️' };
    if (h.includes('macbook') || h.includes('laptop') || h.includes('notebook')) return { type: 'Laptop', vendor, icon: '💻' };
    if (vendor === 'Intel' && h.includes('nuc')) return { type: 'Computer', vendor, icon: '🖥️' };
    if (vendor === 'Raspberry Pi') return { type: 'Single Board Computer', vendor, icon: '🔸' };
    if (vendor === 'NVIDIA') return { type: 'Gaming PC', vendor, icon: '🎮' };
    
    // Gaming
    if (vendor === 'Sony' || vendor === 'PlayStation') return { type: 'Gaming Console', vendor, icon: '🎮' };
    if (vendor === 'Microsoft' && (h.includes('xbox') || h.includes('game'))) return { type: 'Gaming Console', vendor, icon: '🎮' };
    if (vendor === 'Nintendo') return { type: 'Gaming Console', vendor, icon: '🎮' };
    
    // Smart TV
    if (vendor.includes('TV') || h.includes('tv') || h.includes('living room') || h.includes('bedroom')) return { type: 'Smart TV', vendor, icon: '📺' };
    if (vendor === 'Samsung TV' || vendor === 'LG TV' || vendor === 'Sony TV' || vendor === 'Vizio TV') return { type: 'Smart TV', vendor, icon: '📺' };
    
    // Network设备
    if (vendor === 'Cisco' || vendor === 'NETGEAR' || vendor === 'TP-Link' || vendor === 'Ubiquiti') return { type: 'Network Device', vendor, icon: '📡' };
    if (h.includes('router') || h.includes('gateway') || h.includes('modem')) return { type: 'Router', vendor, icon: '📡' };
    if (h.includes('access') || h.includes('ap-')) return { type: 'Access Point', vendor, icon: '📶' };
    
    // Printer
    if (h.includes('printer') || h.includes('print') || vendor === 'HP' || vendor === 'Canon' || vendor === 'Epson') return { type: 'Printer', vendor, icon: '🖨️' };
    
    // Default based on vendor
    if (vendor !== 'Unknown') {
        return { type: 'IoT Device', vendor, icon: '📟' };
    }
    
    return { type: 'Unknown', vendor: 'Unknown', icon: '❓' };
}

// Devices
function isPrivateIP(ip) {
    const parts = ip.split('.').map(Number);
    if (parts.length !== 4 || parts.some(p => isNaN(p) || p < 0 || p > 255)) return true;
    if (parts[0] === 10) return true;
    if (parts[0] === 172 && parts[1] >= 16 && parts[1] <= 31) return true;
    if (parts[0] === 192 && parts[1] === 168) return true;
    if (parts[0] === 127) return true;
    return false;
}

async function fetchGeoIP(ip) {
    try {
        const r = await fetch(`http://ip-api.com/json/${ip}?fields=status,country,countryCode,city`, { signal: AbortSignal.timeout(5000) });
        const j = await r.json();
        if (j.status === 'success') return { country: j.country, countryCode: j.countryCode, city: j.city };
    } catch (_) {}
    return null;
}

let dCache = [], dCacheT = 0;
app.get('/api/devices', async (req, res) => {
    try {
        const enrichGeo = req.query.enrich === 'geo';
        const now = Date.now();
        let devs;
        if (now - dCacheT < 30000 && dCache.length > 0) {
            devs = [...dCache];
        } else {
            let raw = [];
            try {
                const subnet = await getScanSubnet();
                const o = await run(`sudo nmap -sn ${subnet} -oG - 2>/dev/null`);
                for (const l of o.split('\n')) {
                    const m = l.match(/Host:\s+(\d+\.\d+\.\d+\.\d+)\s+\(([^)]*)\)/);
                    if (m) raw.push({ ip: m[1], hostname: m[2] || 'Unknown', mac: '', status: 'Up' });
                }
            } catch (e) {
                const o = await run('ip neighbor show 2>/dev/null||arp -a');
                for (const l of o.split('\n')) {
                    const m = l.match(/^(\d+\.\d+\.\d+\.\d+)\s+dev\s+\S+\s+lladdr\s+(\S+)\s+(\S+)/);
                    if (m) raw.push({ ip: m[1], hostname: 'Unknown', mac: m[2], status: m[3] });
                }
            }
            try {
                const a = await run('arp -a 2>/dev/null');
                const mm = {};
                for (const l of a.split('\n')) {
                    const m = l.match(/\((\d+\.\d+\.\d+\.\d+)\)\s+at\s+([0-9a-f:]+)/i);
                    if (m) mm[m[1]] = m[2];
                }
                for (const d of raw) if (!d.mac && mm[d.ip]) d.mac = mm[d.ip];
            } catch (e) {}
            raw.sort((a, b) => { const ap = a.ip.split('.').map(Number), bp = b.ip.split('.').map(Number); for (let i = 0; i < 4; i++) if (ap[i] !== bp[i]) return ap[i] - bp[i]; return 0; });
            const seen = new Set();
            raw = raw.filter(d => { if (seen.has(d.ip)) return false; seen.add(d.ip); return true; });
            devs = raw.map(d => {
                const info = getDeviceInfo(d.mac, d.hostname);
                return { ...d, type: info.type, vendor: info.vendor, icon: info.icon };
            });
            dCache = devs;
            dCacheT = now;
        }
        if (enrichGeo) {
            const toEnrich = devs.filter(d => !isPrivateIP(d.ip)).slice(0, 30);
            for (let i = 0; i < toEnrich.length; i++) {
                const geo = await fetchGeoIP(toEnrich[i].ip);
                if (geo) Object.assign(toEnrich[i], geo);
                if (i < toEnrich.length - 1) await new Promise(r => setTimeout(r, 1500));
            }
        }
        res.json(devs);
    } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/devices/scan', requireAuth, (_, res) => { dCacheT = 0; res.json({ success: true }); });

// WiFi
app.get('/api/wifi', async (req, res) => {
    try {
        const wiface = await getWirelessIface();
        const [iw, nm] = await Promise.all([
            run(wiface ? `iwconfig ${wiface} 2>/dev/null||echo ""` : 'echo ""'),
            run('nmcli -t -f SSID,SIGNAL,SECURITY,FREQ,CHAN device wifi list 2>/dev/null||echo ""')
        ]);
        const connected = { 
            ssid: iw.match(/ESSID:"([^"]+)"/)?.[1] || 'N/A', 
            frequency: iw.match(/Frequency:([\d.]+\s*GHz)/)?.[1] || '', 
            bitrate: iw.match(/Bit Rate=([\d.]+\s*\w+)/)?.[1] || '', 
            linkQuality: iw.match(/Link Quality=(\d+\/\d+)/)?.[1] || '', 
            signalLevel: iw.match(/Signal level=(-?\d+\s*dBm)/)?.[1] || '', 
            mode: iw.match(/Mode:(\S+)/)?.[1] || '' 
        };
        const nearby = []; 
        for (const l of nm.split('\n').filter(l => l.trim())) { 
            const p = l.split(':'); 
            if (p.length >= 4) nearby.push({ ssid: p[0], signal: p[1] + '%', security: p[2], freq: p[3], channel: p[4] || '' }); 
        }
        res.json({ connected, nearby: nearby.slice(0, 25) });
    } catch (e) { res.status(500).json({ error: e.message }) }
});

app.post('/api/wifi/connect', requireAuth, async (req, res) => {
    const { ssid, password } = req.body; 
    if (!ssid) return res.status(400).json({ error: 'No SSID' });
    try { 
        const o = await run(`nmcli device wifi connect "${ssid}" password "${password || ''}" 2>&1`); 
        res.json({ success: true, output: o }); 
    } catch (e) { res.json({ success: false, output: e.message }) }
});

app.post('/api/wifi/disconnect', requireAuth, async (_, res) => { 
    try {
        const wiface = await getWirelessIface();
        if (!wiface) return res.json({ success: false, error: 'No wireless interface' });
        await run(`nmcli device disconnect ${wiface} 2>&1`);
        res.json({ success: true });
    } catch (e) { res.json({ success: false, error: e.message }); }
});

// DNS/DHCP
app.get('/api/dns', async (_, res) => { 
    try { 
        const r = await run('cat /etc/resolv.conf 2>/dev/null'); 
        const s = []; 
        for (const l of r.split('\n')) { 
            const m = l.match(/^nameserver\s+([\d.]+)/); 
            if (m) s.push(m[1]); 
        } 
        const sys = await run('resolvectl status 2>/dev/null|head -30||echo ""'); 
        res.json({ servers: s, systemd: sys }); 
    } catch (e) { res.status(500).json({ error: e.message }) } 
});

app.get('/api/dhcp', async (_, res) => { 
    try { 
        const iface = await getPrimaryIface();
        const o = await run(iface ? `nmcli device show ${iface} 2>/dev/null|grep -E "IP4\\.(ADDRESS|GATEWAY|DNS|DOMAIN)"|head -10||echo ""` : 'echo ""');
        res.json({ info: o }); 
    } catch (e) { res.status(500).json({ error: e.message }) } 
});

// Ports
const KP = { 22: 'SSH', 25: 'SMTP', 53: 'DNS', 80: 'HTTP', 443: 'HTTPS', 139: 'NetBIOS', 445: 'SMB', 631: 'CUPS', 3000: 'Net Admin', 5432: 'PostgreSQL', 8080: 'HTTP-Alt', 25565: 'Minecraft', 24454: 'VoiceChat' };
app.get('/api/ports', async (_, res) => { 
    try { 
        const o = await run('sudo ss -tlnp 2>/dev/null||ss -tlnp'); 
        const ports = []; 
        for (const l of o.split('\n').slice(1)) { 
            const p = l.trim().split(/\s+/); 
            if (p.length < 5) continue; 
            const lo = p[3], lc = lo.lastIndexOf(':'), port = parseInt(lo.substring(lc + 1)); 
            const pm = l.match(/users:\(\("([^"]+)",pid=(\d+)/); 
            ports.push({ address: lo.substring(0, lc), port, process: pm?.[1] || 'system', pid: pm?.[2] || '', service: KP[port] || '' }); 
        } 
        ports.sort((a, b) => a.port - b.port); 
        res.json(ports); 
    } catch (e) { res.status(500).json({ error: e.message }) } 
});

// Connections
app.get('/api/connections', async (_, res) => { 
    try { 
        const o = await run('sudo ss -tnp 2>/dev/null||ss -tnp'); 
        const c = []; 
        for (const l of o.split('\n').slice(1)) { 
            const p = l.trim().split(/\s+/); 
            if (p.length < 5) continue; 
            const pm = l.match(/users:\(\("([^"]+)",pid=(\d+)/); 
            c.push({ state: p[0], local: p[3], remote: p[4], process: pm?.[1] || 'system' }); 
        } 
        res.json(c); 
    } catch (e) { res.status(500).json({ error: e.message }) } 
});

// Firewall (local) — iptables or UFW fallback
app.get('/api/firewall', async (_, res) => { 
    try { 
        let o = await run('sudo iptables -L INPUT -n --line-numbers 2>/dev/null||echo ""'); 
        const r = []; 
        for (const l of o.split('\n').slice(2)) { 
            const p = l.trim().split(/\s+/); 
            if (p.length >= 5) r.push({ num: p[0], target: p[1], protocol: p[2], source: p[4], destination: p[5] || '*', extra: p.slice(6).join(' ') }); 
        } 
        if (r.length === 0) {
            const ufw = await run('sudo ufw status numbered 2>/dev/null||echo ""');
            for (const l of ufw.split('\n')) {
                const m = l.match(/^\[\s*(\d+)\]\s+(\S+)\s+(\S+)\s+(.*)/);
                if (m) r.push({ num: m[1], target: m[2], protocol: m[3], source: m[4] || '*', destination: '*', extra: '' });
            }
        }
        res.json(r); 
    } catch (e) { res.status(500).json({ error: e.message }) } 
});

app.post('/api/firewall/block-ip', requireAuth, async (req, res) => {
    const { ip } = req.body;
    if (!ip) return res.status(400).json({ error: 'No IP' });
    if (!validateIP(ip)) return res.status(400).json({ error: 'Invalid IP address' });
    try { await run(`sudo iptables -I INPUT -s ${ip} -j DROP`); res.json({ success: true }); }
    catch (e) { res.status(500).json({ error: e.message }) }
});

app.post('/api/firewall/unblock-ip', requireAuth, async (req, res) => {
    const { ip } = req.body;
    if (!ip) return res.status(400).json({ error: 'No IP' });
    if (!validateIP(ip)) return res.status(400).json({ error: 'Invalid IP address' });
    try { await run(`sudo iptables -D INPUT -s ${ip} -j DROP`); res.json({ success: true }); }
    catch (e) { res.status(500).json({ error: e.message }) }
});

app.post('/api/firewall/open-port', requireAuth, async (req, res) => {
    const { port, protocol = 'tcp' } = req.body;
    if (!validatePort(port)) return res.status(400).json({ error: 'Invalid port' });
    if (!validateProtocol(protocol)) return res.status(400).json({ error: 'Invalid protocol' });
    try { await run(`sudo iptables -I INPUT -p ${protocol} --dport ${parseInt(port,10)} -j ACCEPT`); res.json({ success: true }); }
    catch (e) { res.status(500).json({ error: e.message }) }
});

app.post('/api/firewall/close-port', requireAuth, async (req, res) => {
    const { port, protocol = 'tcp' } = req.body;
    if (!validatePort(port)) return res.status(400).json({ error: 'Invalid port' });
    if (!validateProtocol(protocol)) return res.status(400).json({ error: 'Invalid protocol' });
    try { await run(`sudo iptables -I INPUT -p ${protocol} --dport ${parseInt(port,10)} -j DROP`); res.json({ success: true }); }
    catch (e) { res.status(500).json({ error: e.message }) }
});

app.post('/api/firewall/delete-rule', requireAuth, async (req, res) => {
    const { ruleNum } = req.body;
    if (!validateRuleNum(ruleNum)) return res.status(400).json({ error: 'Invalid rule number' });
    try { await run(`sudo iptables -D INPUT ${parseInt(ruleNum,10)}`); res.json({ success: true }); }
    catch (e) { res.status(500).json({ error: e.message }) }
});

// Port Forwarding (local)
app.get('/api/portforward', async (_, res) => {
    try {
        const o = await run('sudo iptables -t nat -L PREROUTING -n -v --line-numbers 2>/dev/null||echo ""');
        const rules = [];
        for (const l of o.split('\n').slice(2)) {
            const m = l.match(/^\s*(\d+).*DNAT\s+(tcp|udp).*dpt:(\d+)\s+to:([\d.]+):(\d+)/);
            if (m) rules.push({ num: m[1], protocol: m[2], extPort: m[3], intIp: m[4], intPort: m[5] });
        }
        res.json(rules);
    } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post('/api/portforward', requireAuth, async (req, res) => {
    const { extPort, intIp, intPort, protocol = 'tcp' } = req.body;
    const port = parseInt(extPort, 10);
    const intP = parseInt(intPort, 10);
    if (!port || port < 1 || port > 65535 || !intP || intP < 1 || intP > 65535) return res.status(400).json({ error: 'Invalid ports' });
    if (!/^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(intIp)) return res.status(400).json({ error: 'Invalid internal IP' });
    const prot = protocol === 'udp' ? 'udp' : 'tcp';
    try {
        await run(`sudo iptables -t nat -A PREROUTING -p ${prot} --dport ${port} -j DNAT --to-destination ${intIp}:${intP}`);
        await run(`sudo iptables -A FORWARD -p ${prot} -d ${intIp} --dport ${intP} -j ACCEPT 2>/dev/null||true`);
        res.json({ success: true });
    } catch (e) { res.status(500).json({ error: e.message }); }
});

app.delete('/api/portforward/:num', requireAuth, async (req, res) => {
    const num = req.params.num.replace(/\D/g, '');
    if (!num) return res.status(400).json({ error: 'Invalid rule number' });
    try {
        await run(`sudo iptables -t nat -D PREROUTING ${num}`);
        res.json({ success: true });
    } catch (e) { res.status(500).json({ error: e.message }); }
});

// Router dashboard — ports, connections, portforward, firewall, gateway, dns, arp
app.get('/api/router/dashboard', async (_, res) => {
    try {
        const [tcpP, udpP, tcpC, udpC, pfRaw, fwRaw, gw, dnsRaw, arpRaw] = await Promise.all([
            run('sudo ss -tlnp 2>/dev/null||ss -tlnp'),
            run('sudo ss -ulnp 2>/dev/null||ss -ulnp'),
            run('sudo ss -tnp 2>/dev/null||ss -tnp'),
            run('sudo ss -unp 2>/dev/null||ss -unp'),
            run('sudo iptables -t nat -L PREROUTING -n -v --line-numbers 2>/dev/null||echo ""'),
            run('sudo iptables -L INPUT -n --line-numbers 2>/dev/null||echo ""'),
            run('ip route | grep default | head -1'),
            run('cat /etc/resolv.conf 2>/dev/null | grep nameserver | awk \'{print $2}\' | head -4'),
            run('ip neigh show 2>/dev/null | grep -v FAILED')
        ]);
        const ports = [], conns = [];
        const parsePorts = (o, proto) => {
            for (const l of (o || '').split('\n').slice(1)) {
                const p = l.trim().split(/\s+/);
                if (p.length < 5) continue;
                const lo = p[3], lc = lo.lastIndexOf(':'), port = parseInt(lo.substring(lc + 1));
                if (isNaN(port) || port < 1) continue;
                const pm = l.match(/users:\(\("([^"]+)",pid=(\d+)/);
                ports.push({ address: lo.substring(0, lc), port, proto, process: pm?.[1] || 'system', service: KP[port] || '' });
            }
        };
        const parseConns = (o, proto) => {
            for (const l of (o || '').split('\n').slice(1)) {
                const p = l.trim().split(/\s+/);
                if (p.length < 5) continue;
                const pm = l.match(/users:\(\("([^"]+)",pid=(\d+)/);
                conns.push({ state: p[0], local: p[3], remote: p[4], process: pm?.[1] || 'system', proto });
            }
        };
        parsePorts(tcpP, 'tcp'); parsePorts(udpP, 'udp');
        parseConns(tcpC, 'tcp'); parseConns(udpC, 'udp');
        ports.sort((a, b) => a.port - b.port);
        const pf = [];
        for (const l of (pfRaw || '').split('\n').slice(2)) {
            const m = l.match(/^\s*(\d+).*DNAT\s+(tcp|udp).*dpt:(\d+)\s+to:([\d.]+):(\d+)/);
            if (m) pf.push({ num: m[1], protocol: m[2], extPort: m[3], intIp: m[4], intPort: m[5] });
        }
        const fw = [];
        for (const l of (fwRaw || '').split('\n').slice(2)) {
            const p = l.trim().split(/\s+/);
            if (p.length >= 5) fw.push({ num: p[0], target: p[1], protocol: p[2], source: p[4], destination: p[5] || '*' });
        }
        if (fw.length === 0) {
            const ufw = await run('sudo ufw status numbered 2>/dev/null||echo ""');
            for (const l of ufw.split('\n')) {
                const m = l.match(/^\[\s*(\d+)\]\s+(\S+)\s+(\S+)\s+(.*)/);
                if (m) fw.push({ num: m[1], target: m[2], protocol: m[3], source: m[4] || '*', destination: '*' });
            }
        }
        const dns = (dnsRaw || '').trim().split('\n').filter(Boolean);
        const arp = (arpRaw || '').split('\n').filter(Boolean).map(l => {
            const p = l.split(/\s+/);
            return { ip: p[0], mac: p[4] || '', state: p[5] || '' };
        });
        const gateway = (gw || '').trim().split(/\s+/)[2] || 'N/A';
        res.json({ ports, connections: conns, portForward: pf, firewall: fw, gateway, dns, arp });
    } catch (e) { res.status(500).json({ error: e.message }); }
});

// Bandwidth
app.get('/api/bandwidth', (_, res) => { 
    try { 
        const now = Date.now(), curr = readDev(), el = (now - prevBwT) / 1000, r = {}; 
        for (const [n, s] of Object.entries(curr)) { 
            const p = prevBw[n]; 
            let rxR = 0, txR = 0; 
            if (p && el > 0 && el < 60) { rxR = Math.max(0, (s.rx - p.rx) / el); txR = Math.max(0, (s.tx - p.tx) / el); } 
            r[n] = { rxTotal: fmt(s.rx), txTotal: fmt(s.tx), rxRate: fmtR(rxR), txRate: fmtR(txR), rxRaw: rxR, txRaw: txR }; 
        } 
        prevBw = curr; prevBwT = now; res.json(r); 
    } catch (e) { res.status(500).json({ error: e.message }) } 
});

// Processes
app.get('/api/processes', async (_, res) => { 
    try { 
        const o = await run('ps aux --sort=-%cpu|head -30'); 
        const p = []; 
        for (const l of o.split('\n').slice(1)) { 
            const x = l.trim().split(/\s+/); 
            if (x.length < 11) continue; 
            p.push({ user: x[0], pid: x[1], cpu: x[2], mem: x[3], rss: x[5], command: x.slice(10).join(' ').substring(0, 100) }); 
        } 
        res.json(p); 
    } catch (e) { res.status(500).json({ error: e.message }) } 
});

app.post('/api/processes/kill', requireAuth, async (req, res) => { 
    const { pid, signal = 'TERM' } = req.body; 
    if (!pid) return res.status(400).json({ error: 'No PID' }); 
    try { await run(`kill -${signal} ${pid}`); res.json({ success: true }); } 
    catch (e) { res.status(500).json({ error: e.message }) } 
});

// Temperatures
app.get('/api/temperatures', async (_, res) => { 
    try { 
        const o = await run('sensors 2>/dev/null||echo ""'); 
        const t = []; 
        for (const l of o.split('\n')) { 
            const m = l.match(/^(.+?):\s+\+?([\d.]+)°C/); 
            if (m) t.push({ label: m[1].trim(), temp: parseFloat(m[2]) }); 
        } 
        try { 
            const g = await run('nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader 2>/dev/null'); 
            if (g) t.push({ label: 'GPU', temp: parseFloat(g) }); 
        } catch (e) { } 
        res.json(t); 
    } catch (e) { res.status(500).json({ error: e.message }) } 
});

// Disk
app.get('/api/disk', async (_, res) => { 
    try { 
        const o = await run('df -h --output=source,fstype,size,used,avail,pcent,target 2>/dev/null|grep -v tmpfs|grep -v udev'); 
        const d = []; 
        for (const l of o.split('\n').slice(1)) { 
            const p = l.trim().split(/\s+/); 
            if (p.length >= 7) d.push({ device: p[0], fstype: p[1], size: p[2], used: p[3], avail: p[4], pct: p[5], mount: p[6] }); 
        } 
        res.json(d); 
    } catch (e) { res.status(500).json({ error: e.message }) } 
});

// USB
app.get('/api/usb', async (_, res) => { 
    try { 
        const o = await run('lsusb 2>/dev/null||echo ""'); 
        const d = []; 
        for (const l of o.split('\n').filter(l => l.trim())) { 
            const m = l.match(/Bus\s+(\d+)\s+Device\s+(\d+):\s+ID\s+(\S+)\s+(.*)/); 
            if (m) d.push({ bus: m[1], device: m[2], id: m[3], name: m[4] }); 
        } 
        res.json(d); 
    } catch (e) { res.status(500).json({ error: e.message }) } 
});

// Services
app.get('/api/services', async (_, res) => { 
    try { 
        const o = await run('systemctl list-units --type=service --no-pager --no-legend 2>/dev/null|head -50'); 
        const s = []; 
        for (const l of o.split('\n').filter(l => l.trim())) { 
            const p = l.trim().split(/\s+/); 
            if (p.length >= 5) s.push({ name: p[0], load: p[1], active: p[2], sub: p[3], description: p.slice(4).join(' ') }); 
        } 
        res.json(s); 
    } catch (e) { res.status(500).json({ error: e.message }) } 
});

app.post('/api/services/action', requireAuth, async (req, res) => { 
    const { name, action } = req.body; 
    if (!name || !['start', 'stop', 'restart', 'enable', 'disable'].includes(action)) return res.status(400).json({ error: 'Invalid' }); 
    try { 
        const o = await run(`sudo systemctl ${action} ${name} 2>&1`); 
        res.json({ success: true, output: o }); 
    } catch (e) { res.json({ success: false, output: e.message }) } 
});

// Docker
app.get('/api/docker', async (_, res) => { 
    try { 
        const c = await run('docker ps -a --format "{{.ID}}|{{.Image}}|{{.Status}}|{{.Ports}}|{{.Names}}" 2>/dev/null||echo ""'); 
        const containers = []; 
        for (const l of c.split('\n').filter(l => l.trim())) { 
            const p = l.split('|'); 
            if (p.length >= 5) containers.push({ id: p[0], image: p[1], status: p[2], ports: p[3], name: p[4] }); 
        } 
        const i = await run('docker images --format "{{.Repository}}:{{.Tag}}|{{.Size}}|{{.CreatedSince}}" 2>/dev/null||echo ""'); 
        const images = []; 
        for (const l of i.split('\n').filter(l => l.trim())) { 
            const p = l.split('|'); 
            if (p.length >= 2) images.push({ name: p[0], size: p[1], created: p[2] || '' }); 
        } 
        res.json({ containers, images }); 
    } catch (e) { res.status(500).json({ error: e.message }) } 
});

app.post('/api/docker/action', requireAuth, async (req, res) => { 
    const { name, action } = req.body; 
    if (!name || !['start', 'stop', 'restart', 'pause', 'unpause', 'rm'].includes(action)) return res.status(400).json({ error: 'Invalid' }); 
    try { 
        const o = await run(`docker ${action} ${name} 2>&1`); 
        res.json({ success: true, output: o }); 
    } catch (e) { res.json({ success: false, output: e.message }) } 
});

app.get('/api/docker/logs/:name', async (req, res) => { 
    try { 
        const o = await run(`docker logs --tail 50 ${req.params.name} 2>&1`); 
        res.json({ logs: o }); 
    } catch (e) { res.status(500).json({ error: e.message }) } 
});

// Tailscale
app.get('/api/tailscale', async (_, res) => { 
    try { 
        const [st, ip] = await Promise.all([
            run('tailscale status 2>/dev/null||echo ""'), 
            run('tailscale ip 2>/dev/null||echo ""')
        ]); 
        const peers = []; 
        for (const l of st.split('\n').filter(l => l.trim())) { 
            const p = l.trim().split(/\s+/); 
            if (p.length >= 4 && /^\d/.test(p[0])) peers.push({ ip: p[0], hostname: p[1], os: p[2], status: p.slice(3).join(' ') }); 
        } 
        res.json({ ips: ip.split('\n'), peers }); 
    } catch (e) { res.status(500).json({ error: e.message }) } 
});

// ═══════════ OPERATIONAL SECURITY (Track 5) ═══════════
app.get('/api/security/vpn-status', async (_, res) => {
    try {
        const [interfacesOut, wgServices, wgShow, tailscaleOut] = await Promise.all([
            run('ip a 2>/dev/null | grep -E "wg|tun|tap" || echo ""'),
            run('systemctl list-units --type=service --state=active 2>/dev/null | grep -E "wg-quick|wireguard" || echo ""'),
            run('wg show 2>/dev/null || echo ""'),
            run('tailscale status 2>/dev/null || echo ""')
        ]);
        const interfaces = interfacesOut.split('\n').filter(l => l.trim()).map(l => l.trim());
        const wireguard = wgServices.trim().length > 0 || wgShow.trim().length > 0;
        const openvpn = interfaces.some(i => /tun|tap/.test(i));
        const tailscale = tailscaleOut.includes('Connected') || tailscaleOut.includes('logged in');
        res.json({ wireguard, openvpn, tailscale, interfaces });
    } catch (e) {
        res.status(500).json({ error: e.message, wireguard: false, openvpn: false, tailscale: false, interfaces: [] });
    }
});

app.get('/api/security/tor-status', async (_, res) => {
    try {
        const out = await run('curl -s --connect-timeout 5 --max-time 10 --socks5-hostname 127.0.0.1:9050 https://check.torproject.org/api/ip 2>/dev/null || echo ""');
        const ok = out.includes('"IsTor":true') || (out.includes('IsTor') && out.includes('true'));
        let ip = null;
        try {
            const j = JSON.parse(out);
            if (j.IP) ip = j.IP;
        } catch (_) {}
        res.json({ connected: ok, exitIp: ip });
    } catch (e) {
        res.json({ connected: false, exitIp: null });
    }
});

// Minecraft
app.get('/api/minecraft', async (_, res) => {
    try {
        const jp = await run('ps aux|grep "fabric-server"|grep -v grep||echo ""'); 
        const running = jp.includes('fabric-server'); 
        let players = [], port = 25565, version = '', motd = '', mem = '', up = '';
        try { 
            const pr = fs.readFileSync(path.join(MC_DIR, 'server.properties'), 'utf8'); 
            port = parseInt(pr.match(/server-port=(\d+)/)?.[1] || '25565'); 
            motd = pr.match(/motd=(.*)/)?.[1] || ''; 
        } catch (e) { }
        if (running) {
            try { 
                const pid = jp.match(/\S+\s+(\d+)/)?.[1]; 
                if (pid) { 
                    const mi = await run(`ps -p ${pid} -o rss=,etime=`); 
                    const pp = mi.trim().split(/\s+/); 
                    mem = (parseInt(pp[0]) / 1024).toFixed(0) + ' MB'; 
                    up = pp[1] || ''; 
                } 
            } catch (e) { }
            try { 
                const log = fs.readFileSync(path.join(MC_DIR, 'logs', 'latest.log'), 'utf8'); 
                const jm = {}; 
                for (const l of log.split('\n')) { 
                    const j = l.match(/(\w+) joined the game/); 
                    const lv = l.match(/(\w+) left the game/); 
                    if (j) jm[j[1]] = true; 
                    if (lv) delete jm[lv[1]]; 
                } 
                players = Object.keys(jm); 
                version = log.match(/Starting minecraft server version ([\d.]+)/)?.[1] || ''; 
                const pk = log.match(/Loaded (\d+) Pokémon species/)?.[1]; 
                if (pk) version += ` | ${pk} Pokémon`; 
            } catch (e) { }
        }
        res.json({ running, port, players, playerCount: players.length, version, motd, mem, uptime: up });
    } catch (e) { res.status(500).json({ error: e.message }) }
});

// Logs
app.get('/api/logs', async (req, res) => {
    const type = req.query.type || 'syslog', n = parseInt(req.query.lines) || 50;
    const files = { syslog: '/var/log/syslog', auth: '/var/log/auth.log', kernel: '/var/log/kern.log', minecraft: path.join(MC_DIR, 'logs', 'latest.log') };
    try { 
        let o; 
        if (type === 'journal') o = await run(`journalctl -n ${n} --no-pager 2>/dev/null`); 
        else { 
            const f = files[type]; 
            if (!f) return res.status(400).json({ error: 'Invalid type' }); 
            o = await run(`sudo tail -n ${n} "${f}" 2>/dev/null||tail -n ${n} "${f}" 2>/dev/null||echo "Cannot read"`); 
        } 
        res.json({ lines: o.split('\n') }); 
    } catch (e) { res.status(500).json({ error: e.message }) }
});

// Tools
app.post('/api/tools/ping', async (req, res) => { 
    const { host } = req.body; 
    try { res.json({ output: await run(`ping -c 4 -W 3 "${host}" 2>&1`) }); } 
    catch (e) { res.json({ output: e.message }) } 
});

app.post('/api/tools/traceroute', async (req, res) => { 
    const { host } = req.body; 
    try { res.json({ output: await run(`traceroute -m 15 -w 2 "${host}" 2>&1`) }); } 
    catch (e) { res.json({ output: e.message }) } 
});

app.post('/api/tools/dns', async (req, res) => { 
    const { host } = req.body; 
    try { res.json({ output: await run(`dig "${host}" +noall +answer 2>&1||nslookup "${host}" 2>&1`) }); } 
    catch (e) { res.json({ output: e.message }) } 
});

app.post('/api/tools/whois', async (req, res) => { 
    const { host } = req.body; 
    try { res.json({ output: await run(`whois "${host}" 2>&1|head -60`) }); } 
    catch (e) { res.json({ output: e.message }) } 
});

app.post('/api/tools/portcheck', async (req, res) => { 
    const { host, port } = req.body; 
    try { 
        const o = await run(`timeout 5 bash -c 'echo ""|nc -v -w3 "${host}" ${port}' 2>&1`); 
        res.json({ output: o, open: o.toLowerCase().includes('succeeded') || o.toLowerCase().includes('open') }); 
    } catch (e) { res.json({ output: e.message, open: false }) } 
});

app.post('/api/tools/wol', async (req, res) => { 
    const { mac } = req.body; 
    try { res.json({ output: await run(`wakeonlan "${mac}" 2>&1||etherwake "${mac}" 2>&1||echo "Not installed"`) }); } 
    catch (e) { res.json({ output: e.message }) } 
});

app.post('/api/tools/nmap', async (req, res) => { 
    const { host } = req.body; 
    try { res.json({ output: await run(`sudo nmap -sV --top-ports 20 "${host}" 2>&1`) }); } 
    catch (e) { res.json({ output: e.message }) } 
});

app.post('/api/tools/curl', async (req, res) => { 
    const { url } = req.body; 
    try { res.json({ output: await run(`curl -sIL --max-time 10 "${url}" 2>&1|head -40`) }); } 
    catch (e) { res.json({ output: e.message }) } 
});

app.post('/api/tools/iplookup', async (req, res) => { 
    const { ip } = req.body; 
    try { res.json({ output: await run(`curl -s "http://ip-api.com/json/${ip}" 2>/dev/null`) }); } 
    catch (e) { res.json({ output: e.message }) } 
});

app.post('/api/speedtest', async (_, res) => { 
    try { 
        const o = await run('curl -o /dev/null -s -w "%{speed_download}" http://speedtest.tele2.net/1MB.zip'); 
        const bps = parseFloat(o); 
        res.json({ mbps: (bps * 8 / 1048576).toFixed(1), raw: fmtR(bps) }); 
    } catch (e) { res.status(500).json({ error: e.message }) } 
});

// Latency
app.get('/api/latency', async (_, res) => { 
    try { 
        const gw = await getDefaultGateway();
        const targets = [
            { name: 'Google DNS', host: '8.8.8.8' }, 
            { name: 'Cloudflare', host: '1.1.1.1' }, 
            { name: 'Router', host: gw }, 
            { name: 'Google', host: 'google.com' }, 
            { name: 'Minecraft Auth', host: 'sessionserver.mojang.com' }
        ]; 
        const r = await Promise.all(targets.map(async t => { 
            try { 
                const o = await run(`ping -c 1 -W 2 ${t.host} 2>/dev/null|grep "time="`); 
                return { ...t, ping: (o.match(/time=([\d.]+)/)?.[1] || 'timeout') + ' ms' }; 
            } catch (e) { return { ...t, ping: 'timeout' }; } 
        })); 
        res.json(r); 
    } catch (e) { res.status(500).json({ error: e.message }) } 
});

// File browser
const FILE_BASE = path.resolve('/home/jack');
function resolveSafe(dirOrFile) {
    const resolved = path.resolve(dirOrFile);
    return resolved.startsWith(FILE_BASE) ? resolved : null;
}

app.get('/api/files', async (req, res) => { 
    const dir = resolveSafe(req.query.path || '/home/jack'); 
    if (!dir) return res.status(400).json({ error: 'Path not allowed' }); 
    try { 
        const entries = fs.readdirSync(dir, { withFileTypes: true }); 
        const files = []; 
        for (const e of entries.slice(0, 100)) { 
            try { 
                const st = fs.statSync(path.join(dir, e.name)); 
                files.push({ name: e.name, isDir: e.isDirectory(), size: e.isDirectory() ? '' : fmt(st.size), modified: st.mtime.toISOString().split('T')[0], permissions: st.mode.toString(8).slice(-3) }); 
            } catch (err) { files.push({ name: e.name, isDir: e.isDirectory(), size: '', modified: '', permissions: '' }); } 
        } 
        files.sort((a, b) => { if (a.isDir && !b.isDir) return -1; if (!a.isDir && b.isDir) return 1; return a.name.localeCompare(b.name) }); 
        res.json({ path: dir, files }); 
    } catch (e) { res.status(500).json({ error: e.message }) } 
});

app.get('/api/files/read', async (req, res) => { 
    const file = resolveSafe(req.query.path); 
    if (!file) return res.status(400).json({ error: 'Path not allowed' }); 
    try { 
        const content = fs.readFileSync(file, 'utf8').substring(0, 50000); 
        res.json({ content, path: file }); 
    } catch (e) { res.status(500).json({ error: e.message }) } 
});

// System info
app.get('/api/system', async (_, res) => {
    try {
        const [pci, gpu, modules, users, cron, hostname] = await Promise.all([
            run('lspci 2>/dev/null|head -20||echo ""'), 
            run('lspci|grep -i vga 2>/dev/null||echo "No dedicated GPU"'),
            run('lsmod|head -20 2>/dev/null||echo ""'), 
            run('who 2>/dev/null||echo ""'),
            run('crontab -l 2>/dev/null||echo "No cron jobs"'), 
            run('hostnamectl 2>/dev/null||echo ""')
        ]);
        res.json({ pci, gpu, modules, users, cron, hostinfo: hostname });
    } catch (e) { res.status(500).json({ error: e.message }) }
});

// Cron
app.post('/api/cron/add', requireAuth, async (req, res) => { 
    const { schedule, command } = req.body; 
    if (!schedule || !command) return res.status(400).json({ error: 'Need schedule and command' }); 
    try { await run(`(crontab -l 2>/dev/null; echo "${schedule} ${command}") | crontab -`); res.json({ success: true }); } 
    catch (e) { res.status(500).json({ error: e.message }) } 
});

// Users
app.get('/api/users', async (_, res) => { 
    try { 
        const o = await run('awk -F: \'$3>=1000{print $1":"$3":"$6":"$7}\' /etc/passwd'); 
        const u = []; 
        for (const l of o.split('\n').filter(l => l.trim())) { 
            const p = l.split(':'); 
            u.push({ name: p[0], uid: p[1], home: p[2], shell: p[3] }); 
        } 
        const logged = await run('who 2>/dev/null||echo ""'); 
        res.json({ users: u, logged }); 
    } catch (e) { res.status(500).json({ error: e.message }) } 
});

// Exec (sandboxed)
app.post('/api/exec', requireAuth, async (req, res) => {
    const { cmd } = req.body;
    if (!cmd || typeof cmd !== 'string') return res.status(400).json({ error: 'No command' });
    if (/[`\n\r]|\$\(/.test(cmd)) return res.status(400).json({ error: 'Command contains disallowed characters' });
    try { const o = await run(cmd); res.json({ output: o }); } catch (e) { res.json({ output: e.message }) }
});

// Startup
app.get('/api/startup', async (_, res) => { 
    try { 
        const o = await run('systemctl list-unit-files --type=service --state=enabled --no-pager --no-legend 2>/dev/null|head -30'); 
        const s = []; 
        for (const l of o.split('\n').filter(l => l.trim())) { 
            const p = l.trim().split(/\s+/); 
            if (p.length >= 2) s.push({ name: p[0], state: p[1] }); 
        } 
        res.json(s); 
    } catch (e) { res.status(500).json({ error: e.message }) } 
});

// Interfaces
app.get('/api/interfaces', async (_, res) => { 
    try { 
        const o = await run('ip -br addr show 2>/dev/null'); 
        const ifaces = []; 
        for (const l of o.split('\n').filter(l => l.trim())) { 
            const p = l.trim().split(/\s+/); 
            ifaces.push({ name: p[0], state: p[1], addresses: p.slice(2).join(', ') }); 
        } 
        res.json(ifaces); 
    } catch (e) { res.status(500).json({ error: e.message }) } 
});

// Routes
app.get('/api/routes', async (_, res) => { 
    try { 
        const o = await run('ip route show 2>/dev/null'); 
        res.json({ routes: o.split('\n') }); 
    } catch (e) { res.status(500).json({ error: e.message }) } 
});

// ARP
app.get('/api/arp', async (_, res) => { 
    try { 
        const o = await run('ip neighbor show 2>/dev/null'); 
        const entries = []; 
        for (const l of o.split('\n').filter(l => l.trim())) { 
            const p = l.trim().split(/\s+/); 
            entries.push({ ip: p[0], dev: p[2] || '', mac: p[4] || '', state: p[p.length - 1] || '' }); 
        } 
        res.json(entries); 
    } catch (e) { res.status(500).json({ error: e.message }) } 
});

// Memory history
const memHist = [];
setInterval(() => { memHist.push(parseFloat(((1 - os.freemem() / os.totalmem()) * 100).toFixed(1))); if (memHist.length > 120) memHist.shift(); }, 2000);
app.get('/api/mem-history', (_, res) => res.json(memHist));

// Packages
app.post('/api/packages/search', async (req, res) => { 
    const { query } = req.body; 
    if (!query) return res.status(400).json({ error: 'No query' }); 
    try { 
        const o = await run(`apt-cache search "${query}" 2>/dev/null | head -30`); 
        const pkgs = []; 
        for (const l of o.split('\n').filter(l => l.trim())) { 
            const m = l.match(/^(\S+)\s+-\s+(.*)/); 
            if (m) pkgs.push({ name: m[1], desc: m[2] }); 
        } 
        res.json(pkgs); 
    } catch (e) { res.status(500).json({ error: e.message }) } 
});

app.post('/api/packages/install', requireAuth, async (req, res) => { 
    const { name } = req.body; 
    if (!name) return res.status(400).json({ error: 'No name' }); 
    try { 
        const o = await run(`sudo apt-get install -y "${name}" 2>&1 | tail -5`); 
        res.json({ success: true, output: o }); 
    } catch (e) { res.json({ success: false, output: e.message }) } 
});

app.post('/api/packages/remove', requireAuth, async (req, res) => { 
    const { name } = req.body; 
    if (!name) return res.status(400).json({ error: 'No name' }); 
    try { 
        const o = await run(`sudo apt-get remove -y "${name}" 2>&1 | tail -5`); 
        res.json({ success: true, output: o }); 
    } catch (e) { res.json({ success: false, output: e.message }) } 
});

app.get('/api/packages/upgradable', async (_, res) => { 
    try { 
        const o = await run('apt list --upgradable 2>/dev/null | tail -20'); 
        const pkgs = []; 
        for (const l of o.split('\n').filter(l => l.includes('/'))) { 
            const n = l.split('/')[0]; 
            pkgs.push(n); 
        } 
        res.json(pkgs); 
    } catch (e) { res.status(500).json({ error: e.message }) } 
});

// Power
app.post('/api/power/reboot', requireAuth, async (_, res) => { 
    try { res.json({ success: true, msg: 'Rebooting...' }); setTimeout(() => exec('sudo reboot'), 1000); } 
    catch (e) { res.status(500).json({ error: e.message }) } 
});

app.post('/api/power/shutdown', requireAuth, async (_, res) => { 
    try { res.json({ success: true, msg: 'Shutting down...' }); setTimeout(() => exec('sudo shutdown -h now'), 1000); } 
    catch (e) { res.status(500).json({ error: e.message }) } 
});

// SSH Keys
app.get('/api/ssh-keys', async (_, res) => { 
    try { 
        const o = await run('cat ~/.ssh/authorized_keys 2>/dev/null || echo ""'); 
        const keys = o.split('\n').filter(l => l.trim()).map(l => { 
            const p = l.split(' '); 
            return { type: p[0], key: p[1]?.substring(0, 20) + '...', comment: p.slice(2).join(' ') || 'No comment' }; 
        }); 
        res.json(keys); 
    } catch (e) { res.status(500).json({ error: e.message }) } 
});

app.post('/api/ssh-keys/add', requireAuth, async (req, res) => { 
    const { key } = req.body; 
    if (!key) return res.status(400).json({ error: 'No key' }); 
    try { await run(`echo "${key}" >> ~/.ssh/authorized_keys`); res.json({ success: true }); } 
    catch (e) { res.status(500).json({ error: e.message }) } 
});

// Fail2Ban
app.get('/api/fail2ban', async (_, res) => { 
    try { 
        const o = await run('sudo fail2ban-client status 2>/dev/null || echo "fail2ban not installed"'); 
        let jails = []; 
        const m = o.match(/Jail list:\s+(.*)/); 
        if (m) { 
            for (const j of m[1].split(',').map(s => s.trim()).filter(s => s)) { 
                try { 
                    const jd = await run(`sudo fail2ban-client status ${j} 2>/dev/null`); 
                    const banned = jd.match(/Currently banned:\s+(\d+)/)?.[1] || '0'; 
                    const total = jd.match(/Total banned:\s+(\d+)/)?.[1] || '0'; 
                    jails.push({ name: j, banned: parseInt(banned), totalBanned: parseInt(total) }); 
                } catch (e) { jails.push({ name: j, banned: 0, totalBanned: 0 }); } 
            } 
        } 
        res.json({ status: o, jails }); 
    } catch (e) { res.status(500).json({ error: e.message }) } 
});

// Notes
const NOTES_FILE = path.join(__dirname, 'notes.json');
app.get('/api/notes', (_, res) => { 
    try { 
        const d = fs.existsSync(NOTES_FILE) ? JSON.parse(fs.readFileSync(NOTES_FILE, 'utf8')) : []; 
        res.json(d); 
    } catch (e) { res.json([]) } 
});

app.post('/api/notes', (req, res) => { 
    try { 
        const d = fs.existsSync(NOTES_FILE) ? JSON.parse(fs.readFileSync(NOTES_FILE, 'utf8')) : []; 
        d.push({ id: Date.now(), text: req.body.text, created: new Date().toISOString() }); 
        fs.writeFileSync(NOTES_FILE, JSON.stringify(d)); 
        res.json({ success: true }); 
    } catch (e) { res.status(500).json({ error: e.message }) } 
});

app.delete('/api/notes/:id', (req, res) => { 
    try { 
        let d = fs.existsSync(NOTES_FILE) ? JSON.parse(fs.readFileSync(NOTES_FILE, 'utf8')) : []; 
        d = d.filter(n => n.id !== parseInt(req.params.id)); 
        fs.writeFileSync(NOTES_FILE, JSON.stringify(d)); 
        res.json({ success: true }); 
    } catch (e) { res.status(500).json({ error: e.message }) } 
});

// Password generator
app.get('/api/password', (req, res) => { 
    const len = parseInt(req.query.length) || 16; 
    const chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+-=[]{}|;:,.<>?'; 
    let pw = ''; 
    for (let i = 0; i < len; i++) pw += chars[Math.floor(Math.random() * chars.length)]; 
    res.json({ password: pw, length: len }); 
});

// AI Config
const AI_CONFIG_FILE = path.join(__dirname, 'ai_config.json');
function getAiConfig() { 
    try { 
        const c = JSON.parse(fs.readFileSync(AI_CONFIG_FILE, 'utf8')); 
        return { apiKey: c.apiKey || '', provider: c.provider || 'groq', assistantName: c.assistantName || 'jarvis' }; 
    } catch (e) { return { apiKey: '', provider: 'groq', assistantName: 'jarvis' }; } 
}

app.get('/api/ai/config', (_, res) => { 
    const c = getAiConfig(); 
    res.json({ hasKey: !!c.apiKey, provider: c.provider, assistantName: c.assistantName || 'jarvis' }); 
});

app.post('/api/ai/config', (req, res) => {
    const { apiKey, provider, assistantName } = req.body;
    const c = getAiConfig();
    fs.writeFileSync(AI_CONFIG_FILE, JSON.stringify({
        apiKey: apiKey !== undefined ? apiKey : c.apiKey,
        provider: provider || c.provider || 'groq',
        assistantName: assistantName || c.assistantName || 'jarvis'
    }));
    res.json({ success: true });
});


// AI Chat endpoint
app.post('/api/ai/chat', requireAuth, async (req, res) => {
    const { messages } = req.body;
    const c = getAiConfig();
    
    if (!c.apiKey) {
        return res.json({ error: 'No API key configured. Go to AI settings to add your Groq API key.' });
    }
    
    try {
        const systemMsg = { role: 'system', content: `You are ${c.assistantName || 'ShadowCypher'}, an elite AI assistant for a router admin panel.` };
        const allMessages = [systemMsg, ...(messages || [])];
        
        const response = await fetch('https://api.groq.com/openai/v1/chat/completions', {
            method: 'POST',
            headers: {
                'Authorization': 'Bearer ' + c.apiKey,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                model: 'llama-3.1-70b-versatile',
                messages: allMessages,
                temperature: 0.7
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            return res.json({ error: data.error.message });
        }
        
        const reply = data.choices?.[0]?.message?.content || 'No response';
        res.json({ reply: reply });
    } catch (e) {
        res.json({ error: 'AI error: ' + e.message });
    }
});



// Shadow Mode
app.post('/api/hacking/shadow-mode', (req, res) => {
    shadowMode = !!req.body.enabled;
    res.json({ success: true, shadowMode });
});

// Pentest tools
app.post('/api/pentest', async (req, res) => {
    const { tool, target, params } = req.body;
    if (!tool || !target) return res.status(400).json({ error: 'Tool and target required' });
    const safeTarget = sanitizeTarget(target);
    if (!safeTarget) return res.status(400).json({ error: 'Invalid target (no shell metacharacters)' });
    const proxy = shadowMode ? 'proxychains4 ' : '';
    const port = Math.min(65535, Math.max(1, parseInt(params?.port, 10) || 80));
    const n = Math.min(10000, Math.max(10, parseInt(params?.n, 10) || 100));
    const c = Math.min(100, Math.max(1, parseInt(params?.c, 10) || 10));
    let cmd = '';
    const urlTarget = safeTarget.startsWith('http') ? safeTarget : 'http://' + safeTarget.replace(/^\/+/, '');
    switch (tool) {
        case 'ab': cmd = `${proxy}ab -n ${n} -c ${c} ${shellQuote(urlTarget)}`; break;
        case 'nikto': cmd = `${proxy}nikto -h ${shellQuote(safeTarget)} -Tuning 123b 2>/dev/null`; break;
        case 'nmap-vuln': cmd = `${proxy}nmap --script vuln ${shellQuote(safeTarget)} 2>/dev/null`; break;
        case 'slowhttptest': cmd = `${proxy}slowhttptest -c 1000 -H -g -o /tmp/slow -i 10 -r 200 -t GET -u ${shellQuote(urlTarget)} -x 24 -p 3 2>/dev/null`; break;
        case 'gobuster': cmd = `${proxy}gobuster dir -u ${shellQuote(urlTarget)} -w /usr/share/wordlists/dirb/common.txt --quiet 2>/dev/null`; break;
        case 'sqlmap': cmd = `${proxy}sqlmap -u ${shellQuote(urlTarget)} --batch --banner 2>/dev/null`; break;
        case 'hping3': cmd = `${proxy}sudo hping3 -S --flood -V -p ${port} ${shellQuote(safeTarget)} 2>/dev/null`; break;
        case 'wifite': cmd = `sudo wifite --kill --all-ips --dict /usr/share/wordlists/rockyou.txt 2>/dev/null`; break;
        case 'searchsploit': cmd = `searchsploit ${shellQuote(safeTarget)} 2>/dev/null`; break;
        default: return res.status(400).json({ error: 'Unknown tool' });
    }
    try {
        const o = await run(`${cmd} 2>&1 | tail -n 80`);
        res.json({ success: true, tool, output: o });
    } catch (e) { res.json({ success: false, output: e.message }); }
});

// DNS Benchmark
app.get('/api/dns/benchmark', async (_, res) => {
    const servers = [
        { name: 'Cloudflare', ip: '1.1.1.1' }, 
        { name: 'Google', ip: '8.8.8.8' }, 
        { name: 'Quad9', ip: '9.9.9.9' }, 
        { name: 'OpenDNS', ip: '208.67.222.222' }
    ];
    const results = [];
    for (const s of servers) {
        try {
            const o = await run(`ping -c 3 -W 1 ${s.ip} | tail -1 | awk -F "/" '{print $5}'`);
            results.push({ ...s, latency: o.trim() || 'timeout' });
        } catch (e) { results.push({ ...s, latency: 'error' }); }
    }
    res.json(results);
});

// Network audit
app.get('/api/audit/network', async (_, res) => {
    try {
        const gw = await run("ip route | grep default | awk '{print $3}'");
        const scan = await run(`nmap -F --open ${gw.trim()} 2>/dev/null | tail -n +5`);
        res.json({ gateway: gw.trim(), scan_results: scan });
    } catch (e) { res.status(500).json({ error: e.message }); }
});

// Intelligence / Security
const INTEL_CONFIG_FILE = path.join(__dirname, 'intel_config.json');
function getIntelConfig() {
    try {
        const c = JSON.parse(fs.readFileSync(INTEL_CONFIG_FILE, 'utf8'));
        return {
            hibpApiKey: c.hibpApiKey || '',
            otxApiKey: c.otxApiKey || '',
            abuseChAuthKey: c.abuseChAuthKey || ''
        };
    } catch (e) { return { hibpApiKey: '', otxApiKey: '', abuseChAuthKey: '' }; }
}

function saveIntelConfig(updates) {
    const c = getIntelConfig();
    const merged = { ...c, ...updates };
    fs.writeFileSync(INTEL_CONFIG_FILE, JSON.stringify(merged, null, 2));
}

app.get('/api/intel/config', (_, res) => {
    const c = getIntelConfig();
    res.json({ hasHibpKey: !!c.hibpApiKey, hasOtxKey: !!c.otxApiKey, hasAbuseChKey: !!c.abuseChAuthKey });
});

app.post('/api/intel/config', (req, res) => {
    try {
        const c = getIntelConfig();
        const hibp = req.body.hibpApiKey != null ? String(req.body.hibpApiKey).trim() : c.hibpApiKey;
        const otx = req.body.otxApiKey != null ? String(req.body.otxApiKey).trim() : c.otxApiKey;
        const abuseCh = req.body.abuseChAuthKey != null ? String(req.body.abuseChAuthKey).trim() : c.abuseChAuthKey;
        saveIntelConfig({ hibpApiKey: hibp, otxApiKey: otx, abuseChAuthKey: abuseCh });
        res.json({ success: true });
    } catch (e) { res.status(500).json({ error: e.message }); }
});

// Sanitization helpers
function sanitizeIface(name) {
    if (!name || name === 'any') return 'any';
    return /^[a-zA-Z0-9_.-]+$/.test(name) ? name : 'any';
}

function sanitizeOnionUrl(url) {
    const s = String(url).trim().toLowerCase();
    if (!s.endsWith('.onion')) return null;
    if (!/^[a-z0-9]+\.onion$/i.test(s.split('/')[0])) return null;
    return s.replace(/[^a-z0-9.:\/-]/gi, '');
}

function sanitizeTarget(t) {
    const s = String(t).trim();
    if (!s.length || /[;&|$`<>()]/.test(s)) return null;
    return s;
}

function sanitizeHash(h) {
    const s = String(h).trim().toLowerCase();
    if (!/^[a-f0-9]{32}$/.test(s) && !/^[a-f0-9]{40}$/.test(s) && !/^[a-f0-9]{64}$/.test(s)) return null;
    return s;
}

function sanitizeUrlForLookup(u) {
    const s = String(u).trim();
    if (!s.length || s.length > 2048) return null;
    try {
        const parsed = new URL(s);
        if (!['http:', 'https:'].includes(parsed.protocol)) return null;
        return parsed.href;
    } catch (_) { return null; }
}

function shellQuote(s) {
    return '"' + String(s).replace(/\\/g, '\\\\').replace(/"/g, '\\"') + '"';
}

// Packet sniffing
app.post('/api/intel/sniff', async (req, res) => {
    const iface = sanitizeIface(req.body.iface);
    const count = Math.min(500, Math.max(5, parseInt(req.body.count, 10) || 20));
    try {
        const o = await run(`sudo tshark -i ${iface} -c ${count} -T fields -e frame.number -e frame.time -e ip.src -e ip.dst -e _ws.col.Protocol -E header=y -E separator=, 2>/dev/null`);
        res.json({ success: true, output: o || "No packets captured." });
    } catch (e) {
        try {
            const oStatus = await run(`sudo tcpdump -i ${iface} -n -c ${count} -A 2>/dev/null`);
            res.json({ success: true, method: 'tcpdump-fallback', output: oStatus });
        } catch (e2) {
            res.status(500).json({ error: e2.message || 'tshark and tcpdump failed.' });
        }
    }
});

// IDS Alerts
app.get('/api/intel/ids-alerts', async (_, res) => {
    try {
        let alerts = '';
        try { alerts = await run('tail -n 50 /var/log/snort/alert 2>/dev/null'); } catch (_) { }
        if (!alerts || alerts.length < 5) {
            try {
                const suricataLog = '/var/log/suricata/fast.log';
                if (fs.existsSync(suricataLog)) {
                    alerts = fs.readFileSync(suricataLog, 'utf8').split('\n').slice(-50).join('\n');
                }
            } catch (_) { }
        }
        if (!alerts || alerts.length < 5) {
            try {
                const evePath = '/var/log/suricata/eve.json';
                if (fs.existsSync(evePath)) {
                    const lines = fs.readFileSync(evePath, 'utf8').trim().split('\n').slice(-30);
                    alerts = lines.filter(l => l.includes('"event_type":"alert"')).map(l => {
                        try { const j = JSON.parse(l); return j.timestamp + ' ' + (j.alert?.signature || '') + ' ' + (j.src_ip || '') + ' -> ' + (j.dest_ip || ''); } catch (_) { return l; }
                    }).join('\n');
                }
            } catch (_) { }
        }
        res.json({ success: true, alerts: alerts || 'No IDS alerts.' });
    } catch (e) { res.json({ success: false, error: e.message }); }
});

// WiFi Recon
app.get('/api/intel/wifi-recon', async (_, res) => {
    try {
        const ifaces = await run("iw dev | grep Interface | awk '{print $2}' || echo ''");
        const wiface = ifaces.split('\n')[0].trim();
        if (!wiface) return res.json({ success: false, output: "No wireless interface found." });
        const o = await run(`sudo iwlist ${wiface} scan 2>/dev/null | grep -E "ESSID|Address|Signal|Quality|Channel" | head -n 80`);
        res.json({ success: true, interface: wiface, output: o || 'No scan results.' });
    } catch (e) { res.json({ success: false, output: e.message }); }
});

// Threat Feed
app.get('/api/intel/threat-feed', async (_, res) => {
    try {
        let ips = [];
        let source = '';
        try {
            const r = await fetch('https://feodotracker.abuse.ch/downloads/ipblocklist_recommended.txt', { signal: AbortSignal.timeout(15000) });
            const txt = await r.text();
            ips = txt.split('\n').map(l => l.trim()).filter(l => l && !l.startsWith('#') && /^\d+\.\d+\.\d+\.\d+$/.test(l));
            source = 'abuse.ch Feodo Tracker';
        } catch (_) { }
        if (ips.length < 10) {
            try {
                const r2 = await fetch('https://raw.githubusercontent.com/stamparm/ipsum/master/levels/3.txt', { signal: AbortSignal.timeout(15000) });
                const txt2 = await r2.text();
                const more = txt2.split('\n').map(l => l.trim()).filter(l => l && !l.startsWith('#') && /^\d+\.\d+\.\d+\.\d+$/.test(l));
                if (more.length) { ips = ips.concat(more); source = source ? source + ' + ipsum' : 'ipsum'; }
            } catch (_) { }
        }
        const uniq = [...new Set(ips)].slice(0, 100);
        res.json({ source: source || 'threat feed', count: uniq.length, samples: uniq });
    } catch (e) { res.status(500).json({ error: e.message }); }
});

// AlienVault OTX - fetch pulses/IOCs (requires OTX API key)
app.get('/api/intel/otx', async (req, res) => {
    const config = getIntelConfig();
    if (!config.otxApiKey) {
        return res.status(400).json({
            error: 'OTX API key required. Add to Intel Config (get at https://otx.alienvault.com/api)',
            pulses: []
        });
    }
    try {
        const modifiedSince = req.query.modified_since || '';
        let url = 'https://otx.alienvault.com/api/v1/pulses/subscribed';
        if (modifiedSince) url += '?modified_since=' + encodeURIComponent(modifiedSince);
        const r = await fetch(url, {
            headers: { 'X-OTX-API-KEY': config.otxApiKey, 'User-Agent': 'ShadowCypher-Intel' },
            signal: AbortSignal.timeout(15000)
        });
        if (!r.ok) {
            const err = await r.text();
            return res.status(r.status).json({
                error: r.status === 401 ? 'Invalid OTX API key' : (err || r.statusText),
                pulses: []
            });
        }
        const data = await r.json();
        const pulses = (data.results || []).slice(0, 50).map(p => ({
            id: p.id,
            name: p.name,
            description: (p.description || '').slice(0, 200),
            author: p.author_name,
            created: p.created,
            modified: p.modified,
            tags: p.tags || [],
            indicator_count: (p.indicators || []).length
        }));
        res.json({ success: true, count: pulses.length, pulses });
    } catch (e) {
        res.status(500).json({ error: e.message || 'OTX request failed', pulses: [] });
    }
});

// MalwareBazaar hash check (MD5/SHA1/SHA256)
app.post('/api/intel/malwarebazaar', async (req, res) => {
    const hash = sanitizeHash(req.body.hash || req.query.hash);
    if (!hash) return res.status(400).json({ error: 'Valid MD5 (32), SHA1 (40), or SHA256 (64) hex hash required' });
    const config = getIntelConfig();
    if (!config.abuseChAuthKey) {
        return res.status(400).json({
            error: 'abuse.ch Auth-Key required. Add to Intel Config (get free at https://auth.abuse.ch/)',
            found: false
        });
    }
    try {
        const form = new URLSearchParams({ query: 'get_info', hash });
        const r = await fetch('https://mb-api.abuse.ch/api/v1/', {
            method: 'POST',
            headers: {
                'Auth-Key': config.abuseChAuthKey,
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'ShadowCypher-Intel'
            },
            body: form.toString(),
            signal: AbortSignal.timeout(15000)
        });
        const data = await r.json();
        if (data.query_status === 'no_api_key' || data.query_status === 'user_blacklisted') {
            return res.status(400).json({
                error: 'Invalid or missing abuse.ch Auth-Key. Get one at https://auth.abuse.ch/',
                found: false
            });
        }
        if (data.query_status === 'hash_not_found' || data.query_status === 'no_hash_provided' || data.query_status === 'illegal_hash') {
            return res.json({ success: true, found: false, hash, message: 'Hash not found in MalwareBazaar' });
        }
        if (data.query_status !== 'ok') {
            return res.json({ success: true, found: false, hash, message: data.query_status || 'Unknown' });
        }
        const sample = data.data?.[0] || data;
        res.json({
            success: true,
            found: true,
            hash,
            sha256: sample.sha256_hash,
            md5: sample.md5_hash,
            malware: sample.signature || null,
            tags: sample.tags || [],
            first_seen: sample.first_seen,
            file_type: sample.file_type,
            file_name: sample.file_name
        });
    } catch (e) {
        res.status(500).json({ error: e.message || 'MalwareBazaar request failed', found: false });
    }
});

// URLhaus URL check
app.post('/api/intel/urlhaus', async (req, res) => {
    const url = sanitizeUrlForLookup(req.body.url || req.query.url);
    if (!url) return res.status(400).json({ error: 'Valid HTTP/HTTPS URL required (max 2048 chars)' });
    const config = getIntelConfig();
    if (!config.abuseChAuthKey) {
        return res.status(400).json({
            error: 'abuse.ch Auth-Key required. Add to Intel Config (get free at https://auth.abuse.ch/)',
            threat: false
        });
    }
    try {
        const form = new URLSearchParams({ url });
        const r = await fetch('https://urlhaus-api.abuse.ch/v1/url/', {
            method: 'POST',
            headers: {
                'Auth-Key': config.abuseChAuthKey,
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'ShadowCypher-Intel'
            },
            body: form.toString(),
            signal: AbortSignal.timeout(15000)
        });
        const data = await r.json();
        if (data.query_status === 'no_api_key' || data.query_status === 'user_blacklisted') {
            return res.status(400).json({
                error: 'Invalid or missing abuse.ch Auth-Key. Get one at https://auth.abuse.ch/',
                threat: false
            });
        }
        if (data.query_status === 'no_results' || !data.threat) {
            return res.json({ success: true, threat: false, url, message: 'URL not found in URLhaus' });
        }
        res.json({
            success: true,
            threat: true,
            url,
            url_status: data.url_status,
            threat_type: data.threat || 'malware_download',
            tags: data.tags || [],
            date_added: data.date_added,
            urlhaus_reference: data.urlhaus_reference
        });
    } catch (e) {
        res.status(500).json({ error: e.message || 'URLhaus request failed', threat: false });
    }
});

// Data breach check
app.post('/api/intel/check-leak', async (req, res) => {
    const email = String(req.body.email || '').trim().toLowerCase();
    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return res.status(400).json({ error: 'Valid email required' });
    const config = getIntelConfig();
    if (!config.hibpApiKey) {
        return res.status(400).json({
            error: 'HIBP API key required. Get one at https://haveibeenpwned.com/API/Key',
            breached: false,
            leaks: []
        });
    }
    try {
        const enc = encodeURIComponent(email);
        const r = await fetch(`https://haveibeenpwned.com/api/v3/breachedaccount/${enc}`, {
            headers: { 'hibp-api-key': config.hibpApiKey, 'User-Agent': 'ShadowCypher-Router-Admin' },
            signal: AbortSignal.timeout(10000)
        });
        if (r.status === 404) return res.json({ email, breached: false, leaks: [] });
        if (!r.ok) {
            const err = await r.text();
            return res.status(r.status).json({
                error: r.status === 401 ? 'Invalid HIBP API key' : (r.status === 429 ? 'Rate limited' : err || r.statusText),
                breached: false,
                leaks: []
            });
        }
        const breaches = await r.json();
        const leaks = (breaches || []).map(b => ({ name: b.Name || b.Title || 'Unknown', date: b.BreachDate, domain: b.Domain }));
        res.json({ email, breached: leaks.length > 0, leaks });
    } catch (e) {
        res.status(500).json({ error: e.message || 'HIBP request failed', breached: false, leaks: [] });
    }
});

// Onion fetch
app.post('/api/intel/onion-fetch', async (req, res) => {
    const raw = req.body.url;
    const url = sanitizeOnionUrl(raw);
    if (!url) return res.status(400).json({ error: 'Valid .onion URL required' });
    try {
        const o = await run(`torsocks curl -s -m 30 "${url}" 2>&1 | head -c 10000`);
        res.json({ success: true, url, data: `[TOR]\n\n${o || 'No content or timeout.'}` });
    } catch (e) {
        res.json({ success: false, error: 'Tor failed: ' + e.message });
    }
});

// ═══════════ DIAGNOSTIC / LOGGING ═══════════
app.get('/api/diagnostic', async (req, res) => {
    const results = {};
    
    const tests = [
        { name: 'overview', fn: () => run('echo ok') },
        { name: 'devices', fn: () => run('ip neighbor show 2>/dev/null || arp -a') },
        { name: 'wifi', fn: async () => { const w = await getWirelessIface(); return run(w ? `iwconfig ${w} 2>/dev/null` : 'echo "no wifi"'); } },
        { name: 'ports', fn: () => run('ss -tlnp 2>/dev/null | head -5') },
        { name: 'firewall', fn: () => run('sudo iptables -L INPUT -n --line-numbers 2>&1 | head -3') },
        { name: 'nmap', fn: () => run('which nmap') },
        { name: 'nikto', fn: () => run('which nikto') },
        { name: 'sqlmap', fn: () => run('which sqlmap') },
        { name: 'proxychains', fn: () => run('which proxychains4') },
        { name: 'tshark', fn: () => run('which tshark') },
        { name: 'tcpdump', fn: () => run('which tcpdump') }
    ];
    
    for (const test of tests) {
        try {
            await test.fn();
            results[test.name] = { status: 'ok' };
        } catch (e) {
            results[test.name] = { status: 'error', message: e.message };
        }
    }
    
    try {
        if (fs.existsSync(LOG_FILE)) {
            const logs = fs.readFileSync(LOG_FILE, 'utf8').split('\n').filter(l => l.trim()).slice(-50);
            results.recentLogs = logs;
        }
    } catch (e) {}
    
    res.json(results);
});

app.get('/api/logs/app', (req, res) => {
    try {
        if (fs.existsSync(LOG_FILE)) {
            const logs = fs.readFileSync(LOG_FILE, 'utf8').split('\n').filter(l => l.trim()).slice(-100);
            res.json({ logs });
        } else {
            res.json({ logs: [] });
        }
    } catch (e) {
        res.json({ logs: [], error: e.message });
    }
});

// AI Functions
const AI_FUNCTIONS = [
    { name: 'get_system_overview', description: 'Get system overview including IPs, CPU, memory, uptime' },
    { name: 'get_devices', description: 'List all devices on the network' },
    { name: 'get_processes', description: 'List top processes by CPU usage' },
    { name: 'kill_process', description: 'Kill a process by PID', parameters: { pid: 'number' } },
    { name: 'block_ip', description: 'Block an IP in the firewall', parameters: { ip: 'string' } },
    { name: 'unblock_ip', description: 'Unblock an IP in the firewall', parameters: { ip: 'string' } },
    { name: 'open_port', description: 'Open a port in the firewall', parameters: { port: 'number', protocol: 'string' } },
    { name: 'close_port', description: 'Close a port', parameters: { port: 'number', protocol: 'string' } },
    { name: 'get_bandwidth', description: 'Get current bandwidth usage per interface' },
    { name: 'get_connections', description: 'Get active network connections' },
    { name: 'get_ports', description: 'List all listening ports' },
    { name: 'get_disk', description: 'Get disk usage information' },
    { name: 'get_temperatures', description: 'Get CPU/GPU temperatures' },
    { name: 'run_command', description: 'Run any shell command', parameters: { cmd: 'string' } },
    { name: 'get_docker', description: 'Get Docker containers and their status' },
    { name: 'docker_action', description: 'Start/stop/restart a Docker container', parameters: { name: 'string', action: 'string' } },
    { name: 'get_minecraft', description: 'Get Minecraft server status' },
    { name: 'scan_network', description: 'Force a network device scan' },
    { name: 'speed_test', description: 'Run a download speed test' },
    { name: 'get_wifi', description: 'Get WiFi connection info and nearby networks' },
    { name: 'install_package', description: 'Install an apt package', parameters: { name: 'string' } },
    { name: 'search_packages', description: 'Search for apt packages', parameters: { query: 'string' } },
    { name: 'run_pentest', description: 'Run a pentesting tool (ab, nikto, nmap-vuln, slowhttptest, gobuster, sqlmap, hping3)', parameters: { tool: 'string', target: 'string' } },
    { name: 'benchmark_dns', description: 'Benchmark common DNS servers to find the fastest one' },
    { name: 'audit_network', description: 'Run a security and performance audit on the router/gateway' },
    { name: 'intercept_signals', description: 'Sniff live network traffic for intelligence gathering', parameters: { count: 'number' } },
    { name: 'wifi_recon', description: 'Perform elite wireless reconnaissance to map nearby signals' },
    { name: 'get_threat_intel', description: 'Fetch the latest global network threat intelligence feeds' },
    { name: 'check_data_leak', description: 'Monitor for data breaches or leaked credentials', parameters: { email: 'string' } },
    { name: 'fetch_onion_intel', description: 'Safely acquire intelligence from .onion services in the darknet', parameters: { url: 'string' } }
];

// Start server
server.listen(PORT, () => {
    console.log(`\nShadowCypher running on http://localhost:${PORT}`);
    console.log(`Default login: admin / shadow`);
});
