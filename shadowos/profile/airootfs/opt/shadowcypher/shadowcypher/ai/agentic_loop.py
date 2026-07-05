"""
ShadowLoop — Agentic Orchestration Layer.

This module implements the 'Observe-Think-Act' loop, allowing ShadowCypher to
chain security tools autonomously to achieve a high-level goal.
"""

import json
import threading
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field

from shadowcypher.ai.intent import TOOL_REGISTRY, _register_tools, _TASK_ID_RE
from shadowcypher.core.logger import logger
from shadowcypher.ai.providers import provider_registry

@dataclass
class Step:
    tool_name: str
    target: str
    output: str = ""
    thought: str = ""

@dataclass
class ShadowLoopSession:
    goal: str
    target: str
    history: List[Step] = field(default_factory=list)
    status: str = "ACTIVE"  # ACTIVE, COMPLETED, FAILED

    def get_context(self) -> str:
        """Formats the tool history for the AI."""
        if not self.history:
            return "No tools have been executed yet."
        
        lines = []
        for i, step in enumerate(self.history):
            lines.append(f"Step {i+1}: [{step.tool_name}] on {step.target}")
            lines.append(f"Thought: {step.thought}")
            lines.append(f"Output:\n{step.output[:2000]}\n")
        return "\n".join(lines)

class ShadowLoop:
    def __init__(self, max_steps: int = 5):
        self.max_steps = max_steps

    def run(self, target: str, goal: str, on_step_update: Callable = None):
        """
        Main agentic loop.
        Args:
            target: The primary target (IP/Domain)
            goal: The high-level objective (e.g., 'Find potential entry points')
            on_step_update: Callback for streaming updates to UI/Hub
        """
        session = ShadowLoopSession(goal=goal, target=target)
        
        # 1. Initial tool registration
        _register_tools()
        available_tools = [f"{t.name}: {t.description}" for t in TOOL_REGISTRY.values()]
        tools_desc = "\n".join(available_tools)

        for step_idx in range(self.max_steps):
            if session.status != "ACTIVE":
                break
            
            if on_step_update:
                on_step_update(f"Thinking... (Step {step_idx + 1}/{self.max_steps})")

            # 2. THINK: Ask AI what to do next
            action = self._decide_next_action(session, tools_desc)
            
            if action["status"] == "COMPLETED":
                session.status = "COMPLETED"
                if on_step_update:
                    on_step_update(f"Goal achieved: {action['summary']}")
                return action['summary']
            
            if action["status"] == "FAILED":
                session.status = "FAILED"
                if on_step_update:
                    on_step_update(f"Agent gave up: {action['reason']}")
                return f"Failed to achieve goal: {action['reason']}"

            # 3. ACT: Execute the chosen tool
            tool_name = action["tool"]
            raw_target = (action["target"] or "").strip()
            tool_target = target if not raw_target or raw_target.lower() == "same" else raw_target
            thought = action["thought"]

            # Guard against weak models that never emit STATUS: COMPLETED and
            # instead repeat the exact same successful action indefinitely.
            if session.history:
                last = session.history[-1]
                if (last.tool_name == tool_name and last.target == tool_target
                        and last.output and "Error" not in last.output[:20]):
                    session.status = "COMPLETED"
                    if on_step_update:
                        on_step_update("Detected repeated identical action — treating prior result as final.")
                    return last.output

            if on_step_update:
                on_step_update(f"Executing {tool_name} on {tool_target}...")

            tool = TOOL_REGISTRY.get(tool_name)
            if not tool:
                output = f"Error: Tool {tool_name} not found in registry."
            else:
                output_lines = []
                done_event = threading.Event()
                def _collect(line):
                    output_lines.append(line)
                    if on_step_update:
                        on_step_update(line)
                    if isinstance(line, str) and ("[done: exit" in line or line.startswith("[TIMEOUT]")):
                        done_event.set()

                try:
                    result = tool.executor(tool_target, _collect)
                    if not done_event.is_set() and isinstance(result, str) and _TASK_ID_RE.match(result):
                        done_event.wait(timeout=1800)
                    output = "".join(output_lines)
                except Exception as e:
                    output = f"Execution error: {str(e)}"

            # 4. OBSERVE: Record the result
            session.history.append(Step(
                tool_name=tool_name, 
                target=tool_target, 
                output=output, 
                thought=thought
            ))

        if session.status == "ACTIVE":
            if on_step_update:
                on_step_update("Reached maximum steps without definitive completion.")
            return "Goal partially pursued, but max steps reached."

    def _decide_next_action(self, session: ShadowLoopSession, tools_desc: str) -> Dict[str, Any]:
        """
        Prompt the AI to decide the next step or mark as complete.
        """
        prompt = f"""You are the ShadowLoop Agent, an autonomous security orchestrator.
Your goal is: {session.goal}
Current target: {session.target}

## Available Tools
{tools_desc}

## Execution History
{session.get_context()}

## Instructions
Based on the history and the goal, decide the next action.
If the goal is achieved, respond with 'STATUS: COMPLETED' and a summary.
If the goal is impossible, respond with 'STATUS: FAILED' and a reason.
Otherwise, respond with 'STATUS: CONTINUE' and specify the tool and target.

Your response MUST follow this exact format:
STATUS: [CONTINUE | COMPLETED | FAILED]
THOUGHT: [Your reasoning for this step]
TOOL: [tool_name]
TARGET: [specific target or 'same' for primary target]
SUMMARY: [Summary if COMPLETED, Reason if FAILED]
"""
        
        # We use a non-streaming call here to get the full decision
        response = provider_registry.generate(
            prompt,
            system_prompt="You are a precise agentic orchestrator. You only output the requested format. No conversational filler.",
            temperature=0.0, # Deterministic for logic
        )

        # Parse the response
        return self._parse_action(response)

    def _parse_action(self, response: str) -> Dict[str, Any]:
        """
        Simple parser for the agent's formatted response.
        """
        data = {"status": "FAILED", "thought": "", "tool": None, "target": None, "summary": ""}
        
        for line in response.splitlines():
            line = line.strip()
            if line.startswith("STATUS:"):
                data["status"] = line.replace("STATUS:", "").strip().upper()
            elif line.startswith("THOUGHT:"):
                data["thought"] = line.replace("THOUGHT:", "").strip()
            elif line.startswith("TOOL:"):
                data["tool"] = line.replace("TOOL:", "").strip()
            elif line.startswith("TARGET:"):
                data["target"] = line.replace("TARGET:", "").strip()
            elif line.startswith("SUMMARY:"):
                data["summary"] = line.replace("SUMMARY:", "").strip()
        
        # Validation
        if data["status"] == "CONTINUE" and not data["tool"]:
            data["status"] = "FAILED"
            data["summary"] = "Agent failed to specify a tool for CONTINUE status."
            
        return data

# Global singleton
shadow_loop = ShadowLoop()
