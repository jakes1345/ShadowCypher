package site.shadowcypher.app.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import site.shadowcypher.app.data.GuardianRepository
import site.shadowcypher.app.data.GuardianSummary
import site.shadowcypher.app.data.Me

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

    fun acknowledgeScaTriggered() {
        _scanTriggered.value = false
    }

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
}
