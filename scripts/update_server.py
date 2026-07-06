#!/usr/bin/env python3

"""
ShadowCypher Update Server

Simple Flask-based HTTP server for delivering ShadowCypher updates.
Provides endpoints to:
- Check for available updates
- Download update packages
- Verify version compatibility
- Support different OS/architecture variants
"""

import os
import json
import hashlib
import logging
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple

try:
    from flask import Flask, jsonify, send_file, request
    from werkzeug.exceptions import NotFound, BadRequest
except ImportError:
    print("Error: Flask not installed. Install with: pip install flask")
    exit(1)

# Configuration
APP_NAME = "ShadowCypher Update Server"
APP_VERSION = "1.0.0"
DEBUG = False
HOST = "0.0.0.0"
PORT = 5000

# Package metadata
UPDATES_DIR = Path(__file__).parent.parent / ".shadowcypher" / "updates"
RELEASES_FILE = Path(__file__).parent.parent / ".shadowcypher" / "releases.json"

# Supported platforms and architectures
SUPPORTED_PLATFORMS = ["linux", "windows", "macos"]
SUPPORTED_ARCHS = ["x86_64", "arm64", "armv7"]

# Version manifest (would be loaded from database in production)
RELEASES = {
    "2.5.0": {
        "version": "2.5.0",
        "released": "2026-07-03",
        "channel": "stable",
        "security_patches": 3,
        "features": 8,
        "changelog": "Security patches and new features",
        "packages": {
            "linux": {
                "x86_64": {
                    "filename": "shadowcypher-2.5.0-x86_64.tar.gz",
                    "size_mb": 148,
                    "sha256": "abc123def456ghi789jkl000",
                },
                "arm64": {
                    "filename": "shadowcypher-2.5.0-arm64.tar.gz",
                    "size_mb": 142,
                    "sha256": "xyz987uvw654rst321opq111",
                },
            },
            "macos": {
                "x86_64": {
                    "filename": "shadowcypher-2.5.0-macos-x86_64.dmg",
                    "size_mb": 156,
                    "sha256": "mno456pqr123stu789vwx222",
                },
                "arm64": {
                    "filename": "shadowcypher-2.5.0-macos-arm64.dmg",
                    "size_mb": 144,
                    "sha256": "cde789fgh456ijk123lmn333",
                },
            },
            "windows": {
                "x86_64": {
                    "filename": "shadowcypher-2.5.0-x86_64.exe",
                    "size_mb": 164,
                    "sha256": "opq012rst789uvw456xyz444",
                },
            },
        },
    },
    "2.4.1": {
        "version": "2.4.1",
        "released": "2026-06-28",
        "channel": "stable",
        "security_patches": 1,
        "features": 2,
        "changelog": "Bug fixes and improvements",
        "packages": {
            "linux": {
                "x86_64": {
                    "filename": "shadowcypher-2.4.1-x86_64.tar.gz",
                    "size_mb": 145,
                    "sha256": "aaa111bbb222ccc333ddd444",
                },
            },
        },
    },
    "2.5.0-beta.1": {
        "version": "2.5.0-beta.1",
        "released": "2026-07-01",
        "channel": "beta",
        "security_patches": 2,
        "features": 12,
        "changelog": "Beta release with experimental features",
        "packages": {
            "linux": {
                "x86_64": {
                    "filename": "shadowcypher-2.5.0-beta.1-x86_64.tar.gz",
                    "size_mb": 150,
                    "sha256": "eee555fff666ggg777hhh888",
                },
            },
        },
    },
}

# Version upgrade paths (defines which versions can upgrade to which)
UPGRADE_PATHS = {
    "2.4.1": ["2.5.0"],
    "2.5.0-beta.1": ["2.5.0"],
}

# Create Flask app
app = Flask(APP_NAME)
app.config["JSON_SORT_KEYS"] = False

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(APP_NAME)


def validate_platform(platform: str) -> bool:
    """Validate platform is supported."""
    return platform in SUPPORTED_PLATFORMS


def validate_arch(arch: str) -> bool:
    """Validate architecture is supported."""
    return arch in SUPPORTED_ARCHS


def validate_version(version: str) -> bool:
    """Validate version format."""
    # Simple version format: X.Y.Z or X.Y.Z-suffix
    parts = version.split(".")
    if len(parts) < 2:
        return False
    try:
        int(parts[0])
        int(parts[1].split("-")[0])
        return True
    except ValueError:
        return False


def get_release_info(version: str) -> Optional[Dict]:
    """Get release information for a version."""
    return RELEASES.get(version)


def find_latest_version(channel: str = "stable") -> Optional[str]:
    """Find the latest version for a channel."""
    latest = None
    for version, info in sorted(RELEASES.items(), reverse=True):
        if info.get("channel") == channel:
            latest = version
            break
    return latest


def can_upgrade(current_version: str, target_version: str) -> bool:
    """Check if upgrade is allowed from current to target version."""
    if current_version not in UPGRADE_PATHS:
        return False
    return target_version in UPGRADE_PATHS[current_version]


def get_package_info(
    version: str, platform: str, arch: str
) -> Optional[Dict]:
    """Get package information for a specific version/platform/arch."""
    release = get_release_info(version)
    if not release:
        return None

    try:
        return release["packages"][platform][arch]
    except KeyError:
        return None


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify(
        {
            "status": "healthy",
            "service": APP_NAME,
            "version": APP_VERSION,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


@app.route("/api/versions", methods=["GET"])
def list_versions():
    """List all available versions."""
    return jsonify(
        {
            "versions": list(RELEASES.keys()),
            "count": len(RELEASES),
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


@app.route("/api/updates/check", methods=["GET"])
def check_updates():
    """
    Check for available updates.

    Query parameters:
    - version: Current version (required)
    - platform: linux/macos/windows (required)
    - arch: x86_64/arm64/armv7 (required)
    - channel: stable/beta/nightly (optional, default: stable)
    """
    # Get and validate parameters
    current_version = request.args.get("version", "").strip()
    platform = request.args.get("platform", "").strip()
    arch = request.args.get("arch", "").strip()
    channel = request.args.get("channel", "stable").strip()

    # Validation
    if not current_version or not validate_version(current_version):
        return (
            jsonify({"error": "Invalid version format", "code": "INVALID_VERSION"}),
            400,
        )

    if not platform or not validate_platform(platform):
        return (
            jsonify(
                {"error": "Unsupported platform", "code": "INVALID_PLATFORM"}
            ),
            400,
        )

    if not arch or not validate_arch(arch):
        return (
            jsonify(
                {"error": "Unsupported architecture", "code": "INVALID_ARCH"}
            ),
            400,
        )

    # Log the check
    logger.info(
        f"Update check: {platform}/{arch}, current={current_version}, channel={channel}"
    )

    # Find latest version in channel
    latest = find_latest_version(channel)
    if not latest:
        return (
            jsonify(
                {
                    "error": "No releases available for channel",
                    "code": "NO_RELEASES",
                }
            ),
            404,
        )

    # Check if package exists for this platform/arch
    release = get_release_info(latest)
    if not release:
        return (
            jsonify({"error": "Release not found", "code": "RELEASE_NOT_FOUND"}),
            404,
        )

    package_info = get_package_info(latest, platform, arch)
    if not package_info:
        return (
            jsonify(
                {
                    "error": f"Package not available for {platform}/{arch}",
                    "code": "PACKAGE_NOT_AVAILABLE",
                }
            ),
            404,
        )

    # Check if update is available
    available = latest != current_version
    can_upgrade_to = (
        can_upgrade(current_version, latest) if available else None
    )

    # Build response
    response = {
        "available": available,
        "current_version": current_version,
        "latest_version": latest,
        "released": release.get("released"),
        "channel": channel,
        "size_mb": package_info.get("size_mb"),
        "sha256": package_info.get("sha256"),
        "security_patches": release.get("security_patches", 0),
        "features": release.get("features", 0),
        "changelog": release.get("changelog"),
        "can_upgrade": can_upgrade_to,
    }

    # Add download URLs if update available
    if available:
        filename = package_info.get("filename")
        response["download_url"] = (
            f"/api/updates/download/{latest}/{filename}"
        )
        response["signature_url"] = (
            f"/api/updates/download/{latest}/{filename}.sig"
        )
        response["signature_algorithm"] = "sha256+ecdsa"

    response["timestamp"] = datetime.utcnow().isoformat()

    return jsonify(response)


@app.route("/api/updates/download/<version>/<filename>", methods=["GET"])
def download_package(version, filename):
    """
    Download an update package.

    Parameters:
    - version: Version to download
    - filename: Package filename
    """
    # Validate version format
    if not validate_version(version):
        return jsonify({"error": "Invalid version"}), 400

    # Security: prevent directory traversal
    if ".." in filename or "/" in filename:
        return jsonify({"error": "Invalid filename"}), 400

    # Get release info
    release = get_release_info(version)
    if not release:
        return jsonify({"error": "Version not found"}), 404

    # Find the package in release
    package_found = False
    for platform_packages in release.get("packages", {}).values():
        for arch_package in platform_packages.values():
            if arch_package.get("filename") == filename:
                package_found = True
                break

    if not package_found:
        logger.warning(f"Package not found: {version}/{filename}")
        return jsonify({"error": "Package not found"}), 404

    # Check if file exists on disk
    package_path = UPDATES_DIR / filename
    if not package_path.exists():
        logger.warning(f"Package file missing: {package_path}")
        # In production, would return error or trigger build
        # For now, return 404
        return (
            jsonify(
                {
                    "error": "Package file not available",
                    "code": "PACKAGE_UNAVAILABLE",
                }
            ),
            404,
        )

    logger.info(f"Downloading package: {version}/{filename}")

    try:
        return send_file(
            str(package_path),
            as_attachment=True,
            download_name=filename,
            mimetype="application/gzip",
        )
    except Exception as e:
        logger.error(f"Error sending file: {e}")
        return jsonify({"error": "Failed to download package"}), 500


@app.route("/api/updates/info/<version>", methods=["GET"])
def get_update_info(version):
    """Get detailed information about a specific version."""
    if not validate_version(version):
        return jsonify({"error": "Invalid version"}), 400

    release = get_release_info(version)
    if not release:
        return jsonify({"error": "Version not found"}), 404

    logger.info(f"Fetching info for version: {version}")

    response = {
        "version": release.get("version"),
        "released": release.get("released"),
        "channel": release.get("channel"),
        "security_patches": release.get("security_patches", 0),
        "features": release.get("features", 0),
        "changelog": release.get("changelog"),
        "packages": {},
    }

    # List available packages
    for platform, arch_packages in release.get("packages", {}).items():
        response["packages"][platform] = {}
        for arch, package in arch_packages.items():
            response["packages"][platform][arch] = {
                "filename": package.get("filename"),
                "size_mb": package.get("size_mb"),
                "sha256": package.get("sha256"),
            }

    response["timestamp"] = datetime.utcnow().isoformat()
    return jsonify(response)


@app.route("/api/updates/rollback/<current_version>", methods=["GET"])
def get_rollback_options(current_version):
    """Get available rollback versions for a current version."""
    if not validate_version(current_version):
        return jsonify({"error": "Invalid version"}), 400

    logger.info(f"Fetching rollback options for: {current_version}")

    # Find versions that current_version can roll back to
    rollback_targets = []
    for version, info in sorted(
        RELEASES.items(),
        key=lambda x: x[1].get("released", ""),
        reverse=True,
    ):
        if version != current_version:
            # Could add more sophisticated rollback logic here
            rollback_targets.append(
                {
                    "version": version,
                    "released": info.get("released"),
                    "channel": info.get("channel"),
                    "changelog": info.get("changelog"),
                }
            )

    return jsonify(
        {
            "current_version": current_version,
            "rollback_targets": rollback_targets[:5],  # Last 5 versions
            "count": len(rollback_targets),
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


@app.route("/api/stats/report", methods=["POST"])
def report_stats():
    """
    Report update statistics (anonymized).

    Expected JSON:
    {
        "current_version": "2.4.1",
        "update_version": "2.5.0",
        "platform": "linux",
        "arch": "x86_64",
        "status": "success",
        "duration_seconds": 45
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Log anonymized stats
    logger.info(
        f"Update stats: {data.get('current_version')} -> "
        f"{data.get('update_version')} on "
        f"{data.get('platform')}/{data.get('arch')}: "
        f"{data.get('status')} ({data.get('duration_seconds')}s)"
    )

    return jsonify({"status": "accepted"}), 202


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return (
        jsonify(
            {
                "error": "Endpoint not found",
                "code": "NOT_FOUND",
                "path": request.path,
            }
        ),
        404,
    )


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {error}")
    return (
        jsonify(
            {"error": "Internal server error", "code": "INTERNAL_ERROR"}
        ),
        500,
    )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="ShadowCypher Update Server"
    )
    parser.add_argument(
        "--host", default=HOST, help=f"Server host (default: {HOST})"
    )
    parser.add_argument(
        "--port", type=int, default=PORT, help=f"Server port (default: {PORT})"
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug mode"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=UPDATES_DIR,
        help="Directory containing update packages",
    )

    args = parser.parse_args()

    logger.info(f"Starting {APP_NAME} v{APP_VERSION}")
    logger.info(f"Listening on {args.host}:{args.port}")
    logger.info(f"Debug mode: {args.debug}")
    logger.info(f"Updates directory: {args.data_dir}")

    app.run(
        host=args.host,
        port=args.port,
        debug=args.debug,
        use_reloader=False,
    )


if __name__ == "__main__":
    main()
