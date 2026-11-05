package site.shadowcypher.assistant

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.provider.Settings
import android.view.View
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import kotlinx.coroutines.*
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

class SettingsActivity : AppCompatActivity() {

    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())
    private lateinit var assistStatus: TextView

    companion object {
        private const val PREFS = "shadow_prefs"
        private const val KEY_API = "sc_api_key"
        private const val KEY_WAKE = "wake_word_enabled"
        private const val KEY_PENDING_DEVICE = "signin_pending_device_code"
        private const val KEY_PENDING_CODE = "signin_pending_user_code"
        private const val KEY_PENDING_UNTIL = "signin_pending_until"
        private const val KEY_PENDING_INTERVAL = "signin_pending_interval"
        private const val API_BASE = "https://api.shadowcypher.site"
        private const val CONNECTED_TEXT = "Connected. Long-press Home or the power button, or say 'Hey Shadow'."
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val prefs = getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val storedKey = prefs.getString(KEY_API, "") ?: ""

        val root = buildUI(storedKey, prefs)
        setContentView(root)
    }

    private fun buildUI(storedKey: String, prefs: android.content.SharedPreferences): View {
        val scroll = ScrollView(this).apply {
            setBackgroundColor(0xFF0A0A14.toInt())
        }

        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(56, 80, 56, 80)
        }

        // Header
        val header = TextView(this).apply {
            text = "SHADOW AI"
            textSize = 28f
            setTextColor(0xFFE2E8F0.toInt())
            typeface = android.graphics.Typeface.DEFAULT_BOLD
            letterSpacing = 0.15f
        }
        val sub = TextView(this).apply {
            text = "Your sovereign voice assistant"
            textSize = 13f
            setTextColor(0xFF6B7280.toInt())
            setPadding(0, 8, 0, 48)
        }

        // Status card
        val statusCard = buildCard()
        val statusTitle = TextView(this).apply {
            text = if (storedKey.isNotEmpty()) "● CONNECTED" else "● NOT CONFIGURED"
            textSize = 11f
            setTextColor(if (storedKey.isNotEmpty()) 0xFF22C55E.toInt() else 0xFFEF4444.toInt())
            letterSpacing = 0.1f
        }
        val statusDesc = TextView(this).apply {
            text = if (storedKey.isNotEmpty())
                CONNECTED_TEXT
            else
                "Sign in below to connect Shadow to your ShadowCypher account."
            textSize = 13f
            setTextColor(0xFF94A3B8.toInt())
            setPadding(0, 8, 0, 0)
        }
        statusCard.addView(statusTitle)
        statusCard.addView(statusDesc)

        // API Key section
        val keyLabel = sectionLabel("OR PASTE AN API KEY")
        val keyInput = EditText(this).apply {
            hint = "sc_live_..."
            setText(storedKey)
            setHintTextColor(0xFF374151.toInt())
            setTextColor(0xFFE2E8F0.toInt())
            textSize = 14f
            inputType = android.text.InputType.TYPE_CLASS_TEXT or android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD
            background = ContextCompat.getDrawable(context, android.R.color.transparent)
            setPadding(32, 28, 32, 28)
            val border = android.graphics.drawable.GradientDrawable().apply {
                setColor(0xFF0F0F1F.toInt())
                setStroke(1, 0xFF1F1F3A.toInt())
                cornerRadius = 12f
            }
            background = border
        }

        val keyStatus = TextView(this).apply {
            textSize = 12f
            setTextColor(0xFF6B7280.toInt())
            setPadding(4, 8, 0, 0)
            text = "Get your key at shadowcypher.site → Account → API Key"
        }

        // Browser sign-in (device flow)
        val signInLabel = sectionLabel("SIGN IN")
        val signInBtn = primaryButton("Sign in with browser")
        val signInStatus = TextView(this).apply {
            textSize = 13f
            setTextColor(0xFF94A3B8.toInt())
            setPadding(4, 8, 0, 0)
            text = "Approve this phone on shadowcypher.site. Your password never goes through this app."
        }
        signInStatusView = signInStatus
        onSignedIn = { key, email ->
            prefs.edit().putString(KEY_API, key).apply()
            keyInput.setText(key)
            signInStatus.text = "✓ Signed in as $email"
            signInStatus.setTextColor(0xFF22C55E.toInt())
            statusTitle.text = "● CONNECTED"
            statusTitle.setTextColor(0xFF22C55E.toInt())
            statusDesc.text = CONNECTED_TEXT
        }
        signInBtn.setOnClickListener {
            signInBtn.isEnabled = false
            signInStatus.setTextColor(0xFF94A3B8.toInt())
            signInStatus.text = "Starting…"
            scope.launch {
                if (startBrowserSignIn(signInStatus)) resumePendingSignIn()
                signInBtn.isEnabled = true
            }
        }

        // AI provider: Community accounts need their own Anthropic key or Ollama server
        val aiLabel = sectionLabel("AI MODEL")
        val aiDesc = TextView(this).apply {
            text = "On the Community plan, Shadow answers with your own Anthropic API key or your own Ollama server. Set one on shadowcypher.site → Account → Shadow AI."
            textSize = 13f
            setTextColor(0xFF94A3B8.toInt())
            setPadding(4, 0, 0, 12)
        }
        val aiBtn = ghostButton("Open AI settings on shadowcypher.site")
        aiBtn.setOnClickListener {
            try { startActivity(Intent(Intent.ACTION_VIEW, android.net.Uri.parse("https://shadowcypher.site/?nav=account"))) }
            catch (_: Exception) {}
        }

        val saveBtn = primaryButton("Save & Connect")
        saveBtn.setOnClickListener {
            val key = keyInput.text.toString().trim()
            if (!key.startsWith("sc_live_")) {
                keyStatus.text = "Invalid key — must start with sc_live_"
                keyStatus.setTextColor(0xFFEF4444.toInt())
                return@setOnClickListener
            }
            keyStatus.text = "Verifying..."
            keyStatus.setTextColor(0xFF94A3B8.toInt())
            saveBtn.isEnabled = false

            scope.launch {
                val result = withContext(Dispatchers.IO) { verifyKey(key) }
                saveBtn.isEnabled = true
                if (result != null) {
                    prefs.edit().putString(KEY_API, key).apply()
                    keyStatus.text = "✓ Connected as ${result}"
                    keyStatus.setTextColor(0xFF22C55E.toInt())
                    statusTitle.text = "● CONNECTED"
                    statusTitle.setTextColor(0xFF22C55E.toInt())
                    statusDesc.text = CONNECTED_TEXT
                } else {
                    keyStatus.text = "Key invalid or API unreachable"
                    keyStatus.setTextColor(0xFFEF4444.toInt())
                }
            }
        }

        // Wake word section
        val wakeLabel = sectionLabel("WAKE WORD")
        val wakeRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = android.view.Gravity.CENTER_VERTICAL
        }
        val wakeDesc = TextView(this).apply {
            text = "\"Hey Shadow\" — listen in background"
            textSize = 13f
            setTextColor(0xFF94A3B8.toInt())
            layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
        }
        val wakeToggle = Switch(this).apply {
            isChecked = prefs.getBoolean(KEY_WAKE, false)
            thumbTintList = android.content.res.ColorStateList.valueOf(0xFFB44AFF.toInt())
            trackTintList = android.content.res.ColorStateList.valueOf(0xFF2A1A4A.toInt())
        }
        wakeToggle.setOnCheckedChangeListener { _, checked ->
            prefs.edit().putBoolean(KEY_WAKE, checked).apply()
            if (checked) WakeWordService.start(this)
            else WakeWordService.stop(this)
        }
        wakeRow.addView(wakeDesc)
        wakeRow.addView(wakeToggle)

        // Set as default assist
        val assistLabel = sectionLabel("DEFAULT ASSISTANT")
        assistStatus = TextView(this).apply {
            textSize = 13f
            setPadding(4, 0, 0, 12)
        }
        val assistBtn = ghostButton("Choose digital assistant app")
        assistBtn.setOnClickListener {
            try { startActivity(Intent(Settings.ACTION_VOICE_INPUT_SETTINGS)) }
            catch (e: Exception) { startActivity(Intent(Settings.ACTION_SETTINGS)) }
        }

        // Launch assistant button
        val launchBtn = primaryButton("Open Shadow")
        launchBtn.setOnClickListener {
            startActivity(Intent(this, AssistantActivity::class.java).apply {
                action = Intent.ACTION_ASSIST
            })
        }

        listOf(header, sub, statusCard,
            assistLabel, assistStatus, assistBtn, sectionSpacer(),
            signInLabel, signInBtn, signInStatus, sectionSpacer(),
            keyLabel, keyInput, keyStatus, sectionSpacer(), saveBtn, sectionSpacer(),
            aiLabel, aiDesc, aiBtn, sectionSpacer(),
            wakeLabel, wakeRow, sectionSpacer(),
            launchBtn
        ).forEach { layout.addView(it) }
        updateAssistStatus()

        scroll.addView(layout)
        return scroll
    }

    private fun buildCard(): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        val bg = android.graphics.drawable.GradientDrawable().apply {
            setColor(0xFF0F0F1F.toInt())
            setStroke(1, 0xFF1F1F3A.toInt())
            cornerRadius = 16f
        }
        background = bg
        setPadding(32, 28, 32, 28)
        (layoutParams ?: LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.WRAP_CONTENT
        )).also {
            (it as LinearLayout.LayoutParams).bottomMargin = 32
            layoutParams = it
        }
    }

    private fun sectionLabel(text: String): TextView = TextView(this).apply {
        this.text = text
        textSize = 10f
        letterSpacing = 0.15f
        setTextColor(0xFF4B5563.toInt())
        setPadding(4, 32, 0, 12)
    }

    private fun sectionSpacer(): View = View(this).apply {
        layoutParams = LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, 16
        )
    }

    private fun primaryButton(label: String): Button = Button(this).apply {
        text = label
        textSize = 13f
        letterSpacing = 0.05f
        setTextColor(0xFFFFFFFF.toInt())
        val bg = android.graphics.drawable.GradientDrawable().apply {
            setColor(0xFF6C1FFF.toInt())
            cornerRadius = 12f
        }
        background = bg
        layoutParams = LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, 128
        ).also { it.bottomMargin = 8 }
        isAllCaps = false
        stateListAnimator = null
    }

    private fun ghostButton(label: String): Button = Button(this).apply {
        text = label
        textSize = 13f
        setTextColor(0xFF94A3B8.toInt())
        val bg = android.graphics.drawable.GradientDrawable().apply {
            setColor(android.graphics.Color.TRANSPARENT)
            setStroke(1, 0xFF1F2937.toInt())
            cornerRadius = 12f
        }
        background = bg
        layoutParams = LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, 112
        )
        isAllCaps = false
        stateListAnimator = null
    }

    private fun verifyKey(key: String): String? {
        return try {
            val url = URL("$API_BASE/v1/me")
            val conn = url.openConnection() as HttpURLConnection
            conn.setRequestProperty("Authorization", "Bearer $key")
            conn.connectTimeout = 8000
            conn.readTimeout = 8000
            if (conn.responseCode != 200) return null
            val body = conn.inputStream.bufferedReader().readText()
            JSONObject(body).optString("email", null)
        } catch (e: Exception) { null }
    }

    override fun onResume() {
        super.onResume()
        if (::assistStatus.isInitialized) updateAssistStatus()
        // Coming back from the browser (or after Android recreated this screen):
        // pick up a sign-in that's still waiting for approval.
        resumePendingSignIn()
    }

    /** Shows whether Shadow currently holds the digital assistant role. */
    private fun updateAssistStatus() {
        val held = if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.Q) {
            val rm = getSystemService(android.app.role.RoleManager::class.java)
            rm?.isRoleHeld(android.app.role.RoleManager.ROLE_ASSISTANT) == true
        } else {
            Settings.Secure.getString(contentResolver, "assistant")?.startsWith(packageName) == true
        }
        assistStatus.text = if (held) "✓ Shadow is your digital assistant. Long-press Home or the power button to talk."
            else "Shadow isn't your digital assistant yet. Tap below, choose 'Digital assistant app', then pick Shadow."
        assistStatus.setTextColor(if (held) 0xFF22C55E.toInt() else 0xFFF59E0B.toInt())
    }

    // ── Browser sign-in (device flow, same as the desktop app) ──────────────
    // The pending code is saved, so approval still lands if Android closes this
    // screen while the user is in the browser.

    private var signInStatusView: TextView? = null
    private var onSignedIn: ((String, String) -> Unit)? = null
    private var pollJob: Job? = null

    /** Gets a code, saves it as pending and opens the approval page. */
    private suspend fun startBrowserSignIn(status: TextView): Boolean {
        val start = withContext(Dispatchers.IO) {
            postJson("/v1/auth/device", JSONObject().put("client_label", "Shadow AI (Android)"))
        }
        if (start == null || start.second != 200) {
            status.text = "Couldn't reach ShadowCypher. Check your connection and try again."
            status.setTextColor(0xFFEF4444.toInt())
            return false
        }
        val s = start.first
        pollJob?.cancel()
        getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
            .putString(KEY_PENDING_DEVICE, s.optString("device_code"))
            .putString(KEY_PENDING_CODE, s.optString("user_code"))
            .putLong(KEY_PENDING_UNTIL, System.currentTimeMillis() + s.optInt("expires_in", 600) * 1000L)
            .putInt(KEY_PENDING_INTERVAL, s.optInt("interval", 5).coerceAtLeast(2))
            .apply()
        status.text = "Approve this phone in your browser. Code: ${s.optString("user_code")}"
        val url = s.optString("verification_uri_complete").ifBlank { s.optString("verification_uri") }
        try { startActivity(Intent(Intent.ACTION_VIEW, android.net.Uri.parse(url))) } catch (_: Exception) {}
        return true
    }

    /** Polls the saved pending code until approved, denied or expired. Safe to call repeatedly. */
    private fun resumePendingSignIn() {
        if (pollJob?.isActive == true) return
        val prefs = getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val deviceCode = prefs.getString(KEY_PENDING_DEVICE, null) ?: return
        val until = prefs.getLong(KEY_PENDING_UNTIL, 0L)
        val interval = prefs.getInt(KEY_PENDING_INTERVAL, 5) * 1000L
        val status = signInStatusView
        status?.setTextColor(0xFF94A3B8.toInt())
        status?.text = "Approve this phone in your browser. Code: ${prefs.getString(KEY_PENDING_CODE, "")}"
        pollJob = scope.launch {
            var outcome = "expired"
            var first = true
            while (System.currentTimeMillis() < until) {
                if (!first) delay(interval)
                first = false
                val poll = withContext(Dispatchers.IO) {
                    postJson("/v1/auth/device/poll", JSONObject().put("device_code", deviceCode))
                } ?: continue
                val st = poll.first.optString("status")
                if (st == "authorized") {
                    val key = poll.first.optString("api_key")
                    if (key.isNotBlank()) {
                        clearPendingSignIn()
                        onSignedIn?.invoke(key, poll.first.optString("email", "your account"))
                        return@launch
                    }
                }
                if (st == "denied") { outcome = "denied"; break }
                if (st == "expired" || st == "consumed") break
            }
            clearPendingSignIn()
            status?.text = if (outcome == "denied") "Sign-in was denied." else "The sign-in code expired. Try again."
            status?.setTextColor(0xFFEF4444.toInt())
        }
    }

    private fun clearPendingSignIn() {
        getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
            .remove(KEY_PENDING_DEVICE).remove(KEY_PENDING_CODE)
            .remove(KEY_PENDING_UNTIL).remove(KEY_PENDING_INTERVAL)
            .apply()
    }

    /** POST JSON; returns (body, status) or null on network failure. Error bodies are read too. */
    private fun postJson(path: String, body: JSONObject): Pair<JSONObject, Int>? = try {
        val conn = URL("$API_BASE$path").openConnection() as HttpURLConnection
        conn.requestMethod = "POST"
        conn.doOutput = true
        conn.connectTimeout = 10000
        conn.readTimeout = 10000
        conn.setRequestProperty("Content-Type", "application/json")
        conn.outputStream.use { it.write(body.toString().toByteArray()) }
        val code = conn.responseCode
        val text = (if (code in 200..299) conn.inputStream else conn.errorStream)?.bufferedReader()?.readText() ?: "{}"
        (try { JSONObject(text) } catch (_: Exception) { JSONObject() }) to code
    } catch (_: Exception) { null }

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }
}
