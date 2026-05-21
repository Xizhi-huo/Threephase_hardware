from __future__ import annotations

from domain.assessment import AssessmentEventType
from domain.models import FaultConfig
from services.blackbox_repair_handler import BlackboxRepairHandler
from services.flow_mode_manager import FlowModeManager
from tests.support.stubs import make_sim_state


class _FaultManagerStub:
    def __init__(self, sim, repairs, all_normal):
        self._sim = sim
        self._repairs = repairs
        self._all_normal = all_normal

    def all_repairable_wiring_targets_normal(self):
        return self._all_normal()

    def repair_fault(self, step: int, source: str):
        self._sim.fault_config.repaired = True
        self._sim.fault_config.detected = False
        self._repairs.append((step, source))


def _build_handler():
    sim = make_sim_state()
    sim.fault_config = FaultConfig(
        scenario_id="E03",
        active=True,
        detected=True,
        repaired=False,
        params={"pt3_a_reversed": True},
    )
    flow_mgr = FlowModeManager()
    events = []
    repairs = []
    pt_phase_orders = {
        "PT1": ["A", "B", "C"],
        "PT2": ["A", "B", "C"],
        "PT3": ["A", "B", "C"],
    }
    g1_order = ["A", "B", "C"]
    g2_order = ["A", "B", "C"]
    pt1_pri_order = ["A", "B", "C"]
    pt1_sec_order = ["A", "B", "C"]
    pt2_sec_order = ["A", "B", "C"]

    handler = BlackboxRepairHandler(
        sim_state=sim,
        flow_mgr=flow_mgr,
        get_fault_mgr=lambda: _FaultManagerStub(
            sim,
            repairs,
            all_normal=lambda: pt2_sec_order == ["A", "B", "C"],
        ),
        append_assessment_event=lambda event_type, **payload: events.append((event_type, payload)),
        get_pt_phase_orders=lambda: pt_phase_orders,
        get_g1_blackbox_order=lambda: g1_order,
        set_g1_blackbox_order=lambda value: g1_order.__setitem__(slice(None), value),
        get_g2_blackbox_order=lambda: g2_order,
        set_g2_blackbox_order=lambda value: g2_order.__setitem__(slice(None), value),
        get_pt1_pri_blackbox_order=lambda: pt1_pri_order,
        set_pt1_pri_blackbox_order=lambda value: pt1_pri_order.__setitem__(slice(None), value),
        get_pt1_sec_blackbox_order=lambda: pt1_sec_order,
        set_pt1_sec_blackbox_order=lambda value: pt1_sec_order.__setitem__(slice(None), value),
        get_pt2_sec_blackbox_order=lambda: pt2_sec_order,
        set_pt2_sec_blackbox_order=lambda value: pt2_sec_order.__setitem__(slice(None), value),
        apply_g2_blackbox_to_pt3=lambda: pt_phase_orders.__setitem__("PT3", list(g2_order)),
        apply_pt1_blackbox_to_pt_phases=lambda value: pt_phase_orders.__setitem__("PT1", list(value)),
        apply_pt2_blackbox_to_pt2=lambda: pt_phase_orders.__setitem__("PT2", list(pt2_sec_order)),
    )
    return sim, events, repairs, handler, pt_phase_orders, pt2_sec_order


def test_e03_pt3_polarity_repair_clears_fault():
    sim, events, repairs, handler, _, _ = _build_handler()

    runtime_state = handler.get_blackbox_runtime_state("PT3")
    assert runtime_state["sec_polarity"] == [-1, 1, 1]

    outcome = handler.apply_blackbox_repair_attempt(
        "PT3",
        step=2,
        initial_sec_order=["A", "B", "C"],
        new_sec_order=["A", "B", "C"],
        initial_sec_polarity=[-1, 1, 1],
        new_sec_polarity=[1, 1, 1],
    )

    assert outcome.component_correct is True
    assert outcome.fault_cleared is True
    assert sim.fault_config.repaired is True
    assert repairs == [(2, "PT3_polarity_blackbox")]
    assert any(
        event_type == AssessmentEventType.BLACKBOX_SWAP
        and payload["target"] == "PT3"
        and payload["layer"] == "polarity"
        for event_type, payload in events
    )


def test_e03_pt3_polarity_must_be_normal_to_clear_fault():
    sim, events, repairs, handler, _, _ = _build_handler()

    outcome = handler.apply_blackbox_repair_attempt(
        "PT3",
        step=2,
        initial_sec_order=["A", "B", "C"],
        new_sec_order=["A", "B", "C"],
        initial_sec_polarity=[-1, 1, 1],
        new_sec_polarity=[-1, 1, 1],
    )

    assert outcome.component_correct is False
    assert outcome.fault_cleared is False
    assert sim.fault_config.repaired is False
    assert repairs == []
    assert any(
        event_type == AssessmentEventType.BLACKBOX_CONFIRM_ATTEMPTED
        and payload["target"] == "PT3"
        and payload["success"] is False
        for event_type, payload in events
    )


def test_pt2_secondary_repair_updates_pt2_blackbox_order():
    sim, events, repairs, handler, pt_phase_orders, pt2_sec_order = _build_handler()
    sim.fault_config = FaultConfig(
        scenario_id="E17",
        active=True,
        detected=True,
        repaired=False,
        params={"pt2_sec_blackbox_order": ["A", "C", "B"]},
    )
    pt2_sec_order[:] = ["A", "C", "B"]

    runtime_state = handler.get_blackbox_runtime_state("PT2")
    assert runtime_state["sec_order"] == ["A", "C", "B"]

    outcome = handler.apply_blackbox_repair_attempt(
        "PT2",
        step=4,
        initial_sec_order=["A", "C", "B"],
        new_sec_order=["A", "B", "C"],
    )

    assert outcome.component_correct is True
    assert outcome.fault_cleared is True
    assert repairs == [(4, "PT2_blackbox")]
    assert pt2_sec_order == ["A", "B", "C"]
    assert pt_phase_orders["PT2"] == ["A", "B", "C"]
    assert any(
        event_type == AssessmentEventType.BLACKBOX_SWAP
        and payload["target"] == "PT2"
        and payload["layer"] == "secondary"
        for event_type, payload in events
    )
