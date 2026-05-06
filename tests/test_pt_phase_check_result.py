from __future__ import annotations

from domain.enums import BreakerPosition
from domain.models import GeneratorState, SimulationState
from domain.test_states import PtPhaseCheckState
from services.flow_mode_manager import FlowModeManager
from services.pt_phase_check_service import PtPhaseCheckService


def _make_sim_state() -> SimulationState:
    return SimulationState(
        gen1=GeneratorState(freq=50.0, amp=10500.0, phase_deg=0.0),
        gen2=GeneratorState(freq=50.0, amp=10500.0, phase_deg=5.0),
    )


def _build_service():
    sim = _make_sim_state()
    sim.grounding_mode = "小电阻接地"
    sim.gen1.breaker_position = BreakerPosition.WORKING
    sim.gen1.breaker_closed = True
    sim.gen2.running = True
    sim.gen2.breaker_closed = False

    state = PtPhaseCheckState(started=True)
    detected = []

    service = PtPhaseCheckService(
        sim_state=sim,
        flow_mgr=FlowModeManager(),
        get_physics=lambda: object(),
        get_pt_phase_check_state=lambda: state,
        set_pt_phase_check_state=lambda next_state: None,
        is_loop_test_complete=lambda: True,
        is_pt_voltage_check_complete=lambda: True,
        append_assessment_event=lambda *args, **kwargs: None,
        mark_fault_detected=lambda **kwargs: detected.append(kwargs),
        set_pt_phase_check_feedback=lambda message, color: (
            setattr(state, "feedback", message),
            setattr(state, "feedback_color", color),
        ),
        mark_pt_phase_check_completed=lambda: setattr(state, "completed", True),
    )
    return state, service


def test_phase_sequence_pass_is_not_reported_until_both_pts_are_recorded():
    state, service = _build_service()

    assert service.record_phase_sequence("PT1", "ABC", origin="simulated")
    assert state.result is None

    assert service.record_phase_sequence("PT3", "ABC", origin="simulated")
    assert state.result == "pass"


def test_phase_sequence_positive_rotations_are_accepted():
    state, service = _build_service()

    assert service.record_phase_sequence("PT1", "BCA", origin="simulated")
    assert state.result is None
    assert state.records["PT1"]["measurement_id"] == "phase_sequence.PT1"
    assert state.records["PT1"]["sequence"] == "BCA"
    assert state.records["PT1"]["passed"] is True

    assert service.record_phase_sequence("PT3", "CAB", origin="simulated")
    assert state.result == "pass"
    assert state.records["PT3"]["measurement_id"] == "phase_sequence.PT3"
    assert state.records["PT3"]["sequence"] == "CAB"
    assert state.records["PT3"]["passed"] is True


def test_phase_sequence_failure_is_not_overwritten_by_later_pass():
    state, service = _build_service()

    assert service.record_phase_sequence("PT1", "ACB", origin="simulated")
    assert state.result == "fail"
    assert state.records["PT1"]["quality"] == "out_of_range"

    assert service.record_phase_sequence("PT3", "ABC", origin="simulated")
    assert state.result == "fail"
