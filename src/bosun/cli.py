"""Command-line interface for bosun, built on Typer."""

import logging
from typing import Annotated
from typer import Typer, Option, Exit
from bosun.core import ImplementationJob, StalledImplementationError
from bosun.logging import configure_logging

logger = logging.getLogger(__name__)

app = Typer()


@app.callback()
def main(
    verbose: Annotated[bool, Option("--verbose", "-v", help="Enable debug logging")] = False,
):
    """Configure logging for the CLI.

    Parameters
    ----------
    verbose : bool, optional
        When ``True``, enable debug-level logging; otherwise log at the
        info level. Defaults to ``False``.
    """
    configure_logging(logging.DEBUG if verbose else logging.INFO)


@app.command(help="Implement a task using the pi agent")
def implement(
    task_file: str,
    iterations: Annotated[int, Option()] = 50,
    extension: Annotated[list[str] | None, Option()] = None,
):
    """Run the ralph loop to implement a task with the pi agent.

    Parameters
    ----------
    task_file : str
        Path to the plan file the agent should work through.
    iterations : int, optional
        The maximum number of iterations to run. Defaults to 50.
    extension : list of str or None, optional
        Extensions to enable for the run. Defaults to ``None``, which is
        treated as an empty list.

    Raises
    ------
    typer.Exit
        With exit code 1 if the implementation job stalls.
    """
    if extension is None:
        extension = []
    implementation_job = ImplementationJob(task_file, iterations)
    try:
        implementation_job.run()
    except StalledImplementationError as error:
        logger.error("Implementation job failed: %s", error)
        raise Exit(code=1) from error
