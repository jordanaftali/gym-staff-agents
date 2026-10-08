"""The coordinator: talks to the gym manager. Its only tools are the workers."""

from __future__ import annotations

from typing import Any

from .approval import ApprovalGate
from .runner import run_agent, run_worker
from .workers import WORKERS

MORNING_BRIEF = (
    "Give me the morning brief: today is Wednesday. What's on the class schedule, "
    "which machines need attention, and which member issues need handling? "
    "Take care of anything you safely can and queue the rest for my approval."
)

SYSTEM = (
    "You are the coordinator for Iron Oak Gym. You talk to the gym manager. You cannot "
    "touch gym systems yourself: delegate every piece of work to the right worker with a "
    "clear, specific task. Then give the manager a short summary in three parts: done, "
    "waiting for your approval (with action numbers), and needs your attention. "
    "Never describe a queued action as done."
)


def worker_tool_specs() -> list[dict]:
    return [{
        "name": f"ask_{w.name}",
        "description": w.job,
        "input_schema": {
            "type": "object",
            "properties": {"task": {"type": "string", "description": "What this worker should do."}},
            "required": ["task"],
        },
    } for w in WORKERS.values()]


def run_coordinator(client: Any, model: str, request: str, gate: ApprovalGate) -> str:
    def call_tool(name: str, args: dict) -> str:
        worker_name = name.removeprefix("ask_")
        if not name.startswith("ask_") or worker_name not in WORKERS:
            raise PermissionError(f"Unknown worker tool '{name}'.")
        return run_worker(client, model, WORKERS[worker_name], args["task"], gate)

    return run_agent(client, model, SYSTEM, worker_tool_specs(), request, call_tool)
