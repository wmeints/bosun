from pathlib import Path
import subprocess
import logging

from bosun.rendering import PiEventRenderer

logger = logging.getLogger(__name__)


class ImplementationJob:
    task_file: str
    max_iterations: int
    current_iteration: int

    def __init__(self, task_file: str, max_iterations: int) -> None:
        self.max_iterations = max_iterations
        self.task_file = task_file
        self.current_iteration = 0

    def run(self):
        while self.current_iteration < self.max_iterations:
            self._run_agent()
            self.current_iteration += 1

    def _run_agent(self):
        task_prompt_file = Path(__file__).parent / "prompts" / "task.md"
        task_prompt = task_prompt_file.read_text()

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
