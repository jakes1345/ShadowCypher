package site.shadowcypher.assistant

import android.content.Context
import android.util.Log
import com.google.mediapipe.tasks.genai.llminference.LlmInference
import kotlinx.coroutines.*
import java.io.File
import java.net.HttpURLConnection
import java.net.URL

/**
 * On-device LLM inference via Gemma 3 1B IT (MediaPipe LLM Inference API).
 * Model is downloaded once (~600 MB) to internal storage on user request.
 *
 * Thread safety: generate() is safe to call from any thread.
 * Model load/download run on IO dispatcher; callbacks fire on Main.
 */
class GemmaInference(private val context: Context) {

    companion object {
        private const val TAG = "GemmaInference"
        private const val MODEL_FILENAME = "gemma3-1b.task"
        const val MODEL_URL =
            "https://huggingface.co/google/gemma-3-1b-it-litert-preview/resolve/main/gemma3-1b-it-int4.task"
        private const val MAX_TOKENS = 512
    }

    private var inference: LlmInference? = null

    @Volatile var isReady = false
    @Volatile var downloadProgress = -1 // -1 = idle, 0-100 = in progress

    private val modelFile get() = File(context.filesDir, MODEL_FILENAME)
    val modelExists get() = modelFile.exists() && modelFile.length() > 10_000_000L

    fun load(onReady: () -> Unit = {}, onError: (Exception) -> Unit = {}) {
        if (!modelExists) { onError(Exception("model_not_downloaded")); return }
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val options = LlmInference.LlmInferenceOptions.builder()
                    .setModelPath(modelFile.absolutePath)
                    .setMaxTokens(MAX_TOKENS)
                    .setTopK(40)
                    .setTemperature(0.7f)
                    .setRandomSeed(42)
                    .build()
                inference = LlmInference.createFromOptions(context, options)
                isReady = true
                Log.i(TAG, "Gemma 3 1B loaded (${modelFile.length() / 1_048_576} MB)")
                withContext(Dispatchers.Main) { onReady() }
            } catch (e: Exception) {
                Log.e(TAG, "Load failed: ${e.message}")
                withContext(Dispatchers.Main) { onError(e) }
            }
        }
    }

    fun generate(systemPrompt: String, userText: String): String {
        val llm = inference ?: return ""
        return try {
            // Gemma instruction-tuned chat template
            val prompt = buildString {
                if (systemPrompt.isNotBlank()) {
                    append("<start_of_turn>system\n")
                    append(systemPrompt.trim())
                    append("<end_of_turn>\n")
                }
                append("<start_of_turn>user\n")
                append(userText.trim())
                append("<end_of_turn>\n")
                append("<start_of_turn>model\n")
            }
            llm.generateResponse(prompt).trim()
        } catch (e: Exception) {
            Log.e(TAG, "Generate failed: ${e.message}")
            ""
        }
    }

    fun download(
        onProgress: (Int) -> Unit = {},
        onComplete: () -> Unit = {},
        onError: (Exception) -> Unit = {}
    ) {
        if (downloadProgress >= 0) return
        CoroutineScope(Dispatchers.IO).launch {
            downloadProgress = 0
            val tmp = File(context.filesDir, "$MODEL_FILENAME.tmp")
            try {
                val conn = URL(MODEL_URL).openConnection() as HttpURLConnection
                conn.connectTimeout = 30_000
                conn.readTimeout = 120_000
                conn.setRequestProperty("User-Agent", "ShadowCypher/1.0")
                conn.connect()
                val total = conn.contentLengthLong
                FileOutputStream(tmp).use { out ->
                    conn.inputStream.use { input ->
                        val buf = ByteArray(131_072)
                        var received = 0L
                        var n: Int
                        while (input.read(buf).also { n = it } >= 0) {
                            out.write(buf, 0, n)
                            received += n
                            if (total > 0) {
                                val pct = (received * 100 / total).toInt()
                                if (pct != downloadProgress) {
                                    downloadProgress = pct
                                    withContext(Dispatchers.Main) { onProgress(pct) }
                                }
                            }
                        }
                    }
                }
                tmp.renameTo(modelFile)
                downloadProgress = -1
                Log.i(TAG, "Model downloaded: ${modelFile.length() / 1_048_576} MB")
                withContext(Dispatchers.Main) { onComplete() }
            } catch (e: Exception) {
                tmp.delete()
                downloadProgress = -1
                Log.e(TAG, "Download failed: ${e.message}")
                withContext(Dispatchers.Main) { onError(e) }
            }
        }
    }

    fun deleteModel() {
        modelFile.delete()
        inference?.close()
        inference = null
        isReady = false
    }

    fun release() {
        inference?.close()
        inference = null
        isReady = false
    }
}
