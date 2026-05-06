"""
ui/tabs/pt_voltage_check_tab.py
PT 单体线电压检查 Tab（独立 QWidget 组件）
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
from ui.widgets._record_view import reading_text


_ALL_KEYS = (
    "PT1_AB", "PT1_BC", "PT1_CA",
    "PT2_AB", "PT2_BC", "PT2_CA",
    "PT3_AB", "PT3_BC", "PT3_CA",
)

_KEY_TO_NODES = {
    "PT1_AB": ("PT1_A", "PT1_B"), "PT1_BC": ("PT1_B", "PT1_C"), "PT1_CA": ("PT1_C", "PT1_A"),
    "PT2_AB": ("PT2_A", "PT2_B"), "PT2_BC": ("PT2_B", "PT2_C"), "PT2_CA": ("PT2_C", "PT2_A"),
    "PT3_AB": ("PT3_A", "PT3_B"), "PT3_BC": ("PT3_B", "PT3_C"), "PT3_CA": ("PT3_C", "PT3_A"),
}


class PtVoltageCheckTabAPI(Protocol):
    @property
    def pt_voltage_check_state(self) -> object: ...

    def reset_pt_voltage_check(self) -> None: ...

    def finalize_pt_voltage_check(self) -> None: ...

    def start_pt_voltage_check(self) -> None: ...

    def stop_pt_voltage_check(self) -> None: ...

    def record_pt_voltage_measurement(self, pt_name: str, pair: str) -> None: ...

    def get_pt_voltage_check_steps(self) -> List[Tuple[str, bool]]: ...


class PtVoltageCheckTab(QtWidgets.QWidget):
    def __init__(
        self,
        api: PtVoltageCheckTabAPI,
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

        header = QtWidgets.QLabel("隔离母排合闸前 - 第二步：PT 单体线电压检查")
        outer.addWidget(header)

        desc = QtWidgets.QLabel(
            "完成第一步后：① 恢复小电阻接地；② Gen1 起机并入母排（提供 PT1/PT2 参考电压）；"
            "③ 启动 Gen2，保持断路器断开（提供 PT3 参考电压）；④ 开启万用表，"
            "将红/黑表笔分别接同一 PT 的两相端子，依次测量 PT1/PT2/PT3 各自的 AB/BC/CA 线电压；"
            "⑤ 确认三组 PT 输出电压量级一致（均约 100V AC）后，点击「完成第二步测试」。"
        )
        desc.setWordWrap(True)
        outer.addWidget(desc)

        self._banner = QtWidgets.QLabel(
            "📏 第二步测试进行中 — 请在母排拓扑页完成 PT1/PT2/PT3 各相线电压测量"
        )
        self._banner.setWordWrap(True)
        self._banner.setVisible(False)
        outer.addWidget(self._banner)
        apply_step_shell(
            self,
            scroll,
            tab,
            header,
            desc,
            self._banner,
            banner_tone="success",
        )

        action_row = QtWidgets.QWidget()
        row_layout = QtWidgets.QHBoxLayout(action_row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        set_props(action_row, actionRow=True)

        self._btn_start = QtWidgets.QPushButton("开始第二步测试")
        self._btn_start.clicked.connect(self._on_toggle_start)
        apply_button_tone(self, self._btn_start, "warning", hero=True)

        btn_topo = QtWidgets.QPushButton("打开母排拓扑页")
        btn_topo.clicked.connect(self._on_open_circuit_tab)
        apply_button_tone(self, btn_topo, "primary", secondary=True)

        btn_mm = QtWidgets.QPushButton("开启/关闭万用表")
        btn_mm.clicked.connect(self._on_toggle_multimeter)
        apply_button_tone(self, btn_mm, "warning")

        btn_reset = QtWidgets.QPushButton("重置线电压检查")
        btn_reset.clicked.connect(self._api.reset_pt_voltage_check)
        apply_button_tone(self, btn_reset, "danger")

        btn_done = QtWidgets.QPushButton("完成第二步测试")
        btn_done.clicked.connect(self._api.finalize_pt_voltage_check)
        apply_button_tone(self, btn_done, "success", hero=True)

        row_layout.addWidget(self._btn_start)
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
        for _ in range(9):
            label = QtWidgets.QLabel("")
            set_props(label, stepListItem=True)
            steps_layout.addWidget(label)
            self._step_labels.append(label)
        outer.addWidget(steps_grp)

        rec_grp = QtWidgets.QGroupBox("PT 线电压测量记录（PT1/PT2/PT3 各三组，共九组）")
        rec_layout = QtWidgets.QVBoxLayout(rec_grp)
        self._record_labels: dict[str, QtWidgets.QLabel] = {}

        pt_colors = {"PT1": "#e8f4f8", "PT2": "#f0fff0", "PT3": "#fff3e0"}
        pt_hints = {
            "PT1": "←Gen1在母排，提供PT1二次参考电压",
            "PT2": "←母排电压，Gen1并入后与PT1同源",
            "PT3": "←Gen2起机（不合闸），提供PT3二次参考电压",
        }

        for pt_name in ("PT1", "PT2", "PT3"):
            pt_grp = QtWidgets.QGroupBox(f"{pt_name} 侧线电压  {pt_hints[pt_name]}")
            pt_grp.setStyleSheet(
                f"QGroupBox{{background:{pt_colors[pt_name]}; color:#444; font-size:13px;}}"
                "QGroupBox *{font-weight:normal; font-size:12px;}"
            )
            pt_layout = QtWidgets.QVBoxLayout(pt_grp)

            for pair in ("AB", "BC", "CA"):
                key = f"{pt_name}_{pair}"
                n1, n2 = _KEY_TO_NODES[key]
                row_widget = QtWidgets.QWidget()
                set_props(row_widget, recordRow=True)
                row = QtWidgets.QHBoxLayout(row_widget)
                row.setContentsMargins(10, 6, 10, 6)

                pair_label = QtWidgets.QLabel(f"{pair} 线电压")
                pair_label.setFixedWidth(80)
                set_live_text(pair_label, "info")

                probe_hint = QtWidgets.QLabel(f"（{n1} ↔ {n2}）")
                probe_hint.setFixedWidth(180)
                probe_hint.setStyleSheet("font-size:12px; color:#888888;")

                value_label = QtWidgets.QLabel("未记录")
                value_label.setFixedWidth(200)
                set_record_value(value_label, "neutral")

                record_btn = QtWidgets.QPushButton(f"记录 {key}")
                record_btn.clicked.connect(
                    lambda _, pt=pt_name, pp=pair: self._api.record_pt_voltage_measurement(pt, pp)
                )
                apply_button_tone(self, record_btn, "primary")

                row.addWidget(pair_label)
                row.addWidget(probe_hint)
                row.addWidget(value_label)
                row.addWidget(record_btn)
                pt_layout.addWidget(row_widget)
                self._record_labels[key] = value_label

            rec_layout.addWidget(pt_grp)

        outer.addWidget(rec_grp)
        outer.addStretch()

    def _on_toggle_start(self) -> None:
        if self._api.pt_voltage_check_state.started:
            self._api.stop_pt_voltage_check()
        else:
            self._api.start_pt_voltage_check()

    def render(self, p) -> None:
        state = self._api.pt_voltage_check_state
        records = state.records

        if state.completed:
            self._banner.setVisible(False)
            self._btn_start.setText("开始第二步测试")
            apply_button_tone(self, self._btn_start, "warning", hero=True)
            self._summary_lbl.setText("✅ 第二步已确认完成：PT1/PT2/PT3 线电压检查通过，数据已锁定。")
            set_live_text(self._summary_lbl, "success")
            self._meter_lbl.setText("")
            self._feedback_lbl.setText("操作提示：第二步测试已完成，请继续进行第三步 PT 相序检查。")
            set_live_text(self._feedback_lbl, "success")
            for label, (text, _) in zip(self._step_labels, self._api.get_pt_voltage_check_steps()):
                set_step_item(label, text, True, True)
            for key, label in self._record_labels.items():
                record = records.get(key)
                if record is not None:
                    ok = record.get("passed") is True
                    label.setText(f"{reading_text(record)} {'✓' if ok else '⚠'}")
                    set_record_value(label, "success" if ok else "warning")
            return

        started = state.started
        self._banner.setVisible(started)
        if started:
            self._btn_start.setText("退出第二步测试")
            apply_button_tone(self, self._btn_start, "danger", hero=True)
        else:
            self._btn_start.setText("开始第二步测试")
            apply_button_tone(self, self._btn_start, "warning", hero=True)

        feedback = state.feedback
        done_count = sum(1 for key in _ALL_KEYS if records.get(key) is not None)
        if done_count == 9:
            summary = 'PT1/PT2/PT3 线电压已全部记录，请点击“完成第二步测试”继续。'
            summary_tone = "warning"
        elif done_count > 0:
            summary = f"已记录 {done_count}/9 组线电压，请继续完成剩余项目。"
            summary_tone = "info"
        else:
            summary = "请按步骤：Gen1并网 → 启动Gen2(不合闸) → 万用表 → 逐项记录PT1/PT2/PT3线电压。"
            summary_tone = "info"

        self._summary_lbl.setText(summary)
        set_live_text(self._summary_lbl, summary_tone)

        self._meter_lbl.setText(f"实时测量：{p.meter_reading}")
        set_props(
            self._meter_lbl,
            liveText=True,
            tone=tone_from_color(getattr(p, "meter_color", "black")),
        )

        self._feedback_lbl.setText(f"操作提示：{feedback}")
        set_live_text(self._feedback_lbl, tone_from_color(state.feedback_color))

        steps = self._api.get_pt_voltage_check_steps()
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
                continue

            ok = record.get("passed") is True
            label.setText(f"{reading_text(record)} {'✓' if ok else '⚠'}")
            set_record_value(label, "success" if ok else "warning")
