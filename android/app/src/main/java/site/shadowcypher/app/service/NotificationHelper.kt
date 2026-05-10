package site.shadowcypher.app.service

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import site.shadowcypher.app.data.Incident

const val CHANNEL_INCIDENTS = "channel_incidents"
const val CHANNEL_CVE = "channel_cve"
const val CHANNEL_SYNC = "channel_sync"

object NotificationHelper {

    fun createChannels(context: Context) {
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

    fun postIncidentNotification(context: Context, incident: Incident) {
        val nm = NotificationManagerCompat.from(context)

        // Check notification permission at runtime (Android 13+)
        if (!nm.areNotificationsEnabled()) return

        val notification = NotificationCompat.Builder(context, CHANNEL_INCIDENTS)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setContentTitle("${incident.severity} — ${incident.type}")
            .setContentText(incident.description)
            .setStyle(NotificationCompat.BigTextStyle().bigText(incident.description))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .build()

        nm.notify(incident.id.hashCode(), notification)
    }

    fun postCveNotification(context: Context, cveId: String, description: String) {
        val nm = NotificationManagerCompat.from(context)
        if (!nm.areNotificationsEnabled()) return

        val notification = NotificationCompat.Builder(context, CHANNEL_CVE)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle("CVE Alert: $cveId")
            .setContentText(description)
            .setStyle(NotificationCompat.BigTextStyle().bigText(description))
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .setAutoCancel(true)
            .build()

        nm.notify(cveId.hashCode(), notification)
    }
}
