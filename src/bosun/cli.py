import logging
from typing import Annotated
from typer import Typer, Option
from bosun.core import ImplementationJob
from bosun.logging import configure_logging

app = Typer()


@app.callback()
def main(
    verbose: Annotated[bool, Option("--verbose", "-v", help="Enable debug logging")] = False,
):
    configure_logging(logging.DEBUG if verbose else logging.INFO)


@app.command(help="Implement a task using the pi agent")
def implement(
    task_file: str,
    iterations: Annotated[int, Option()] = 50,
    extension: Annotated[list[str] | None, Option()] = None,
):
    if extension is None:
        extension = []
    implementation_job = ImplementationJob(task_file, iterations)
    implementation_job.run()
