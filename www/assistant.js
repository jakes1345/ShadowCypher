/**
 * ShadowCypher Device Assistant
 * Bridges the Android ShadowAssistantPlugin to the web UI.
 * Activated when user sets ShadowCypher as their default Assist app
 * and triggers it via long-press Home / squeeze / hotkey.
 */

const ShadowAssistant = (() => {
  let plugin = null;
  let overlay = null;
  let state = 'idle'; // idle | listening | thinking | speaking
  let conversationHistory = [];

  const API_BASE = 'https://shadowcypher-api.jacksnewaccount12.workers.dev';

  // ── Bootstrap ──────────────────────────────────────────────────────────────

  async function init() {
    // Only activate on Android inside Capacitor
    if (!window.Capacitor || !window.Capacitor.isNativePlatform()) return;

    try {
      // Capacitor 8 exposes plugins at window.Capacitor.Plugins after native bridge loads
      // Wait up to 3s for the bridge to be ready
      for (let i = 0; i < 30; i++) {
        plugin = window.Capacitor?.Plugins?.ShadowAssistant;
        if (plugin) break;
        await new Promise(r => setTimeout(r, 100));
      }
      if (!plugin) {
        console.warn('[ShadowAssistant] Plugin not available (non-Android or bridge not loaded)');
        return;
      }

      // Listen for assistant invocation from the native side
      plugin.addListener('assistInvoked', handleAssistInvoke);
      plugin.addListener('speechResult', handleSpeechResult);
      plugin.addListener('partialResult', handlePartialResult);
      plugin.addListener('speechError', handleSpeechError);
      plugin.addListener('listeningStarted', () => setState('listening'));
      plugin.addListener('speechEnded', () => {
        if (state === 'listening') setState('thinking');
      });

      buildOverlay();

      // Check if app was launched via ASSIST intent
      const status = await plugin.checkAssistStatus();
      if (status.wasAssistLaunch) handleAssistInvoke({ source: 'launch' });

      console.log('[ShadowAssistant] Ready. STT:', status.sttAvailable, 'TTS:', status.ttsReady);
    } catch (e) {
      console.warn('[ShadowAssistant] Init failed:', e);
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
        <div class="sa-orb-ring">
          <div class="sa-orb" id="sa-orb"></div>
        </div>
        <div class="sa-status" id="sa-status">SHADOW AI — Ready</div>
        <div class="sa-transcript" id="sa-transcript"></div>
        <div class="sa-response" id="sa-response"></div>
        <div class="sa-controls">
          <button class="sa-btn sa-mic" id="sa-mic-btn" onclick="ShadowAssistant.startListening()">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
              <path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v4M8 23h8"/>
            </svg>
          </button>
          <button class="sa-btn sa-dismiss" onclick="ShadowAssistant.dismiss()">✕</button>
        </div>
        <div class="sa-tip">Long-press Home → ShadowCypher to invoke</div>
      </div>
    `;

    const style = document.createElement('style');
    style.textContent = `
      #shadow-assistant-overlay {
        position: fixed; inset: 0; z-index: 99999;
        display: none; align-items: flex-end; justify-content: center;
        font-family: 'JetBrains Mono', monospace;
      }
      #shadow-assistant-overlay.active { display: flex; }
      .sa-backdrop {
        position: absolute; inset: 0;
        background: rgba(0,0,0,0.75); backdrop-filter: blur(4px);
      }
      .sa-panel {
        position: relative; z-index: 1;
        background: linear-gradient(180deg, #0d0d1a 0%, #050510 100%);
        border: 1px solid rgba(180,74,255,0.3);
        border-bottom: none;
        border-radius: 24px 24px 0 0;
        padding: 32px 24px 40px;
        width: 100%; max-width: 480px;
        text-align: center;
        box-shadow: 0 -8px 60px rgba(180,74,255,0.15);
      }
      .sa-orb-ring {
        width: 96px; height: 96px; border-radius: 50%;
        border: 2px solid rgba(180,74,255,0.4);
        display: flex; align-items: center; justify-content: center;
        margin: 0 auto 20px;
        animation: sa-ring-pulse 2s ease-in-out infinite;
      }
      .sa-orb {
        width: 72px; height: 72px; border-radius: 50%;
        background: radial-gradient(circle at 35% 35%, #c77dff, #7b2ff7);
        box-shadow: 0 0 30px rgba(180,74,255,0.5);
        transition: transform 0.15s ease;
      }
      .sa-orb.listening { animation: sa-orb-pulse 0.6s ease-in-out infinite alternate; }
      .sa-orb.thinking {
        background: radial-gradient(circle at 35% 35%, #00ffcc, #0080ff);
        animation: sa-orb-think 1.2s ease-in-out infinite;
      }
      .sa-orb.speaking { animation: sa-orb-speak 0.3s ease-in-out infinite alternate; }
      @keyframes sa-ring-pulse {
        0%,100% { border-color: rgba(180,74,255,0.3); }
        50% { border-color: rgba(180,74,255,0.7); }
      }
      @keyframes sa-orb-pulse {
        from { transform: scale(0.92); box-shadow: 0 0 20px rgba(180,74,255,0.4); }
        to   { transform: scale(1.08); box-shadow: 0 0 50px rgba(180,74,255,0.8); }
      }
      @keyframes sa-orb-think {
        0%,100% { transform: scale(1) rotate(0deg); }
        50% { transform: scale(0.95) rotate(180deg); }
      }
      @keyframes sa-orb-speak {
        from { transform: scaleY(0.9); }
        to   { transform: scaleY(1.1); }
      }
      .sa-status {
        font-size: 0.7rem; letter-spacing: 3px; color: #b44aff;
        margin-bottom: 16px; text-transform: uppercase;
      }
      .sa-transcript {
        min-height: 24px; font-size: 0.9rem; color: #e2e8f0;
        margin-bottom: 8px; opacity: 0.85;
        transition: opacity 0.3s;
      }
      .sa-response {
        min-height: 48px; font-size: 0.85rem; color: #94a3b8;
        line-height: 1.5; margin-bottom: 24px;
        max-height: 150px; overflow-y: auto;
      }
      .sa-controls { display: flex; justify-content: center; gap: 16px; margin-bottom: 16px; }
      .sa-btn {
        border: none; border-radius: 50%; cursor: pointer;
        transition: transform 0.15s, box-shadow 0.15s;
      }
      .sa-mic {
        width: 64px; height: 64px; padding: 16px;
        background: linear-gradient(135deg, #7b2ff7, #b44aff);
        color: white;
        box-shadow: 0 4px 20px rgba(180,74,255,0.4);
      }
      .sa-mic:active { transform: scale(0.92); }
      .sa-mic svg { width: 100%; height: 100%; }
      .sa-dismiss {
        width: 40px; height: 40px; font-size: 1rem;
        background: rgba(255,255,255,0.08); color: #94a3b8;
        align-self: center;
      }
      .sa-tip { font-size: 0.65rem; color: #475569; letter-spacing: 1px; }
    `;

    document.head.appendChild(style);
    document.body.appendChild(el);
    overlay = el;
  }

  function setState(s) {
    state = s;
    const orb = document.getElementById('sa-orb');
    const statusEl = document.getElementById('sa-status');
    if (!orb || !statusEl) return;

    orb.className = 'sa-orb ' + s;
    const labels = {
      idle: 'SHADOW AI — Ready',
      listening: '// LISTENING...',
      thinking: '// PROCESSING...',
      speaking: '// RESPONDING...',
    };
    statusEl.textContent = labels[s] || s.toUpperCase();
  }

  function show() {
    if (!overlay) buildOverlay();
    overlay.classList.add('active');
    setState('idle');
    document.getElementById('sa-transcript').textContent = '';
    document.getElementById('sa-response').textContent = '';
  }

  function dismiss() {
    if (overlay) overlay.classList.remove('active');
    if (plugin) plugin.stopListening().catch(() => {});
    if (plugin) plugin.stopSpeaking().catch(() => {});
    state = 'idle';
    conversationHistory = [];
  }

  // ── Handlers ──────────────────────────────────────────────────────────────

  async function handleAssistInvoke(data) {
    show();
    // Auto-start listening after a short delay for UX
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
      const response = await queryAI(transcript);
      document.getElementById('sa-response').textContent = response;
      setState('speaking');
      if (plugin) {
        await plugin.speak({ text: response, rate: 1.05 });
        setState('idle');
      }
    } catch (e) {
      document.getElementById('sa-response').textContent = 'Failed to reach ShadowCypher AI.';
      setState('idle');
    }
  }

  function handleSpeechError(data) {
    const el = document.getElementById('sa-response');
    if (el) el.textContent = `Error: ${data.message}`;
    setState('idle');
  }

  // ── AI Query ──────────────────────────────────────────────────────────────

  async function queryAI(userText) {
    conversationHistory.push({ role: 'user', content: userText });

    // Keep last 6 turns to stay within context limits
    const messages = conversationHistory.slice(-6);

    const resp = await fetch(`${API_BASE}/ai/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages,
        model: 'shadowcypher-ai',
        system: 'You are SHADOW AI, a concise voice assistant. Reply in 1-3 short sentences suitable for speech. No markdown, no bullet points, no code blocks in voice responses.',
        max_tokens: 200,
      }),
    });

    if (!resp.ok) throw new Error(`API ${resp.status}`);
    const data = await resp.json();
    const reply = data.content || data.choices?.[0]?.message?.content || 'No response.';

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
    } catch (e) {
      setState('idle');
    }
  }

  function openSettings() {
    if (plugin) plugin.openAssistSettings();
  }

  return { init, show, dismiss, startListening, openSettings };
})();

// Auto-init when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', ShadowAssistant.init);
} else {
  ShadowAssistant.init();
}

window.ShadowAssistant = ShadowAssistant;
