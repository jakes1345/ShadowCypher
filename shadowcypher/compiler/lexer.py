import re
from typing import List


class Token:
    TYPE_KEYWORD    = "KEYWORD"
    TYPE_IDENTIFIER = "IDENTIFIER"
    TYPE_OPERATOR   = "OPERATOR"
    TYPE_STRING     = "STRING"
    TYPE_NUMBER     = "NUMBER"
    TYPE_BRACE      = "BRACE"

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
    }

    def tokenize(self, code: str) -> List[Token]:
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
