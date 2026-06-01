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

    companion object {
        private const val PREFS = "shadow_prefs"
        private const val KEY_API = "sc_api_key"
        private const val KEY_WAKE = "wake_word_enabled"
        private const val API_BASE = "https://api.shadowcypher.site"
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
                "Guardian network connected. Say 'Hey Shadow' or long-press Home."
            else
                "Enter your ShadowCypher API key below to connect to your Guardian network."
            textSize = 13f
            setTextColor(0xFF94A3B8.toInt())
            setPadding(0, 8, 0, 0)
        }
        statusCard.addView(statusTitle)
        statusCard.addView(statusDesc)

        // API Key section
        val keyLabel = sectionLabel("API KEY")
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
                    statusDesc.text = "Guardian network connected. Say 'Hey Shadow' or long-press Home."
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
        val assistBtn = ghostButton("Set as Default Assist App")
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

        listOf(header, sub, statusCard, keyLabel, keyInput, keyStatus,
            sectionSpacer(), saveBtn, sectionSpacer(),
            wakeLabel, wakeRow, sectionSpacer(),
            assistLabel, assistBtn, sectionSpacer(),
            launchBtn
        ).forEach { layout.addView(it) }

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

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }
}
