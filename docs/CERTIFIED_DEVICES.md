# Certified Devices Registry

## Overview

The Certified Devices Registry is a system for tracking, verifying, and managing hardware devices that meet ShadowCypher security and compliance standards. This registry enables device identification, certification validation, and compliance checking across the ShadowCypher ecosystem.

## Registry Schema

### Device Record Structure

Each certified device in the registry contains the following fields:

```json
{
  "id": "string",                    // Unique device identifier (format: VENDOR-MODEL-VARIANT)
  "manufacturer": "string",          // Device manufacturer/vendor name
  "model": "string",                 // Device model name
  "variant": "string",               // Device variant (e.g., revision, region)
  "specifications": {
    "processor": "string",           // CPU/processor model
    "memory_gb": "number",           // RAM in gigabytes
    "storage_type": "string",        // Storage type (SSD, NVMe, etc.)
    "storage_capacity_gb": "number", // Storage capacity in gigabytes
    "form_factor": "string",         // Device form factor (phone, tablet, laptop, etc.)
    "os_platforms": ["string"]       // Supported operating systems
  },
  "certification": {
    "level": "string",               // Certification level (gold, silver, bronze)
    "issued_date": "string",         // ISO 8601 date format
    "expiration_date": "string",     // ISO 8601 date format
    "compliance_standards": ["string"], // Standards met (e.g., NIST, CIS, OWASP)
    "security_patches_required": boolean, // Whether latest security patches are required
    "biometric_support": boolean,    // Hardware supports biometric authentication
    "encrypted_storage": boolean,    // Hardware supports encrypted storage
    "secure_boot": boolean           // Hardware supports secure boot
  },
  "audit_trail": {
    "last_verified": "string",       // ISO 8601 timestamp of last verification
    "verification_count": "number",  // Total number of verifications
    "issues_found": "number"         // Number of compliance issues discovered
  }
}
```

## Certification Levels

### Gold (Highest)
- Meets all security standards and compliance requirements
- All modern security features enabled
- Latest firmware/OS support available
- 2-year certification validity
- Recommended for sensitive operations

### Silver (Intermediate)
- Meets core security standards
- Majority of modern security features available
- Current firmware/OS support
- 18-month certification validity
- Suitable for standard operations

### Bronze (Basic)
- Meets minimum security requirements
- Limited modern security features
- Basic firmware/OS support available
- 12-month certification validity
- For legacy or resource-constrained environments

## Lookup Procedures

### By Device ID
```bash
device-checker.sh --lookup-id VENDOR-MODEL-VARIANT
```

Returns device certification status and specifications.

### By Manufacturer
```bash
device-checker.sh --lookup-manufacturer "Apple"
```

Returns all certified devices from specified manufacturer.

### By Model Pattern
```bash
device-checker.sh --lookup-model "iPhone 15*"
```

Returns devices matching model pattern (supports wildcards).

### Compliance Check
```bash
device-checker.sh --check-compliance DEVICE-ID
```

Validates device certification and compliance status.

## Certification Tracking

### Verification Process

1. **Device Identification**: Extract device model and specifications
2. **Registry Lookup**: Query certified devices registry
3. **Status Validation**: Check certification expiration and compliance
4. **Audit Log**: Record verification attempt with timestamp
5. **Report Generation**: Output compliance status and recommendations

### Tracking Metadata

- `last_verified`: Timestamp of most recent verification
- `verification_count`: Total number of successful verifications
- `issues_found`: Count of compliance violations discovered
- `expiration_date`: When certification validity expires
- `compliance_standards`: Which standards the device meets

### Certification Renewal

Certifications are valid until the expiration date. Renewal is required:
- Upon expiration date
- After major OS/firmware updates
- When security standards change
- During regulatory audit cycles

## Registry Maintenance

### Adding Devices

To add a new certified device:

1. Gather device specifications and security features
2. Determine appropriate certification level
3. Calculate expiration date (based on certification level)
4. Populate device record with all required fields
5. Add to device-registry.json
6. Update audit trail with verification date

### Updating Certifications

To update an existing device certification:

1. Identify the device by ID
2. Update relevant fields (primarily certification dates and standards)
3. Increment verification_count
4. Set last_verified to current timestamp
5. Commit changes to registry

### Decommissioning Devices

Devices should not be removed but marked as inactive:

1. Set expiration_date to current date
2. Add note in compliance_standards: "DEPRECATED"
3. Keep audit trail for historical reference
4. Update device-checker.sh to flag as unsupported

## Security Considerations

- Registry contains public hardware information only
- No sensitive credentials stored in registry
- Device checker validates against timestamped snapshots
- Audit trail provides tamper-evidence trail
- Regular registry reviews recommended

## Integration Points

The registry integrates with:
- Guardian module audit workflows
- Device compliance reporting
- Hardware security assessments
- Incident response playbooks
- Security baseline validation

## File Locations

- **Documentation**: `/home/jack/ShadowCypher/docs/CERTIFIED_DEVICES.md`
- **Registry Data**: `/home/jack/ShadowCypher/data/security/device-registry.json`
- **Checker Tool**: `/home/jack/ShadowCypher/bin/device-checker.sh`

## References

- CIS Controls: Device and Application Security
- NIST Cybersecurity Framework: Asset Management
- OWASP: Secure Hardware Development
