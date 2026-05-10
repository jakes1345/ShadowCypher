package site.shadowcypher.app.data

import android.content.Context
import android.content.SharedPreferences
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

private const val BASE_URL = "https://api.shadowcypher.site"
const val PREFS_NAME = "shadow_prefs"
const val PREF_API_KEY = "sc_api_key"

class GuardianRepository(private val context: Context) {

    private val prefs: SharedPreferences =
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    fun getApiKey(): String = prefs.getString(PREF_API_KEY, "") ?: ""

    fun saveApiKey(key: String) {
        prefs.edit().putString(PREF_API_KEY, key).apply()
    }

    fun clearApiKey() {
        prefs.edit().remove(PREF_API_KEY).apply()
    }

    private fun buildApi(apiKey: String): GuardianApi {
        val authInterceptor = Interceptor { chain ->
            val request = chain.request().newBuilder()
                .addHeader("Authorization", "Bearer $apiKey")
                .addHeader("Accept", "application/json")
                .addHeader("Content-Type", "application/json")
                .build()
            chain.proceed(request)
        }

        val logging = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BASIC
        }

        val client = OkHttpClient.Builder()
            .addInterceptor(authInterceptor)
            .addInterceptor(logging)
            .build()

        return Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(GuardianApi::class.java)
    }

    suspend fun fetchMe(): Result<Me> = runCatching {
        buildApi(getApiKey()).getMe()
    }

    suspend fun fetchSummary(): Result<GuardianSummary> = runCatching {
        buildApi(getApiKey()).getSummary()
    }

    suspend fun triggerScan(): Result<ScanResponse> = runCatching {
        buildApi(getApiKey()).triggerScan()
    }

    suspend fun fetchIncidents(): Result<List<Incident>> = runCatching {
        buildApi(getApiKey()).getIncidents()
    }

    suspend fun fetchAgents(): Result<List<Agent>> = runCatching {
        buildApi(getApiKey()).getAgents()
    }

    suspend fun createMission(agentId: String, script: String, label: String? = null): Result<CreateMissionResponse> = runCatching {
        buildApi(getApiKey()).createMission(agentId, CreateMissionRequest(script, label))
    }

    suspend fun getMission(missionId: String): Result<Mission> = runCatching {
        buildApi(getApiKey()).getMission(missionId)
    }

    suspend fun listMissions(agentId: String? = null): Result<MissionListResponse> = runCatching {
        buildApi(getApiKey()).listMissions(agentId)
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
