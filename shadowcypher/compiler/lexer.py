import re
from typing import Dict, List, Tuple


class Token:
    TYPE_KEYWORD    = "KEYWORD"
    TYPE_IDENTIFIER = "IDENTIFIER"
    TYPE_OPERATOR   = "OPERATOR"
    TYPE_STRING     = "STRING"
    TYPE_NUMBER     = "NUMBER"
    TYPE_BRACE      = "BRACE"
    TYPE_LANGBLOCK  = "LANGBLOCK"   # native language block: rust/go/cpp { ... }

    def __init__(self, ttype, value):
        self.ttype = ttype
        self.value = value

    def __repr__(self):
        return f"Token({self.ttype}, {self.value!r})"


class ShadowLexer:
    """Tokeniser for ShadowScript — ShadowCypher's native tactical DSL."""

    KEYWORDS = {
        # Control flow
        "IF", "ELSE", "FOR", "WHILE", "RETURN", "BREAK",
        # Directives
        "TARGET", "STRIKE", "SWARM", "AI", "SCAN", "LOAD",
        # Data
        "VAR", "SET",
        # Modifiers
        "UNSAFE", "ASYNC", "AWAIT",
        # Functional
        "MAP", "FILTER", "YIELD",
        # Loop helper
        "IN",
        # Import/export
        "IMPORT", "EXPORT",
        # Block terminator
        "END",
    }

    # Lowercase language names that introduce native blocks
    _LANG_NAMES = {"rust", "go", "cpp"}

    # ── native block pre-processor ────────────────────────────────────────────

    def _extract_lang_blocks(self, code: str) -> Tuple[str, Dict[int, dict]]:
        """
        Pre-scan source for  rust/go/cpp <name> { ... }  blocks.
        Extracts raw source (brace-matched), replaces each block with a
        placeholder token SHADOWLANGBLK<N> so the main regex tokeniser never
        sees the raw C++/Rust/Go source (which would confuse it with its own
        operators and strings).

        Returns (modified_code, {index: {"lang":…, "name":…, "source":…}}).

        Variable injection: every $VAR reference in the native source is
        replaced with its value at parse-time so the native block can read
        ShadowScript state.  (Write-back uses the SHADOWVAR: stdout protocol.)
        """
        pattern = re.compile(
            r'\b(rust|go|cpp)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{',
            re.MULTILINE,
        )
        blocks: Dict[int, dict] = {}
        parts:  List[str]       = []
        last_end = 0

        for m in pattern.finditer(code):
            lang = m.group(1)
            name = m.group(2)
            open_brace = m.end() - 1  # index of the opening {

            # Brace-match to find the closing }
            depth = 0
            i = open_brace
            while i < len(code):
                if code[i] == '{':
                    depth += 1
                elif code[i] == '}':
                    depth -= 1
                    if depth == 0:
                        break
                i += 1

            source = code[open_brace + 1:i].strip()
            idx = len(blocks)
            blocks[idx] = {"lang": lang, "name": name, "source": source}

            parts.append(code[last_end:m.start()])
            parts.append(f" SHADOWLANGBLK{idx} ")
            last_end = i + 1

        parts.append(code[last_end:])
        return "".join(parts), blocks

    # ── main tokeniser ────────────────────────────────────────────────────────

    def tokenize(self, code: str) -> List[Token]:
        code, lang_blocks = self._extract_lang_blocks(code)

        tokens: List[Token] = []
        token_spec = [
            ("COMMENT",  r"#[^\n]*"),
            ("NUMBER",   r"0x[0-9A-Fa-f]+|\d+(\.\d*)?"),
            ("STRING",   r"'[^']*'|\"[^\"]*\""),
            ("VARREF",   r"\$[A-Za-z_][A-Za-z0-9_]*"),  # $varname — preserved as-is
            ("SYSCALL",  r"![a-z_]+"),
            # Keywords must be ALL-CAPS to avoid clashing with user variable names
            ("KEYWORD",  r"[A-Z][A-Z0-9_]+"),
            ("WORD",     r"[A-Za-z_][A-Za-z0-9_]*"),
            ("OP",       r"==|!=|>=|<=|->|[=\+\-\*\/\|&<>]"),
            ("BRACE",    r"[\(\)\{\}\[\]]"),
            ("COMMA",    r","),
            ("SKIP",     r"[ \t\n\r]+"),
            ("MISMATCH", r"."),
        ]
        tok_re = "|".join(f"(?P<{name}>{pat})" for name, pat in token_spec)

        for mo in re.finditer(tok_re, code):
            kind  = mo.lastgroup
            value = mo.group()

            if kind in ("SKIP", "COMMENT", "MISMATCH"):
                continue
            elif kind == "NUMBER":
                tokens.append(Token(Token.TYPE_NUMBER, value))
            elif kind == "STRING":
                tokens.append(Token(Token.TYPE_STRING, value[1:-1]))
            elif kind == "VARREF":
                # Store as STRING with the $name value so resolve_var picks it up
                tokens.append(Token(Token.TYPE_STRING, value))
            elif kind == "SYSCALL":
                tokens.append(Token(Token.TYPE_KEYWORD, value))
            elif kind == "KEYWORD":
                # Check for SHADOWLANGBLK<N> placeholders first
                if value.startswith("SHADOWLANGBLK"):
                    try:
                        idx = int(value[len("SHADOWLANGBLK"):])
                        tokens.append(Token(Token.TYPE_LANGBLOCK, lang_blocks[idx]))
                        continue
                    except (ValueError, KeyError):
                        pass
                if value in self.KEYWORDS:
                    tokens.append(Token(Token.TYPE_KEYWORD, value))
                else:
                    tokens.append(Token(Token.TYPE_IDENTIFIER, value))
            elif kind == "WORD":
                tokens.append(Token(Token.TYPE_IDENTIFIER, value))
            elif kind == "OP":
                tokens.append(Token(Token.TYPE_OPERATOR, value))
            elif kind in ("BRACE", "COMMA"):
                tokens.append(Token(Token.TYPE_BRACE, value))

        return tokens


if __name__ == "__main__":
    lexer = ShadowLexer()
    src = 'VAR target = "192.168.1.1"\nTARGET($target)\nIF $target == "192.168.1.1" { !echo("confirmed") }'
    for tok in lexer.tokenize(src):
        print(tok)
