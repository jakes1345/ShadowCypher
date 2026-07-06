# Certified Devices Registry

## Overview

The ShadowCypher Certified Devices Registry maintains a curated list of hardware devices that meet enterprise security standards and have been verified for compatibility with ShadowOS and ShadowCypher security applications.

Devices are categorized by certification level, indicating the degree of security compliance, feature support, and deployment readiness.

---

## Certification Levels

### Gold Certified (100% Compliance)

Gold-certified devices meet all ShadowCypher security standards, support the full feature set, and are recommended for sensitive and critical deployments.

**Requirements:**
- FIPS 140-2 compliant components (or equivalent)
- All modern security features enabled (SecureBoot, TPM 2.0, ECC memory)
- Active firmware/OS security updates
- 2-year certification validity
- Full compliance with NIST and CIS standards

**Gold Certified Devices:**

#### Enterprise Workstations
- **Intel Xeon W9-3595X** (60-core, 3.0GHz)
  - RAM: Up to 192GB DDR5 ECC
  - GPU: NVIDIA RTX 6000 Ada (48GB VRAM)
  - Storage: 2TB NVMe SSD
  - Certification: 2025-06-01
  - Use Case: High-performance security operations, threat analysis, encrypted research

- **Dell Precision 7680**
  - CPU: Intel Xeon W9-3495X (60-core)
  - RAM: Up to 192GB DDR5 ECC
  - GPU: NVIDIA RTX 6000 Ada (48GB)
  - Storage: 2TB NVMe SSD
  - Certification: 2025-06-10
  - Use Case: Enterprise security analysis, cryptographic operations

#### Laptops/Portables
- **Apple MacBook Pro 16-inch (M4 Max)**
  - CPU: Apple M4 Max (12-core)
  - RAM: Up to 36GB unified memory
  - GPU: Apple GPU (10-core)
  - Storage: 1TB SSD
  - Certification: 2025-05-15
  - Use Case: macOS-based security operations, portable classified work

- **Lenovo ThinkPad X1 Extreme Gen 7**
  - CPU: Intel Core Ultra 9 285H (14-core)
  - RAM: Up to 32GB LPDDR5X
  - GPU: NVIDIA RTX 6050 Ada (12GB)
  - Storage: 1TB NVMe SSD
  - Certification: 2025-05-01
  - Use Case: Mobile enterprise security operations, field assessments

#### Servers
- **HPE ProLiant DL380 Gen11**
  - CPU: Intel Xeon Platinum 8592+ (60-core)
  - RAM: Up to 2TB DDR5 ECC
  - Storage: 12x 1.92TB SAS SSD
  - GPU: Optional NVIDIA A100
  - Certification: 2025-05-20
  - Use Case: Enterprise security operations center, centralized threat management

- **Supermicro SYS-1U X12 LGA1700**
  - CPU: Intel Xeon Platinum 8592 (60-core)
  - RAM: Up to 2TB DDR5 ECC
  - Storage: 12x 1.92TB SAS SSD
  - GPU: Optional NVIDIA A100
  - Certification: 2025-06-05
  - Use Case: Data center deployments, high-performance security analytics

---

### Silver Certified (95%+ Compliance)

Silver-certified devices meet core security standards and support the majority of modern security features. Suitable for standard operations with minor feature limitations.

**Requirements:**
- Core security features enabled (TPM 2.0, SecureBoot)
- Current firmware/OS support with regular updates
- 18-month certification validity
- Compliance with most NIST and CIS controls

**Silver Certified Devices:**

#### Laptops/Ultrabooks
- **ASUS VivoBook 15 Ultra**
  - CPU: Intel Core Ultra 7 165U (10-core)
  - RAM: Up to 16GB LPDDR5X
  - GPU: Intel Arc GPU
  - Storage: 512GB NVMe SSD
  - Certification: 2025-04-15
  - Issues: GPU driver support limited on Linux, biometric firmware update needed
  - Use Case: Standard user operations, light security analysis

- **HP Envy 16 Plus**
  - CPU: Intel Core Ultra 9 285H
  - RAM: Up to 32GB LPDDR5X
  - GPU: NVIDIA RTX 4060 (8GB)
  - Storage: 1TB NVMe SSD
  - Certification: 2025-04-01
  - Issues: Audio codec firmware outdated
  - Use Case: General purpose security work, presentation ready

- **Framework Laptop 16 (13th Gen Intel)**
  - CPU: Intel Core i7-13700H (16-core)
  - RAM: Up to 64GB DDR5
  - GPU: Intel Arc A770M (8GB)
  - Storage: 2TB NVMe SSD
  - Certification: 2025-04-10
  - Issues: EC firmware updates needed for full security
  - Use Case: Modular, reputable, open-source friendly deployments

#### Edge Computing & IoT
- **Raspberry Pi 5 (8GB)**
  - CPU: Broadcom BCM2712 (4-core ARM, 2.4GHz)
  - RAM: 8GB LPDDR5
  - Storage: External microSD/NVMe
  - Certification: 2025-03-20
  - Issues: Limited cryptographic acceleration, external storage dependency
  - Use Case: Security appliances, edge threat detection, monitoring nodes

- **NVIDIA Jetson AGX Orin**
  - CPU: ARM Cortex-A78AE (12-core)
  - RAM: 32GB LPDDR5X
  - GPU: NVIDIA GPU (504 CUDA cores)
  - Storage: 1TB NVMe SSD
  - Certification: 2025-05-01
  - Issues: CUDA driver updates critical for security
  - Use Case: AI/ML-based threat detection, edge analytics, security automation

---

### Community Verified

Community-verified devices have been tested and validated by ShadowCypher community members. These devices offer basic security support suitable for educational and non-critical deployments.

**Requirements:**
- Basic security features present
- Community support for driver/firmware updates
- 12-month verification validity
- Limited NIST/CIS control coverage

**Community Verified Devices:**

#### Educational & Development Boards
- **Banana Pi M7**
  - CPU: MediaTek Dimensity 7300 (8-core ARM)
  - RAM: 8GB LPDDR5
  - GPU: Mali-G77
  - Storage: 128GB eMMC + microSD
  - Verified: 2025-03-10
  - Issues: Limited security updates, minimal hardware security features, community driver quality varies
  - Use Case: Educational purposes, development environments, learning platforms

- **BeagleBone Black**
  - CPU: AM335x (1GHz ARM Cortex-A8)
  - RAM: 512MB DDR3
  - Storage: 4GB eMMC + microSD
  - Verified: 2025-01-20
  - Issues: Minimal cryptographic performance, limited RAM, end-of-life consideration
  - Use Case: Legacy systems, educational projects, hobbyist work

#### Legacy Systems
- **Google Pixelbook Go**
  - CPU: Intel Core m3-8100Y (2-core)
  - RAM: 8GB LPDDR3
  - Storage: 128GB SSD
  - Verified: 2025-02-15
  - Issues: Not recommended for Linux deployments, deprecated hardware
  - Use Case: ChromeOS environments only, legacy support
  - Status: Community maintained, not recommended for new deployments

---

## Device Specifications Summary

| Manufacturer | Model | Certification | CPU | RAM | GPU | Storage |
|---|---|---|---|---|---|---|
| Intel | Xeon W9-3595X | Gold | 60-core, 3.0GHz | 192GB DDR5 | RTX 6000 Ada | 2TB NVMe |
| Apple | MacBook Pro 16" M4 Max | Gold | 12-core | 36GB Unified | 10-core GPU | 1TB SSD |
| Lenovo | ThinkPad X1 Extreme Gen 7 | Gold | 14-core Ultra 9 | 32GB LPDDR5X | RTX 6050 Ada | 1TB NVMe |
| Dell | Precision 7680 | Gold | 60-core Xeon | 192GB DDR5 ECC | RTX 6000 Ada | 2TB NVMe |
| HPE | ProLiant DL380 Gen11 | Gold | 60-core Platinum | 2TB DDR5 ECC | Optional A100 | 12x 1.92TB |
| Supermicro | SYS-1U X12 LGA1700 | Gold | 60-core Platinum | 2TB DDR5 ECC | Optional A100 | 12x 1.92TB |
| ASUS | VivoBook 15 Ultra | Silver | 10-core Ultra 7 | 16GB LPDDR5X | Intel Arc | 512GB NVMe |
| HP | Envy 16 Plus | Silver | 14-core Ultra 9 | 32GB LPDDR5X | RTX 4060 | 1TB NVMe |
| Framework | Laptop 16 (13th Gen) | Silver | 16-core i7-13700H | 64GB DDR5 | Arc A770M | 2TB NVMe |
| Raspberry Pi | Pi 5 (8GB) | Silver | 4-core ARM | 8GB LPDDR5 | VideoCore VII | External |
| NVIDIA | Jetson AGX Orin | Silver | 12-core ARM | 32GB LPDDR5X | NVIDIA GPU | 1TB NVMe |
| Banana Pi | M7 | Community | 8-core ARM | 8GB LPDDR5 | Mali-G77 | 128GB eMMC |
| BeagleBone | Black | Community | 1GHz Cortex-A8 | 512MB DDR3 | None | 4GB eMMC |
| Google | Pixelbook Go | Community | 2-core m3-8100Y | 8GB LPDDR3 | UHD 615 | 128GB SSD |

---

## Deployment Recommendations

### For Sensitive Operations (Intelligence, Classified)
- **Recommend**: Gold-certified workstations and servers
- **Example Stack**: Intel Xeon W9 or Dell Precision 7680 + HPE ProLiant DL380 Gen11

### For Standard Enterprise Security
- **Recommend**: Silver-certified devices with Enterprise SKUs
- **Example Stack**: Lenovo ThinkPad X1 Extreme + HPE ProLiant DL380 Gen11

### For Field Operations & Mobility
- **Recommend**: Gold-certified laptops (MacBook Pro, ThinkPad X1)
- **Example Stack**: Apple MacBook Pro M4 Max or Lenovo ThinkPad X1 Extreme Gen 7

### For Edge Security & IoT
- **Recommend**: Silver-certified edge devices
- **Example Stack**: Raspberry Pi 5 or NVIDIA Jetson AGX Orin for threat detection

### For Development & Testing
- **Recommend**: Community-verified boards (non-production)
- **Example Stack**: Raspberry Pi 5 or Banana Pi M7 for development

---

## Compatibility Matrix

### Operating System Support
- **Gold**: Linux (6.8+), Windows Server 2022+, macOS 14.5+
- **Silver**: Linux (6.6+), Windows 10/11, macOS 12+
- **Community**: Linux (6.1+), ChromeOS, limited Windows support

### Security Features
| Feature | Gold | Silver | Community |
|---|---|---|---|
| TPM 2.0 | ✓ | ✓ | Limited |
| Secure Boot | ✓ | ✓ | Limited |
| ECC Memory | ✓ | Optional | No |
| Hardware Crypto | ✓ | Partial | No |
| FIPS 140-2 | ✓ | No | No |

---

## Certification Process

### Requirements for Gold Certification
1. Hardware security assessment and validation
2. Firmware/BIOS security audit
3. OS compatibility testing across supported distributions
4. Cryptographic performance benchmarking
5. Physical security feature validation (TPM, SecureBoot)
6. Annual recertification required

### Requirements for Silver Certification
1. Hardware specification review
2. OS compatibility verification
3. Security feature checking
4. 18-month recertification required

### Community Verification
1. Community member testing and submission
2. Basic compatibility documentation
3. Known issues tracking
4. 12-month community update cycle

---

## Adding New Devices

To propose a new device for certification:

1. **Submit Device Information**
   - Manufacturer, model, variant
   - Complete technical specifications
   - Security features present

2. **Test Requirements**
   - ShadowOS compatibility testing
   - Security feature validation
   - Performance benchmarking

3. **Review Process**
   - Security team assessment
   - Compliance evaluation
   - Certification level assignment

4. **Registry Update**
   - Device added to `.github/certified-devices.json`
   - Documentation updated
   - Verification tracking initiated

---

## Device Registry Database

The authoritative device registry is maintained in `.github/certified-devices.json` with machine-readable specifications for each certified device, including:

- Unique device identifier
- Manufacturer and model information
- CPU, RAM, GPU, storage specifications
- Certification level and date
- Kernel version requirements
- Known issues and workarounds
- Verification history and audit trail

Use the `shadowos/device-registry.py` tool to query and manage the registry programmatically.

---

## Resources

- **Registry Manager**: `shadowos/device-registry.py`
- **Registry Database**: `.github/certified-devices.json`
- **Compliance Standards**: NIST Cybersecurity Framework, CIS Controls, FIPS 140-2
- **Hardware Security**: TPM 2.0 Specification, Secure Boot Specification

---

**Last Updated**: 2025-06-10
**Maintained By**: ShadowCypher Security Team
