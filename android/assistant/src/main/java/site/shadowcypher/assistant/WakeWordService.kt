package site.shadowcypher.assistant

import android.app.*
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat

/**
 * Foreground service that listens for "Hey Shadow" in the background.
 * When the wake word fires it launches AssistantActivity.
 *
 * Start:   context.startForegroundService(Intent(context, WakeWordService::class.java))
 * Stop:    context.stopService(Intent(context, WakeWordService::class.java))
 *
 * Permissions required in AndroidManifest.xml (already declared):
 *   RECORD_AUDIO, FOREGROUND_SERVICE, FOREGROUND_SERVICE_MICROPHONE (API 34+)
 */
class WakeWordService : Service() {

    companion object {
        private const val TAG = "WakeWordService"
        private const val CHANNEL_ID = "shadow_wake_word"
        private const val NOTIF_ID = 1001

        fun start(context: Context) {
            val intent = Intent(context, WakeWordService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }

        fun stop(context: Context) {
            context.stopService(Intent(context, WakeWordService::class.java))
        }
    }

    private lateinit var detector: WakeWordDetector

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        startForeground(NOTIF_ID, buildNotification())
        detector = WakeWordDetector(this)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (!detector.isReady) {
            val loaded = detector.load()
            if (!loaded) {
                Log.w(TAG, "Wake word model not available — service stopping")
                stopSelf()
                return START_NOT_STICKY
            }
        }

        detector.start {
            Log.i(TAG, "Wake word fired — launching AssistantActivity")
            val launch = Intent(this, AssistantActivity::class.java).apply {
                action = Intent.ACTION_ASSIST
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
                putExtra("source", "wake_word")
            }
            startActivity(launch)
        }

        return START_STICKY
    }

    override fun onDestroy() {
        detector.release()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    // ── Notification ──────────────────────────────────────────────────────────

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Shadow Wake Word",
                NotificationManager.IMPORTANCE_LOW,
            ).apply {
                description = "Listens for 'Hey Shadow' in the background"
                setShowBadge(false)
            }
            getSystemService(NotificationManager::class.java)
                .createNotificationChannel(channel)
        }
    }

    private fun buildNotification(): Notification {
        val stopIntent = PendingIntent.getService(
            this,
            0,
            Intent(this, WakeWordService::class.java).apply { action = "STOP" },
            PendingIntent.FLAG_IMMUTABLE,
        )

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Shadow is listening")
            .setContentText("Say \"Hey Shadow\" to activate")
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setOngoing(true)
            .addAction(android.R.drawable.ic_delete, "Stop", stopIntent)
            .build()
    }
}
