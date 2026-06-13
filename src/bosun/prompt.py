from pathlib import Path

from jinja2 import Template

_PROMPTS_DIR = Path(__file__).parent / "prompts"


class TaskPrompt:
    """Loads and renders the task prompt handed to the pi agent.

    The prompt lives in ``prompts/task.md`` and is a Jinja2 template whose
    ``{{input_file}}`` placeholder is filled in with the path to the plan the
    agent should work through on each iteration.
    """

    def __init__(self, template_file: Path | None = None) -> None:
        """Initialize the prompt template based on a file.

        Parameters
        ----------
        template_file : Path or None, optional
            Path to the Jinja2 template to render. When ``None`` (the
            default), the bundled ``prompts/task.md`` template is used.
        """
        self._template_file = template_file or _PROMPTS_DIR / "task.md"

    def render(self, input_file: str) -> str:
        """Render the prompt for the given input file.

        Parameters
        ----------
        input_file : str
            Path to the plan the agent should work through, substituted
            into the template's ``{{input_file}}`` placeholder.

        Returns
        -------
        str
            The rendered prompt with the placeholder filled in.
        """
        template = Template(self._template_file.read_text())
        return template.render(input_file=input_file)
