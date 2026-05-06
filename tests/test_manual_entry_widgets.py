from __future__ import annotations

import os
import tempfile

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault(
    "MPLCONFIGDIR",
    os.path.join(tempfile.gettempdir(), "matplotlib_threephase_tests"),
)

from PyQt5 import QtWidgets

from ui.widgets.manual_entry import (
    LoopManualEntryWidget,
    PhaseSequenceManualEntryWidget,
    PtDiffManualEntryWidget,
    PtVoltageManualEntryWidget,
)


@pytest.fixture(scope="session")
def qapp():
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


def _capture(widget):
    emitted: list[dict] = []
    widget.submitted.connect(lambda payload: emitted.append(dict(payload)))
    return emitted


def test_loop_widget_initial_state(qapp):
    widget = LoopManualEntryWidget()

    assert not widget.submit_button.isEnabled()
    assert "请测量" in widget._guidance_label.text()


def test_loop_widget_valid_submit_emits_manual_kwargs(qapp):
    widget = LoopManualEntryWidget()
    emitted = _capture(widget)

    widget.closed_radio.click()
    widget.raw_note.setText("meter beeped")
    widget.submit_button.click()

    assert len(emitted) == 1
    payload = emitted[0]
    assert payload["pair"] == "AA"
    assert payload["origin"] == "manual"
    assert payload["continuity"] == "closed"
    assert payload["instrument_id"] == "manual:multimeter"
    assert payload["terminal_ids"] == ["LOOP_G1_A", "LOOP_G2_A"]
    assert payload["raw"] == "meter beeped"


def test_loop_widget_rejects_missing_continuity(qapp):
    widget = LoopManualEntryWidget()
    emitted = _capture(widget)

    widget._submit()

    assert emitted == []
    assert not widget._error_label.isHidden()
    assert widget._error_label.text()


def test_pt_voltage_widget_initial_state(qapp):
    widget = PtVoltageManualEntryWidget()

    assert not widget.submit_button.isEnabled()
    assert "请测量" in widget._guidance_label.text()


def test_pt_voltage_widget_valid_submit_emits_manual_kwargs(qapp):
    widget = PtVoltageManualEntryWidget()
    emitted = _capture(widget)

    widget.pt_combo.setCurrentText("PT1")
    widget.pair_combo.setCurrentText("AB")
    widget.voltage_spin.setValue(105.0)
    widget.raw_note.setText("105VAC")
    widget.submit_button.click()

    assert len(emitted) == 1
    payload = emitted[0]
    assert payload["pt_name"] == "PT1"
    assert payload["phase_pair"] == "AB"
    assert payload["origin"] == "manual"
    assert payload["voltage_sec"] == 105.0
    assert payload["instrument_id"] == "manual:multimeter"
    assert payload["terminal_ids"] == ["PT1_A", "PT1_B"]
    assert payload["raw"] == "105VAC"


def test_pt_voltage_widget_rejects_missing_reading(qapp):
    widget = PtVoltageManualEntryWidget()
    emitted = _capture(widget)

    widget._submit()

    assert emitted == []
    assert not widget._error_label.isHidden()
    assert widget._error_label.text()


def test_phase_sequence_widget_initial_state(qapp):
    widget = PhaseSequenceManualEntryWidget()

    assert not widget.submit_button.isEnabled()
    assert "请测量" in widget._guidance_label.text()


def test_phase_sequence_widget_valid_submit_emits_manual_kwargs(qapp):
    widget = PhaseSequenceManualEntryWidget()
    emitted = _capture(widget)

    widget.pt_combo.setCurrentText("PT1")
    widget.sequence_buttons["ABC"].click()
    widget.submit_button.click()

    assert len(emitted) == 1
    payload = emitted[0]
    assert payload["pt_name"] == "PT1"
    assert payload["seq"] == "ABC"
    assert payload["origin"] == "manual"
    assert payload["instrument_id"] == "manual:phase_seq_meter"
    assert payload["terminal_ids"] == ["PT1_A", "PT1_B", "PT1_C"]


def test_phase_sequence_widget_rejects_missing_sequence(qapp):
    widget = PhaseSequenceManualEntryWidget()
    emitted = _capture(widget)

    widget._submit()

    assert emitted == []
    assert not widget._error_label.isHidden()
    assert widget._error_label.text()


def test_pt_diff_widget_initial_state(qapp):
    widget = PtDiffManualEntryWidget()

    assert not widget.submit_button.isEnabled()
    assert "请测量" in widget._guidance_label.text()


def test_pt_diff_widget_valid_submit_emits_manual_kwargs(qapp):
    widget = PtDiffManualEntryWidget()
    emitted = _capture(widget)

    widget.gen_combo.setCurrentIndex(0)
    widget.gen_phase_combo.setCurrentText("A")
    widget.bus_phase_combo.setCurrentText("A")
    widget.voltage_spin.setValue(0.12)
    widget.submit_button.click()

    assert len(emitted) == 1
    payload = emitted[0]
    assert payload["gen_id"] == 1
    assert payload["gen_phase"] == "A"
    assert payload["bus_phase"] == "A"
    assert payload["origin"] == "manual"
    assert payload["voltage_sec"] == 0.12
    assert payload["instrument_id"] == "manual:multimeter"
    assert payload["terminal_ids"] == ["PT1_A", "PT2_A"]


def test_pt_diff_widget_rejects_missing_reading(qapp):
    widget = PtDiffManualEntryWidget()
    emitted = _capture(widget)

    widget._submit()

    assert emitted == []
    assert not widget._error_label.isHidden()
    assert widget._error_label.text()
