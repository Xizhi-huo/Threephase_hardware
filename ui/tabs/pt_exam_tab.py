"""
ui/tabs/pt_exam_tab.py
PT 二次端子压差测试 Tab（独立 QWidget 组件）
"""

from __future__ import annotations

from typing import Callable, List, Optional, Protocol, Tuple

from PyQt5 import QtWidgets

from ui.tabs._step_style import (
    apply_button_tone,
    apply_step_shell,
    set_live_text,
    set_props,
    set_record_value,
    set_step_item,
    tone_from_color,
)


_RECORD_KEYS = tuple(f"{gen_phase}{bus_phase}" for gen_phase in "ABC" for bus_phase in "ABC")


class PtExamTabAPI(Protocol):
    @property
    def pt_exam_states(self) -> object: ...

    @property
    def sim_state(self) -> object: ...

    def reset_pt_exam(self, gen_id: int) -> None: ...

    def finalize_all_pt_exams(self) -> None: ...

    def start_pt_exam(self, gen_id: int) -> None: ...

    def stop_pt_exam(self, gen_id: int) -> None: ...

    def record_pt_diff_measurement(self, gen_id: int, gen_phase: str, bus_phase: str) -> None: ...

    def get_pt_exam_steps(self, gen_id: int) -> List[Tuple[str, bool]]: ...

    def get_generator_state(self, gen_id: int) -> object: ...

    def get_current_pt_exam_phase_match(self, gen_id: int) -> Optional[Tuple[str, str]]: ...


class PtExamTab(QtWidgets.QWidget):
    def __init__(
        self,
        api: PtExamTabAPI,
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

        header = QtWidgets.QLabel("隔离母排合闸前 - 第四步：PT二次端子压差测试")
        outer.addWidget(header)

        desc = QtWidgets.QLabel(
            "完成第三步PT相序检查后，恢复中性点小电阻接地，并将机组切至工作位置并入母排。"
            "随后在母排拓扑页使用万用表测量并记录三相 PT 二次端子压差。"
        )
        desc.setWordWrap(True)
        outer.addWidget(desc)

        self._mode_banner = QtWidgets.QLabel(
            "🧪 第四步测试进行中 — 请在母排拓扑页完成 PT 二次端子压差测量"
        )
        self._mode_banner.setWordWrap(True)
        self._mode_banner.setVisible(False)
        outer.addWidget(self._mode_banner)
        apply_step_shell(
            self,
            scroll,
            tab,
            header,
            desc,
            self._mode_banner,
            banner_tone="info",
        )

        target_group = QtWidgets.QGroupBox("测试对象")
        set_props(target_group, cardTone="info")
        target_layout = QtWidgets.QHBoxLayout(target_group)
        self._pt_target_bg = QtWidgets.QButtonGroup(self)
        self._pt_target_rb: dict[int, QtWidgets.QRadioButton] = {}
        for text, value in (("Gen 1", 1), ("Gen 2", 2)):
            radio = QtWidgets.QRadioButton(text)
            radio.setChecked(value == 1)
            self._pt_target_bg.addButton(radio, value)
            target_layout.addWidget(radio)
            self._pt_target_rb[value] = radio
        outer.addWidget(target_group)

        action_row = QtWidgets.QWidget()
        row_layout = QtWidgets.QHBoxLayout(action_row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        set_props(action_row, actionRow=True)

        self._btn_start = QtWidgets.QPushButton("开始第四步测试")
        self._btn_start.clicked.connect(self._on_toggle_pt_exam_mode)
        apply_button_tone(self, self._btn_start, "warning", hero=True)

        btn_topo = QtWidgets.QPushButton("打开母排拓扑页")
        btn_topo.clicked.connect(self._on_open_circuit_tab)
        apply_button_tone(self, btn_topo, "primary", secondary=True)

        btn_mm = QtWidgets.QPushButton("开启/关闭万用表")
        btn_mm.clicked.connect(self._on_toggle_multimeter)
        apply_button_tone(self, btn_mm, "warning")

        btn_reset = QtWidgets.QPushButton("重置当前机组测试")
        btn_reset.clicked.connect(lambda: self._api.reset_pt_exam(self._current_gen_id()))
        apply_button_tone(self, btn_reset, "danger")

        btn_done = QtWidgets.QPushButton("完成第四步测试")
        btn_done.clicked.connect(self._api.finalize_all_pt_exams)
        apply_button_tone(self, btn_done, "success", hero=True)

        row_layout.addWidget(self._btn_start)
        row_layout.addWidget(btn_topo)
        row_layout.addWidget(btn_mm)
        row_layout.addWidget(btn_reset)
        row_layout.addWidget(btn_done)
        outer.addWidget(action_row)

        status_group = QtWidgets.QGroupBox("实时状态")
        status_layout = QtWidgets.QVBoxLayout(status_group)

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
        outer.addWidget(status_group)

        steps_group = QtWidgets.QGroupBox("测试步骤")
        steps_layout = QtWidgets.QVBoxLayout(steps_group)
        self._step_labels: List[QtWidgets.QLabel] = []
        for _ in range(5):
            label = QtWidgets.QLabel("")
            set_props(label, stepListItem=True)
            steps_layout.addWidget(label)
            self._step_labels.append(label)
        outer.addWidget(steps_group)

        records_group = QtWidgets.QGroupBox("9 组矢量压差记录（机组相 × 母排相，AA~CC）")
        records_layout = QtWidgets.QVBoxLayout(records_group)
        records_layout.setSpacing(2)
        self._record_labels: dict[str, QtWidgets.QLabel] = {}

        for gen_phase in "ABC":
            for bus_phase in "ABC":
                key = f"{gen_phase}{bus_phase}"
                row_widget = QtWidgets.QWidget()
                set_props(row_widget, recordRow=True)
                row = QtWidgets.QHBoxLayout(row_widget)
                row.setContentsMargins(10, 6, 10, 6)
                row.setSpacing(4)

                key_label = QtWidgets.QLabel(key)
                key_label.setFixedWidth(28)
                set_live_text(key_label, "info")

                hint_label = QtWidgets.QLabel(f"机{gen_phase}↔排{bus_phase}")
                hint_label.setFixedWidth(72)
                set_live_text(hint_label, "neutral")

                value_label = QtWidgets.QLabel("未记录")
                set_record_value(value_label, "neutral")

                record_btn = QtWidgets.QPushButton(f"记录 {key}")
                record_btn.setFixedWidth(72)
                record_btn.clicked.connect(
                    lambda _, g=gen_phase, b=bus_phase: self._api.record_pt_diff_measurement(
                        self._current_gen_id(),
                        g,
                        b,
                    )
                )
                apply_button_tone(self, record_btn, "primary")

                row.addWidget(key_label)
                row.addWidget(hint_label)
                row.addWidget(value_label)
                row.addStretch()
                row.addWidget(record_btn)
                records_layout.addWidget(row_widget)
                self._record_labels[key] = value_label

        outer.addWidget(records_group)
        outer.addStretch()

    def _current_gen_id(self) -> int:
        gen_id = self._pt_target_bg.checkedId()
        return gen_id if gen_id in (1, 2) else 1

    def _on_toggle_pt_exam_mode(self) -> None:
        both_started = (
            self._api.pt_exam_states[1].started and self._api.pt_exam_states[2].started
        )
        if both_started:
            self._api.stop_pt_exam(1)
            self._api.stop_pt_exam(2)
        else:
            self._api.start_pt_exam(1)
            self._api.start_pt_exam(2)

    def render(self, p) -> None:
        gen_id = self._current_gen_id()
        state = self._api.pt_exam_states[gen_id]
        records = state.records
        both_completed = (
            self._api.pt_exam_states[1].completed and self._api.pt_exam_states[2].completed
        )
        both_started = (
            self._api.pt_exam_states[1].started and self._api.pt_exam_states[2].started
        )

        if both_completed:
            self._mode_banner.setVisible(False)
            self._btn_start.setText("开始第四步测试")
            apply_button_tone(self, self._btn_start, "warning", hero=True)
            self._summary_lbl.setText(
                "✅ 第四步已确认完成：Gen1 和 Gen2 PT 二次端子压差测试均通过，数据已锁定。"
            )
            set_live_text(self._summary_lbl, "success")
            self._meter_lbl.setText("")
            self._feedback_lbl.setText("考核提示：第四步测试已完成，请继续进行第五步。")
            set_live_text(self._feedback_lbl, "success")
            for label, (text, _) in zip(self._step_labels, self._api.get_pt_exam_steps(gen_id)):
                set_step_item(label, text, True, True)
            for key, label in self._record_labels.items():
                record = records.get(key)
                if record is not None:
                    label.setText(f"{record['voltage_sec']:.2f} V ✓")
                    set_record_value(label, "success")
            return

        self._mode_banner.setVisible(both_started)
        if both_started:
            self._btn_start.setText("退出第四步测试")
            apply_button_tone(self, self._btn_start, "danger", hero=True)
        else:
            self._btn_start.setText("开始第四步测试")
            apply_button_tone(self, self._btn_start, "warning", hero=True)

        started = both_started
        feedback = state.feedback
        generator = self._api.get_generator_state(gen_id)
        current_combo = self._api.get_current_pt_exam_phase_match(gen_id)

        other_id = 2 if gen_id == 1 else 1
        other_done = all(
            self._api.pt_exam_states[other_id].records[key] is not None for key in _RECORD_KEYS
        )
        this_done = all(records[key] is not None for key in _RECORD_KEYS)

        if this_done and other_done:
            summary = "Gen1 和 Gen2 全部 9 组矢量压差已记录，可点击「完成第四步测试」锁定结果。"
            summary_tone = "success"
        elif this_done:
            summary = f"Gen {gen_id} 全部 9 组已记录，请切换至 Gen {other_id} 完成压差测量。"
            summary_tone = "warning"
        else:
            summary = f"Gen {gen_id} 当前开关柜位置：{generator.breaker_position}。"
            summary_tone = "info"
        self._summary_lbl.setText(summary)
        set_live_text(self._summary_lbl, summary_tone)

        meter_text = p.meter_reading
        if current_combo:
            meter_text = f"当前表笔：机组{current_combo[0]}相 ↔ 母排{current_combo[1]}相。{meter_text}"
        self._meter_lbl.setText(f"实时测量：{meter_text}")
        set_live_text(self._meter_lbl, tone_from_color(getattr(p, "meter_color", "black")))

        self._feedback_lbl.setText(f"考核提示：{feedback}")
        set_live_text(self._feedback_lbl, tone_from_color(state.feedback_color))

        steps = self._api.get_pt_exam_steps(gen_id)
        if not started:
            for label, (text, _) in zip(self._step_labels, steps):
                set_step_item(label, text, False, False)
        else:
            for label, (text, done) in zip(self._step_labels, steps):
                set_step_item(label, text, done, True)

        for key, label in self._record_labels.items():
            record = records.get(key)
            if record is None:
                label.setText("未记录")
                set_record_value(label, "neutral")
            else:
                label.setText(f"{record['voltage_sec']:.2f} V ✓")
                set_record_value(label, "success")
