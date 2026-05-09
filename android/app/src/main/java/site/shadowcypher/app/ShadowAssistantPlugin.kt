package site.shadowcypher.app

import android.Manifest
import android.content.Intent
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.util.Log
import com.getcapacitor.JSObject
import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.PluginMethod
import com.getcapacitor.annotation.CapacitorPlugin
import com.getcapacitor.annotation.Permission
import com.getcapacitor.annotation.PermissionCallback
import java.util.Locale

@CapacitorPlugin(
    name = "ShadowAssistant",
    permissions = [
        Permission(strings = [Manifest.permission.RECORD_AUDIO], alias = "microphone")
    ]
)
class ShadowAssistantPlugin : Plugin() {

    private var speechRecognizer: SpeechRecognizer? = null
    private var tts: TextToSpeech? = null
    private var ttsReady = false
    private var activeCall: PluginCall? = null

    override fun load() {
        initTTS()
        checkAssistLaunch()
    }

    private fun initTTS() {
        tts = TextToSpeech(context) { status ->
            if (status == TextToSpeech.SUCCESS) {
                tts?.language = Locale.US
                tts?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                    override fun onStart(utteranceId: String?) {}
                    override fun onDone(utteranceId: String?) {
                        val data = JSObject().apply { put("utteranceId", utteranceId) }
                        notifyListeners("speakDone", data)
                    }
                    @Deprecated("Deprecated in API level 21")
                    override fun onError(utteranceId: String?) {}
                })
                ttsReady = true
                Log.d("ShadowAssistant", "TTS initialized")
            } else {
                Log.e("ShadowAssistant", "TTS init failed with status $status — speak will be unavailable")
                notifyListeners("ttsUnavailable", JSObject().apply { put("status", status) })
            }
        }
    }

    private fun checkAssistLaunch() {
        val intent = activity.intent ?: return
        if (intent.action == Intent.ACTION_ASSIST ||
            intent.action == "android.intent.action.VOICE_ASSIST" ||
            intent.hasCategory(Intent.CATEGORY_DEFAULT) && intent.action == Intent.ACTION_ASSIST
        ) {
            bridge.webView.post {
                val data = JSObject().apply {
                    put("source", "assist_long_press")
                    put("timestamp", System.currentTimeMillis())
                }
                notifyListeners("assistInvoked", data)
            }
        }
    }

    @PluginMethod
    fun checkAssistStatus(call: PluginCall) {
        val intent = activity.intent
        val wasAssist = intent?.action == Intent.ACTION_ASSIST
        val result = JSObject().apply {
            put("wasAssistLaunch", wasAssist)
            put("ttsReady", ttsReady)
            put("sttAvailable", SpeechRecognizer.isRecognitionAvailable(context))
        }
        call.resolve(result)
    }

    @PluginMethod
    fun requestMicPermission(call: PluginCall) {
        if (getPermissionState("microphone") == com.getcapacitor.PermissionState.GRANTED) {
            call.resolve(JSObject().apply { put("granted", true) })
        } else {
            requestPermissionForAlias("microphone", call, "microphonePermissionCallback")
        }
    }

    @PermissionCallback
    private fun microphonePermissionCallback(call: PluginCall) {
        val granted = getPermissionState("microphone") == com.getcapacitor.PermissionState.GRANTED
        call.resolve(JSObject().apply { put("granted", granted) })
    }

    @PluginMethod
    fun startListening(call: PluginCall) {
        if (getPermissionState("microphone") != com.getcapacitor.PermissionState.GRANTED) {
            call.reject("PERMISSION_DENIED", "Microphone permission required")
            return
        }
        activeCall = call

        activity.runOnUiThread {
            speechRecognizer?.destroy()
            speechRecognizer = SpeechRecognizer.createSpeechRecognizer(context)
            speechRecognizer?.setRecognitionListener(object : RecognitionListener {
                override fun onReadyForSpeech(params: Bundle?) {
                    notifyListeners("listeningStarted", JSObject())
                }
                override fun onBeginningOfSpeech() {
                    notifyListeners("speechDetected", JSObject())
                }
                override fun onRmsChanged(rmsdB: Float) {
                    val d = JSObject().apply { put("rms", rmsdB) }
                    notifyListeners("rmsChanged", d)
                }
                override fun onResults(results: Bundle?) {
                    val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                    val text = matches?.firstOrNull() ?: ""
                    val confidence = results?.getFloatArray(SpeechRecognizer.CONFIDENCE_SCORES)?.firstOrNull() ?: 0f
                    val data = JSObject().apply {
                        put("transcript", text)
                        put("confidence", confidence)
                        put("allMatches", matches?.joinToString("|") ?: "")
                    }
                    notifyListeners("speechResult", data)
                    activeCall?.resolve(JSObject().apply {
                        put("transcript", text)
                        put("confidence", confidence)
                    })
                    activeCall = null
                }
                override fun onError(error: Int) {
                    val msg = when (error) {
                        SpeechRecognizer.ERROR_AUDIO -> "Audio recording error"
                        SpeechRecognizer.ERROR_CLIENT -> "Client error"
                        SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> "Insufficient permissions"
                        SpeechRecognizer.ERROR_NETWORK -> "Network error"
                        SpeechRecognizer.ERROR_NO_MATCH -> "No speech match"
                        SpeechRecognizer.ERROR_RECOGNIZER_BUSY -> "Recognizer busy"
                        SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> "Speech timeout"
                        else -> "Unknown error ($error)"
                    }
                    notifyListeners("speechError", JSObject().apply { put("message", msg) })
                    activeCall?.reject(msg)
                    activeCall = null
                }
                override fun onBufferReceived(buffer: ByteArray?) {}
                override fun onEndOfSpeech() { notifyListeners("speechEnded", JSObject()) }
                override fun onEvent(eventType: Int, params: Bundle?) {}
                override fun onPartialResults(partial: Bundle?) {
                    val matches = partial?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                    val text = matches?.firstOrNull() ?: ""
                    if (text.isNotEmpty()) {
                        notifyListeners("partialResult", JSObject().apply { put("transcript", text) })
                    }
                }
            })

            val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault())
                putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
                putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 3)
                putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 1500L)
                putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_POSSIBLY_COMPLETE_SILENCE_LENGTH_MILLIS, 1000L)
            }
            speechRecognizer?.startListening(intent)
        }
    }

    @PluginMethod
    fun stopListening(call: PluginCall) {
        activity.runOnUiThread {
            speechRecognizer?.stopListening()
        }
        call.resolve()
    }

    @PluginMethod
    fun speak(call: PluginCall) {
        val text = call.getString("text") ?: run { call.reject("text required"); return }
        val utteranceId = call.getString("utteranceId", "shadow_speak_${System.currentTimeMillis()}")!!
        val pitch = call.getFloat("pitch", 1.0f)!!
        val rate = call.getFloat("rate", 1.0f)!!

        if (!ttsReady) { call.reject("TTS_NOT_READY"); return }

        tts?.setPitch(pitch)
        tts?.setSpeechRate(rate)

        val params = Bundle().apply {
            putString(TextToSpeech.Engine.KEY_PARAM_UTTERANCE_ID, utteranceId)
        }
        tts?.speak(text, TextToSpeech.QUEUE_FLUSH, params, utteranceId)
        call.resolve(JSObject().apply { put("utteranceId", utteranceId) })
    }

    @PluginMethod
    fun stopSpeaking(call: PluginCall) {
        tts?.stop()
        call.resolve()
    }

    @PluginMethod
    fun finishActivity(call: PluginCall) {
        activity.runOnUiThread { activity.finish() }
        call.resolve()
    }

    @PluginMethod
    fun openAssistSettings(call: PluginCall) {
        try {
            val intent = Intent(android.provider.Settings.ACTION_VOICE_INPUT_SETTINGS)
            activity.startActivity(intent)
        } catch (e: Exception) {
            val fallback = Intent(android.provider.Settings.ACTION_SETTINGS)
            activity.startActivity(fallback)
        }
        call.resolve()
    }

    override fun handleOnNewIntent(intent: Intent) {
        super.handleOnNewIntent(intent)
        if (intent.action == Intent.ACTION_ASSIST) {
            bridge.webView.post {
                val data = JSObject().apply {
                    put("source", "assist_new_intent")
                    put("timestamp", System.currentTimeMillis())
                }
                notifyListeners("assistInvoked", data)
            }
        }
    }

    override fun handleOnDestroy() {
        speechRecognizer?.destroy()
        tts?.shutdown()
        super.handleOnDestroy()
    }
}
