"""Core implementation of the ralph loop related logic."""

from pathlib import Path
import hashlib
import subprocess
import logging

from bosun.prompt import TaskPrompt
from bosun.rendering import PiEventRenderer

logger = logging.getLogger(__name__)

# Number of consecutive iterations the input file may remain unchanged before
# the job is considered stalled. The agent edits the task file every iteration
# (checking off items), so an unchanging file means it is making no progress.
_MAX_STALLED_ITERATIONS = 3


class StalledImplementationError(RuntimeError):
    """Raised when the agent stops making progress on the task file.

    If the input file's contents are identical for ``_MAX_STALLED_ITERATIONS``
    iterations in a row, the agent is no longer advancing the plan and the job
    is aborted rather than burning through the remaining iterations.
    """


class ImplementationJob:
    """Manages the implementation job the agent is running.

    This is the core of the ralph loop mechanism. It has stall detection
    built-in and runs for a maximum number iterations to prevent issues
    with hanging agents.

    Attributes
    ----------
    task_file : str
        The file containing the current task.
    max_iterations : int
        The maximum number of iterations the agent is allowed to run.
    current_iteration : int
        The index of the iteration currently being run.
    """

    task_file: str
    max_iterations: int
    current_iteration: int

    def __init__(self, task_file: str, max_iterations: int) -> None:
        """Initialize a new implementation job.

        Parameters
        ----------
        task_file : str
            The filename containing the plan we're going to work on.
        max_iterations : int
            The maximum number of iterations the ralph loop is allowed to
            run for.
        """
        self.max_iterations = max_iterations
        self.task_file = task_file
        self.current_iteration = 0
        self._prompt = TaskPrompt()

    def run(self):
        """Run the implementation job until completion or stall.

        The agent is invoked once per iteration, up to ``max_iterations``
        times. After each iteration the task file is hashed; if it stays
        unchanged for ``_MAX_STALLED_ITERATIONS`` consecutive iterations the
        job is aborted.

        Raises
        ------
        StalledImplementationError
            If the task file remains unchanged for
            ``_MAX_STALLED_ITERATIONS`` consecutive iterations, indicating
            the agent is no longer making progress.
        """
        previous_hash = self._task_file_hash()
        stalled_iterations = 0

        while self.current_iteration < self.max_iterations:
            self._run_agent()
            self.current_iteration += 1

            current_hash = self._task_file_hash()

            if current_hash == previous_hash:
                stalled_iterations += 1

                logger.warning(
                    "Task file unchanged after iteration %d (%d/%d before abort).",
                    self.current_iteration,
                    stalled_iterations,
                    _MAX_STALLED_ITERATIONS,
                )
            else:
                stalled_iterations = 0

            previous_hash = current_hash

            if stalled_iterations >= _MAX_STALLED_ITERATIONS:
                raise StalledImplementationError(
                    f"No changes to '{self.task_file}' after "
                    f"{_MAX_STALLED_ITERATIONS} iterations; the agent is not "
                    "making progress."
                )

    def _task_file_hash(self) -> str | None:
        """Compute the MD5 hash of the task file's contents.

        Returns
        -------
        str or None
            The hex-encoded MD5 digest of the task file, or ``None`` if the
            file cannot be read (e.g. it does not exist).
        """
        try:
            contents = Path(self.task_file).read_bytes()
        except OSError:
            return None

        return hashlib.md5(contents).hexdigest()

    def _run_agent(self):
        """Run the pi agent once and render its output to the terminal.

        The task prompt is rendered for the current task file and passed to
        the ``pi`` subprocess in JSON mode. Each line of the agent's output
        is streamed through a :class:`PiEventRenderer`.

        Returns
        -------
        int
            The exit code returned by the ``pi`` subprocess.
        """
        task_prompt = self._prompt.render(input_file=self.task_file)

        proc = subprocess.Popen(
            ["pi", "--mode", "json", f"{task_prompt}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        renderer = PiEventRenderer()

        with proc.stdout:
            for line in proc.stdout:
                renderer.feed(line)

        return proc.wait()
