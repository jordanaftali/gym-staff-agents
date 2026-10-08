"""Gym tools.

Each tool is a plain Python function plus a description the model reads.
`requires_approval=True` marks anything that spends money, commits the gym
to a member, or goes public. Those never run until a human approves them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .data import GymState


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input_schema: dict
    func: Callable[..., Any]
    requires_approval: bool = False

    def spec(self) -> dict:
        """The tool definition sent to the model."""
        note = " Requires staff approval before it happens." if self.requires_approval else ""
        return {
            "name": self.name,
            "description": self.description + note,
            "input_schema": self.input_schema,
        }


def _obj(props: dict, required: list[str] | None = None) -> dict:
    return {"type": "object", "properties": props, "required": required or list(props)}


_STR = {"type": "string"}
_NUM = {"type": "number"}
_INT = {"type": "integer"}


def _member(state: GymState, member_id: str) -> dict:
    if member_id not in state.members:
        raise ValueError(f"No member with id {member_id}")
    return state.members[member_id]


# ---------- Front desk ----------

def lookup_member(state: GymState, name: str) -> list[dict]:
    q = name.lower()
    return [{"member_id": mid, **m} for mid, m in state.members.items() if q in m["name"].lower()]


def check_in_member(state: GymState, member_id: str) -> str:
    m = _member(state, member_id)
    if m["status"] != "active":
        return f"{m['name']} is {m['status']} (balance due ${m['balance_due']:.2f}). Not checked in; send them to the desk."
    state.check_ins.append(member_id)
    return f"{m['name']} checked in."


def draft_member_message(state: GymState, member_id: str, text: str) -> str:
    m = _member(state, member_id)
    state.drafts.append({"member_id": member_id, "text": text})
    return f"Draft saved for {m['name']}. It has not been sent."


def send_member_message(state: GymState, member_id: str, text: str) -> str:
    m = _member(state, member_id)
    state.sent_messages.append({"member_id": member_id, "text": text})
    return f"Message sent to {m['name']}."


def post_announcement(state: GymState, text: str) -> str:
    state.announcements.append(text)
    return "Announcement posted to the gym's social accounts and lobby screen."


# ---------- Classes & trainers ----------

def list_classes(state: GymState, day: str) -> list[dict]:
    d = day.lower()
    return [{"class_id": cid, **c} for cid, c in state.classes.items() if c["day"] == d]


def trainer_availability(state: GymState, trainer: str) -> dict:
    if trainer not in state.trainers:
        raise ValueError(f"No trainer named {trainer}. Trainers: {', '.join(state.trainers)}")
    return state.trainers[trainer]


def book_personal_training(state: GymState, member_id: str, trainer: str, slot: str) -> str:
    m = _member(state, member_id)
    t = trainer_availability(state, trainer)
    if slot not in t["open_slots"]:
        raise ValueError(f"{trainer} is not free at {slot}. Open: {t['open_slots']}")
    t["open_slots"].remove(slot)
    state.bookings.append({"member_id": member_id, "trainer": trainer, "slot": slot})
    return f"Booked {m['name']} with {trainer} on {slot}."


def cancel_class(state: GymState, class_id: str, reason: str) -> str:
    if class_id not in state.classes:
        raise ValueError(f"No class with id {class_id}")
    c = state.classes.pop(class_id)
    return f"Cancelled {c['name']} ({c['day']} {c['time']}); {c['booked']} booked members will be notified. Reason: {reason}"


# ---------- Equipment ----------

def list_equipment_issues(state: GymState) -> list[dict]:
    return [{"equipment_id": eid, **e} for eid, e in state.equipment.items()
            if e["issue"] or e["status"] != "in_service"]


def mark_out_of_order(state: GymState, equipment_id: str, note: str) -> str:
    if equipment_id not in state.equipment:
        raise ValueError(f"No equipment with id {equipment_id}")
    e = state.equipment[equipment_id]
    e["status"] = "out_of_order"
    e["issue"] = note
    return f"{e['name']} marked out of order and tagged on the floor."


def order_part(state: GymState, equipment_id: str, part: str, cost: float) -> str:
    if equipment_id not in state.equipment:
        raise ValueError(f"No equipment with id {equipment_id}")
    state.part_orders.append({"equipment_id": equipment_id, "part": part, "cost": cost})
    return f"Ordered {part} for {state.equipment[equipment_id]['name']} (${cost:.2f})."


# ---------- Membership & billing ----------

def membership_status(state: GymState, member_id: str) -> dict:
    return {"member_id": member_id, **_member(state, member_id)}


def freeze_membership(state: GymState, member_id: str, months: int) -> str:
    m = _member(state, member_id)
    m["status"] = "frozen"
    m["frozen_months"] = months
    return f"{m['name']}'s membership frozen for {months} month(s)."


def issue_refund(state: GymState, member_id: str, amount: float, reason: str) -> str:
    m = _member(state, member_id)
    state.refunds.append({"member_id": member_id, "amount": amount, "reason": reason})
    return f"Refunded ${amount:.2f} to {m['name']}."


TOOLS: dict[str, Tool] = {t.name: t for t in [
    Tool("lookup_member", "Find members by (part of) their name.", _obj({"name": _STR}), lookup_member),
    Tool("check_in_member", "Check a member in at the front desk.", _obj({"member_id": _STR}), check_in_member),
    Tool("draft_member_message", "Save a draft message to a member for staff to review. Does not send.",
         _obj({"member_id": _STR, "text": _STR}), draft_member_message),
    Tool("send_member_message", "Send a message to a member by email/SMS.",
         _obj({"member_id": _STR, "text": _STR}), send_member_message, requires_approval=True),
    Tool("post_announcement", "Post a public announcement to the gym's social accounts and lobby screen.",
         _obj({"text": _STR}), post_announcement, requires_approval=True),

    Tool("list_classes", "List group classes on a day of the week (e.g. 'monday').",
         _obj({"day": _STR}), list_classes),
    Tool("trainer_availability", "Show a personal trainer's specialty and open slots.",
         _obj({"trainer": _STR}), trainer_availability),
    Tool("book_personal_training", "Book a member into a trainer's open slot (slot text must match exactly).",
         _obj({"member_id": _STR, "trainer": _STR, "slot": _STR}), book_personal_training, requires_approval=True),
    Tool("cancel_class", "Cancel a group class and notify everyone booked.",
         _obj({"class_id": _STR, "reason": _STR}), cancel_class, requires_approval=True),

    Tool("list_equipment_issues", "List equipment that is broken or has a reported issue.",
         _obj({}), list_equipment_issues),
    Tool("mark_out_of_order", "Take a machine out of service right away for safety. Reversible.",
         _obj({"equipment_id": _STR, "note": _STR}), mark_out_of_order),
    Tool("order_part", "Order a replacement part from the supplier.",
         _obj({"equipment_id": _STR, "part": _STR, "cost": _NUM}), order_part, requires_approval=True),

    Tool("membership_status", "Show a member's plan, status, balance and notes.",
         _obj({"member_id": _STR}), membership_status),
    Tool("freeze_membership", "Freeze a member's membership for a number of months.",
         _obj({"member_id": _STR, "months": _INT}), freeze_membership, requires_approval=True),
    Tool("issue_refund", "Refund money to a member's card.",
         _obj({"member_id": _STR, "amount": _NUM, "reason": _STR}), issue_refund, requires_approval=True),
]}
