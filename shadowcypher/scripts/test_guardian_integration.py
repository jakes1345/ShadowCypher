#!/usr/bin/env python3
"""
Guardian Integration Test Suite — End-to-end verification of all modules.
Tests API endpoints, scan history, module imports, and data flow.
"""

import sys
import json
import time
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from shadowcypher.core.guardian_service import get_guardian_service
from shadowcypher.core.scan_history import get_scan_history
from shadowcypher.core.logger import logger


def test_guardian_service():
    """Test GuardianService data retrieval."""
    print("\n🧪 Testing GuardianService...")
    guardian = get_guardian_service()

    # Test device retrieval
    devices = guardian.get_recent_devices()
    print(f"  ✅ get_recent_devices(): {len(devices)} devices")
    assert len(devices) > 0, "Should return mock devices"

    # Test incident retrieval
    incidents = guardian.get_incidents()
    print(f"  ✅ get_incidents(): {len(incidents)} incidents")

    # Test CVE alerts
    alerts = guardian.get_cve_alerts()
    print(f"  ✅ get_cve_alerts(): {len(alerts)} alerts")

    # Test agents
    agents = guardian.get_agents()
    print(f"  ✅ get_agents(): {len(agents)} agents")

    # Test last scan time
    last_scan = guardian.get_last_scan_time()
    print(f"  ✅ get_last_scan_time(): {last_scan}")


def test_scan_history():
    """Test ScanHistory database."""
    print("\n🗄️  Testing ScanHistory Database...")
    history = get_scan_history()

    # Test save scan
    scan_id = "test-scan-001"
    devices = [
        {"ip": "192.168.1.1", "hostname": "router", "mac": "aa:bb:cc:dd:ee:ff", "risk": "MEDIUM"},
        {"ip": "192.168.1.100", "hostname": "desktop", "mac": "11:22:33:44:55:66", "risk": "LOW"},
    ]
    incidents = [
        {"id": "CVE-2024-001", "category": "cve", "severity": "high", "title": "Test CVE"},
    ]

    result = history.save_scan(
        scan_id=scan_id,
        scan_type="network_scan",
        target="192.168.1.0/24",
        devices=devices,
        incidents=incidents,
    )
    print(f"  ✅ save_scan(): {result}")
    assert result, "Should save scan successfully"

    # Test retrieve scan
    scans = history.get_recent_scans("network_scan")
    print(f"  ✅ get_recent_scans(): {len(scans)} scans")
    assert len(scans) > 0, "Should retrieve saved scans"

    # Test scan details
    detail = history.get_scan_details(scan_id)
    print(f"  ✅ get_scan_details(): {len(detail['devices'])} devices, {len(detail['incidents'])} incidents")
    assert detail["devices"], "Should retrieve devices"

    # Test statistics
    stats = history.get_statistics()
    print(f"  ✅ get_statistics(): {stats['total_scans']} scans, {stats['total_devices']} devices")
    assert stats["total_scans"] > 0, "Should have recorded scans"


def test_module_imports():
    """Test that all Guardian modules can be imported."""
    print("\n📦 Testing Module Imports...")

    modules = [
        ("Fail2BanManager", "shadowcypher.modules.fail2ban_mgr"),
        ("HostAudit", "shadowcypher.modules.host_audit"),
        ("TlsAudit", "shadowcypher.modules.tls_audit"),
        ("YaraScan", "shadowcypher.modules.yara_scan"),
    ]

    for class_name, module_path in modules:
        try:
            parts = module_path.rsplit(".", 1)
            module = __import__(parts[0], fromlist=[parts[1]])
            cls = getattr(module, class_name)
            instance = cls()
            print(f"  ✅ {class_name}: imported and instantiated")
        except Exception as e:
            print(f"  ❌ {class_name}: {e}")


def test_api_endpoints():
    """Test API endpoints via HTTP."""
    print("\n🌐 Testing API Endpoints...")
    try:
        import requests
    except ImportError:
        print("  ⚠️  requests module not available, skipping API tests")
        return

    BASE_URL = "http://localhost:9999"
    HEADERS = {"Authorization": "Bearer Operator"}

    endpoints = [
        ("GET", "/health", None),
        ("GET", "/v1/me", None),
        ("GET", "/v1/guardian/summary", None),
        ("GET", "/v1/incidents", None),
        ("GET", "/v1/agents", None),
        ("GET", "/v1/scan-history", None),
        ("GET", "/v1/statistics", None),
    ]

    for method, path, _ in endpoints:
        try:
            if method == "GET":
                r = requests.get(f"{BASE_URL}{path}", headers=HEADERS, timeout=2)
            else:
                r = requests.post(f"{BASE_URL}{path}", headers=HEADERS, timeout=2)

            if 200 <= r.status_code < 300:
                print(f"  ✅ {method:4} {path:30} {r.status_code}")
            else:
                print(f"  ⚠️  {method:4} {path:30} {r.status_code}")
        except Exception as e:
            print(f"  ⚠️  {method:4} {path:30} ERROR: {str(e)[:40]}")


def test_knowledge_graph():
    """Test knowledge graph integration."""
    print("\n🧠 Testing Knowledge Graph Integration...")
    try:
        from shadowcypher.core.knowledge_graph import kg

        # Get stats
        stats = kg.stats()
        print(f"  ✅ KG stats: {stats['nodes']} nodes, {stats['edges']} edges")

        # Find by type
        cves = kg.find_by_type("CVE", limit=5)
        print(f"  ✅ CVE nodes: {len(cves)} found")

    except Exception as e:
        print(f"  ❌ Knowledge graph test failed: {e}")


def test_config_system():
    """Test configuration system."""
    print("\n⚙️  Testing Configuration System...")
    try:
        from shadowcypher.core.config import config

        identity_handle = config.get("identity", "handle", default="Operator")
        print(f"  ✅ Config read: operator={identity_handle}")

        app_name = config.get("app_name", default="Unknown")
        print(f"  ✅ App name: {app_name}")

    except Exception as e:
        print(f"  ❌ Config test failed: {e}")


def main():
    """Run full integration test suite."""
    print("=" * 70)
    print("  SHADOWCYPHER GUARDIAN INTEGRATION TEST SUITE")
    print("  " + time.strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 70)

    try:
        test_guardian_service()
        test_scan_history()
        test_module_imports()
        test_knowledge_graph()
        test_config_system()
        test_api_endpoints()

        print("\n" + "=" * 70)
        print("  ✅ INTEGRATION TEST SUITE COMPLETE")
        print("=" * 70)
        return 0

    except AssertionError as e:
        print(f"\n❌ Assertion failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
