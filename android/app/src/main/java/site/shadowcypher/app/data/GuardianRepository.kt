package site.shadowcypher.app.data

import android.content.Context
import android.content.SharedPreferences
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

private const val BASE_URL_REMOTE = "https://api.shadowcypher.site"
const val PREFS_NAME = "shadow_prefs"
const val PREF_API_KEY = "sc_api_key"
const val PREF_BASE_URL = "sc_base_url"

class GuardianRepository(private val context: Context) {

    private val prefs: SharedPreferences =
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    @Volatile private var _cachedApiKey: String = ""
    @Volatile private var _cachedApi: GuardianApi? = null

    fun getApiKey(): String = prefs.getString(PREF_API_KEY, "") ?: ""

    fun saveApiKey(key: String) {
        prefs.edit().putString(PREF_API_KEY, key).apply()
    }

    fun clearApiKey() {
        prefs.edit().remove(PREF_API_KEY).apply()
        _cachedApiKey = ""
        _cachedApi = null
    }

    fun getBaseUrl(): String = prefs.getString(PREF_BASE_URL, null)?.takeIf { it.isNotBlank() } ?: BASE_URL_REMOTE

    fun setBaseUrl(url: String) {
        prefs.edit().putString(PREF_BASE_URL, url).apply()
        _cachedApi = null  // Invalidate cache
    }

    private fun buildApi(apiKey: String): GuardianApi {
        _cachedApi?.let { if (apiKey == _cachedApiKey) return it }

        val authInterceptor = Interceptor { chain ->
            val request = chain.request().newBuilder()
                .addHeader("Authorization", "Bearer $apiKey")
                .addHeader("Accept", "application/json")
                .build()
            chain.proceed(request)
        }

        val logging = HttpLoggingInterceptor().apply {
            level = if (android.os.Build.VERSION.SDK_INT > 0 && isDebugBuild())
                HttpLoggingInterceptor.Level.BASIC
            else
                HttpLoggingInterceptor.Level.NONE
        }

        val client = OkHttpClient.Builder()
            .addInterceptor(authInterceptor)
            .addInterceptor(logging)
            .build()

        val baseUrl = getBaseUrl()
        val api = Retrofit.Builder()
            .baseUrl(baseUrl)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(GuardianApi::class.java)

        _cachedApiKey = apiKey
        _cachedApi = api
        return api
    }

    private fun isDebugBuild(): Boolean = try {
        context.packageManager.getApplicationInfo(context.packageName, 0)
            .flags and android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE != 0
    } catch (e: Exception) { false }

    private fun requireKey(): String {
        val key = getApiKey()
        if (key.isBlank()) throw IllegalStateException("No API key configured. Please add your key in Settings.")
        return key
    }

    suspend fun fetchMe(): Result<Me> = runCatching { buildApi(requireKey()).getMe() }

    suspend fun fetchSummary(): Result<GuardianSummary> = runCatching { buildApi(requireKey()).getSummary() }

    suspend fun fetchIncidents(): Result<List<Incident>> = runCatching { buildApi(requireKey()).getIncidents().incidents }

    private val deviceAuthApi: DeviceAuthApi by lazy {
        Retrofit.Builder()
            .baseUrl(getBaseUrl())
            .client(OkHttpClient.Builder().build())
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(DeviceAuthApi::class.java)
    }

    suspend fun startDeviceAuth(): Result<DeviceAuthStart> = runCatching {
        deviceAuthApi.start(DeviceAuthStartRequest("Guardian (Android)"))
    }

    /** Returns the poll status; "authorized" responses carry api_key. 403/410 bodies carry denied/expired. */
    suspend fun pollDeviceAuth(deviceCode: String): Result<DeviceAuthPoll> = runCatching {
        val resp = deviceAuthApi.poll(DeviceAuthPollRequest(deviceCode))
        resp.body() ?: when (resp.code()) {
            403 -> DeviceAuthPoll("denied", null, null, null)
            410 -> DeviceAuthPoll("expired", null, null, null)
            404 -> DeviceAuthPoll("expired", null, null, "invalid_code")
            else -> throw IllegalStateException("Sign-in check failed (HTTP ${resp.code()})")
        }
    }

    suspend fun fetchAgents(): Result<List<Agent>> = runCatching { buildApi(requireKey()).getAgents().agents }

    suspend fun createMission(agentId: String, script: String, label: String? = null): Result<CreateMissionResponse> = runCatching {
        buildApi(requireKey()).createMission(agentId, CreateMissionRequest(script, label))
    }

    suspend fun getMission(missionId: String): Result<Mission> = runCatching {
        buildApi(requireKey()).getMission(missionId)
    }

    suspend fun acknowledgeIncident(id: String): Result<Unit> = runCatching {
        val resp = buildApi(requireKey()).acknowledgeIncident(id)
        if (!resp.isSuccessful) throw IllegalStateException("HTTP ${resp.code()}")
        Unit
    }

    suspend fun listMissions(agentId: String? = null): Result<MissionListResponse> = runCatching {
        buildApi(requireKey()).listMissions(agentId)
    }

    suspend fun queryAssistant(question: String, history: List<AiChatMessage>): Result<AiQueryResponse> = runCatching {
        try {
            buildApi(requireKey()).queryAssistant(AiQueryRequest(question = question, history = history.takeLast(8)))
        } catch (e: retrofit2.HttpException) {
            throw IllegalStateException(apiErrorMessage(e))
        }
    }

    /** Turns an API error body ({error, reason, hint}) into a readable message. */
    private fun apiErrorMessage(e: retrofit2.HttpException): String {
        val body = try { e.response()?.errorBody()?.string() } catch (_: Exception) { null }
        val json = try { body?.let { org.json.JSONObject(it) } } catch (_: Exception) { null }
        val reason = json?.optString("reason")?.takeIf { it.isNotBlank() }
        val hint = json?.optString("hint")?.takeIf { it.isNotBlank() }
        return when {
            reason != null -> reason
            json?.optString("error") == "quota_exceeded" -> "Monthly AI quota used up." + (hint?.let { " $it" } ?: "")
            json?.optString("error")?.isNotBlank() == true -> "${json.optString("error")} (HTTP ${e.code()})"
            else -> "HTTP ${e.code()}"
        }
    }

    companion object {
        @Volatile
        private var instance: GuardianRepository? = null

        fun get(context: Context): GuardianRepository =
            instance ?: synchronized(this) {
                instance ?: GuardianRepository(context.applicationContext).also { instance = it }
            }
    }
}
