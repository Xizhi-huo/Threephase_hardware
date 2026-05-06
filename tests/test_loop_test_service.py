from __future__ import annotations

from types import SimpleNamespace

from domain.assessment import AssessmentEventType
from domain.enums import BreakerPosition
from domain.models import FaultConfig
from domain.test_states import LOOP_TEST_RECORD_KEYS, LoopTestState
from services.flow_mode_manager import FlowModeManager
from services.loop_test_service import LoopTestService
from tests.support.stubs import make_sim_state


def _ready_loop_sim():
    sim = make_sim_state()
    sim.grounding_mode = "断开"
    sim.multimeter_mode = True
    sim.gen1.mode = "manual"
    sim.gen2.mode = "manual"
    sim.gen1.breaker_closed = True
    sim.gen2.breaker_closed = True
    sim.gen1.breaker_position = BreakerPosition.WORKING
    sim.gen2.breaker_position = BreakerPosition.WORKING
    return sim


def _make_service(sim, state, physics, *, detected=None, exited=None):
    detected = [] if detected is None else detected
    exited = [] if exited is None else exited
    events = []

    def append_event(event_type, step=0, **payload):
        events.append((event_type, step, payload))

    service = LoopTestService(
        sim_state=sim,
        flow_mgr=FlowModeManager(),
        get_physics=lambda: physics,
        get_loop_test_state=lambda: state,
        set_loop_test_state=lambda next_state: None,
        append_assessment_event=append_event,
        exit_loop_test_mode=lambda: exited.append(True),
        mark_fault_detected=lambda **payload: detected.append(payload) or True,
    )
    return service, events, detected, exited


def _expected_record(pair):
    return {
        "measurement_id": f"loop.global.{pair}",
        "continuity": "closed" if pair[0] == pair[1] else "open",
        "quality": "ok",
        "reading": "test",
        "passed": True,
    }


def test_loop_test_state_tracks_same_and_cross_phase_pairs():
    assert tuple(LoopTestState().records) == LOOP_TEST_RECORD_KEYS


def test_cross_phase_open_is_recorded_as_expected_result():
    sim = _ready_loop_sim()
    sim.probe1_node = "LOOP_G1_A"
    sim.probe2_node = "LOOP_G2_B"
    state = LoopTestState()
    physics = SimpleNamespace(meter_status="danger", meter_reading="断路 [∞Ω]")
    service, events, _, _ = _make_service(sim, state, physics)

    service.record_loop_measurement("AB", origin="simulated")

    record = state.records["AB"]
    assert record["measurement_id"] == "loop.global.AB"
    assert record["continuity"] == "open"
    assert record["quality"] == "ok"
    assert record["reading"] == "断路 [∞Ω]"
    assert record["passed"] is True
    assert events[-1][0] == AssessmentEventType.MEASUREMENT_RECORDED
    assert events[-1][2]["point"] == "AB"
    assert events[-1][2]["passed"] is True
    assert events[-1][2]["measurement_id"] == "loop.global.AB"


def test_cross_phase_unexpected_conductance_marks_loop_fault_detected():
    sim = _ready_loop_sim()
    sim.probe1_node = "LOOP_G1_A"
    sim.probe2_node = "LOOP_G2_B"
    sim.fault_config = FaultConfig(
        scenario_id="E02",
        active=True,
        repaired=False,
        params={"g2_loop_swap": ("A", "B")},
    )
    state = LoopTestState()
    physics = SimpleNamespace(meter_status="ok", meter_reading="通路 [≈0Ω]")
    service, _, detected, _ = _make_service(sim, state, physics)

    service.record_loop_measurement("AB", origin="simulated")

    assert state.records["AB"]["passed"] is False
    assert detected[-1]["step"] == 1
    assert detected[-1]["target"] == "loop"
    assert detected[-1]["point"] == "AB"


def test_finalize_loop_test_requires_all_six_records():
    sim = _ready_loop_sim()
    state = LoopTestState()
    physics = SimpleNamespace(meter_status="ok", meter_reading="通路 [≈0Ω]")
    service, _, _, exited = _make_service(sim, state, physics)

    for pair in LOOP_TEST_RECORD_KEYS[:3]:
        state.records[pair] = _expected_record(pair)

    service.finalize_loop_test()

    assert state.completed is False
    assert exited == []

    for pair in LOOP_TEST_RECORD_KEYS[3:]:
        state.records[pair] = _expected_record(pair)

    service.finalize_loop_test()

    assert state.completed is True
    assert exited == [True]
