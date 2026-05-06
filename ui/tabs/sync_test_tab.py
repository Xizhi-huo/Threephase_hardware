"""
ui/tabs/sync_test_tab.py
同步功能测试 Tab（独立 QWidget 组件）
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


class SyncTestTabAPI(Protocol):
    @property
    def sync_test_state(self) -> object: ...

    @property
    def sim_state(self) -> object: ...

    def reset_sync_test(self) -> None: ...

    def finalize_sync_test(self) -> None: ...

    def start_sync_test(self) -> None: ...

    def stop_sync_test(self) -> None: ...

    def record_sync_round(self, round_no: int) -> None: ...

    def get_sync_test_steps(self) -> List[Tuple[str, bool]]: ...

    def is_sync_test_complete(self) -> bool: ...

    def is_gen_synced(self, gen_a, gen_b) -> bool: ...


class SyncTestTab(QtWidgets.QWidget):
    def __init__(
        self,
        api: SyncTestTabAPI,
        *,
        on_open_waveform_tab: Callable[[], None],
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._api = api
        self._on_open_waveform_tab = on_open_waveform_tab
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

        header = QtWidgets.QLabel("隔离母排合闸前 - 第五步：同步功能测试")
        outer.addWidget(header)

        desc = QtWidgets.QLabel(
            "验证两台发电机的同步功能是否正常：第一轮以 Gen 1 为基准合闸，"
            "Gen 2 切至自动模式同步跟踪；第二轮互换角色，Gen 2 为基准，Gen 1 自动同步。"
            "两轮均记录后测试完成。"
        )
        desc.setWordWrap(True)
        outer.addWidget(desc)

        self._mode_banner = QtWidgets.QLabel(
            "⚡ 第五步测试进行中 — 请按两轮步骤完成同步功能验证"
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
            banner_tone="warning",
        )

        action_row = QtWidgets.QWidget()
        row_layout = QtWidgets.QHBoxLayout(action_row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        set_props(action_row, actionRow=True)

        self._btn_start = QtWidgets.QPushButton("开始第五步测试")
        self._btn_start.clicked.connect(self._on_toggle_sync_test_mode)
        apply_button_tone(self, self._btn_start, "warning", hero=True)

        btn_wave = QtWidgets.QPushButton("打开波形/相量页")
        btn_wave.clicked.connect(self._on_open_waveform_tab)
        apply_button_tone(self, btn_wave, "primary", secondary=True)

        btn_reset = QtWidgets.QPushButton("重置同步测试")
        btn_reset.clicked.connect(self._api.reset_sync_test)
        apply_button_tone(self, btn_reset, "danger")

        btn_done = QtWidgets.QPushButton("完成第五步测试")
        btn_done.clicked.connect(self._api.finalize_sync_test)
        apply_button_tone(self, btn_done, "success", hero=True)

        row_layout.addWidget(self._btn_start)
        row_layout.addWidget(btn_wave)
        row_layout.addWidget(btn_reset)
        row_layout.addWidget(btn_done)
        outer.addWidget(action_row)

        status_grp = QtWidgets.QGroupBox("实时同步状态")
        status_layout = QtWidgets.QVBoxLayout(status_grp)

        self._summary_lbl = QtWidgets.QLabel("")
        set_live_text(self._summary_lbl, "info")
        self._summary_lbl.setWordWrap(True)

        self._live_lbl = QtWidgets.QLabel("")
        set_live_text(self._live_lbl, "neutral")
        self._live_lbl.setWordWrap(True)

        self._feedback_lbl = QtWidgets.QLabel("")
        set_live_text(self._feedback_lbl, "neutral")
        self._feedback_lbl.setWordWrap(True)

        status_layout.addWidget(self._summary_lbl)
        status_layout.addWidget(self._live_lbl)
        status_layout.addWidget(self._feedback_lbl)
        outer.addWidget(status_grp)

        steps_grp = QtWidgets.QGroupBox("测试步骤（共两轮，需按顺序完成）")
        steps_layout = QtWidgets.QVBoxLayout(steps_grp)
        self._step_labels: List[QtWidgets.QLabel] = []
        for _ in range(12):
            label = QtWidgets.QLabel("")
            set_props(label, stepListItem=True)
            steps_layout.addWidget(label)
            self._step_labels.append(label)
        outer.addWidget(steps_grp)

        rec_grp = QtWidgets.QGroupBox("记录测试结果")
        rec_layout = QtWidgets.QVBoxLayout(rec_grp)

        row1_widget = QtWidgets.QWidget()
        set_props(row1_widget, recordRow=True)
        row1 = QtWidgets.QHBoxLayout(row1_widget)
        row1.setContentsMargins(10, 6, 10, 6)
        self._round1_lbl = QtWidgets.QLabel("Gen 1 基准 → Gen 2 同步：未记录")
        set_record_value(self._round1_lbl, "neutral")
        btn_r1 = QtWidgets.QPushButton("记录第一轮")
        btn_r1.clicked.connect(lambda: self._api.record_sync_round(1))
        apply_button_tone(self, btn_r1, "primary")
        row1.addWidget(self._round1_lbl, 1)
        row1.addWidget(btn_r1)
        rec_layout.addWidget(row1_widget)

        row2_widget = QtWidgets.QWidget()
        set_props(row2_widget, recordRow=True)
        row2 = QtWidgets.QHBoxLayout(row2_widget)
        row2.setContentsMargins(10, 6, 10, 6)
        self._round2_lbl = QtWidgets.QLabel("Gen 2 基准 → Gen 1 同步：未记录")
        set_record_value(self._round2_lbl, "neutral")
        btn_r2 = QtWidgets.QPushButton("记录第二轮")
        btn_r2.clicked.connect(lambda: self._api.record_sync_round(2))
        apply_button_tone(self, btn_r2, "primary")
        row2.addWidget(self._round2_lbl, 1)
        row2.addWidget(btn_r2)
        rec_layout.addWidget(row2_widget)

        outer.addWidget(rec_grp)
        outer.addStretch()

    def _on_toggle_sync_test_mode(self) -> None:
        if self._api.sync_test_state.started:
            self._api.stop_sync_test()
        else:
            self._api.start_sync_test()

    @staticmethod
    def _phase_diff(gen_a, gen_b) -> float:
        delta = abs(gen_a.phase_deg - gen_b.phase_deg)
        return min(delta, 360.0 - delta)

    def render(self, p) -> None:
        state = self._api.sync_test_state
        sim = self._api.sim_state
        gen1, gen2 = sim.gen1, sim.gen2
        started = state.started

        if state.completed:
            self._mode_banner.setVisible(False)
            self._btn_start.setText("开始第五步测试")
            apply_button_tone(self, self._btn_start, "warning", hero=True)
            self._summary_lbl.setText("✅ 第五步已确认完成：同步功能测试通过，数据已锁定。")
            set_live_text(self._summary_lbl, "success")
            self._live_lbl.setText("")
            self._feedback_lbl.setText("操作提示：第五步测试已完成，全部预合闸测量流程通过。")
            set_live_text(self._feedback_lbl, "success")
            for label, (text, _) in zip(self._step_labels, self._api.get_sync_test_steps()):
                set_step_item(label, text, True, True)
            self._round1_lbl.setText("Gen 1 基准 → Gen 2 同步：已记录 ✓")
            set_record_value(self._round1_lbl, "success")
            self._round2_lbl.setText("Gen 2 基准 → Gen 1 同步：已记录 ✓")
            set_record_value(self._round2_lbl, "success")
            return

        self._mode_banner.setVisible(started)
        if started:
            self._btn_start.setText("退出第五步测试")
            apply_button_tone(self, self._btn_start, "danger", hero=True)
        else:
            self._btn_start.setText("开始第五步测试")
            apply_button_tone(self, self._btn_start, "warning", hero=True)

        if self._api.is_sync_test_complete():
            summary = "第五步已确认完成：同步功能测试通过，系统已恢复正常自动合闸逻辑。"
            summary_tone = "success"
        elif state.round1_done and state.round2_done:
            summary = "两轮同步测试记录已完成，请点击“完成第五步测试”。"
            summary_tone = "warning"
        elif state.round1_done:
            summary = "第一轮已完成，请互换角色进行第二轮测试。"
            summary_tone = "warning"
        else:
            summary = "请按步骤完成两轮同步测试。"
            summary_tone = "info"
        self._summary_lbl.setText(summary)
        set_live_text(self._summary_lbl, summary_tone)

        ref_gen = getattr(p, "bus_reference_gen", None)
        if ref_gen == 1 and gen2.mode == "auto":
            df = abs(gen2.freq - gen1.freq)
            dv = abs(gen2.amp - gen1.amp)
            dp = self._phase_diff(gen2, gen1)
            synced = self._api.is_gen_synced(gen2, gen1)
            self._live_lbl.setText(
                f"[第一轮] Gen2跟踪Gen1 — Δf={df:.3f} Hz，ΔV={dv:.0f} V，Δθ={dp:.1f}°  "
                f"{'[已同步 ✓]' if synced else '[同步中…]'}"
            )
            set_live_text(self._live_lbl, "success" if synced else "warning")
        elif ref_gen == 2 and gen1.mode == "auto":
            df = abs(gen1.freq - gen2.freq)
            dv = abs(gen1.amp - gen2.amp)
            dp = self._phase_diff(gen1, gen2)
            synced = self._api.is_gen_synced(gen1, gen2)
            self._live_lbl.setText(
                f"[第二轮] Gen1跟踪Gen2 — Δf={df:.3f} Hz，ΔV={dv:.0f} V，Δθ={dp:.1f}°  "
                f"{'[已同步 ✓]' if synced else '[同步中…]'}"
            )
            set_live_text(self._live_lbl, "success" if synced else "warning")
        elif gen1.mode == "auto" and gen2.mode == "auto":
            df = abs(gen1.freq - gen2.freq)
            dv = abs(gen1.amp - gen2.amp)
            dp = self._phase_diff(gen1, gen2)
            synced = self._api.is_gen_synced(gen1, gen2)
            self._live_lbl.setText(
                f"[最终] 双机自动 — Δf={df:.3f} Hz，ΔV={dv:.0f} V，Δθ={dp:.1f}°  "
                f"{'[三值收敛 ✓ 可完成]' if synced else '[等待收敛…]'}"
            )
            set_live_text(self._live_lbl, "success" if synced else "warning")
        else:
            self._live_lbl.setText(
                f"母排基准: {'Gen ' + str(ref_gen) if ref_gen else '无（死母线）'}  "
                f"| Gen1: {gen1.freq:.2f}Hz/{gen1.amp:.0f}V ({gen1.mode})  "
                f"| Gen2: {gen2.freq:.2f}Hz/{gen2.amp:.0f}V ({gen2.mode})"
            )
            set_live_text(self._live_lbl, "neutral")

        self._feedback_lbl.setText(f"操作提示：{state.feedback}")
        set_live_text(self._feedback_lbl, tone_from_color(state.feedback_color))

        steps = self._api.get_sync_test_steps()
        if not started:
            for label, (text, _) in zip(self._step_labels, steps):
                set_step_item(label, text, False, False)
        else:
            for label, (text, done) in zip(self._step_labels, steps):
                set_step_item(label, text, done, True)

        if state.round1_done:
            self._round1_lbl.setText("Gen 1 基准 → Gen 2 同步：已记录 ✓")
            set_record_value(self._round1_lbl, "success")
        else:
            self._round1_lbl.setText("Gen 1 基准 → Gen 2 同步：未记录")
            set_record_value(self._round1_lbl, "neutral")

        if state.round2_done:
            self._round2_lbl.setText("Gen 2 基准 → Gen 1 同步：已记录 ✓")
            set_record_value(self._round2_lbl, "success")
        else:
            self._round2_lbl.setText("Gen 2 基准 → Gen 1 同步：未记录")
            set_record_value(self._round2_lbl, "neutral")
