"""
ui/tabs/loop_test_tab.py
回路连通性测试 Tab（独立 QWidget 组件）
"""

from __future__ import annotations

from typing import Callable, List, Optional, Protocol, Tuple

from PyQt5 import QtWidgets

from domain.enums import BreakerPosition
from domain.test_states import LOOP_TEST_RECORD_KEYS
from ui.tabs._step_style import (
    apply_button_tone,
    apply_step_shell,
    set_live_text,
    set_props,
    set_record_value,
    set_step_item,
    tone_from_color,
)
from ui.widgets._record_view import continuity_to_status, reading_text


class LoopTestTabAPI(Protocol):
    @property
    def loop_test_state(self) -> object: ...

    @property
    def sim_state(self) -> object: ...

    def reset_loop_test(self) -> None: ...

    def finalize_loop_test(self) -> None: ...

    def record_loop_measurement(self, pair: str) -> None: ...

    def enter_loop_test_mode(self) -> None: ...

    def exit_loop_test_mode(self) -> None: ...

    def get_loop_test_steps(self) -> List[Tuple[str, bool]]: ...

    def get_current_loop_phase_match(self) -> Optional[str]: ...

    def get_current_loop_pair(self) -> Optional[str]: ...

    def is_loop_test_complete(self) -> bool: ...


class LoopTestTab(QtWidgets.QWidget):
    def __init__(
        self,
        api: LoopTestTabAPI,
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

        header = QtWidgets.QLabel("隔离母排合闸前 - 第一步：回路连通性测试")
        outer.addWidget(header)

        desc = QtWidgets.QLabel(
            "合闸前首先验证三相回路连通性：断开中性点小电阻，将两台发电机切至手动模式，"
            "依次合闸（不要起机），再用万用表通断挡测量同相与异相回路（万用表靠自身电池"
            "注入微小电流），确认 G1 与 G2 同相回路导通、异相回路隔离。"
        )
        desc.setWordWrap(True)
        outer.addWidget(desc)

        self._loop_test_mode_banner = QtWidgets.QLabel(
            "⚡ 回路检查模式已激活 — 开关机械合闸，发电机未起机，母排无电压（高压侧悬空）"
        )
        self._loop_test_mode_banner.setWordWrap(True)
        self._loop_test_mode_banner.setVisible(False)
        outer.addWidget(self._loop_test_mode_banner)
        apply_step_shell(
            self,
            scroll,
            tab,
            header,
            desc,
            self._loop_test_mode_banner,
            banner_tone="warning",
        )

        action_row = QtWidgets.QWidget()
        row_layout = QtWidgets.QHBoxLayout(action_row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        set_props(action_row, actionRow=True)

        self._btn_loop_mode = QtWidgets.QPushButton("进入回路检查模式")
        self._btn_loop_mode.clicked.connect(self._on_toggle_loop_mode)
        apply_button_tone(self, self._btn_loop_mode, "warning", hero=True)

        btn_topo = QtWidgets.QPushButton("打开母排拓扑页")
        btn_topo.clicked.connect(self._on_open_circuit_tab)
        apply_button_tone(self, btn_topo, "primary", secondary=True)

        btn_mm = QtWidgets.QPushButton("开启/关闭万用表")
        btn_mm.clicked.connect(self._on_toggle_multimeter)
        apply_button_tone(self, btn_mm, "warning")

        btn_reset = QtWidgets.QPushButton("重置回路测试")
        btn_reset.clicked.connect(self._api.reset_loop_test)
        apply_button_tone(self, btn_reset, "danger")

        btn_done = QtWidgets.QPushButton("完成第一步测试")
        btn_done.clicked.connect(self._api.finalize_loop_test)
        apply_button_tone(self, btn_done, "success", hero=True)

        row_layout.addWidget(self._btn_loop_mode)
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
        set_live_text(self._meter_lbl, "neutral")
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
        for _ in range(7):
            label = QtWidgets.QLabel("")
            set_props(label, stepListItem=True)
            steps_layout.addWidget(label)
            self._step_labels.append(label)
        outer.addWidget(steps_grp)

        rec_grp = QtWidgets.QGroupBox("回路测量记录")
        rec_layout = QtWidgets.QVBoxLayout(rec_grp)
        self._record_labels: dict[str, QtWidgets.QLabel] = {}
        record_titles = {
            "AA": "AA 同相",
            "BB": "BB 同相",
            "CC": "CC 同相",
            "AB": "AB 异相",
            "AC": "AC 异相",
            "BC": "BC 异相",
        }
        for pair in LOOP_TEST_RECORD_KEYS:
            row_widget = QtWidgets.QWidget()
            set_props(row_widget, recordRow=True)
            row = QtWidgets.QHBoxLayout(row_widget)
            row.setContentsMargins(10, 6, 10, 6)

            phase_label = QtWidgets.QLabel(record_titles[pair])
            phase_label.setFixedWidth(80)
            set_live_text(phase_label, "info")

            value_label = QtWidgets.QLabel("未记录")
            value_label.setFixedWidth(280)
            set_record_value(value_label, "neutral")

            record_btn = QtWidgets.QPushButton(f"记录 {pair}")
            record_btn.clicked.connect(
                lambda _, p=pair: self._api.record_loop_measurement(p)
            )
            apply_button_tone(self, record_btn, "primary")

            row.addWidget(phase_label)
            row.addWidget(value_label)
            row.addWidget(record_btn)
            rec_layout.addWidget(row_widget)
            self._record_labels[pair] = value_label

        outer.addWidget(rec_grp)
        outer.addStretch()

    def _on_toggle_loop_mode(self) -> None:
        if self._api.sim_state.loop_test_mode:
            self._api.exit_loop_test_mode()
        else:
            self._api.enter_loop_test_mode()

    def render(self, p) -> None:
        state = self._api.loop_test_state
        records = state.records
        sim = self._api.sim_state
        in_mode = sim.loop_test_mode

        if state.completed:
            has_fault_record = any(
                record and record.get("passed") is False
                for record in records.values()
            )
            self._loop_test_mode_banner.setVisible(False)
            self._btn_loop_mode.setText("进入回路检查模式")
            apply_button_tone(self, self._btn_loop_mode, "warning", hero=True)
            if has_fault_record:
                self._summary_lbl.setText("第一步已确认完成：存在异常回路记录，数据已锁定。")
                set_live_text(self._summary_lbl, "warning")
            else:
                self._summary_lbl.setText("第一步已确认完成：六组回路连通性测试通过，数据已锁定。")
                set_live_text(self._summary_lbl, "success")
            self._meter_lbl.setText("")
            self._feedback_lbl.setText(f"操作提示：{state.feedback}")
            set_live_text(self._feedback_lbl, tone_from_color(state.feedback_color))
            for label, (text, _) in zip(self._step_labels, self._api.get_loop_test_steps()):
                set_step_item(label, text, True, True)
            for pair, label in self._record_labels.items():
                self._render_record_label(pair, label, records.get(pair))
            return

        self._loop_test_mode_banner.setVisible(in_mode)
        if in_mode:
            self._btn_loop_mode.setText("退出回路检查模式")
            apply_button_tone(self, self._btn_loop_mode, "danger", hero=True)
        else:
            self._btn_loop_mode.setText("进入回路检查模式")
            apply_button_tone(self, self._btn_loop_mode, "warning", hero=True)

        feedback = state.feedback
        current_pair = self._api.get_current_loop_pair()
        if (
            sim.gen1.breaker_closed
            and sim.gen1.breaker_position == BreakerPosition.WORKING
            and sim.gen2.breaker_closed
            and sim.gen2.breaker_position == BreakerPosition.WORKING
        ):
            summary = "两台发电机均已切至工作位置并合闸，可在母排拓扑页开始六组通断测试。"
            summary_tone = "warning"
        else:
            summary = "请按步骤操作：断开小电阻 → 手动模式 → 合闸（不起机）→ 母排拓扑页通断测试。"
            summary_tone = "info"
        if self._api.is_loop_test_complete():
            summary = "第一步已确认完成：六组回路连通性测试通过，后续操作不再影响本步骤。"
            summary_tone = "success"

        self._summary_lbl.setText(summary)
        set_live_text(self._summary_lbl, summary_tone)

        meter_text = p.meter_reading
        if current_pair:
            meter_text = f"当前表笔对准 {current_pair} 回路。{meter_text}"
        self._meter_lbl.setText(f"实时测量：{meter_text}")
        set_live_text(self._meter_lbl, tone_from_color(getattr(p, "meter_color", "black")))

        self._feedback_lbl.setText(f"操作提示：{feedback}")
        set_live_text(self._feedback_lbl, tone_from_color(state.feedback_color))

        steps = self._api.get_loop_test_steps()
        if not in_mode:
            for label, (text, _) in zip(self._step_labels, steps):
                set_step_item(label, text, False, False)
        else:
            for label, (text, done) in zip(self._step_labels, steps):
                set_step_item(label, text, done, True)

        for pair, label in self._record_labels.items():
            self._render_record_label(pair, label, records.get(pair))

    def _render_record_label(self, pair: str, label: QtWidgets.QLabel, record: Optional[dict]) -> None:
        if record is None:
            label.setText("未记录")
            set_record_value(label, "neutral")
            return

        status = continuity_to_status(record.get("continuity"))
        passed = bool(record.get("passed", status == "ok"))
        reading = reading_text(record)
        if passed:
            label.setText(f"{reading} ✓")
            set_record_value(label, "success")
        else:
            expected = "导通" if pair[0] == pair[1] else "断路"
            label.setText(f"{reading} ⚠ 期望{expected}")
            set_record_value(label, "warning")
