import logging

from rich.logging import RichHandler


def configure_logging(level: int = logging.INFO) -> None:
    """Configure pretty-printed logging to the terminal using Rich.

    Parameters
    ----------
    level : int, optional
        The root logging level to set, e.g. :data:`logging.INFO` (the
        default) or :data:`logging.DEBUG`.
    """
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
    )
