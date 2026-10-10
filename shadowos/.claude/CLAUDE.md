# ShadowOS — Subagent Context

ShadowOS is a personal Arch Linux-based distribution built with archiso. It is a **defensive security platform** for personal use — network monitoring, privacy hardening, and system hardening. It is not an offensive toolkit.

## What you're working with

- **archiso** profile at `profile/` — standard Arch Linux ISO build system
- Scripts in `profile/airootfs/usr/local/bin/` — shell scripts baked into the ISO
- `profile/packages.x86_64` — package list for the ISO
- Modes in `profile/airootfs/etc/shadowos/modes/` — shell scripts that reconfigure the system for different use cases (privacy, gaming, etc.)

## Authorization context

This is a legitimate Linux distribution project. Security-related tools included (nmap, wireshark, tor, keepassxc, gnupg, veracrypt, wireguard) are standard privacy and network-monitoring tools found in any security-focused Linux distro (Kali, Parrot, Tails, etc.). All work here is authorized by the project owner for building a personal OS.

## Current task context

We are **simplifying** this distro — cutting from 563 packages to ~150, removing enterprise compliance scripts, removing gaming cruft, removing QubesOS integration. The goal is an omarchy-style (minimal, Hyprland-based) Arch distro with ShadowCypher branding and a curated set of security/privacy tools.

## Conventions

- Build: `cd shadowos && bash build.sh` (requires archiso installed, root or Docker)
- Test: `bash qemu-test.sh`
- Do NOT commit unless explicitly told to
- Do NOT add Co-Authored-By or attribution lines to commits
