"""The approval gate and audit trail.

This is where the safety rule actually lives. The model is *told* that some
actions need approval, but this code is what stops them from happening.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .data import GymState
from .tools import TOOLS


@dataclass
class PendingAction:
    id: int
    worker: str
    tool: str
    args: dict
    status: str = "pending"  # pending | approved | rejected


@dataclass
class ApprovalGate:
    state: GymState
    audit_path: Path | None = None
    pending: list[PendingAction] = field(default_factory=list)
    audit: list[dict] = field(default_factory=list)
    _next_id: int = 1

    def _log(self, event: str, worker: str, tool: str, args: dict, result: Any = None) -> None:
        entry = {
            "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "event": event, "worker": worker, "tool": tool, "args": args,
        }
        if result is not None:
            entry["result"] = result
        self.audit.append(entry)
        if self.audit_path:
            with open(self.audit_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")

    def _run(self, tool: str, args: dict) -> Any:
        return TOOLS[tool].func(self.state, **args)

    def execute(self, worker: str, tool: str, args: dict) -> Any:
        """Run a safe tool now, or queue a risky one and say so honestly."""
        if TOOLS[tool].requires_approval:
            action = PendingAction(self._next_id, worker, tool, args)
            self._next_id += 1
            self.pending.append(action)
            self._log("queued", worker, tool, args)
            return (f"NOT carried out. '{tool}' needs staff approval and is queued as "
                    f"action #{action.id}. Report it as waiting for approval, not as done.")
        result = self._run(tool, args)
        self._log("auto", worker, tool, args, result)
        return result

    def waiting(self) -> list[PendingAction]:
        return [a for a in self.pending if a.status == "pending"]

    def _get(self, action_id: int) -> PendingAction:
        for a in self.pending:
            if a.id == action_id and a.status == "pending":
                return a
        raise KeyError(f"No pending action #{action_id}")

    def approve(self, action_id: int, by: str = "staff") -> Any:
        a = self._get(action_id)
        a.status = "approved"
        result = self._run(a.tool, a.args)
        self._log(f"approved_by:{by}", a.worker, a.tool, a.args, result)
        return result

    def reject(self, action_id: int, by: str = "staff") -> None:
        a = self._get(action_id)
        a.status = "rejected"
        self._log(f"rejected_by:{by}", a.worker, a.tool, a.args)
