"""
ShadowCypher Vendor Partnership API Client Module

Provides unified interface for integrating threat intelligence feeds,
hardware vendors, and cloud services. Handles authentication, data sync,
webhook processing, and credential management.

Author: ShadowCypher Development Team
License: Sovereign
"""

import json
import hmac
import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Awaitable
from pathlib import Path
import asyncio
import aiohttp
from urllib.parse import urljoin

import pydantic
from pydantic import BaseModel, Field, ValidationError


logger = logging.getLogger(__name__)


# ============================================================================
# Enums & Types
# ============================================================================

class PartnerTier(str, Enum):
    """Partnership tier classification."""
    TIER_1_THREAT_INTEL = "tier_1_threat_intel"
    TIER_2_HARDWARE = "tier_2_hardware"
    TIER_3_CLOUD_SAAS = "tier_3_cloud_saas"


class AuthType(str, Enum):
    """Authentication mechanism types."""
    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    MUTUAL_TLS = "mutual_tls"
    CUSTOM_HEADER = "custom_header"


class SyncStatus(str, Enum):
    """Status of a sync operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"


class PartnerStatus(str, Enum):
    """Activation status of a partner integration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"
    ERROR = "error"


# ============================================================================
# Exceptions
# ============================================================================

class PartnerAPIError(Exception):
    """Base exception for partner API errors."""

    def __init__(self, vendor: str, code: str, message: str,
                 transient: bool = False):
        self.vendor = vendor
        self.code = code
        self.message = message
        self.transient = transient  # True if error is retriable
        super().__init__(f"[{vendor}] {code}: {message}")


class PartnerAuthError(PartnerAPIError):
    """Authentication/authorization error."""
    pass


class PartnerRateLimitError(PartnerAPIError):
    """Rate limit exceeded."""

    def __init__(self, vendor: str, retry_after: Optional[int] = None):
        super().__init__(vendor, "RATE_LIMIT",
                        f"Rate limit exceeded (retry after {retry_after}s)",
                        transient=True)
        self.retry_after = retry_after or 60


class PartnerValidationError(PartnerAPIError):
    """Data validation error."""
    pass


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class SyncResult:
    """Result of a data synchronization operation."""
    vendor: str
    status: SyncStatus
    records_fetched: int
    records_valid: int
    records_ingested: int
    duration_seconds: float
    timestamp: datetime
    error: Optional[str] = None
    next_sync_time: Optional[datetime] = None


@dataclass
class WebhookEvent:
    """Incoming webhook event from a partner."""
    vendor: str
    event_type: str
    timestamp: datetime
    payload: Dict[str, Any]
    signature: Optional[str] = None
    verified: bool = False


class PartnerCredential(BaseModel):
    """Stored partner credential with metadata."""
    vendor: str
    auth_type: AuthType
    api_key: Optional[str] = Field(None, exclude=True)  # Never in JSON
    oauth_token: Optional[str] = Field(None, exclude=True)
    oauth_refresh_token: Optional[str] = Field(None, exclude=True)
    tls_cert_path: Optional[str] = None
    tls_key_path: Optional[str] = None
    custom_headers: Optional[Dict[str, str]] = Field(None, exclude=True)
    created_at: datetime
    expires_at: Optional[datetime] = None
    rotated_at: Optional[datetime] = None

    class Config:
        arbitrary_types_allowed = True


class PartnerCapability(BaseModel):
    """Vendor capability descriptor."""
    name: str
    description: str
    data_type: str  # e.g., "ip_reputation", "malware_samples"
    supported: bool = True


class PartnerInfo(BaseModel):
    """Partner integration metadata."""
    vendor_id: str
    name: str
    tier: PartnerTier
    endpoint: str
    auth_type: AuthType
    status: PartnerStatus
    rate_limit: str
    data_freshness: str
    agreement_date: datetime
    sla_uptime: float  # e.g., 99.5
    contact_name: str
    contact_email: str
    contact_support_url: str
    capabilities: List[PartnerCapability]
    last_sync: Optional[datetime] = None
    last_error: Optional[str] = None
    health_check_interval: int = 3600  # seconds

    class Config:
        arbitrary_types_allowed = True


# ============================================================================
# Partner API Client (Abstract Base)
# ============================================================================

class PartnerAPIClient(ABC):
    """Abstract base class for partner API integrations."""

    def __init__(self, vendor: str, endpoint: str, auth_type: AuthType,
                 credential: PartnerCredential,
                 session: Optional[aiohttp.ClientSession] = None):
        self.vendor = vendor
        self.endpoint = endpoint
        self.auth_type = auth_type
        self.credential = credential
        self.session = session or aiohttp.ClientSession()
        self._owned_session = session is None
        self._last_sync: Optional[datetime] = None
        self._cache: Dict[str, Any] = {}
        self.logger = logging.getLogger(f"partner.{vendor}")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        """Close HTTP session if owned by this client."""
        if self._owned_session and self.session:
            await self.session.close()

    def _build_headers(self) -> Dict[str, str]:
        """Build request headers with authentication."""
        headers = {"Content-Type": "application/json"}

        if self.auth_type == AuthType.API_KEY:
            if not self.credential.api_key:
                raise PartnerAuthError(self.vendor, "NO_CREDENTIALS",
                                      "API key not configured")
            headers["Authorization"] = f"Bearer {self.credential.api_key}"

        elif self.auth_type == AuthType.CUSTOM_HEADER:
            if self.credential.custom_headers:
                headers.update(self.credential.custom_headers)

        return headers

    async def _make_request(self, method: str, path: str,
                           params: Optional[Dict] = None,
                           json_data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated HTTP request to partner API."""
        url = urljoin(self.endpoint, path)
        headers = self._build_headers()

        try:
            async with self.session.request(
                method, url, headers=headers,
                params=params, json=json_data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:

                if resp.status == 401 or resp.status == 403:
                    raise PartnerAuthError(self.vendor, f"HTTP_{resp.status}",
                                         f"Authentication failed: {resp.reason}")

                if resp.status == 429:
                    retry_after = int(resp.headers.get("Retry-After", 60))
                    raise PartnerRateLimitError(self.vendor, retry_after)

                if resp.status >= 400:
                    error_text = await resp.text()
                    transient = resp.status >= 500
                    raise PartnerAPIError(
                        self.vendor, f"HTTP_{resp.status}",
                        f"{resp.reason}: {error_text[:200]}",
                        transient=transient
                    )

                return await resp.json()

        except aiohttp.ClientError as e:
            raise PartnerAPIError(self.vendor, "NETWORK_ERROR",
                                str(e), transient=True)

    @abstractmethod
    async def fetch_updates(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Fetch updates from partner API.

        Args:
            since: Only fetch records modified after this timestamp

        Returns:
            List of data records from partner

        Raises:
            PartnerAPIError: If fetch fails
        """
        pass

    @abstractmethod
    def validate_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate incoming data against schema.

        Args:
            data: Data to validate

        Returns:
            True if valid, False otherwise
        """
        pass

    def cache_locally(self, data: Dict[str, Any], key: Optional[str] = None) -> None:
        """
        Store data in local cache for quick access.

        Args:
            data: Data to cache
            key: Cache key (defaults to vendor + timestamp)
        """
        if key is None:
            key = f"{self.vendor}_{datetime.now().isoformat()}"

        self._cache[key] = {
            "data": data,
            "cached_at": datetime.now(),
            "ttl": 3600  # 1 hour default TTL
        }

    def get_cached(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve data from cache if not expired."""
        if key not in self._cache:
            return None

        cached = self._cache[key]
        age = (datetime.now() - cached["cached_at"]).total_seconds()

        if age > cached.get("ttl", 3600):
            del self._cache[key]
            return None

        return cached["data"]

    async def sync(self, since: Optional[datetime] = None) -> SyncResult:
        """
        Execute full sync cycle: fetch, validate, cache.

        Returns:
            SyncResult with operation details
        """
        start_time = datetime.now()

        try:
            records = await self.fetch_updates(since)
            fetched_count = len(records)

            valid_count = sum(1 for r in records if self.validate_data(r))

            for record in records:
                if self.validate_data(record):
                    self.cache_locally(record)

            duration = (datetime.now() - start_time).total_seconds()
            self._last_sync = datetime.now()

            return SyncResult(
                vendor=self.vendor,
                status=SyncStatus.SUCCESS,
                records_fetched=fetched_count,
                records_valid=valid_count,
                records_ingested=valid_count,
                duration_seconds=duration,
                timestamp=datetime.now(),
                next_sync_time=self._last_sync + timedelta(hours=1)
            )

        except PartnerRateLimitError as e:
            duration = (datetime.now() - start_time).total_seconds()
            return SyncResult(
                vendor=self.vendor,
                status=SyncStatus.RATE_LIMITED,
                records_fetched=0,
                records_valid=0,
                records_ingested=0,
                duration_seconds=duration,
                timestamp=datetime.now(),
                error=str(e),
                next_sync_time=datetime.now() + timedelta(seconds=e.retry_after)
            )

        except PartnerAPIError as e:
            duration = (datetime.now() - start_time).total_seconds()
            return SyncResult(
                vendor=self.vendor,
                status=SyncStatus.FAILED,
                records_fetched=0,
                records_valid=0,
                records_ingested=0,
                duration_seconds=duration,
                timestamp=datetime.now(),
                error=str(e)
            )


# ============================================================================
# Webhook Handler
# ============================================================================

class WebhookHandler:
    """Process incoming webhooks from partner platforms."""

    def __init__(self, vendor: str, signing_key: str):
        self.vendor = vendor
        self.signing_key = signing_key.encode() if isinstance(signing_key, str) else signing_key
        self.logger = logging.getLogger(f"webhook.{vendor}")
        self._event_log: List[WebhookEvent] = []

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify webhook signature using HMAC-SHA256.

        Args:
            payload: Raw request body
            signature: Signature from webhook header

        Returns:
            True if signature is valid
        """
        expected = hmac.new(
            self.signing_key,
            payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected)

    async def process_event(self, event: Dict[str, Any],
                          signature: Optional[str] = None) -> WebhookEvent:
        """
        Process incoming webhook event atomically.

        Args:
            event: Webhook payload
            signature: Optional signature for verification

        Returns:
            Processed WebhookEvent

        Raises:
            PartnerValidationError: If event is invalid
        """
        payload_json = json.dumps(event, sort_keys=True).encode()
        verified = False

        if signature:
            verified = self.verify_signature(payload_json, signature)
            if not verified:
                self.logger.warning(f"Invalid signature from {self.vendor}")

        try:
            webhook_event = WebhookEvent(
                vendor=self.vendor,
                event_type=event.get("type", "unknown"),
                timestamp=datetime.now(),
                payload=event,
                signature=signature,
                verified=verified
            )
        except Exception as e:
            raise PartnerValidationError(self.vendor, "INVALID_EVENT",
                                        f"Event validation failed: {str(e)}")

        self._event_log.append(webhook_event)
        self.logger.info(f"Processed webhook event: {webhook_event.event_type}")

        return webhook_event

    def get_event_log(self, limit: int = 100) -> List[WebhookEvent]:
        """Retrieve webhook event audit log."""
        return self._event_log[-limit:]


# ============================================================================
# Credential Manager
# ============================================================================

class CredentialManager:
    """Manage partner API credentials securely."""

    def __init__(self, storage_path: Path):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("credentials")

    def store_credential(self, credential: PartnerCredential) -> None:
        """
        Store credential securely (should use encryption in production).

        Args:
            credential: Credential to store
        """
        credentials = self._load_all()
        credentials[credential.vendor] = credential.dict(exclude_none=True)

        self.storage_path.write_text(
            json.dumps(credentials, indent=2, default=str)
        )
        self.logger.info(f"Stored credential for {credential.vendor}")

    def get_credential(self, vendor: str) -> Optional[PartnerCredential]:
        """Retrieve stored credential."""
        credentials = self._load_all()

        if vendor not in credentials:
            return None

        try:
            return PartnerCredential(**credentials[vendor])
        except ValidationError as e:
            self.logger.error(f"Invalid credential for {vendor}: {e}")
            return None

    def delete_credential(self, vendor: str) -> bool:
        """Delete stored credential."""
        credentials = self._load_all()

        if vendor in credentials:
            del credentials[vendor]
            self.storage_path.write_text(
                json.dumps(credentials, indent=2, default=str)
            )
            self.logger.info(f"Deleted credential for {vendor}")
            return True

        return False

    def _load_all(self) -> Dict[str, Dict]:
        """Load all stored credentials."""
        if not self.storage_path.exists():
            return {}

        try:
            return json.loads(self.storage_path.read_text())
        except json.JSONDecodeError:
            self.logger.warning("Credential store corrupted, starting fresh")
            return {}


# ============================================================================
# Partner Registry
# ============================================================================

class PartnerRegistry:
    """Load and manage partner integrations from registry file."""

    def __init__(self, registry_path: Path):
        self.registry_path = Path(registry_path)
        self.logger = logging.getLogger("registry")
        self.partners: Dict[str, PartnerInfo] = {}
        self._load_registry()

    def _load_registry(self) -> None:
        """Load partner registry from JSON file."""
        if not self.registry_path.exists():
            self.logger.warning(f"Registry file not found: {self.registry_path}")
            return

        try:
            data = json.loads(self.registry_path.read_text())

            for vendor_id, partner_data in data.get("partners", {}).items():
                partner_data["vendor_id"] = vendor_id
                partner_data["tier"] = PartnerTier(partner_data.get("tier"))
                partner_data["auth_type"] = AuthType(partner_data.get("auth_type"))
                partner_data["status"] = PartnerStatus(partner_data.get("status"))

                # Parse dates
                if partner_data.get("agreement_date"):
                    partner_data["agreement_date"] = datetime.fromisoformat(
                        partner_data["agreement_date"]
                    )
                if partner_data.get("last_sync"):
                    partner_data["last_sync"] = datetime.fromisoformat(
                        partner_data["last_sync"]
                    )

                # Parse capabilities
                caps = []
                for cap in partner_data.get("capabilities", []):
                    if isinstance(cap, str):
                        caps.append(PartnerCapability(
                            name=cap,
                            description="",
                            data_type=cap,
                            supported=True
                        ))
                    else:
                        caps.append(PartnerCapability(**cap))
                partner_data["capabilities"] = caps

                try:
                    partner = PartnerInfo(**partner_data)
                    self.partners[vendor_id] = partner
                except ValidationError as e:
                    self.logger.error(f"Invalid partner entry {vendor_id}: {e}")

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse registry: {e}")

    def get_partner(self, vendor_id: str) -> Optional[PartnerInfo]:
        """Get partner by ID."""
        return self.partners.get(vendor_id)

    def get_active_partners(self) -> List[PartnerInfo]:
        """Get all active partners."""
        return [p for p in self.partners.values()
                if p.status == PartnerStatus.ACTIVE]

    def get_partners_by_tier(self, tier: PartnerTier) -> List[PartnerInfo]:
        """Get partners by tier."""
        return [p for p in self.partners.values() if p.tier == tier]


# ============================================================================
# Health Check Monitor
# ============================================================================

class PartnerHealthMonitor:
    """Monitor health and status of partner integrations."""

    def __init__(self, registry: PartnerRegistry,
                 credential_mgr: CredentialManager):
        self.registry = registry
        self.credential_mgr = credential_mgr
        self.logger = logging.getLogger("health")
        self.health_status: Dict[str, Dict[str, Any]] = {}

    async def check_partner_health(self, vendor_id: str) -> Dict[str, Any]:
        """
        Check health of a single partner integration.

        Returns:
            Health status dict with: reachable, last_sync_age, error_rate, etc.
        """
        partner = self.registry.get_partner(vendor_id)
        if not partner:
            return {"vendor": vendor_id, "status": "unknown"}

        credential = self.credential_mgr.get_credential(vendor_id)
        if not credential:
            return {"vendor": vendor_id, "status": "unconfigured"}

        status = {
            "vendor": vendor_id,
            "name": partner.name,
            "status": partner.status.value,
            "api_reachable": False,
            "last_sync": partner.last_sync.isoformat() if partner.last_sync else None,
            "last_error": partner.last_error,
            "checked_at": datetime.now().isoformat()
        }

        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {credential.api_key}"}
                async with session.head(partner.endpoint, headers=headers,
                                       timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    status["api_reachable"] = resp.status < 500
                    status["http_status"] = resp.status
        except Exception as e:
            status["api_reachable"] = False
            status["error"] = str(e)

        self.health_status[vendor_id] = status
        return status

    async def check_all_partners(self) -> Dict[str, Dict[str, Any]]:
        """Check health of all active partners."""
        tasks = [
            self.check_partner_health(p.vendor_id)
            for p in self.registry.get_active_partners()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        return {r.get("vendor"): r for r in results if isinstance(r, dict)}


# ============================================================================
# Main Entry Point
# ============================================================================

def initialize_partner_system(
    registry_path: Path,
    credential_storage_path: Path
) -> tuple[PartnerRegistry, CredentialManager, PartnerHealthMonitor]:
    """
    Initialize the partner integration system.

    Args:
        registry_path: Path to partner-registry.json
        credential_storage_path: Path to store credentials

    Returns:
        Tuple of (registry, credential_manager, health_monitor)
    """
    registry = PartnerRegistry(registry_path)
    credential_mgr = CredentialManager(credential_storage_path)
    health_monitor = PartnerHealthMonitor(registry, credential_mgr)

    return registry, credential_mgr, health_monitor


if __name__ == "__main__":
    # Example usage
    print("ShadowCypher Partner API Module")
    print("Import as: from shadowcypher.api.partner_api import *")
