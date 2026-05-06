from __future__ import annotations

import random
from pathlib import Path

import numpy as np

from domain.constants import GRID_AMP, GRID_FREQ
from services.physics_engine import PhysicsEngine
from tests.support.snapshots import assert_json_snapshot
from tests.support.stubs import (
    ControllerStub,
    apply_fault_e01,
    configure_loop_measurement_state,
)


SNAPSHOT_DIR = Path(__file__).parent / "snapshots"


def _render_state_payload(render_state):
    return {
        "bus_live": render_state.bus_live,
        "bus_amp": render_state.bus_amp,
        "bus_source": render_state.bus_source,
        "bus_reference_gen": render_state.bus_reference_gen,
        "bus_status_msg": render_state.bus_status_msg,
        "bus_reference_msg": render_state.bus_reference_msg,
        "relay_msg": render_state.relay_msg,
        "relay_color": render_state.relay_color,
        "arb_msg": render_state.arb_msg,
        "arb_color": render_state.arb_color,
        "meter_reading": render_state.meter_reading,
        "meter_color": render_state.meter_color,
        "meter_voltage": render_state.meter_voltage,
        "meter_status": render_state.meter_status,
        "meter_nodes": render_state.meter_nodes,
        "meter_phase_match": render_state.meter_phase_match,
        "pt1_v": render_state.pt1_v,
        "pt2_v": render_state.pt2_v,
        "pt3_v": render_state.pt3_v,
        "brk1_text": render_state.brk1_text,
        "brk2_text": render_state.brk2_text,
        "plot_data": render_state.plot_data,
        "fixed_deg": render_state.fixed_deg,
    }


def _build_engine(ctrl: ControllerStub) -> PhysicsEngine:
    engine = PhysicsEngine(ctrl)
    engine.update_physics()
    return engine


def test_physics_engine_runs_without_ui():
    ctrl = ControllerStub()
    configure_loop_measurement_state(ctrl)
    engine = _build_engine(ctrl)
    render_state = engine.build_render_state()
    assert render_state.meter_reading
    assert render_state.plot_data


def test_reset_wave_history_rebuilds_after_phase_jump():
    ctrl = ControllerStub()
    sim = ctrl.sim_state
    sim.gen1.running = True
    sim.gen2.running = True
    sim.gen1.actual_amp = sim.gen1.amp = 10500.0
    sim.gen2.actual_amp = sim.gen2.amp = 10500.0
    sim.gen1.freq = sim.gen2.freq = 50.0
    sim.gen1.phase_deg = 0.0
    sim.gen2.phase_deg = 40.0
    engine = _build_engine(ctrl)

    sim.gen2.phase_deg = 0.0
    engine.reset_wave_history()
    engine.update_physics()
    plot_data = engine.build_render_state().plot_data

    assert float(np.max(np.abs(plot_data["g1a"] - plot_data["g2a"]))) == 0.0


def test_completed_pt_voltage_check_does_not_keep_tracking_active():
    random.seed(0)
    ctrl = ControllerStub()
    sim = ctrl.sim_state
    sim.gen1.running = True
    sim.gen2.running = True
    sim.gen1.freq = sim.gen2.freq = GRID_FREQ
    sim.gen1.amp = sim.gen2.amp = GRID_AMP
    sim.gen1.actual_amp = sim.gen2.actual_amp = GRID_AMP
    ctrl.pt_voltage_check_state.started = True
    ctrl.pt_voltage_check_state.completed = True

    engine = PhysicsEngine(ctrl)
    engine.update_physics()

    assert sim.gen1.freq == GRID_FREQ
    assert sim.gen1.amp == GRID_AMP
    assert sim.gen2.freq == GRID_FREQ
    assert sim.gen2.amp == GRID_AMP


def test_cross_phase_loop_measurement_reports_expected_open_state():
    ctrl = ControllerStub()
    configure_loop_measurement_state(ctrl)
    ctrl.sim_state.probe1_node = "LOOP_G1_A"
    ctrl.sim_state.probe2_node = "LOOP_G2_B"

    engine = _build_engine(ctrl)
    render_state = engine.build_render_state()

    assert render_state.meter_status == "danger"
    assert render_state.meter_color == "green"
    assert "异相隔离正常" in render_state.meter_reading


def test_physics_snapshot_normal():
    ctrl = ControllerStub()
    configure_loop_measurement_state(ctrl)
    engine = _build_engine(ctrl)
    assert_json_snapshot(
        SNAPSHOT_DIR / "physics_normal.json",
        _render_state_payload(engine.build_render_state()),
    )


def test_physics_snapshot_fault_e01():
    ctrl = ControllerStub()
    configure_loop_measurement_state(ctrl)
    apply_fault_e01(ctrl)
    engine = _build_engine(ctrl)
    assert_json_snapshot(
        SNAPSHOT_DIR / "physics_fault_E01.json",
        _render_state_payload(engine.build_render_state()),
    )
