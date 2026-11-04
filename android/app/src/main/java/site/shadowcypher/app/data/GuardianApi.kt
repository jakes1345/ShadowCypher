package site.shadowcypher.app.data

import retrofit2.Response
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

    @GET("/v1/incidents")
    suspend fun getIncidents(): IncidentsResponse

    @POST("/v1/incidents/ack")
    suspend fun acknowledgeIncident(@Query("incident_id") id: String): Response<Unit>

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

    @POST("/v1/assistant/query")
    suspend fun queryAssistant(@Body body: AiQueryRequest): AiQueryResponse
}

/** Sign-in through the browser. These routes take no API key. */
interface DeviceAuthApi {

    @POST("/v1/auth/device")
    suspend fun start(@Body body: DeviceAuthStartRequest): DeviceAuthStart

    @POST("/v1/auth/device/poll")
    suspend fun poll(@Body body: DeviceAuthPollRequest): Response<DeviceAuthPoll>
}
