"""
ShadowCypher Test Suite — Sanitization & Input Validation
Tests every validator in core/sanitize.py with both valid and adversarial input.
"""

import pytest

from shadowcypher.core.sanitize import (
    quote,
    sanitize_bpf_filter,
    validate_filepath,
    validate_interface,
    validate_ip,
    validate_mac,
    validate_port,
    validate_ports,
    validate_target,
)


class TestValidateTarget:
    """Target validation must accept IPs, hostnames, CIDRs, URLs and reject injection."""

    @pytest.mark.parametrize("target", [
        "192.168.1.1",
        "10.0.0.0/8",
        "172.16.0.0/12",
        "255.255.255.255",
        "0.0.0.0",
        "example.com",
        "sub.domain.example.com",
        "http://example.com",
        "https://example.com/path",
        "my-server-01",
    ])
    def test_valid_targets(self, target):
        assert validate_target(target) is True

    @pytest.mark.parametrize("target", [
        "",
        "   ",
        "999.999.999.999",
        "192.168.1.1; rm -rf /",
        "example.com$(whoami)",
        "example.com`id`",
        "a" * 300,  # Exceeds 253 char hostname limit
        "-invalid.com",
    ])
    def test_invalid_targets(self, target):
        assert validate_target(target) is False


class TestValidateIP:
    @pytest.mark.parametrize("ip", [
        "192.168.1.1", "10.0.0.1", "0.0.0.0", "255.255.255.255"
    ])
    def test_valid_ips(self, ip):
        assert validate_ip(ip) is True

    @pytest.mark.parametrize("ip", [
        "", "256.1.1.1", "1.2.3", "1.2.3.4.5", "abc.def.ghi.jkl",
        "192.168.1.1/24", "192.168.1.1:80", "$(whoami)",
    ])
    def test_invalid_ips(self, ip):
        assert validate_ip(ip) is False


class TestValidateMAC:
    def test_valid_mac(self):
        assert validate_mac("AA:BB:CC:DD:EE:FF") is True
        assert validate_mac("00:11:22:33:44:55") is True

    def test_invalid_mac(self):
        assert validate_mac("") is False
        assert validate_mac("AABBCCDDEEFF") is False
        assert validate_mac("GG:HH:II:JJ:KK:LL") is False
        assert validate_mac("AA:BB:CC:DD:EE") is False


class TestValidateInterface:
    @pytest.mark.parametrize("iface", ["eth0", "wlan0", "lo", "ens33", "br-lan", "docker0"])
    def test_valid_interfaces(self, iface):
        assert validate_interface(iface) is True

    @pytest.mark.parametrize("iface", ["", "eth0;id", "wlan0$(cmd)", "a b"])
    def test_invalid_interfaces(self, iface):
        assert validate_interface(iface) is False


class TestValidatePort:
    @pytest.mark.parametrize("port", [1, 22, 80, 443, 8080, 65535])
    def test_valid_ports(self, port):
        assert validate_port(port) is True

    @pytest.mark.parametrize("port", [0, -1, 65536, "abc", None, ""])
    def test_invalid_ports(self, port):
        assert validate_port(port) is False


class TestValidatePorts:
    @pytest.mark.parametrize("spec", ["22", "80,443", "1-1024", "22,80,8000-9000"])
    def test_valid_port_specs(self, spec):
        assert validate_ports(spec) is True

    @pytest.mark.parametrize("spec", ["", "0", "65536", "abc", "22,", "-1-100", "80;id"])
    def test_invalid_port_specs(self, spec):
        assert validate_ports(spec) is False


class TestValidateFilepath:
    @pytest.mark.parametrize("path", [
        "/tmp/output.txt", "/home/user/scan.xml", "report.html", "./findings/scan1.json"
    ])
    def test_valid_paths(self, path):
        assert validate_filepath(path) is True

    @pytest.mark.parametrize("path", [
        "",
        "/tmp/$(whoami)",
        "/tmp/`id`",
        "/etc/passwd | cat",
        "/tmp/file; rm -rf /",
        "/tmp/file && whoami",
        "../../../etc/shadow",
    ])
    def test_injection_blocked(self, path):
        assert validate_filepath(path) is False


class TestSanitizeBPF:
    def test_valid_bpf(self):
        assert sanitize_bpf_filter("tcp port 80") == "tcp port 80"
        assert sanitize_bpf_filter("host 192.168.1.1 and port 22") != ""
        assert sanitize_bpf_filter("not port 53") != ""

    def test_injection_blocked(self):
        assert sanitize_bpf_filter("tcp; rm -rf /") == ""
        assert sanitize_bpf_filter("tcp$(whoami)") == ""


class TestQuote:
    def test_quotes_shell_metacharacters(self):
        # shlex.quote wraps in single quotes, making metacharacters inert
        result = quote("hello; world")
        assert result.startswith("'") and result.endswith("'")
        # Backticks inside single quotes are safe in shell
        result = quote("`whoami`")
        assert result == "'`whoami`'"
        # Dollar signs inside single quotes are safe
        result = quote("test$(id)")
        assert result == "'test$(id)'"
