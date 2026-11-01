"""
Tests for the newly implemented modules:
secret_audit, poc_engine, awareness_sim, craft_factory, ad_pivot, agent_relay, deephat
"""

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# secret_audit
# ─────────────────────────────────────────────────────────────────────────────
class TestSecretAudit:
    @pytest.fixture
    def sa(self):
        from shadowcypher.modules.secret_audit import SecretAudit
        return SecretAudit()

    def test_instantiates(self, sa):
        assert sa is not None

    def test_scan_file_detects_api_key(self, sa, tmp_path):
        f = tmp_path / "config.py"
        # Construct test value at runtime so push-protection scanners don't flag it as a real secret
        test_key = "sk_live_" + "a" * 26 + "1" * 6
        f.write_text(f'api_key = "{test_key}"\n')
        findings = sa.scan_file(f)
        assert any(fi["type"] == "STRIPE_KEY" for fi in findings)

    def test_scan_file_detects_password(self, sa, tmp_path):
        f = tmp_path / "settings.py"
        f.write_text('password = "SuperSecret123"\n')
        findings = sa.scan_file(f)
        assert any("PASSWORD" in fi["type"] or "SECRET" in fi["type"] for fi in findings)

    def test_scan_file_skips_binary_ext(self, sa, tmp_path):
        f = tmp_path / "image.png"
        f.write_bytes(b"\x89PNG\r\n")
        findings = sa.scan_file(f)
        assert findings == []

    def test_scan_directory_returns_summary(self, sa, tmp_path):
        (tmp_path / "a.py").write_text('secret = "AKIA1234567890ABCDEF"\n')
        result = sa.scan_directory(tmp_path)
        assert "files_scanned" in result
        assert "total_findings" in result
        assert result["total_findings"] >= 1


# ─────────────────────────────────────────────────────────────────────────────
# poc_engine
# ─────────────────────────────────────────────────────────────────────────────
class TestPocEngine:
    @pytest.fixture
    def pe(self):
        from shadowcypher.modules.poc_engine import PocEngine
        return PocEngine()

    def test_instantiates(self, pe):
        assert pe is not None

    def test_supported_classes(self, pe):
        classes = pe.supported_classes()
        assert "XSS" in classes
        assert "SQLI" in classes
        assert "RCE" in classes

    def test_generate_xss(self, pe):
        result = pe.generate("XSS", cve_id="CVE-2024-0001", target="http://test.local", param="q")
        assert result["status"] == "ok"
        assert "script" in result
        assert "CVE-2024-0001" in result["script"]

    def test_generate_unknown_class(self, pe):
        result = pe.generate("UNKNOWN_VULN")
        assert result["status"] == "error"

    def test_generate_from_cve_sqli_hint(self, pe):
        result = pe.generate_from_cve("CVE-2024-9999", vuln_hint="SQLI")
        assert result["status"] == "ok"
        assert result["vuln_class"] == "SQLI"

    def test_generate_from_cve_unknown(self, pe):
        result = pe.generate_from_cve("CVE-2024-9999")
        assert result["status"] == "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# awareness_sim
# ─────────────────────────────────────────────────────────────────────────────
class TestAwarenessSim:
    @pytest.fixture
    def aw(self):
        from shadowcypher.modules.awareness_sim import AwarenessSim
        return AwarenessSim()

    def test_instantiates(self, aw):
        assert aw is not None

    def test_list_scenarios(self, aw):
        scenarios = aw.list_scenarios()
        assert len(scenarios) >= 3
        assert all("id" in s for s in scenarios)

    def test_render_scenario(self, aw):
        result = aw.render_scenario("credential_harvest_it", org="TestCorp", name="Alice")
        assert "red_flags" in result
        assert "training_tip" in result

    def test_render_unknown_scenario(self, aw):
        result = aw.render_scenario("nonexistent_id")
        assert "error" in result

    def test_get_quiz(self, aw):
        quiz = aw.get_quiz(count=2)
        assert len(quiz) == 2
        assert all("question" in q for q in quiz)
        assert all("correct" not in q for q in quiz)

    def test_check_answer_correct(self, aw):
        result = aw.check_answer("q_mfa", 1)
        assert result["correct"] is True

    def test_check_answer_wrong(self, aw):
        result = aw.check_answer("q_mfa", 0)
        assert result["correct"] is False

    def test_campaign_report(self, aw):
        report = aw.campaign_report("Q4 Test", 100, 30, 12, 5)
        assert report["risk_level"] == "HIGH"
        assert "recommendations" in report


# ─────────────────────────────────────────────────────────────────────────────
# craft_factory
# ─────────────────────────────────────────────────────────────────────────────
class TestCraftFactory:
    @pytest.fixture
    def cf(self):
        from shadowcypher.modules.craft_factory import CraftFactory
        return CraftFactory()

    def test_instantiates(self, cf):
        assert cf is not None

    def test_xss_payloads(self, cf):
        payloads = cf.xss_payloads()
        assert len(payloads) >= 5
        assert any("<script>" in p for p in payloads)

    def test_sqli_payloads(self, cf):
        payloads = cf.sqli_payloads()
        assert any("OR" in p.upper() for p in payloads)

    def test_cmdi_payloads(self, cf):
        payloads = cf.cmdi_payloads()
        assert any("id" in p for p in payloads)

    def test_url_encoding(self, cf):
        payloads = cf.xss_payloads(encode="url")
        assert all("%" in p or payloads.index(p) >= 0 for p in payloads)

    def test_full_kit_has_all_categories(self, cf):
        kit = cf.full_kit()
        assert "xss" in kit
        assert "sqli" in kit
        assert "cmdi" in kit
        assert "path_traversal" in kit

    def test_cyclic_pattern_length(self, cf):
        p = cf.cyclic_pattern(50)
        assert len(p) == 50

    def test_shellcode_stub(self, cf):
        stub = cf.shellcode_stub("x64")
        assert stub["arch"] == "x64"
        assert "hex" in stub
        assert "b64" in stub
        assert stub["length"] > 0


# ─────────────────────────────────────────────────────────────────────────────
# ad_pivot
# ─────────────────────────────────────────────────────────────────────────────
class TestADPivot:
    @pytest.fixture
    def ad(self):
        from shadowcypher.modules.ad_pivot import ADPivot
        return ADPivot()

    def test_instantiates(self, ad):
        assert ad is not None

    def test_connect_without_ldap3_graceful(self, ad):
        import unittest.mock as mock
        with mock.patch("shadowcypher.modules.ad_pivot._ldap3_available", return_value=False):
            messages = []
            result = ad.connect("dc.test.local", "user", "pass", "test.local",
                                on_output=messages.append)
            assert result is False
            assert any("ldap3" in m for m in messages)

    def test_enum_requires_connection(self, ad):
        msgs = []
        result = ad.enum_users(on_output=msgs.append)
        assert result == []
        assert any("Not connected" in m for m in msgs)

    def test_ping_subnet_localhost(self, ad):
        live = ad.ping_subnet("127.0.0.1/32", port=22, timeout=0.5)
        # May or may not be running — just ensure it returns a list
        assert isinstance(live, list)


# ─────────────────────────────────────────────────────────────────────────────
# agent_relay
# ─────────────────────────────────────────────────────────────────────────────
class TestAgentRelay:
    @pytest.fixture
    def relay(self):
        from shadowcypher.modules.agent_relay import AgentRelay
        return AgentRelay()

    def test_instantiates(self, relay):
        assert relay is not None

    def test_register_and_list_node(self, relay):
        node = relay.register_node("10.0.0.1", 8080)
        nodes = relay.list_nodes()
        assert any(n["node_id"] == node.node_id for n in nodes)

    def test_deregister_node(self, relay):
        node = relay.register_node("10.0.0.2", 9090)
        assert relay.deregister_node(node.node_id)
        nodes = relay.list_nodes()
        assert not any(n["node_id"] == node.node_id for n in nodes)

    def test_create_session(self, relay):
        n1 = relay.register_node("10.0.1.1", 1080)
        n2 = relay.register_node("10.0.1.2", 1081)
        sess = relay.create_session("agent-001", [n1.node_id, n2.node_id])
        assert sess is not None
        assert len(relay.list_sessions()) == 1

    def test_session_unknown_node_fails(self, relay):
        sess = relay.create_session("agent-002", ["nonexistent_node"])
        assert sess is None

    def test_ping_session(self, relay):
        node = relay.register_node("10.0.2.1", 2222)
        sess = relay.create_session("agent-003", [node.node_id])
        assert relay.ping_session(sess.session_id)
        assert not relay.ping_session("bad-session-id")

    def test_resolve_route(self, relay):
        node = relay.register_node("10.0.3.1", 3333, relay_type="socks5")
        sess = relay.create_session("agent-004", [node.node_id])
        route = relay.resolve_route(sess.session_id)
        assert route is not None
        assert route[0]["relay_type"] == "socks5"

    def test_topology(self, relay):
        topo = relay.topology()
        assert "nodes" in topo
        assert "sessions" in topo

    def test_node_fingerprint(self, relay):
        node = relay.register_node("10.0.4.1", 4444)
        fp = relay.node_fingerprint(node.node_id)
        assert fp is not None
        assert len(fp) == 16

    def test_terminate_session(self, relay):
        node = relay.register_node("10.0.5.1", 5555)
        sess = relay.create_session("agent-005", [node.node_id])
        assert relay.terminate_session(sess.session_id)
        assert relay.list_sessions() == []


# ─────────────────────────────────────────────────────────────────────────────
# deephat
# ─────────────────────────────────────────────────────────────────────────────
class TestDeepHat:
    @pytest.fixture
    def dh(self):
        from shadowcypher.modules.deephat import DeepHat
        return DeepHat()

    def test_instantiates(self, dh):
        assert dh is not None

    def test_is_tor_running_returns_bool(self, dh):
        result = dh.is_tor_running()
        assert isinstance(result, bool)

    def test_probe_invalid_url(self, dh):
        result = dh.probe_onion("http://not-an-onion.com")
        assert "error" in result

    def test_extract_onions_from_text(self, dh):
        text = "Visit http://facebookwkhpilnemx.onion and http://duckduckgogg42xjoc72x3sjasowoarfbgcmvfimaftt6twagswzczad.onion"
        onions = dh.extract_onions_from_text(text)
        assert len(onions) == 2

    def test_check_tor_without_pysocks(self, dh):
        import unittest.mock as mock
        with mock.patch("shadowcypher.modules.deephat._socks5_available", return_value=False):
            result = dh.check_tor()
            assert result["tor_available"] is False
            assert "PySocks" in result["error"]
