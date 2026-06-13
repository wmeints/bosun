from pathlib import Path

from bosun.prompt import TaskPrompt


def test_renders_input_file_placeholder(tmp_path: Path) -> None:
    template_file = tmp_path / "task.md"
    template_file.write_text("Read {{input_file}} and implement it.")

    prompt = TaskPrompt(template_file)
    rendered = prompt.render(input_file="PLAN.md")

    assert rendered == "Read PLAN.md and implement it."


def test_default_template_renders_the_input_file() -> None:
    rendered = TaskPrompt().render(input_file="PLAN.md")

    assert "PLAN.md" in rendered
    assert "{{input_file}}" not in rendered
