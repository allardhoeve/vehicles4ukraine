# CLAUDE.md

## Project

Vehicle scouting system that crawls Dutch car platforms to find cheap, reliable vehicles for export to Ukraine.

## Tooling

- Python package/venv management: always use `uv` (not pip, not venv)
  - `uv init`, `uv add <package>`, `uv run python ...`
- Tasks/planning: `todo/tasks/` directory, follow `task-template.md`

## Running

```bash
uv run python search.py
```
