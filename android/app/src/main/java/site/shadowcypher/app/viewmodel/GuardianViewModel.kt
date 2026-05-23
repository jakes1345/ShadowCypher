package site.shadowcypher.app.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import site.shadowcypher.app.data.Agent
import site.shadowcypher.app.data.GuardianRepository
import site.shadowcypher.app.data.GuardianSummary
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

    init {
        if (repo.getApiKey().isNotBlank()) {
            refresh()
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
            summaryResult.onSuccess { _summary.value = it }
            summaryResult.onFailure {
                if (_error.value == null) _error.value = it.message
            }

            _isLoading.value = false
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

    @Deprecated("Typo — use acknowledgeScanTriggered()", ReplaceWith("acknowledgeScanTriggered()"))
    fun acknowledgeScaTriggered() = acknowledgeScanTriggered()

    fun setApiKey(key: String) {
        repo.saveApiKey(key)
        _apiKey.value = key
        if (key.isNotBlank()) {
            refresh()
        } else {
            _me.value = null
            _summary.value = null
        }
    }

    fun clearApiKey() {
        repo.clearApiKey()
        _apiKey.value = ""
        _me.value = null
        _summary.value = null
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
                .onSuccess { _missions.value = it.missions }
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
                }
                .onFailure { _missionStatus.value = "Failed: ${it.message}" }
        }
    }

    fun clearMissionStatus() {
        _missionStatus.value = null
    }
}
