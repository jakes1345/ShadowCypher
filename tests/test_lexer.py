"""
ShadowCypher Test Suite — ShadowScript Lexer
Tests tokenization of keywords, identifiers, literals, operators,
and full expression parsing. No mocking needed — pure function.
"""

import pytest
from shadowcypher.compiler.lexer import ShadowLexer, Token


@pytest.fixture
def lexer():
    return ShadowLexer()


def token_values(tokens):
    return [(t.ttype, t.value) for t in tokens]


class TestKeywords:

    @pytest.mark.parametrize("kw", [
        "VAR", "SWARM", "STRIKE", "TARGET", "AI", "IF", "FOR",
        "WHILE", "RETURN", "IMPORT", "EXPORT", "ASYNC", "AWAIT",
        "UNSAFE", "VOID", "MAP", "FILTER", "YIELD",
    ])
    def test_keyword_tokenized(self, lexer, kw):
        tokens = lexer.tokenize(kw)
        assert len(tokens) == 1
        assert tokens[0].ttype == Token.TYPE_KEYWORD
        assert tokens[0].value == kw

    def test_register_rax_becomes_reg_rax(self, lexer):
        tokens = lexer.tokenize("RAX")
        assert tokens[0].ttype == Token.TYPE_KEYWORD
        assert tokens[0].value == "REG_RAX"

    def test_register_rbx_becomes_reg_rbx(self, lexer):
        tokens = lexer.tokenize("RBX")
        assert tokens[0].value == "REG_RBX"

    @pytest.mark.parametrize("reg", ["RAX", "RBX", "RCX", "RDX", "RSP", "RBP", "RIP"])
    def test_all_registers_get_prefix(self, lexer, reg):
        tokens = lexer.tokenize(reg)
        assert tokens[0].value == f"REG_{reg}"

    def test_unknown_uppercase_becomes_identifier(self, lexer):
        tokens = lexer.tokenize("FOOBAR")
        assert tokens[0].ttype == Token.TYPE_IDENTIFIER
        assert tokens[0].value == "FOOBAR"


class TestIdentifiers:

    def test_lowercase_word_is_identifier(self, lexer):
        tokens = lexer.tokenize("target")
        assert tokens[0].ttype == Token.TYPE_IDENTIFIER
        assert tokens[0].value == "target"

    def test_lowercase_with_numbers(self, lexer):
        tokens = lexer.tokenize("host01")
        assert tokens[0].ttype == Token.TYPE_IDENTIFIER

    def test_lowercase_with_underscore(self, lexer):
        tokens = lexer.tokenize("my_var")
        assert tokens[0].ttype == Token.TYPE_IDENTIFIER


class TestStringLiterals:

    def test_single_quoted_string(self, lexer):
        tokens = lexer.tokenize("'hello world'")
        assert tokens[0].ttype == Token.TYPE_STRING
        assert tokens[0].value == "hello world"

    def test_double_quoted_string(self, lexer):
        tokens = lexer.tokenize('"127.0.0.1"')
        assert tokens[0].ttype == Token.TYPE_STRING
        assert tokens[0].value == "127.0.0.1"

    def test_ip_in_string(self, lexer):
        tokens = lexer.tokenize("'192.168.1.100'")
        assert tokens[0].value == "192.168.1.100"

    def test_empty_string(self, lexer):
        tokens = lexer.tokenize("''")
        assert tokens[0].ttype == Token.TYPE_STRING
        assert tokens[0].value == ""


class TestNumbers:

    def test_decimal_integer(self, lexer):
        tokens = lexer.tokenize("42")
        assert tokens[0].ttype == Token.TYPE_NUMBER
        assert tokens[0].value == "42"

    def test_hex_number(self, lexer):
        tokens = lexer.tokenize("0xFF")
        assert tokens[0].ttype == Token.TYPE_NUMBER
        assert tokens[0].value == "0xFF"

    def test_hex_lowercase(self, lexer):
        tokens = lexer.tokenize("0x1a2b")
        assert tokens[0].ttype == Token.TYPE_NUMBER

    def test_float_number(self, lexer):
        tokens = lexer.tokenize("3.14")
        assert tokens[0].ttype == Token.TYPE_NUMBER


class TestOperators:

    @pytest.mark.parametrize("op", ["=", "->", "|", "+", "-", "*", "/", "&", "==", "!="])
    def test_operator_tokenized(self, lexer, op):
        tokens = lexer.tokenize(op)
        assert len(tokens) == 1
        assert tokens[0].ttype == Token.TYPE_OPERATOR

    def test_arrow_operator(self, lexer):
        tokens = lexer.tokenize("->")
        assert tokens[0].value == "->"

    def test_equality_operator(self, lexer):
        tokens = lexer.tokenize("==")
        assert tokens[0].value == "=="


class TestBraces:

    @pytest.mark.parametrize("brace", ["(", ")", "{", "}", "[", "]"])
    def test_brace_tokenized(self, lexer, brace):
        tokens = lexer.tokenize(brace)
        assert tokens[0].ttype == Token.TYPE_BRACE

    def test_nested_braces(self, lexer):
        tokens = lexer.tokenize("{()}")
        assert len(tokens) == 4
        assert all(t.ttype == Token.TYPE_BRACE for t in tokens)


class TestSyscalls:

    def test_syscall_ai(self, lexer):
        tokens = lexer.tokenize("!ai")
        assert tokens[0].ttype == Token.TYPE_KEYWORD
        assert tokens[0].value == "!ai"

    def test_syscall_sys(self, lexer):
        tokens = lexer.tokenize("!sys")
        assert tokens[0].ttype == Token.TYPE_KEYWORD


class TestWhitespaceHandling:

    def test_spaces_skipped(self, lexer):
        tokens = lexer.tokenize("VAR   target")
        assert len(tokens) == 2

    def test_newlines_skipped(self, lexer):
        tokens = lexer.tokenize("VAR\ntarget")
        assert len(tokens) == 2

    def test_empty_input_returns_empty_list(self, lexer):
        assert lexer.tokenize("") == []

    def test_whitespace_only_returns_empty(self, lexer):
        assert lexer.tokenize("   \n\t  ") == []


class TestFullExpression:

    def test_canonical_expression(self, lexer):
        code = "VAR target = '127.0.0.1' -> SWARM { STRIKE(target) }"
        tokens = lexer.tokenize(code)
        ttypes = [t.ttype for t in tokens]
        values = [t.value for t in tokens]

        assert Token.TYPE_KEYWORD in ttypes   # VAR, SWARM, STRIKE
        assert Token.TYPE_IDENTIFIER in ttypes  # target
        assert Token.TYPE_STRING in ttypes     # '127.0.0.1'
        assert Token.TYPE_OPERATOR in ttypes   # =, ->
        assert Token.TYPE_BRACE in ttypes      # {, (, ), }

        assert "VAR" in values
        assert "127.0.0.1" in values
        assert "SWARM" in values

    def test_token_count_reasonable(self, lexer):
        code = "VAR x = 42"
        tokens = lexer.tokenize(code)
        # VAR, x, =, 42 → 4 tokens
        assert len(tokens) == 4
