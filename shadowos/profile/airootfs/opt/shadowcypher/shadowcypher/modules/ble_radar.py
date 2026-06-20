"""
BLE Proximity Radar (T4-1).
Bluetooth Low Energy MAC scanner for physical proximity surveillance.
Tracks nearby devices, their signal strength, manufacturer, and movement.
Requires: pip install bleak
"""
import asyncio
import time
import threading
from dataclasses import dataclass, field
from typing import Optional, Callable
from shadowcypher.core.logger import logger

try:
    from bleak import BleakScanner
    from bleak.backends.device import BLEDevice
    from bleak.backends.scanner import AdvertisementData
    HAS_BLEAK = True
except ImportError:
    HAS_BLEAK = False

# OUI → Manufacturer (partial list of common vendors)
OUI_MAP = {
    "AC:DE:48": "Apple", "00:17:F2": "Apple", "F8:FF:C2": "Apple",
    "00:23:14": "Apple", "B8:8D:12": "Apple", "8C:85:90": "Apple",
    "E0:55:3D": "Samsung", "94:35:0A": "Samsung", "FC:A1:3E": "Samsung",
    "00:1A:11": "Google", "54:60:09": "Google",
    "00:15:5D": "Microsoft", "28:18:78": "Microsoft",
    "DC:A6:32": "Raspberry Pi", "B8:27:EB": "Raspberry Pi",
    "00:1B:44": "SonyEricsson", "00:1F:E4": "Sony",
}


@dataclass
class BLETarget:
    mac: str
    name: str
    rssi: int
    manufacturer: str
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    seen_count: int = 1
    services: list = field(default_factory=list)
    raw_adv: dict = field(default_factory=dict)

    @property
    def distance_estimate(self) -> str:
        """Rough distance estimate from RSSI (very approximate)."""
        if self.rssi >= -50:
            return "~1m (very close)"
        if self.rssi >= -65:
            return "~5m (close)"
        if self.rssi >= -75:
            return "~10m (nearby)"
        if self.rssi >= -85:
            return "~20m (distant)"
        return ">30m (far)"

    def to_dict(self) -> dict:
        return {
            "mac": self.mac, "name": self.name, "rssi": self.rssi,
            "manufacturer": self.manufacturer, "distance": self.distance_estimate,
            "first_seen": self.first_seen, "last_seen": self.last_seen,
            "seen_count": self.seen_count, "services": self.services,
        }

    def __str__(self) -> str:
        age = round(time.time() - self.last_seen, 1)
        return (f"  [{self.rssi:4d}dBm] {self.mac}  {self.name or '(unknown)':20s}"
                f"  {self.manufacturer:12s}  {self.distance_estimate}  seen {self.seen_count}x  {age}s ago")


class BLERadar:
    """
    Passive BLE scanner — detects, tracks, and logs nearby Bluetooth devices.
    Useful for:
    - Physical proximity surveillance (is a target in the building?)
    - MAC address fingerprinting
    - Detecting IoT devices, trackers, wearables
    - RF environment mapping
    """

    def __init__(self):
        self._targets: dict[str, BLETarget] = {}
        self._lock = threading.Lock()
        self._scanning = False
        self._scan_thread: Optional[threading.Thread] = None
        self._on_new_device: Optional[Callable] = None
        self._on_device_lost: Optional[Callable] = None

    # ── Public API ────────────────────────────────────────────────────────────

    def start_scan(self, duration: int = 0, on_output: Callable = None,
                   on_new_device: Callable = None,
                   on_device_lost: Callable = None) -> bool:
        """
        Start continuous BLE scanning.

        Args:
            duration: Scan for N seconds, then stop. 0 = continuous until stop().
            on_output: Stream device discovery to this callback.
            on_new_device: Called with BLETarget when a new device appears.
            on_device_lost: Called with BLETarget when a device hasn't been seen for 60s.
        """
        if not HAS_BLEAK:
            if on_output:
                on_output("[BLE] DEPENDENCY_MISSING: pip install bleak\n")
            return False

        if self._scanning:
            if on_output:
                on_output("[BLE] Already scanning\n")
            return True

        self._on_new_device = on_new_device
        self._on_device_lost = on_device_lost
        self._scanning = True

        def _run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    self._scan_loop(duration, on_output)
                )
            except Exception as e:
                if on_output:
                    on_output(f"[BLE] SCAN_ERROR: {e}\n")
            finally:
                self._scanning = False
                loop.close()

        self._scan_thread = threading.Thread(target=_run, daemon=True, name="BLERadar")
        self._scan_thread.start()

        if on_output:
            on_output(f"[BLE] RADAR_ACTIVE — scanning for BLE devices"
                      f"{f' ({duration}s)' if duration else ' (continuous)'}...\n")
        return True

    def stop_scan(self):
        self._scanning = False

    def get_targets(self, min_rssi: int = -100,
                    active_only: bool = True) -> list[BLETarget]:
        """Get current target list sorted by RSSI (strongest first)."""
        cutoff = time.time() - 60
        with self._lock:
            targets = list(self._targets.values())
        if active_only:
            targets = [t for t in targets if t.last_seen >= cutoff]
        targets = [t for t in targets if t.rssi >= min_rssi]
        return sorted(targets, key=lambda t: t.rssi, reverse=True)

    def watch_mac(self, mac: str, on_output: Callable = None) -> bool:
        """Alert if a specific MAC address is detected nearby."""
        mac = mac.upper()
        with self._lock:
            if mac in self._targets:
                t = self._targets[mac]
                if on_output:
                    on_output(f"[BLE] TARGET_DETECTED: {mac} is nearby! {t}\n")
                return True
        if on_output:
            on_output(f"[BLE] {mac} not currently detected\n")
        return False

    def print_radar(self, on_output: Callable = None):
        """Print current radar state."""
        targets = self.get_targets()
        header = f"\n[BLE RADAR] {len(targets)} active device(s)\n" + "─" * 90 + "\n"
        if on_output:
            on_output(header)
            for t in targets:
                on_output(str(t) + "\n")

    # ── Internals ─────────────────────────────────────────────────────────────

    async def _scan_loop(self, duration: int, cb: Callable):
        start = time.time()
        reaper_ts = time.time()

        def _detection_cb(device: "BLEDevice", adv: "AdvertisementData"):
            mac = device.address.upper()
            oui = mac[:8]
            manufacturer = OUI_MAP.get(oui, "Unknown")
            # Try manufacturer data
            if adv.manufacturer_data:
                manufacturer = manufacturer  # keep OUI match
            services = list(adv.service_uuids or [])

            with self._lock:
                if mac in self._targets:
                    t = self._targets[mac]
                    t.rssi = device.rssi
                    t.last_seen = time.time()
                    t.seen_count += 1
                    if services:
                        t.services = services
                else:
                    t = BLETarget(
                        mac=mac,
                        name=device.name or "",
                        rssi=device.rssi,
                        manufacturer=manufacturer,
                        services=services,
                    )
                    self._targets[mac] = t
                    if self._on_new_device:
                        try:
                            self._on_new_device(t)
                        except Exception:
                            pass
                    if cb:
                        try:
                            cb(f"[BLE] NEW: {t}\n")
                        except Exception:
                            pass

        async with BleakScanner(detection_callback=_detection_cb):
            while self._scanning:
                await asyncio.sleep(1)

                # Reaper: remove devices not seen for 60s
                if time.time() - reaper_ts > 30:
                    reaper_ts = time.time()
                    cutoff = time.time() - 60
                    with self._lock:
                        lost = [t for t in self._targets.values()
                                if t.last_seen < cutoff]
                        for t in lost:
                            del self._targets[t.mac]
                            if self._on_device_lost:
                                try:
                                    self._on_device_lost(t)
                                except Exception:
                                    pass
                            if cb:
                                try:
                                    cb(f"[BLE] LOST: {t.mac} ({t.name})\n")
                                except Exception:
                                    pass

                if duration and (time.time() - start) >= duration:
                    self._scanning = False
                    break


ble_radar = BLERadar()
