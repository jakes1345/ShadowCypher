# ShadowScript — Language Reference

ShadowScript is ShadowCypher's native tactical scripting language. Write missions,
automate security workflows, chain AI queries, and orchestrate Shadow Nodes — all in
one clean, purpose-built syntax.

---

## Variables

```shadow
VAR target = "192.168.1.1"
VAR port   = "80"
SET name   = "home-lab"   # SET is an alias for VAR
```

Reference a variable anywhere with `$name`:

```shadow
!echo("Target is $target on port $port")
```

---

## Target

Lock the mission kernel onto an IP or domain:

```shadow
TARGET("192.168.1.1")
TARGET($target)
```

---

## Network Scan

```shadow
SCAN(1-1000)          # scan ports 1–1000 on current target
SCAN(22,80,443,8080)  # specific ports
```

---

## Modules — STRIKE

Run any ShadowCypher module against the current target:

```shadow
STRIKE(recon,    quick_scan)
STRIKE(network,  arp_scan)
STRIKE(web,      ffuf_dir_fuzz)
STRIKE(vuln,     nuclei_scan)
STRIKE(osint,    whois_lookup)
STRIKE(forensics, hash_file)
STRIKE(wireless, scan_networks)
```

Available modules: `recon`, `network`, `wireless`, `exploit`, `poc`, `privesc`,
`c2`, `payload`, `craft`, `web`, `osint`, `credentials`, `secrets`, `forensics`, `vuln`

---

## AI Integration

Query the local AI brain inline:

```shadow
AI("What services typically run on port 8080?")
AI("Summarise vulnerabilities found on $target")
```

Result is stored in `$AI_RESULT` and printed to the terminal.

---

## System Commands

```shadow
!sys("whoami")
!sys("nmap -sV $target")
!sys("ls /etc")
```

Output goes to `$LAST`. Exit code is in `$EXIT_CODE`.

```shadow
!pipe("ip addr show")   # output → $PIPE_OUT
```

---

## Module Direct Call

Call a module method with explicit arguments:

```shadow
!module(recon, quick_scan, 10.0.0.1)
!module(web, ffuf_dir_fuzz, http://10.0.0.1)
```

---

## Print and Sleep

```shadow
!echo("Scan complete — result: $LAST")
!sleep(2)
```

---

## Control Flow

### IF / ELSE

```shadow
IF $EXIT_CODE == 0 {
    !echo("command succeeded")
}

IF $AI_RESULT != "" {
    !echo("AI responded: $AI_RESULT")
} ELSE {
    !echo("AI offline or no response")
}
```

Supported operators: `==`, `!=`, `>`, `<`, `>=`, `<=`
Truthy check (single var): `IF $LAST { ... }`

### FOR loop

```shadow
FOR ip IN 192.168.1.1 192.168.1.2 192.168.1.3 {
    TARGET($ip)
    SCAN(22,80,443)
    !echo("Scanned $ip — result: $LAST")
}
```

### WHILE loop

```shadow
VAR counter = "0"
WHILE $counter < 5 {
    !echo("Pass $counter")
    !sys("echo done")
    VAR counter = "999"   # update to exit (full arithmetic coming)
}
```

### BREAK / RETURN

```shadow
FOR host IN 10.0.0.1 10.0.0.2 {
    IF $host == "10.0.0.2" {
        BREAK
    }
    STRIKE(recon, quick_scan)
}

RETURN "mission complete"   # sets $RESULT
```

---

## Shadow Nodes — SWARM

Broadcast a command to all linked Shadow Node agents:

```shadow
SWARM()
SWARM("id")    # run 'id' on all nodes
```

Nodes must be registered via the Shadow Nodes tab or the native agent binary.

---

## Load Another Script

```shadow
LOAD("recon_phase.shadow")     # relative path (missions/ dir)
LOAD("/opt/scripts/foo.shadow") # absolute path
```

---

## MAP / FILTER

Process lines from `$LAST`:

```shadow
!sys("cat /etc/hosts")
MAP {
    !echo("host: $ITEM")
}

FILTER { $ITEM != "" }     # keep non-empty lines → $FILTERED
```

---

## UNSAFE Block

Disables stealth checks for the enclosed block — use for local lab work only:

```shadow
UNSAFE {
    !sys("iptables -L")
    !sys("tcpdump -i any -c 5")
}
```

---

## Full Example Mission

```shadow
# Recon mission — local lab network

VAR network = "192.168.1"

TARGET("$network.1")
!echo("=== GATEWAY ===")
SCAN(22,80,443,8080,8443)
STRIKE(recon, quick_scan)
AI("What services are likely running on a home router?")

FOR host IN 10 20 30 50 {
    TARGET("$network.$host")
    SCAN(22,80,443)
    IF $EXIT_CODE == 0 {
        !echo("Active host: $network.$host")
        STRIKE(vuln, nuclei_scan)
    }
}

!echo("=== MISSION COMPLETE ===")
RETURN "ok"
```

---

## REPL

Launch the interactive shell:

```
python3 shadowscript/core/engine.py
```

Metacommands: `.vars` `.modules` `.help` `.exit`
