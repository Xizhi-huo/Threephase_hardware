from __future__ import annotations

import os
import tempfile
from typing import Any

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault(
    "MPLCONFIGDIR",
    os.path.join(tempfile.gettempdir(), "matplotlib_threephase_tests"),
)

from PyQt5 import QtWidgets

from domain.test_states import LoopTestState, PtExamState, PtPhaseCheckState, PtVoltageCheckState
from tests.support.stubs import make_sim_state
from ui.tabs.circuit_tab._phase_wiring import PhaseWiringStatus
from ui.widgets.step_panels.loop_test_panel import LoopTestPanel
from ui.widgets.step_panels.pt_exam_panel import PtExamPanel
from ui.widgets.step_panels.pt_phase_check_panel import PtPhaseCheckPanel
from ui.widgets.step_panels.pt_voltage_check_panel import PtVoltageCheckPanel


@pytest.fixture(scope="session")
def qapp():
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


class PanelApiStub:
    def __init__(self) -> None:
        self.sim_state = make_sim_state()
        self.loop_test_state = LoopTestState()
        self.pt_voltage_check_state = PtVoltageCheckState(started=True)
        self.pt_phase_check_state = PtPhaseCheckState(started=True)
        self.pt_exam_states = {1: PtExamState(started=True), 2: PtExamState(started=True)}
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def record_loop_measurement(self, pair: str, **kwargs) -> None:
        payload = {"pair": pair, **kwargs}
        self.calls.append(("loop", payload))
        self.loop_test_state.records[pair] = {
            "measurement_id": f"loop.global.{pair}",
            "origin": kwargs["origin"],
            "reading": "导通",
            "timestamp": 1.0,
            "quality": "ok",
            "passed": True,
            "continuity": kwargs.get("continuity"),
        }

    def record_pt_voltage_measurement(self, pt_name: str, phase_pair: str, **kwargs) -> None:
        key = f"{pt_name}_{phase_pair}"
        payload = {"pt_name": pt_name, "phase_pair": phase_pair, **kwargs}
        self.calls.append(("pt_voltage", payload))
        self.pt_voltage_check_state.records[key] = {
            "measurement_id": f"pt_voltage.{pt_name}.{phase_pair}",
            "origin": kwargs["origin"],
            "reading": f"{kwargs['voltage_sec']:.1f} V",
            "timestamp": 1.0,
            "quality": "ok",
            "passed": True,
            "voltage_sec": kwargs.get("voltage_sec"),
        }

    def record_phase_sequence(self, pt_name: str, seq: str, **kwargs) -> bool:
        payload = {"pt_name": pt_name, "seq": seq, **kwargs}
        self.calls.append(("phase_sequence", payload))
        self.pt_phase_check_state.records[pt_name] = {
            "measurement_id": f"phase_sequence.{pt_name}",
            "origin": kwargs["origin"],
            "reading": seq,
            "timestamp": 1.0,
            "quality": "ok",
            "passed": True,
            "sequence": seq,
        }
        return True

    def record_pt_diff_measurement(self, gen_id: int, gen_phase: str, bus_phase: str, **kwargs) -> None:
        key = f"{gen_phase}{bus_phase}"
        payload = {"gen_id": gen_id, "gen_phase": gen_phase, "bus_phase": bus_phase, **kwargs}
        self.calls.append(("pt_diff", payload))
        self.pt_exam_states[gen_id].records[key] = {
            "measurement_id": f"pt_diff.gen{gen_id}.{key}",
            "origin": kwargs["origin"],
            "reading": f"{kwargs['voltage_sec']:.2f} V",
            "timestamp": 1.0,
            "quality": "ok",
            "passed": True,
            "voltage_sec": kwargs.get("voltage_sec"),
        }

    def record_current_pt_measurement(self, gen_id: int) -> None:
        self.calls.append(("current_pt", {"gen_id": gen_id}))

    def record_all_pt_measurements_quick(self) -> None:
        self.calls.append(("quick_pt", {}))

    def update_pt_ratio(self, attr: str, ratio: float) -> None:
        self.calls.append(("ratio", {"attr": attr, "ratio": ratio}))

    def toggle_engine(self, gen_id: int) -> None:
        self.calls.append(("engine", {"gen_id": gen_id}))

    def toggle_breaker(self, gen_id: int) -> None:
        self.calls.append(("breaker", {"gen_id": gen_id}))

    def get_loop_test_steps(self):
        return [(f"loop {idx}", False) for idx in range(7)]

    def get_pt_voltage_check_steps(self):
        return [(f"voltage {idx}", False) for idx in range(9)]

    def get_pt_phase_check_steps(self):
        return [(f"phase {idx}", False) for idx in range(7)]

    def get_pt_exam_steps(self, gen_id: int):
        return [(f"exam {gen_id}-{idx}", False) for idx in range(5)]


def test_loop_panel_manual_smoke(qapp):
    api = PanelApiStub()
    panel = LoopTestPanel(api, get_current_test_step=lambda: 1, is_step_complete=lambda _step: False)

    panel._manual_mode_rb.click()
    assert not panel.manual_widget.isHidden()
    panel.manual_widget.closed_radio.click()
    panel.manual_widget.submit_button.click()

    assert api.calls[-1][0] == "loop"
    assert api.calls[-1][1]["origin"] == "manual"
    assert api.loop_test_state.records["AA"]["measurement_id"] == "loop.global.AA"
    assert api.loop_test_state.records["AA"]["origin"] == "manual"
    panel._sim_mode_rb.click()
    assert panel.manual_widget.isHidden()
    assert api.loop_test_state.records["AA"]["origin"] == "manual"


def test_pt_voltage_panel_manual_smoke(qapp):
    api = PanelApiStub()
    panel = PtVoltageCheckPanel(api, get_current_test_step=lambda: 2, is_step_complete=lambda _step: False)

    panel._manual_mode_rb.click()
    assert not panel.manual_widget.isHidden()
    panel.manual_widget.voltage_spin.setValue(105.0)
    panel.manual_widget.submit_button.click()

    assert api.calls[-1][0] == "pt_voltage"
    assert api.calls[-1][1]["origin"] == "manual"
    assert api.pt_voltage_check_state.records["PT1_AB"]["measurement_id"] == "pt_voltage.PT1.AB"
    assert api.pt_voltage_check_state.records["PT1_AB"]["origin"] == "manual"
    panel._sim_mode_rb.click()
    assert panel.manual_widget.isHidden()
    assert api.pt_voltage_check_state.records["PT1_AB"]["origin"] == "manual"


def test_pt_phase_panel_manual_smoke(qapp):
    api = PanelApiStub()
    panel = PtPhaseCheckPanel(
        api,
        get_current_test_step=lambda: 3,
        is_step_complete=lambda _step: False,
        get_phase_wiring_status=lambda: PhaseWiringStatus.IDLE,
        get_phase_wiring_active_pt=lambda: None,
    )

    panel._manual_mode_rb.click()
    assert not panel.manual_widget.isHidden()
    panel.manual_widget.sequence_buttons["ABC"].click()
    panel.manual_widget.submit_button.click()

    assert api.calls[-1][0] == "phase_sequence"
    assert api.calls[-1][1]["origin"] == "manual"
    assert api.pt_phase_check_state.records["PT1"]["measurement_id"] == "phase_sequence.PT1"
    assert api.pt_phase_check_state.records["PT1"]["origin"] == "manual"
    panel._sim_mode_rb.click()
    assert panel.manual_widget.isHidden()
    assert api.pt_phase_check_state.records["PT1"]["origin"] == "manual"


def test_pt_exam_panel_manual_smoke(qapp):
    api = PanelApiStub()
    panel = PtExamPanel(api, get_current_test_step=lambda: 4, is_step_complete=lambda _step: False)

    panel._manual_mode_rb.click()
    assert not panel.manual_widget.isHidden()
    panel.manual_widget.voltage_spin.setValue(0.25)
    panel.manual_widget.submit_button.click()

    assert api.calls[-1][0] == "pt_diff"
    assert api.calls[-1][1]["origin"] == "manual"
    assert api.pt_exam_states[1].records["AA"]["measurement_id"] == "pt_diff.gen1.AA"
    assert api.pt_exam_states[1].records["AA"]["origin"] == "manual"
    panel._sim_mode_rb.click()
    assert panel.manual_widget.isHidden()
    assert api.pt_exam_states[1].records["AA"]["origin"] == "manual"
