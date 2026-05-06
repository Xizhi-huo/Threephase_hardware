from __future__ import annotations

from domain.phase_order_state import PhaseOrderState


def test_reset_methods_preserve_container_identity():
    state = PhaseOrderState.default()

    pt_orders_ref = state.pt_phase_orders
    pt1_ref = state.pt_phase_orders["PT1"]
    pt2_ref = state.pt_phase_orders["PT2"]
    pt3_ref = state.pt_phase_orders["PT3"]
    g1_ref = state.g1_blackbox_order
    g2_ref = state.g2_blackbox_order
    pt1_pri_ref = state.pt1_pri_blackbox_order
    pt1_sec_ref = state.pt1_sec_blackbox_order

    state.pt_phase_orders["PT1"][:] = ["B", "A", "C"]
    state.pt_phase_orders["PT2"][:] = ["C", "A", "B"]
    state.pt_phase_orders["PT3"][:] = ["A", "C", "B"]
    state.g1_blackbox_order[:] = ["B", "A", "C"]
    state.g2_blackbox_order[:] = ["A", "C", "B"]
    state.pt1_pri_blackbox_order[:] = ["C", "A", "B"]
    state.pt1_sec_blackbox_order[:] = ["B", "C", "A"]

    state.reset_pt_phase_orders()
    state.reset_blackbox_orders()

    assert state.pt_phase_orders is pt_orders_ref
    assert state.pt_phase_orders["PT1"] is pt1_ref
    assert state.pt_phase_orders["PT2"] is pt2_ref
    assert state.pt_phase_orders["PT3"] is pt3_ref
    assert state.g1_blackbox_order is g1_ref
    assert state.g2_blackbox_order is g2_ref
    assert state.pt1_pri_blackbox_order is pt1_pri_ref
    assert state.pt1_sec_blackbox_order is pt1_sec_ref

    assert state.pt_phase_orders == {
        "PT1": ["A", "B", "C"],
        "PT2": ["A", "B", "C"],
        "PT3": ["A", "B", "C"],
    }
    assert state.g1_blackbox_order == ["A", "B", "C"]
    assert state.g2_blackbox_order == ["A", "B", "C"]
    assert state.pt1_pri_blackbox_order == ["A", "B", "C"]
    assert state.pt1_sec_blackbox_order == ["A", "B", "C"]


def test_apply_methods_update_phase_orders_in_place():
    state = PhaseOrderState.default()

    pt1_ref = state.pt_phase_orders["PT1"]
    pt2_ref = state.pt_phase_orders["PT2"]
    pt3_ref = state.pt_phase_orders["PT3"]

    state.g2_blackbox_order[:] = ["A", "C", "B"]
    state.apply_g2_blackbox_to_pt3()
    assert state.pt_phase_orders["PT3"] is pt3_ref
    assert state.pt_phase_orders["PT3"] == ["A", "C", "B"]

    state.g1_blackbox_order[:] = ["B", "A", "C"]
    state.apply_pt1_blackbox_to_pt_phases(["C", "B", "A"])
    assert state.pt_phase_orders["PT2"] is pt2_ref
    assert state.pt_phase_orders["PT1"] is pt1_ref
    assert state.pt_phase_orders["PT2"] == ["B", "A", "C"]
    assert state.pt_phase_orders["PT1"] == ["C", "B", "A"]

