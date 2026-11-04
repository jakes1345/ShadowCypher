package site.shadowcypher.assistant

import android.content.Intent
import android.os.Bundle
import android.service.voice.VoiceInteractionService
import android.service.voice.VoiceInteractionSession
import android.service.voice.VoiceInteractionSessionService
import android.speech.RecognitionService
import android.speech.SpeechRecognizer

/**
 * Makes Shadow selectable under Settings → Default apps → Digital assistant app.
 * Once selected, Android calls the session below for long-press home, the power
 * button (where the phone maps it to the assistant), the corner swipe gesture and
 * headset buttons.
 */
class ShadowVoiceInteractionService : VoiceInteractionService()

class ShadowVoiceSessionService : VoiceInteractionSessionService() {
    override fun onNewSession(args: Bundle?): VoiceInteractionSession = ShadowVoiceSession(this)
}

/** Opens the assistant overlay, which starts listening because it sees ACTION_ASSIST. */
class ShadowVoiceSession(service: VoiceInteractionSessionService) : VoiceInteractionSession(service) {
    override fun onShow(args: Bundle?, showFlags: Int) {
        super.onShow(args, showFlags)
        val intent = Intent(context, AssistantActivity::class.java)
            .setAction(Intent.ACTION_ASSIST)
            .addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP)
        startAssistantActivity(intent)
        hide()
    }
}

/**
 * Android requires a digital assistant to declare a recognition service. Shadow does
 * its own listening in AssistantActivity, so other apps asking it for speech
 * recognition get a clean "not available" error.
 */
class ShadowRecognitionService : RecognitionService() {
    override fun onStartListening(recognizerIntent: Intent?, listener: Callback?) {
        listener?.error(SpeechRecognizer.ERROR_CLIENT)
    }
    override fun onCancel(listener: Callback?) {}
    override fun onStopListening(listener: Callback?) {}
}
