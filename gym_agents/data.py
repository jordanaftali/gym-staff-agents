"""In-memory demo gym.

Everything the agents can see or change lives in one GymState object.
A real deployment would swap this for the gym's member system, booking
app, maintenance tracker and payment processor.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field

_MEMBERS = {
    "M001": {"name": "Ana Souza", "plan": "Monthly Unlimited", "status": "active",
             "balance_due": 0.0, "last_visit": "2026-10-06"},
    "M002": {"name": "Marcus Lee", "plan": "Monthly Unlimited", "status": "active",
             "balance_due": 0.0, "last_visit": "2026-09-30",
             "note": "Says he was charged twice for October ($59 x2)."},
    "M003": {"name": "Priya Shah", "plan": "Annual", "status": "active",
             "balance_due": 0.0, "last_visit": "2026-08-12",
             "note": "Asked by email about freezing her membership for 2 months (knee surgery recovery)."},
    "M004": {"name": "Diego Ramos", "plan": "Class Pack (10)", "status": "past_due",
             "balance_due": 89.0, "last_visit": "2026-10-01"},
}

_CLASSES = {
    "C101": {"name": "Strength Basics", "day": "monday", "time": "06:00",
             "coach": "Dani", "booked": 11, "capacity": 14},
    "C102": {"name": "Spin", "day": "monday", "time": "18:00",
             "coach": "Leo", "booked": 20, "capacity": 20},
    "C201": {"name": "Olympic Lifting", "day": "tuesday", "time": "07:00",
             "coach": "Dani", "booked": 6, "capacity": 10},
    "C301": {"name": "Mobility & Recovery", "day": "wednesday", "time": "12:00",
             "coach": "Leo", "booked": 3, "capacity": 15},
    "C302": {"name": "HIIT", "day": "wednesday", "time": "18:30",
             "coach": "Dani", "booked": 15, "capacity": 16},
}

_TRAINERS = {
    "Dani": {"specialty": "strength, powerlifting",
             "open_slots": ["tuesday 10:00", "wednesday 15:00", "friday 09:00"]},
    "Leo": {"specialty": "cardio, mobility, rehab-friendly training",
            "open_slots": ["monday 12:00", "thursday 17:00"]},
}

_EQUIPMENT = {
    "E01": {"name": "Treadmill #3", "status": "in_service", "issue": "Belt slipping at high speed"},
    "E02": {"name": "Cable crossover", "status": "in_service", "issue": None},
    "E03": {"name": "Leg press", "status": "in_service", "issue": "Seat pin missing"},
    "E04": {"name": "Rowing machine #1", "status": "out_of_order", "issue": "Display dead, waiting on part"},
}


@dataclass
class GymState:
    members: dict = field(default_factory=lambda: copy.deepcopy(_MEMBERS))
    classes: dict = field(default_factory=lambda: copy.deepcopy(_CLASSES))
    trainers: dict = field(default_factory=lambda: copy.deepcopy(_TRAINERS))
    equipment: dict = field(default_factory=lambda: copy.deepcopy(_EQUIPMENT))
    check_ins: list = field(default_factory=list)
    drafts: list = field(default_factory=list)
    sent_messages: list = field(default_factory=list)
    announcements: list = field(default_factory=list)
    bookings: list = field(default_factory=list)
    part_orders: list = field(default_factory=list)
    refunds: list = field(default_factory=list)
