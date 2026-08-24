"""
Tests for AgentLoop — the real tool-calling agentic loop.
Ollama is mocked so tests run offline.
"""

import json
import pytest
from unittest.mock import patch, MagicMock, call
from shadowcypher.ai.tool_loop import AgentLoop, AgentTool


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_tool(name="echo", requires_approval=False):
    """Simple tool that returns its input as a string."""
    return AgentTool(
        name=name,
        description=f"Echo tool: {name}",
        parameters={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
        fn=lambda text="": f"ECHO:{text}",
        requires_approval=requires_approval,
    )


def _ollama_final(content="Final answer"):
    """Simulate Ollama returning a final text response (no tool calls)."""
    return {"message": {"content": content, "tool_calls": []}}


def _ollama_tool_call(tool_name, args: dict):
    """Simulate Ollama requesting a tool call."""
    return {
        "message": {
            "content": "",
            "tool_calls": [{"function": {"name": tool_name, "arguments": args}}],
        }
    }


@pytest.fixture
def loop():
    return AgentLoop(
        tools=[_make_tool("echo"), _make_tool("echo2")],
        model="test-model",
        system_prompt="You are a test agent.",
    )


# ── Tool Schema ───────────────────────────────────────────────────────────────

class TestToolSchema:

    def test_schema_contains_all_tools(self, loop):
        schemas = loop._tool_schemas()
        names = [s["function"]["name"] for s in schemas]
        assert "echo" in names
        assert "echo2" in names

    def test_schema_type_is_function(self, loop):
        schema = loop._tool_schemas()[0]
        assert schema["type"] == "function"

    def test_schema_has_description(self, loop):
        schema = loop._tool_schemas()[0]
        assert "description" in schema["function"]

    def test_schema_has_parameters(self, loop):
        schema = loop._tool_schemas()[0]
        assert "parameters" in schema["function"]


# ── Tool Execution ────────────────────────────────────────────────────────────

class TestToolExecution:

    def test_run_tool_calls_function(self, loop):
        tool = _make_tool("echo")
        result = loop._run_tool(tool, {"text": "hello"})
        assert result == "ECHO:hello"

    def test_run_tool_bad_args_returns_error(self, loop):
        tool = _make_tool("echo")
        result = loop._run_tool(tool, {"wrong_param": "x"})
        assert "TOOL_ARG_ERROR" in result or "ECHO" in result

    def test_run_tool_exception_returns_error(self):
        bad_tool = AgentTool(
            name="bad", description="", parameters={}, fn=lambda: 1 / 0
        )
        loop = AgentLoop(tools=[bad_tool], model="m")
        result = loop._run_tool(bad_tool, {})
        assert "TOOL_ERROR" in result


# ── Agentic Loop ──────────────────────────────────────────────────────────────

class TestAgentLoop:

    def test_final_answer_returned_directly(self, loop):
        with patch.object(loop, "_chat", return_value=_ollama_final("Done!")):
            result = loop.run("do something")
        assert result == "Done!"

    def test_tool_call_then_final_answer(self, loop):
        responses = [
            _ollama_tool_call("echo", {"text": "hi"}),
            _ollama_final("All done"),
        ]
        with patch.object(loop, "_chat", side_effect=responses):
            result = loop.run("say hi")
        assert result == "All done"

    def test_tool_result_fed_back_into_messages(self, loop):
        captured_messages = []

        def mock_chat(messages):
            captured_messages.append(list(messages))
            if len(captured_messages) == 1:
                return _ollama_tool_call("echo", {"text": "test"})
            return _ollama_final("done")

        with patch.object(loop, "_chat", side_effect=mock_chat):
            loop.run("task")

        # Second call should include the tool result message
        second_call_messages = captured_messages[1]
        roles = [m["role"] for m in second_call_messages]
        assert "tool" in roles

    def test_tool_result_content_correct(self, loop):
        tool_messages = []

        def mock_chat(messages):
            tool_msgs = [m for m in messages if m["role"] == "tool"]
            if tool_msgs:
                tool_messages.extend(tool_msgs)
                return _ollama_final("done")
            return _ollama_tool_call("echo", {"text": "payload"})

        with patch.object(loop, "_chat", side_effect=mock_chat):
            loop.run("task")

        assert any("ECHO:payload" in m["content"] for m in tool_messages)

    def test_unknown_tool_returns_error_message(self, loop):
        responses = [
            _ollama_tool_call("nonexistent_tool", {}),
            _ollama_final("done"),
        ]
        with patch.object(loop, "_chat", side_effect=responses):
            result = loop.run("task")
        assert result == "done"  # Loop continues despite unknown tool

    def test_callback_called_on_tool_run(self, loop):
        updates = []
        responses = [
            _ollama_tool_call("echo", {"text": "x"}),
            _ollama_final("done"),
        ]
        with patch.object(loop, "_chat", side_effect=responses):
            loop.run("task", callback=updates.append)
        assert any("[TOOL:RUN]" in u for u in updates)

    def test_callback_called_on_done(self, loop):
        updates = []
        with patch.object(loop, "_chat", return_value=_ollama_final("done")):
            loop.run("task", callback=updates.append)
        assert any("[LOOP:DONE]" in u for u in updates)

    def test_ollama_error_returns_error_string(self, loop):
        with patch.object(loop, "_chat", side_effect=Exception("connection refused")):
            result = loop.run("task")
        assert "LOOP_ERROR" in result

    def test_max_iterations_respected(self, loop):
        # Always returns tool calls — should stop at max_iterations
        with patch.object(loop, "_chat",
                          return_value=_ollama_tool_call("echo", {"text": "x"})):
            result = loop.run("task", max_iterations=3)
        assert "LOOP:LIMIT" in result

    def test_system_prompt_in_first_message(self, loop):
        captured = []

        def mock_chat(messages):
            captured.append(messages)
            return _ollama_final("done")

        with patch.object(loop, "_chat", side_effect=mock_chat):
            loop.run("task")

        first_call = captured[0]
        assert first_call[0]["role"] == "system"
        assert "test agent" in first_call[0]["content"]

    def test_no_system_prompt_skipped(self):
        loop = AgentLoop(tools=[], model="m", system_prompt="")
        captured = []

        def mock_chat(messages):
            captured.append(messages)
            return _ollama_final("done")

        with patch.object(loop, "_chat", side_effect=mock_chat):
            loop.run("task")

        first_call = captured[0]
        assert first_call[0]["role"] == "user"

    def test_string_arguments_parsed_as_json(self, loop):
        """LLMs sometimes return arguments as a JSON string instead of dict."""
        args_as_string = json.dumps({"text": "from_string"})
        responses = [
            {"message": {"content": "", "tool_calls": [
                {"function": {"name": "echo", "arguments": args_as_string}}
            ]}},
            _ollama_final("done"),
        ]
        with patch.object(loop, "_chat", side_effect=responses):
            result = loop.run("task")
        assert result == "done"

    def test_large_result_truncated(self, loop):
        """Tool results over 6000 chars are truncated to avoid context explosion."""
        big_tool = AgentTool(
            name="big", description="", parameters={},
            fn=lambda: "x" * 10000,
        )
        loop2 = AgentLoop(tools=[big_tool], model="m")
        responses = [
            _ollama_tool_call("big", {}),
            _ollama_final("done"),
        ]
        tool_messages = []

        original_chat = loop2._chat

        def intercepting_chat(messages):
            tool_msgs = [m for m in messages if m["role"] == "tool"]
            tool_messages.extend(tool_msgs)
            return responses.pop(0)

        with patch.object(loop2, "_chat", side_effect=intercepting_chat):
            loop2.run("task")

        if tool_messages:
            assert len(tool_messages[-1]["content"]) <= 6100


# ── Approval Gate ─────────────────────────────────────────────────────────────

class TestApprovalGate:

    def test_requires_approval_tool_calls_gate(self):
        tool = _make_tool("dangerous", requires_approval=True)
        loop = AgentLoop(tools=[tool], model="m")
        gate_calls = []

        def gate(name, args):
            gate_calls.append((name, args))
            return True  # approve

        responses = [
            _ollama_tool_call("dangerous", {"text": "boom"}),
            _ollama_final("done"),
        ]
        with patch.object(loop, "_chat", side_effect=responses):
            loop.run("task", approval_gate=gate)

        assert len(gate_calls) == 1
        assert gate_calls[0][0] == "dangerous"

    def test_gate_rejection_skips_tool(self):
        tool = _make_tool("dangerous", requires_approval=True)
        loop = AgentLoop(tools=[tool], model="m")
        fn_calls = []
        tool.fn = lambda text="": fn_calls.append(text) or "called"

        responses = [
            _ollama_tool_call("dangerous", {"text": "boom"}),
            _ollama_final("done"),
        ]
        with patch.object(loop, "_chat", side_effect=responses):
            loop.run("task", approval_gate=lambda name, args: False)

        assert len(fn_calls) == 0  # Function was never called

    def test_no_approval_gate_runs_tool_regardless(self):
        tool = _make_tool("dangerous", requires_approval=True)
        loop = AgentLoop(tools=[tool], model="m")
        called = []
        tool.fn = lambda text="": called.append(True) or "ok"

        responses = [
            _ollama_tool_call("dangerous", {"text": "x"}),
            _ollama_final("done"),
        ]
        with patch.object(loop, "_chat", side_effect=responses):
            loop.run("task")  # No approval_gate passed

        assert len(called) == 1


# ── Async ─────────────────────────────────────────────────────────────────────

class TestRunAsync:

    def test_async_calls_on_complete(self, loop):
        import threading
        done = threading.Event()
        results = []

        with patch.object(loop, "_chat", return_value=_ollama_final("async result")):
            loop.run_async("task", on_complete=lambda r: (results.append(r), done.set()))
            done.wait(timeout=5)

        assert results == ["async result"]

    def test_async_callback_receives_updates(self, loop):
        import threading
        done = threading.Event()
        updates = []
        responses = [
            _ollama_tool_call("echo", {"text": "x"}),
            _ollama_final("done"),
        ]

        with patch.object(loop, "_chat", side_effect=responses):
            loop.run_async(
                "task",
                callback=updates.append,
                on_complete=lambda _: done.set(),
            )
            done.wait(timeout=5)

        assert len(updates) > 0
