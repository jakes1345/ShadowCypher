package site.shadowcypher.assistant

import android.util.Log
import kotlinx.coroutines.*
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import org.json.JSONObject
import java.io.IOException

/**
 * LLM Client — talks to local Ollama or Guardian API for AI responses.
 * Handles: streaming text generation, request/response formatting, error handling.
 */
class LLMClient(private val apiKey: String, private val baseUrl: String = "http://10.0.2.2:9999") {

	companion object {
		private const val TAG = "LLMClient"
		private const val OLLAMA_URL = "http://10.0.2.2:11434"
		private const val OLLAMA_MODEL = "mistral:latest"
	}

	private val client = OkHttpClient.Builder()
		.connectTimeout(30, java.util.concurrent.TimeUnit.SECONDS)
		.readTimeout(60, java.util.concurrent.TimeUnit.SECONDS)
		.build()

	/**
	 * Query LLM for a response. Falls back: Guardian API → Ollama.
	 */
	suspend fun query(prompt: String): Result<String> = withContext(Dispatchers.IO) {
		try {
			// Try Guardian API first
			val guardianResult = queryGuardianAPI(prompt)
			if (guardianResult.isSuccess) {
				return@withContext guardianResult
			}

			// Fallback to Ollama
			Log.i(TAG, "Guardian API failed, falling back to Ollama")
			queryOllama(prompt)
		} catch (e: Exception) {
			Log.e(TAG, "LLM query failed", e)
			Result.failure(e)
		}
	}

	private suspend fun queryGuardianAPI(prompt: String): Result<String> = try {
		val body = JSONObject().apply {
			put("query", prompt)
		}.toString().toRequestBody("application/json".toMediaType())

		val request = Request.Builder()
			.url("$baseUrl/v1/llm/chat")
			.post(body)
			.addHeader("Authorization", "Bearer $apiKey")
			.addHeader("Accept", "application/json")
			.build()

		val response = client.newCall(request).execute()

		if (!response.isSuccessful) {
			throw IOException("Guardian API error: ${response.code}")
		}

		val responseBody = response.body?.string() ?: throw IOException("Empty response body")
		val json = JSONObject(responseBody)
		val reply = json.optString("response", null) ?: throw IOException("No response field in JSON")

		Log.i(TAG, "Guardian API response: ${reply.take(100)}...")
		Result.success(reply)
	} catch (e: Exception) {
		Log.w(TAG, "Guardian API query failed: ${e.message}")
		Result.failure(e)
	}

	private suspend fun queryOllama(prompt: String): Result<String> = try {
		val body = JSONObject().apply {
			put("model", OLLAMA_MODEL)
			put("prompt", prompt)
			put("stream", false)
			put("temperature", 0.7)
		}.toString().toRequestBody("application/json".toMediaType())

		val request = Request.Builder()
			.url("$OLLAMA_URL/api/generate")
			.post(body)
			.build()

		val response = client.newCall(request).execute()

		if (!response.isSuccessful) {
			throw IOException("Ollama error: ${response.code}")
		}

		val responseBody = response.body?.string() ?: throw IOException("Empty response body")
		val json = JSONObject(responseBody)
		val reply = json.optString("response", null) ?: throw IOException("No response field in JSON")

		Log.i(TAG, "Ollama response: ${reply.take(100)}...")
		Result.success(reply)
	} catch (e: Exception) {
		Log.w(TAG, "Ollama query failed: ${e.message}")
		Result.failure(e)
	}
}
