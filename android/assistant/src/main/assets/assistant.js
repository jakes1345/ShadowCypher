/**
 * Shadow — ShadowCypher Voice Assistant
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
  let _lastTranscript = '';

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
    // ── Structured API commands (no LLM) ──
    {
      pattern: /\b(weather|temperature|forecast|raining|sunny|cloudy)\b.{0,40}(?:in|at|for)?\s+([a-zA-Z\s]+)|\b(?:in|at|for)\s+([a-zA-Z\s]{2,30})\b.{0,20}\b(weather|temperature|forecast)\b/i,
      action: 'weather',
    },
    {
      pattern: /\b(\d[\d,\.]*)\s+([A-Z]{3})\s+(?:to|in|into)\s+([A-Z]{3})\b|\bconvert\s+([A-Z]{3})\s+to\s+([A-Z]{3})\b|\bexchange rate\b/i,
      action: 'currency',
    },
    {
      pattern: /\b(CVE-\d{4}-\d+)\b|\blook ?up\s+(CVE-\d{4}-\d+)\b/i,
      action: 'cve_lookup',
    },
    {
      pattern: /\bcheck\s+((?:\d{1,3}\.){3}\d{1,3})\b|\bip\s+(?:rep(?:utation)?|abuse|malicious|safe)\b.*((?:\d{1,3}\.){3}\d{1,3})/i,
      action: 'ip_lookup',
    },
    {
      pattern: /\b(?:been|check|am i).{0,20}(?:breached|hacked|pwned|leaked|compromised)\b|\bhaveibeenpwned\b/i,
      action: 'breach_check',
    },
    {
      pattern: /\bdns\s+(?:lookup|check|resolve)\s+([a-zA-Z0-9\.\-]+)\b|\b(?:resolve|lookup)\s+([a-zA-Z0-9\.\-]+)\b/i,
      action: 'dns_lookup',
    },
    {
      pattern: /\b(?:search|google|look up|find|research).{0,10}(?:online|web|internet|for)\b|\bwhat(?:'s| is) (?:the latest|happening|going on)\b|\blatest news\b|\bwho (?:is|was|are)\b|\bwhen (?:is|was|did)\b/i,
      action: 'web_search',
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

      // Pre-load Guardian context + KB + classifier in background
      if (apiKey) loadGuardianContext().catch(() => {});
      loadKB().catch(() => {});
      if (typeof ShadowClassifier !== 'undefined') ShadowClassifier.load().catch(() => {});
      // Check OTA for updated KB/classifier assets (non-blocking)
      checkOtaUpdates().catch(() => {});

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
      'You are SHADOW, the personal voice assistant built into the ShadowCypher security platform.',
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

      case 'weather': {
        const transcript = _lastTranscript || '';
        // Extract city: look for "in <City>" or leading city names
        const cityMatch = transcript.match(/(?:in|at|for)\s+([A-Za-z][A-Za-z\s]{1,25}?)(?:\s*\?|$|\s+weather|\s+temp|\s+forecast)/i)
          || transcript.match(/^([A-Za-z][A-Za-z\s]{1,20}?)\s+(?:weather|temperature|forecast)/i);
        const city = cityMatch ? cityMatch[1].trim() : null;
        if (!city) return 'Which city do you want the weather for?';
        try {
          const r = await fetch(`${API_BASE}/v1/shadow/weather?q=${encodeURIComponent(city)}`, { headers });
          const d = await r.json();
          if (!r.ok || d.error) return `Could not get weather for ${city}.`;
          const c = d.current;
          return `${d.location.name}: ${c.temp_c}°C (${c.temp_f}°F), ${c.condition}. Humidity ${c.humidity_pct}%, wind ${c.wind_kph} km/h.`;
        } catch (_) { return 'Weather service unavailable.'; }
      }

      case 'currency': {
        const transcript = _lastTranscript || '';
        const m = transcript.match(/(\d[\d,\.]*)\s*([A-Za-z]{3})\s+(?:to|in|into)\s+([A-Za-z]{3})/i)
          || transcript.match(/convert\s+([A-Za-z]{3})\s+to\s+([A-Za-z]{3})/i);
        let amount = 1, from = 'USD', to = 'EUR';
        if (m) {
          if (m[1] && /\d/.test(m[1])) { amount = parseFloat(m[1].replace(/,/g, '')); from = (m[2] || 'USD').toUpperCase(); to = (m[3] || 'EUR').toUpperCase(); }
          else { from = (m[1] || 'USD').toUpperCase(); to = (m[2] || 'EUR').toUpperCase(); }
        }
        try {
          const r = await fetch(`${API_BASE}/v1/shadow/currency?from=${from}&to=${to}&amount=${amount}`, { headers });
          const d = await r.json();
          if (!r.ok || d.error) return `Could not convert ${from} to ${to}.`;
          return d.formatted + ` (rate as of ${d.date}).`;
        } catch (_) { return 'Currency service unavailable.'; }
      }

      case 'cve_lookup': {
        const transcript = _lastTranscript || '';
        const cveId = (transcript.match(/CVE-\d{4}-\d+/i) || [])[0];
        if (!cveId) return 'Which CVE do you want to look up?';
        try {
          const r = await fetch(`${API_BASE}/v1/shadow/cve?q=${cveId}`, { headers });
          const d = await r.json();
          if (!r.ok || !d.results?.length) return `${cveId} not found in NVD.`;
          const v = d.results[0];
          return `${v.id}: Score ${v.score ?? 'N/A'} (${v.severity ?? 'unknown'}). ${v.description}`;
        } catch (_) { return 'CVE lookup unavailable.'; }
      }

      case 'ip_lookup': {
        const transcript = _lastTranscript || '';
        const ipMatch = transcript.match(/((?:\d{1,3}\.){3}\d{1,3})/);
        const ip = ipMatch ? ipMatch[1] : null;
        if (!ip) return 'Which IP address do you want to check?';
        try {
          const r = await fetch(`${API_BASE}/v1/shadow/ip?addr=${ip}`, { headers });
          const d = await r.json();
          if (!r.ok || d.error) return `Could not check IP ${ip}.`;
          if (d.is_private) return `${ip} is a private/internal IP address.`;
          return `${ip}: Abuse score ${d.abuse_score}/100 (${d.risk_level}). ISP: ${d.isp}. Country: ${d.country}. Total reports: ${d.total_reports}.`;
        } catch (_) { return 'IP reputation service unavailable.'; }
      }

      case 'breach_check': {
        const email = guardianCtx?.me?.email;
        if (!email) return 'No account email found. Check your API key settings.';
        try {
          const r = await fetch(`${API_BASE}/v1/shadow/breach?email=${encodeURIComponent(email)}`, { headers });
          const d = await r.json();
          if (!r.ok) return 'Breach check unavailable.';
          if (!d.breached) return `Good news — ${email} has not appeared in any known data breaches.`;
          const top = d.breaches.slice(0, 3).map(b => b.title).join(', ');
          return `${email} was found in ${d.count} breach${d.count !== 1 ? 'es' : ''}. Most notable: ${top}.`;
        } catch (_) { return 'Breach check service unavailable.'; }
      }

      case 'dns_lookup': {
        const transcript = _lastTranscript || '';
        const domainMatch = transcript.match(/(?:dns|resolve|lookup)\s+([a-zA-Z0-9\.\-]+)/i)
          || transcript.match(/([a-zA-Z0-9\-]+\.[a-zA-Z]{2,})/);
        const domain = domainMatch ? domainMatch[1] : null;
        if (!domain) return 'Which domain do you want to look up?';
        try {
          const r = await fetch(`${API_BASE}/v1/shadow/dns?q=${encodeURIComponent(domain)}&type=A`, { headers });
          const d = await r.json();
          if (!r.ok || d.error) return `DNS lookup for ${domain} failed.`;
          if (!d.records.length) return `${domain} has no A records (status: ${d.status}).`;
          const ips = d.records.map(r => r.value).slice(0, 4).join(', ');
          return `${domain} resolves to: ${ips}.`;
        } catch (_) { return 'DNS lookup unavailable.'; }
      }

      case 'web_search':
        return await _doWebSearch(_lastTranscript || '');

      default:
        return null;
    }
  }

  async function _doWebSearch(query) {
    if (!apiKey) return 'Set your API key in settings to enable web search.';
    const headers = { Authorization: `Bearer ${apiKey}` };
    // Strip search trigger words to get the actual query
    const cleaned = query
      .replace(/\b(?:search(?:\s+the\s+web|\s+online|\s+for)?|google|look\s+up|find\s+(?:out|info(?:rmation)?\s+about)?|research)\s*/gi, '')
      .trim() || query;
    try {
      const r = await fetch(`${API_BASE}/v1/shadow/search?q=${encodeURIComponent(cleaned)}&limit=4`, { headers });
      const d = await r.json();
      if (!r.ok || !d.results?.length) {
        return `No results found for "${cleaned}".`;
      }
      // Feed results as context into AI for a natural spoken summary
      const ctx = d.results.map((res, i) => `[${i+1}] ${res.title}: ${res.snippet}`).join('\n');
      const prompt = `Based on these search results, give a 1-3 sentence spoken summary answering: "${cleaned}"\n\n${ctx}`;
      return await queryAI(prompt);
    } catch (_) { return 'Web search unavailable.'; }
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
          <div class="sa-orb-ring" id="sa-orb-ring">
            <div class="sa-orb" id="sa-orb"></div>
          </div>
          <div class="sa-status" id="sa-status">SHADOW</div>
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
          <!-- Text input fallback -->
          <div class="sa-text-row" id="sa-text-row">
            <input id="sa-text-input" class="sa-text-input" type="text" placeholder="Type a message…" autocomplete="off" spellcheck="false"/>
            <button class="sa-btn sa-send-btn" id="sa-send-btn" onclick="ShadowAssistant._submitText()">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
            </button>
          </div>
          <div class="sa-chips" id="sa-chips">
            <button class="sa-chip" onclick="ShadowAssistant._runChip('Scan my network')">Scan</button>
            <button class="sa-chip" onclick="ShadowAssistant._runChip('Any active incidents?')">Incidents</button>
            <button class="sa-chip" onclick="ShadowAssistant._runChip('Set a timer for 5 minutes')">Timer</button>
            <button class="sa-chip" onclick="ShadowAssistant._runChip('Weather in New York')">Weather</button>
          </div>
        </div>

        <!-- Settings view -->
        <div id="sa-settings" style="display:none">
          <div class="sa-handle"></div>
          <div class="sa-settings-title">SHADOW // SETTINGS</div>

          <!-- Hey Shadow toggle -->
          <div class="sa-field-label">Hey Shadow (Wake Word)</div>
          <div class="sa-toggle-row">
            <span class="sa-toggle-desc">Listen for "Hey Shadow" in background</span>
            <label class="sa-switch">
              <input type="checkbox" id="sa-wake-toggle" onchange="ShadowAssistant._toggleWakeWord(this.checked)"/>
              <span class="sa-slider"></span>
            </label>
          </div>
          <div class="sa-field-hint" id="sa-wake-hint">Requires microphone permission. Uses ~1% battery.</div>

          <div class="sa-field-label" style="margin-top:16px">ShadowCypher API Key</div>
          <div class="sa-key-row">
            <input id="sa-key-input" class="sa-key-input" type="password" placeholder="sc_live_..." autocomplete="off" spellcheck="false"/>
            <button class="sa-btn-small" id="sa-key-toggle" onclick="ShadowAssistant._toggleKeyVisibility()">SHOW</button>
          </div>
          <div class="sa-field-hint">Find your key under Account → API Key on shadowcypher.site</div>
          <button class="sa-btn-primary" onclick="ShadowAssistant._saveApiKey()">Save &amp; Connect</button>
          <button class="sa-btn-danger" id="sa-remove-key-btn" style="display:none" onclick="ShadowAssistant._clearApiKey()">Remove Key</button>

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
      /* Text input row */
      .sa-text-row {
        display: flex; gap: 8px; margin-bottom: 12px; padding: 0 4px;
      }
      .sa-text-input {
        flex: 1; background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.1); border-radius: 24px;
        padding: 10px 16px; color: #e2e8f0;
        font-family: -apple-system, system-ui, sans-serif; font-size: 0.9rem;
        outline: none;
      }
      .sa-text-input:focus { border-color: rgba(180,74,255,0.4); }
      .sa-send-btn {
        width: 40px; height: 40px; padding: 10px;
        background: linear-gradient(135deg, #6c1fff, #b44aff);
        border-radius: 50%; color: white; flex-shrink: 0;
        align-self: center;
      }
      .sa-send-btn svg { width: 100%; height: 100%; }
      /* Wake word toggle */
      .sa-toggle-row {
        display: flex; align-items: center; justify-content: space-between;
        margin-bottom: 6px;
      }
      .sa-toggle-desc { font-size: 0.75rem; color: #94a3b8; }
      .sa-switch { position: relative; display: inline-block; width: 44px; height: 24px; }
      .sa-switch input { opacity: 0; width: 0; height: 0; }
      .sa-slider {
        position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0;
        background: #333; border-radius: 24px; transition: 0.2s;
      }
      .sa-slider:before {
        position: absolute; content: '';
        height: 18px; width: 18px; left: 3px; bottom: 3px;
        background: white; border-radius: 50%; transition: 0.2s;
      }
      input:checked + .sa-slider { background: #6c1fff; }
      input:checked + .sa-slider:before { transform: translateX(20px); }
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

    // Enter key submits text input
    const textInput = document.getElementById('sa-text-input');
    if (textInput) {
      textInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { e.preventDefault(); _submitText(); }
      });
    }

    _syncSettingsView();
  }

  function _syncSettingsView() {
    const removeBtn = document.getElementById('sa-remove-key-btn');
    const keyInput = document.getElementById('sa-key-input');
    if (removeBtn) removeBtn.style.display = apiKey ? '' : 'none';
    if (keyInput && apiKey) keyInput.value = apiKey;
    // Sync wake word toggle
    const wakeToggle = document.getElementById('sa-wake-toggle');
    if (wakeToggle) {
      const enabled = localStorage.getItem('wake_word_enabled') === 'true';
      wakeToggle.checked = enabled;
    }
  }

  async function _toggleWakeWord(enabled) {
    localStorage.setItem('wake_word_enabled', enabled ? 'true' : 'false');
    const hint = document.getElementById('sa-wake-hint');
    if (enabled) {
      if (hint) hint.textContent = 'Starting "Hey Shadow" listener…';
      try {
        if (plugin?.requestMicPermission) {
          const perm = await plugin.requestMicPermission();
          if (!perm.granted) {
            document.getElementById('sa-wake-toggle').checked = false;
            localStorage.setItem('wake_word_enabled', 'false');
            if (hint) hint.textContent = 'Microphone permission required.';
            return;
          }
        }
        // Tell native to start the service via a launchIntent shim
        if (plugin?.launchIntent) {
          await plugin.launchIntent({ intent: 'wake_word_service', args: ['start'] });
        }
        if (hint) hint.textContent = 'Active — say "Hey Shadow" anytime.';
      } catch (e) {
        if (hint) hint.textContent = 'Could not start wake word service.';
      }
    } else {
      if (plugin?.launchIntent) {
        await plugin.launchIntent({ intent: 'wake_word_service', args: ['stop'] }).catch(() => {});
      }
      if (hint) hint.textContent = 'Disabled. Requires microphone permission. Uses ~1% battery.';
    }
  }

  async function _submitText() {
    const input = document.getElementById('sa-text-input');
    const text = input?.value?.trim();
    if (!text || state === 'thinking' || state === 'speaking') return;
    input.value = '';
    _lastTranscript = text;
    document.getElementById('sa-transcript').textContent = `"${text}"`;
    setState('thinking');
    try {
      let response = await route(text);
      if (response === null) response = await queryAI(text);
      else { addMemory('user', text); addMemory('assistant', response); }
      if (response) {
        document.getElementById('sa-response').textContent = response;
        setState('speaking');
        if (plugin) await plugin.speak({ text: response, rate: 1.05 });
        setState('idle');
        setTimeout(() => _animatedDismiss(), 3000);
      }
    } catch (_) {
      document.getElementById('sa-response').textContent = 'Command failed.';
      setState('idle');
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
      idle: 'SHADOW',
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

  function _animatedDismiss() {
    if (!overlay) return;
    const panel = overlay.querySelector('.sa-panel');
    if (panel) {
      panel.style.transition = 'transform 0.28s cubic-bezier(0.32,0.72,0,1), opacity 0.28s';
      panel.style.transform = 'translateY(100%)';
      panel.style.opacity = '0';
      setTimeout(() => dismiss(), 300);
    } else {
      dismiss();
    }
  }

  function dismiss() {
    if (overlay) {
      overlay.classList.remove('active');
      // Reset panel animation state for next open
      const panel = overlay.querySelector('.sa-panel');
      if (panel) { panel.style.transform = ''; panel.style.opacity = ''; panel.style.transition = ''; }
    }
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
    _syncSettingsView();
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
      _syncSettingsView();
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
    _syncSettingsView();
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

    _lastTranscript = transcript;
    document.getElementById('sa-transcript').textContent = `"${transcript}"`;
    setState('thinking');

    try {
      // Cascading router: OS → Classifier → KB → LLM
      let response = await route(transcript);
      if (response === null) {
        response = await queryAI(transcript);
      } else {
        addMemory('user', transcript);
        addMemory('assistant', response);
      }

      if (response) {
        document.getElementById('sa-response').textContent = response;
        setState('speaking');
        if (plugin) {
          await plugin.speak({ text: response, rate: 1.05 });
        }
        setState('idle');
        setTimeout(() => _animatedDismiss(), 2500);
      }
    } catch (e) {
      document.getElementById('sa-response').textContent = 'Could not reach Shadow.';
      setState('idle');
      setTimeout(() => _animatedDismiss(), 2500);
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

  // ── OTA update check ─────────────────────────────────────────────────────

  const OTA_URL = 'https://api.shadowcypher.site/v1/shadow/ota';
  const OTA_KEY = 'shadow_ota_seen_version';

  async function checkOtaUpdates() {
    try {
      const r = await fetch(OTA_URL, { cache: 'no-store' });
      if (!r.ok) return;
      const manifest = await r.json();
      const seenVersion = localStorage.getItem(OTA_KEY) || '0';
      if (manifest.version === seenVersion) return;

      console.log(`[OTA] New version ${manifest.version} (was ${seenVersion})`);

      // Fetch and cache updated KB chunks
      if (manifest.chunks_url) {
        const cr = await fetch(manifest.chunks_url);
        if (cr.ok) {
          const newChunks = await cr.json();
          // Reload in-memory KB
          _kbChunks = newChunks;
          _kbLoaded = true;
          console.log(`[OTA] KB updated: ${newChunks.length} chunks`);
        }
      }

      // Fetch and reload classifier if updated
      if (manifest.classifier_url && typeof ShadowClassifier !== 'undefined') {
        const xr = await fetch(manifest.classifier_url);
        if (xr.ok) {
          // Reload classifier by re-invoking load with fresh URL
          console.log('[OTA] Classifier update available — reload to apply');
          // Can't hot-swap ONNX models; just note it for next cold start
        }
      }

      localStorage.setItem(OTA_KEY, manifest.version);
      console.log(`[OTA] Updated to ${manifest.version}`);
    } catch (e) {
      console.debug('[OTA] Check failed (offline?):', e.message);
    }
  }

  // ── Knowledge base search (BM25 over chunks.json) ────────────────────────

  let _kbChunks = null;
  let _kbLoaded = false;

  async function loadKB() {
    if (_kbLoaded) return;
    _kbLoaded = true;
    try {
      const r = await fetch('chunks.json');
      if (r.ok) {
        _kbChunks = await r.json();
        console.log(`[KB] Loaded ${_kbChunks.length} chunks`);
      }
    } catch (_) { _kbChunks = null; }
  }

  function bm25Score(queryTokens, docTokens, avgLen, k1 = 1.5, b = 0.75) {
    const freq = {};
    for (const t of docTokens) freq[t] = (freq[t] || 0) + 1;
    const docLen = docTokens.length;
    let score = 0;
    for (const t of queryTokens) {
      if (!freq[t]) continue;
      const tf = freq[t];
      score += (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * docLen / avgLen));
    }
    return score;
  }

  function kbSearch(query, topK = 1) {
    if (!_kbChunks || !_kbChunks.length) return null;
    const qTokens = query.toLowerCase().match(/\b[a-z][a-z0-9\-\.]{0,}\b/g) || [];
    if (!qTokens.length) return null;
    const avgLen = _kbChunks.length > 0
      ? _kbChunks.reduce((s, c) => s + (c.bm25_tokens?.length || 0), 0) / _kbChunks.length
      : 1;
    const scored = _kbChunks.map(chunk => ({
      chunk,
      score: bm25Score(qTokens, chunk.bm25_tokens || [], avgLen),
    })).sort((a, b) => b.score - a.score);
    const best = scored[0];
    if (best.score < 0.5) return null; // not relevant enough
    return best.chunk;
  }

  // ── Cascading router ──────────────────────────────────────────────────────
  // Layer 1: OS intents (call/text/alarm/timer/open/maps)
  // Layer 2: Classifier → structured API commands
  // Layer 3: KB search (local knowledge)
  // Layer 4: LLM fallback (remote, costs quota)

  async function route(userText) {
    const headers = apiKey
      ? { 'Content-Type': 'application/json', Authorization: `Bearer ${apiKey}` }
      : { 'Content-Type': 'application/json' };

    // Layer 1: OS intents
    const sys = trySystemIntent(userText);
    if (sys && plugin) {
      try {
        await plugin.launchIntent({ intent: sys.intent, args: Array.from(sys.match).slice(1) });
        return sys.label;
      } catch (_) {}
    }

    // Layer 2: Classifier → dispatch to command handler
    let classifierIntent = null;
    if (typeof ShadowClassifier !== 'undefined' && ShadowClassifier.isReady()) {
      const result = ShadowClassifier.classify(userText);
      if (result.intent && result.intent !== 'unknown' && result.confidence >= 0.45) {
        classifierIntent = result.intent;
      }
    } else {
      // Regex fallback while classifier is loading
      for (const cmd of COMMANDS) {
        if (cmd.pattern.test(userText)) {
          classifierIntent = cmd.action;
          break;
        }
      }
    }

    if (classifierIntent) {
      const resp = await dispatchCommand(classifierIntent);
      if (resp !== null) return resp;
    }

    // Layer 3: KB search
    await loadKB();
    const chunk = kbSearch(userText);
    if (chunk) {
      // Return the relevant chunk text, trimmed for speech
      const text = chunk.text.replace(/[#*`\[\]]/g, '').replace(/\n+/g, ' ').trim();
      const snippet = text.slice(0, 350);
      return snippet + (text.length > 350 ? '…' : '');
    }

    // Layer 3.5: Web search — auto-triggered for current-events / factual queries not in KB
    if (apiKey && _looksLikeWebQuery(userText)) {
      const webResp = await _doWebSearch(userText).catch(() => null);
      if (webResp && webResp !== 'Web search unavailable.') return webResp;
    }

    // Layer 4: LLM
    return null; // caller falls through to queryAI
  }

  function _looksLikeWebQuery(text) {
    return /\b(?:latest|current|today|recent|news|2024|2025|2026|who is|what is|when (?:is|was|did)|how do I|price of|stock|score)\b/i.test(text);
  }

  // ── Conversational memory ────────────────────────────────────────────────
  // Last 5 turns for context continuity

  const MAX_MEMORY = 5;
  function addMemory(role, content) {
    conversationHistory.push({ role, content });
    if (conversationHistory.length > MAX_MEMORY * 2) {
      conversationHistory = conversationHistory.slice(-MAX_MEMORY * 2);
    }
  }

  // ── AI query — cloud assistant (Claude Haiku) ─────────────────────────────

  async function queryAI(userText) {
    addMemory('user', userText);

    if (!apiKey) {
      return 'Set your ShadowCypher API key in settings to enable AI responses.';
    }

    try {
      const headers = { 'Content-Type': 'application/json', 'Authorization': `Bearer ${apiKey}` };
      // Build payload: send full conversation history for multi-turn context
      // and inject guardian context into system prompt
      const payload = {
        question: userText,
        history: conversationHistory.slice(-8), // last 4 turns (user+assistant pairs)
        system: buildSystemPrompt(),
      };
      const resp = await fetch(`${API_BASE}/v1/assistant/query`, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload),
      });
      if (!resp.ok) {
        if (resp.status === 402) return 'Monthly AI query limit reached. Upgrade to Operator for 5000 queries/month.';
        throw new Error(`API ${resp.status}`);
      }
      const data = await resp.json();
      const reply = data.answer || 'No response.';
      addMemory('assistant', reply);
      return reply;
    } catch (e) {
      throw new Error(`Cloud query failed: ${e.message}`);
    }
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
    _lastTranscript = text;
    document.getElementById('sa-transcript').textContent = `"${text}"`;
    setState('thinking');
    await loadGuardianContext();
    try {
      let response = await route(text);
      if (response === null) response = await queryAI(text);
      else { addMemory('user', text); addMemory('assistant', response); }
      if (response) {
        document.getElementById('sa-response').textContent = response;
        setState('speaking');
        if (plugin) await plugin.speak({ text: response, rate: 1.05 });
        setState('idle');
        setTimeout(() => _animatedDismiss(), 2500);
      }
    } catch (_) {
      document.getElementById('sa-response').textContent = 'Command failed.';
      setState('idle');
    }
  }

  function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

  return { init, show, dismiss, startListening, openSettings,
           _saveApiKey, _clearApiKey, _closeSettings, _toggleKeyVisibility,
           _runChip, _submitText, _toggleWakeWord };
})();

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', ShadowAssistant.init);
} else {
  ShadowAssistant.init();
}

Object.defineProperty(window, 'ShadowAssistant', {
  value: ShadowAssistant,
  writable: false,
  configurable: false,
  enumerable: true
});
