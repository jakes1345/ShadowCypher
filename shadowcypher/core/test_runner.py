"""
ShadowCypher Test Suite — Apex Runner Execution Engine
Tests command execution, callback delivery, process termination,
concurrent tasks, and cleanup.
"""

import queue
import threading
import time

import pytest

from shadowcypher.core.runner import Runner


@pytest.fixture
def runner():
    return Runner()


def collect(q, timeout=5):
    """Drain a queue into a list within timeout seconds."""
    results = []
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            results.append(q.get(timeout=0.1))
        except queue.Empty:
            if any("[done:" in r for r in results):
                break
    return results


class TestBasicExecution:

    def test_list_command_delivers_output(self, runner):
        q = queue.Queue()
        runner.execute_task("ECHO", ["echo", "hello"], callback=q.put)
        lines = collect(q)
        assert any("hello" in line for line in lines)

    def test_string_command_delivers_output(self, runner):
        q = queue.Queue()
        runner.execute_task("ECHO_STR", "echo worldtest", callback=q.put)
        lines = collect(q)
        assert any("worldtest" in line for line in lines)

    def test_shell_command_delivers_output(self, runner):
        q = queue.Queue()
        runner.execute_task_shell("SHELL", "echo shelltest", callback=q.put)
        lines = collect(q)
        assert any("shelltest" in line for line in lines)

    def test_callback_receives_termination_message(self, runner):
        q = queue.Queue()
        runner.execute_task("TERM", ["true"], callback=q.put)
        lines = collect(q)
        assert any("[done:" in line for line in lines)

    def test_failing_command_delivers_return_code(self, runner):
        q = queue.Queue()
        runner.execute_task("FAIL", ["false"], callback=q.put)
        lines = collect(q)
        term_lines = [line for line in lines if "[done:" in line]
        assert term_lines
        assert "1" in term_lines[0]  # Return code 1

    def test_no_callback_runs_without_crash(self, runner):
        task_id = runner.execute_task("NOCB", ["true"])
        assert task_id is not None
        time.sleep(0.3)  # Let it finish

    def test_multiline_output_all_delivered(self, runner):
        q = queue.Queue()
        runner.execute_task_shell("MULTI", "printf 'line1\\nline2\\nline3\\n'", callback=q.put)
        lines = collect(q)
        combined = "".join(lines)
        assert "line1" in combined
        assert "line2" in combined
        assert "line3" in combined


class TestTaskIds:

    def test_task_id_is_string(self, runner):
        tid = runner.execute_task("IDTEST", ["true"])
        assert isinstance(tid, str)
        assert len(tid) > 0

    def test_concurrent_tasks_have_unique_ids(self, runner):
        ids = [runner.execute_task(f"T{i}", ["true"]) for i in range(10)]
        assert len(set(ids)) == 10

    def test_task_removed_from_active_after_completion(self, runner):
        done = threading.Event()

        def cb(line):
            if "[done:" in line:
                done.set()

        runner.execute_task("CLEANUP", ["true"], callback=cb)
        done.wait(timeout=5)
        time.sleep(0.1)  # Give cleanup goroutine time to run
        assert len(runner.active_processes) == 0


class TestProcessControl:

    def test_stop_unknown_task_does_nothing(self, runner):
        runner.stop_task("nonexistent_task_id_xyz")  # Must not raise

    def test_stop_running_task_terminates_it(self, runner):
        terminated = threading.Event()
        lines = []

        def cb(line):
            lines.append(line)
            if "[done:" in line:
                terminated.set()

        task_id = runner.execute_task("SLEEP", ["sleep", "30"], callback=cb)
        time.sleep(0.2)  # Let it start
        runner.stop_task(task_id)
        terminated.wait(timeout=5)
        assert terminated.is_set()


class TestConcurrency:

    def test_five_concurrent_tasks_all_complete(self, runner):
        done_events = []
        for i in range(5):
            ev = threading.Event()
            done_events.append(ev)

            def make_cb(event):
                def cb(line):
                    if "[done:" in line:
                        event.set()
                return cb

            runner.execute_task(f"CONC_{i}", ["echo", f"task_{i}"], callback=make_cb(ev))

        for ev in done_events:
            assert ev.wait(timeout=8), "Concurrent task did not complete"

    def test_output_not_interleaved_between_tasks(self, runner):
        """Each task's output goes to its own callback."""
        buckets = {0: [], 1: [], 2: []}
        events = [threading.Event() for _ in range(3)]

        for i in range(3):
            def make_cb(bucket_idx, ev):
                def cb(line):
                    buckets[bucket_idx].append(line)
                    if "[done:" in line:
                        ev.set()
                return cb

            runner.execute_task_shell(
                f"ISO_{i}",
                f"echo unique_marker_{i}",
                callback=make_cb(i, events[i])
            )

        for ev in events:
            assert ev.wait(timeout=8)

        for i in range(3):
            combined = "".join(buckets[i])
            assert f"unique_marker_{i}" in combined
