# Bosun

This application implements the [ralph loop](https://ghuntley.com/ralph/)
pattern against the [Pi](https://pi.dev) coding agent and open-source models
hosted on my [Spark DGX machine](https://build.nvidia.com/spark).

The inspiration for the name comes from shipping. The Bosun on the ship is the
person connecting the captain and the deckhands. They supervise the
day-to-day work on the ship and translate orders from the captain to the deck
hands doing the work. In this case, this tool takes care of the connection
between your plan and the code.

## Getting started

Download the sources, and run `uv pip install -e .` to install the package on
your machine. Then, run `bosun implement <spec-file>` to implement a
specification in your project.

## How does it work

First, start with a good quality plan. Write a `TASK.md` file with the plan
for whatever you want to build. You're the captain and you have to tell your
team what to build and how to verify the outcomes.

I recommend adding tasks the agent can check. Typical it looks like this:

```markdown
# Task title

## Goal

Describe the high-level goal for the plan

## Out-of-scope

Describe what's not to be done in the plan

## Tasks

- [ ] Task description
- [ ] Task description
- [ ] Task description
- [ ] Task description
- [ ] Task description
```

Then, you can run the Bosun tool and it will start iterating over your plan
implementing each of the sub tasks in the markdown file.

The agent will implement whatever quality spec you placed in the
input file. This means you have to spent more time writing a good quality spec
with the right sized tasks for your agent. Make sure you also have configured
your project correctly with a suitable validation suite, otherwise this fails
badly.

## Configuration

The application can be configured with these extra command-line arguments:

- `--iterations`: Controls how many attempts the agent takes to implement the
  full plan.
