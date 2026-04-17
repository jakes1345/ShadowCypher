import sys
from shadowcypher.compiler.lexer import ShadowLexer, Token
from shadowcypher.core.logger import logger

class ShadowRuntime:
    """The Sovereign Environment where ShadowCypher lives."""
    def __init__(self):
        self.variables = {}
        self.swarm_active = False

    def execute_directive(self, cmd, args):
        if cmd == "TARGET":
            self.variables["CURRENT_TARGET"] = args[0]
            logger.info("shadow_core", f"TARGET_ACQUIRED: {args[0]}")
        elif cmd == "STRIKE":
            target = self.variables.get("CURRENT_TARGET", "UNKNOWN")
            logger.info("shadow_core", f"STRIKE_INITIATED on {target} with mod: {args}")
        elif cmd == "SWARM":
            self.swarm_active = True
            logger.info("shadow_core", "SWARM_MODE: SYNCHRONIZING_NODES")
        elif cmd == "UNSAFE":
            logger.warning("shadow_core", "UNSAFE_BLOCK_DETECTION: Entering Raw Memory Sovereignty...")
        elif cmd == "!sys":
            import os
            os.system(args[0])

class ShadowInterpreter:
    """The Engine that breathes life into .shadow scripts."""
    def __init__(self):
        self.lexer = ShadowLexer()
        self.runtime = ShadowRuntime()

    def run(self, code: str):
        tokens = self.lexer.tokenize(code)
        logger.info("shadow_core", f"INGESTING_MISSION_SIGNAL: {len(tokens)} tokens")
        
        # Primitive "Soul" of the language: Directive Execution
        ptr = 0
        while ptr < len(tokens):
            token = tokens[ptr]
            
            if token.ttype == Token.TYPE_KEYWORD:
                if token.value == "VAR":
                    name = tokens[ptr+1].value
                    val = tokens[ptr+3].value
                    self.runtime.variables[name] = val
                    ptr += 4
                elif token.value in ["U64", "U32", "U8"]:
                    # HolyC Type System
                    typename = token.value
                    name = tokens[ptr+1].value
                    val = tokens[ptr+3].value
                    self.runtime.variables[name] = {"type": typename, "value": val}
                    logger.info("shadow_core", f"TYPE_ALLOCATION: {typename} {name} = {val}")
                    ptr += 4
                elif token.value == "AI":
                    # Neural Link Directive: AI "query"
                    if ptr+2 < len(tokens):
                        prompt = tokens[ptr+2].value
                        logger.info("shadow_core", f"NEURAL_LINK_INITIATED: Querying Shadow-AI...")
                        from shadowcypher.ai.orchestrator import AIOrchestrator
                        orch = AIOrchestrator()
                        result = orch.execute_sync(prompt)
                        print(f"\033[1;34m[SHADOW-AI]> {result}\033[0m")
                        ptr += 3
                    else:
                        logger.error("shadow_core", "MALFORMED_AI_DIRECTIVE: Missing prompt.")
                        ptr += 1
                elif token.value in ["STRIKE", "TARGET", "SWARM", "UNSAFE", "!sys"]:
                    # Simple directive execution
                    cmd = token.value
                    args = []
                    if ptr+1 < len(tokens) and tokens[ptr+1].ttype == Token.TYPE_BRACE and tokens[ptr+1].value == "(":
                        # Handle args inside ()
                        ptr += 2
                        while tokens[ptr].value != ")":
                            args.append(tokens[ptr].value)
                            ptr += 1
                    self.runtime.execute_directive(cmd, args)
            
            ptr += 1

if __name__ == "__main__":
    interpreter = ShadowInterpreter()
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            interpreter.run(f.read())
    else:
        # Interactive "Shadow-Shell" could go here
        pass
