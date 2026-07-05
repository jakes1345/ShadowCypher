package site.shadowcypher.app.service

import android.Manifest
import android.annotation.SuppressLint
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.SharedPreferences
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import site.shadowcypher.app.data.Incident

const val CHANNEL_INCIDENTS = "channel_incidents"
const val CHANNEL_CVE = "channel_cve"
const val CHANNEL_SYNC = "channel_sync"

object NotificationHelper {

    fun createChannels(context: Context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val nm = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

        nm.createNotificationChannel(
            NotificationChannel(
                CHANNEL_INCIDENTS,
                "Security Incidents",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Alerts for new security incidents detected on your network"
            }
        )

        nm.createNotificationChannel(
            NotificationChannel(
                CHANNEL_CVE,
                "CVE Alerts",
                NotificationManager.IMPORTANCE_DEFAULT
            ).apply {
                description = "Notifications for CVE vulnerabilities affecting your devices"
            }
        )

        nm.createNotificationChannel(
            NotificationChannel(
                CHANNEL_SYNC,
                "Sync Status",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Background sync status updates"
            }
        )
    }

    private fun notifiedPrefs(context: Context): SharedPreferences =
        context.getSharedPreferences("shadow_notified", Context.MODE_PRIVATE)

    fun clearNotifiedCache(context: Context) {
        notifiedPrefs(context).edit().clear().apply()
    }

    private fun hasNotificationPermission(context: Context): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) return true
        return ContextCompat.checkSelfPermission(
            context, Manifest.permission.POST_NOTIFICATIONS
        ) == PackageManager.PERMISSION_GRANTED
    }

    @SuppressLint("MissingPermission") // gated by hasNotificationPermission() below
    fun postIncidentNotification(context: Context, incident: Incident) {
        val nm = NotificationManagerCompat.from(context)
        if (!nm.areNotificationsEnabled() || !hasNotificationPermission(context)) return

        val prefs = notifiedPrefs(context)
        val key = "incident_${incident.id}"
        if (prefs.getBoolean(key, false)) return
        prefs.edit().putBoolean(key, true).apply()

        val notifId = (incident.id.hashCode() and 0x7FFFFFFF) % 100_000 + 1

        val notification = NotificationCompat.Builder(context, CHANNEL_INCIDENTS)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setContentTitle("${incident.severity.orEmpty()} — ${incident.type.orEmpty()}")
            .setContentText(incident.description.orEmpty())
            .setStyle(NotificationCompat.BigTextStyle().bigText(incident.description.orEmpty()))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .build()

        nm.notify(notifId, notification)
    }

    @SuppressLint("MissingPermission") // gated by hasNotificationPermission() below
    fun postCveNotification(context: Context, cveId: String, description: String) {
        val nm = NotificationManagerCompat.from(context)
        if (!nm.areNotificationsEnabled() || !hasNotificationPermission(context)) return

        val prefs = notifiedPrefs(context)
        val key = "cve_${cveId}"
        if (prefs.getBoolean(key, false)) return
        prefs.edit().putBoolean(key, true).apply()

        val notifId = (cveId.hashCode() and 0x7FFFFFFF) % 100_000 + 100_001

        val notification = NotificationCompat.Builder(context, CHANNEL_CVE)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle("CVE Alert: $cveId")
            .setContentText(description)
            .setStyle(NotificationCompat.BigTextStyle().bigText(description))
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .setAutoCancel(true)
            .build()

        nm.notify(notifId, notification)
    }
}
