# ShadowOS Kernel Module Hardening

## Blacklisted Modules

The following modules are blacklisted to reduce attack surface:

**Networking:**
- DCCP (Datagram Congestion Control Protocol)
- SCTP (Stream Control Transmission Protocol)
- RDS (Reliable Datagram Sockets)
- TIPC (TIPC Messaging Protocol)

**Filesystems:**
- CRAMFS, FreeVXFS (rarely used)
- JFFS2, HFS, HFSPLUS, UDF

**Debugging:**
- kgdboc, kgdbts (kernel debugging)

## Viewing Loaded Modules

```bash
lsmod | grep -v "^Module"
```

## Loading a Blacklisted Module (if needed)

```bash
sudo modprobe --force dccp
```

## Custom Module Policies

Edit `/etc/modprobe.d/` files to customize module loading.
