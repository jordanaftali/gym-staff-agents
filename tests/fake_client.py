"""A scripted stand-in for the Anthropic client, so tests run offline."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace


def text(t: str) -> SimpleNamespace:
    return SimpleNamespace(type="text", text=t)


def tool_use(name: str, args: dict, id: str = "tu_1") -> SimpleNamespace:
    return SimpleNamespace(type="tool_use", id=id, name=name, input=args)


def reply(*blocks: SimpleNamespace) -> SimpleNamespace:
    stop = "tool_use" if any(b.type == "tool_use" for b in blocks) else "end_turn"
    return SimpleNamespace(content=list(blocks), stop_reason=stop)


@dataclass
class FakeClient:
    """Returns scripted replies in order and records every request."""
    script: list
    calls: list = field(default_factory=list)

    def __post_init__(self):
        self.messages = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if not self.script:
            raise AssertionError("Fake client ran out of scripted replies")
        return self.script.pop(0)

    def last_tool_results(self, call_index: int = -1) -> list[dict]:
        return self.calls[call_index]["messages"][-1]["content"]
