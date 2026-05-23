package site.shadowcypher.assistant

import android.content.Context
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.util.Log
import kotlinx.coroutines.*
import org.vosk.Model
import org.vosk.Recognizer
import org.vosk.android.StorageService
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

    fun loadModel(onReady: () -> Unit, onError: (Throwable) -> Unit) {
        scope.launch {
            try {
                val modelDir = getOrDownloadModel()
                model = Model(modelDir.absolutePath)
                Log.i(TAG, "Model loaded from ${modelDir.absolutePath}")
                withContext(Dispatchers.Main) { onReady() }
            } catch (e: Exception) {
                Log.e(TAG, "Failed to load model", e)
                withContext(Dispatchers.Main) { onError(e) }
            }
        }
    }

    private suspend fun getOrDownloadModel(): File {
        val cacheDir = File(context.filesDir, "vosk")
        val modelDir = File(cacheDir, MODEL_DIR_NAME)

        if (modelDir.exists() && File(modelDir, "am/final.mdl").exists()) {
            Log.d(TAG, "Using cached model at ${modelDir.absolutePath}")
            return modelDir
        }

        cacheDir.mkdirs()
        Log.i(TAG, "Downloading Vosk model…")

        // Use a CompletableDeferred so the coroutine waits cleanly for StorageService
        val unpacked = kotlinx.coroutines.CompletableDeferred<String>()
        StorageService.unpack(context, MODEL_URL, "vosk", { setOf(modelDir) }) { modelPath ->
            Log.i(TAG, "Model unpacked to $modelPath")
            unpacked.complete(modelPath)
        }

        // Wait up to 120s with proper coroutine suspension (not Thread.sleep)
        withContext(Dispatchers.IO) {
            kotlinx.coroutines.withTimeoutOrNull(120_000L) { unpacked.await() }
        }

        if (!modelDir.exists()) throw IOException("Model download timed out")
        return modelDir
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
            val maxSilence = (SAMPLE_RATE * 1.5 / buf.size).toInt() // 1.5 s silence → finalize

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
                        withContext(Dispatchers.Main) { onResult(result) }
                        break
                    }
                } else {
                    val partial = parseText(recognizer?.partialResult ?: "")
                    if (partial.isNotBlank()) {
                        silenceFrames = 0
                        withContext(Dispatchers.Main) { onPartial?.invoke(partial) }
                    } else {
                        silenceFrames++
                    }

                    if (silenceFrames >= maxSilence) {
                        val final = parseText(recognizer?.finalResult ?: "")
                        if (final.isNotBlank()) {
                            withContext(Dispatchers.Main) { onResult(final) }
                        }
                        break
                    }
                }
            }
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
