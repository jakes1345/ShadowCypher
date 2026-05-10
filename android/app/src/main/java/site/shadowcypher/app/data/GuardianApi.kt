package site.shadowcypher.app.data

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST

interface GuardianApi {

    @GET("/v1/me")
    suspend fun getMe(): Me

    @GET("/v1/guardian/summary")
    suspend fun getSummary(): GuardianSummary

    @POST("/v1/scans")
    suspend fun triggerScan(@Body body: Map<String, String> = emptyMap()): ScanResponse

    @GET("/v1/incidents")
    suspend fun getIncidents(): List<Incident>
}
