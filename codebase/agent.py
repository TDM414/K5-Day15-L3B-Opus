"""Batch/eval entry point; shares extraction, menu filtering and cart validation with web."""
from workflow import run_text


def answer(text: str) -> dict:
    """Run one isolated Lunchie request and return the runner contract."""
    return {"output": run_text(text)}
