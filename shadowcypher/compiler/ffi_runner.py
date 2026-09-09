"""
ShadowScript FFI runner — compiles and executes native language blocks.

Protocol: JSON string written to binary's stdin, JSON string read from stdout.
Isolation: every call is a subprocess — a crash or segfault kills the child,
           not the ShadowScript runtime.
Cache: binaries are cached by source hash under ~/.shadowcypher/native_cache/
       so compilation only happens once per unique source block.
"""

import hashlib
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple

CACHE_DIR = Path.home() / ".shadowcypher" / "native_cache"
COMPILE_TIMEOUT = 120  # seconds — Rust cold builds can be slow
CALL_TIMEOUT    = 60   # seconds — per native invocation


# ── helpers ──────────────────────────────────────────────────────────────────

def _cache_key(lang: str, source: str) -> str:
    return hashlib.sha256(f"{lang}:{source}".encode()).hexdigest()[:20]


# ── public API ────────────────────────────────────────────────────────────────

def compile_native(lang: str, name: str, source: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Compile a native language block.
    Returns (binary_path, error). binary_path is None on failure.

    The source must be a complete program (has a main() / func main() / int main())
    that reads JSON from stdin and writes JSON to stdout.
    """
    key = _cache_key(lang, source)
    cache_dir = CACHE_DIR / key
    binary_path = cache_dir / "shadow_native"

    if binary_path.exists():
        return str(binary_path), None

    cache_dir.mkdir(parents=True, exist_ok=True)

    compilers = {"rust": _compile_rust, "go": _compile_go, "cpp": _compile_cpp}
    fn = compilers.get(lang)
    if fn is None:
        return None, f"unsupported language: {lang!r} — supported: rust, go, cpp"
    return fn(source, cache_dir, binary_path)


def call_native(binary_path: str, args_json: str) -> Tuple[str, Optional[str]]:
    """
    Call a compiled native binary via subprocess.
    Sends args_json to stdin; returns (stdout, error).
    A non-zero exit code or timeout returns ("", error_message).
    A crash in the binary does not propagate — the subprocess absorbs it.
    """
    if not os.path.isfile(binary_path):
        return "", f"binary not found: {binary_path}"

    try:
        proc = subprocess.run(
            [binary_path],
            input=args_json,
            capture_output=True,
            text=True,
            timeout=CALL_TIMEOUT,
        )
        if proc.returncode != 0:
            stderr = (proc.stderr or "").strip()
            return "", f"exit {proc.returncode}: {stderr[:500]}"
        return proc.stdout.strip(), None

    except subprocess.TimeoutExpired:
        return "", f"call timed out after {CALL_TIMEOUT}s"
    except FileNotFoundError:
        return "", f"binary not executable: {binary_path}"
    except OSError as e:
        return "", f"OS error: {e}"


# ── language compilers ────────────────────────────────────────────────────────

def _compile_rust(source: str, cache_dir: Path, binary_path: Path) -> Tuple[Optional[str], Optional[str]]:
    # Minimal Cargo workspace — serde_json for JSON i/o
    cargo_toml = (
        '[package]\n'
        'name = "shadow_native"\n'
        'version = "0.1.0"\n'
        'edition = "2021"\n\n'
        '[[bin]]\n'
        'name = "shadow_native"\n'
        'path = "src/main.rs"\n\n'
        '[dependencies]\n'
        'serde_json = "1"\n'
    )
    src_dir = cache_dir / "src"
    src_dir.mkdir(exist_ok=True)
    (cache_dir / "Cargo.toml").write_text(cargo_toml)
    (src_dir / "main.rs").write_text(source)

    try:
        result = subprocess.run(
            ["cargo", "build", "--release",
             "--manifest-path", str(cache_dir / "Cargo.toml")],
            capture_output=True, text=True, timeout=COMPILE_TIMEOUT,
            cwd=str(cache_dir),
        )
        built = cache_dir / "target" / "release" / "shadow_native"
        if built.exists():
            shutil.copy(str(built), str(binary_path))
            return str(binary_path), None
        err = (result.stderr or result.stdout or "").strip()
        return None, f"cargo build failed:\n{err[-2000:]}"
    except FileNotFoundError:
        return None, "cargo not found — install Rust: rustup.rs"
    except subprocess.TimeoutExpired:
        return None, f"Rust compilation timed out after {COMPILE_TIMEOUT}s"


def _compile_go(source: str, cache_dir: Path, binary_path: Path) -> Tuple[Optional[str], Optional[str]]:
    main_file = cache_dir / "main.go"
    main_file.write_text(source)
    try:
        result = subprocess.run(
            ["go", "build", "-o", str(binary_path), str(main_file)],
            capture_output=True, text=True, timeout=COMPILE_TIMEOUT,
        )
        if binary_path.exists():
            return str(binary_path), None
        err = (result.stderr or "").strip()
        return None, f"go build failed:\n{err[-2000:]}"
    except FileNotFoundError:
        return None, "go not found — install Go: go.dev/dl/"
    except subprocess.TimeoutExpired:
        return None, f"Go compilation timed out after {COMPILE_TIMEOUT}s"


def _compile_cpp(source: str, cache_dir: Path, binary_path: Path) -> Tuple[Optional[str], Optional[str]]:
    src_file = cache_dir / "main.cpp"
    src_file.write_text(source)
    try:
        result = subprocess.run(
            ["g++", "-O2", "-std=c++17", "-o", str(binary_path), str(src_file)],
            capture_output=True, text=True, timeout=COMPILE_TIMEOUT,
        )
        if binary_path.exists():
            return str(binary_path), None
        err = (result.stderr or "").strip()
        return None, f"g++ failed:\n{err[-2000:]}"
    except FileNotFoundError:
        return None, "g++ not found — install build-essential or base-devel"
    except subprocess.TimeoutExpired:
        return None, f"C++ compilation timed out after {COMPILE_TIMEOUT}s"
