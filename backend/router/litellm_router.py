"""Compatibility wrappers matching the bootcamp LiteLLM examples."""

from backend.models.llm import chat


def planner(messages: list[dict]) -> str:
    return chat("planner", messages)


def coder(messages: list[dict]) -> str:
    return chat("coder", messages)


def reasoning(messages: list[dict]) -> str:
    return chat("reasoning", messages)
