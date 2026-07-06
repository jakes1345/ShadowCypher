#!/usr/bin/env python3
"""
Device Registry Manager for ShadowCypher

Manages certified devices registry, validation, and compatibility checking.
Provides methods for device lookup, filtering, and certification verification.
"""

import json
import os
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path


class DeviceRegistry:
    """
    Device Registry Manager for certified devices.

    Manages the certified devices database, provides lookup and filtering
    capabilities, and validates device certifications.
    """

    # Registry file path
    REGISTRY_PATH = Path(__file__).parent.parent / ".github" / "certified-devices.json"

    def __init__(self, registry_path: Optional[Path] = None):
        """
        Initialize the DeviceRegistry.

        Args:
            registry_path: Path to certified devices JSON file.
                          Defaults to .github/certified-devices.json
        """
        if registry_path:
            self.registry_path = Path(registry_path)
        else:
            self.registry_path = self.REGISTRY_PATH

        self.devices: List[Dict[str, Any]] = []
        self.load_registry()

    def load_registry(self) -> bool:
        """
        Load the certified devices registry from JSON file.

        Returns:
            bool: True if registry loaded successfully, False otherwise

        Raises:
            FileNotFoundError: If registry file does not exist
            json.JSONDecodeError: If registry file is invalid JSON
        """
        try:
            if not self.registry_path.exists():
                raise FileNotFoundError(f"Registry file not found: {self.registry_path}")

            with open(self.registry_path, 'r') as f:
                data = json.load(f)

            self.devices = data.get('certified_devices', [])
            return True

        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading registry: {e}")
            raise

    def get_by_manufacturer(self, manufacturer: str) -> List[Dict[str, Any]]:
        """
        Get all devices by manufacturer name.

        Args:
            manufacturer: Manufacturer name to filter by

        Returns:
            List of device records matching the manufacturer
        """
        return [
            device for device in self.devices
            if device.get('manufacturer', '').lower() == manufacturer.lower()
        ]

    def get_gold_certified(self) -> List[Dict[str, Any]]:
        """
        Get all Gold-certified devices.

        Returns:
            List of Gold-certified device records
        """
        return [
            device for device in self.devices
            if device.get('certification_level') == 'gold'
        ]

    def get_silver_certified(self) -> List[Dict[str, Any]]:
        """
        Get all Silver-certified devices.

        Returns:
            List of Silver-certified device records
        """
        return [
            device for device in self.devices
            if device.get('certification_level') == 'silver'
        ]

    def get_community_verified(self) -> List[Dict[str, Any]]:
        """
        Get all Community-verified devices.

        Returns:
            List of Community-verified device records
        """
        return [
            device for device in self.devices
            if device.get('certification_level') == 'community'
        ]

    def get_by_id(self, device_id: str) -> Optional[Dict[str, Any]]:
        """
        Get device by unique ID.

        Args:
            device_id: Unique device identifier

        Returns:
            Device record if found, None otherwise
        """
        for device in self.devices:
            if device.get('id', '').upper() == device_id.upper():
                return device
        return None

    def find_compatible(self,
                       kernel_version: str = None,
                       min_ram_gb: int = None,
                       min_storage_gb: int = None,
                       certification_level: str = None) -> List[Dict[str, Any]]:
        """
        Find devices compatible with specified requirements.

        Args:
            kernel_version: Minimum kernel version (e.g., "6.8")
            min_ram_gb: Minimum RAM in GB
            min_storage_gb: Minimum storage in GB
            certification_level: Filter by certification level (gold, silver, community)

        Returns:
            List of compatible device records
        """
        compatible = self.devices[:]

        # Filter by kernel version
        if kernel_version:
            compatible = [
                d for d in compatible
                if self._compare_versions(d.get('kernel_version', ''), kernel_version) >= 0
            ]

        # Filter by RAM requirement
        if min_ram_gb:
            compatible = [
                d for d in compatible
                if self._extract_ram_gb(d.get('ram_supported', '')) >= min_ram_gb
            ]

        # Filter by storage requirement
        if min_storage_gb:
            compatible = [
                d for d in compatible
                if self._extract_storage_gb(d.get('storage', '')) >= min_storage_gb
            ]

        # Filter by certification level
        if certification_level:
            compatible = [
                d for d in compatible
                if d.get('certification_level') == certification_level.lower()
            ]

        return compatible

    def get_devices_with_issues(self) -> List[Dict[str, Any]]:
        """
        Get all devices that have known issues.

        Returns:
            List of device records with issues
        """
        return [
            device for device in self.devices
            if device.get('issues', [])
        ]

    def print_summary(self) -> None:
        """
        Print a summary of the device registry.

        Outputs certification level counts, manufacturer breakdown,
        and devices with known issues.
        """
        gold = self.get_gold_certified()
        silver = self.get_silver_certified()
        community = self.get_community_verified()
        with_issues = self.get_devices_with_issues()

        print("=" * 70)
        print("SHADOWCYPHER CERTIFIED DEVICES REGISTRY SUMMARY")
        print("=" * 70)

        print(f"\nTotal Devices: {len(self.devices)}")
        print(f"  Gold-Certified:     {len(gold)}")
        print(f"  Silver-Certified:   {len(silver)}")
        print(f"  Community-Verified: {len(community)}")
        print(f"  Devices with Issues: {len(with_issues)}")

        # Manufacturer breakdown
        manufacturers = {}
        for device in self.devices:
            mfr = device.get('manufacturer', 'Unknown')
            manufacturers[mfr] = manufacturers.get(mfr, 0) + 1

        print("\nManufacturer Breakdown:")
        for mfr in sorted(manufacturers.keys()):
            print(f"  {mfr}: {manufacturers[mfr]}")

        # Devices with issues
        if with_issues:
            print("\nDevices with Known Issues:")
            for device in with_issues:
                device_id = device.get('id', 'Unknown')
                model = device.get('model', 'Unknown')
                issues = device.get('issues', [])
                print(f"  {device_id} ({model}):")
                for issue in issues:
                    print(f"    - {issue}")

        print("\n" + "=" * 70)

    def export_by_certification_level(self, level: str, output_path: Path) -> bool:
        """
        Export devices of specific certification level to JSON file.

        Args:
            level: Certification level (gold, silver, community)
            output_path: Path to output JSON file

        Returns:
            bool: True if export successful, False otherwise
        """
        try:
            if level.lower() == 'gold':
                devices = self.get_gold_certified()
            elif level.lower() == 'silver':
                devices = self.get_silver_certified()
            elif level.lower() == 'community':
                devices = self.get_community_verified()
            else:
                print(f"Unknown certification level: {level}")
                return False

            export_data = {
                'certification_level': level.lower(),
                'device_count': len(devices),
                'exported_at': datetime.now().isoformat(),
                'devices': devices
            }

            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2)

            return True

        except Exception as e:
            print(f"Error exporting devices: {e}")
            return False

    @staticmethod
    def _compare_versions(version1: str, version2: str) -> int:
        """
        Compare two version strings (e.g., "6.8" vs "6.6").

        Args:
            version1: First version string
            version2: Second version string

        Returns:
            1 if version1 > version2, -1 if version1 < version2, 0 if equal
        """
        try:
            # Handle versions with '+' suffix (e.g., "6.8+")
            v1_parts = version1.rstrip('+').split('.')
            v2_parts = version2.rstrip('+').split('.')

            for i in range(max(len(v1_parts), len(v2_parts))):
                v1_num = int(v1_parts[i]) if i < len(v1_parts) else 0
                v2_num = int(v2_parts[i]) if i < len(v2_parts) else 0

                if v1_num > v2_num:
                    return 1
                elif v1_num < v2_num:
                    return -1

            return 0
        except (ValueError, AttributeError):
            return 0

    @staticmethod
    def _extract_ram_gb(ram_string: str) -> float:
        """
        Extract RAM amount in GB from string (e.g., "32GB LPDDR5X" -> 32).

        Args:
            ram_string: RAM specification string

        Returns:
            RAM amount in GB as float
        """
        try:
            # Extract number followed by 'GB'
            import re
            match = re.search(r'(\d+(?:\.\d+)?)\s*(?:GB|TB)', ram_string, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                # Handle TB conversion
                if 'TB' in ram_string.upper():
                    value *= 1024
                return value
            return 0
        except (ValueError, AttributeError):
            return 0

    @staticmethod
    def _extract_storage_gb(storage_string: str) -> float:
        """
        Extract storage capacity in GB from string (e.g., "1TB NVMe SSD" -> 1024).

        Args:
            storage_string: Storage specification string

        Returns:
            Storage capacity in GB as float
        """
        try:
            # Extract number followed by 'GB' or 'TB'
            import re
            match = re.search(r'(\d+(?:\.\d+)?)\s*(?:TB|GB)', storage_string, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                # Handle TB conversion
                if 'TB' in storage_string.upper():
                    value *= 1024
                return value
            return 0
        except (ValueError, AttributeError):
            return 0


def main():
    """CLI interface for device registry."""
    import sys

    # Initialize registry
    registry = DeviceRegistry()

    if len(sys.argv) < 2:
        registry.print_summary()
        return

    command = sys.argv[1].lower()

    if command == 'summary':
        registry.print_summary()

    elif command == 'gold':
        print(f"Gold-Certified Devices ({len(registry.get_gold_certified())}):")
        for device in registry.get_gold_certified():
            print(f"  {device['id']}: {device['manufacturer']} {device['model']}")

    elif command == 'silver':
        print(f"Silver-Certified Devices ({len(registry.get_silver_certified())}):")
        for device in registry.get_silver_certified():
            print(f"  {device['id']}: {device['manufacturer']} {device['model']}")

    elif command == 'community':
        print(f"Community-Verified Devices ({len(registry.get_community_verified())}):")
        for device in registry.get_community_verified():
            print(f"  {device['id']}: {device['manufacturer']} {device['model']}")

    elif command == 'lookup' and len(sys.argv) > 2:
        device_id = sys.argv[2]
        device = registry.get_by_id(device_id)
        if device:
            print(f"Device Found: {device['id']}")
            print(f"  Manufacturer: {device['manufacturer']}")
            print(f"  Model: {device['model']}")
            print(f"  CPU: {device['cpu']}")
            print(f"  RAM: {device['ram_supported']}")
            print(f"  Storage: {device['storage']}")
            print(f"  Certification: {device['certification_level'].upper()}")
            print(f"  Verified by: {device['verified_by']}")
            if device.get('issues'):
                print(f"  Issues: {', '.join(device['issues'])}")
        else:
            print(f"Device not found: {device_id}")

    elif command == 'manufacturer' and len(sys.argv) > 2:
        manufacturer = sys.argv[2]
        devices = registry.get_by_manufacturer(manufacturer)
        print(f"Devices from {manufacturer} ({len(devices)}):")
        for device in devices:
            print(f"  {device['id']}: {device['model']} ({device['certification_level']})")

    else:
        print("Usage:")
        print("  device-registry.py [summary]                    - Show registry summary")
        print("  device-registry.py gold                          - List gold-certified")
        print("  device-registry.py silver                        - List silver-certified")
        print("  device-registry.py community                     - List community-verified")
        print("  device-registry.py lookup <device-id>            - Lookup device by ID")
        print("  device-registry.py manufacturer <manufacturer>   - List by manufacturer")


if __name__ == '__main__':
    main()
