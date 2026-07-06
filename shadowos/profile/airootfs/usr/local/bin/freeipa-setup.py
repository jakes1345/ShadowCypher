#!/usr/bin/env python3
"""
FreeIPA Integration Setup for ShadowCypher Enterprise

Handles user provisioning, group management, sudo rule configuration,
certificate issuance, and audit logging for Guardian vault integration.
"""

import json
import logging
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import hashlib
import secrets

try:
    import requests
    from requests.auth import HTTPBasicAuth
    from requests.structures import CaseInsensitiveDict
except ImportError:
    print("Error: requests library required. Install with: pip install requests")
    sys.exit(1)


@dataclass
class User:
    """FreeIPA User representation"""
    uid: str
    cn: str
    mail: str
    password: str
    description: str
    telephone_number: Optional[str] = None
    clearance_level: Optional[str] = None

    def to_ldap_dict(self) -> Dict[str, Any]:
        """Convert to LDAP attribute dictionary"""
        attrs = {
            "uid": self.uid,
            "cn": self.cn,
            "mail": self.mail,
            "userPassword": self.password,
            "description": self.description,
            "objectClass": ["inetOrgPerson", "organizationalPerson", "person", "top"],
        }
        if self.telephone_number:
            attrs["telephoneNumber"] = self.telephone_number
        if self.clearance_level:
            attrs["clearanceLevel"] = self.clearance_level
        return attrs


@dataclass
class Group:
    """FreeIPA Group representation"""
    cn: str
    description: str
    members: List[str] = None

    def __post_init__(self):
        if self.members is None:
            self.members = []


@dataclass
class SudoRule:
    """FreeIPA Sudo Rule representation"""
    name: str
    users: List[str]
    hosts: List[str]
    commands: List[str]
    run_as_user: str = "ALL"
    run_as_group: str = "ALL"
    options: List[str] = None

    def __post_init__(self):
        if self.options is None:
            self.options = ["!authenticate"]


class FreeIPAClient:
    """FreeIPA API Client for enterprise identity management"""

    def __init__(
        self,
        host: str,
        realm: str,
        admin_user: str,
        admin_password: str,
        verify_ssl: bool = True,
        timeout: int = 30,
    ):
        """
        Initialize FreeIPA client

        Args:
            host: FreeIPA server FQDN
            realm: Kerberos realm (e.g., SHADOWCYPHER.SITE)
            admin_user: FreeIPA admin username
            admin_password: FreeIPA admin password
            verify_ssl: Whether to verify SSL certificates
            timeout: Request timeout in seconds
        """
        self.host = host
        self.realm = realm
        self.admin_user = admin_user
        self.admin_password = admin_password
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.base_url = f"https://{host}/ipa/session/json"
        self.api_url = f"https://{host}/ipa/json"
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "ShadowCypher-FreeIPA-Client/1.0",
        })
        self.authenticated = False
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Configure logging"""
        logger = logging.getLogger(__name__)
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        return logger

    def authenticate(self) -> bool:
        """
        Authenticate to FreeIPA server

        Returns:
            True if authentication successful
        """
        try:
            auth = HTTPBasicAuth(self.admin_user, self.admin_password)
            response = self.session.post(
                f"https://{self.host}/ipa/session/login_password",
                auth=auth,
                data={"user": self.admin_user, "password": self.admin_password},
                verify=self.verify_ssl,
                timeout=self.timeout,
                allow_redirects=False,
            )

            if response.status_code in (200, 401):
                self.authenticated = True
                self.logger.info(f"Successfully authenticated to FreeIPA {self.host}")
                return True
            else:
                self.logger.error(f"Authentication failed: HTTP {response.status_code}")
                return False
        except requests.RequestException as e:
            self.logger.error(f"Authentication error: {e}")
            return False

    def _api_call(
        self,
        method: str,
        params: Dict[str, Any],
        skip_validation: bool = False,
    ) -> Tuple[bool, Any]:
        """
        Execute FreeIPA API call

        Args:
            method: FreeIPA API method name
            params: Method parameters
            skip_validation: Skip result validation

        Returns:
            Tuple of (success, result)
        """
        payload = {
            "method": method,
            "params": [[], params],
        }

        try:
            response = self.session.post(
                self.api_url,
                json=payload,
                verify=self.verify_ssl,
                timeout=self.timeout,
            )

            result = response.json()

            if result.get("error"):
                error_msg = result["error"].get("message", "Unknown error")
                self.logger.warning(f"API call failed: {method} - {error_msg}")
                return False, result

            self.logger.debug(f"API call successful: {method}")
            return True, result.get("result", result)
        except requests.RequestException as e:
            self.logger.error(f"API request failed: {method} - {e}")
            return False, None
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {e}")
            return False, None

    def create_user(self, user: User) -> Tuple[bool, Optional[str]]:
        """
        Create user in FreeIPA

        Args:
            user: User object to create

        Returns:
            Tuple of (success, uid)
        """
        params = {
            "uid": user.uid,
            "cn": user.cn,
            "mail": user.mail,
            "description": user.description,
            "userPassword": user.password,
            "noprivate": False,
        }

        if user.telephone_number:
            params["telephoneNumber"] = user.telephone_number

        success, result = self._api_call("user_add", params)

        if success:
            self.logger.info(f"Created user: {user.uid}")
            return True, user.uid
        else:
            self.logger.error(f"Failed to create user: {user.uid}")
            return False, None

    def delete_user(self, uid: str, preserve: bool = False) -> bool:
        """
        Delete user from FreeIPA

        Args:
            uid: User ID to delete
            preserve: Preserve user data (mark inactive)

        Returns:
            Success status
        """
        params = {
            "uid": uid,
            "preserve": preserve,
        }

        success, _ = self._api_call("user_del", params)

        if success:
            self.logger.info(f"Deleted user: {uid}")
        else:
            self.logger.error(f"Failed to delete user: {uid}")

        return success

    def modify_user(self, uid: str, **kwargs) -> bool:
        """
        Modify existing user in FreeIPA

        Args:
            uid: User ID to modify
            **kwargs: User attributes to modify

        Returns:
            Success status
        """
        params = {"uid": uid}
        params.update(kwargs)

        success, _ = self._api_call("user_mod", params)

        if success:
            self.logger.info(f"Modified user: {uid}")
        else:
            self.logger.error(f"Failed to modify user: {uid}")

        return success

    def create_group(self, group: Group) -> Tuple[bool, Optional[str]]:
        """
        Create group in FreeIPA

        Args:
            group: Group object to create

        Returns:
            Tuple of (success, cn)
        """
        params = {
            "cn": group.cn,
            "description": group.description,
            "noprivate": False,
        }

        success, result = self._api_call("group_add", params)

        if success:
            self.logger.info(f"Created group: {group.cn}")
            return True, group.cn
        else:
            self.logger.error(f"Failed to create group: {group.cn}")
            return False, None

    def add_group_member(self, group_cn: str, uid: str) -> bool:
        """
        Add user to group

        Args:
            group_cn: Group name
            uid: User ID to add

        Returns:
            Success status
        """
        params = {
            "cn": group_cn,
            "user": uid,
        }

        success, _ = self._api_call("group_add_member", params)

        if success:
            self.logger.info(f"Added {uid} to group {group_cn}")
        else:
            self.logger.debug(f"User {uid} already in group {group_cn} or not found")

        return success

    def remove_group_member(self, group_cn: str, uid: str) -> bool:
        """
        Remove user from group

        Args:
            group_cn: Group name
            uid: User ID to remove

        Returns:
            Success status
        """
        params = {
            "cn": group_cn,
            "user": uid,
        }

        success, _ = self._api_call("group_remove_member", params)

        if success:
            self.logger.info(f"Removed {uid} from group {group_cn}")
        else:
            self.logger.debug(f"Failed to remove {uid} from {group_cn}")

        return success

    def create_sudo_rule(self, rule: SudoRule) -> Tuple[bool, Optional[str]]:
        """
        Create sudo rule in FreeIPA

        Args:
            rule: SudoRule object to create

        Returns:
            Tuple of (success, rule_name)
        """
        params = {
            "sudorule_name": rule.name,
            "description": f"Privilege escalation for {', '.join(rule.users)}",
        }

        success, result = self._api_call("sudorule_add", params)

        if not success:
            self.logger.error(f"Failed to create sudo rule: {rule.name}")
            return False, None

        # Add users
        for user in rule.users:
            user_params = {
                "sudorule_name": rule.name,
                "group": user if user.startswith("%") else None,
                "user": user if not user.startswith("%") else None,
            }
            # Clean up None values
            user_params = {k: v for k, v in user_params.items() if v is not None}

            self._api_call("sudorule_add_user", user_params)

        # Add hosts
        for host in rule.hosts:
            host_params = {
                "sudorule_name": rule.name,
                "host": host,
            }
            self._api_call("sudorule_add_host", host_params)

        # Add commands
        for cmd in rule.commands:
            cmd_params = {
                "sudorule_name": rule.name,
                "allow_sudocmd": cmd,
            }
            self._api_call("sudorule_add_allow_command", cmd_params)

        self.logger.info(f"Created sudo rule: {rule.name}")
        return True, rule.name

    def set_password_policy(self, max_age: int = 90, min_length: int = 12) -> bool:
        """
        Set global password policy

        Args:
            max_age: Password maximum age in days
            min_length: Minimum password length

        Returns:
            Success status
        """
        params = {
            "krbmaxpwdlife": max_age * 86400,  # Convert days to seconds
            "krbminpwdlength": min_length,
            "krbpwdhistorylength": 24,
        }

        success, _ = self._api_call("pwpolicy_mod", params)

        if success:
            self.logger.info(f"Password policy updated: max_age={max_age}d, min_len={min_length}")
        else:
            self.logger.error("Failed to set password policy")

        return success

    def request_certificate(
        self,
        principal: str,
        cn: str,
        san_list: Optional[List[str]] = None,
        lifetime_days: int = 365,
    ) -> Tuple[bool, Optional[str]]:
        """
        Request certificate from FreeIPA CA

        Args:
            principal: Kerberos principal (user@REALM or host/fqdn@REALM)
            cn: Common Name for certificate
            san_list: Subject Alternative Names
            lifetime_days: Certificate lifetime in days

        Returns:
            Tuple of (success, certificate_serial)
        """
        params = {
            "principal": principal,
            "cn": cn,
            "validity_period": lifetime_days,
        }

        if san_list:
            params["san"] = san_list

        success, result = self._api_call("cert_request", params)

        if success and result:
            serial = result.get("serial_number")
            self.logger.info(f"Certificate requested: {principal} (serial={serial})")
            return True, serial
        else:
            self.logger.error(f"Certificate request failed: {principal}")
            return False, None

    def revoke_certificate(self, serial: str, reason: str = "unspecified") -> bool:
        """
        Revoke certificate

        Args:
            serial: Certificate serial number
            reason: Revocation reason

        Returns:
            Success status
        """
        params = {
            "serial": serial,
            "revocation_reason": reason,
        }

        success, _ = self._api_call("cert_revoke", params)

        if success:
            self.logger.info(f"Certificate revoked: {serial}")
        else:
            self.logger.error(f"Certificate revocation failed: {serial}")

        return success

    def get_audit_logs(
        self,
        start_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve audit logs from FreeIPA

        Args:
            start_time: Start time for logs (defaults to 24 hours ago)
            limit: Maximum logs to retrieve

        Returns:
            List of audit log entries
        """
        if not start_time:
            start_time = datetime.now() - timedelta(hours=24)

        params = {
            "sizelimit": limit,
            "timelimit": 30,
        }

        success, result = self._api_call("audit_log_find", params)

        if success:
            logs = result.get("result", [])
            self.logger.info(f"Retrieved {len(logs)} audit logs")
            return logs
        else:
            self.logger.error("Failed to retrieve audit logs")
            return []


class VaultIntegration:
    """Guardian vault integration for user provisioning"""

    def __init__(self, vault_endpoint: str, vault_token: str):
        """
        Initialize vault integration

        Args:
            vault_endpoint: Guardian vault API endpoint
            vault_token: Vault authentication token
        """
        self.endpoint = vault_endpoint
        self.token = vault_token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {vault_token}",
            "Content-Type": "application/json",
        })
        self.logger = logging.getLogger(__name__)

    def get_active_users(self) -> List[Dict[str, Any]]:
        """
        Retrieve active users from Guardian vault

        Returns:
            List of user dictionaries
        """
        try:
            response = self.session.get(
                f"{self.endpoint}/api/v1/users",
                params={"status": "active"},
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            self.logger.error(f"Failed to get vault users: {e}")
            return []

    def get_user_roles(self, user_id: str) -> List[str]:
        """
        Get roles assigned to a user

        Args:
            user_id: User ID

        Returns:
            List of role names
        """
        try:
            response = self.session.get(
                f"{self.endpoint}/api/v1/users/{user_id}/roles",
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            return [role["name"] for role in data.get("roles", [])]
        except requests.RequestException as e:
            self.logger.error(f"Failed to get user roles: {e}")
            return []


class EnterpriseSetup:
    """Enterprise setup orchestration"""

    def __init__(
        self,
        freeipa_host: str,
        freeipa_realm: str,
        freeipa_admin: str,
        freeipa_password: str,
        config_file: Optional[str] = None,
    ):
        """
        Initialize enterprise setup

        Args:
            freeipa_host: FreeIPA server FQDN
            freeipa_realm: Kerberos realm
            freeipa_admin: FreeIPA admin user
            freeipa_password: FreeIPA admin password
            config_file: Optional configuration file path
        """
        self.client = FreeIPAClient(
            freeipa_host,
            freeipa_realm,
            freeipa_admin,
            freeipa_password,
        )
        self.config = {}
        if config_file:
            with open(config_file) as f:
                self.config = json.load(f)
        self.logger = logging.getLogger(__name__)

    def generate_password(self, length: int = 16) -> str:
        """
        Generate secure random password

        Args:
            length: Password length

        Returns:
            Generated password
        """
        return secrets.token_urlsafe(length)

    def setup_default_groups(self) -> bool:
        """
        Create default security groups

        Returns:
            Success status
        """
        groups = [
            Group("shadow-admins", "Guardian vault administrators"),
            Group("shadow-auditors", "Security auditors with read-only access"),
            Group("shadow-analysts", "Threat analysts with operational access"),
            Group("shadow-soc", "Security operations center staff"),
            Group("shadow-incident-response", "Incident response team"),
            Group("shadow-compliance", "Compliance and risk management"),
        ]

        for group in groups:
            success, _ = self.client.create_group(group)
            if not success:
                self.logger.warning(f"Failed to create group: {group.cn}")

        return True

    def setup_sudo_rules(self) -> bool:
        """
        Create default sudo rules for roles

        Returns:
            Success status
        """
        rules = [
            SudoRule(
                name="soc-operator-sudo",
                users=["%shadow-soc"],
                hosts=["+shadowcypher-servers"],
                commands=[
                    "/bin/systemctl restart *",
                    "/bin/systemctl restart",
                    "/usr/bin/tail",
                    "/usr/bin/journalctl",
                ],
                options=["!authenticate", "log_output"],
            ),
            SudoRule(
                name="incident-response-sudo",
                users=["%shadow-incident-response"],
                hosts=["+shadowcypher-servers"],
                commands=["ALL"],
                options=["!authenticate", "log_output"],
            ),
        ]

        for rule in rules:
            success, _ = self.client.create_sudo_rule(rule)
            if not success:
                self.logger.warning(f"Failed to create sudo rule: {rule.name}")

        return True

    def setup_password_policy(self) -> bool:
        """
        Configure password policy

        Returns:
            Success status
        """
        max_age = self.config.get("password_policy", {}).get("max_age_days", 90)
        min_length = self.config.get("password_policy", {}).get("min_length", 12)

        return self.client.set_password_policy(max_age=max_age, min_length=min_length)

    def provision_vault_users(self, vault_endpoint: str, vault_token: str) -> bool:
        """
        Provision users from Guardian vault

        Args:
            vault_endpoint: Vault API endpoint
            vault_token: Vault authentication token

        Returns:
            Success status
        """
        vault = VaultIntegration(vault_endpoint, vault_token)
        vault_users = vault.get_active_users()

        for vault_user in vault_users:
            uid = vault_user.get("id")
            cn = vault_user.get("full_name", uid)
            email = vault_user.get("email", f"{uid}@shadowcypher.site")

            # Generate Kerberos password
            password = self.generate_password()

            user = User(
                uid=uid,
                cn=cn,
                mail=email,
                password=password,
                description=f"Guardian vault user",
                clearance_level=vault_user.get("clearance_level", "user"),
            )

            success, _ = self.client.create_user(user)

            if success:
                # Add to appropriate groups based on roles
                roles = vault.get_user_roles(uid)
                self._assign_groups(uid, roles)

        return True

    def _assign_groups(self, uid: str, roles: List[str]) -> None:
        """
        Assign user to groups based on roles

        Args:
            uid: User ID
            roles: List of role names
        """
        group_mappings = {
            "admin": "shadow-admins",
            "auditor": "shadow-auditors",
            "analyst": "shadow-analysts",
            "soc": "shadow-soc",
            "incident-response": "shadow-incident-response",
            "compliance": "shadow-compliance",
        }

        for role in roles:
            group = group_mappings.get(role)
            if group:
                self.client.add_group_member(group, uid)

    def run_full_setup(self) -> bool:
        """
        Execute full enterprise setup

        Returns:
            Success status
        """
        if not self.client.authenticate():
            self.logger.error("Failed to authenticate to FreeIPA")
            return False

        steps = [
            ("Setting up default groups", self.setup_default_groups),
            ("Setting up sudo rules", self.setup_sudo_rules),
            ("Configuring password policy", self.setup_password_policy),
        ]

        for step_name, step_func in steps:
            self.logger.info(f"Starting: {step_name}")
            if not step_func():
                self.logger.error(f"Failed: {step_name}")
                return False
            self.logger.info(f"Completed: {step_name}")

        return True


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="FreeIPA Integration Setup for ShadowCypher"
    )
    parser.add_argument("--host", required=True, help="FreeIPA server FQDN")
    parser.add_argument("--realm", required=True, help="Kerberos realm")
    parser.add_argument("--admin-user", required=True, help="FreeIPA admin username")
    parser.add_argument("--admin-password", required=True, help="FreeIPA admin password")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--vault-endpoint", help="Guardian vault endpoint")
    parser.add_argument("--vault-token", help="Guardian vault token")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    setup = EnterpriseSetup(
        args.host,
        args.realm,
        args.admin_user,
        args.admin_password,
        args.config,
    )

    if args.vault_endpoint and args.vault_token:
        setup.provision_vault_users(args.vault_endpoint, args.vault_token)

    success = setup.run_full_setup()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
