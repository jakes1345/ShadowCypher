package site.shadowcypher.assistant

import android.content.Context
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.util.Log
import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import kotlinx.coroutines.*
import kotlin.coroutines.coroutineContext
import java.nio.FloatBuffer

/**
 * "Hey Shadow" wake word detection using the openWakeWord 3-stage ONNX pipeline.
 *
 * Pipeline:
 *   1. Raw PCM (16kHz, float32, 1280-sample chunks)
 *        └→ melspectrogram.onnx → mel frames  [1, 1, T, 32]
 *   2. Mel ring-buffer (76 frames) → embedding_model.onnx → 96-dim embedding
 *   3. Embedding ring-buffer (16 embeddings) → hey_shadow.onnx → probability
 *
 * All three ONNX models must be present in src/main/assets/:
 *   melspectrogram.onnx   — shared pre-processing model
 *   embedding_model.onnx  — shared audio embedding model
 *   hey_shadow.onnx       — wake-word classifier (hey_jarvis weights)
 *
 * Model input/output shapes (verified against openWakeWord v0.4.0):
 *   melspectrogram : input  [batch, samples]  → output [1, 1, T, 32]
 *   embedding_model: input  [1, 76, 32, 1]   → output [1, 1, 1, 96]
 *   hey_shadow     : input  [1, 16, 96]       → output [1, 1]
 */
class WakeWordDetector(private val context: Context) {

    companion object {
        private const val TAG = "WakeWordDetector"
        private const val SAMPLE_RATE   = 16_000
        private const val CHUNK_SAMPLES = 1280          // 80 ms @ 16 kHz
        private const val MEL_FRAMES_PER_CHUNK = 8      // frames produced per 1280-sample chunk
        private const val MEL_WIN_FRAMES  = 76          // embedding model window
        private const val EMB_WIN_SIZE    = 16          // classifier window (embeddings)
        private const val EMB_FEATURES   = 96
        private const val MEL_FEATURES   = 32
        private const val THRESHOLD      = 0.5f
        private const val COOLDOWN_MS    = 2_000L

        // Asset file names
        private const val MEL_ASSET = "melspectrogram.onnx"
        private const val EMB_ASSET = "embedding_model.onnx"
        private const val KW_ASSET  = "hey_shadow.onnx"

        // openWakeWord mel normalisation: output = (raw / 10) + 2
        private const val MEL_DIV  = 10f
        private const val MEL_ADD  = 2f
    }

    private var ortEnv: OrtEnvironment? = null
    private var melSession: OrtSession? = null
    private var embSession: OrtSession? = null
    private var kwSession:  OrtSession? = null

    private var audioRecord: AudioRecord? = null
    private var job: Job? = null
    private val scope = CoroutineScope(Dispatchers.Default + SupervisorJob())
    private var onWakeCallback: (() -> Unit)? = null

    // Ring buffers
    // Mel ring: flattened [MEL_WIN_FRAMES * MEL_FEATURES] in row-major order
    private val melRing  = FloatArray(MEL_WIN_FRAMES * MEL_FEATURES)
    private var melFill  = 0   // how many frames accumulated so far (capped at MEL_WIN_FRAMES)

    // Embedding ring: flattened [EMB_WIN_SIZE * EMB_FEATURES]
    private val embRing  = FloatArray(EMB_WIN_SIZE * EMB_FEATURES)
    private var embFill  = 0

    val isReady: Boolean get() = kwSession != null

    // ── Initialization ────────────────────────────────────────────────────────

    fun load(): Boolean {
        return try {
            ortEnv = OrtEnvironment.getEnvironment()
            val opts = OrtSession.SessionOptions().apply {
                setIntraOpNumThreads(2)
                setInterOpNumThreads(1)
            }
            melSession = ortEnv!!.createSession(loadAsset(MEL_ASSET), opts)
            embSession = ortEnv!!.createSession(loadAsset(EMB_ASSET), opts)
            kwSession  = ortEnv!!.createSession(loadAsset(KW_ASSET),  opts)

            Log.i(TAG, "All 3 wake-word models loaded. " +
                "mel_inputs=${melSession!!.inputNames} " +
                "emb_inputs=${embSession!!.inputNames} " +
                "kw_inputs=${kwSession!!.inputNames}")
            true
        } catch (e: Exception) {
            Log.w(TAG, "Wake word model load failed (${e.message}) — detector disabled")
            false
        }
    }

    private fun loadAsset(name: String): ByteArray =
        context.assets.open(name).use { it.readBytes() }

    // ── Start / stop ──────────────────────────────────────────────────────────

    fun start(onWake: () -> Unit) {
        if (!isReady) {
            Log.w(TAG, "start() called but models not loaded")
            return
        }
        onWakeCallback = onWake
        stop()

        val bufSize = AudioRecord.getMinBufferSize(
            SAMPLE_RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT
        ).coerceAtLeast(CHUNK_SAMPLES * 4)

        try {
            audioRecord = AudioRecord(
                MediaRecorder.AudioSource.MIC,
                SAMPLE_RATE,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
                bufSize,
            )
        } catch (e: SecurityException) {
            Log.e(TAG, "Microphone permission denied", e)
            return
        }

        melFill = 0
        embFill = 0
        melRing.fill(0f)
        embRing.fill(0f)

        audioRecord?.startRecording()
        job = scope.launch { captureLoop() }
        Log.i(TAG, "Wake word detector started")
    }

    fun stop() {
        job?.cancel()
        job = null
        audioRecord?.let {
            if (it.state == AudioRecord.STATE_INITIALIZED) {
                it.stop()
                it.release()
            }
        }
        audioRecord = null
    }

    fun release() {
        stop()
        scope.cancel()
        kwSession?.close();  kwSession  = null
        embSession?.close(); embSession = null
        melSession?.close(); melSession = null
        ortEnv?.close();     ortEnv     = null
    }

    // ── Audio capture loop ────────────────────────────────────────────────────

    private suspend fun captureLoop() {
        val shorts = ShortArray(CHUNK_SAMPLES)
        val floats = FloatArray(CHUNK_SAMPLES)

        while (coroutineContext.isActive) {
            val read = audioRecord?.read(shorts, 0, CHUNK_SAMPLES) ?: -1
            if (read <= 0) { delay(10); continue }

            // int16 → float32 normalised [-1, 1]
            for (i in 0 until read) floats[i] = shorts[i] / 32768f

            // Stage 1: mel spectrogram
            val newMelFrames = runMel(floats.copyOf(read)) ?: continue

            // Stage 2: try to produce a new embedding
            val newEmb = runEmbedding(newMelFrames) ?: continue

            // Stage 3: classify
            val prob = runClassifier(newEmb)
            if (prob >= THRESHOLD) {
                Log.i(TAG, "Wake word detected (p=%.3f)".format(prob))
                withContext(Dispatchers.Main) { onWakeCallback?.invoke() }
                delay(COOLDOWN_MS)
                // Reset embedding ring to avoid double-fire after cooldown
                embFill = 0
                embRing.fill(0f)
            }
        }
    }

    // ── Stage 1: mel spectrogram ──────────────────────────────────────────────
    //
    // Input:  [1, N_SAMPLES] float32
    // Output: [1, 1, T, 32] float32   (T ≈ N_SAMPLES/160 − 1, nominally 8 per 1280)
    // Normalise: val = (raw / 10) + 2

    private fun runMel(audio: FloatArray): FloatArray? {
        val env  = ortEnv    ?: return null
        val sess = melSession ?: return null
        return try {
            val inputName = sess.inputNames.first()
            val tensor = OnnxTensor.createTensor(
                env,
                FloatBuffer.wrap(audio),
                longArrayOf(1, audio.size.toLong())
            )
            val result = sess.run(mapOf(inputName to tensor))
            // Output shape [1, 1, T, 32] — get as nested array
            @Suppress("UNCHECKED_CAST")
            val raw = result[0].value as Array<Array<Array<FloatArray>>>
            tensor.close(); result.close()

            // raw[0][0] is [T][32]; flatten and normalise
            val frames = raw[0][0]
            val out = FloatArray(frames.size * MEL_FEATURES)
            for (t in frames.indices) {
                for (f in 0 until MEL_FEATURES) {
                    out[t * MEL_FEATURES + f] = (frames[t][f] / MEL_DIV) + MEL_ADD
                }
            }
            // Push into ring buffer (drop oldest if full)
            pushMel(out, frames.size)
            out
        } catch (e: Exception) {
            Log.e(TAG, "Mel inference error", e)
            null
        }
    }

    /** Push [nFrames] rows of 32 features into the mel ring (slide left, add right). */
    private fun pushMel(newFrames: FloatArray, nFrames: Int) {
        for (t in 0 until nFrames) {
            if (melFill < MEL_WIN_FRAMES) {
                // Ring not yet full — append to the right
                val dst = melFill * MEL_FEATURES
                System.arraycopy(newFrames, t * MEL_FEATURES, melRing, dst, MEL_FEATURES)
                melFill++
            } else {
                // Ring full — slide left by 1 frame, place new at end
                System.arraycopy(melRing, MEL_FEATURES, melRing, 0, (MEL_WIN_FRAMES - 1) * MEL_FEATURES)
                System.arraycopy(newFrames, t * MEL_FEATURES, melRing, (MEL_WIN_FRAMES - 1) * MEL_FEATURES, MEL_FEATURES)
            }
        }
    }

    // ── Stage 2: embedding model ──────────────────────────────────────────────
    //
    // Input:  [1, 76, 32, 1] float32
    // Output: [1, 1, 1, 96]  float32

    private fun runEmbedding(ignoredNewFrames: FloatArray): FloatArray? {
        if (melFill < MEL_WIN_FRAMES) return null   // not enough mel frames yet
        val env  = ortEnv    ?: return null
        val sess = embSession ?: return null
        return try {
            val inputName = sess.inputNames.first()
            // melRing is [MEL_WIN_FRAMES * MEL_FEATURES] in [frame][feature] order
            // Target shape [1, 76, 32, 1] — same layout, just wrap
            val tensor = OnnxTensor.createTensor(
                env,
                FloatBuffer.wrap(melRing),
                longArrayOf(1, MEL_WIN_FRAMES.toLong(), MEL_FEATURES.toLong(), 1)
            )
            val result = sess.run(mapOf(inputName to tensor))
            @Suppress("UNCHECKED_CAST")
            val raw = result[0].value as Array<Array<Array<FloatArray>>>
            tensor.close(); result.close()
            // raw[0][0][0] is float[96]
            val emb = raw[0][0][0]
            pushEmb(emb)
            emb
        } catch (e: Exception) {
            Log.e(TAG, "Embedding inference error", e)
            null
        }
    }

    private fun pushEmb(newEmb: FloatArray) {
        if (embFill < EMB_WIN_SIZE) {
            System.arraycopy(newEmb, 0, embRing, embFill * EMB_FEATURES, EMB_FEATURES)
            embFill++
        } else {
            System.arraycopy(embRing, EMB_FEATURES, embRing, 0, (EMB_WIN_SIZE - 1) * EMB_FEATURES)
            System.arraycopy(newEmb, 0, embRing, (EMB_WIN_SIZE - 1) * EMB_FEATURES, EMB_FEATURES)
        }
    }

    // ── Stage 3: classifier ───────────────────────────────────────────────────
    //
    // Input:  [1, 16, 96] float32
    // Output: [1, 1]      float32  (probability)

    private fun runClassifier(ignoredEmb: FloatArray): Float {
        if (embFill < EMB_WIN_SIZE) return 0f
        val env  = ortEnv   ?: return 0f
        val sess = kwSession ?: return 0f
        return try {
            val inputName = sess.inputNames.first()
            val tensor = OnnxTensor.createTensor(
                env,
                FloatBuffer.wrap(embRing),
                longArrayOf(1, EMB_WIN_SIZE.toLong(), EMB_FEATURES.toLong())
            )
            val result = sess.run(mapOf(inputName to tensor))
            @Suppress("UNCHECKED_CAST")
            val prob = ((result[0].value as Array<*>)[0] as FloatArray)[0]
            tensor.close(); result.close()
            prob
        } catch (e: Exception) {
            Log.e(TAG, "Classifier inference error", e)
            0f
        }
    }
}
