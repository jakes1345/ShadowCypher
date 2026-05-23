package site.shadowcypher.app.service

import android.content.Context
import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import site.shadowcypher.app.data.GuardianRepository
import java.util.concurrent.TimeUnit

class BackgroundSyncWorker(
    private val context: Context,
    workerParams: WorkerParameters
) : CoroutineWorker(context, workerParams) {

    override suspend fun doWork(): Result {
        val repo = GuardianRepository.get(context)

        if (repo.getApiKey().isBlank()) {
            return Result.success()
        }

        val summaryResult = repo.fetchSummary()
        summaryResult.onFailure { err ->
            val isTransient = err !is IllegalStateException &&
                err.message?.contains("401") != true &&
                err.message?.contains("403") != true &&
                err.message?.contains("No API key") != true
            return if (isTransient) Result.retry() else Result.success()
        }

        val summary = summaryResult.getOrNull() ?: return Result.success()

        val unresolvedIncidents = summary.incidents.filter { !it.resolved }
        unresolvedIncidents.take(5).forEach { incident ->
            NotificationHelper.postIncidentNotification(context, incident)
        }

        summary.cve_alerts.take(3).forEach { cve ->
            NotificationHelper.postCveNotification(context, cve.cve_id, cve.description.orEmpty())
        }

        return Result.success()
    }

    companion object {
        private const val WORK_NAME = "guardian_background_sync"

        fun schedule(context: Context) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build()

            val request = PeriodicWorkRequestBuilder<BackgroundSyncWorker>(
                15, TimeUnit.MINUTES
            )
                .setConstraints(constraints)
                .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30, TimeUnit.SECONDS)
                .build()

            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                WORK_NAME,
                ExistingPeriodicWorkPolicy.KEEP,
                request
            )
        }

        fun cancel(context: Context) {
            WorkManager.getInstance(context).cancelUniqueWork(WORK_NAME)
        }
    }
}
