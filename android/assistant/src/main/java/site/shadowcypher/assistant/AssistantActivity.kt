package site.shadowcypher.assistant

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
import android.provider.AlarmClock
import android.provider.Settings
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.util.Log
import android.webkit.*
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import org.json.JSONArray
import org.json.JSONObject
import java.util.Locale
import java.util.concurrent.TimeUnit

class AssistantActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private var speechRecognizer: SpeechRecognizer? = null
    private var tts: TextToSpeech? = null
    private var ttsReady = false
    private var wasAssistLaunch = false

    companion object {
        private const val MIC_REQ = 1001
        private const val TAG = "ShadowAssistant"
        private const val PREFS = "shadow_prefs"
        private const val KEY_API = "sc_api_key"
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        wasAssistLaunch = intent?.action == Intent.ACTION_ASSIST ||
                          intent?.action == "android.intent.action.VOICE_ASSIST"

        window.setBackgroundDrawableResource(android.R.color.transparent)

        webView = WebView(this).apply {
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.allowFileAccess = true
            settings.mixedContentMode = WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
            addJavascriptInterface(ShadowBridge(), "ShadowBridge")
            webViewClient = object : WebViewClient() {
                override fun onPageFinished(view: WebView?, url: String?) = injectShim()
            }
            setBackgroundColor(0x00000000)
        }
        setContentView(webView)

        initTTS()
        initSTT()

        webView.loadUrl("file:///android_asset/index.html")
    }

    // ── Capacitor shim injected after page load ───────────────────────────────

    private fun injectShim() {
        val wasAssist = if (wasAssistLaunch) "true" else "false"
        val ttsOk = if (ttsReady) "true" else "false"
        val sttOk = if (SpeechRecognizer.isRecognitionAvailable(this)) "true" else "false"
        val js = """
(function() {
  var listeners = {};
  window._fireEvent = function(event, dataJson) {
    var cb = listeners[event];
    if (cb) cb(JSON.parse(dataJson));
  };
  var plugin = {
    startListening:      function() { ShadowBridge.startListening(); return Promise.resolve(); },
    stopListening:       function() { ShadowBridge.stopListening(); return Promise.resolve(); },
    stopSpeaking:        function() { ShadowBridge.stopSpeaking(); return Promise.resolve(); },
    openAssistSettings:  function() { ShadowBridge.openAssistSettings(); },
    finishActivity:      function() { ShadowBridge.finishActivity(); return Promise.resolve(); },
    getApiKey:    function() { return Promise.resolve(JSON.parse(ShadowBridge.getApiKey())); },
    setApiKey:    function(opts) { ShadowBridge.setApiKey(opts.key || ''); return Promise.resolve(); },
    launchIntent: function(opts) { return Promise.resolve(JSON.parse(ShadowBridge.launchIntent(JSON.stringify(opts)))); },
    speak: function(opts) {
      ShadowBridge.speak(opts.text || '', opts.rate || 1.0, opts.pitch || 1.0);
      return new Promise(function(resolve) {
        var prev = listeners['speakDone'];
        listeners['speakDone'] = function(d) { if (prev) prev(d); resolve(d); listeners['speakDone'] = prev; };
      });
    },
    requestMicPermission: function() {
      return new Promise(function(resolve) {
        window._micPermResolve = resolve;
        ShadowBridge.requestMicPermission();
      });
    },
    checkAssistStatus: function() {
      return Promise.resolve({ wasAssistLaunch: $wasAssist, ttsReady: $ttsOk, sttAvailable: $sttOk });
    },
    addListener: function(event, cb) {
      listeners[event] = cb;
      return { remove: function() { delete listeners[event]; } };
    }
  };
  window.Capacitor = {
    isNativePlatform: function() { return true; },
    Plugins: { ShadowAssistant: plugin }
  };
  console.log('[shim] Capacitor bridge ready');
})();
        """.trimIndent()
        webView.evaluateJavascript(js, null)
    }

    // ── JavascriptInterface ───────────────────────────────────────────────────

    inner class ShadowBridge {

        @JavascriptInterface
        fun startListening() {
            if (ContextCompat.checkSelfPermission(this@AssistantActivity, Manifest.permission.RECORD_AUDIO)
                    != PackageManager.PERMISSION_GRANTED) {
                fireEvent("speechError", mapOf("message" to "Microphone permission denied"))
                return
            }
            runOnUiThread {
                val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault())
                    putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
                    putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
                }
                speechRecognizer?.startListening(intent)
                fireEvent("listeningStarted", emptyMap())
            }
        }

        @JavascriptInterface
        fun stopListening() = runOnUiThread { speechRecognizer?.stopListening() }

        @JavascriptInterface
        fun speak(text: String, rate: Float, pitch: Float) {
            if (!ttsReady) { fireEvent("speakDone", mapOf("utteranceId" to "err")); return }
            val id = "sa_${System.currentTimeMillis()}"
            tts?.setSpeechRate(rate)
            tts?.setPitch(pitch)
            tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, id)
        }

        @JavascriptInterface
        fun stopSpeaking() = tts?.stop()

        @JavascriptInterface
        fun requestMicPermission() {
            if (ContextCompat.checkSelfPermission(this@AssistantActivity, Manifest.permission.RECORD_AUDIO)
                    == PackageManager.PERMISSION_GRANTED) {
                webView.post { webView.evaluateJavascript(
                    "if(window._micPermResolve){window._micPermResolve({granted:true});window._micPermResolve=null;}", null) }
            } else {
                ActivityCompat.requestPermissions(this@AssistantActivity,
                    arrayOf(Manifest.permission.RECORD_AUDIO), MIC_REQ)
            }
        }

        @JavascriptInterface
        fun openAssistSettings() {
            try {
                startActivity(Intent(Settings.ACTION_VOICE_INPUT_SETTINGS))
            } catch (e: Exception) {
                startActivity(Intent(Settings.ACTION_SETTINGS))
            }
        }

        @JavascriptInterface
        fun finishActivity() = runOnUiThread {
            tts?.stop()
            speechRecognizer?.stopListening()
            finishAndRemoveTask()
        }

        @JavascriptInterface
        fun getApiKey(): String {
            val key = getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY_API, "") ?: ""
            return "{\"key\":\"$key\"}"
        }

        @JavascriptInterface
        fun setApiKey(key: String) {
            getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                .edit().putString(KEY_API, key).apply()
        }

        @JavascriptInterface
        fun launchIntent(jsonStr: String): String {
            return try {
                val obj = JSONObject(jsonStr)
                val intent_type = obj.optString("intent", "")
                val args = obj.optJSONArray("args") ?: JSONArray()

                val launched = when (intent_type) {
                    "dial" -> {
                        val name = args.optString(0, "")
                        val i = Intent(Intent.ACTION_DIAL, Uri.parse("tel:$name"))
                        startActivity(i)
                        true
                    }
                    "sms" -> {
                        val contact = args.optString(0, "")
                        val msg = args.optString(1, "")
                        val i = Intent(Intent.ACTION_SENDTO, Uri.parse("smsto:$contact")).apply {
                            putExtra("sms_body", msg)
                        }
                        startActivity(i)
                        true
                    }
                    "alarm" -> {
                        val timeStr = args.optString(0, "")
                        val hourMin = parseTimeStr(timeStr)
                        val i = Intent(AlarmClock.ACTION_SET_ALARM).apply {
                            if (hourMin != null) {
                                putExtra(AlarmClock.EXTRA_HOUR, hourMin.first)
                                putExtra(AlarmClock.EXTRA_MINUTES, hourMin.second)
                            }
                            putExtra(AlarmClock.EXTRA_MESSAGE, "Shadow alarm")
                            putExtra(AlarmClock.EXTRA_SKIP_UI, hourMin != null)
                        }
                        startActivity(i)
                        true
                    }
                    "timer" -> {
                        val durStr = args.optString(0, "")
                        val seconds = parseDurationSeconds(durStr)
                        val i = Intent(AlarmClock.ACTION_SET_TIMER).apply {
                            if (seconds > 0) {
                                putExtra(AlarmClock.EXTRA_LENGTH, seconds)
                                putExtra(AlarmClock.EXTRA_SKIP_UI, true)
                            }
                        }
                        startActivity(i)
                        true
                    }
                    "maps" -> {
                        val dest = args.optString(0, "")
                        val i = Intent(Intent.ACTION_VIEW, Uri.parse("geo:0,0?q=${Uri.encode(dest)}"))
                        startActivity(i)
                        true
                    }
                    "open_app" -> {
                        val appName = args.optString(0, "").lowercase()
                        val pm = packageManager
                        val knownApps = mapOf(
                            "chrome" to "com.android.chrome",
                            "settings" to "com.android.settings",
                            "camera" to "com.android.camera2",
                            "photos" to "com.google.android.apps.photos",
                            "youtube" to "com.google.android.youtube",
                            "spotify" to "com.spotify.music",
                        )
                        val pkg = knownApps.entries.firstOrNull { appName.contains(it.key) }?.value
                        if (pkg != null) {
                            pm.getLaunchIntentForPackage(pkg)?.let { startActivity(it); true } ?: false
                        } else false
                    }
                    else -> false
                }
                "{\"ok\":$launched}"
            } catch (e: Exception) {
                "{\"ok\":false,\"error\":\"${e.message?.replace("\"","'")}\"}"
            }
        }

        private fun parseTimeStr(s: String): Pair<Int, Int>? {
            val m12 = Regex("""(\d{1,2})(?::(\d{2}))?\s*(am|pm)""", RegexOption.IGNORE_CASE).find(s)
            if (m12 != null) {
                var h = m12.groupValues[1].toIntOrNull() ?: return null
                val min = m12.groupValues[2].toIntOrNull() ?: 0
                val ampm = m12.groupValues[3].lowercase()
                if (ampm == "pm" && h < 12) h += 12
                if (ampm == "am" && h == 12) h = 0
                return Pair(h, min)
            }
            val m24 = Regex("""(\d{1,2}):(\d{2})""").find(s)
            if (m24 != null) {
                return Pair(m24.groupValues[1].toInt(), m24.groupValues[2].toInt())
            }
            return null
        }

        private fun parseDurationSeconds(s: String): Int {
            var total = 0
            Regex("""(\d+)\s*(hour|hr|h|minute|min|m|second|sec|s)s?""", RegexOption.IGNORE_CASE)
                .findAll(s).forEach { mr ->
                    val n = mr.groupValues[1].toIntOrNull() ?: 0
                    total += when (mr.groupValues[2].lowercase().first()) {
                        'h' -> n * 3600
                        'm' -> n * 60
                        else -> n
                    }
                }
            return total
        }
    }

    // ── STT setup ────────────────────────────────────────────────────────────

    private fun initSTT() {
        if (!SpeechRecognizer.isRecognitionAvailable(this)) return
        speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this).apply {
            setRecognitionListener(object : RecognitionListener {
                override fun onReadyForSpeech(p: Bundle?) = fireEvent("listeningStarted", emptyMap())
                override fun onBeginningOfSpeech() {}
                override fun onRmsChanged(v: Float) {}
                override fun onBufferReceived(b: ByteArray?) {}
                override fun onEndOfSpeech() = fireEvent("speechEnded", emptyMap())
                override fun onError(code: Int) = fireEvent("speechError", mapOf("message" to "STT error $code"))
                override fun onPartialResults(b: Bundle?) {
                    val t = b?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull() ?: return
                    fireEvent("partialResult", mapOf("transcript" to t))
                }
                override fun onResults(b: Bundle?) {
                    val t = b?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull() ?: return
                    fireEvent("speechResult", mapOf("transcript" to t))
                }
                override fun onEvent(type: Int, params: Bundle?) {}
            })
        }
    }

    // ── TTS setup ────────────────────────────────────────────────────────────

    private fun initTTS() {
        tts = TextToSpeech(this) { status ->
            ttsReady = status == TextToSpeech.SUCCESS
            if (ttsReady) {
                tts?.language = Locale.US
                tts?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                    override fun onStart(id: String?) {}
                    override fun onDone(id: String?) = fireEvent("speakDone", mapOf("utteranceId" to (id ?: "")))
                    @Deprecated("") override fun onError(id: String?) {}
                })
            }
        }
    }

    // ── Event helper ─────────────────────────────────────────────────────────

    private fun fireEvent(event: String, data: Map<String, Any>) {
        val json = JSONObject(data).toString().replace("\\", "\\\\").replace("'", "\\'")
        webView.post { webView.evaluateJavascript("window._fireEvent('$event','$json')", null) }
    }

    // ── Lifecycle ────────────────────────────────────────────────────────────

    override fun onRequestPermissionsResult(req: Int, perms: Array<String>, results: IntArray) {
        super.onRequestPermissionsResult(req, perms, results)
        if (req == MIC_REQ) {
            val granted = results.isNotEmpty() && results[0] == PackageManager.PERMISSION_GRANTED
            webView.post { webView.evaluateJavascript(
                "if(window._micPermResolve){window._micPermResolve({granted:$granted});window._micPermResolve=null;}", null) }
        }
    }

    override fun onNewIntent(intent: Intent?) {
        super.onNewIntent(intent)
        setIntent(intent)
        wasAssistLaunch = intent?.action == Intent.ACTION_ASSIST ||
                          intent?.action == "android.intent.action.VOICE_ASSIST"
        if (wasAssistLaunch) {
            webView.evaluateJavascript("if(window.ShadowAssistant)ShadowAssistant.show()", null)
            webView.evaluateJavascript("setTimeout(()=>ShadowAssistant.startListening(),400)", null)
        }
    }

    override fun onDestroy() {
        speechRecognizer?.destroy()
        tts?.shutdown()
        super.onDestroy()
    }
}
