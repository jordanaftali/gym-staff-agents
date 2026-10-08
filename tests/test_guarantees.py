import json

import pytest

from gym_agents import ApprovalGate, GymState, run_coordinator
from gym_agents.coordinator import worker_tool_specs
from gym_agents.runner import run_worker
from gym_agents.tools import TOOLS
from gym_agents.workers import WORKERS

from .fake_client import FakeClient, reply, text, tool_use


@pytest.fixture
def gate():
    return ApprovalGate(GymState())


def test_safe_tool_runs_immediately(gate):
    client = FakeClient([
        reply(tool_use("check_in_member", {"member_id": "M001"})),
        reply(text("Ana is checked in.")),
    ])
    answer = run_worker(client, "m", WORKERS["front_desk"], "Check in Ana", gate)

    assert answer == "Ana is checked in."
    assert gate.state.check_ins == ["M001"]
    assert gate.waiting() == []


def test_risky_tool_is_queued_not_run(gate):
    client = FakeClient([
        reply(tool_use("issue_refund", {"member_id": "M002", "amount": 59, "reason": "double charge"})),
        reply(text("Refund is waiting for approval (#1).")),
    ])
    run_worker(client, "m", WORKERS["membership"], "Refund Marcus", gate)

    assert gate.state.refunds == []                      # no money moved
    assert len(gate.waiting()) == 1
    result = client.last_tool_results()[0]["content"]
    assert result.startswith("NOT carried out")          # agent is told the truth


def test_approved_action_runs_once(gate):
    gate.execute("membership", "issue_refund", {"member_id": "M002", "amount": 59, "reason": "double charge"})
    gate.approve(1, by="manager")

    assert gate.state.refunds == [{"member_id": "M002", "amount": 59, "reason": "double charge"}]
    with pytest.raises(KeyError):                         # can't approve twice
        gate.approve(1)


def test_rejected_action_never_runs(gate):
    gate.execute("front_desk", "post_announcement", {"text": "Free smoothies!"})
    gate.reject(1, by="manager")

    assert gate.state.announcements == []
    assert gate.waiting() == []
    with pytest.raises(KeyError):
        gate.approve(1)


def test_worker_cannot_use_tool_outside_its_job(gate):
    client = FakeClient([
        reply(tool_use("issue_refund", {"member_id": "M002", "amount": 59, "reason": "x"})),
        reply(text("I can't do that.")),
    ])
    run_worker(client, "m", WORKERS["equipment"], "Refund Marcus", gate)

    result = client.last_tool_results()[0]
    assert result["is_error"] is True
    assert "not one of equipment's tools" in result["content"]
    assert gate.waiting() == [] and gate.state.refunds == []


def test_tool_errors_go_back_to_the_model(gate):
    client = FakeClient([
        reply(tool_use("check_in_member", {"member_id": "M999"})),
        reply(text("No such member.")),
    ])
    run_worker(client, "m", WORKERS["front_desk"], "Check in M999", gate)
    assert client.last_tool_results()[0]["is_error"] is True


def test_past_due_member_is_not_checked_in(gate):
    gate.execute("front_desk", "check_in_member", {"member_id": "M004"})
    assert gate.state.check_ins == []


def test_coordinator_only_has_worker_tools():
    names = {spec["name"] for spec in worker_tool_specs()}
    assert names == {f"ask_{w}" for w in WORKERS}
    assert names.isdisjoint(TOOLS)


def test_coordinator_delegates_through_workers(gate):
    client = FakeClient([
        reply(tool_use("ask_equipment", {"task": "Handle the leg press"})),            # coordinator
        reply(tool_use("mark_out_of_order", {"equipment_id": "E03", "note": "Seat pin missing"})),  # worker
        reply(tool_use("order_part", {"equipment_id": "E03", "part": "seat pin", "cost": 24.0}, id="tu_2")),
        reply(text("Leg press tagged; pin order waiting for approval (#1).")),         # worker done
        reply(text("Done: leg press out of order. Waiting: #1 seat pin order.")),       # coordinator done
    ])
    answer = run_coordinator(client, "m", "Leg press seat pin is missing", gate)

    assert "Waiting" in answer
    assert gate.state.equipment["E03"]["status"] == "out_of_order"   # safe action ran
    assert gate.state.part_orders == []                               # spending waits
    assert [a.tool for a in gate.waiting()] == ["order_part"]


def test_every_worker_tool_exists():
    for worker in WORKERS.values():
        for tool in worker.tools:
            assert tool in TOOLS, f"{worker.name} lists unknown tool {tool}"


def test_audit_log_is_written(tmp_path):
    path = tmp_path / "audit.jsonl"
    gate = ApprovalGate(GymState(), audit_path=path)
    gate.execute("front_desk", "check_in_member", {"member_id": "M001"})
    gate.execute("membership", "freeze_membership", {"member_id": "M003", "months": 2})
    gate.approve(1, by="manager")

    events = [json.loads(line)["event"] for line in path.read_text().splitlines()]
    assert events == ["auto", "queued", "approved_by:manager"]
