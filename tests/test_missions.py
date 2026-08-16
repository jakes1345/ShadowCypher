"""
ShadowCypher Test Suite — GhostMission Base Class
Tests mission lifecycle: init, bus reporting, phase execution,
error recovery, and uuid uniqueness.
All AI/orchestrator calls are mocked — no real inference.
"""

import pytest
from unittest.mock import patch, MagicMock, call


@pytest.fixture
def mock_bus():
    with patch("shadowcypher.core.missions.bus") as m:
        yield m


@pytest.fixture
def mock_orchestrator():
    with patch("shadowcypher.core.missions.orchestrator") as m:
        m.run.return_value = "mock AI response"
        yield m


@pytest.fixture
def mission(mock_bus, mock_orchestrator):
    from shadowcypher.core.missions import GhostMission
    return GhostMission("10.0.0.1")


class TestMissionInit:

    def test_target_stored(self, mission):
        assert mission.target == "10.0.0.1"

    def test_mid_is_8_chars(self, mission):
        assert len(mission.mid) == 8

    def test_findings_starts_empty(self, mission):
        assert mission.findings == []

    def test_each_mission_gets_unique_mid(self, mock_bus, mock_orchestrator):
        from shadowcypher.core.missions import GhostMission
        mids = {GhostMission("1.1.1.1").mid for _ in range(20)}
        assert len(mids) == 20  # All unique


class TestReport:

    def test_report_publishes_to_bus(self, mission, mock_bus):
        mission.report("TEST_PHASE", "test message", 0.5)
        mock_bus.publish.assert_called_once()

    def test_report_publishes_correct_event_type(self, mission, mock_bus):
        mission.report("P1", "msg", 0.0)
        event_type = mock_bus.publish.call_args[0][0]
        assert event_type == "mission"

    def test_report_payload_contains_mid(self, mission, mock_bus):
        mission.report("P1", "msg", 0.0)
        payload = mock_bus.publish.call_args[0][1]
        assert payload["mid"] == mission.mid

    def test_report_payload_contains_phase(self, mission, mock_bus):
        mission.report("RECON", "scanning", 0.25)
        payload = mock_bus.publish.call_args[0][1]
        assert payload["phase"] == "RECON"

    def test_report_payload_contains_message(self, mission, mock_bus):
        mission.report("X", "hello world", 0.0)
        payload = mock_bus.publish.call_args[0][1]
        assert payload["message"] == "hello world"

    def test_report_payload_contains_progress(self, mission, mock_bus):
        mission.report("X", "msg", 0.75)
        payload = mock_bus.publish.call_args[0][1]
        assert payload["progress"] == 0.75


class TestRunPhase:

    def test_run_phase_calls_orchestrator(self, mission, mock_orchestrator):
        mission._run_phase("ANALYSIS", "analyze this", 0.5, "Analyzing...")
        mock_orchestrator.run.assert_called_once_with("analyze this")

    def test_run_phase_returns_ai_response(self, mission, mock_orchestrator):
        result = mission._run_phase("P", "prompt", 0.0, "status")
        assert result == "mock AI response"

    def test_run_phase_appends_to_findings(self, mission, mock_orchestrator):
        mission._run_phase("PHASE1", "prompt1", 0.3, "status1")
        assert len(mission.findings) == 1
        assert mission.findings[0]["phase"] == "PHASE1"
        assert mission.findings[0]["result"] == "mock AI response"

    def test_multiple_phases_all_in_findings(self, mission, mock_orchestrator):
        mock_orchestrator.run.side_effect = ["result_a", "result_b", "result_c"]
        mission._run_phase("A", "p1", 0.1, "s1")
        mission._run_phase("B", "p2", 0.5, "s2")
        mission._run_phase("C", "p3", 1.0, "s3")
        assert len(mission.findings) == 3
        phases = [f["phase"] for f in mission.findings]
        assert phases == ["A", "B", "C"]

    def test_run_phase_publishes_status_report(self, mission, mock_bus, mock_orchestrator):
        mock_bus.publish.reset_mock()
        mission._run_phase("STATUS_TEST", "prompt", 0.5, "Status message")
        # At least one publish call for the status report
        assert mock_bus.publish.called

    def test_run_phase_orchestrator_error_returns_error_string(self, mission, mock_orchestrator):
        mock_orchestrator.run.side_effect = RuntimeError("AI offline")
        result = mission._run_phase("ERR_PHASE", "prompt", 0.5, "status")
        assert "ERR_PHASE" in result or "ERROR" in result

    def test_run_phase_orchestrator_error_still_appends_finding(self, mission, mock_orchestrator):
        mock_orchestrator.run.side_effect = ValueError("boom")
        mission._run_phase("ERR", "p", 0.5, "s")
        assert len(mission.findings) == 1  # Error still recorded

    def test_run_phase_orchestrator_error_does_not_raise(self, mission, mock_orchestrator):
        mock_orchestrator.run.side_effect = Exception("any error")
        # Must not propagate the exception
        mission._run_phase("SAFE", "p", 0.5, "s")


class TestEmergencySever:

    def test_sever_publishes_abort_event(self, mission, mock_bus):
        mock_bus.publish.reset_mock()
        mission._emergency_sever()
        assert mock_bus.publish.called
        payload = mock_bus.publish.call_args[0][1]
        assert payload["phase"] == "ABORT"

    def test_sever_progress_is_1(self, mission, mock_bus):
        mock_bus.publish.reset_mock()
        mission._emergency_sever()
        payload = mock_bus.publish.call_args[0][1]
        assert payload["progress"] == 1.0


class TestExecuteNotImplemented:

    def test_base_execute_raises(self, mission):
        with pytest.raises(NotImplementedError):
            mission.execute()
