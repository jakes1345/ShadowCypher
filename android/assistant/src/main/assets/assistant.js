/**
 * Shadow AI — ShadowCypher Voice Assistant
 * Authenticated, context-aware, action-capable.
 * Replaces Bixby / Siri / Google Assistant.
 */

const ShadowAssistant = (() => {
  let plugin = null;
  let overlay = null;
  let state = 'idle'; // idle | listening | thinking | speaking | setup
  let conversationHistory = [];
  let _idleTimer = null;
  let apiKey = null;
  let guardianCtx = null; // { me, summary }

  const API_BASE = 'https://api.shadowcypher.site';

  // ── Security command patterns ──────────────────────────────────────────────

  const COMMANDS = [
    {
      pattern: /\b(scan|scanning).*(network|lan|devices?)\b|\brun (a )?scan\b/i,
      action: 'scan_network',
    },
    {
      pattern: /\b(what|which|show|list|how many).*(devices?|machines?|hosts?).*(network|lan|connected)\b|what.*(on|connected to).*(network|lan)\b/i,
      action: 'list_devices',
    },
    {
      pattern: /\b(any|check|show|what).*(incident|alert|threat|attack)\b|am i (being )?(attacked|hacked|monitored)\b/i,
      action: 'list_incidents',
    },
    {
      pattern: /\b(any|check|show|list|what).*(cve|vulnerabilit|exploit)\b/i,
      action: 'list_cves',
    },
    {
      pattern: /\b(is |check |am i ).*(anonymous|ghost|hidden|invisible)\b|\bghost (mode|protocol)\b/i,
      action: 'ghost_status',
    },
    {
      pattern: /\b(network |guardian )status\b|how.*(network|lan)\b|summary\b/i,
      action: 'network_summary',
    },
    {
      pattern: /\bset (api )?key\b|\benter (api )?key\b|\bapi key\b|\bconfigure\b/i,
      action: 'open_settings',
    },
  ];

  // ── Bootstrap ──────────────────────────────────────────────────────────────

  async function init() {
    if (!window.Capacitor || !window.Capacitor.isNativePlatform()) return;

    try {
      for (let i = 0; i < 30; i++) {
        plugin = window.Capacitor?.Plugins?.ShadowAssistant;
        if (plugin) break;
        await sleep(100);
      }
      if (!plugin) {
        console.warn('[ShadowAssistant] Plugin not available');
        return;
      }

      plugin.addListener('assistInvoked', handleAssistInvoke);
      plugin.addListener('speechResult', handleSpeechResult);
      plugin.addListener('partialResult', handlePartialResult);
      plugin.addListener('speechError', handleSpeechError);
      plugin.addListener('listeningStarted', () => setState('listening'));
      plugin.addListener('speechEnded', () => {
        if (state === 'listening') setState('thinking');
      });

      buildOverlay();

      // Load stored API key
      try {
        const result = await plugin.getApiKey();
        apiKey = result?.key || null;
      } catch (_) {}

      // Pre-load Guardian context in background
      if (apiKey) loadGuardianContext().catch(() => {});

      const status = await plugin.checkAssistStatus();
      if (status.wasAssistLaunch) handleAssistInvoke({ source: 'launch' });

      console.log('[ShadowAssistant] Ready. key:', apiKey ? 'set' : 'missing');
    } catch (e) {
      console.warn('[ShadowAssistant] Init failed:', e);
    }
  }

  // ── Guardian context ───────────────────────────────────────────────────────

  async function loadGuardianContext() {
    if (!apiKey) return;
    try {
      const headers = { Authorization: `Bearer ${apiKey}` };
      const [meRes, sumRes] = await Promise.all([
        fetch(`${API_BASE}/v1/me`, { headers }),
        fetch(`${API_BASE}/v1/guardian/summary`, { headers }),
      ]);
      const me = meRes.ok ? await meRes.json() : null;
      const summary = sumRes.ok ? await sumRes.json() : null;
      guardianCtx = { me, summary };
    } catch (_) {
      guardianCtx = null;
    }
  }

  function buildSystemPrompt() {
    const lines = [
      'You are SHADOW AI, the personal voice assistant built into the ShadowCypher security platform.',
      'Reply in 1-3 short sentences for speech. No markdown, no bullet points, no code blocks.',
      'Be direct and concise. Use plain language.',
    ];

    if (guardianCtx?.me) {
      const { email, effective_plan, in_trial } = guardianCtx.me;
      lines.push(`\nUser: ${email}, plan: ${effective_plan}${in_trial ? ' (trial)' : ''}.`);
    }

    if (guardianCtx?.summary) {
      const { agents = [], devices = [], incidents = [], cve_alerts = [], last_scan_at } = guardianCtx.summary;
      const activeIncidents = incidents.filter(i => !i.resolved);
      const onlineAgents = agents.filter(a => a.online);

      lines.push(`\nNetwork: ${devices.length} devices, ${activeIncidents.length} active incidents, ${cve_alerts.length} CVE alerts.`);
      lines.push(`Agents: ${onlineAgents.length}/${agents.length} online.`);
      if (last_scan_at) {
        const ago = Math.round((Date.now() - new Date(last_scan_at).getTime()) / 60000);
        lines.push(`Last scan: ${ago < 60 ? ago + ' minutes ago' : Math.round(ago / 60) + ' hours ago'}.`);
      }
      if (activeIncidents.length > 0) {
        lines.push(`Most recent incident: ${activeIncidents[0].description} (${activeIncidents[0].severity}).`);
      }
    } else if (!apiKey) {
      lines.push('\nNote: No API key configured — you can only answer general questions. Security-specific commands are unavailable.');
    }

    return lines.join(' ');
  }

  // ── Command dispatch ───────────────────────────────────────────────────────

  async function dispatchCommand(action) {
    const headers = apiKey ? { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' };

    switch (action) {
      case 'scan_network': {
        if (!apiKey) return 'No API key set. Go to settings to configure your ShadowCypher API key.';
        const r = await fetch(`${API_BASE}/v1/scans`, { method: 'POST', headers, body: '{}' });
        return r.ok
          ? 'Network scan initiated. Results will appear in your Guardian dashboard.'
          : 'Failed to start scan. Check your network connection.';
      }

      case 'list_devices': {
        if (!apiKey) return 'API key required to check network devices.';
        await loadGuardianContext();
        const devices = guardianCtx?.summary?.devices || [];
        if (!devices.length) return 'No devices found. Make sure the Guardian agent is running on your network.';
        const names = devices.slice(0, 5).map(d => d.hostname || d.ip);
        const extra = devices.length > 5 ? ` and ${devices.length - 5} more` : '';
        return `${devices.length} device${devices.length > 1 ? 's' : ''} on your network: ${names.join(', ')}${extra}.`;
      }

      case 'list_incidents': {
        if (!apiKey) return 'API key required to check incidents.';
        await loadGuardianContext();
        const active = (guardianCtx?.summary?.incidents || []).filter(i => !i.resolved);
        if (!active.length) return 'No active incidents. Your network looks clean.';
        const top = active[0];
        return `${active.length} active incident${active.length > 1 ? 's' : ''}. Most severe: ${top.description} — ${top.severity} priority.`;
      }

      case 'list_cves': {
        if (!apiKey) return 'API key required to check CVE alerts.';
        await loadGuardianContext();
        const cves = guardianCtx?.summary?.cve_alerts || [];
        if (!cves.length) return 'No CVE alerts matched against your devices.';
        const critical = cves.filter(c => c.severity === 'CRITICAL').length;
        return `${cves.length} CVE${cves.length > 1 ? 's' : ''} matched against your devices — ${critical} critical. Check the Guardian dashboard for details.`;
      }

      case 'ghost_status': {
        return 'Ghost Protocol status is managed from the desktop app. Use the ShadowCypher desktop app to engage or disengage ghost mode.';
      }

      case 'network_summary': {
        if (!apiKey) return 'Configure your API key in settings to get network status.';
        await loadGuardianContext();
        if (!guardianCtx) return 'Could not reach the Guardian API. Check your connection.';
        const { agents = [], devices = [], incidents = [] } = guardianCtx.summary || {};
        const active = incidents.filter(i => !i.resolved).length;
        const online = agents.filter(a => a.online).length;
        return `Network summary: ${devices.length} devices, ${active} active incident${active !== 1 ? 's' : ''}, ${online} of ${agents.length} agent${agents.length !== 1 ? 's' : ''} online.`;
      }

      case 'open_settings': {
        showSettings();
        return null; // handled by settings UI
      }

      default:
        return null;
    }
  }

  // ── Overlay UI ────────────────────────────────────────────────────────────

  function buildOverlay() {
    if (overlay) return;

    const el = document.createElement('div');
    el.id = 'shadow-assistant-overlay';
    el.innerHTML = `
      <div class="sa-backdrop" onclick="ShadowAssistant.dismiss()"></div>
      <div class="sa-panel">

        <!-- Main assistant view -->
        <div id="sa-main">
          <div class="sa-handle"></div>
          <div class="sa-orb-ring">
            <div class="sa-orb" id="sa-orb"></div>
          </div>
          <div class="sa-status" id="sa-status">SHADOW AI</div>
          <div class="sa-transcript" id="sa-transcript"></div>
          <div class="sa-response" id="sa-response"></div>
          <div class="sa-controls">
            <button class="sa-btn sa-action" id="sa-secondary-btn" onclick="ShadowAssistant.openSettings()" title="Settings">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
            </button>
            <button class="sa-btn sa-mic" id="sa-mic-btn" onclick="ShadowAssistant.startListening()">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
                <path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v4M8 23h8"/>
              </svg>
            </button>
            <button class="sa-btn sa-action" onclick="ShadowAssistant.dismiss()">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>
          <div class="sa-chips" id="sa-chips">
            <button class="sa-chip" onclick="ShadowAssistant._runChip('Scan my network')">Scan network</button>
            <button class="sa-chip" onclick="ShadowAssistant._runChip('Any active incidents?')">Incidents</button>
            <button class="sa-chip" onclick="ShadowAssistant._runChip('What devices are on my network?')">Devices</button>
            <button class="sa-chip" onclick="ShadowAssistant._runChip('Network status summary')">Summary</button>
          </div>
        </div>

        <!-- Settings view -->
        <div id="sa-settings" style="display:none">
          <div class="sa-handle"></div>
          <div class="sa-settings-title">SHADOW AI // SETTINGS</div>
          <div class="sa-field-label">ShadowCypher API Key</div>
          <div class="sa-key-row">
            <input id="sa-key-input" class="sa-key-input" type="password" placeholder="sc_live_..." autocomplete="off" spellcheck="false"/>
            <button class="sa-btn-small" id="sa-key-toggle" onclick="ShadowAssistant._toggleKeyVisibility()">SHOW</button>
          </div>
          <div class="sa-field-hint">Find your key under Account → API Key on shadowcypher.site</div>
          <button class="sa-btn-primary" onclick="ShadowAssistant._saveApiKey()">Save &amp; Connect</button>
          ${apiKey ? '<button class="sa-btn-danger" onclick="ShadowAssistant._clearApiKey()">Remove Key</button>' : ''}
          <button class="sa-btn-ghost" onclick="ShadowAssistant._closeSettings()">← Back</button>
          <div class="sa-key-status" id="sa-key-status"></div>
        </div>

      </div>
    `;

    const style = document.createElement('style');
    style.textContent = `
      #shadow-assistant-overlay {
        position: fixed; inset: 0; z-index: 99999;
        display: none; align-items: flex-end; justify-content: center;
        font-family: 'JetBrains Mono', 'Courier New', monospace;
      }
      #shadow-assistant-overlay.active { display: flex; }
      .sa-backdrop {
        position: absolute; inset: 0;
        background: rgba(0,0,0,0.72); backdrop-filter: blur(6px);
      }
      .sa-panel {
        position: relative; z-index: 1;
        background: linear-gradient(180deg, #0d0d1a 0%, #050510 100%);
        border: 1px solid rgba(180,74,255,0.25);
        border-bottom: none;
        border-radius: 20px 20px 0 0;
        padding: 0 24px 48px;
        width: 100%; max-width: 520px;
        box-shadow: 0 -8px 60px rgba(180,74,255,0.12);
        animation: sa-slide-up 0.3s cubic-bezier(0.32,0.72,0,1);
      }
      @keyframes sa-slide-up {
        from { transform: translateY(100%); opacity: 0; }
        to   { transform: translateY(0); opacity: 1; }
      }
      .sa-handle {
        width: 36px; height: 4px; border-radius: 2px;
        background: rgba(255,255,255,0.15); margin: 12px auto 24px;
      }
      .sa-orb-ring {
        width: 88px; height: 88px; border-radius: 50%;
        border: 1.5px solid rgba(180,74,255,0.35);
        display: flex; align-items: center; justify-content: center;
        margin: 0 auto 18px;
        animation: sa-ring-pulse 3s ease-in-out infinite;
      }
      .sa-orb {
        width: 64px; height: 64px; border-radius: 50%;
        background: radial-gradient(circle at 35% 35%, #c77dff, #6c1fff);
        box-shadow: 0 0 24px rgba(180,74,255,0.45);
        transition: all 0.2s ease;
      }
      .sa-orb.listening {
        animation: sa-orb-listen 0.5s ease-in-out infinite alternate;
        background: radial-gradient(circle at 35% 35%, #ff6b6b, #cc1a1a);
      }
      .sa-orb.thinking {
        background: radial-gradient(circle at 35% 35%, #4de8c2, #0070f3);
        animation: sa-orb-think 1.4s ease-in-out infinite;
      }
      .sa-orb.speaking {
        animation: sa-orb-speak 0.25s ease-in-out infinite alternate;
      }
      @keyframes sa-ring-pulse {
        0%,100% { border-color: rgba(180,74,255,0.25); }
        50% { border-color: rgba(180,74,255,0.6); }
      }
      @keyframes sa-orb-listen {
        from { transform: scale(0.88); box-shadow: 0 0 16px rgba(239,68,68,0.5); }
        to   { transform: scale(1.12); box-shadow: 0 0 44px rgba(239,68,68,0.8); }
      }
      @keyframes sa-orb-think {
        0%,100% { transform: scale(1); opacity: 1; }
        50% { transform: scale(0.92); opacity: 0.7; }
      }
      @keyframes sa-orb-speak {
        from { transform: scaleY(0.88); }
        to   { transform: scaleY(1.12); }
      }
      .sa-status {
        font-size: 0.65rem; letter-spacing: 4px; color: rgba(180,74,255,0.8);
        text-align: center; margin-bottom: 12px; text-transform: uppercase;
      }
      .sa-transcript {
        min-height: 22px; text-align: center;
        font-size: 0.95rem; color: #e2e8f0;
        margin-bottom: 6px; opacity: 0.85;
        transition: opacity 0.2s;
        padding: 0 8px;
      }
      .sa-response {
        min-height: 44px; text-align: center;
        font-size: 0.82rem; color: #94a3b8; line-height: 1.6;
        margin-bottom: 20px; max-height: 120px; overflow-y: auto;
        font-family: -apple-system, system-ui, sans-serif;
        padding: 0 8px;
      }
      .sa-controls {
        display: flex; justify-content: center; align-items: center;
        gap: 20px; margin-bottom: 20px;
      }
      .sa-btn {
        border: none; border-radius: 50%; cursor: pointer;
        transition: transform 0.15s, box-shadow 0.15s;
        display: flex; align-items: center; justify-content: center;
      }
      .sa-btn:active { transform: scale(0.88); }
      .sa-mic {
        width: 68px; height: 68px; padding: 18px;
        background: linear-gradient(135deg, #6c1fff, #b44aff);
        color: white;
        box-shadow: 0 4px 24px rgba(180,74,255,0.45);
      }
      .sa-mic svg { width: 100%; height: 100%; }
      .sa-action {
        width: 44px; height: 44px; padding: 10px;
        background: rgba(255,255,255,0.07); color: #94a3b8;
      }
      .sa-action svg { width: 100%; height: 100%; }
      .sa-chips {
        display: flex; flex-wrap: wrap; gap: 8px; justify-content: center;
        padding: 0 4px;
      }
      .sa-chip {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.6rem; letter-spacing: 1px; text-transform: uppercase;
        padding: 6px 14px; border-radius: 20px;
        background: rgba(180,74,255,0.08);
        border: 1px solid rgba(180,74,255,0.2);
        color: rgba(180,74,255,0.8); cursor: pointer;
        transition: background 0.15s, border-color 0.15s;
      }
      .sa-chip:active { background: rgba(180,74,255,0.2); }

      /* Settings */
      .sa-settings-title {
        font-size: 0.6rem; letter-spacing: 4px; color: rgba(180,74,255,0.7);
        text-align: center; margin-bottom: 24px;
      }
      .sa-field-label {
        font-size: 0.6rem; letter-spacing: 2px; color: #555;
        text-transform: uppercase; margin-bottom: 8px;
      }
      .sa-key-row {
        display: flex; gap: 8px; margin-bottom: 6px;
      }
      .sa-key-input {
        flex: 1; background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.1); border-radius: 6px;
        padding: 10px 14px; color: #e2e8f0;
        font-family: 'JetBrains Mono', monospace; font-size: 0.8rem;
        outline: none;
      }
      .sa-key-input:focus { border-color: rgba(180,74,255,0.4); }
      .sa-btn-small {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.55rem; letter-spacing: 1px; padding: 0 12px;
        background: transparent; border: 1px solid #333; color: #666;
        border-radius: 6px; cursor: pointer;
      }
      .sa-field-hint {
        font-size: 0.65rem; color: #444; margin-bottom: 20px; line-height: 1.5;
      }
      .sa-btn-primary {
        width: 100%; padding: 12px; border-radius: 8px; border: none;
        background: linear-gradient(135deg, #6c1fff, #b44aff);
        color: white; font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem; letter-spacing: 2px; cursor: pointer;
        margin-bottom: 10px;
      }
      .sa-btn-danger {
        width: 100%; padding: 10px; border-radius: 8px;
        background: transparent; border: 1px solid rgba(239,68,68,0.3);
        color: rgba(239,68,68,0.7); font-family: 'JetBrains Mono', monospace;
        font-size: 0.65rem; letter-spacing: 1px; cursor: pointer;
        margin-bottom: 10px;
      }
      .sa-btn-ghost {
        width: 100%; padding: 10px; border-radius: 8px;
        background: transparent; border: 1px solid #222;
        color: #555; font-family: 'JetBrains Mono', monospace;
        font-size: 0.65rem; cursor: pointer;
        margin-bottom: 16px;
      }
      .sa-key-status { font-size: 0.7rem; text-align: center; min-height: 20px; }
    `;

    document.head.appendChild(style);
    document.body.appendChild(el);
    overlay = el;

    if (apiKey) {
      document.getElementById('sa-key-input').value = apiKey;
    }
  }

  // ── State machine ─────────────────────────────────────────────────────────

  function setState(s) {
    state = s;
    const orb = document.getElementById('sa-orb');
    const statusEl = document.getElementById('sa-status');
    const micBtn = document.getElementById('sa-mic-btn');
    if (!orb || !statusEl) return;

    orb.className = 'sa-orb ' + s;
    const labels = {
      idle: 'SHADOW AI',
      listening: '// LISTENING',
      thinking: '// PROCESSING',
      speaking: '// SPEAKING',
    };
    statusEl.textContent = labels[s] || s.toUpperCase();

    if (micBtn) {
      micBtn.disabled = (s === 'thinking' || s === 'speaking');
      micBtn.style.opacity = micBtn.disabled ? '0.5' : '1';
    }
  }

  function show() {
    if (!overlay) buildOverlay();
    overlay.classList.add('active');
    document.getElementById('sa-main').style.display = '';
    document.getElementById('sa-settings').style.display = 'none';
    setState('idle');
    document.getElementById('sa-transcript').textContent = '';
    document.getElementById('sa-response').textContent = apiKey ? '' : '← Tap settings to add your API key';
    clearTimeout(_idleTimer);
    _idleTimer = setTimeout(() => { if (state === 'idle') dismiss(); }, 60000);
  }

  function dismiss() {
    if (overlay) overlay.classList.remove('active');
    if (plugin) plugin.stopListening().catch(() => {});
    if (plugin) plugin.stopSpeaking().catch(() => {});
    state = 'idle';
    conversationHistory = [];
    if (plugin?.finishActivity) plugin.finishActivity().catch(() => {});
    else if (window.ShadowBridge?.finishActivity) window.ShadowBridge.finishActivity();
  }

  function showSettings() {
    document.getElementById('sa-main').style.display = 'none';
    document.getElementById('sa-settings').style.display = '';
    if (apiKey) document.getElementById('sa-key-input').value = apiKey;
  }

  // ── Settings handlers ─────────────────────────────────────────────────────

  async function _saveApiKey() {
    const input = document.getElementById('sa-key-input').value.trim();
    if (!input || !input.startsWith('sc_')) {
      document.getElementById('sa-key-status').textContent = 'Invalid key — must start with sc_';
      document.getElementById('sa-key-status').style.color = '#ef4444';
      return;
    }
    document.getElementById('sa-key-status').textContent = 'Verifying...';
    document.getElementById('sa-key-status').style.color = '#94a3b8';
    try {
      const res = await fetch(`${API_BASE}/v1/me`, {
        headers: { Authorization: `Bearer ${input}` },
      });
      if (!res.ok) throw new Error('Key rejected');
      const me = await res.json();
      apiKey = input;
      if (plugin?.setApiKey) await plugin.setApiKey({ key: apiKey });
      else if (window.ShadowBridge?.setApiKey) window.ShadowBridge.setApiKey(apiKey);
      guardianCtx = { me, summary: null };
      loadGuardianContext().catch(() => {});
      document.getElementById('sa-key-status').textContent = `✓ Connected as ${me.email}`;
      document.getElementById('sa-key-status').style.color = '#22c55e';
      setTimeout(() => _closeSettings(), 1500);
    } catch (_) {
      document.getElementById('sa-key-status').textContent = 'Key invalid or API unreachable';
      document.getElementById('sa-key-status').style.color = '#ef4444';
    }
  }

  async function _clearApiKey() {
    apiKey = null;
    guardianCtx = null;
    if (plugin?.setApiKey) await plugin.setApiKey({ key: '' }).catch(() => {});
    else if (window.ShadowBridge?.setApiKey) window.ShadowBridge.setApiKey('');
    document.getElementById('sa-key-input').value = '';
    document.getElementById('sa-key-status').textContent = 'API key removed';
    document.getElementById('sa-key-status').style.color = '#94a3b8';
  }

  function _closeSettings() {
    document.getElementById('sa-main').style.display = '';
    document.getElementById('sa-settings').style.display = 'none';
    document.getElementById('sa-response').textContent = apiKey ? '' : '← Tap settings to add your API key';
  }

  function _toggleKeyVisibility() {
    const input = document.getElementById('sa-key-input');
    const btn = document.getElementById('sa-key-toggle');
    if (input.type === 'password') {
      input.type = 'text';
      btn.textContent = 'HIDE';
    } else {
      input.type = 'password';
      btn.textContent = 'SHOW';
    }
  }

  // ── Input handlers ────────────────────────────────────────────────────────

  async function handleAssistInvoke() {
    show();
    await loadGuardianContext();
    setTimeout(() => startListening(), 400);
  }

  function handlePartialResult(data) {
    const el = document.getElementById('sa-transcript');
    if (el) el.textContent = data.transcript + '…';
  }

  async function handleSpeechResult(data) {
    const transcript = data.transcript?.trim();
    if (!transcript) { setState('idle'); return; }

    document.getElementById('sa-transcript').textContent = `"${transcript}"`;
    setState('thinking');

    try {
      // Try direct command first
      let response = null;
      for (const cmd of COMMANDS) {
        if (cmd.pattern.test(transcript)) {
          response = await dispatchCommand(cmd.action);
          break;
        }
      }

      // Fall through to AI
      if (response === null) {
        response = await queryAI(transcript);
      }

      if (response) {
        document.getElementById('sa-response').textContent = response;
        setState('speaking');
        if (plugin) {
          await plugin.speak({ text: response, rate: 1.0 });
        }
        setState('idle');
        setTimeout(() => dismiss(), 3000);
      }
    } catch (e) {
      document.getElementById('sa-response').textContent = 'Could not reach Shadow AI.';
      setState('idle');
      setTimeout(() => dismiss(), 3000);
    }
  }

  function handleSpeechError(data) {
    const el = document.getElementById('sa-response');
    if (el) {
      const friendly = {
        'STT error 7': 'No speech detected. Try again.',
        'STT error 6': 'No match. Speak clearly.',
        'Microphone permission denied': 'Microphone access denied.',
      };
      el.textContent = friendly[data.message] || data.message;
    }
    setState('idle');
  }

  // ── System command intercept (no LLM needed) ──────────────────────────────

  const SYSTEM_INTENTS = [
    { pattern: /^(?:call|ring|phone)\s+(.+)/i, intent: 'dial', label: (m) => `Calling ${m[1]}…` },
    { pattern: /^(?:text|message|sms)\s+(.+?)\s+(?:saying?\s+)?(.+)/i, intent: 'sms', label: (m) => `Sending message to ${m[1]}…` },
    { pattern: /^(?:set\s+)?(?:an?\s+)?alarm\s+(?:for|at)?\s*(.+)/i, intent: 'alarm', label: (m) => `Setting alarm for ${m[1]}.` },
    { pattern: /^(?:set\s+)?(?:a\s+)?timer\s+(?:for)?\s*(.+)/i, intent: 'timer', label: (m) => `Timer started for ${m[1]}.` },
    { pattern: /^(?:open|launch|start)\s+(.+)/i, intent: 'open_app', label: (m) => `Opening ${m[1]}…` },
    { pattern: /^(?:navigate|directions?|take me|go)\s+to\s+(.+)/i, intent: 'maps', label: (m) => `Navigating to ${m[1]}…` },
  ];

  function trySystemIntent(text) {
    for (const si of SYSTEM_INTENTS) {
      const m = text.match(si.pattern);
      if (m) return { intent: si.intent, match: m, label: si.label(m) };
    }
    return null;
  }

  // ── AI query ──────────────────────────────────────────────────────────────

  async function queryAI(userText) {
    // Intercept phone OS actions before burning API quota
    const sys = trySystemIntent(userText);
    if (sys && plugin) {
      try {
        await plugin.launchIntent({ intent: sys.intent, args: Array.from(sys.match).slice(1) });
        return sys.label;
      } catch (_) { /* native intent not supported; fall through to AI */ }
    }

    conversationHistory.push({ role: 'user', content: userText });

    const headers = { 'Content-Type': 'application/json' };
    if (apiKey) headers['Authorization'] = `Bearer ${apiKey}`;

    const resp = await fetch(`${API_BASE}/v1/assistant/query`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ question: userText }),
    });

    if (!resp.ok) throw new Error(`API ${resp.status}`);
    const data = await resp.json();
    const reply = data.answer || 'No response.';
    conversationHistory.push({ role: 'assistant', content: reply });
    return reply;
  }

  // ── Public API ────────────────────────────────────────────────────────────

  async function startListening() {
    if (!plugin) return;
    setState('listening');
    document.getElementById('sa-transcript').textContent = '';

    try {
      const perm = await plugin.requestMicPermission();
      if (!perm.granted) {
        document.getElementById('sa-response').textContent = 'Microphone permission denied.';
        setState('idle');
        return;
      }
      await plugin.startListening();
    } catch (_) {
      setState('idle');
    }
  }

  function openSettings() {
    if (!overlay) buildOverlay();
    if (!overlay.classList.contains('active')) {
      overlay.classList.add('active');
    }
    showSettings();
  }

  async function _runChip(text) {
    document.getElementById('sa-transcript').textContent = `"${text}"`;
    setState('thinking');
    await loadGuardianContext();
    try {
      let response = null;
      for (const cmd of COMMANDS) {
        if (cmd.pattern.test(text)) {
          response = await dispatchCommand(cmd.action);
          break;
        }
      }
      if (response === null) response = await queryAI(text);
      if (response) {
        document.getElementById('sa-response').textContent = response;
        setState('speaking');
        if (plugin) await plugin.speak({ text: response, rate: 1.0 });
        setState('idle');
      }
    } catch (_) {
      document.getElementById('sa-response').textContent = 'Command failed.';
      setState('idle');
    }
  }

  function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

  return { init, show, dismiss, startListening, openSettings, _saveApiKey, _clearApiKey, _closeSettings, _toggleKeyVisibility, _runChip };
})();

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', ShadowAssistant.init);
} else {
  ShadowAssistant.init();
}

window.ShadowAssistant = ShadowAssistant;
