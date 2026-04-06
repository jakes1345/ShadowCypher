"""ShadowCypher AI Orchestrator — DeepHat Autonomous Agent Subsystem.
Fully weaponized ReAct (Reason + Act) loop allowing the local LLM to execute
shell commands, search GitHub, and write files dynamically.
"""

import requests
import json
import os
import re
import subprocess
from shadowcypher.core.logger import logger

class AIOrchestrator:
    """The 'Brain' of the suite. Orchestrates DeepHat-V1-7B as an active Agent."""
    def __init__(self, model="DeepHat-V1-7B:latest"):
        self.model = model
        self.base_url = "http://localhost:11434/api/generate"
        self.payload_dir = "payloads"
        os.makedirs(self.payload_dir, exist_ok=True)

    def execute_query(self, query, callback=None, agent_role="commander"):
        """Execute a query using an autonomous ReAct loop with Subagent support."""
        logger.info("ai", f"DeepHat Query [{agent_role}]: {query}")
        
        roles = {
            "commander": "You are the COMMANDER AI. You oversee the mission. You can use tools and DELEGATE complex tasks to subagents ('recon' or 'coder').",
            "recon": "You are the RECON SUBAGENT. You focus solely on intelligence gathering, finding open ports, and searching github.",
            "coder": "You are the CODER SUBAGENT. You focus entirely on writing tight, flawless exploit scripts and reading local files."
        }
        
        system_prompt = f"""ACT AS SHADOWCYPHER DEEPHAT {agent_role.upper()} AI.
{roles.get(agent_role, roles['commander'])}
You are fully autonomous. You have the ability to run tools.
To use a tool, you must reply with EXACTLY this JSON wrapper format and nothing else:
<TOOL_CALL>
{{"tool": "command", "args": {{"cmd": "ls -la"}}}}
</TOOL_CALL>

Available tools:
1. command: args: {{"cmd": "shell command"}} -> Executes a bash command.
2. write_file: args: {{"path": "file_path", "content": "file_content"}} -> Writes a file.
3. read_file: args: {{"path": "file_path"}} -> Reads a local file.
4. github_search: args: {{"query": "repo or topic"}} -> Searches github repos.
5. delegate: args: {{"subagent": "recon|coder", "instructions": "what to do"}} -> Spawns a dedicated subagent to solve a specific sub-problem.

If you use a tool, wait for the TOOL_RESULT. Do not hallucinate the result.
When you have the final answer, answer the user normally without <TOOL_CALL>.
"""
        
        conversation_history = system_prompt + f"\n\nUSER COMMAND: {query}\n"
        
        for step in range(6): # Max 6 loops of autonomous thought
            if callback: callback(f"[TENGU] REASONING_CYCLE_{step+1}...")
            
            try:
                response = requests.post(self.base_url, json={
                    "model": self.model,
                    "prompt": conversation_history,
                    "stream": False
                }, timeout=120)
                
                if response.status_code == 200:
                    result = response.json().get("response", "")
                    
                    # Detect if the AI is trying to use a tool
                    tool_match = re.search(r"<TOOL_CALL>(.*?)</TOOL_CALL>", result, re.DOTALL)
                    if tool_match:
                        try:
                            tool_req = json.loads(tool_match.group(1).strip())
                            tool_name = tool_req.get("tool")
                            tool_args = tool_req.get("args", {})
                            
                            if callback: callback(f"[TENGU] EXECUTING_TOOL: {tool_name} {str(tool_args)[:50]}")
                            tool_output = self._execute_tool(tool_name, tool_args)
                            
                            # Append the tool use and result to the context memory so it can analyze it
                            conversation_history += f"\nAI: {result}\n[SYSTEM TOOL_RESULT]:\n{tool_output}\n"
                            
                            if callback: callback("[TENGU] ANALYZING_TOOL_OUTPUT...")
                            continue # Loop back to the AI for its next move
                        except Exception as e:
                            conversation_history += f"\nAI: {result}\n[SYSTEM TOOL_ERROR]: {str(e)}\n"
                            continue
                            
                    # Self-correction: extract any raw script blocks it wrote outside of the tool
                    if "```python" in result or "```bash" in result:
                        self._extract_and_write_script(result)
                    
                    return result
                else:
                    return f"ERROR: OLLAMA_BACKEND_UNREACHABLE (Status {response.status_code})"
            except Exception as e:
                return f"ERROR: SWARM_FAILURE [{str(e)}]"
        
        return "ERROR: MAX_ORCHESTRATION_CYCLES_EXCEEDED"

    def _execute_tool(self, name, args):
        """The actual routing logic for the AI's autonomous tools."""
        if name == "command":
            cmd = args.get("cmd", "")
            try:
                out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=30)
                return out.decode('utf-8')[:4000] # Truncate massive outputs
            except subprocess.CalledProcessError as e:
                return f"Command Failed: {e.output.decode('utf-8')[:4000]}"
            except Exception as e:
                return f"Execution Error: {str(e)}"
                
        elif name == "write_file":
            path = args.get("path")
            with open(path, "w") as f:
                f.write(args.get("content", ""))
            return f"SUCCESS: File written to {path}"
            
        elif name == "read_file":
            try:
                with open(args.get("path"), "r") as f:
                    return f.read()[:4000]
            except Exception as e:
                return str(e)
                
        elif name == "github_search":
            query = args.get("query", "").replace(" ", "+")
            # We use curl natively to query the GitHub API
            cmd = f"curl -s 'https://api.github.com/search/repositories?q={query}&per_page=5' | grep -E 'full_name|html_url|description'"
            try:
                out = subprocess.check_output(cmd, shell=True)
                return out.decode('utf-8') if out else "No results found."
            except:
                return "GITHUB_SEARCH_FAILED"
                
        elif name == "delegate":
            subagent = args.get("subagent", "recon")
            instructions = args.get("instructions", "")
            # Recursive call: The commander pauses and spawns a new orchestrator context
            return self.execute_query(instructions, callback=None, agent_role=subagent)
            
        return "UNKNOWN_TOOL"

    def _extract_and_write_script(self, text):
        """Fallback: Extract code blocks and write them to the payloads directory."""
        # Find all triple-backtick blocks
        blocks = re.findall(r"```(python|bash)\n(.*?)\n```", text, re.DOTALL)
        for i, (lang, code) in enumerate(blocks):
            ext = "py" if lang == "python" else "sh"
            filename = f"deephat_gen_{i}.{ext}"
            filepath = os.path.join(self.payload_dir, filename)
            
            with open(filepath, "w") as f:
                f.write(code)
            
            logger.info("ai", f"AUTONOMOUS_SCRIPT_WRITTEN: {filepath}")
            print(f"[TACTICAL] Script saved to {filepath}")
