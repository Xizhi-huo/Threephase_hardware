from __future__ import annotations

from domain.measurement_id import loop_id
from ui.widgets.manual_entry._base import ManualEntryWidget, QtWidgets


class LoopManualEntryWidget(ManualEntryWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._terminal_ids: list[str] = []
        self._continuity: str | None = None

        row = self._row()
        layout = row.layout()
        self.pair_combo = QtWidgets.QComboBox()
        self.pair_combo.addItems(["AA", "BB", "CC", "AB", "AC", "BC"])
        layout.addWidget(QtWidgets.QLabel("端子对"))
        layout.addWidget(self.pair_combo)
        self._content_layout.addWidget(row)

        read_row = self._row()
        read_layout = read_row.layout()
        read_layout.addWidget(QtWidgets.QLabel("读数"))
        self._continuity_group = QtWidgets.QButtonGroup(self)
        self.closed_radio = QtWidgets.QRadioButton("导通")
        self.open_radio = QtWidgets.QRadioButton("断开")
        self._continuity_group.addButton(self.closed_radio)
        self._continuity_group.addButton(self.open_radio)
        read_layout.addWidget(self.closed_radio)
        read_layout.addWidget(self.open_radio)
        self._content_layout.addWidget(read_row)

        self.raw_note = self._make_raw_note_field()
        self._content_layout.addWidget(self.raw_note)

        self.submit_button = QtWidgets.QPushButton("记录")
        self.submit_button.setEnabled(False)
        self._content_layout.addWidget(self.submit_button)

        self.pair_combo.currentTextChanged.connect(lambda _text: self._refresh_state())
        self.closed_radio.toggled.connect(lambda checked: self._set_continuity("closed", checked))
        self.open_radio.toggled.connect(lambda checked: self._set_continuity("open", checked))
        self.submit_button.clicked.connect(self._submit)
        self._refresh_state()

    def _set_continuity(self, value: str, checked: bool) -> None:
        if checked:
            self._continuity = value
        self._refresh_state()

    def _refresh_state(self) -> None:
        pair = self.pair_combo.currentText()
        guidance, terminal_ids = self._two_terminal_guidance(loop_id(pair), f"{pair} 回路")
        self._terminal_ids = terminal_ids
        self._set_guidance_text(guidance)
        self.submit_button.setEnabled(bool(self._terminal_ids and self._continuity))

    def _submit(self) -> None:
        self._clear_input_error()
        if self._continuity not in {"closed", "open"}:
            self._show_input_error("请选择导通或断开。")
            return
        if not self._terminal_ids:
            self._show_input_error("当前端子映射缺失，不能记录。")
            return
        self.submitted.emit(
            {
                "pair": self.pair_combo.currentText(),
                "origin": "manual",
                "continuity": self._continuity,
                "instrument_id": "manual:multimeter",
                "terminal_ids": list(self._terminal_ids),
                "raw": self._raw_value(self.raw_note),
            }
        )
