from __future__ import annotations

from typing import Any

from PyQt5 import QtCore, QtWidgets  # type: ignore[import-untyped]  # PyQt5 ships without type stubs in this env.

from domain.measurement_map import get_measurement_spec, get_terminal


class ManualEntryWidget(QtWidgets.QWidget):
    """Shared base for manual measurement entry widgets."""

    submitted = QtCore.pyqtSignal(dict)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._root_layout = QtWidgets.QVBoxLayout(self)
        self._root_layout.setContentsMargins(6, 6, 6, 6)
        self._root_layout.setSpacing(5)

        self._guidance_label = QtWidgets.QLabel("")
        self._guidance_label.setWordWrap(True)
        self._guidance_label.setObjectName("manual_entry_guidance")
        self._root_layout.addWidget(self._guidance_label)

        self._content_layout = QtWidgets.QVBoxLayout()
        self._content_layout.setSpacing(5)
        self._root_layout.addLayout(self._content_layout)

        self._error_label = QtWidgets.QLabel("")
        self._error_label.setWordWrap(True)
        self._error_label.setObjectName("manual_entry_error")
        self._error_label.setStyleSheet("color:#b91c1c;")
        self._error_label.setVisible(False)
        self._root_layout.addWidget(self._error_label)

    def _show_input_error(self, msg: str) -> None:
        self._error_label.setText(msg)
        self._error_label.setVisible(True)

    def _clear_input_error(self) -> None:
        self._error_label.setText("")
        self._error_label.setVisible(False)

    def _set_guidance_text(self, text: str) -> None:
        self._guidance_label.setText(text)

    def _make_raw_note_field(self) -> QtWidgets.QLineEdit:
        field = QtWidgets.QLineEdit()
        field.setObjectName("manual_entry_raw_note")
        field.setPlaceholderText("原始备注（可选）")
        return field

    def _row(self) -> QtWidgets.QWidget:
        row = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        return row

    def _terminal_ids_for(self, measurement_id: str) -> list[str]:
        spec = get_measurement_spec(measurement_id)
        if not spec:
            return []
        terminal_ids = spec.get("terminal_ids")
        return list(terminal_ids) if terminal_ids else []

    def _two_terminal_guidance(self, measurement_id: str, title: str) -> tuple[str, list[str]]:
        terminal_ids = self._terminal_ids_for(measurement_id)
        if len(terminal_ids) != 2:
            return f"未找到 {measurement_id} 的端子映射，暂不能手动记录。", []
        left, right = terminal_ids
        return (
            f"请测量：{title}（红={self._terminal_text(left)}，黑={self._terminal_text(right)}）",
            terminal_ids,
        )

    def _three_terminal_guidance(self, measurement_id: str, title: str) -> tuple[str, list[str]]:
        terminal_ids = self._terminal_ids_for(measurement_id)
        if len(terminal_ids) != 3:
            return f"未找到 {measurement_id} 的端子映射，暂不能手动记录。", []
        a_term, b_term, c_term = terminal_ids
        return (
            f"请测量：{title}（A={self._terminal_text(a_term)}，"
            f"B={self._terminal_text(b_term)}，C={self._terminal_text(c_term)}）",
            terminal_ids,
        )

    def _terminal_text(self, terminal_id: str) -> str:
        terminal = get_terminal(terminal_id)
        if not terminal:
            return terminal_id
        label = terminal.get("label") or terminal_id
        return f"{terminal_id}/{label}" if label != terminal_id else terminal_id

    def _raw_value(self, field: QtWidgets.QLineEdit) -> str | dict[str, Any] | None:
        raw = field.text().strip()
        return raw or None
