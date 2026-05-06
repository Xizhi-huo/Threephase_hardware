from typing import Callable, Optional, TYPE_CHECKING

from PyQt5 import QtCore, QtWidgets

from ui.tabs._step_style import apply_button_tone
from ui.widgets.step_panels._panel_builders import (
    add_load_share_cabinet_section,
    make_button,
    make_feedback_label,
    make_gen_block,
    make_gen_fap_block,
    make_inline_row,
    make_note_label,
    make_step_list,
    set_feedback_label,
    set_props,
    set_step_list_label,
)

if TYPE_CHECKING:
    from ui.test_panel import TestPanelAPI


class SyncTestPanel(QtWidgets.QGroupBox):
    def __init__(
        self,
        api: "TestPanelAPI",
        *,
        get_current_test_step: Callable[[], int],
        is_step_complete: Callable[[int], bool],
        on_toggle_multimeter: Optional[Callable[[], None]] = None,
        show_load_share_cabinet_dialog: Optional[Callable[[], None]] = None,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__("第五步：同步功能测试", parent)
        self._api = api
        self._get_current_test_step = get_current_test_step
        self._is_step_complete = is_step_complete
        self._show_load_share_cabinet_dialog = show_load_share_cabinet_dialog
        self.gen_refs = {}
        self._build()

    def _build(self):
        lay = QtWidgets.QVBoxLayout(self)
        lay.setSpacing(4)
        self.tp_s5_step_lbls = make_step_list(lay, 12)

        rs_row = make_inline_row()
        rs_h = QtWidgets.QHBoxLayout(rs_row)
        rs_h.setContentsMargins(4, 2, 4, 2)
        rs_h.addWidget(make_note_label("远程启动信号:"))
        self.tp_s5_remote_btn = QtWidgets.QPushButton("⚡ 开启自动")
        self.tp_s5_remote_btn.setCheckable(True)
        apply_button_tone(self, self.tp_s5_remote_btn, "primary", secondary=True)
        self.tp_s5_remote_btn.clicked.connect(self._on_tp_s5_remote_toggle)
        rs_h.addStretch()
        rs_h.addWidget(self.tp_s5_remote_btn)
        lay.addWidget(rs_row)

        make_gen_block(
            lay,
            owner=self,
            api=self._api,
            gen_refs=self.gen_refs,
            step_key="s5",
            gen_id=1,
            mode_options=[("手动", "manual"), ("自动", "auto")],
            show_engine=True,
        )
        self._tp_s5_fap = {1: make_gen_fap_block(lay, api=self._api, gen_id=1)}
        make_gen_block(
            lay,
            owner=self,
            api=self._api,
            gen_refs=self.gen_refs,
            step_key="s5",
            gen_id=2,
            mode_options=[("手动", "manual"), ("自动", "auto")],
            show_engine=True,
        )
        self._tp_s5_fap[2] = make_gen_fap_block(lay, api=self._api, gen_id=2)

        lay.addWidget(make_note_label("同步误差监测（越低越好，趋近零可合闸）:", "primary"))
        self.tp_s5_bars = {}
        for key, label, unit, max_val in [
            ("freq", "频率差", "Hz", 5.0),
            ("amp", "幅值差", "V", 5000.0),
            ("phase", "相位差", "°", 180.0),
        ]:
            rw = make_inline_row()
            rh = QtWidgets.QHBoxLayout(rw)
            rh.setContentsMargins(4, 2, 4, 2)
            rh.setSpacing(4)
            lbl = QtWidgets.QLabel(f"{label}({unit})")
            lbl.setFixedWidth(72)
            set_props(lbl, noteText=True)
            bar = QtWidgets.QProgressBar()
            bar.setRange(0, 1000)
            bar.setValue(0)
            bar.setTextVisible(False)
            bar.setFixedHeight(14)
            set_props(bar, metricBar=True)
            val_lbl = QtWidgets.QLabel("0.0")
            val_lbl.setFixedWidth(46)
            set_props(val_lbl, valueChip=True)
            val_lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            rh.addWidget(lbl)
            rh.addWidget(bar, 1)
            rh.addWidget(val_lbl)
            lay.addWidget(rw)
            self.tp_s5_bars[key] = (bar, val_lbl, max_val)

        btn_r1 = make_button(self, "记录第一轮（Gen1 基准 → Gen2 同步）", "#16a34a")
        btn_r1.clicked.connect(lambda: self._api.record_sync_round(1))
        lay.addWidget(btn_r1)
        btn_r2 = make_button(self, "记录第二轮（Gen2 基准 → Gen1 同步）", "#16a34a")
        btn_r2.clicked.connect(lambda: self._api.record_sync_round(2))
        lay.addWidget(btn_r2)
        if self._show_load_share_cabinet_dialog is not None:
            add_load_share_cabinet_section(
                lay,
                owner=self,
                show_load_share_cabinet_dialog=self._show_load_share_cabinet_dialog,
            )

        self.tp_s5_fb_lbl = make_feedback_label("请按步骤列表操作")
        self.tp_s5_fb_lbl.setMinimumHeight(48)
        lay.addWidget(self.tp_s5_fb_lbl)

    def _on_tp_s5_remote_toggle(self, checked):
        self._api.sim_state.remote_start_signal = checked
        if checked:
            self.tp_s5_remote_btn.setText("⚡ 关闭自动")
            apply_button_tone(self, self.tp_s5_remote_btn, "success")
        else:
            self.tp_s5_remote_btn.setText("⚡ 开启自动")
            apply_button_tone(self, self.tp_s5_remote_btn, "primary", secondary=True)

    def on_enter(self) -> None:
        pass

    def reset(self) -> None:
        pass

    def refresh(self, rs, step: int) -> None:
        sim = self._api.sim_state
        state = self._api.sync_test_state
        in_mode = state.started
        for lbl, (text, done) in zip(self.tp_s5_step_lbls, self._api.get_sync_test_steps()):
            set_step_list_label(lbl, text, done, in_mode)
        rs_value = sim.remote_start_signal
        self.tp_s5_remote_btn.blockSignals(True)
        self.tp_s5_remote_btn.setChecked(rs_value)
        self.tp_s5_remote_btn.blockSignals(False)
        if rs_value:
            self.tp_s5_remote_btn.setText("⚡ 关闭自动")
            apply_button_tone(self, self.tp_s5_remote_btn, "success")
        else:
            self.tp_s5_remote_btn.setText("⚡ 开启自动")
            apply_button_tone(self, self.tp_s5_remote_btn, "primary", secondary=True)

        for gid, entry_map in self._tp_s5_fap.items():
            gen = sim.gen1 if gid == 1 else sim.gen2
            is_auto = gen.mode == "auto"
            for attr, (sl, entry) in entry_map.items():
                scale = 10 if attr in ("freq", "phase_deg") else 1
                sl.blockSignals(True)
                sl.setValue(int(getattr(gen, attr) * scale))
                sl.blockSignals(False)
                sl.setEnabled(not is_auto)
                if not entry.hasFocus():
                    entry.setText(f"{getattr(gen, attr):.1f}")
                entry.setReadOnly(is_auto)
                set_props(entry, compactInput=True, readonlyTone=is_auto)

        gen1, gen2 = sim.gen1, sim.gen2
        freq_diff = abs(gen1.freq - gen2.freq)
        amp_diff = abs(getattr(gen1, "actual_amp", gen1.amp) - getattr(gen2, "actual_amp", gen2.amp))
        pd = abs(gen1.phase_deg - gen2.phase_deg)
        phase_diff = min(pd, 360.0 - pd)
        for key, diff in [("freq", freq_diff), ("amp", amp_diff), ("phase", phase_diff)]:
            bar, val_lbl, max_val = self.tp_s5_bars[key]
            bar.setValue(min(1000, int(1000 * diff / max_val)))
            val_lbl.setText(f"{diff:.1f}")
        set_feedback_label(self.tp_s5_fb_lbl, state.feedback, state.feedback_color)
