package site.shadowcypher.assistant

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED) {
            val prefs = context.getSharedPreferences("shadow_prefs", Context.MODE_PRIVATE)
            if (prefs.getBoolean("wake_word_enabled", false)) {
                WakeWordService.start(context)
            }
        }
    }
}
