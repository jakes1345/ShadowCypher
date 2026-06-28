package site.shadowcypher.app.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import site.shadowcypher.app.data.Agent
import site.shadowcypher.app.data.CveAlert
import site.shadowcypher.app.data.GuardianRepository
import site.shadowcypher.app.data.GuardianSummary
import site.shadowcypher.app.data.Incident
import site.shadowcypher.app.data.Me
import site.shadowcypher.app.data.Mission

class GuardianViewModel(application: Application) : AndroidViewModel(application) {

    private val repo = GuardianRepository.get(application)

    private val _me = MutableStateFlow<Me?>(null)
    val me: StateFlow<Me?> = _me.asStateFlow()

    private val _summary = MutableStateFlow<GuardianSummary?>(null)
    val summary: StateFlow<GuardianSummary?> = _summary.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error.asStateFlow()

    private val _scanTriggered = MutableStateFlow(false)
    val scanTriggered: StateFlow<Boolean> = _scanTriggered.asStateFlow()

    private val _agents = MutableStateFlow<List<Agent>>(emptyList())
    val agents: StateFlow<List<Agent>> = _agents.asStateFlow()

    private val _missions = MutableStateFlow<List<Mission>>(emptyList())
    val missions: StateFlow<List<Mission>> = _missions.asStateFlow()

    private val _missionStatus = MutableStateFlow<String?>(null)
    val missionStatus: StateFlow<String?> = _missionStatus.asStateFlow()

    private val _apiKey = MutableStateFlow(repo.getApiKey())
    val apiKey: StateFlow<String> = _apiKey.asStateFlow()

    // Flattened CVE alerts derived from summary — own StateFlow so CVE screen
    // can observe it without re-collecting the whole summary.
    private val _cveAlerts = MutableStateFlow<List<CveAlert>>(emptyList())
    val cveAlerts: StateFlow<List<CveAlert>> = _cveAlerts.asStateFlow()

    private var autoRefreshJob: Job? = null
    private val activeMissionPolls = mutableMapOf<String, Job>()

    init {
        if (repo.getApiKey().isNotBlank()) {
            refresh()
            startAutoRefresh()
        }
    }

    fun refresh() {
        viewModelScope.launch {
            _isLoading.value = true
            _error.value = null

            val meResult = repo.fetchMe()
            meResult.onSuccess { _me.value = it }
            meResult.onFailure { _error.value = it.message }

            val summaryResult = repo.fetchSummary()
            summaryResult.onSuccess {
                _summary.value = it
                _cveAlerts.value = it.cve_alerts
            }
            summaryResult.onFailure {
                if (_error.value == null) _error.value = it.message
            }

            _isLoading.value = false
        }
    }

    private fun startAutoRefresh() {
        autoRefreshJob?.cancel()
        autoRefreshJob = viewModelScope.launch {
            while (true) {
                delay(30_000)
                if (repo.getApiKey().isNotBlank()) {
                    repo.fetchSummary().onSuccess {
                        _summary.value = it
                        _cveAlerts.value = it.cve_alerts
                    }
                }
            }
        }
    }

    fun triggerScan() {
        viewModelScope.launch {
            _error.value = null
            val result = repo.triggerScan()
            result.onSuccess { _scanTriggered.value = true }
            result.onFailure { _error.value = "Scan failed: ${it.message}" }
        }
    }

    fun acknowledgeScanTriggered() {
        _scanTriggered.value = false
    }

    fun acknowledgeIncident(incidentId: String) {
        viewModelScope.launch {
            repo.acknowledgeIncident(incidentId)
                .onSuccess {
                    // Optimistically update local state
                    _summary.value = _summary.value?.let { s ->
                        s.copy(incidents = s.incidents.map { i ->
                            if (i.id == incidentId) i.copy(resolved = true) else i
                        })
                    }
                }
                .onFailure { _error.value = "Acknowledge failed: ${it.message}" }
        }
    }

    fun setApiKey(key: String) {
        repo.saveApiKey(key)
        _apiKey.value = key
        if (key.isNotBlank()) {
            refresh()
            startAutoRefresh()
        } else {
            autoRefreshJob?.cancel()
            _me.value = null
            _summary.value = null
            _cveAlerts.value = emptyList()
        }
    }

    fun clearApiKey() {
        repo.clearApiKey()
        _apiKey.value = ""
        autoRefreshJob?.cancel()
        _me.value = null
        _summary.value = null
        _cveAlerts.value = emptyList()
    }

    fun dismissError() {
        _error.value = null
    }

    fun loadAgents() {
        viewModelScope.launch {
            repo.fetchAgents()
                .onSuccess { _agents.value = it }
                .onFailure { _error.value = "Agents: ${it.message}" }
        }
    }

    fun loadMissions(agentId: String? = null) {
        viewModelScope.launch {
            repo.listMissions(agentId)
                .onSuccess { resp ->
                    _missions.value = resp.missions
                    // Start polling any missions that are still running
                    resp.missions.filter { it.status == "running" || it.status == "queued" }
                        .forEach { pollMissionUntilDone(it.id) }
                }
                .onFailure { _error.value = "Missions: ${it.message}" }
        }
    }

    fun submitMission(agentId: String, script: String, label: String? = null) {
        viewModelScope.launch {
            _missionStatus.value = "Submitting…"
            repo.createMission(agentId, script, label)
                .onSuccess {
                    _missionStatus.value = "Mission ${it.mission_id} queued"
                    loadMissions(agentId)
                    pollMissionUntilDone(it.mission_id)
                }
                .onFailure { _missionStatus.value = "Failed: ${it.message}" }
        }
    }

    fun pollMissionUntilDone(missionId: String) {
        if (activeMissionPolls.containsKey(missionId)) return
        activeMissionPolls[missionId] = viewModelScope.launch {
            repeat(120) { // max 6 minutes of polling
                delay(3_000)
                repo.getMission(missionId).onSuccess { updated ->
                    _missions.value = _missions.value.map { if (it.id == missionId) updated else it }
                    if (updated.status == "completed" || updated.status == "failed") {
                        activeMissionPolls.remove(missionId)
                        return@launch
                    }
                }.onFailure {
                    activeMissionPolls.remove(missionId)
                    return@launch
                }
            }
            activeMissionPolls.remove(missionId)
        }
    }

    fun clearMissionStatus() {
        _missionStatus.value = null
    }
}
