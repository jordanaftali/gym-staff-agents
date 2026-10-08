"""The tool-use loop shared by the coordinator and every worker."""

from __future__ import annotations

import json
from typing import Any, Callable

from .approval import ApprovalGate
from .workers import Worker

DEFAULT_MODEL = "claude-sonnet-5-5"
MAX_TURNS = 10


def _block_to_dict(block: Any) -> dict:
    if block.type == "text":
        return {"type": "text", "text": block.text}
    if block.type == "tool_use":
        return {"type": "tool_use", "id": block.id, "name": block.name, "input": block.input}
    raise ValueError(f"Unexpected content block: {block.type}")


def run_agent(
    client: Any,
    model: str,
    system: str,
    tools: list[dict],
    task: str,
    call_tool: Callable[[str, dict], Any],
    max_turns: int = MAX_TURNS,
) -> str:
    """Ask the model, run whatever tools it calls, repeat until it answers in text."""
    messages: list[dict] = [{"role": "user", "content": task}]
    for _ in range(max_turns):
        response = client.messages.create(
            model=model, max_tokens=1500, system=system, tools=tools, messages=messages,
        )
        if response.stop_reason != "tool_use":
            return "".join(b.text for b in response.content if b.type == "text").strip()

        messages.append({"role": "assistant", "content": [_block_to_dict(b) for b in response.content]})
        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            try:
                output = call_tool(block.name, block.input)
                content, is_error = (output if isinstance(output, str)
                                     else json.dumps(output, default=str)), False
            except Exception as exc:  # report errors back to the model instead of crashing
                content, is_error = f"Error: {exc}", True
            results.append({"type": "tool_result", "tool_use_id": block.id,
                            "content": content, "is_error": is_error})
        messages.append({"role": "user", "content": results})
    return "Stopped: too many steps without a final answer."


def run_worker(client: Any, model: str, worker: Worker, task: str, gate: ApprovalGate) -> str:
    def call_tool(name: str, args: dict) -> Any:
        if name not in worker.tools:  # enforced in code, not just in the prompt
            raise PermissionError(f"'{name}' is not one of {worker.name}'s tools.")
        return gate.execute(worker.name, name, args)

    return run_agent(client, model, worker.system_prompt, worker.tool_specs(), task, call_tool)
