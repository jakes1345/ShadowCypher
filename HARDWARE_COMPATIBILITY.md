# Hardware Compatibility Guide

## Overview

This document outlines the hardware requirements and compatibility matrix for ShadowCypher across supported architectures and platforms. ShadowCypher is designed to run on modern x86_64 and ARM64 systems with reasonable resource constraints.

## Supported Architectures

### x86_64 (Intel/AMD)
- **Status**: Primary support tier
- **Compatibility**: Full feature support on all modern Intel and AMD processors
- **Minimum CPU**: Intel Core i5 (6th generation or newer) / AMD Ryzen 5 2600 or equivalent
- **Tested Processors**:
  - Intel Core i7-13700H and newer
  - Intel Core Ultra (Meteor Lake) and newer
  - AMD Ryzen 5000 series and newer
  - AWS Graviton2 and compatible equivalents

### ARM64 (Apple Silicon, ARM Server)
- **Status**: Primary support tier
- **Compatibility**: Full feature support on Apple Silicon and ARMv8.0+ platforms
- **Minimum CPU**: Apple M1 or equivalent ARM64 processor (ARMv8.0+)
- **Tested Processors**:
  - Apple M1, M2, M3 (all variants)
  - Apple M4 and newer
  - AWS Graviton2/3
  - Broadcom BCM2712 (Raspberry Pi 5)

### ARM32/ARMv7
- **Status**: Unsupported
- **Reason**: Limited by 32-bit address space and older cryptographic library constraints
- **Workaround**: Consider ARM64 alternatives

## Minimum Hardware Specifications

### For Desktop/Laptop Development

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU Cores | 2 cores | 4+ cores |
| RAM | 8 GB | 16 GB+ |
| Storage | 10 GB free | 50 GB+ free SSD |
| GPU | Integrated graphics | Dedicated GPU (optional) |

### For Server/Cloud Deployment

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| vCPU | 2 vCPU | 4+ vCPU |
| RAM | 4 GB | 8 GB+ |
| Storage | 20 GB | 100 GB+ SSD |
| Network | 1 Mbps | 10 Mbps+ |

### For Lightweight/Edge Deployment

| Component | Minimum | Status |
|-----------|---------|--------|
| CPU Cores | 1 core | Supported but degraded |
| RAM | 512 MB | Functional, limited workloads |
| Storage | 5 GB | Minimal config only |

## Operating System Support

### Primary Support

| OS | Minimum Version | Notes |
|----|-----------------|-------|
| Ubuntu | 20.04 LTS | Recommended: 22.04 LTS or 24.04 LTS |
| Fedora | 37 | Recommended: Latest stable |
| Debian | 11 (Bullseye) | Stable releases supported |
| macOS | 11 (Big Sur) | Recommended: 12+ for best performance |
| Windows | Windows 10 21H2 | Requires WSL2 for Linux workloads |

### Secondary Support (Community Verified)

- Alpine Linux 3.16+
- RHEL/CentOS 8+
- Rocky Linux 8+
- openSUSE Leap 15+
- Arch Linux (rolling)

## Tested Hardware Configurations

Refer to `hardware-db.json` for a comprehensive list of tested and verified hardware configurations including:
- 15 certified hardware profiles
- Mix of laptops, desktops, servers, and cloud VMs
- Performance classifications (supported/degraded/unsupported)
- Specific notes for each configuration

## Virtualization Support

### Supported Hypervisors

| Platform | Support | Notes |
|----------|---------|-------|
| KVM/QEMU | Full | Linux host. Best performance. |
| VirtualBox | Full | All platforms. Good compatibility. |
| Hyper-V | Full | Windows host. Enable nested virtualization if available. |
| VMware ESXi | Full | Enterprise. Excellent performance. |
| Proxmox VE | Full | Open-source. KVM-based. Good for labs. |
| Docker | Full | Container support. Lightweight deployment. |

### Important Virtualization Notes

- **Nested Virtualization**: If running nested VM (VM inside VM), performance may degrade significantly
- **CPU Pinning**: Recommended for production deployments to avoid context switching
- **Memory Overcommit**: Not recommended; allocate dedicated RAM
- **Storage Backend**: SSD-backed storage strongly recommended over spinning disks

## Performance Recommendations

### CPU-Intensive Workloads
- Minimum: 4 cores (8 with hyperthreading)
- Recommended: 8+ cores
- **Avoid**: Single-core or dual-core systems for heavy monitoring

### Memory-Intensive Workloads
- Baseline: 16 GB RAM
- Heavy monitoring: 32 GB+ recommended
- Disk caching benefits from additional RAM

### Storage Performance
- **SSD Recommended**: NVMe M.2 drives preferred for database operations
- **HDD Performance**: Acceptable for archival/backup but not recommended for live workloads
- **Storage Encryption**: Can add 5-15% overhead; ensure sufficient CPU headroom

### Network Performance
- **Minimum**: 1 Mbps for basic operations
- **Recommended**: 10 Mbps+ for real-time threat feed ingestion
- **Latency**: Keep to <50ms for responsive UI (desktop)

## Known Hardware Issues

### Graphics/GPU Issues

| Issue | Hardware | Status | Workaround |
|-------|----------|--------|-----------|
| GPU acceleration unavailable | Raspberry Pi 4/5 | Known limitation | Use CPU-only mode (default) |
| Intel Arc stability | Some Arc A770+ | Occasional | Update drivers to latest |
| AMD iGPU underclocking | Some Ryzen APUs | Temporary | Reboot or disable power management |

### CPU Issues

| Issue | Hardware | Status | Workaround |
|-------|----------|--------|-----------|
| Thermal throttling | Older MacBook Pros | Transient | Improve ventilation, reduce load |
| ARM NEON intrinsics | Older ARM64 devices | Rare | Fallback code path active |
| AVX-512 incompatibility | Some Intel 12th Gen | Edge case | CPU detection disables feature |

### Storage Issues

| Issue | Hardware | Status | Workaround |
|-------|----------|--------|-----------|
| SSD wear | Excessive write loads | Degradation | Monitor SMART health, plan replacement |
| File system limits | Very old ext2/ext3 | Incompatible | Use ext4 or newer |
| Case sensitivity | macOS/Windows | Data loss risk | Ensure consistent naming conventions |

## Performance Baseline Metrics

Measured on reference hardware (MacBook Pro 16" M1 Max, 32GB RAM, 512GB SSD):

- **Boot time**: ~3-5 seconds
- **Database query**: <100ms (p99)
- **Real-time scanning**: <2% CPU overhead
- **Memory footprint**: 200-400 MB at rest
- **Concurrent connections**: 100+ simultaneous clients

Scales linearly with architecture. ARM64 and modern x86_64 perform comparably.

## Unsupported Hardware

### Architectures
- **32-bit x86** (i386, i686): No support
- **PowerPC**: No support
- **MIPS**: No support

### Devices
- **Legacy phones** (pre-2015 Android): No support
- **IoT single-core devices** (<512 MB RAM): Unsupported
- **Very old Apple hardware** (pre-2008 Intel Macs): Unsupported

## Upgrading Hardware

### When to Upgrade

Consider upgrading if you experience:
- Consistent CPU load >80% during normal operation
- Less than 1 GB free RAM during runtime
- SSD nearly full (>90% capacity)
- Persistent thermal throttling
- Storage SMART warnings

### Cost-Effective Upgrades

1. **RAM**: Most impactful upgrade. Aim for 16-32 GB.
2. **SSD**: Replace aging hard drives or small SSDs.
3. **Network**: Upgrade network interface if bandwidth-limited.
4. **CPU**: Least impactful for most workloads; consider only if CPU-bound.

## Getting Hardware Reports

Use the included `hardware-report.sh` script to generate a detailed hardware compatibility report:

```bash
./hardware-report.sh
./hardware-report.sh --json
./hardware-report.sh --check-db
```

Reports include:
- Detected hardware specifications
- Compatibility assessment
- Performance recommendations
- Optimization suggestions

## Requesting Hardware Support

If your hardware is not listed in `hardware-db.json` and you need support:

1. Run `hardware-report.sh` to generate a full report
2. Open an issue with the JSON output
3. Include your OS, driver versions, and any performance issues
4. Expected response: Community validation or engineering assessment

## Future Hardware Roadmap

### Planned Support

- **Android 13+**: Mobile app in development
- **iOS 16+**: Mobile companion app (roadmap)
- **Raspberry Pi 4/5**: Enhanced ARM32/ARM64 optimization
- **Apple Vision Pro**: Spatial computing support (future)

### Hardware Technology Watch

- ARM SVE (Scalable Vector Extension): Monitoring for future cryptographic acceleration
- Intel AVX-512 Sapphire Rapids: Evaluating for performance improvements
- AMD Zen 5+: Continuous testing and optimization

## Support and Troubleshooting

### Check Compatibility
```bash
# Quick hardware check
./hardware-report.sh --quick

# Detailed assessment
./hardware-report.sh --full

# Check against database
./hardware-report.sh --check-db
```

### Common Issues

**Q: My hardware isn't in the database. Is it supported?**
A: Run `hardware-report.sh` to verify. Most modern systems (2015+) will work fine.

**Q: Should I upgrade my hardware?**
A: Check if you're hitting resource limits. If CPU/RAM utilization is consistently <70%, upgrade not needed.

**Q: Can I run this on older hardware?**
A: Possibly. Degraded mode is available for older systems (2010-2014). Not recommended for production.

**Q: Is virtualization supported?**
A: Yes. KVM, VirtualBox, Hyper-V, and Docker all fully supported.

---

**Last Updated**: 2026-07-05
**Version**: 1.0.0
**Maintainer**: ShadowCypher Security Team
