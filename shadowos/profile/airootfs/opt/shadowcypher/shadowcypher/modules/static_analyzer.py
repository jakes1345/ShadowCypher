"""
Tree-Sitter Static Code Analyzer (T2-2).
Uses tree-sitter ASTs to scan source code for vulnerability patterns:
hardcoded creds, SQL injection, dangerous eval/exec, system() with user input,
weak crypto, path traversal, command injection.

Works on: Python, JavaScript, Go, C (any language with a tree-sitter grammar).
"""
import os, re
from typing import Callable
from shadowcypher.core.logger import logger

try:
    import tree_sitter
    from tree_sitter import Language, Parser
    HAS_TS = True
except ImportError:
    HAS_TS = False


# ── Regex-based fallback patterns (used when tree-sitter grammar unavailable) ──
_VULN_PATTERNS = {
    "hardcoded_password": [
        (r'(?i)(password|passwd|pwd|secret|api_?key|auth_?token)\s*=\s*["\'][^"\']{4,}["\']', "HIGH"),
        (r'(?i)Authorization:\s*Bearer\s+\S{10,}', "HIGH"),
    ],
    "sql_injection": [
        (r'(?i)(execute|query|cursor\.execute)\s*\(\s*["\'].*%s.*["\']', "CRITICAL"),
        (r'(?i)f["\'].*SELECT.*\{', "CRITICAL"),
        (r'(?i)"SELECT.*"\s*\+', "HIGH"),
        (r'(?i)\.format\(.*\)\s*#.*sql', "HIGH"),
    ],
    "command_injection": [
        (r'(?i)(os\.system|subprocess\.call|subprocess\.run|popen)\s*\([^)]*\+', "CRITICAL"),
        (r'(?i)eval\s*\(.*input\s*\(', "CRITICAL"),
        (r'(?i)exec\s*\(.*request\.(get|post|args)', "CRITICAL"),
    ],
    "path_traversal": [
        (r'(?i)open\s*\([^)]*\+', "HIGH"),
        (r'(?i)(os\.path\.join|open)\s*\([^)]*request\.(get|post|args)', "HIGH"),
        (r'\.\./|\.\.\/', "MEDIUM"),
    ],
    "weak_crypto": [
        (r'(?i)\b(md5|sha1)\s*\(', "MEDIUM"),
        (r'(?i)hashlib\.(md5|sha1)\s*\(', "MEDIUM"),
        (r'(?i)DES\s*\(|RC4\s*\(|ECB\s*mode', "HIGH"),
        (r'(?i)random\.random\(\)|random\.randint', "LOW"),  # not crypto-safe
    ],
    "dangerous_deserialization": [
        (r'(?i)pickle\.loads?\s*\(', "CRITICAL"),
        (r'(?i)yaml\.load\s*\([^)]*(?!Loader=yaml\.SafeLoader)', "HIGH"),
        (r'(?i)json\.loads?\s*\(.*user', "MEDIUM"),
    ],
    "debug_exposure": [
        (r'(?i)DEBUG\s*=\s*True', "MEDIUM"),
        (r'(?i)app\.run\s*\(.*debug\s*=\s*True', "HIGH"),
        (r'(?i)print\s*\(.*password|print\s*\(.*secret|print\s*\(.*token', "MEDIUM"),
    ],
    "hardcoded_ip": [
        (r'\b(?:192\.168|10\.\d+|172\.(?:1[6-9]|2\d|3[01]))\.\d+\.\d+\b', "LOW"),
    ],
}


class Finding:
    def __init__(self, vuln_type: str, severity: str, file_path: str,
                 line: int, col: int, snippet: str, match: str = ""):
        self.vuln_type = vuln_type
        self.severity = severity
        self.file_path = file_path
        self.line = line
        self.col = col
        self.snippet = snippet.strip()[:200]
        self.match = match

    def __str__(self) -> str:
        return (f"  [{self.severity:8s}] {self.vuln_type}\n"
                f"             {self.file_path}:{self.line}:{self.col}\n"
                f"             {self.snippet}\n")


class StaticAnalyzer:
    """
    Multi-language static vulnerability analyzer.
    Uses tree-sitter for precise AST analysis where grammars are available,
    falls back to regex scanning for maximum language coverage.
    """

    def __init__(self):
        self._parsers: dict = {}
        if HAS_TS:
            self._init_ts_parsers()

    def _init_ts_parsers(self):
        """Try to load tree-sitter language grammars."""
        grammar_map = {
            "python": "tree_sitter_python",
            "javascript": "tree_sitter_javascript",
            "go": "tree_sitter_go",
            "c": "tree_sitter_c",
        }
        for lang, module in grammar_map.items():
            try:
                mod = __import__(module)
                lang_obj = Language(mod.language())
                parser = Parser(lang_obj)
                self._parsers[lang] = parser
                logger.info("static_analyzer", f"Tree-sitter grammar loaded: {lang}")
            except Exception:
                pass  # Grammar not installed — regex fallback handles it

    # ── Public API ────────────────────────────────────────────────────────────

    def scan_file(self, path: str, on_output: Callable = None) -> list[Finding]:
        """Scan a single file for vulnerabilities."""
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            if on_output: on_output(f"[SA] Cannot read {path}: {e}\n")
            return []

        lang = self._detect_language(path)
        findings = self._regex_scan(content, path, lang)

        if HAS_TS and lang in self._parsers:
            findings += self._ast_scan(content, path, lang)

        # Deduplicate by (type, line)
        seen = set()
        unique = []
        for f in findings:
            key = (f.vuln_type, f.line)
            if key not in seen:
                seen.add(key); unique.append(f)

        unique.sort(key=lambda x: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}.get(x.severity, 4))

        if on_output and unique:
            on_output(f"[SA] {path} → {len(unique)} finding(s)\n")
            for f in unique:
                on_output(str(f))

        return unique

    def scan_directory(self, directory: str, extensions: list = None,
                       on_output: Callable = None) -> dict:
        """Scan all source files in a directory recursively."""
        exts = set(extensions or [".py", ".js", ".ts", ".go", ".c", ".cpp",
                                   ".php", ".rb", ".java"])
        all_findings: list[Finding] = []
        file_count = 0

        if on_output:
            on_output(f"[SA] Scanning: {directory}\n")

        for root, _, files in os.walk(directory):
            # Skip common junk dirs
            if any(skip in root for skip in
                   [".git", "__pycache__", "node_modules", ".venv", "dist", "build"]):
                continue
            for fname in files:
                if any(fname.endswith(e) for e in exts):
                    path = os.path.join(root, fname)
                    findings = self.scan_file(path, on_output=None)
                    all_findings.extend(findings)
                    file_count += 1

        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for f in all_findings:
            severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1

        if on_output:
            on_output(f"\n[SA] SCAN COMPLETE: {file_count} files, "
                      f"{len(all_findings)} total findings\n")
            on_output(f"[SA] CRITICAL:{severity_counts['CRITICAL']} "
                      f"HIGH:{severity_counts['HIGH']} "
                      f"MEDIUM:{severity_counts['MEDIUM']} "
                      f"LOW:{severity_counts['LOW']}\n")
            crits = [f for f in all_findings if f.severity == "CRITICAL"]
            if crits:
                on_output("\n[SA] ⚠️  CRITICAL FINDINGS:\n")
                for f in crits[:10]:
                    on_output(str(f))

        return {
            "files_scanned": file_count,
            "total_findings": len(all_findings),
            "severity_counts": severity_counts,
            "findings": all_findings,
        }

    # ── Regex Scanner ─────────────────────────────────────────────────────────

    def _regex_scan(self, content: str, path: str, lang: str) -> list[Finding]:
        findings = []
        lines = content.splitlines()
        for vuln_type, patterns in _VULN_PATTERNS.items():
            for pattern, severity in patterns:
                for match in re.finditer(pattern, content, re.MULTILINE):
                    line_no = content[:match.start()].count("\n") + 1
                    col = match.start() - content[:match.start()].rfind("\n") - 1
                    snippet = lines[line_no - 1] if line_no <= len(lines) else ""
                    findings.append(Finding(
                        vuln_type=vuln_type, severity=severity,
                        file_path=path, line=line_no, col=col,
                        snippet=snippet, match=match.group(0)[:80]
                    ))
        return findings

    # ── AST Scanner (tree-sitter) ─────────────────────────────────────────────

    def _ast_scan(self, content: str, path: str, lang: str) -> list[Finding]:
        """Deep AST-level analysis — finds patterns regex can't."""
        findings = []
        parser = self._parsers.get(lang)
        if not parser:
            return []
        try:
            tree = parser.parse(content.encode())
            # Query for dangerous function calls
            findings += self._query_dangerous_calls(tree, content, path, lang)
        except Exception as e:
            logger.debug("static_analyzer", f"AST scan error {path}: {e}")
        return findings

    def _query_dangerous_calls(self, tree, content: str, path: str,
                                lang: str) -> list[Finding]:
        """Walk AST nodes looking for dangerous call patterns."""
        findings = []
        lines = content.splitlines()
        danger_funcs = {"eval", "exec", "compile", "pickle.loads", "yaml.load",
                        "os.system", "subprocess.call", "popen", "__import__"}

        def walk(node):
            if node.type in ("call", "call_expression"):
                func_text = content[node.start_byte:node.end_byte][:60]
                for df in danger_funcs:
                    if df in func_text:
                        ln = node.start_point[0] + 1
                        snippet = lines[ln - 1] if ln <= len(lines) else ""
                        sev = "CRITICAL" if df in {"eval", "exec", "pickle.loads",
                                                    "os.system"} else "HIGH"
                        findings.append(Finding(
                            vuln_type="dangerous_call", severity=sev,
                            file_path=path, line=ln, col=node.start_point[1],
                            snippet=snippet, match=df
                        ))
            for child in node.children:
                walk(child)

        walk(tree.root_node)
        return findings

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _detect_language(path: str) -> str:
        ext = os.path.splitext(path)[1].lower()
        return {
            ".py": "python", ".js": "javascript", ".ts": "javascript",
            ".go": "go", ".c": "c", ".cpp": "c", ".php": "php",
            ".rb": "ruby", ".java": "java", ".sh": "bash",
        }.get(ext, "unknown")


static_analyzer = StaticAnalyzer()
