package site.shadowcypher.app.data

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

interface GuardianApi {

    @GET("/v1/me")
    suspend fun getMe(): Me

    @GET("/v1/guardian/summary")
    suspend fun getSummary(): GuardianSummary

    @POST("/v1/scans")
    suspend fun triggerScan(@Body body: Map<String, String> = emptyMap()): ScanResponse

    @GET("/v1/incidents")
    suspend fun getIncidents(): List<Incident>

    @GET("/v1/agents")
    suspend fun getAgents(): AgentsResponse

    @POST("/v1/agents/{agent_id}/missions")
    suspend fun createMission(
        @Path("agent_id") agentId: String,
        @Body body: CreateMissionRequest
    ): CreateMissionResponse

    @GET("/v1/missions/{mission_id}")
    suspend fun getMission(@Path("mission_id") missionId: String): Mission

    @GET("/v1/missions")
    suspend fun listMissions(@Query("agent_id") agentId: String? = null): MissionListResponse
}
