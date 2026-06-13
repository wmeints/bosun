import io
from pathlib import Path

import pytest

from bosun.core import (
    _MAX_STALLED_ITERATIONS,
    ImplementationJob,
    StalledImplementationError,
)


def _make_job(tmp_path: Path, agent, max_iterations: int = 50) -> ImplementationJob:
    """Build a job whose ``_run_agent`` is replaced by ``agent``.

    ``agent`` receives the job instance and stands in for the real subprocess,
    optionally mutating the task file to simulate progress.
    """
    task_file = tmp_path / "TASK.md"
    task_file.write_text("- [ ] do the thing\n")

    job = ImplementationJob(str(task_file), max_iterations)
    job._run_agent = lambda: agent(job)  # type: ignore[method-assign]
    return job


def test_aborts_when_file_unchanged_for_max_stalled_iterations(tmp_path: Path) -> None:
    """A file that never changes trips the stall guard and aborts the job."""
    calls = 0

    def never_changes(_job: ImplementationJob) -> None:
        nonlocal calls
        calls += 1

    job = _make_job(tmp_path, never_changes)

    with pytest.raises(StalledImplementationError):
        job.run()

    # It runs exactly until the stall threshold is reached, then stops -- it does
    # not burn through the remaining iterations.
    assert calls == _MAX_STALLED_ITERATIONS


def test_runs_to_completion_when_file_keeps_changing(tmp_path: Path) -> None:
    """Steady progress (a changing file) lets the job finish all iterations."""

    def always_changes(job: ImplementationJob) -> None:
        # Keep an unchecked item present so the run is driven to its iteration
        # cap by progress, not by completion.
        Path(job.task_file).write_text(
            f"- [x] item {job.current_iteration}\n- [ ] still more to do\n"
        )

    job = _make_job(tmp_path, always_changes, max_iterations=5)

    job.run()

    assert job.current_iteration == 5


def test_stops_when_agent_completes_final_task(tmp_path: Path) -> None:
    """Once the agent checks off the last item, the loop stops early."""

    def complete_on_first_run(job: ImplementationJob) -> None:
        Path(job.task_file).write_text("- [x] do the thing\n")

    job = _make_job(tmp_path, complete_on_first_run, max_iterations=50)

    job.run()

    # The agent ran once to finish the task, then the loop saw a fully checked
    # file and stopped rather than running to the iteration cap.
    assert job.current_iteration == 1


def test_does_not_run_agent_when_tasks_already_complete(tmp_path: Path) -> None:
    """A file with no open items short-circuits before the agent runs."""
    task_file = tmp_path / "TASK.md"
    task_file.write_text("- [x] already done\n")

    calls = 0

    def agent(_job: ImplementationJob) -> None:
        nonlocal calls
        calls += 1

    job = ImplementationJob(str(task_file), max_iterations=50)
    job._run_agent = lambda: agent(job)  # type: ignore[method-assign]

    job.run()

    assert calls == 0
    assert job.current_iteration == 0


def test_all_tasks_completed_requires_at_least_one_item(tmp_path: Path) -> None:
    """A file with no checkbox items is not treated as complete."""
    task_file = tmp_path / "TASK.md"
    task_file.write_text("# Just a heading, no tasks here\n")

    job = ImplementationJob(str(task_file), max_iterations=1)

    assert job._all_tasks_completed() is False


def test_all_tasks_completed_false_with_open_item(tmp_path: Path) -> None:
    """A mix of checked and unchecked items is not complete."""
    task_file = tmp_path / "TASK.md"
    task_file.write_text("- [x] done\n- [ ] not done\n")

    job = ImplementationJob(str(task_file), max_iterations=1)

    assert job._all_tasks_completed() is False


def test_run_agent_renders_input_file_into_prompt(tmp_path: Path, monkeypatch) -> None:
    """The task template is rendered with the input file before reaching pi."""
    task_file = tmp_path / "PLAN.md"
    task_file.write_text("- [ ] do the thing\n")
    job = ImplementationJob(str(task_file), max_iterations=1)

    captured: dict[str, list[str]] = {}

    class _FakeProc:
        stdout = io.StringIO()

        def wait(self) -> int:
            return 0

    def fake_popen(args, **_kwargs):
        captured["args"] = args
        return _FakeProc()

    monkeypatch.setattr("bosun.core.subprocess.Popen", fake_popen)

    job._run_agent()

    prompt = captured["args"][-1]
    assert str(task_file) in prompt
    assert "{{input_file}}" not in prompt


def test_stall_counter_resets_on_change(tmp_path: Path) -> None:
    """Intermittent progress keeps the consecutive-stall counter below the limit."""

    def change_every_other_iteration(job: ImplementationJob) -> None:
        # Stalls on odd iterations, makes progress on even ones, so the
        # consecutive-stall count never reaches the threshold.
        if job.current_iteration % 2 == 0:
            # Leave an unchecked item so completion never short-circuits the
            # run; this test is only about the stall counter.
            Path(job.task_file).write_text(
                f"- [x] item {job.current_iteration}\n- [ ] still more to do\n"
            )

    job = _make_job(tmp_path, change_every_other_iteration, max_iterations=6)

    job.run()

    assert job.current_iteration == 6
