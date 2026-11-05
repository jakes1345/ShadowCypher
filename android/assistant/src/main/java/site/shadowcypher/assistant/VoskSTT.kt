package site.shadowcypher.assistant

import android.content.Context
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.util.Log
import kotlinx.coroutines.*
import org.vosk.Model
import org.vosk.Recognizer
import java.io.File
import java.io.IOException

/**
 * Offline speech-to-text via Vosk (alphacephei.com/vosk).
 *
 * Model: vosk-model-small-en-us-0.15 (~40 MB).
 * Downloaded once to internal storage on first call; subsequent launches use cache.
 *
 * Usage:
 *   val vosk = VoskSTT(context)
 *   vosk.start { transcript -> handleResult(transcript) }
 *   vosk.stop()
 */
class VoskSTT(private val context: Context) {

    companion object {
        private const val TAG = "VoskSTT"
        private const val SAMPLE_RATE = 16_000
        private const val CHANNEL_CONFIG = AudioFormat.CHANNEL_IN_MONO
        private const val AUDIO_FORMAT = AudioFormat.ENCODING_PCM_16BIT
        private const val MODEL_URL =
            "https://alphacephei.com/kaldi/models/vosk-model-small-en-us-0.15.zip"
        private const val MODEL_DIR_NAME = "vosk-model-small-en-us-0.15"
    }

    private var model: Model? = null
    private var recognizer: Recognizer? = null
    private var audioRecord: AudioRecord? = null
    private var job: Job? = null
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    val isReady: Boolean get() = model != null

    // ── Model bootstrapping ───────────────────────────────────────────────────

    fun loadModel(
        onReady: () -> Unit,
        onError: (Throwable) -> Unit,
        onDownloadStart: (() -> Unit)? = null,
        onProgress: ((Float) -> Unit)? = null,
    ) {
        scope.launch {
            try {
                val modelDir = getOrDownloadModel(onDownloadStart, onProgress)
                model = Model(modelDir.absolutePath)
                Log.i(TAG, "Model loaded from ${modelDir.absolutePath}")
                withContext(Dispatchers.Main) { onReady() }
            } catch (e: Exception) {
                Log.e(TAG, "Failed to load model", e)
                withContext(Dispatchers.Main) { onError(e) }
            }
        }
    }

    private suspend fun getOrDownloadModel(
        onDownloadStart: (() -> Unit)? = null,
        onProgress: ((Float) -> Unit)? = null,
    ): File {
        val cacheDir = File(context.filesDir, "vosk")
        val modelDir = File(cacheDir, MODEL_DIR_NAME)

        if (modelDir.exists() && File(modelDir, "am/final.mdl").exists()) {
            Log.d(TAG, "Using cached model at ${modelDir.absolutePath}")
            // Signal ~instant progress for cached load
            withContext(Dispatchers.Main) { onProgress?.invoke(1f) }
            return modelDir
        }

        // 41 MB: only fetch on Wi-Fi or another unmetered network
        val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as android.net.ConnectivityManager
        if (cm.isActiveNetworkMetered) throw IOException("Offline speech model will download on Wi-Fi")

        cacheDir.mkdirs()
        Log.i(TAG, "Downloading Vosk model…")
        withContext(Dispatchers.Main) { onDownloadStart?.invoke() }

        // Download the zip with real progress, then unpack it. (StorageService.unpack
        // only unpacks a model bundled in the app's assets; it can't download.)
        val zip = File(cacheDir, "$MODEL_DIR_NAME.zip.part")
        val staging = File(cacheDir, "$MODEL_DIR_NAME.staging")
        try {
            download(MODEL_URL, zip) { p -> scope.launch(Dispatchers.Main) { onProgress?.invoke(p * 0.9f) } }
            staging.deleteRecursively()
            unzip(zip, staging)
            val unpacked = File(staging, MODEL_DIR_NAME)
            if (!File(unpacked, "am/final.mdl").exists()) throw IOException("Model archive is missing am/final.mdl")
            modelDir.deleteRecursively()
            if (!unpacked.renameTo(modelDir)) throw IOException("Couldn't move the model into place")
            withContext(Dispatchers.Main) { onProgress?.invoke(1f) }
        } finally {
            zip.delete()
            staging.deleteRecursively()
        }
        return modelDir
    }

    private fun download(url: String, dest: File, onProgress: (Float) -> Unit) {
        val conn = java.net.URL(url).openConnection() as java.net.HttpURLConnection
        conn.connectTimeout = 15_000
        conn.readTimeout = 30_000
        try {
            if (conn.responseCode != 200) throw IOException("Model download failed: HTTP ${conn.responseCode}")
            val total = conn.contentLengthLong
            var done = 0L
            var lastTick = 0L
            conn.inputStream.use { input ->
                dest.outputStream().use { out ->
                    val buf = ByteArray(64 * 1024)
                    while (true) {
                        val n = input.read(buf)
                        if (n < 0) break
                        out.write(buf, 0, n)
                        done += n
                        if (total > 0 && done - lastTick > 512 * 1024) { lastTick = done; onProgress(done.toFloat() / total) }
                    }
                }
            }
            if (total > 0 && done != total) throw IOException("Model download incomplete ($done of $total bytes)")
        } finally {
            conn.disconnect()
        }
    }

    /** Unzips [zip] into [dest], refusing entries that would land outside it. */
    private fun unzip(zip: File, dest: File) {
        val root = dest.canonicalFile
        java.util.zip.ZipInputStream(zip.inputStream().buffered()).use { zin ->
            while (true) {
                val entry = zin.nextEntry ?: break
                val out = File(root, entry.name).canonicalFile
                if (!out.path.startsWith(root.path + File.separator)) throw IOException("Unsafe path in model archive: ${entry.name}")
                if (entry.isDirectory) { out.mkdirs(); continue }
                out.parentFile?.mkdirs()
                out.outputStream().use { zin.copyTo(it) }
            }
        }
    }

    // ── Recording ─────────────────────────────────────────────────────────────

    fun start(onPartial: ((String) -> Unit)? = null, onResult: (String) -> Unit) {
        if (model == null) {
            onResult("")
            return
        }

        stop()

        val bufferSize = AudioRecord.getMinBufferSize(SAMPLE_RATE, CHANNEL_CONFIG, AUDIO_FORMAT)
            .coerceAtLeast(8192)

        try {
            recognizer = Recognizer(model, SAMPLE_RATE.toFloat())
            audioRecord = AudioRecord(
                MediaRecorder.AudioSource.MIC,
                SAMPLE_RATE,
                CHANNEL_CONFIG,
                AUDIO_FORMAT,
                bufferSize,
            )
        } catch (e: SecurityException) {
            Log.e(TAG, "Mic permission denied", e)
            return
        }

        audioRecord?.startRecording()

        job = scope.launch {
            val buf = ShortArray(bufferSize / 2)
            var silenceFrames = 0
            var reported = false
            val maxSilence = (SAMPLE_RATE * 1.5 / buf.size).toInt() // 1.5 s silence → finalize
            val deadline = System.currentTimeMillis() + 15_000L                 // hard cap per listen

            while (isActive) {
                val read = audioRecord?.read(buf, 0, buf.size) ?: -1
                if (read <= 0) break

                val bytes = ByteArray(read * 2)
                for (i in 0 until read) {
                    bytes[i * 2] = (buf[i].toInt() and 0xFF).toByte()
                    bytes[i * 2 + 1] = (buf[i].toInt() shr 8 and 0xFF).toByte()
                }

                val isSpeech = recognizer?.acceptWaveForm(bytes, bytes.size) ?: false

                if (isSpeech) {
                    silenceFrames = 0
                    val result = parseText(recognizer?.result ?: "")
                    if (result.isNotBlank()) {
                        reported = true
                        withContext(Dispatchers.Main) { onResult(result) }
                        break
                    }
                    if (System.currentTimeMillis() > deadline) break
                } else {
                    val partial = parseText(recognizer?.partialResult ?: "")
                    if (partial.isNotBlank()) {
                        silenceFrames = 0
                        withContext(Dispatchers.Main) { onPartial?.invoke(partial) }
                    } else {
                        silenceFrames++
                    }

                    if (silenceFrames >= maxSilence || System.currentTimeMillis() > deadline) {
                        // Always report back, even when nothing was heard, so the UI
                        // leaves the listening state (an empty transcript means idle).
                        val final = parseText(recognizer?.finalResult ?: "")
                        reported = true
                        withContext(Dispatchers.Main) { onResult(final) }
                        break
                    }
                }
            }
            if (!reported && isActive) withContext(Dispatchers.Main) { onResult("") }
            stopInternal()
        }
    }

    fun stop() {
        job?.cancel()
        job = null
        stopInternal()
    }

    private fun stopInternal() {
        audioRecord?.let {
            if (it.state == AudioRecord.STATE_INITIALIZED) {
                it.stop()
                it.release()
            }
        }
        audioRecord = null
        recognizer?.close()
        recognizer = null
    }

    fun release() {
        stop()
        scope.cancel()
        model?.close()
        model = null
    }

    // ── JSON parsing ──────────────────────────────────────────────────────────

    private fun parseText(json: String): String {
        // Vosk returns {"text":"..."} or {"partial":"..."}
        return Regex(""""(?:text|partial)"\s*:\s*"([^"]*?)"""")
            .find(json)?.groupValues?.getOrNull(1)?.trim() ?: ""
    }
}
