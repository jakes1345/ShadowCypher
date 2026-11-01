"""
AD Pivot — Active Directory Enumeration & Lateral Movement Toolkit
Enumerates AD via LDAP for authorized internal assessments.
"""

from __future__ import annotations

import socket
from typing import Any

from shadowcypher.core.module import BaseModule


def _ldap3_available() -> bool:
    try:
        import ldap3  # noqa: F401
        return True
    except ImportError:
        return False


class ADPivot(BaseModule):
    """Active Directory enumeration and lateral movement primitives."""

    def __init__(self):
        super().__init__(module_name="ad_pivot")
        self._conn: Any = None
        self._domain_dn: str = ""

    # ── Connection ────────────────────────────────────────────────────────────

    def connect(
        self,
        dc_host: str,
        username: str,
        password: str,
        domain: str,
        use_ssl: bool = False,
        on_output=None,
    ) -> bool:
        """
        Connect to an AD domain controller via LDAP.
        Returns True on success.
        """
        if not _ldap3_available():
            msg = "[AD_PIVOT] ldap3 not installed — run: pip install ldap3\n"
            if on_output:
                on_output(msg)
            self.log("ldap3 not available")
            return False

        import ldap3

        port = 636 if use_ssl else 389
        self._domain_dn = "DC=" + ",DC=".join(domain.split("."))
        upn = f"{username}@{domain}"

        server = ldap3.Server(dc_host, port=port, use_ssl=use_ssl, get_info=ldap3.ALL)
        try:
            conn = ldap3.Connection(server, user=upn, password=password, auto_bind=True)
            self._conn = conn
            self.log(f"CONNECTED: {dc_host} as {upn}")
            if on_output:
                on_output(f"[AD_PIVOT] Connected to {dc_host} ({domain})\n")
            return True
        except Exception as e:
            if on_output:
                on_output(f"[AD_PIVOT] Connection failed: {e}\n")
            self.log(f"CONNECTION_FAILED: {e}")
            return False

    def disconnect(self) -> None:
        if self._conn:
            try:
                self._conn.unbind()
            except Exception:
                pass
            self._conn = None

    # ── Enumeration ───────────────────────────────────────────────────────────

    def enum_users(
        self,
        search_base: str | None = None,
        limit: int = 500,
        on_output=None,
    ) -> list[dict[str, Any]]:
        """Enumerate domain user accounts."""
        return self._search(
            search_filter="(&(objectCategory=person)(objectClass=user))",
            attributes=["sAMAccountName", "displayName", "mail", "memberOf",
                        "userAccountControl", "lastLogon", "pwdLastSet"],
            search_base=search_base,
            limit=limit,
            label="enum_users",
            on_output=on_output,
        )

    def enum_groups(
        self,
        search_base: str | None = None,
        limit: int = 200,
        on_output=None,
    ) -> list[dict[str, Any]]:
        """Enumerate domain security groups."""
        return self._search(
            search_filter="(objectClass=group)",
            attributes=["cn", "description", "member", "sAMAccountName"],
            search_base=search_base,
            limit=limit,
            label="enum_groups",
            on_output=on_output,
        )

    def enum_computers(
        self,
        search_base: str | None = None,
        limit: int = 500,
        on_output=None,
    ) -> list[dict[str, Any]]:
        """Enumerate domain-joined computers."""
        return self._search(
            search_filter="(objectClass=computer)",
            attributes=["cn", "dNSHostName", "operatingSystem",
                        "operatingSystemVersion", "lastLogonTimestamp"],
            search_base=search_base,
            limit=limit,
            label="enum_computers",
            on_output=on_output,
        )

    def find_privileged_users(
        self,
        on_output=None,
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Find members of high-privilege groups:
        Domain Admins, Enterprise Admins, Schema Admins, Backup Operators.
        """
        groups = {
            "Domain Admins": f"CN=Domain Admins,CN=Users,{self._domain_dn}",
            "Enterprise Admins": f"CN=Enterprise Admins,CN=Users,{self._domain_dn}",
            "Schema Admins": f"CN=Schema Admins,CN=Users,{self._domain_dn}",
            "Backup Operators": f"CN=Backup Operators,CN=Builtin,{self._domain_dn}",
        }
        result: dict[str, list[dict[str, Any]]] = {}
        for group_name, group_dn in groups.items():
            members = self._search(
                search_filter=f"(&(objectClass=user)(memberOf={group_dn}))",
                attributes=["sAMAccountName", "displayName", "mail"],
                label=f"priv_{group_name.replace(' ', '_').lower()}",
                on_output=on_output,
            )
            result[group_name] = members
            if on_output and members:
                on_output(f"[AD_PIVOT] {group_name}: {len(members)} member(s)\n")
        return result

    def find_kerberoastable(
        self,
        on_output=None,
    ) -> list[dict[str, Any]]:
        """
        Find accounts with SPNs set — Kerberoasting candidates.
        Returns user accounts with servicePrincipalName attributes.
        """
        return self._search(
            search_filter="(&(objectClass=user)(servicePrincipalName=*)(!objectClass=computer))",
            attributes=["sAMAccountName", "servicePrincipalName", "displayName",
                        "userAccountControl"],
            label="kerberoastable",
            on_output=on_output,
        )

    def find_asrep_roastable(self, on_output=None) -> list[dict[str, Any]]:
        """
        Find accounts with 'Do not require Kerberos pre-auth' (UF_DONT_REQUIRE_PREAUTH).
        AS-REP roasting candidates.
        """
        results = self._search(
            search_filter="(&(objectClass=user)(userAccountControl:1.2.840.113556.1.4.803:=4194304))",
            attributes=["sAMAccountName", "userAccountControl", "displayName"],
            label="asrep_roastable",
            on_output=on_output,
        )
        return results

    # ── Ping sweep ────────────────────────────────────────────────────────────

    @staticmethod
    def ping_subnet(
        subnet: str,
        port: int = 445,
        timeout: float = 0.5,
        on_output=None,
    ) -> list[str]:
        """
        Fast TCP-connect sweep of a /24 subnet on a given port.
        Returns list of live hosts. No admin rights needed.
        """
        import ipaddress
        net = ipaddress.IPv4Network(subnet, strict=False)
        live: list[str] = []
        for host in net.hosts():
            ip = str(host)
            try:
                with socket.create_connection((ip, port), timeout=timeout):
                    live.append(ip)
                    if on_output:
                        on_output(f"[AD_PIVOT] LIVE: {ip}:{port}\n")
            except (OSError, socket.timeout):
                pass
        return live

    # ── Internal ─────────────────────────────────────────────────────────────

    def _search(
        self,
        search_filter: str,
        attributes: list[str],
        search_base: str | None = None,
        limit: int = 500,
        label: str = "search",
        on_output=None,
    ) -> list[dict[str, Any]]:
        if self._conn is None:
            if on_output:
                on_output("[AD_PIVOT] Not connected — call connect() first\n")
            return []

        base = search_base or self._domain_dn
        try:
            self._conn.search(
                search_base=base,
                search_filter=search_filter,
                attributes=attributes,
                size_limit=limit,
            )
            results = []
            for entry in self._conn.entries:
                row: dict[str, Any] = {"dn": str(entry.entry_dn)}
                for attr in attributes:
                    try:
                        val = entry[attr].value
                        row[attr] = val
                    except Exception:
                        row[attr] = None
                results.append(row)
            self.log(f"{label.upper()}: {len(results)} entries")
            if on_output:
                on_output(f"[AD_PIVOT] {label}: found {len(results)} entries\n")
            return results
        except Exception as e:
            if on_output:
                on_output(f"[AD_PIVOT] Search error ({label}): {e}\n")
            self.log(f"SEARCH_ERROR ({label}): {e}")
            return []
