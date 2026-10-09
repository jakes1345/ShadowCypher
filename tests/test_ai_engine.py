"""
ShadowCypher Test Suite — AI Engine
Tests model selection, backend fallback, and generation routing.
No actual model required — all LLM calls are mocked.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestAIEngine:
    """Test the dual-backend AI engine logic."""

    @pytest.fixture
    def engine(self):
        from shadowcypher.ai.engine import AIEngine
        return AIEngine()

    def test_initial_state(self, engine):
        assert engine.is_loaded is False
        assert engine.is_loading is False
        assert engine.backend is None
        assert engine.model_name is None

    @patch("shadowcypher.ai.engine.AIEngine._select_ollama_model", return_value=None)
    @patch("shadowcypher.ai.engine.provider_registry")
    def test_generate_when_not_loaded(self, mock_registry, mock_select, engine):
        mock_registry.active = None
        result = engine.generate("test prompt")
        assert "[AI offline]" in result or "not loaded" in result.lower()

    @patch("shadowcypher.ai.engine.AIEngine.check_ollama", return_value=True)
    @patch("shadowcypher.ai.engine.AIEngine.list_ollama_models", return_value=["shadowcypher-ai:latest", "llama3:latest"])
    @patch("shadowcypher.ai.engine.AIEngine._ollama_request")
    def test_ollama_load_and_model_selection(self, mock_req, mock_list, mock_check, engine):
        mock_req.return_value = {"message": {"content": "ok"}}
        result = engine.load()
        assert result is True
        assert engine.backend == "ollama"
        assert engine.model_name == "shadowcypher-ai:latest"  # First preference

    @patch("shadowcypher.ai.engine.AIEngine.check_ollama", return_value=True)
    @patch("shadowcypher.ai.engine.AIEngine.list_ollama_models", return_value=["qwen2.5-coder:7b", "mistral:latest"])
    @patch("shadowcypher.ai.engine.AIEngine._ollama_request")
    def test_model_preference_order(self, mock_req, mock_list, mock_check, engine):
        mock_req.return_value = {"message": {"content": "ok"}}
        engine.load()
        # qwen2.5-coder should be selected over mistral per preference list
        assert "qwen2.5-coder" in engine.model_name

    @patch("shadowcypher.ai.engine.AIEngine.check_ollama", return_value=True)
    @patch("shadowcypher.ai.engine.AIEngine._ollama_request")
    def test_generate_routes_to_ollama(self, mock_req, mock_check, engine):
        engine._loaded = True
        engine._backend = "ollama"
        engine._model_name = "test-model"
        mock_req.return_value = {"message": {"content": "test response"}}

        result = engine.generate("hello")
        assert result == "test response"

    def test_unload(self, engine):
        engine._loaded = True
        engine._backend = "ollama"
        engine._model_name = "test"
        engine.unload()
        assert engine.is_loaded is False
        assert engine.backend is None

    def test_double_load_returns_true(self, engine):
        engine._loaded = True
        assert engine.load() is True  # Should short-circuit
