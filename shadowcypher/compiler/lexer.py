import re
from typing import List, Tuple

class Token:
    """The smallest unit of the Shadow-Language."""
    TYPE_KEYWORD = "KEYWORD"
    TYPE_IDENTIFIER = "IDENTIFIER"
    TYPE_OPERATOR = "OPERATOR"
    TYPE_STRING = "STRING"
    TYPE_NUMBER = "NUMBER"
    TYPE_BRACE = "BRACE"

    def __init__(self, ttype, value):
        self.ttype = ttype
        self.value = value

    def __repr__(self):
        return f"Token({self.ttype}, '{self.value}')"

class ShadowLexer:
    """Scans raw text and generates tactical tokens for the Omni-Language."""
    
    KEYWORDS = {
        "SWARM", "STRIKE", "TARGET", "AI", "VAR", "IF", "FOR", "UNSAFE",
        "U64", "U32", "U8", "VOID", "MAP", "FILTER", "YIELD"
    }
    REGISTERS = {"RAX", "RBX", "RCX", "RDX", "RSP", "RBP", "RIP"}
    OPERATORS = {"=", "->", "|", "+", "-", "*", "/", "&", "!", "=="}
    
    def tokenize(self, code: str) -> List[Token]:
        tokens = []
        token_specification = [
            ('NUMBER',   r'0x[0-9A-Fa-f]+|\d+(\.\d*)?'), # hex and decimal
            ('STRING',   r'\'[^\']*\'|\"[^\"]*\"'), 
            ('KEYWORD',  r'[A-Z][A-Z0-9_]*'), 
            ('ID',       r'[a-z][a-z0-9_]*'), 
            ('SYSCALL',  r'![a-z_]+'), # !sys !ai
            ('OP',       r'[=\-\+\*\/\|&!]{1,2}|->'), 
            ('BRACE',    r'[\(\)\{\}\[\]]'), 
            ('SKIP',     r'[ \t\n]+'), 
            ('MISMATCH', r'.'), 
        ]
        
        tok_regex = '|'.join('(?P<%s>%s)' % pair for pair in token_specification)
        
        for mo in re.finditer(tok_regex, code):
            kind = mo.lastgroup
            value = mo.group()
            if kind == 'NUMBER':
                tokens.append(Token(Token.TYPE_NUMBER, value))
            elif kind == 'STRING':
                tokens.append(Token(Token.TYPE_STRING, value.strip("'\"")))
            elif kind == 'KEYWORD':
                if value in self.KEYWORDS:
                    tokens.append(Token(Token.TYPE_KEYWORD, value))
                elif value in self.REGISTERS:
                    tokens.append(Token(Token.TYPE_KEYWORD, f"REG_{value}"))
                else:
                    tokens.append(Token(Token.TYPE_IDENTIFIER, value))
            elif kind == 'SYSCALL':
                tokens.append(Token(Token.TYPE_KEYWORD, value))
            elif kind == 'ID':
                tokens.append(Token(Token.TYPE_IDENTIFIER, value))
            elif kind == 'OP':
                tokens.append(Token(Token.TYPE_OPERATOR, value))
            elif kind == 'BRACE':
                tokens.append(Token(Token.TYPE_BRACE, value))
            elif kind == 'SKIP':
                continue
            elif kind == 'MISMATCH':
                # Ignore for now or log error
                pass
                
        return tokens

# Tactical Test Entry
if __name__ == "__main__":
    lexer = ShadowLexer()
    code = "VAR target = '127.0.0.1' -> SWARM { STRIKE(target) }"
    tokens = lexer.tokenize(code)
    for t in tokens:
        print(t)
