from __future__ import annotations

from domain.measurement_id import phase_sequence_id
from ui.widgets.manual_entry._base import ManualEntryWidget, QtWidgets


class PhaseSequenceManualEntryWidget(ManualEntryWidget):
    _SEQ_OPTIONS = (
        ("ABC", "ABC"),
        ("BCA", "BCA"),
        ("CAB", "CAB"),
        ("ACB", "ACB"),
        ("BAC", "BAC"),
        ("CBA", "CBA"),
        ("异常", "FAULT"),
    )

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._terminal_ids: list[str] = []
        self._sequence: str | None = None

        pt_row = self._row()
        pt_layout = pt_row.layout()
        self.pt_combo = QtWidgets.QComboBox()
        self.pt_combo.addItems(["PT1", "PT3"])
        pt_layout.addWidget(QtWidgets.QLabel("PT"))
        pt_layout.addWidget(self.pt_combo)
        self._content_layout.addWidget(pt_row)

        seq_row = self._row()
        seq_layout = seq_row.layout()
        seq_layout.addWidget(QtWidgets.QLabel("相序仪读数"))
        self.sequence_group = QtWidgets.QButtonGroup(self)
        self.sequence_group.setExclusive(True)
        self.sequence_buttons: dict[str, QtWidgets.QPushButton] = {}
        for label, value in self._SEQ_OPTIONS:
            button = QtWidgets.QPushButton(label)
            button.setCheckable(True)
            self.sequence_group.addButton(button)
            seq_layout.addWidget(button)
            self.sequence_buttons[value] = button
            button.clicked.connect(lambda _checked, seq=value: self._set_sequence(seq))
        self._content_layout.addWidget(seq_row)

        self.raw_note = self._make_raw_note_field()
        self._content_layout.addWidget(self.raw_note)

        self.submit_button = QtWidgets.QPushButton("记录")
        self.submit_button.setEnabled(False)
        self._content_layout.addWidget(self.submit_button)

        self.pt_combo.currentTextChanged.connect(lambda _text: self._refresh_state())
        self.submit_button.clicked.connect(self._submit)
        self._refresh_state()

    def _set_sequence(self, seq: str) -> None:
        self._sequence = seq
        self._refresh_state()

    def _refresh_state(self) -> None:
        pt_name = self.pt_combo.currentText()
        guidance, terminal_ids = self._three_terminal_guidance(
            phase_sequence_id(pt_name),
            f"{pt_name} 三相相序",
        )
        self._terminal_ids = terminal_ids
        self._set_guidance_text(guidance)
        self.submit_button.setEnabled(bool(self._terminal_ids and self._sequence))

    def _submit(self) -> None:
        self._clear_input_error()
        if not self._sequence:
            self._show_input_error("请选择相序仪读数。")
            return
        if not self._terminal_ids:
            self._show_input_error("当前端子映射缺失，不能记录。")
            return
        self.submitted.emit(
            {
                "pt_name": self.pt_combo.currentText(),
                "seq": self._sequence,
                "origin": "manual",
                "instrument_id": "manual:phase_seq_meter",
                "terminal_ids": list(self._terminal_ids),
                "raw": self._raw_value(self.raw_note),
            }
        )
