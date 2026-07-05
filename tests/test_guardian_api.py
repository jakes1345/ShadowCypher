"""
Integration tests for Guardian Local API.
Validates all endpoints work correctly with real data flow.
"""

import requests
import json
import time
from typing import Dict, Any

BASE_URL = "http://localhost:9999"
TOKEN = "Operator"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


def test_health_check():
    """Test API health endpoint."""
    resp = requests.get(f"{BASE_URL}/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    print("✓ Health check passed")


def test_operator_profile():
    """Test getting operator profile."""
    resp = requests.get(f"{BASE_URL}/v1/me", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "operator@shadowcypher.site"
    assert data["plan"] == "personal"
    print("✓ Operator profile retrieved")


def test_guardian_summary():
    """Test guardian summary endpoint."""
    resp = requests.get(f"{BASE_URL}/v1/guardian/summary", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "devices" in data
    assert "incidents" in data
    assert "cve_alerts" in data
    assert "agents" in data
    print(f"✓ Guardian summary: {len(data['devices'])} devices, {len(data['incidents'])} incidents")


def test_incidents():
    """Test getting incidents."""
    resp = requests.get(f"{BASE_URL}/v1/incidents", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    print(f"✓ Retrieved {len(data)} incidents")


def test_agents():
    """Test getting agents."""
    resp = requests.get(f"{BASE_URL}/v1/agents", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "agents" in data
    print(f"✓ Retrieved {len(data['agents'])} agents")


def test_scan_history():
    """Test getting scan history."""
    resp = requests.get(f"{BASE_URL}/v1/scan-history?limit=10", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    print(f"✓ Retrieved {len(data)} historical scans")


def test_statistics():
    """Test getting statistics."""
    resp = requests.get(f"{BASE_URL}/v1/statistics", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_scans" in data
    print(f"✓ Statistics: {data.get('total_scans', 0)} total scans")


def test_analytics_effectiveness():
    """Test scan effectiveness analytics."""
    resp = requests.get(f"{BASE_URL}/v1/analytics/effectiveness", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_scans" in data
    assert "completion_rate" in data
    assert "avg_devices_per_scan" in data
    print(f"✓ Effectiveness: {data['total_scans']} scans, {data['completion_rate']*100:.0f}% completion")


def test_analytics_timeline():
    """Test device discovery timeline."""
    resp = requests.get(f"{BASE_URL}/v1/analytics/timeline?days=30", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "timeline" in data
    print(f"✓ Timeline: {len(data.get('timeline', []))} data points")


def test_analytics_risk_distribution():
    """Test risk distribution analytics."""
    resp = requests.get(f"{BASE_URL}/v1/analytics/risk-distribution", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "distribution" in data
    dist = data["distribution"]
    print(f"✓ Risk distribution: HIGH={dist.get('HIGH', 0)}, MEDIUM={dist.get('MEDIUM', 0)}, LOW={dist.get('LOW', 0)}")


def test_analytics_threats():
    """Test threat summary analytics."""
    resp = requests.get(f"{BASE_URL}/v1/analytics/threats", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "critical_incidents" in data
    assert "high_risk_devices" in data
    assert "unique_threat_types" in data
    print(f"✓ Threat summary: {data['critical_incidents']} critical, {data['unique_threat_types']} unique threats")


def test_analytics_top_devices():
    """Test top devices by incident count."""
    resp = requests.get(f"{BASE_URL}/v1/analytics/top-devices?limit=5", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "top_devices" in data
    print(f"✓ Top devices: {len(data['top_devices'])} devices retrieved")


def test_mission_lifecycle():
    """Test full mission lifecycle: create, monitor, complete."""
    # Trigger a scan
    resp = requests.post(f"{BASE_URL}/v1/scans", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] == True
    print(f"✓ Scan triggered: {data['message']}")

    # Extract mission ID from message
    import re
    match = re.search(r"mission-[a-f0-9]+", data["message"])
    if match:
        mission_id = match.group(0)

        # Wait for mission to complete
        time.sleep(2)

        # Get mission status
        resp = requests.get(f"{BASE_URL}/v1/missions/{mission_id}", headers=HEADERS)
        assert resp.status_code == 200
        mission = resp.json()
        print(f"✓ Mission status: {mission['status']}, {mission['devices_found']} devices found")

        return mission_id
    return None


def test_missions_list():
    """Test listing missions."""
    resp = requests.get(f"{BASE_URL}/v1/missions?limit=10", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "missions" in data
    print(f"✓ Missions list: {len(data['missions'])} missions")

    if data["missions"]:
        mission = data["missions"][0]
        print(f"  Latest mission: {mission['id']} ({mission['status']}), {mission['devices_found']} devices")


def test_llm_chat():
    """Test LLM chat endpoint."""
    payload = {"query": "hello"}
    resp = requests.post(f"{BASE_URL}/v1/llm/chat", json=payload, headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data
    assert "confidence" in data
    print(f"✓ LLM chat: Got response (confidence: {data['confidence']})")


def test_unauthorized_access():
    """Test that endpoints require proper auth."""
    resp = requests.get(f"{BASE_URL}/v1/me")  # No auth header
    assert resp.status_code == 401

    resp = requests.get(f"{BASE_URL}/v1/me", headers={"Authorization": "Bearer invalid"})
    assert resp.status_code == 403

    print("✓ Authorization checks passed")


def run_all_tests():
    """Run all integration tests."""
    print("\n" + "="*60)
    print("Guardian API Integration Tests")
    print("="*60 + "\n")

    tests = [
        ("Health Check", test_health_check),
        ("Authorization", test_unauthorized_access),
        ("Operator Profile", test_operator_profile),
        ("Guardian Summary", test_guardian_summary),
        ("Incidents", test_incidents),
        ("Agents", test_agents),
        ("Scan History", test_scan_history),
        ("Statistics", test_statistics),
        ("Analytics: Effectiveness", test_analytics_effectiveness),
        ("Analytics: Timeline", test_analytics_timeline),
        ("Analytics: Risk Distribution", test_analytics_risk_distribution),
        ("Analytics: Threats", test_analytics_threats),
        ("Analytics: Top Devices", test_analytics_top_devices),
        ("Mission Lifecycle", test_mission_lifecycle),
        ("Missions List", test_missions_list),
        ("LLM Chat", test_llm_chat),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            print(f"\n[{name}]")
            test_func()
            passed += 1
        except Exception as e:
            print(f"✗ {name} failed: {e}")
            failed += 1

    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60 + "\n")

    return failed == 0


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
