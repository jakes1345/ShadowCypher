"""Input sanitization — prevent command injection in shell commands."""

import re
import shlex


def quote(value: str) -> str:
    """Shell-quote a value for safe interpolation into commands."""
    return shlex.quote(value)


def validate_target(target: str) -> bool:
    """Validate a target is a reasonable IP/hostname/CIDR/URL."""
    target = target.strip()
    if not target:
        return False

    # Strip protocol prefix for URL targets
    bare = re.sub(r'^https?://', '', target).split('/')[0].split(':')[0]

    # IPv4 or CIDR
    if re.match(r'^(\d{1,3}\.){3}\d{1,3}(/\d{1,2})?$', bare):
        octets = bare.split('/')[0].split('.')
        return all(0 <= int(o) <= 255 for o in octets)

    # Hostname / domain
    if re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9\-\.]*[a-zA-Z0-9])?$', bare):
        return len(bare) <= 253

    return False


def validate_ip(ip: str) -> bool:
    """Validate a single IPv4 address."""
    if not re.match(r'^(\d{1,3}\.){3}\d{1,3}$', ip.strip()):
        return False
    return all(0 <= int(o) <= 255 for o in ip.strip().split('.'))


def validate_mac(mac: str) -> bool:
    """Validate a MAC address."""
    return bool(re.match(r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$', mac.strip()))


def validate_interface(iface: str) -> bool:
    """Validate a network interface name (alphanumeric + hyphens)."""
    return bool(re.match(r'^[a-zA-Z0-9_\-\.]+$', iface.strip()))


def validate_port(port) -> bool:
    """Validate a port number."""
    try:
        p = int(port)
        return 1 <= p <= 65535
    except (ValueError, TypeError):
        return False


def validate_ports(ports: str) -> bool:
    """Validate a port spec like '22,80,443' or '1-1024' or '22,80,100-200'."""
    if not ports.strip():
        return False
    for part in ports.strip().split(','):
        part = part.strip()
        if '-' in part:
            pieces = part.split('-', 1)
            if len(pieces) != 2:
                return False
            if not (pieces[0].isdigit() and pieces[1].isdigit()):
                return False
            if not (1 <= int(pieces[0]) <= 65535 and 1 <= int(pieces[1]) <= 65535):
                return False
        elif part.isdigit():
            if not (1 <= int(part) <= 65535):
                return False
        else:
            return False
    return True


def validate_filepath(path: str) -> bool:
    """Validate a file path doesn't contain shell metacharacters."""
    # Block obvious injection attempts
    dangerous = ['$(', '`', '|', ';', '&&', '||', '>', '<', '\n', '\r']
    for d in dangerous:
        if d in path:
            return False
    return bool(path.strip())


def sanitize_bpf_filter(expr: str) -> str:
    """Basic sanitization of BPF filter expressions."""
    # BPF filters should only contain alphanumeric, spaces, dots, colons, parens, and operators
    if re.match(r'^[a-zA-Z0-9\s\.\:\(\)\/\-\!\=\<\>\&\|]+$', expr.strip()):
        return expr.strip()
    return ""
