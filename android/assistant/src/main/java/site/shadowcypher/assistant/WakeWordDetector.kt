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
import java.io.File
import java.nio.FloatBuffer

/**
 * "Hey Shadow" wake word detection using openWakeWord ONNX model.
 *
 * Audio pipeline:
 *   Mic → 16kHz PCM16 → 1280-sample (80ms) frames → mel spectrogram →
 *   openWakeWord ONNX model → probability → threshold gate → callback
 *
 * Model: hey_shadow.onnx placed in android/assistant/src/main/assets/
 * If the model file is absent the detector silently skips inference.
 *
 * ONNX Runtime Android: com.microsoft.onnxruntime:onnxruntime-android:1.19.2
 */
class WakeWordDetector(private val context: Context) {

    companion object {
        private const val TAG = "WakeWordDetector"
        private const val SAMPLE_RATE = 16_000
        private const val FRAME_SAMPLES = 1280          // 80 ms @ 16kHz
        private const val DETECTION_THRESHOLD = 0.5f
        private const val MODEL_ASSET = "hey_shadow.onnx"

        // openWakeWord input node name (model-specific; verify with Netron if changed)
        private const val INPUT_NODE = "input"
    }

    private var ortEnv: OrtEnvironment? = null
    private var session: OrtSession? = null
    private var audioRecord: AudioRecord? = null
    private var job: Job? = null
    private val scope = CoroutineScope(Dispatchers.Default + SupervisorJob())
    private var onWakeCallback: (() -> Unit)? = null

    // Ring buffer — accumulate 3 frames (240ms context) before inference
    private val ringBuf = FloatArray(FRAME_SAMPLES * 3)
    private var ringPos = 0

    val isReady: Boolean get() = session != null

    // ── Initialization ────────────────────────────────────────────────────────

    fun load(): Boolean {
        return try {
            val modelBytes = context.assets.open(MODEL_ASSET).readBytes()
            ortEnv = OrtEnvironment.getEnvironment()
            val opts = OrtSession.SessionOptions().apply {
                setIntraOpNumThreads(1)
                setInterOpNumThreads(1)
            }
            session = ortEnv!!.createSession(modelBytes, opts)
            Log.i(TAG, "Wake word model loaded. Inputs: ${session!!.inputNames}")
            true
        } catch (e: Exception) {
            Log.w(TAG, "Wake word model unavailable (${e.message}) — skipping")
            false
        }
    }

    // ── Start / stop ──────────────────────────────────────────────────────────

    fun start(onWake: () -> Unit) {
        if (session == null) return
        onWakeCallback = onWake
        stop()

        val bufSize = AudioRecord.getMinBufferSize(
            SAMPLE_RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT
        ).coerceAtLeast(FRAME_SAMPLES * 2)

        try {
            audioRecord = AudioRecord(
                MediaRecorder.AudioSource.MIC,
                SAMPLE_RATE,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
                bufSize,
            )
        } catch (e: SecurityException) {
            Log.e(TAG, "Mic permission denied for wake word", e)
            return
        }

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
        session?.close()
        session = null
        ortEnv?.close()
        ortEnv = null
    }

    // ── Audio capture & inference ─────────────────────────────────────────────

    private suspend fun captureLoop() {
        val shorts = ShortArray(FRAME_SAMPLES)
        while (isActive) {
            val read = audioRecord?.read(shorts, 0, FRAME_SAMPLES) ?: -1
            if (read <= 0) { delay(10); continue }

            // Normalize int16 → float32 [-1, 1]
            for (i in 0 until read) {
                ringBuf[ringPos % ringBuf.size] = shorts[i] / 32768f
                ringPos++
            }

            // Run inference every FRAME_SAMPLES new samples once ring is seeded
            if (ringPos >= ringBuf.size) {
                val prob = infer(ringBuf.copyOf())
                if (prob >= DETECTION_THRESHOLD) {
                    Log.i(TAG, "Wake word detected (p=%.3f)".format(prob))
                    withContext(Dispatchers.Main) { onWakeCallback?.invoke() }
                    // Brief cooldown to avoid double-fire
                    delay(2_000)
                    ringPos = 0
                }
            }
        }
    }

    private fun infer(frames: FloatArray): Float {
        val env = ortEnv ?: return 0f
        val sess = session ?: return 0f
        return try {
            val tensor = OnnxTensor.createTensor(
                env,
                FloatBuffer.wrap(frames),
                longArrayOf(1, frames.size.toLong()),
            )
            val result = sess.run(mapOf(INPUT_NODE to tensor))
            val output = (result[0].value as Array<*>)[0] as FloatArray
            val prob = output[0]
            tensor.close()
            result.close()
            prob
        } catch (e: Exception) {
            Log.e(TAG, "Inference error", e)
            0f
        }
    }
}
