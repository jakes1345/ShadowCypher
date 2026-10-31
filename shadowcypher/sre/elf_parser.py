"""
SHADOWCYPHER SRE — Binary Parsing & Checksec Engine
Deep ELF32/ELF64 binary deconstruction using pure binary-level struct unpacking.
Parses ELF headers, program headers, section headers, symbol tables, and dynamic tags.
Implements complete Checksec binary hardening analysis (Canary, NX, PIE, RELRO, RPATH).
"""

from __future__ import annotations

import dataclasses
import os
import struct
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


# ── ELF Constants ────────────────────────────────────────────────────────────

ELF_MAGIC = b"\x7fELF"
EI_CLASS_32 = 1
EI_CLASS_64 = 2
EI_DATA_LSB = 1  # Little endian
EI_DATA_MSB = 2  # Big endian

# Program header types
PT_NULL = 0
PT_LOAD = 1
PT_DYNAMIC = 2
PT_INTERP = 3
PT_NOTE = 4
PT_SHLIB = 5
PT_PHDR = 6
PT_TLS = 7
PT_GNU_EH_FRAME = 0x6474e550
PT_GNU_STACK = 0x6474e551
PT_GNU_RELRO = 0x6474e552

# Program header flags
PF_X = 1  # Execute
PF_W = 2  # Write
PF_R = 4  # Read

# Section types
SHT_NULL = 0
SHT_PROGBITS = 1
SHT_SYMTAB = 2
SHT_STRTAB = 3
SHT_RELA = 4
SHT_HASH = 5
SHT_DYNAMIC = 6
SHT_NOTE = 7
SHT_NOBITS = 8
SHT_REL = 9
SHT_DYNSYM = 11

# Dynamic array tags
DT_NULL = 0
DT_NEEDED = 1
DT_STRTAB = 5
DT_SYMTAB = 6
DT_RPATH = 15
DT_SYMBOLIC = 16
DT_REL = 17
DT_RELA = 7
DT_BIND_NOW = 24
DT_FLAGS = 30
DT_RUNPATH = 29
DT_FLAGS_1 = 0x6ffffffb

DF_1_NOW = 0x00000001
DF_1_PIE = 0x08000000

# Machine architectures
ARCH_MAP = {
    0x03: "x86 (Intel 80386)",
    0x3E: "x86_64 (AMD64 / Intel 64)",
    0x28: "ARM (32-bit)",
    0xB7: "AArch64 (ARM 64-bit)",
    0xF3: "RISC-V",
    0x08: "MIPS",
    0x14: "PowerPC",
    0x15: "PowerPC 64-bit",
}

TYPE_MAP = {
    1: "ET_REL (Relocatable object)",
    2: "ET_EXEC (Executable binary)",
    3: "ET_DYN (Shared object / PIE Executable)",
    4: "ET_CORE (Core dump)",
}


@dataclasses.dataclass
class ProgramHeader:
    p_type: int
    p_type_name: str
    p_flags: int
    p_offset: int
    p_vaddr: int
    p_paddr: int
    p_filesz: int
    p_memsz: int
    p_align: int
    is_executable: bool
    is_writable: bool
    is_readable: bool


@dataclasses.dataclass
class SectionHeader:
    sh_name_idx: int
    name: str
    sh_type: int
    sh_flags: int
    sh_addr: int
    sh_offset: int
    sh_size: int
    sh_link: int
    sh_info: int
    sh_addralign: int
    sh_entsize: int


@dataclasses.dataclass
class ChecksecReport:
    canary: bool
    canary_symbols: List[str]
    nx: bool  # No-Execute (True = stack non-executable)
    pie: bool  # Position Independent Executable
    relro: str  # "Full", "Partial", "None"
    rpath: Optional[str]
    runpath: Optional[str]
    fortify: bool
    fortify_symbols: List[str]
    security_score: int  # 0 to 100 based on active mitigations


class ELFParser:
    """Production-grade ELF32/ELF64 parser and security mitigation auditor."""

    def __init__(self, binary_path: str | Path):
        self.path = Path(binary_path).resolve()
        if not self.path.exists():
            raise FileNotFoundError(f"Binary target not found: {self.path}")

        self.raw_data = self.path.read_bytes()
        if len(self.raw_data) < 52 or self.raw_data[:4] != ELF_MAGIC:
            raise ValueError(f"File '{self.path}' is not a valid ELF binary")

        # Parse ELF identification
        self.is_64bit = (self.raw_data[4] == EI_CLASS_64)
        self.is_little_endian = (self.raw_data[5] == EI_DATA_LSB)
        self.endian_prefix = "<" if self.is_little_endian else ">"
        self.os_abi = self.raw_data[7]

        # Header fields
        self.e_type = 0
        self.e_machine = 0
        self.e_entry = 0
        self.e_phoff = 0
        self.e_shoff = 0
        self.e_phentsize = 0
        self.e_phnum = 0
        self.e_shentsize = 0
        self.e_shnum = 0
        self.e_shstrndx = 0

        self.program_headers: List[ProgramHeader] = []
        self.section_headers: List[SectionHeader] = []
        self.section_by_name: Dict[str, SectionHeader] = {}
        self.symbols: Set[str] = set()
        self.dynamic_tags: Dict[int, List[int]] = {}

        self._parse_elf_header()
        self._parse_program_headers()
        self._parse_section_headers()
        self._parse_symbol_tables()
        self._parse_dynamic_tags()

    def _parse_elf_header(self) -> None:
        if self.is_64bit:
            hdr_fmt = self.endian_prefix + "HHIQQQIHHHHHH"
            fields = struct.unpack(hdr_fmt, self.raw_data[16:64])
            (self.e_type, self.e_machine, _, self.e_entry, self.e_phoff,
             self.e_shoff, _, _, self.e_phentsize, self.e_phnum,
             self.e_shentsize, self.e_shnum, self.e_shstrndx) = fields
        else:
            hdr_fmt = self.endian_prefix + "HHIIIIIHHHHHH"
            fields = struct.unpack(hdr_fmt, self.raw_data[16:52])
            (self.e_type, self.e_machine, _, self.e_entry, self.e_phoff,
             self.e_shoff, _, _, self.e_phentsize, self.e_phnum,
             self.e_shentsize, self.e_shnum, self.e_shstrndx) = fields

    def _parse_program_headers(self) -> None:
        type_names = {
            PT_NULL: "PT_NULL", PT_LOAD: "PT_LOAD", PT_DYNAMIC: "PT_DYNAMIC",
            PT_INTERP: "PT_INTERP", PT_NOTE: "PT_NOTE", PT_SHLIB: "PT_SHLIB",
            PT_PHDR: "PT_PHDR", PT_TLS: "PT_TLS", PT_GNU_EH_FRAME: "PT_GNU_EH_FRAME",
            PT_GNU_STACK: "PT_GNU_STACK", PT_GNU_RELRO: "PT_GNU_RELRO"
        }
        for i in range(self.e_phnum):
            offset = self.e_phoff + (i * self.e_phentsize)
            if offset + self.e_phentsize > len(self.raw_data):
                break
            if self.is_64bit:
                p_fmt = self.endian_prefix + "IIQQQQQQ"
                p_type, p_flags, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_align = struct.unpack(
                    p_fmt, self.raw_data[offset:offset + 56]
                )
            else:
                p_fmt = self.endian_prefix + "IIIIIIII"
                p_type, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_flags, p_align = struct.unpack(
                    p_fmt, self.raw_data[offset:offset + 32]
                )

            self.program_headers.append(
                ProgramHeader(
                    p_type=p_type,
                    p_type_name=type_names.get(p_type, f"PT_UNKNOWN({hex(p_type)})"),
                    p_flags=p_flags,
                    p_offset=p_offset,
                    p_vaddr=p_vaddr,
                    p_paddr=p_paddr,
                    p_filesz=p_filesz,
                    p_memsz=p_memsz,
                    p_align=p_align,
                    is_executable=bool(p_flags & PF_X),
                    is_writable=bool(p_flags & PF_W),
                    is_readable=bool(p_flags & PF_R)
                )
            )

    def _parse_section_headers(self) -> None:
        raw_sections = []
        for i in range(self.e_shnum):
            offset = self.e_shoff + (i * self.e_shentsize)
            if offset + self.e_shentsize > len(self.raw_data):
                break
            if self.is_64bit:
                s_fmt = self.endian_prefix + "IIQQQQIIQQ"
                fields = struct.unpack(s_fmt, self.raw_data[offset:offset + 64])
                sh_name, sh_type, sh_flags, sh_addr, sh_offset, sh_size, sh_link, sh_info, sh_addralign, sh_entsize = fields
            else:
                s_fmt = self.endian_prefix + "IIIIIIIIII"
                fields = struct.unpack(s_fmt, self.raw_data[offset:offset + 40])
                sh_name, sh_type, sh_flags, sh_addr, sh_offset, sh_size, sh_link, sh_info, sh_addralign, sh_entsize = fields

            raw_sections.append((sh_name, sh_type, sh_flags, sh_addr, sh_offset, sh_size, sh_link, sh_info, sh_addralign, sh_entsize))

        # Resolve section names via .shstrtab string table
        shstrtab_data = b""
        if 0 <= self.e_shstrndx < len(raw_sections):
            strtab_offset = raw_sections[self.e_shstrndx][4]
            strtab_size = raw_sections[self.e_shstrndx][5]
            shstrtab_data = self.raw_data[strtab_offset:strtab_offset + strtab_size]

        def get_string(idx: int) -> str:
            if idx >= len(shstrtab_data):
                return ""
            end = shstrtab_data.find(b"\x00", idx)
            return shstrtab_data[idx:end].decode("utf-8", errors="replace") if end != -1 else ""

        for s in raw_sections:
            name = get_string(s[0])
            sh = SectionHeader(
                sh_name_idx=s[0],
                name=name,
                sh_type=s[1],
                sh_flags=s[2],
                sh_addr=s[3],
                sh_offset=s[4],
                sh_size=s[5],
                sh_link=s[6],
                sh_info=s[7],
                sh_addralign=s[8],
                sh_entsize=s[9]
            )
            self.section_headers.append(sh)
            if name:
                self.section_by_name[name] = sh

    def _parse_symbol_tables(self) -> None:
        # Parse both .dynsym and .symtab if present
        for sym_sec_name in [".dynsym", ".symtab"]:
            if sym_sec_name not in self.section_by_name:
                continue
            sec = self.section_by_name[sym_sec_name]
            # Associated string table is in sec.sh_link
            if sec.sh_link >= len(self.section_headers):
                continue
            strtab_sec = self.section_headers[sec.sh_link]
            strtab_bytes = self.raw_data[strtab_sec.sh_offset:strtab_sec.sh_offset + strtab_sec.sh_size]
            sym_bytes = self.raw_data[sec.sh_offset:sec.sh_offset + sec.sh_size]

            entsize = sec.sh_entsize or (24 if self.is_64bit else 16)
            num_syms = len(sym_bytes) // entsize

            for i in range(num_syms):
                chunk = sym_bytes[i * entsize:(i + 1) * entsize]
                st_name_idx = struct.unpack(self.endian_prefix + "I", chunk[:4])[0]
                if st_name_idx < len(strtab_bytes):
                    null_pos = strtab_bytes.find(b"\x00", st_name_idx)
                    if null_pos != -1:
                        sym_str = strtab_bytes[st_name_idx:null_pos].decode("utf-8", errors="replace")
                        if sym_str:
                            self.symbols.add(sym_str)

    def _parse_dynamic_tags(self) -> None:
        if ".dynamic" not in self.section_by_name:
            return
        sec = self.section_by_name[".dynamic"]
        dyn_bytes = self.raw_data[sec.sh_offset:sec.sh_offset + sec.sh_size]
        entsize = 16 if self.is_64bit else 8
        num_tags = len(dyn_bytes) // entsize

        for i in range(num_tags):
            chunk = dyn_bytes[i * entsize:(i + 1) * entsize]
            if self.is_64bit:
                d_tag, d_val = struct.unpack(self.endian_prefix + "QQ", chunk)
            else:
                d_tag, d_val = struct.unpack(self.endian_prefix + "II", chunk)
            if d_tag == DT_NULL:
                break
            self.dynamic_tags.setdefault(d_tag, []).append(d_val)

    def run_checksec(self) -> ChecksecReport:
        """Evaluate binary security hardening mitigations."""
        # 1. Stack Canary
        canary_syms = [s for s in self.symbols if "__stack_chk" in s]
        has_canary = len(canary_syms) > 0

        # 2. NX (No-Execute)
        has_nx = True
        for ph in self.program_headers:
            if ph.p_type == PT_GNU_STACK:
                # If stack has execute flag (PF_X), NX is disabled
                if ph.is_executable:
                    has_nx = False
                break

        # 3. PIE (Position Independent Executable)
        is_pie = False
        if self.e_type == 3:  # ET_DYN
            # Check for DT_DEBUG or dynamic tags
            flags_1 = self.dynamic_tags.get(DT_FLAGS_1, [])
            if any(f & DF_1_PIE for f in flags_1) or PT_INTERP in [ph.p_type for ph in self.program_headers]:
                is_pie = True

        # 4. RELRO
        has_relro_header = any(ph.p_type == PT_GNU_RELRO for ph in self.program_headers)
        bind_now = False
        if DT_BIND_NOW in self.dynamic_tags:
            bind_now = True
        flags_1 = self.dynamic_tags.get(DT_FLAGS_1, [])
        if any(f & DF_1_NOW for f in flags_1):
            bind_now = True

        if has_relro_header and bind_now:
            relro_status = "Full RELRO"
        elif has_relro_header:
            relro_status = "Partial RELRO"
        else:
            relro_status = "No RELRO"

        # 5. RPATH / RUNPATH
        rpath = None
        runpath = None
        # String table for dynamic strings
        if ".dynstr" in self.section_by_name:
            dynstr = self.raw_data[self.section_by_name[".dynstr"].sh_offset:
                                   self.section_by_name[".dynstr"].sh_offset + self.section_by_name[".dynstr"].sh_size]
            for tag_val in self.dynamic_tags.get(DT_RPATH, []):
                if tag_val < len(dynstr):
                    end = dynstr.find(b"\x00", tag_val)
                    rpath = dynstr[tag_val:end].decode("utf-8", errors="replace")
            for tag_val in self.dynamic_tags.get(DT_RUNPATH, []):
                if tag_val < len(dynstr):
                    end = dynstr.find(b"\x00", tag_val)
                    runpath = dynstr[tag_val:end].decode("utf-8", errors="replace")

        # 6. Fortify Source
        fortify_syms = [s for s in self.symbols if s.endswith("_chk")]
        has_fortify = len(fortify_syms) > 0

        # Calculate security score (0-100)
        score = 0
        if has_canary:
            score += 25
        if has_nx:
            score += 25
        if is_pie:
            score += 25
        if relro_status == "Full RELRO":
            score += 20
        elif relro_status == "Partial RELRO":
            score += 10
        if has_fortify:
            score += 5

        return ChecksecReport(
            canary=has_canary,
            canary_symbols=canary_syms,
            nx=has_nx,
            pie=is_pie,
            relro=relro_status,
            rpath=rpath,
            runpath=runpath,
            fortify=has_fortify,
            fortify_symbols=fortify_syms[:10],
            security_score=score
        )

    def get_summary(self) -> Dict[str, Any]:
        checksec = self.run_checksec()
        return {
            "binary": str(self.path),
            "size_bytes": len(self.raw_data),
            "architecture": ARCH_MAP.get(self.e_machine, f"Unknown ({hex(self.e_machine)})"),
            "elf_class": "ELF64" if self.is_64bit else "ELF32",
            "endianness": "Little-Endian" if self.is_little_endian else "Big-Endian",
            "type": TYPE_MAP.get(self.e_type, f"Unknown ({self.e_type})"),
            "entry_point": hex(self.e_entry),
            "program_headers_count": len(self.program_headers),
            "section_headers_count": len(self.section_headers),
            "total_symbols_indexed": len(self.symbols),
            "checksec": dataclasses.asdict(checksec)
        }
