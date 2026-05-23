package site.shadowcypher.assistant

import android.app.*
import android.content.Context
import android.content.Intent
import android.os.*
import android.util.Log
import androidx.core.app.NotificationCompat
import kotlinx.coroutines.*

/**
 * Foreground service that continuously listens for "Hey Shadow".
 * When the wake word fires it launches AssistantActivity via ACTION_ASSIST.
 *
 * Start:  WakeWordService.start(context)
 * Stop:   WakeWordService.stop(context)
 *
 * Required manifest permissions:
 *   RECORD_AUDIO, FOREGROUND_SERVICE, FOREGROUND_SERVICE_MICROPHONE (API 34+),
 *   VIBRATE
 */
class WakeWordService : Service() {

    companion object {
        private const val TAG          = "WakeWordService"
        private const val CHANNEL_ID   = "shadow_wake_word"
        private const val NOTIF_ID     = 1001
        private const val ACTION_STOP  = "site.shadowcypher.assistant.WAKE_STOP"

        fun start(context: Context) {
            val intent = Intent(context, WakeWordService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }

        fun stop(context: Context) =
            context.stopService(Intent(context, WakeWordService::class.java))
    }

    private val serviceScope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private lateinit var detector: WakeWordDetector
    private var loaded = false
    private var wakeLock: PowerManager.WakeLock? = null

    // ── Lifecycle ──────────────────────────────────────────────────────────────

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        startForeground(NOTIF_ID, buildNotification("Loading wake word model…"))
        detector = WakeWordDetector(this)
        val pm = getSystemService(POWER_SERVICE) as PowerManager
        wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "ShadowCypher:WakeWordWakeLock")
            .also { it.acquire() }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        // Handle stop action from notification button
        if (intent?.action == ACTION_STOP) {
            Log.i(TAG, "Stop action received")
            stopSelf()
            return START_NOT_STICKY
        }

        if (!loaded) {
            serviceScope.launch {
                loaded = detector.load()
                if (!loaded) {
                    Log.w(TAG, "Wake word model not available — service stopping")
                    withContext(Dispatchers.Main) { stopSelf() }
                    return@launch
                }
                withContext(Dispatchers.Main) {
                    updateNotification("Listening for \"Hey Shadow\"…")
                    startDetection()
                }
            }
        } else {
            startDetection()
        }

        return START_STICKY
    }

    private fun startDetection() {
        detector.start {
            Log.i(TAG, "Wake word fired — launching AssistantActivity")
            vibrateWakePattern()
            val launch = Intent(this, AssistantActivity::class.java).apply {
                action = Intent.ACTION_ASSIST
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
                putExtra("source", "wake_word")
            }
            startActivity(launch)
        }
    }

    override fun onDestroy() {
        detector.release()
        serviceScope.cancel()
        wakeLock?.let { if (it.isHeld) it.release() }
        wakeLock = null
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    // ── Haptic feedback ───────────────────────────────────────────────────────

    private fun vibrateWakePattern() {
        val vibrator = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            val vm = getSystemService(VibratorManager::class.java)
            vm?.defaultVibrator
        } else {
            @Suppress("DEPRECATION")
            getSystemService(VIBRATOR_SERVICE) as? Vibrator
        }
        vibrator ?: return
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            vibrator.vibrate(VibrationEffect.createWaveform(longArrayOf(0, 80, 60, 80), -1))
        } else {
            @Suppress("DEPRECATION")
            vibrator.vibrate(longArrayOf(0, 80, 60, 80), -1)
        }
    }

    // ── Notification ──────────────────────────────────────────────────────────

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Shadow Wake Word",
                NotificationManager.IMPORTANCE_LOW,
            ).apply {
                description = "Listens for \"Hey Shadow\" in the background"
                setShowBadge(false)
            }
            getSystemService(NotificationManager::class.java)
                .createNotificationChannel(channel)
        }
    }

    private fun buildNotification(text: String): Notification {
        val stopPendingIntent = PendingIntent.getService(
            this, 0,
            Intent(this, WakeWordService::class.java).apply { action = ACTION_STOP },
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )
        val openPendingIntent = PendingIntent.getActivity(
            this, 1,
            Intent(this, AssistantActivity::class.java).apply {
                action = Intent.ACTION_MAIN
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            },
            PendingIntent.FLAG_IMMUTABLE,
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Shadow is listening")
            .setContentText(text)
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentIntent(openPendingIntent)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setOngoing(true)
            .addAction(android.R.drawable.ic_delete, "Stop", stopPendingIntent)
            .build()
    }

    private fun updateNotification(text: String) {
        val nm = getSystemService(NotificationManager::class.java)
        nm.notify(NOTIF_ID, buildNotification(text))
    }
}
