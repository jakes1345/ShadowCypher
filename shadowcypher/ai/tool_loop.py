"""
AgentLoop — real Ollama tool-calling agentic loop.

Instead of sending a prompt and getting text back, the LLM decides which
tools to call, sees the actual results, and decides what to do next.
Loop continues until the LLM stops calling tools and gives a final answer.
"""

import json
import threading
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from shadowcypher.core.logger import logger

OLLAMA_BASE = "http://127.0.0.1:11434"
DEFAULT_MODEL = "llama3.2"
MAX_ITERATIONS = 20


@dataclass
class AgentTool:
    name: str
    description: str
    parameters: Dict          # JSON Schema
    fn: Callable
    requires_approval: bool = False  # Human gate before running


class AgentLoop:
    """
    Core agentic loop over Ollama's tool-calling API.

    Usage:
        loop = AgentLoop(tools=[...], model="llama3.2", system_prompt="...")
        result = loop.run("scan 10.0.0.1 and report findings", callback=print)
    """

    def __init__(self, tools: List[AgentTool], model: str = DEFAULT_MODEL,
                 system_prompt: str = ""):
        self.tools = {t.name: t for t in tools}
        self.model = model
        self.system_prompt = system_prompt

    # ── Ollama API ────────────────────────────────────────────────

    def _tool_schemas(self) -> List[Dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                }
            }
            for t in self.tools.values()
        ]

    def _chat(self, messages: List[Dict]) -> Dict:
        payload = {
            "model": self.model,
            "messages": messages,
            "tools": self._tool_schemas(),
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 4096},
        }
        req = urllib.request.Request(
            f"{OLLAMA_BASE}/api/chat",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=180) as resp:
            return json.loads(resp.read())

    # ── Tool Execution ────────────────────────────────────────────

    def _run_tool(self, tool: AgentTool, args: Dict) -> str:
        try:
            result = tool.fn(**args)
            return str(result) if result is not None else "(no output)"
        except TypeError as e:
            return f"TOOL_ARG_ERROR: {e}"
        except Exception as e:
            return f"TOOL_ERROR: {e}"

    # ── Main Loop ─────────────────────────────────────────────────

    def run(self, task: str,
            callback: Optional[Callable[[str], None]] = None,
            approval_gate: Optional[Callable[[str, Dict], bool]] = None,
            max_iterations: int = MAX_ITERATIONS) -> str:
        """
        Run the agentic loop synchronously.

        callback(msg): called with each status line
        approval_gate(tool_name, args) -> bool: called before requires_approval tools;
            return True to run, False to skip
        Returns the LLM's final answer string.
        """
        messages: List[Dict] = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": task})

        def emit(msg: str):
            logger.info("agent_loop", msg)
            if callback:
                callback(msg)

        emit(f"[LOOP:START] {task[:100]}")

        for iteration in range(max_iterations):
            try:
                response = self._chat(messages)
            except Exception as e:
                emit(f"[LOOP:ERROR] Ollama unreachable: {e}")
                return f"LOOP_ERROR: Ollama unreachable — {e}"

            msg = response.get("message", {})
            content: str = msg.get("content") or ""
            tool_calls: List[Dict] = msg.get("tool_calls") or []

            # Record assistant turn (strip None values so Ollama accepts it back)
            assistant_entry: Dict = {"role": "assistant", "content": content}
            if tool_calls:
                assistant_entry["tool_calls"] = tool_calls
            messages.append(assistant_entry)

            if not tool_calls:
                emit(f"[LOOP:DONE] {iteration + 1} iterations")
                return content or "Mission complete — no findings to report."

            # Execute tool calls
            for tc in tool_calls:
                fn_info = tc.get("function", {})
                tool_name: str = fn_info.get("name", "")
                raw_args = fn_info.get("arguments", {})

                if isinstance(raw_args, str):
                    try:
                        raw_args = json.loads(raw_args)
                    except Exception:
                        raw_args = {}

                tool = self.tools.get(tool_name)
                if not tool:
                    tool_result = f"UNKNOWN_TOOL: {tool_name}"
                    emit(f"[TOOL:UNKNOWN] {tool_name}")
                else:
                    if tool.requires_approval and approval_gate:
                        approved = approval_gate(tool_name, raw_args)
                        if not approved:
                            tool_result = f"SKIPPED: {tool_name} not approved"
                            emit(f"[TOOL:SKIPPED] {tool_name}")
                        else:
                            emit(f"[TOOL:RUN] {tool_name}({raw_args})")
                            tool_result = self._run_tool(tool, raw_args)
                    else:
                        emit(f"[TOOL:RUN] {tool_name}({raw_args})")
                        tool_result = self._run_tool(tool, raw_args)

                # Truncate massive outputs so context doesn't explode
                if len(tool_result) > 6000:
                    tool_result = tool_result[:6000] + "\n... [truncated]"

                emit(f"[TOOL:RESULT] {tool_result[:300]}")
                messages.append({"role": "tool", "content": tool_result})

        return "[LOOP:LIMIT] Max iterations reached. Partial results in findings."

    def run_async(self, task: str,
                  callback: Optional[Callable[[str], None]] = None,
                  on_complete: Optional[Callable[[str], None]] = None,
                  approval_gate: Optional[Callable[[str, Dict], bool]] = None,
                  max_iterations: int = MAX_ITERATIONS):
        """Non-blocking version. Fires on_complete(result) when done."""
        def _target():
            result = self.run(task, callback=callback,
                              approval_gate=approval_gate,
                              max_iterations=max_iterations)
            if on_complete:
                on_complete(result)

        threading.Thread(target=_target, daemon=True, name="AgentLoop").start()
