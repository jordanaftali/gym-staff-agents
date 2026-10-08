"""Command-line entry point.

    python main.py                                      # the morning brief
    python main.py "Marcus says he was charged twice"   # any request
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from gym_agents import MORNING_BRIEF, ApprovalGate, GymState, run_coordinator
from gym_agents.runner import DEFAULT_MODEL


def review_approvals(gate: ApprovalGate) -> None:
    waiting = gate.waiting()
    if not waiting:
        print("\nNothing waiting for approval.")
        return
    print(f"\n{len(waiting)} action(s) waiting for your approval:\n")
    for action in waiting:
        print(f"  #{action.id}  [{action.worker}] {action.tool}")
        for key, value in action.args.items():
            print(f"        {key}: {value}")
        answer = input("  Approve? [y/N] ").strip().lower()
        if answer == "y":
            try:
                print("  ->", gate.approve(action.id, by="manager"))
            except Exception as exc:
                print("  -> Failed:", exc)
        else:
            gate.reject(action.id, by="manager")
            print("  -> Rejected. Nothing happened.")
        print()


def main() -> None:
    try:
        import anthropic
    except ImportError:
        sys.exit("Install requirements first: pip install -r requirements.txt")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("Set ANTHROPIC_API_KEY first (see .env.example).")

    request = " ".join(sys.argv[1:]) or MORNING_BRIEF
    model = os.environ.get("GYM_AGENTS_MODEL", DEFAULT_MODEL)
    gate = ApprovalGate(GymState(), audit_path=Path("audit.jsonl"))

    print(f"Request: {request}\n")
    answer = run_coordinator(anthropic.Anthropic(), model, request, gate)
    print(answer)
    review_approvals(gate)
    print("Every action and decision is logged in audit.jsonl.")


if __name__ == "__main__":
    main()
