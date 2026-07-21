package site.shadowcypher.app.data

import com.google.gson.annotations.SerializedName

data class Me(
    val email: String,
    val plan: String?,
    val effective_plan: String,
    val in_trial: Boolean,
    val trial_days_remaining: Int?
)

data class Agent(
    val id: String,
    val hostname: String,
    val online: Boolean,
    val last_seen_at: String?,
    val os: String? = null,
    val agent_version: String? = null
)

// Wrapper matching backend { agents: [...] } envelope from GET /v1/agents
data class AgentsResponse(val agents: List<Agent>)

data class Device(
    val ip: String?,
    val hostname: String?,
    val mac: String?,
    @SerializedName("device_type") val os: String?,
    val vendor: String?,
    val status: String? = null
)

data class Incident(
    val id: String,
    @SerializedName("category") val type: String?,
    val severity: String?,
    @SerializedName("title") val description: String?,
    val created_at: String,
    @SerializedName("acknowledged") val resolved: Boolean
)

data class CveAlert(
    val cve_id: String,
    val severity: String?,
    val description: String?,
    val affected_device: String?
)

data class GuardianSummary(
    val agents: List<Agent>,
    val devices: List<Device>,
    val incidents: List<Incident>,
    val cve_alerts: List<CveAlert>,
    val last_scan_at: String?
)

data class ScanResponse(val success: Boolean?, val message: String?)

data class Mission(
    val id: String,
    val agent_id: String,
    val status: String,
    val created_at: String,
    val started_at: String?,
    val completed_at: String?,
    val result_output: String?,
    val exit_code: Int?
)

data class CreateMissionRequest(val script: String, val label: String? = null)
data class CreateMissionResponse(val mission_id: String, val status: String)
data class MissionListResponse(val missions: List<Mission>)

data class AiChatMessage(val role: String, val content: String)
data class AiQueryRequest(val question: String, val tier: String = "fast", val history: List<AiChatMessage> = emptyList())
data class AiQueryResponse(val answer: String?, val model: String?, val provider: String?, val error: String?)
