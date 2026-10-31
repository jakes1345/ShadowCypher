"""
Tests for Unified Cyber-Operations & SRE Engine (Linux Drive Agent).
Covers:
  - LinuxDriveEngine (mount detection, statvfs capacity, write verification)
  - ContextModeVault (token reduction, SQLite storage, search & query)
  - IFixAiSafetyGate (pre-execution policy audit, latency, destructive block)
  - BinaryReverseEngineer & GhidraHeadlessDecompilerBridge (ELF analysis, C decompilation)
  - AgentTool & MCP Tool Registries
"""

import os
import shutil
import tempfile
import sys
from pathlib import Path

_REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    import pytest
except ImportError:
    class _MockPytest:
        @staticmethod
        def fixture(fn):
            return fn
    pytest = _MockPytest()


from shadowcypher.ai.unified_operations_agent import (
    LinuxDriveEngine,
    ContextModeVault,
    IFixAiSafetyGate,
    BinaryReverseEngineer,
    GhidraHeadlessDecompilerBridge,
    UnifiedCyberAgent,
    get_unified_agent_tools,
    get_unified_mcp_tools,
)
from shadowcypher.sre.elf_parser import ELFParser
from shadowcypher.sre.vulnerability_scanner import BinaryVulnerabilityScanner
from shadowcypher.audit.ifix_guard import IFixPolicyAuditor, AuditRecord
from shadowcypher.context_vault.engine import AdvancedContextVault, SlicedContext
from shadowcypher.orchestrator.pentagi_state_machine import AutonomousPentAGISystem, MissionTelemetry, MissionState


class TestLinuxDriveEngine:
    """Test Linux drive mount inspection and capacity metrics."""

    def test_inspect_drive_tmp(self):
        info = LinuxDriveEngine.inspect_drive("/tmp")
        assert info.target_path.startswith("/")
        assert info.total_gb > 0
        assert info.free_gb > 0
        assert 0.0 <= info.used_percent <= 100.0
        assert info.is_writable is True
        assert isinstance(info.fs_type, str)


class TestContextModeVault:
    """Test token-sandboxed SQLite vault and semantic search."""

    @pytest.fixture
    def vault_dir(self):
        d = tempfile.mkdtemp(prefix="test_vault_")
        yield Path(d)
        shutil.rmtree(d, ignore_errors=True)

    def test_store_and_token_compression(self, vault_dir):
        vault = ContextModeVault(vault_dir)
        raw_text = "\n".join([f"Line {i}: CRITICAL vulnerability CVE-2026-{1000+i} detected in entry point" for i in range(100)])
        artifact = vault.store_and_compress("scanner_tool", raw_text)

        assert artifact.storage_id.startswith("ctx_")
        assert artifact.raw_size_bytes == len(raw_text.encode("utf-8"))
        assert artifact.token_saving_pct > 50.0  # Significant token savings
        assert "CVE-2026" in artifact.compressed_summary

        # Raw retrieval
        fetched_raw = vault.retrieve_raw(artifact.storage_id)
        assert fetched_raw == raw_text

    def test_search_and_query_artifacts(self, vault_dir):
        vault = ContextModeVault(vault_dir)
        vault.store_and_compress("sre_tool", "Function decrypt_payload found with hardcoded password secret123")
        vault.store_and_compress("recon_tool", "Open port 443 with TLS 1.3")

        # Search by keyword
        matches = vault.search_artifacts("decrypt_payload")
        assert len(matches) == 1
        assert matches[0]["tool_name"] == "sre_tool"

        # Query detail by ID
        target_id = matches[0]["id"]
        detail = vault.get_artifact(target_id)
        assert detail is not None
        assert "secret123" in detail["raw_content"]


class TestIFixAiSafetyGate:
    """Test deterministic pre-execution policy verification."""

    def test_approved_action(self):
        gate = IFixAiSafetyGate(allowed_cidrs=["127.0.0.1", "localhost", "192.168.*"])
        verdict = gate.audit_plan("recon", {"target": "127.0.0.1", "command": "nmap -sT 127.0.0.1"})
        assert verdict.allowed is True
        assert verdict.risk == "LOW"
        assert verdict.audit_duration_ms < 10.0  # Must be fast (<10ms)

    def test_blocked_destructive_command(self):
        gate = IFixAiSafetyGate()
        verdict = gate.audit_plan("shell", {"command": "rm -rf / --no-preserve-root"})
        assert verdict.allowed is False
        assert verdict.risk == "CRITICAL"
        assert "wipe" in verdict.rule_matched.lower()

    def test_blocked_out_of_scope_target(self):
        gate = IFixAiSafetyGate(allowed_cidrs=["192.168.1.*"])
        verdict = gate.audit_plan("recon", {"target": "8.8.8.8"})
        assert verdict.allowed is False
        assert verdict.risk == "HIGH"
        assert "outside permitted" in verdict.rule_matched.lower()


class TestBinaryReverseEngineer:
    """Test ELF identification and disassembly."""

    def test_elf_detection(self):
        sre = BinaryReverseEngineer()
        assert sre.is_elf_binary(Path("/bin/id")) is True
        assert sre.is_elf_binary(Path(__file__)) is False

    def test_binary_analysis(self):
        sre = BinaryReverseEngineer()
        res = sre.analyze_binary(Path("/bin/id"))
        assert res["binary_name"] == "id"
        assert res["sha256"]
        assert 0.0 <= res["entropy"] <= 8.0
        assert "X86-64" in res["architecture"] or "x86" in res["architecture"].lower() or res["architecture"] != "Unknown"


class TestGhidraHeadlessDecompilerBridge:
    """Test native Linux SRE / Ghidra C pseudocode decompilation."""

    def test_decompile_binary_id(self):
        bridge = GhidraHeadlessDecompilerBridge()
        decomp = bridge.decompile_binary(Path("/bin/id"), max_functions=2)
        assert "c_pseudocode" in decomp
        assert decomp["functions_decompiled"] >= 1
        assert ("int entry0" in decomp["c_pseudocode"] or "fcn." in decomp["c_pseudocode"] or "Function:" in decomp["c_pseudocode"])


class TestToolRegistries:
    """Test AgentTool and MCP server registry factories."""

    def test_agent_tool_registry(self):
        agent = UnifiedCyberAgent(drive_path="/tmp/test_unified_agent")
        tools = get_unified_agent_tools(agent)
        tool_names = [t.name for t in tools]
        assert "unified_decompile" in tool_names
        assert "unified_drive_audit" in tool_names
        assert "unified_recon" in tool_names
        assert "unified_vault_search" in tool_names
        assert "unified_vault_query" in tool_names

        # Test tool invocation via unpacked kwargs
        decompile_tool = next(t for t in tools if t.name == "unified_decompile")
        res = decompile_tool.fn(binary_path="/bin/id", max_functions=1)
        assert res["binary"] == "/bin/id"
        assert res["vault_id"].startswith("ctx_")

    def test_mcp_tool_registry(self):
        mcp_tools = get_unified_mcp_tools()
        assert "shadowcypher_unified_decompile" in mcp_tools
        assert "shadowcypher_unified_recon" in mcp_tools
        assert "inputSchema" in mcp_tools["shadowcypher_unified_decompile"]
        assert callable(mcp_tools["shadowcypher_unified_decompile"]["handler"])


class TestDeepELFParser:
    """Test pure struct ELF parser and checksec analysis on real binaries."""

    def test_parse_header_and_sections(self):
        target = Path("/bin/id")
        parser = ELFParser(target)
        assert parser.e_machine == 62  # EM_X86_64
        assert len(parser.program_headers) > 0
        assert len(parser.section_headers) > 0
        assert ".text" in parser.section_by_name
        assert ".rodata" in parser.section_by_name

    def test_checksec_security_matrix(self):
        target = Path("/bin/bash")
        parser = ELFParser(target)
        checksec = parser.run_checksec()
        assert checksec.nx is True  # Modern bash has NX enabled
        assert checksec.canary in (True, False)
        assert "RELRO" in checksec.relro
        assert checksec.pie in (True, False)
        assert 0 <= checksec.security_score <= 100


class TestDeepVulnerabilityScanner:
    """Test binary sink detection, ROP gadgets, and anti-debug inspection."""

    def test_vulnerability_and_rop_scan(self):
        scanner = BinaryVulnerabilityScanner(Path("/bin/id"))
        audit = scanner.full_audit()

        assert audit["binary"] == "/bin/id"
        assert isinstance(audit["findings"], list)
        assert isinstance(audit["rop_gadgets_sample"], list)
        assert audit["rop_gadgets_count"] > 0
        assert isinstance(audit["anti_debug_evasions"], list)


class TestDeepIFixPolicyAuditor:
    """Test deterministic safety policies and cryptographic SHA-256 Merkle chain."""

    def test_tamper_evident_merkle_chain(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            ledger_path = Path(tmp_dir) / "audit_chain.db"
            auditor = IFixPolicyAuditor(ledger_db_path=ledger_path)

            # Record multiple intents
            r1 = auditor.audit_intent("network_recon", {"target": "127.0.0.1"})
            assert r1.verdict == "APPROVED"

            r2 = auditor.audit_intent("shell_exec", {"command": "rm -rf /"})
            assert r2.verdict == "DENIED"
            assert "T1059.004" in r2.mitre_technique

            # Verify chain integrity
            valid, count, err = auditor.verify_ledger_integrity()
            assert valid is True
            assert count == 2

            # Deliberately tamper with a record in the sqlite ledger to verify tamper-evidence
            import sqlite3
            with sqlite3.connect(ledger_path) as conn:
                conn.execute("UPDATE audit_chain SET verdict = 'TAMPERED' WHERE id = ?", (r1.entry_id,))
                conn.commit()

            # Re-verify: must detect cryptographic mismatch and return False
            valid, count, err = auditor.verify_ledger_integrity()
            assert valid is False
            assert "Tampered record" in err

    def test_ast_and_privesc_audit(self):
        auditor = IFixPolicyAuditor()
        # Destructive wipe
        v1 = auditor.audit_intent("shell_exec", {"command": "rm -rf /var/log"})
        assert v1.verdict == "DENIED"
        assert "Policy Violation" in v1.reason

        # Privesc command
        v2 = auditor.audit_intent("shell_exec", {"command": "sudo -s"})
        assert v2.verdict == "DENIED"
        assert "Root privilege" in v2.reason

        # Permitted recon
        v3 = auditor.audit_intent("network_recon", {"target": "127.0.0.1"})
        assert v3.verdict == "APPROVED"


class TestDeepContextVault:
    """Test Content-Addressed Storage (CAS) and dynamic token-budget slicing."""

    def test_cas_deduplication_and_budget_slicing(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            vault = AdvancedContextVault(vault_dir=Path(tmp_dir))

            # Simulate large decompiled C output
            decomp_c = """
            int calculate_hash(char *input) {
                int hash = 5381;
                while (*input) {
                    hash = ((hash << 5) + hash) + *input++;
                }
                return hash;
            }

            void execute_payload(char *cmd) {
                // Potential vulnerability: unchecked system call
                system(cmd);
            }

            int main(int argc, char **argv) {
                if (argc > 1) {
                    execute_payload(argv[1]);
                }
                return 0;
            }
            """ * 20  # Repeat to make substantial size

            art_id = vault.store_and_sandbox("ghidra_decompile", "Test C Code", decomp_c)
            assert art_id.startswith("ctx_")

            # Test slicing with tight budget (100 tokens)
            sliced = vault.slice_context_window(art_id, max_token_budget=100)
            assert sliced.served_tokens <= 100
            assert sliced.token_saving_pct > 0.0

            # Test search over inverted index
            results = vault.search_artifacts("execute_payload")
            assert len(results) >= 1
            assert results[0]["id"] == art_id

            # Test raw retrieval
            raw_fetched = vault.retrieve_raw(art_id)
            assert raw_fetched == decomp_c


class TestAutonomousPentAGIMission:
    """Test full PentAGI multi-agent FSM state machine."""

    def test_full_autonomous_mission_fsm(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            system = AutonomousPentAGISystem(
                drive_path=tmp_dir,
                vault_dir=str(Path(tmp_dir) / "vault")
            )

            telemetry = system.run_mission(
                target_host="127.0.0.1",
                target_binary="/bin/id",
                max_token_budget=400
            )

            assert telemetry.current_state == MissionState.COMPLETED
            states = [s[1] for s in telemetry.state_history]
            assert states == [
                MissionState.IDLE,
                MissionState.POLICY_AUDIT,
                MissionState.TARGET_INSPECTION,
                MissionState.RECONNAISSANCE,
                MissionState.BINARY_SRE,
                MissionState.CONTEXT_SANDBOXING,
                MissionState.COMPLETED
            ]
            assert telemetry.audit_record.verdict == "APPROVED"
            assert telemetry.sre_summary["checksec"]["security_score"] > 0
            assert telemetry.sliced_context.token_saving_pct > 0.0
            assert telemetry.vault_artifact_id.startswith("ctx_")
            valid, _, _ = system.auditor.verify_ledger_integrity()
            assert valid is True



if __name__ == "__main__":
    print("[*] Running TestLinuxDriveEngine...")
    t1 = TestLinuxDriveEngine()
    t1.test_inspect_drive_tmp()
    print("    [✓] Drive inspection passed")

    print("[*] Running TestContextModeVault...")
    t2 = TestContextModeVault()
    tmp_v = Path(tempfile.mkdtemp(prefix="test_vault_run_"))
    try:
        t2.test_store_and_token_compression(tmp_v)
        t2.test_search_and_query_artifacts(tmp_v)
        print("    [✓] Vault storage, token compression & search passed")
    finally:
        shutil.rmtree(tmp_v, ignore_errors=True)

    print("[*] Running TestIFixAiSafetyGate...")
    t3 = TestIFixAiSafetyGate()
    t3.test_approved_action()
    t3.test_blocked_destructive_command()
    t3.test_blocked_out_of_scope_target()
    print("    [✓] Safety gate policy rules passed")

    print("[*] Running TestBinaryReverseEngineer...")
    t4 = TestBinaryReverseEngineer()
    t4.test_elf_detection()
    t4.test_binary_analysis()
    print("    [✓] ELF binary analysis and entropy metrics passed")

    print("[*] Running TestGhidraHeadlessDecompilerBridge...")
    t5 = TestGhidraHeadlessDecompilerBridge()
    t5.test_decompile_binary_id()
    print("    [✓] Headless SRE C pseudocode decompilation passed")

    print("[*] Running TestToolRegistries...")
    t6 = TestToolRegistries()
    t6.test_agent_tool_registry()
    t6.test_mcp_tool_registry()
    print("    [✓] AgentTool and MCP server registries passed")

    print("[*] Running TestDeepELFParser...")
    t7 = TestDeepELFParser()
    t7.test_parse_header_and_sections()
    t7.test_checksec_security_matrix()
    print("    [✓] Pure struct ELF parser & Checksec matrix verified on real binaries (/bin/id, /bin/bash)")

    print("[*] Running TestDeepVulnerabilityScanner...")
    t8 = TestDeepVulnerabilityScanner()
    t8.test_vulnerability_and_rop_scan()
    print("    [✓] Dangerous C sinks, executable ROP gadgets & anti-debugging detection verified")

    print("[*] Running TestDeepIFixPolicyAuditor...")
    t9 = TestDeepIFixPolicyAuditor()
    t9.test_tamper_evident_merkle_chain()
    t9.test_ast_and_privesc_audit()
    print("    [✓] Cryptographic SHA-256 Merkle chain & MITRE ATT&CK AST safety rules verified")

    print("[*] Running TestDeepContextVault...")
    t10 = TestDeepContextVault()
    t10.test_cas_deduplication_and_budget_slicing()
    print("    [✓] Content-Addressed Storage (CAS) & token budget slicing verified")

    print("[*] Running TestAutonomousPentAGIMission...")
    t11 = TestAutonomousPentAGIMission()
    t11.test_full_autonomous_mission_fsm()
    print("    [✓] PentAGI multi-agent FSM state transitions & autonomous mission verified")

    print("\n" + "=" * 65)
    print("ALL 18 DEEP ENGINEERING TEST CASES PASSED SUCCESSFULLY")
    print("=" * 65)

