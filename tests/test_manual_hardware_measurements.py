from __future__ import annotations

from types import SimpleNamespace

import pytest

from domain.enums import BreakerPosition
from domain.test_states import LoopTestState, PtVoltageCheckState
from services.flow_mode_manager import FlowModeManager
from services.loop_test_service import LoopTestService
from services.pt_voltage_check_service import PtVoltageCheckService
from tests.support.stubs import make_sim_state


def _ready_loop_sim():
    sim = make_sim_state()
    sim.grounding_mode = "断开"
    sim.multimeter_mode = False
    sim.gen1.mode = "manual"
    sim.gen2.mode = "manual"
    sim.gen1.breaker_closed = True
    sim.gen2.breaker_closed = True
    sim.gen1.breaker_position = BreakerPosition.WORKING
    sim.gen2.breaker_position = BreakerPosition.WORKING
    return sim


def test_manual_loop_record_skips_virtual_probe_and_meter_checks():
    sim = _ready_loop_sim()
    state = LoopTestState()
    events = []
    service = LoopTestService(
        sim_state=sim,
        flow_mgr=FlowModeManager(),
        get_physics=lambda: SimpleNamespace(),
        get_loop_test_state=lambda: state,
        set_loop_test_state=lambda next_state: None,
        append_assessment_event=lambda event_type, step=0, **payload: events.append((event_type, step, payload)),
        exit_loop_test_mode=lambda: None,
    )

    service.record_loop_measurement("AA", origin="manual", continuity="closed")

    record = state.records["AA"]
    assert record["measurement_id"] == "loop.global.AA"
    assert record["origin"] == "manual"
    assert record["instrument_id"] is None
    assert record["quality"] == "ok"
    assert record["passed"] is True
    assert events[-1][2]["origin"] == "manual"


def test_hardware_voltage_requires_timestamp_and_instrument_id():
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

    with pytest.raises(ValueError):
        service.record_pt_voltage_measurement(
            "PT2",
            "AB",
            origin="hardware",
            voltage_sec=105.0,
            instrument_id="hw:meter1",
        )
    with pytest.raises(ValueError):
        service.record_pt_voltage_measurement(
            "PT2",
            "AB",
            origin="hardware",
            voltage_sec=105.0,
            timestamp=123.0,
        )

    service.record_pt_voltage_measurement(
        "PT2",
        "AB",
        origin="hardware",
        voltage_sec=105.0,
        instrument_id="hw:meter1",
        timestamp=123.0,
    )

    record = state.records["PT2_AB"]
    assert record["measurement_id"] == "pt_voltage.PT2.AB"
    assert record["origin"] == "hardware"
    assert record["instrument_id"] == "hw:meter1"
    assert record["timestamp"] == 123.0
    assert record["quality"] == "ok"
    assert record["passed"] is True
