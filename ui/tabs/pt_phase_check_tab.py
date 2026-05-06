"""
ui/tabs/pt_phase_check_tab.py
PT 相序检查 Tab（独立 QWidget 组件）
"""

from __future__ import annotations

from typing import Callable, List, Optional, Protocol, Tuple

from PyQt5 import QtWidgets

from ui.tabs._step_style import (
    apply_button_tone,
    apply_step_shell,
    normalize_qt_color,
    set_live_text,
    set_props,
    set_record_value,
    set_step_item,
    tone_from_color,
)
from ui.widgets._record_view import expand_phase_sequence_to_columns, origin_text


_ALL_KEYS = ("PT1", "PT3")


class PtPhaseCheckTabAPI(Protocol):
    @property
    def pt_phase_check_state(self) -> object: ...

    def reset_pt_phase_check(self) -> None: ...

    def finalize_pt_phase_check(self) -> None: ...

    def start_pt_phase_check(self) -> None: ...

    def stop_pt_phase_check(self) -> None: ...

    def record_pt_phase_check(self, pt_name: str, phase: str) -> None: ...

    def get_pt_phase_check_steps(self) -> List[Tuple[str, bool]]: ...


class PtPhaseCheckTab(QtWidgets.QWidget):
    def __init__(
        self,
        api: PtPhaseCheckTabAPI,
        *,
        on_open_circuit_tab: Callable[[], None],
        on_toggle_multimeter: Callable[[], None],
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._api = api
        self._on_open_circuit_tab = on_open_circuit_tab
        self._on_toggle_multimeter = on_toggle_multimeter
        self._build()

    def _build(self) -> None:
        outer_layout = QtWidgets.QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QtWidgets.QScrollArea()
        tab = QtWidgets.QWidget()
        scroll.setWidget(tab)
        outer_layout.addWidget(scroll)

        outer = QtWidgets.QVBoxLayout(tab)
        outer.setContentsMargins(18, 14, 18, 14)
        outer.setSpacing(8)

        header = QtWidgets.QLabel("隔离母排合闸前 - 第三步：PT 相序检查")
        outer.addWidget(header)

        desc = QtWidgets.QLabel(
            "完成前两步后：① 恢复小电阻接地；② Gen1 手动工作模式起机并入母排（建立 PT1/PT2 参考）；"
            "③ Gen2 手动工作模式起机，保持断路器断开（Gen2 自身电压提供 PT3 参考）；"
            "④ 点击「开始第三步测试」，开启万用表，"
            "依次测量 PT1_A/PT2_A、PT1_B/PT2_B、PT1_C/PT2_C 和 PT3_A/PT2_A、PT3_B/PT2_B、PT3_C/PT2_C，"
            "逐项记录相序结果；⑤ 全部通过后点击「完成第三步测试」。\n"
            "相序判断以万用表内置相位比较为准，与电压幅值大小无关。"
        )
        desc.setWordWrap(True)
        outer.addWidget(desc)

        self._started_banner = QtWidgets.QLabel(
            "⚡ 第三步测试进行中 — Gen1 已并网，Gen2 起机断路器断开，可开始测量相序"
        )
        self._started_banner.setWordWrap(True)
        self._started_banner.setVisible(False)
        outer.addWidget(self._started_banner)
        apply_step_shell(
            self,
            scroll,
            tab,
            header,
            desc,
            self._started_banner,
            banner_tone="warning",
        )

        action_row = QtWidgets.QWidget()
        row_layout = QtWidgets.QHBoxLayout(action_row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        set_props(action_row, actionRow=True)

        self._btn_mode = QtWidgets.QPushButton("开始第三步测试")
        self._btn_mode.clicked.connect(self._on_toggle_start)
        apply_button_tone(self, self._btn_mode, "warning", hero=True)

        btn_topo = QtWidgets.QPushButton("打开母排拓扑页")
        btn_topo.clicked.connect(self._on_open_circuit_tab)
        apply_button_tone(self, btn_topo, "primary", secondary=True)

        btn_mm = QtWidgets.QPushButton("开启/关闭万用表")
        btn_mm.clicked.connect(self._on_toggle_multimeter)
        apply_button_tone(self, btn_mm, "warning")

        btn_reset = QtWidgets.QPushButton("重置相序检查")
        btn_reset.clicked.connect(self._api.reset_pt_phase_check)
        apply_button_tone(self, btn_reset, "danger")

        btn_done = QtWidgets.QPushButton("完成第三步测试")
        btn_done.clicked.connect(self._api.finalize_pt_phase_check)
        apply_button_tone(self, btn_done, "success", hero=True)

        row_layout.addWidget(self._btn_mode)
        row_layout.addWidget(btn_topo)
        row_layout.addWidget(btn_mm)
        row_layout.addWidget(btn_reset)
        row_layout.addWidget(btn_done)
        outer.addWidget(action_row)

        status_grp = QtWidgets.QGroupBox("实时状态")
        status_layout = QtWidgets.QVBoxLayout(status_grp)

        self._summary_lbl = QtWidgets.QLabel("")
        set_live_text(self._summary_lbl, "info")
        self._summary_lbl.setWordWrap(True)

        self._meter_lbl = QtWidgets.QLabel("")
        set_props(self._meter_lbl, liveText=True, tone="neutral")
        self._meter_lbl.setWordWrap(True)

        self._feedback_lbl = QtWidgets.QLabel("")
        set_live_text(self._feedback_lbl, "neutral")
        self._feedback_lbl.setWordWrap(True)

        status_layout.addWidget(self._summary_lbl)
        status_layout.addWidget(self._meter_lbl)
        status_layout.addWidget(self._feedback_lbl)
        outer.addWidget(status_grp)

        steps_grp = QtWidgets.QGroupBox("测试步骤")
        steps_layout = QtWidgets.QVBoxLayout(steps_grp)
        self._step_labels: List[QtWidgets.QLabel] = []
        for _ in range(12):
            label = QtWidgets.QLabel("")
            set_props(label, stepListItem=True)
            steps_layout.addWidget(label)
            self._step_labels.append(label)
        outer.addWidget(steps_grp)

        rec_grp = QtWidgets.QGroupBox("PT 相序测量记录（PT1/PT3 各三相，共六组）")
        rec_layout = QtWidgets.QVBoxLayout(rec_grp)
        self._record_labels: dict[str, QtWidgets.QLabel] = {}

        for pt_name, pt_color in (("PT1", "#e8f4f8"), ("PT3", "#fff3e0")):
            pt_grp = QtWidgets.QGroupBox(
                f"{pt_name} 侧（{pt_name}_X ↔ PT2_X）"
                + (
                    "  ←Gen1在母排，两侧同频同源，接线正确≈0V"
                    if pt_name == "PT1"
                    else "  ←Gen2起机断路器断开，自身电压提供PT3参考，相位比较判断相序"
                )
            )
            pt_grp.setStyleSheet(
                f"QGroupBox{{background:{pt_color}; color:#444; font-size:13px;}}"
                "QGroupBox *{font-weight:normal; font-size:12px;}"
            )
            pt_layout = QtWidgets.QVBoxLayout(pt_grp)

            for phase in ("A", "B", "C"):
                key = f"{pt_name}_{phase}"
                row_widget = QtWidgets.QWidget()
                set_props(row_widget, recordRow=True)
                row = QtWidgets.QHBoxLayout(row_widget)
                row.setContentsMargins(10, 6, 10, 6)

                phase_label = QtWidgets.QLabel(f"{phase} 相")
                phase_label.setFixedWidth(50)
                set_live_text(phase_label, "info")

                probe_hint = QtWidgets.QLabel(f"（{key} ↔ PT2_{phase}）")
                probe_hint.setFixedWidth(170)
                probe_hint.setStyleSheet("font-size:12px; color:#888888;")

                value_label = QtWidgets.QLabel("未记录")
                value_label.setFixedWidth(240)
                set_record_value(value_label, "neutral")

                record_btn = QtWidgets.QPushButton(f"记录 {key}")
                record_btn.clicked.connect(
                    lambda _, pt=pt_name, ph=phase: self._api.record_pt_phase_check(pt, ph)
                )
                apply_button_tone(self, record_btn, "primary")

                row.addWidget(phase_label)
                row.addWidget(probe_hint)
                row.addWidget(value_label)
                row.addWidget(record_btn)
                pt_layout.addWidget(row_widget)
                self._record_labels[key] = value_label

            rec_layout.addWidget(pt_grp)

        outer.addWidget(rec_grp)
        outer.addStretch()

    def _on_toggle_start(self) -> None:
        if self._api.pt_phase_check_state.started:
            self._api.stop_pt_phase_check()
        else:
            self._api.start_pt_phase_check()

    def render(self, p) -> None:
        state = self._api.pt_phase_check_state
        records = state.records

        if state.completed:
            self._started_banner.setVisible(False)
            self._btn_mode.setText("开始第三步测试")
            apply_button_tone(self, self._btn_mode, "warning", hero=True)
            self._summary_lbl.setText(
                "✅ 第三步已确认完成：PT1/PT3 相序检查通过，数据已锁定。"
            )
            set_live_text(self._summary_lbl, "success")
            self._meter_lbl.setText("")
            self._feedback_lbl.setText(
                "操作提示：第三步测试已完成，请继续进行第四步 PT 二次端子压差测试。"
            )
            set_live_text(self._feedback_lbl, "success")
            for label, (text, _) in zip(self._step_labels, self._api.get_pt_phase_check_steps()):
                set_step_item(label, text, True, True)
            expanded_records = {}
            for pt_name in ("PT1", "PT3"):
                expanded_records.update(expand_phase_sequence_to_columns(records.get(pt_name)))
            for key, label in self._record_labels.items():
                record = expanded_records.get(key)
                if record and record.get("passed") is True:
                    label.setText(f"{origin_text(record)} · 相序正确 ✓")
                    set_record_value(label, "success")
                elif record:
                    label.setText(f"{origin_text(record)} · 相序错误 ✗（接线有误）")
                    set_record_value(label, "danger")
            return

        started = state.started
        self._started_banner.setVisible(started)
        if started:
            self._btn_mode.setText("退出第三步测试")
            apply_button_tone(self, self._btn_mode, "danger", hero=True)
        else:
            self._btn_mode.setText("开始第三步测试")
            apply_button_tone(self, self._btn_mode, "warning", hero=True)

        feedback = state.feedback
        result = state.result
        done_count = sum(
            1 for key in _ALL_KEYS
            if records.get(key) is not None and records[key].get("quality") in {"ok", "out_of_range"}
        )
        if result == "pass":
            summary = "PT1/PT3 相序检查均通过，可点击“完成第三步测试”继续。"
            summary_tone = "success"
        elif result == "fail":
            summary = "⚠️ 检测到相序异常，请检查对应 PT 侧接线后重新记录。"
            summary_tone = "danger"
        elif done_count > 0:
            summary = f"已记录 {done_count}/2 条 PT 相序，请继续完成剩余项目。"
            summary_tone = "info"
        else:
            summary = (
                "请按步骤：Gen1并网 → 起机Gen2(不合闸) → 开始第三步测试 → 万用表 → "
                "逐项记录PT1和PT3相序。"
            )
            summary_tone = "info"

        self._summary_lbl.setText(summary)
        set_live_text(self._summary_lbl, summary_tone)

        meter_text = p.meter_reading
        phase_match = getattr(p, "meter_phase_match", None)
        if phase_match is True:
            match_color = "green"
        elif phase_match is False:
            match_color = "red"
        else:
            match_color = normalize_qt_color(getattr(p, "meter_color", "black"))
        self._meter_lbl.setText(f"实时测量：{meter_text}")
        set_props(self._meter_lbl, liveText=True, tone=tone_from_color(match_color))

        self._feedback_lbl.setText(f"操作提示：{feedback}")
        set_live_text(self._feedback_lbl, tone_from_color(state.feedback_color))

        steps = self._api.get_pt_phase_check_steps()
        if not started:
            for label, (text, _) in zip(self._step_labels, steps):
                set_step_item(label, text, False, False)
        else:
            for label, (text, done) in zip(self._step_labels, steps):
                set_step_item(label, text, done, True)

        expanded_records = {}
        for pt_name in ("PT1", "PT3"):
            expanded_records.update(expand_phase_sequence_to_columns(records.get(pt_name)))
        for key, label in self._record_labels.items():
            record = expanded_records.get(key)
            if record is None:
                label.setText("未记录")
                set_record_value(label, "neutral")
            elif record.get("passed") is True:
                label.setText(f"{origin_text(record)} · 相序正确 ✓")
                set_record_value(label, "success")
            else:
                label.setText(f"{origin_text(record)} · 相序错误 ✗（接线有误）")
                set_record_value(label, "danger")
