from __future__ import annotations

from domain.constants import DEFAULT_PT3_RATIO, E04_PT3_RATIO
from domain.enums import SystemMode
from domain.models import GeneratorState, SimulationState
from services.fault_manager import FaultManager


class _BlackboxHandlerStub:
    def __init__(self):
        self.pt1_syncs = 0
        self.pt2_syncs = 0

    def sync_g2_blackbox_to_phase_orders(self):
        pass

    def sync_pt1_blackbox_to_phase_orders(self):
        self.pt1_syncs += 1

    def sync_pt2_blackbox_to_phase_orders(self):
        self.pt2_syncs += 1


def _make_sim_state() -> SimulationState:
    return SimulationState(
        gen1=GeneratorState(freq=50.0, amp=10500.0, phase_deg=0.0),
        gen2=GeneratorState(freq=50.0, amp=10500.0, phase_deg=5.0),
        system_mode=SystemMode.ISOLATED_BUS,
    )


def _build_fault_manager():
    sim = _make_sim_state()
    updates = []
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
    blackbox_handler = _BlackboxHandlerStub()

    manager = FaultManager(
        sim_state=sim,
        blackbox_handler=blackbox_handler,
        append_assessment_event=lambda *args, **kwargs: None,
        request_pt_ratio_row_update=lambda attr, pri, sec: updates.append((attr, pri, sec)),
        set_last_fault_detected=lambda value: None,
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
    )
    return sim, updates, manager, pt_phase_orders, pt2_sec_order, blackbox_handler


def test_injecting_non_e04_fault_restores_pt3_ratio_after_e04():
    sim, updates, manager, _, _, _ = _build_fault_manager()

    manager.inject_fault("E04")
    assert sim.pt3_ratio == E04_PT3_RATIO
    assert updates[-1] == ("pt3_ratio", 11000, 93)

    manager.inject_fault("")
    assert sim.pt3_ratio == DEFAULT_PT3_RATIO
    assert updates[-1] == ("pt3_ratio", 11000, 193)


def test_e04_is_repaired_when_pt3_ratio_returns_to_default():
    sim, updates, manager, _, _, _ = _build_fault_manager()

    manager.inject_fault("E04")
    sim.pt3_ratio = DEFAULT_PT3_RATIO

    assert manager.maybe_repair_pt_ratio_fault("pt3_ratio", DEFAULT_PT3_RATIO)
    assert sim.fault_config.repaired is True
    assert sim.pt3_ratio == DEFAULT_PT3_RATIO
    assert updates[-1] == ("pt3_ratio", 11000, 193)


def test_e17_injects_pt2_secondary_blackbox_order_only():
    sim, _, manager, _, pt2_sec_order, blackbox_handler = _build_fault_manager()

    manager.inject_fault("E17")

    assert sim.fault_config.params["pt2_sec_blackbox_order"] == ["A", "C", "B"]
    assert pt2_sec_order == ["A", "C", "B"]
    assert blackbox_handler.pt2_syncs == 1
    assert blackbox_handler.pt1_syncs == 0
    assert manager.has_unrepaired_wiring_fault() is True


def test_e17_repair_resets_pt2_secondary_blackbox_order():
    _, _, manager, pt_phase_orders, pt2_sec_order, _ = _build_fault_manager()

    manager.inject_fault("E17")
    manager.repair_fault(step=4, source="PT2_blackbox")

    assert pt2_sec_order == ["A", "B", "C"]
    assert pt_phase_orders["PT2"] == ["A", "B", "C"]
    assert manager.has_unrepaired_wiring_fault() is False
