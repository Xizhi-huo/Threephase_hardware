from __future__ import annotations

from types import SimpleNamespace

import pytest

from domain.enums import BreakerPosition
from domain.test_states import (
    LoopTestState,
    PtExamState,
    PtPhaseCheckState,
    PtVoltageCheckState,
)
from services.flow_mode_manager import FlowModeManager
from services.loop_test_service import LoopTestService
from services.pt_exam_service import PtExamService
from services.pt_phase_check_service import PtPhaseCheckService
from services.pt_voltage_check_service import PtVoltageCheckService
from tests.support.stubs import make_sim_state


def _assert_manual_record(record, measurement_id: str) -> None:
    assert record["measurement_id"] == measurement_id
    assert record["origin"] == "manual"
    assert record["timestamp"] is not None
    assert isinstance(record["reading"], str)
    assert record["reading"]


def _make_loop_service():
    sim = make_sim_state()
    sim.grounding_mode = "断开"
    sim.gen1.mode = "manual"
    sim.gen2.mode = "manual"
    sim.gen1.breaker_closed = True
    sim.gen2.breaker_closed = True
    sim.gen1.breaker_position = BreakerPosition.WORKING
    sim.gen2.breaker_position = BreakerPosition.WORKING
    state = LoopTestState()
    service = LoopTestService(
        sim_state=sim,
        flow_mgr=FlowModeManager(),
        get_physics=lambda: SimpleNamespace(),
        get_loop_test_state=lambda: state,
        set_loop_test_state=lambda next_state: None,
        append_assessment_event=lambda *args, **kwargs: None,
        exit_loop_test_mode=lambda: None,
    )
    return service, state


def _make_voltage_service():
    sim = make_sim_state()
    sim.grounding_mode = "小电阻接地"
    sim.gen1.breaker_position = BreakerPosition.WORKING
    sim.gen1.breaker_closed = True
    state = PtVoltageCheckState(started=True)
    service = PtVoltageCheckService(
        sim_state=sim,
        flow_mgr=FlowModeManager(),
        get_physics=lambda: SimpleNamespace(),
        get_pt_voltage_check_state=lambda: state,
        set_pt_voltage_check_state=lambda next_state: None,
        is_loop_test_complete=lambda: True,
        append_assessment_event=lambda *args, **kwargs: None,
    )
    return service, state


def _make_phase_service():
    sim = make_sim_state()
    sim.grounding_mode = "小电阻接地"
    sim.gen1.breaker_position = BreakerPosition.WORKING
    sim.gen1.breaker_closed = True
    state = PtPhaseCheckState(started=True)
    service = PtPhaseCheckService(
        sim_state=sim,
        flow_mgr=FlowModeManager(),
        get_physics=lambda: SimpleNamespace(),
        get_pt_phase_check_state=lambda: state,
        set_pt_phase_check_state=lambda next_state: None,
        is_loop_test_complete=lambda: True,
        is_pt_voltage_check_complete=lambda: True,
        append_assessment_event=lambda *args, **kwargs: None,
        mark_fault_detected=lambda **kwargs: None,
        set_pt_phase_check_feedback=lambda message, color: None,
        mark_pt_phase_check_completed=lambda: None,
    )
    return service, state


def _make_exam_service():
    sim = make_sim_state()
    sim.grounding_mode = "小电阻接地"
    sim.gen1.breaker_position = BreakerPosition.WORKING
    sim.gen1.breaker_closed = True
    sim.gen2.breaker_closed = False
    states = {1: PtExamState(started=True), 2: PtExamState(started=True)}
    service = PtExamService(
        sim_state=sim,
        flow_mgr=FlowModeManager(),
        get_physics=lambda: SimpleNamespace(),
        get_pt_exam_states=lambda: states,
        is_loop_test_complete=lambda: True,
        is_pt_voltage_check_complete=lambda: True,
        is_pt_phase_check_complete=lambda: True,
        append_assessment_event=lambda *args, **kwargs: None,
    )
    return service, states


def test_manual_loop_record_writes_new_schema_fields():
    service, state = _make_loop_service()

    service.record_loop_measurement("AA", origin="manual", continuity="closed")

    _assert_manual_record(state.records["AA"], "loop.global.AA")


def test_loop_record_rejects_invalid_manual_hardware_and_origin_inputs():
    service, _ = _make_loop_service()

    with pytest.raises(ValueError):
        service.record_loop_measurement("AA", origin="manual")
    with pytest.raises(ValueError):
        service.record_loop_measurement("AA", origin="hardware", continuity="closed", instrument_id="hw:meter1")
    with pytest.raises(ValueError):
        service.record_loop_measurement("AA", origin="hardware", continuity="closed", timestamp=123.0)
    with pytest.raises(ValueError):
        service.record_loop_measurement("ZZ", origin="foo", continuity="closed")


def test_manual_pt_voltage_record_writes_new_schema_fields():
    service, state = _make_voltage_service()

    service.record_pt_voltage_measurement("PT1", "AB", origin="manual", voltage_sec=105.0)

    _assert_manual_record(state.records["PT1_AB"], "pt_voltage.PT1.AB")


def test_pt_voltage_record_rejects_invalid_manual_hardware_and_origin_inputs():
    service, _ = _make_voltage_service()

    with pytest.raises(ValueError):
        service.record_pt_voltage_measurement("PT1", "AB", origin="manual")
    with pytest.raises(ValueError):
        service.record_pt_voltage_measurement(
            "PT1", "AB", origin="hardware", voltage_sec=105.0, instrument_id="hw:meter1"
        )
    with pytest.raises(ValueError):
        service.record_pt_voltage_measurement(
            "PT1", "AB", origin="hardware", voltage_sec=105.0, timestamp=123.0
        )
    with pytest.raises(ValueError):
        service.record_pt_voltage_measurement("PTX", "AB", origin="foo", voltage_sec=105.0)


def test_manual_phase_sequence_record_writes_new_schema_fields():
    service, state = _make_phase_service()

    assert service.record_phase_sequence("PT1", "ABC", origin="manual") is True

    _assert_manual_record(state.records["PT1"], "phase_sequence.PT1")


def test_phase_sequence_record_rejects_invalid_manual_hardware_and_origin_inputs():
    service, state = _make_phase_service()

    with pytest.raises(ValueError):
        service.record_phase_sequence("PT1", None, origin="manual")
    with pytest.raises(ValueError):
        service.record_phase_sequence("PT1", "ABC", origin="hardware", instrument_id="hw:phase1")
    with pytest.raises(ValueError):
        service.record_phase_sequence("PT1", "ABC", origin="hardware", timestamp=123.0)
    state.started = False
    with pytest.raises(ValueError):
        service.record_phase_sequence("PT1", "ABC", origin="foo")


def test_manual_pt_diff_record_writes_new_schema_fields():
    service, states = _make_exam_service()

    service.record_pt_diff_measurement(1, "A", "A", origin="manual", voltage_sec=0.0)

    _assert_manual_record(states[1].records["AA"], "pt_diff.gen1.AA")


def test_pt_diff_record_rejects_invalid_manual_hardware_and_origin_inputs():
    service, _ = _make_exam_service()

    with pytest.raises(ValueError):
        service.record_pt_diff_measurement(1, "A", "A", origin="manual")
    with pytest.raises(ValueError):
        service.record_pt_diff_measurement(
            1, "A", "A", origin="hardware", voltage_sec=0.0, instrument_id="hw:meter1"
        )
    with pytest.raises(ValueError):
        service.record_pt_diff_measurement(
            1, "A", "A", origin="hardware", voltage_sec=0.0, timestamp=123.0
        )
    with pytest.raises(ValueError):
        service.record_pt_diff_measurement(1, "Z", "Z", origin="foo", voltage_sec=0.0)
