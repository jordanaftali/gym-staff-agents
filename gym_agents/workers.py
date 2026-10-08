"""The four workers. Each one: a short job description and an allow-list of tools."""

from __future__ import annotations

from dataclasses import dataclass

from .tools import TOOLS

_SHARED = (
    "You work at Iron Oak Gym, a small independent strength gym. Be brief and factual. "
    "Only use your tools; never invent members, prices or times. Some actions need staff "
    "approval: if a tool result says NOT carried out, report it as waiting for approval."
)


@dataclass(frozen=True)
class Worker:
    name: str
    job: str
    tools: tuple[str, ...]

    @property
    def system_prompt(self) -> str:
        return f"{_SHARED}\n\nYour job: {self.job}"

    def tool_specs(self) -> list[dict]:
        return [TOOLS[t].spec() for t in self.tools]


WORKERS: dict[str, Worker] = {w.name: w for w in [
    Worker(
        "front_desk",
        "Front desk. Check members in, answer member questions, draft and send member "
        "messages, and post gym announcements.",
        ("lookup_member", "check_in_member", "draft_member_message",
         "send_member_message", "post_announcement"),
    ),
    Worker(
        "classes",
        "Classes and coaching. Know the group class schedule and trainer availability, "
        "book personal training sessions, and cancel classes when needed.",
        ("list_classes", "trainer_availability", "book_personal_training", "cancel_class"),
    ),
    Worker(
        "equipment",
        "Equipment and safety. Track broken machines. If a machine could hurt someone, "
        "take it out of order immediately. Order replacement parts.",
        ("list_equipment_issues", "mark_out_of_order", "order_part"),
    ),
    Worker(
        "membership",
        "Memberships and billing. Look up plans and balances, handle freezes and refunds. "
        "Check the member's notes before acting.",
        ("lookup_member", "membership_status", "freeze_membership", "issue_refund"),
    ),
]}
