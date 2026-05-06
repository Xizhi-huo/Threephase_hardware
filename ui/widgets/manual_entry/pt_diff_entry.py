from __future__ import annotations

from domain.measurement_id import pt_diff_id
from ui.widgets.manual_entry._base import ManualEntryWidget, QtWidgets


class PtDiffManualEntryWidget(ManualEntryWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._terminal_ids: list[str] = []
        self._voltage_entered = False

        target_row = self._row()
        target_layout = target_row.layout()
        self.gen_combo = QtWidgets.QComboBox()
        self.gen_combo.addItem("Gen1", 1)
        self.gen_combo.addItem("Gen2", 2)
        self.gen_phase_combo = QtWidgets.QComboBox()
        self.gen_phase_combo.addItems(["A", "B", "C"])
        self.bus_phase_combo = QtWidgets.QComboBox()
        self.bus_phase_combo.addItems(["A", "B", "C"])
        target_layout.addWidget(QtWidgets.QLabel("发电机"))
        target_layout.addWidget(self.gen_combo)
        target_layout.addWidget(QtWidgets.QLabel("Gen 端子"))
        target_layout.addWidget(self.gen_phase_combo)
        target_layout.addWidget(QtWidgets.QLabel("Bus 端子"))
        target_layout.addWidget(self.bus_phase_combo)
        self._content_layout.addWidget(target_row)

        value_row = self._row()
        value_layout = value_row.layout()
        self.voltage_spin = QtWidgets.QDoubleSpinBox()
        self.voltage_spin.setDecimals(2)
        self.voltage_spin.setSingleStep(0.01)
        self.voltage_spin.setRange(0.0, 10.0)
        self.voltage_spin.setSuffix(" V")
        value_layout.addWidget(QtWidgets.QLabel("二次压差"))
        value_layout.addWidget(self.voltage_spin)
        self._content_layout.addWidget(value_row)

        self.raw_note = self._make_raw_note_field()
        self._content_layout.addWidget(self.raw_note)

        self.submit_button = QtWidgets.QPushButton("记录")
        self.submit_button.setEnabled(False)
        self._content_layout.addWidget(self.submit_button)

        self.gen_combo.currentIndexChanged.connect(lambda _idx: self._refresh_state())
        self.gen_phase_combo.currentTextChanged.connect(lambda _text: self._refresh_state())
        self.bus_phase_combo.currentTextChanged.connect(lambda _text: self._refresh_state())
        self.voltage_spin.valueChanged.connect(self._on_voltage_changed)
        self.voltage_spin.editingFinished.connect(self._on_voltage_edited)
        self.submit_button.clicked.connect(self._submit)
        self._refresh_state()

    def _on_voltage_changed(self, _value: float) -> None:
        self._voltage_entered = True
        self._refresh_state()

    def _on_voltage_edited(self) -> None:
        self._voltage_entered = True
        self._refresh_state()

    def _current_gen_id(self) -> int:
        gen_id = self.gen_combo.currentData()
        return int(gen_id) if gen_id in (1, 2) else 1

    def _current_cell(self) -> str:
        return f"{self.gen_phase_combo.currentText()}{self.bus_phase_combo.currentText()}"

    def _refresh_state(self) -> None:
        gen_id = self._current_gen_id()
        cell = self._current_cell()
        guidance, terminal_ids = self._two_terminal_guidance(
            pt_diff_id(gen_id, cell),
            f"Gen{gen_id} {cell} PT 二次端子压差",
        )
        self._terminal_ids = terminal_ids
        self._set_guidance_text(guidance)
        self.submit_button.setEnabled(bool(self._terminal_ids and self._voltage_entered))

    def _submit(self) -> None:
        self._clear_input_error()
        if not self._voltage_entered:
            self._show_input_error("请输入二次压差读数。")
            return
        voltage = float(self.voltage_spin.value())
        if voltage < 0:
            self._show_input_error("二次压差不能为负数。")
            return
        if not self._terminal_ids:
            self._show_input_error("当前端子映射缺失，不能记录。")
            return
        self.submitted.emit(
            {
                "gen_id": self._current_gen_id(),
                "gen_phase": self.gen_phase_combo.currentText(),
                "bus_phase": self.bus_phase_combo.currentText(),
                "origin": "manual",
                "voltage_sec": voltage,
                "instrument_id": "manual:multimeter",
                "terminal_ids": list(self._terminal_ids),
                "raw": self._raw_value(self.raw_note),
            }
        )
