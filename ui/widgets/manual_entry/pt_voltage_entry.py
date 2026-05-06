from __future__ import annotations

from domain.measurement_id import pt_voltage_id
from ui.widgets.manual_entry._base import ManualEntryWidget, QtWidgets


class PtVoltageManualEntryWidget(ManualEntryWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._terminal_ids: list[str] = []
        self._voltage_entered = False

        target_row = self._row()
        target_layout = target_row.layout()
        self.pt_combo = QtWidgets.QComboBox()
        self.pt_combo.addItems(["PT1", "PT2", "PT3"])
        self.pair_combo = QtWidgets.QComboBox()
        self.pair_combo.addItems(["AB", "BC", "CA"])
        target_layout.addWidget(QtWidgets.QLabel("PT"))
        target_layout.addWidget(self.pt_combo)
        target_layout.addWidget(QtWidgets.QLabel("相对"))
        target_layout.addWidget(self.pair_combo)
        self._content_layout.addWidget(target_row)

        value_row = self._row()
        value_layout = value_row.layout()
        self.voltage_spin = QtWidgets.QDoubleSpinBox()
        self.voltage_spin.setDecimals(1)
        self.voltage_spin.setSingleStep(0.1)
        self.voltage_spin.setRange(0.0, 100000.0)
        self.voltage_spin.setSuffix(" V")
        value_layout.addWidget(QtWidgets.QLabel("二次电压"))
        value_layout.addWidget(self.voltage_spin)
        self._content_layout.addWidget(value_row)

        self.warning_label = QtWidgets.QLabel("")
        self.warning_label.setStyleSheet("color:#b45309;")
        self.warning_label.setVisible(False)
        self._content_layout.addWidget(self.warning_label)

        self.raw_note = self._make_raw_note_field()
        self._content_layout.addWidget(self.raw_note)

        self.submit_button = QtWidgets.QPushButton("记录")
        self.submit_button.setEnabled(False)
        self._content_layout.addWidget(self.submit_button)

        self.pt_combo.currentTextChanged.connect(lambda _text: self._refresh_state())
        self.pair_combo.currentTextChanged.connect(lambda _text: self._refresh_state())
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

    def _refresh_state(self) -> None:
        pt_name = self.pt_combo.currentText()
        pair = self.pair_combo.currentText()
        guidance, terminal_ids = self._two_terminal_guidance(
            pt_voltage_id(pt_name, pair),
            f"{pt_name} {pair} 二次线电压",
        )
        self._terminal_ids = terminal_ids
        self._set_guidance_text(guidance)
        high = self.voltage_spin.value() > 200.0
        self.warning_label.setVisible(high)
        if high:
            self.warning_label.setText("读数超过 200 V，请确认是否误测高压侧。")
        self.submit_button.setEnabled(bool(self._terminal_ids and self._voltage_entered))

    def _submit(self) -> None:
        self._clear_input_error()
        if not self._voltage_entered:
            self._show_input_error("请输入二次电压读数。")
            return
        voltage = float(self.voltage_spin.value())
        if voltage < 0:
            self._show_input_error("二次电压不能为负数。")
            return
        if not self._terminal_ids:
            self._show_input_error("当前端子映射缺失，不能记录。")
            return
        self.submitted.emit(
            {
                "pt_name": self.pt_combo.currentText(),
                "phase_pair": self.pair_combo.currentText(),
                "origin": "manual",
                "voltage_sec": voltage,
                "instrument_id": "manual:multimeter",
                "terminal_ids": list(self._terminal_ids),
                "raw": self._raw_value(self.raw_note),
            }
        )
