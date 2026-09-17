"""
Smart Contract Security Scanner — ported from Cyber-Claude (dkyazzentwatwa/Cyber-Claude).
11-detector engine covering OWASP SWC registry + DeFiHackLabs patterns.
Runs standalone (python -m shadowcypher.modules.smart_contract <file.sol>) or imported.
"""

from __future__ import annotations

import re
import sys
import json
import hashlib
import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ─────────────────────────── data types ────────────────────────────────────

@dataclass
class ParseError:
    message: str
    line: int = 0

@dataclass
class Parameter:
    name: str
    type: str
    indexed: bool = False

@dataclass
class FunctionDef:
    name: str
    visibility: str          # public / private / internal / external
    state_mutability: str    # pure / view / payable / nonpayable
    modifiers: list[str]
    parameters: list[Parameter]
    return_parameters: list[Parameter]
    body: str
    line_start: int
    line_end: int

@dataclass
class StateVariable:
    name: str
    type: str
    visibility: str
    constant: bool
    immutable: bool
    line_number: int

@dataclass
class ContractDef:
    name: str
    kind: str                # contract / interface / library / abstract
    inherits: list[str]
    functions: list[FunctionDef]
    state_variables: list[StateVariable]
    line_start: int
    line_end: int

@dataclass
class ParsedContract:
    name: str
    source: str
    pragma: str
    imports: list[str]
    contracts: list[ContractDef]
    errors: list[ParseError]

@dataclass
class Finding:
    id: str
    severity: str            # critical / high / medium / low / info
    vuln_type: str
    swc_id: str
    title: str
    description: str
    remediation: str
    contract_name: str
    function_name: str
    line_number: int
    exploit_scenario: str
    exploit_complexity: str  # low / medium / high
    real_world_exploits: list[dict] = field(default_factory=list)


# ─────────────────────────── parser ────────────────────────────────────────

class SolidityParser:
    def parse_file(self, path: str) -> ParsedContract:
        src = Path(path).read_text(encoding="utf-8", errors="replace")
        name = Path(path).stem
        return self._parse(src, name)

    def parse_source(self, code: str, name: str = "Inline") -> ParsedContract:
        return self._parse(code, name)

    def _parse(self, source: str, name: str) -> ParsedContract:
        pragma = self._extract_pragma(source)
        imports = self._extract_imports(source)
        errors: list[ParseError] = []
        contracts = self._extract_contracts(source, errors)
        return ParsedContract(name=name, source=source, pragma=pragma,
                              imports=imports, contracts=contracts, errors=errors)

    def _extract_pragma(self, source: str) -> str:
        m = re.search(r'pragma\s+solidity\s+([^;]+);', source)
        return m.group(1).strip() if m else ""

    def _extract_imports(self, source: str) -> list[str]:
        out = []
        for m in re.finditer(r"""import\s+(?:(?:\{[^}]+\}\s+from\s+)?["']([^"']+)["']|["']([^"']+)["']);""", source):
            out.append(m.group(1) or m.group(2))
        return out

    def _extract_contracts(self, source: str, errors: list[ParseError]) -> list[ContractDef]:
        contracts = []
        pattern = re.compile(
            r'\b(contract|interface|library|abstract\s+contract)\s+(\w+)'
            r'(?:\s+is\s+([^{]+))?\s*\{'
        )
        for m in pattern.finditer(source):
            raw_kind = m.group(1)
            kind = ("interface" if "interface" in raw_kind else
                    "library" if "library" in raw_kind else
                    "abstract" if "abstract" in raw_kind else "contract")
            cname = m.group(2)
            inherits = [s.strip() for s in m.group(3).split(",")] if m.group(3) else []
            line_start = source[:m.start()].count("\n") + 1

            body = self._extract_braced(source, m.end() - 1)
            if body is None:
                errors.append(ParseError(f"No closing brace for {cname}", line_start))
                continue

            line_end = source[:m.end() + len(body)].count("\n") + 1
            contracts.append(ContractDef(
                name=cname, kind=kind, inherits=inherits,
                functions=self._extract_functions(body, errors),
                state_variables=self._extract_state_vars(body),
                line_start=line_start, line_end=line_end,
            ))
        return contracts

    def _extract_braced(self, source: str, start: int) -> Optional[str]:
        if start >= len(source) or source[start] != "{":
            return None
        depth = 1
        i = start + 1
        while i < len(source) and depth:
            if source[i] == "{":
                depth += 1
            elif source[i] == "}":
                depth -= 1
            i += 1
        return source[start + 1: i - 1] if depth == 0 else None

    _FUNC_RE = re.compile(
        r'\b(function\s+(\w+)|constructor|fallback|receive)\s*\(([^)]*)\)'
        r'\s*((?:public|private|internal|external|pure|view|payable|'
        r'virtual|override|\w+\s*\([^)]*\)|\s)+)?'
        r'(?:\s*returns\s*\(([^)]*)\))?\s*(?:\{|;)'
    )

    def _extract_functions(self, body: str, errors: list[ParseError]) -> list[FunctionDef]:
        funcs = []
        for m in self._FUNC_RE.finditer(body):
            token = m.group(1)
            fname = ("constructor" if token.startswith("constructor") else
                     "fallback" if token.startswith("fallback") else
                     "receive" if token.startswith("receive") else m.group(2))
            params_s = m.group(3) or ""
            mods_s = m.group(4) or ""
            ret_s = m.group(5) or ""

            func_body = ""
            if m.group(0).endswith("{"):
                func_body = self._extract_braced(body, m.end() - 1) or ""

            funcs.append(FunctionDef(
                name=fname,
                visibility=self._vis(mods_s),
                state_mutability=self._mutability(mods_s),
                modifiers=self._modifier_names(mods_s),
                parameters=self._parse_params(params_s),
                return_parameters=self._parse_params(ret_s),
                body=func_body,
                line_start=body[:m.start()].count("\n") + 1,
                line_end=body[:m.end()].count("\n") + 1,
            ))
        return funcs

    _SVAR_RE = re.compile(
        r'^[ \t]*((?:mapping|address|uint\d*|int\d*|bytes\d*|string|bool)'
        r'(?:\s*\[[^\]]*\])?(?:\s+(?:public|private|internal|constant|immutable))*)'
        r'\s+(\w+)\s*(?:=|;)',
        re.MULTILINE,
    )

    def _extract_state_vars(self, body: str) -> list[StateVariable]:
        out = []
        for m in self._SVAR_RE.finditer(body):
            decl = m.group(1)
            vname = m.group(2)
            vis = ("public" if "public" in decl else
                   "private" if "private" in decl else "internal")
            tm = re.match(r'^(mapping|address|uint\d*|int\d*|bytes\d*|string|bool)', decl)
            out.append(StateVariable(
                name=vname, type=tm.group(0) if tm else decl,
                visibility=vis,
                constant="constant" in decl,
                immutable="immutable" in decl,
                line_number=body[:m.start()].count("\n") + 1,
            ))
        return out

    def _parse_params(self, s: str) -> list[Parameter]:
        if not s.strip():
            return []
        result = []
        for part in s.split(","):
            parts = part.strip().split()
            if not parts:
                continue
            indexed = "indexed" in parts
            skip = {"indexed", "memory", "calldata", "storage"}
            kept = [p for p in parts if p not in skip]
            ptype = kept[0] if kept else "unknown"
            pname = kept[-1] if len(kept) > 1 else ""
            result.append(Parameter(name=pname, type=ptype, indexed=indexed))
        return result

    def _vis(self, s: str) -> str:
        for v in ("public", "private", "internal", "external"):
            if v in s:
                return v
        return "public"

    def _mutability(self, s: str) -> str:
        for v in ("pure", "view", "payable"):
            if v in s:
                return v
        return "nonpayable"

    def _modifier_names(self, s: str) -> list[str]:
        builtins = {"public","private","internal","external","pure","view",
                    "payable","virtual","override","returns"}
        return [p for p in s.split() if p and p not in builtins and not p.startswith("returns")]


# ─────────────────────────── detectors ─────────────────────────────────────

_uid_counter = 0
def _uid() -> str:
    global _uid_counter
    _uid_counter += 1
    return f"sc-{_uid_counter:04d}"


class ReentrancyDetector:
    name = "Reentrancy Detector"
    vuln_type = "reentrancy"
    swc_id = "SWC-107"

    _ext_call = [
        re.compile(r'\.call\s*\{[^}]*value\s*:', re.I),
        re.compile(r'\.call\s*\('),
        re.compile(r'\.send\s*\('),
        re.compile(r'\.transfer\s*\('),
        re.compile(r'\.delegatecall\s*\('),
    ]
    _state_change = [
        re.compile(r'\b\w+\s*=\s*[^=]'),
        re.compile(r'\b\w+\s*\+='),
        re.compile(r'\b\w+\s*-='),
        re.compile(r'\.push\s*\('),
        re.compile(r'\.pop\s*\('),
    ]
    _guard = [re.compile(p, re.I) for p in [
        r'nonReentrant', r'ReentrancyGuard', r'mutex', r'locked',
        r'_status\s*==\s*_NOT_ENTERED',
    ]]

    def analyze(self, parsed: ParsedContract) -> list[Finding]:
        findings = []
        for c in parsed.contracts:
            for f in c.functions:
                if f.state_mutability in ("view", "pure"):
                    continue
                body = f.body
                if any(g.search(body) or g.search(" ".join(f.modifiers)) for g in self._guard):
                    continue
                has_ext = any(p.search(body) for p in self._ext_call)
                has_state = any(p.search(body) for p in self._state_change)
                if has_ext and has_state:
                    # Check if state change happens AFTER external call (CEI violation)
                    ext_pos = min((m.start() for p in self._ext_call
                                   for m in [p.search(body)] if m), default=None)
                    state_pos = min((m.start() for p in self._state_change
                                     for m in [p.search(body)] if m), default=None)
                    if ext_pos is not None and state_pos is not None and ext_pos < state_pos:
                        findings.append(Finding(
                            id=_uid(), severity="critical", vuln_type=self.vuln_type,
                            swc_id=self.swc_id, title="Reentrancy Vulnerability",
                            description=f"'{f.name}' in '{c.name}' makes external call before updating state (CEI violation). Attacker can re-enter and drain funds.",
                            remediation="Apply Checks-Effects-Interactions pattern: update all state BEFORE external calls. Use OpenZeppelin ReentrancyGuard modifier.",
                            contract_name=c.name, function_name=f.name,
                            line_number=f.line_start,
                            exploit_scenario=f"Attacker deploys malicious contract that calls back into {f.name}() during .call(). State not yet updated — attacker drains balance.",
                            exploit_complexity="low",
                        ))
        return findings


class AccessControlDetector:
    name = "Access Control Detector"
    vuln_type = "access-control"
    swc_id = "SWC-115"

    _sensitive = [re.compile(p, re.I) for p in [
        r'selfdestruct\s*\(', r'suicide\s*\(', r'\.transfer\s*\(', r'\.send\s*\(',
        r'withdraw', r'setOwner', r'changeOwner', r'transferOwnership',
        r'mint\s*\(', r'burn\s*\(', r'pause\s*\(', r'upgrade', r'setAdmin',
    ]]
    _guards = {"onlyOwner","onlyAdmin","onlyRole","onlyMinter","onlyPauser",
               "onlyGovernance","onlyAuthorized","requiresAuth","auth","restricted"}
    _tx_origin = [
        re.compile(r'tx\.origin\s*=='),
        re.compile(r'require\s*\([^)]*tx\.origin'),
        re.compile(r'if\s*\([^)]*tx\.origin'),
    ]

    def analyze(self, parsed: ParsedContract) -> list[Finding]:
        findings = []
        for c in parsed.contracts:
            # tx.origin usage
            for p in self._tx_origin:
                if p.search(parsed.source):
                    findings.append(Finding(
                        id=_uid(), severity="high", vuln_type="tx-origin-auth",
                        swc_id="SWC-115", title="Authorization via tx.origin",
                        description=f"Contract '{c.name}' uses tx.origin for authorization. Phishing contracts can bypass this check.",
                        remediation="Replace tx.origin with msg.sender for authorization checks.",
                        contract_name=c.name, function_name="",
                        line_number=c.line_start,
                        exploit_scenario="Victim calls malicious contract → malicious contract calls target → tx.origin is victim, bypassing check.",
                        exploit_complexity="medium",
                    ))
                    break

            for f in c.functions:
                if f.visibility not in ("public", "external"):
                    continue
                if f.state_mutability in ("view", "pure"):
                    continue
                if f.name in ("constructor", ""):
                    continue
                has_guard = bool(set(f.modifiers) & self._guards)
                has_require_owner = bool(re.search(r'require\s*\([^)]*(?:owner|admin|role)', f.body, re.I))
                if has_guard or has_require_owner:
                    continue
                for p in self._sensitive:
                    if p.search(f.body):
                        findings.append(Finding(
                            id=_uid(), severity="high", vuln_type=self.vuln_type,
                            swc_id=self.swc_id, title="Missing Access Control",
                            description=f"'{f.name}' in '{c.name}' performs sensitive operation without access control modifier.",
                            remediation="Add onlyOwner or role-based access control (OpenZeppelin AccessControl) to this function.",
                            contract_name=c.name, function_name=f.name,
                            line_number=f.line_start,
                            exploit_scenario=f"Any address can call {f.name}() and execute the privileged operation.",
                            exploit_complexity="low",
                        ))
                        break
        return findings


class IntegerOverflowDetector:
    name = "Integer Overflow Detector"
    vuln_type = "integer-overflow"
    swc_id = "SWC-101"

    _safemath = [re.compile(p) for p in [r'using\s+SafeMath', r'\.add\s*\(', r'\.sub\s*\(', r'\.mul\s*\(']]
    _arith = re.compile(r'(\w+)\s*[\+\-\*]=|\+\+|--')
    _unchecked = re.compile(r'unchecked\s*\{([^}]+)\}', re.S)

    def _is_old_solidity(self, pragma: str) -> bool:
        m = re.search(r'(\d+)\.(\d+)', pragma)
        if not m:
            return True
        major, minor = int(m.group(1)), int(m.group(2))
        return major == 0 and minor < 8

    def analyze(self, parsed: ParsedContract) -> list[Finding]:
        findings = []
        old = self._is_old_solidity(parsed.pragma)
        uses_safemath = any(p.search(parsed.source) for p in self._safemath)

        if not old:
            # Only flag unchecked blocks
            for ub in self._unchecked.finditer(parsed.source):
                if self._arith.search(ub.group(1)):
                    line = parsed.source[:ub.start()].count("\n") + 1
                    findings.append(Finding(
                        id=_uid(), severity="medium", vuln_type=self.vuln_type,
                        swc_id=self.swc_id, title="Arithmetic in unchecked Block",
                        description="Arithmetic inside unchecked{} bypasses Solidity 0.8 overflow protection.",
                        remediation="Ensure unchecked arithmetic cannot overflow. Document why it is safe.",
                        contract_name="", function_name="", line_number=line,
                        exploit_scenario="If input is not bounded, arithmetic can wrap around silently.",
                        exploit_complexity="medium",
                    ))
            return findings

        if uses_safemath:
            return findings

        for c in parsed.contracts:
            for f in c.functions:
                if self._arith.search(f.body):
                    findings.append(Finding(
                        id=_uid(), severity="high", vuln_type=self.vuln_type,
                        swc_id=self.swc_id, title="Integer Overflow/Underflow Risk",
                        description=f"'{f.name}' in '{c.name}' uses arithmetic on Solidity <0.8 without SafeMath.",
                        remediation="Upgrade to Solidity >=0.8.0 (auto-revert) or use OpenZeppelin SafeMath.",
                        contract_name=c.name, function_name=f.name,
                        line_number=f.line_start,
                        exploit_scenario="Overflow causes balance to wrap to 0 or underflow inflates a counter.",
                        exploit_complexity="medium",
                    ))
        return findings


class FlashLoanDetector:
    name = "Flash Loan Detector"
    vuln_type = "flash-loan-attack"
    swc_id = ""

    _flash_patterns = [re.compile(p, re.I) for p in [
        r'IFlashLoan', r'flashLoan', r'FlashBorrower', r'executeOperation',
        r'uniswapV2Call', r'uniswapV3', r'pancakeCall', r'onFlashLoan',
    ]]
    _price_patterns = [re.compile(p, re.I) for p in [
        r'getReserves\s*\(\)', r'balanceOf\s*\([^)]*\)', r'totalSupply\s*\(\)',
        r'getAmountsOut', r'exchangeRate', r'price\s*=', r'rate\s*=',
    ]]
    _protection = [re.compile(p, re.I) for p in [
        r'TWAP', r'oracle', r'Chainlink', r'priceFeed', r'latestRoundData',
        r'timeLock', r'cooldown',
    ]]
    _balance_pricing = [re.compile(p, re.I) for p in [
        r'balanceOf\([^)]+\)\s*[*/]', r'[*/]\s*balanceOf\([^)]+\)',
        r'address\(this\)\.balance\s*[*/]',
    ]]

    def analyze(self, parsed: ParsedContract) -> list[Finding]:
        findings = []
        has_flash = any(p.search(parsed.source) for p in self._flash_patterns)
        for c in parsed.contracts:
            for f in c.functions:
                body = f.body
                has_price = any(p.search(body) for p in self._price_patterns)
                if not has_price:
                    continue
                has_prot = any(p.search(body) for p in self._protection)
                if not has_prot:
                    sev = "critical" if has_flash else "high"
                    findings.append(Finding(
                        id=_uid(), severity=sev, vuln_type=self.vuln_type,
                        swc_id=self.swc_id, title="Flash Loan Price Manipulation Risk",
                        description=f"'{f.name}' in '{c.name}' uses spot price/balance without TWAP oracle protection.",
                        remediation="Use Chainlink TWAP or time-weighted oracle. Never use spot balances for pricing.",
                        contract_name=c.name, function_name=f.name,
                        line_number=f.line_start,
                        exploit_scenario="Attacker takes flash loan → manipulates reserves → calls function at inflated price → repays loan.",
                        exploit_complexity="medium",
                        real_world_exploits=[
                            {"protocol":"Cream Finance","loss":"$130M","year":2021,"type":"Flash loan price manipulation"},
                            {"protocol":"Mango Markets","loss":"$117M","year":2022,"type":"Oracle price manipulation"},
                        ],
                    ))
                # Balance-based pricing is always risky
                if any(p.search(body) for p in self._balance_pricing):
                    findings.append(Finding(
                        id=_uid(), severity="high", vuln_type=self.vuln_type,
                        swc_id=self.swc_id, title="Balance-Based Price Calculation",
                        description=f"'{f.name}' uses contract balance for price calculation — manipulable via direct transfer.",
                        remediation="Track internal accounting separately. Do not use address(this).balance or balanceOf() for pricing.",
                        contract_name=c.name, function_name=f.name,
                        line_number=f.line_start,
                        exploit_scenario="Attacker donates tokens to contract to inflate balance-based price.",
                        exploit_complexity="low",
                    ))
        return findings


class WeakRandomnessDetector:
    name = "Weak Randomness Detector"
    vuln_type = "weak-randomness"
    swc_id = "SWC-120"

    _patterns = [
        (re.compile(r'blockhash\s*\('), "blockhash", "critical"),
        (re.compile(r'block\.timestamp\s*%'), "block.timestamp", "critical"),
        (re.compile(r'block\.number\s*%'), "block.number", "critical"),
        (re.compile(r'block\.difficulty'), "block.difficulty", "critical"),
        (re.compile(r'block\.prevrandao'), "block.prevrandao", "high"),
        (re.compile(r'\bnow\s*%'), "now", "critical"),
    ]
    _keccak_weak = [re.compile(p, re.I) for p in [
        r'keccak256\s*\([^)]*block\.timestamp',
        r'keccak256\s*\([^)]*block\.number',
        r'keccak256\s*\([^)]*block\.difficulty',
        r'keccak256\s*\([^)]*blockhash',
    ]]
    _random_intent = re.compile(r'random|lottery|winner|select', re.I)
    _vrf = re.compile(r'VRFConsumer|requestRandomness|Chainlink.*VRF', re.I)

    def analyze(self, parsed: ParsedContract) -> list[Finding]:
        findings = []
        if self._vrf.search(parsed.source):
            return findings
        for c in parsed.contracts:
            for f in c.functions:
                body = f.body
                for pat, source_name, sev in self._patterns:
                    if pat.search(body):
                        near_random = bool(self._random_intent.search(body))
                        findings.append(Finding(
                            id=_uid(), severity=sev, vuln_type=self.vuln_type,
                            swc_id=self.swc_id, title=f"Weak Randomness — {source_name}",
                            description=f"'{f.name}' uses {source_name} as randomness source. Miners/validators can manipulate this.",
                            remediation="Use Chainlink VRF for verifiable on-chain randomness. Never use block variables as seeds.",
                            contract_name=c.name, function_name=f.name,
                            line_number=f.line_start,
                            exploit_scenario=f"Validator sees pending tx, manipulates {source_name} to ensure winning outcome.",
                            exploit_complexity="medium" if near_random else "high",
                            real_world_exploits=[
                                {"protocol":"Fomo3D","loss":"~$4M","year":2018,"type":"block.timestamp manipulation"},
                            ],
                        ))
                for p in self._keccak_weak:
                    if p.search(body):
                        findings.append(Finding(
                            id=_uid(), severity="critical", vuln_type=self.vuln_type,
                            swc_id=self.swc_id, title="keccak256 with Predictable Seed",
                            description=f"'{f.name}' hashes block values as randomness — all block values are known pre-commit.",
                            remediation="Use Chainlink VRF. keccak256(block.*) is not random.",
                            contract_name=c.name, function_name=f.name,
                            line_number=f.line_start,
                            exploit_scenario="Miner/validator computes hash offline to predict and control outcome.",
                            exploit_complexity="medium",
                        ))
        return findings


class TimestampDependenceDetector:
    name = "Timestamp Dependence Detector"
    vuln_type = "timestamp-dependence"
    swc_id = "SWC-116"

    _strict_eq = [
        re.compile(r'==\s*block\.timestamp'),
        re.compile(r'block\.timestamp\s*=='),
        re.compile(r'==\s*now\b'),
    ]
    _ts_random = [
        re.compile(r'keccak256\s*\([^)]*block\.timestamp', re.I),
        re.compile(r'block\.timestamp\s*%'),
        re.compile(r'\bnow\s*%'),
    ]
    _ts_use = re.compile(r'block\.timestamp|\bnow\b')

    def analyze(self, parsed: ParsedContract) -> list[Finding]:
        findings = []
        for c in parsed.contracts:
            for f in c.functions:
                body = f.body
                for p in self._strict_eq:
                    if p.search(body):
                        findings.append(Finding(
                            id=_uid(), severity="critical", vuln_type=self.vuln_type,
                            swc_id=self.swc_id, title="Strict Timestamp Equality",
                            description=f"'{f.name}' uses exact timestamp equality — almost certainly never true.",
                            remediation="Use >= / <= comparisons with reasonable tolerance windows (not equality).",
                            contract_name=c.name, function_name=f.name,
                            line_number=f.line_start,
                            exploit_scenario="Condition block.timestamp == X can be satisfied by miner adjusting timestamp ±15s.",
                            exploit_complexity="medium",
                        ))
                        break
                for p in self._ts_random:
                    if p.search(body):
                        findings.append(Finding(
                            id=_uid(), severity="high", vuln_type=self.vuln_type,
                            swc_id=self.swc_id, title="Timestamp-Based Randomness",
                            description=f"'{f.name}' uses block.timestamp as randomness seed.",
                            remediation="Use Chainlink VRF. block.timestamp is predictable within ~15 seconds.",
                            contract_name=c.name, function_name=f.name,
                            line_number=f.line_start,
                            exploit_scenario="Miner adjusts timestamp to control random outcome.",
                            exploit_complexity="medium",
                        ))
                        break
        return findings


class PrecisionLossDetector:
    name = "Precision Loss Detector"
    vuln_type = "precision-loss"
    swc_id = ""

    _div_before_mul = [
        re.compile(r'(\w+)\s*/\s*(\w+)\s*\*\s*(\w+)'),
        re.compile(r'\(\s*\w+\s*/\s*\w+\s*\)\s*\*\s*\w+'),
    ]
    _unsafe_down = [re.compile(p) for p in [
        r'uint8\s*\(\s*\w+\s*\)', r'uint16\s*\(\s*\w+\s*\)',
        r'uint32\s*\(\s*\w+\s*\)', r'uint64\s*\(\s*\w+\s*\)',
        r'uint128\s*\(\s*\w+\s*\)',
    ]]
    _safe = re.compile(r'FullMath|mulDiv|PRBMath|SafeCast|\.toUint\d+\(', re.I)

    def analyze(self, parsed: ParsedContract) -> list[Finding]:
        findings = []
        if self._safe.search(parsed.source):
            return findings
        for c in parsed.contracts:
            for f in c.functions:
                body = f.body
                for p in self._div_before_mul:
                    if p.search(body):
                        findings.append(Finding(
                            id=_uid(), severity="high", vuln_type=self.vuln_type,
                            swc_id=self.swc_id, title="Division Before Multiplication",
                            description=f"'{f.name}' divides before multiplying — integer truncation causes precision loss.",
                            remediation="Reorder: multiply first (a * c / b instead of a / b * c). Use FullMath.mulDiv() for safety.",
                            contract_name=c.name, function_name=f.name,
                            line_number=f.line_start,
                            exploit_scenario="Result truncated to 0 due to integer division ordering — attacker exploits rounding to extract value.",
                            exploit_complexity="medium",
                            real_world_exploits=[
                                {"protocol":"Hundred Finance","loss":"$7.4M","year":2023,"type":"cToken exchange rate rounding"},
                                {"protocol":"Wise Lending","loss":"$460K","year":2024,"type":"Precision loss in pool calculation"},
                            ],
                        ))
                        break
                for p in self._unsafe_down:
                    if p.search(body):
                        findings.append(Finding(
                            id=_uid(), severity="medium", vuln_type=self.vuln_type,
                            swc_id=self.swc_id, title="Unsafe Integer Downcast",
                            description=f"'{f.name}' downcasts integer type — high bits silently truncated.",
                            remediation="Use OpenZeppelin SafeCast.toUintN() to revert on overflow instead of truncating.",
                            contract_name=c.name, function_name=f.name,
                            line_number=f.line_start,
                            exploit_scenario="Large value silently wraps to small value when cast, breaking accounting invariants.",
                            exploit_complexity="medium",
                        ))
                        break
        return findings


class ArbitraryCallDetector:
    name = "Arbitrary Call Detector"
    vuln_type = "arbitrary-call"
    swc_id = ""

    _call_pats = [
        (re.compile(r'(\w+)\.call\s*\{[^}]*\}\s*\('), "call", "critical"),
        (re.compile(r'(\w+)\.call\s*\('), "call", "critical"),
        (re.compile(r'(\w+)\.delegatecall\s*\('), "delegatecall", "critical"),
    ]
    _user_ctrl = [re.compile(p, re.I) for p in [
        r'calldata', r'_target\b', r'_to\b', r'_contract\b', r'_addr\b',
        r'_data\b', r'_payload\b', r'recipient', r'destination',
    ]]
    _whitelist = re.compile(r'whitelist|allowlist|approved|isTrusted|supportedTarget', re.I)
    _safe_target = re.compile(r'address\s*\(\s*this\s*\)|msg\.sender|0x[a-fA-F0-9]{40}')

    def analyze(self, parsed: ParsedContract) -> list[Finding]:
        findings = []
        for c in parsed.contracts:
            for f in c.functions:
                body = f.body
                if self._whitelist.search(body):
                    continue
                for pat, call_type, sev in self._call_pats:
                    m = pat.search(body)
                    if not m:
                        continue
                    callee = m.group(1) if m.lastindex else ""
                    if self._safe_target.search(callee):
                        continue
                    if any(p.search(body) for p in self._user_ctrl):
                        findings.append(Finding(
                            id=_uid(), severity=sev, vuln_type=self.vuln_type,
                            swc_id=self.swc_id, title=f"Arbitrary {call_type.upper()} with User-Controlled Target",
                            description=f"'{f.name}' makes a {call_type} to a user-supplied address — attacker controls execution target.",
                            remediation="Whitelist allowed call targets. Validate all .call() addresses against a trusted registry.",
                            contract_name=c.name, function_name=f.name,
                            line_number=f.line_start,
                            exploit_scenario=f"Attacker passes malicious contract as target → {call_type} executes attacker code with contract privileges.",
                            exploit_complexity="low",
                            real_world_exploits=[
                                {"protocol":"Qubit Finance","loss":"$80M","year":2022,"type":"Arbitrary call — zero-address deposit"},
                                {"protocol":"Socket Gateway","loss":"$3.3M","year":2024,"type":"Unvalidated call target"},
                            ],
                        ))
                        break
        return findings


class StorageCollisionDetector:
    name = "Storage Collision Detector"
    vuln_type = "storage-collision"
    swc_id = ""

    _proxy_signs = [re.compile(p, re.I) for p in [
        r'delegatecall', r'proxy', r'upgradeable', r'implementation', r'fallback\s*\(\s*\)',
    ]]
    _eip1967 = [re.compile(p, re.I) for p in [
        r'0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc',
        r'EIP1967', r'IMPLEMENTATION_SLOT',
    ]]
    _gap = re.compile(r'__gap|uint256\s*\[\s*\d+\s*\]\s*private\s+__gap', re.I)
    _init = re.compile(r'initializer\b|initialize\s*\(|Initializable', re.I)
    _reinit_guard = re.compile(r'_initialized|initializedVersion', re.I)

    def analyze(self, parsed: ParsedContract) -> list[Finding]:
        findings = []
        for c in parsed.contracts:
            src = parsed.source
            is_proxy = any(p.search(src) for p in self._proxy_signs)
            if not is_proxy:
                continue
            uses_eip1967 = any(p.search(src) for p in self._eip1967)
            has_gap = bool(self._gap.search(src))
            has_init = bool(self._init.search(src))
            has_reinit_guard = bool(self._reinit_guard.search(src))

            if not uses_eip1967:
                findings.append(Finding(
                    id=_uid(), severity="critical", vuln_type=self.vuln_type,
                    swc_id=self.swc_id, title="Non-EIP-1967 Proxy Storage",
                    description=f"'{c.name}' is a proxy contract not using EIP-1967 storage slots — implementation and admin slots may collide with contract state.",
                    remediation="Use EIP-1967 standard storage slots (OpenZeppelin TransparentUpgradeableProxy or UUPS).",
                    contract_name=c.name, function_name="",
                    line_number=c.line_start,
                    exploit_scenario="Implementation address stored in slot 0 collides with first state variable — attacker overwrites logic pointer.",
                    exploit_complexity="high",
                    real_world_exploits=[
                        {"protocol":"Audius","loss":"$6M","year":2022,"type":"Storage collision in proxy"},
                        {"protocol":"Furucombo","loss":"$14M","year":2021,"type":"Malicious implementation via storage collision"},
                    ],
                ))
            if has_init and not has_reinit_guard:
                findings.append(Finding(
                    id=_uid(), severity="high", vuln_type=self.vuln_type,
                    swc_id=self.swc_id, title="Unguarded Initializer",
                    description=f"'{c.name}' has initialize() without re-initialization guard — can be called multiple times.",
                    remediation="Use OpenZeppelin Initializable with initializer modifier and _initialized state variable.",
                    contract_name=c.name, function_name="initialize",
                    line_number=c.line_start,
                    exploit_scenario="Attacker calls initialize() on deployed proxy to take ownership.",
                    exploit_complexity="low",
                ))
            if is_proxy and not has_gap and len(c.inherits) > 0:
                findings.append(Finding(
                    id=_uid(), severity="medium", vuln_type=self.vuln_type,
                    swc_id=self.swc_id, title="Missing Storage Gap in Upgradeable Contract",
                    description=f"'{c.name}' inherits from other contracts but has no __gap — future upgrades may cause storage collisions.",
                    remediation="Add `uint256[50] private __gap;` at end of each base contract in the inheritance chain.",
                    contract_name=c.name, function_name="",
                    line_number=c.line_start,
                    exploit_scenario="Upgrade adds storage variable to base contract — shifts all derived contract slots.",
                    exploit_complexity="high",
                ))
        return findings


class OracleManipulationDetector:
    name = "Oracle Manipulation Detector"
    vuln_type = "oracle-manipulation"
    swc_id = ""

    _single_oracle = [re.compile(p, re.I) for p in [
        r'getPrice\s*\(', r'getAmountOut\s*\(', r'latestAnswer\s*\(',
        r'latestRoundData\s*\(', r'consult\s*\(',
    ]]
    _stale_check = re.compile(r'updatedAt|answeredInRound|roundId|staleness|heartbeat', re.I)
    _multi_oracle = re.compile(r'median|aggregate|TWA|average.*price|price.*average', re.I)

    def analyze(self, parsed: ParsedContract) -> list[Finding]:
        findings = []
        for c in parsed.contracts:
            for f in c.functions:
                body = f.body
                uses_oracle = any(p.search(body) for p in self._single_oracle)
                if not uses_oracle:
                    continue
                if self._multi_oracle.search(body):
                    continue
                if not self._stale_check.search(body):
                    findings.append(Finding(
                        id=_uid(), severity="high", vuln_type=self.vuln_type,
                        swc_id=self.swc_id, title="Stale Oracle Price (No Freshness Check)",
                        description=f"'{f.name}' reads oracle price without checking staleness (updatedAt / heartbeat).",
                        remediation="Validate oracle freshness: require(block.timestamp - updatedAt <= STALE_THRESHOLD). Use multiple oracles.",
                        contract_name=c.name, function_name=f.name,
                        line_number=f.line_start,
                        exploit_scenario="Oracle becomes stale during network congestion — contract uses outdated price for liquidations/swaps.",
                        exploit_complexity="medium",
                        real_world_exploits=[
                            {"protocol":"Venus Protocol","loss":"$200M","year":2021,"type":"Stale oracle / price manipulation"},
                        ],
                    ))
        return findings


class StateModificationDetector:
    name = "State Modification Detector"
    vuln_type = "unprotected-state-modification"
    swc_id = ""

    _selfdestruct = re.compile(r'selfdestruct\s*\(|suicide\s*\(')
    _delegatecall_var = re.compile(r'(\w+)\.delegatecall\s*\(')
    _immutable_override = re.compile(r'(immutable|constant)\s+\w+.*=(?!=)', re.I)

    def analyze(self, parsed: ParsedContract) -> list[Finding]:
        findings = []
        for c in parsed.contracts:
            for f in c.functions:
                body = f.body
                if self._selfdestruct.search(body):
                    is_guarded = any(g in f.modifiers for g in
                                     ["onlyOwner","onlyAdmin","onlyRole","restricted"])
                    has_require = bool(re.search(r'require\s*\([^)]*(?:owner|admin)', body, re.I))
                    if not is_guarded and not has_require:
                        findings.append(Finding(
                            id=_uid(), severity="critical", vuln_type=self.vuln_type,
                            swc_id="SWC-106", title="Unprotected SELFDESTRUCT",
                            description=f"'{f.name}' in '{c.name}' calls selfdestruct without access control.",
                            remediation="Add onlyOwner modifier. Consider removing selfdestruct entirely (deprecated in Cancun).",
                            contract_name=c.name, function_name=f.name,
                            line_number=f.line_start,
                            exploit_scenario="Anyone calls function → contract permanently destroyed, all ETH/tokens lost.",
                            exploit_complexity="low",
                        ))
                m = self._delegatecall_var.search(body)
                if m and m.group(1) not in ("this",):
                    is_hardcoded = bool(re.search(r'immutable|constant', body, re.I))
                    if not is_hardcoded:
                        findings.append(Finding(
                            id=_uid(), severity="critical", vuln_type=self.vuln_type,
                            swc_id="SWC-112", title="Delegatecall to Variable Address",
                            description=f"'{f.name}' uses delegatecall on a non-constant address.",
                            remediation="Only delegatecall to trusted, hardcoded implementation addresses. Use EIP-1967 pattern.",
                            contract_name=c.name, function_name=f.name,
                            line_number=f.line_start,
                            exploit_scenario="Attacker controls implementation address → delegatecall executes arbitrary code in storage context.",
                            exploit_complexity="low",
                        ))
        return findings


# ─────────────────────────── scanner ───────────────────────────────────────

DETECTORS = [
    ReentrancyDetector(),
    AccessControlDetector(),
    IntegerOverflowDetector(),
    FlashLoanDetector(),
    WeakRandomnessDetector(),
    TimestampDependenceDetector(),
    PrecisionLossDetector(),
    ArbitraryCallDetector(),
    StorageCollisionDetector(),
    OracleManipulationDetector(),
    StateModificationDetector(),
]

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


class SmartContractScanner:
    def __init__(self):
        self._parser = SolidityParser()

    def scan_file(self, path: str, on_progress=None) -> dict:
        if on_progress:
            on_progress(f"Parsing {path}...")
        parsed = self._parser.parse_file(path)
        return self._run(parsed, path=path, on_progress=on_progress)

    def scan_source(self, code: str, name: str = "Inline", on_progress=None) -> dict:
        if on_progress:
            on_progress(f"Parsing inline source '{name}'...")
        parsed = self._parser.parse_source(code, name)
        return self._run(parsed, on_progress=on_progress)

    def _run(self, parsed: ParsedContract, path: str = "", on_progress=None) -> dict:
        all_findings: list[Finding] = []
        for det in DETECTORS:
            if on_progress:
                on_progress(f"  [{det.name}]")
            try:
                all_findings.extend(det.analyze(parsed))
            except Exception as e:
                if on_progress:
                    on_progress(f"  WARNING: {det.name} failed — {e}")

        all_findings.sort(key=lambda f: SEVERITY_ORDER.get(f.severity, 9))

        src_hash = hashlib.sha256(parsed.source.encode()).hexdigest()[:12]
        counts = {s: 0 for s in SEVERITY_ORDER}
        for f in all_findings:
            counts[f.severity] = counts.get(f.severity, 0) + 1

        return {
            "contract": {
                "name": parsed.name,
                "path": path,
                "pragma": parsed.pragma,
                "source_hash": src_hash,
                "contract_count": len(parsed.contracts),
                "function_count": sum(len(c.functions) for c in parsed.contracts),
            },
            "summary": {
                "total": len(all_findings),
                "critical": counts.get("critical", 0),
                "high": counts.get("high", 0),
                "medium": counts.get("medium", 0),
                "low": counts.get("low", 0),
            },
            "findings": [
                {
                    "id": f.id,
                    "severity": f.severity,
                    "vuln_type": f.vuln_type,
                    "swc_id": f.swc_id,
                    "title": f.title,
                    "description": f.description,
                    "remediation": f.remediation,
                    "contract": f.contract_name,
                    "function": f.function_name,
                    "line": f.line_number,
                    "exploit_scenario": f.exploit_scenario,
                    "exploit_complexity": f.exploit_complexity,
                    "real_world_exploits": f.real_world_exploits,
                }
                for f in all_findings
            ],
            "parse_errors": [{"message": e.message, "line": e.line} for e in parsed.errors],
        }


# ─────────────────────────── CLI entry point ───────────────────────────────

def _sev_color(sev: str) -> str:
    return {"critical": "\033[91m", "high": "\033[93m",
            "medium": "\033[33m", "low": "\033[36m"}.get(sev, "\033[0m")

def _main():
    ap = argparse.ArgumentParser(description="ShadowCypher Smart Contract Scanner")
    ap.add_argument("target", help=".sol file to scan")
    ap.add_argument("--json", action="store_true", help="Output raw JSON")
    ap.add_argument("--min-severity", default="low",
                    choices=["critical","high","medium","low","info"])
    args = ap.parse_args()

    scanner = SmartContractScanner()
    result = scanner.scan_file(args.target, on_progress=lambda m: print(f"[*] {m}", flush=True))

    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return

    c = result["contract"]
    s = result["summary"]
    print(f"\n{'='*60}")
    print(f"  SHADOWCYPHER SMART CONTRACT AUDIT")
    print(f"  Contract : {c['name']}")
    print(f"  Pragma   : {c['pragma'] or 'unknown'}")
    print(f"  Hash     : {c['source_hash']}")
    print(f"  Contracts: {c['contract_count']}  Functions: {c['function_count']}")
    print(f"{'='*60}")
    print(f"  FINDINGS: {s['total']} total — "
          f"\033[91m{s['critical']} critical\033[0m  "
          f"\033[93m{s['high']} high\033[0m  "
          f"\033[33m{s['medium']} medium\033[0m  "
          f"\033[36m{s['low']} low\033[0m")
    print(f"{'='*60}\n")

    min_order = SEVERITY_ORDER.get(args.min_severity, 3)
    shown = [f for f in result["findings"] if SEVERITY_ORDER.get(f["severity"], 9) <= min_order]

    for f in shown:
        col = _sev_color(f["severity"])
        print(f"{col}[{f['severity'].upper():8s}]\033[0m  {f['title']}")
        print(f"           Contract : {f['contract']}  Function: {f['function'] or '—'}")
        if f["swc_id"]:
            print(f"           SWC      : {f['swc_id']}")
        print(f"           Line     : {f['line']}")
        print(f"           {f['description']}")
        if f.get("real_world_exploits"):
            for ex in f["real_world_exploits"][:2]:
                print(f"           ⚡ {ex['protocol']} ({ex.get('year','')}) — {ex.get('loss','')} — {ex.get('type','')}")
        print()

    if result.get("parse_errors"):
        print("\033[33m[PARSE WARNINGS]\033[0m")
        for e in result["parse_errors"]:
            print(f"  Line {e['line']}: {e['message']}")

if __name__ == "__main__":
    _main()
