"""Render pi's JSON event stream to the terminal using Rich."""

import json
import logging
from typing import Any

from rich.console import Console
from rich.json import JSON
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

logger = logging.getLogger(__name__)

# Maximum number of characters to show for a single tool result before truncating.
_MAX_RESULT_CHARS = 2000


class PiEventRenderer:
    """Parse pi's ``--mode json`` event stream and render it to the terminal.

    pi emits newline-delimited JSON objects on stdout. Each line is one event
    (see https://pi.dev/docs/latest/json). This renderer turns the events worth
    showing into Rich output and ignores the noisy intermediate ones (streaming
    deltas, lifecycle markers) so the terminal reflects the conversation.
    """

    def __init__(self, console: Console | None = None) -> None:
        """Initialize the renderer.

        Parameters
        ----------
        console : Console or None, optional
            The Rich console to render to. When ``None`` (the default), a
            new :class:`rich.console.Console` is created.
        """
        self.console = console or Console()
        self._model: str | None = None
        self._total_tokens = 0

    def feed(self, line: str) -> None:
        """Render a single line of pi JSON output.

        Parameters
        ----------
        line : str
            One line from pi's stdout. Expected to be a JSON-encoded event;
            blank lines are ignored and non-JSON lines are printed dimmed.
        """
        line = line.strip()
        if not line:
            return

        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            # Not JSON (e.g. a stray log line on stderr merged into stdout).
            self.console.print(Text(line, style="dim"))
            return

        logger.debug("pi event: %s", event.get("type"))
        self._dispatch(event)

    def _dispatch(self, event: dict[str, Any]) -> None:
        """Route a decoded event to the matching render method.

        Parameters
        ----------
        event : dict
            A single decoded pi event, keyed by its ``"type"`` field.
        """
        match event.get("type"):
            case "session":
                self._render_session(event)
            case "message_end":
                self._render_message(event.get("message", {}))
            case "agent_end":
                self._render_summary()
            # Streaming deltas and lifecycle events are intentionally ignored;
            # message_end carries the complete, final message for each turn.

    def _render_session(self, event: dict[str, Any]) -> None:
        """Render the session header panel.

        Parameters
        ----------
        event : dict
            A ``"session"`` event carrying the session ``id`` and ``cwd``.
        """
        cwd = event.get("cwd", "?")
        session_id = event.get("id", "?")
        self.console.print(
            Panel(
                Text.assemble(
                    ("session ", "bold"),
                    (session_id, "cyan"),
                    ("\ncwd ", "bold"),
                    (cwd, "cyan"),
                ),
                title="pi",
                border_style="blue",
                expand=False,
            )
        )

    def _render_message(self, message: dict[str, Any]) -> None:
        """Render a completed message and update the running token tally.

        Parameters
        ----------
        message : dict
            The ``message`` payload from a ``"message_end"`` event. Its
            ``role`` determines which renderer is used.
        """
        role = message.get("role")
        if model := message.get("model"):
            self._model = model
        if usage := message.get("usage"):
            self._total_tokens = usage.get("totalTokens", self._total_tokens)

        if role == "user":
            self._render_user(message)
        elif role == "assistant":
            self._render_assistant(message)
        elif role == "toolResult":
            self._render_tool_result(message)

    def _render_user(self, message: dict[str, Any]) -> None:
        """Render a user message in a panel.

        Parameters
        ----------
        message : dict
            A message whose ``role`` is ``"user"``.
        """
        text = self._collect_text(message.get("content", []))
        if text:
            self.console.print(
                Panel(text, title="user", border_style="green", expand=False)
            )

    def _render_assistant(self, message: dict[str, Any]) -> None:
        """Render an assistant message, including any tool calls.

        Parameters
        ----------
        message : dict
            A message whose ``role`` is ``"assistant"``. Text blocks are
            rendered as Markdown and ``toolCall`` blocks are rendered
            separately.
        """
        for block in message.get("content", []):
            block_type = block.get("type")
            if block_type == "text":
                if text := block.get("text", "").strip():
                    self.console.print(Markdown(text))
            elif block_type == "toolCall":
                self._render_tool_call(block)

    def _render_tool_call(self, block: dict[str, Any]) -> None:
        """Render a single tool call and its arguments.

        Parameters
        ----------
        block : dict
            A ``toolCall`` content block carrying the tool ``name`` and its
            ``arguments``.
        """
        name = block.get("name", "?")
        arguments = block.get("arguments", {})
        header = Text.assemble(("→ ", "yellow"), (name, "bold yellow"))
        self.console.print(header)
        if arguments:
            self.console.print(JSON.from_data(arguments), style="dim")

    def _render_tool_result(self, message: dict[str, Any]) -> None:
        """Render a tool result panel, truncating long output.

        Parameters
        ----------
        message : dict
            A message whose ``role`` is ``"toolResult"``. Output longer than
            ``_MAX_RESULT_CHARS`` is truncated with a trailing note.
        """
        is_error = message.get("isError", False)
        name = message.get("toolName", "tool")
        text = self._collect_text(message.get("content", []))

        if len(text) > _MAX_RESULT_CHARS:
            omitted = len(text) - _MAX_RESULT_CHARS
            text = f"{text[:_MAX_RESULT_CHARS]}\n… ({omitted} more characters)"

        self.console.print(
            Panel(
                Text(text or "(no output)"),
                title=f"{name} error" if is_error else name,
                border_style="red" if is_error else "grey50",
                expand=False,
            )
        )

    def _render_summary(self) -> None:
        """Render the closing summary line with the model and token count."""
        parts: list[str] = []
        if self._model:
            parts.append(self._model)
        if self._total_tokens:
            parts.append(f"{self._total_tokens} tokens")
        if parts:
            self.console.print(Text("  ".join(parts), style="dim italic"))

    @staticmethod
    def _collect_text(content: list[dict[str, Any]]) -> str:
        """Join the text blocks of a content list into a single string.

        Parameters
        ----------
        content : list of dict
            A message's content blocks. Only blocks of type ``"text"``
            contribute.

        Returns
        -------
        str
            The text blocks joined by newlines, stripped of surrounding
            whitespace.
        """
        return "\n".join(
            block.get("text", "") for block in content if block.get("type") == "text"
        ).strip()
