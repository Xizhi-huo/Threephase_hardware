from typing import Callable, Optional, TYPE_CHECKING

from PyQt5 import QtCore, QtWidgets

from domain.constants import DEFAULT_PT_RATIO_ROWS
from ui.widgets.step_panels._panel_builders import (
    add_blackbox_section,
    add_load_share_cabinet_section,
    make_button,
    make_feedback_label,
    make_gen_block,
    make_gen_fap_block,
    make_group,
    make_inline_row,
    make_note_label,
    make_step_list,
    set_feedback_label,
    set_props,
    set_step_list_label,
)

if TYPE_CHECKING:
    from ui.test_panel import TestPanelAPI


class PtVoltageCheckPanel(QtWidgets.QGroupBox):
    def __init__(
        self,
        api: "TestPanelAPI",
        *,
        get_current_test_step: Callable[[], int],
        is_step_complete: Callable[[int], bool],
        on_toggle_multimeter: Optional[Callable[[], None]] = None,
        show_blackbox_dialog: Optional[Callable[[str], None]] = None,
        show_load_share_cabinet_dialog: Optional[Callable[[], None]] = None,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__("第二步：PT 单体线电压检查", parent)
        self._api = api
        self._get_current_test_step = get_current_test_step
        self._is_step_complete = is_step_complete
        self._show_blackbox_dialog = show_blackbox_dialog
        self._show_load_share_cabinet_dialog = show_load_share_cabinet_dialog
        self.gen_refs = {}
        self._build()

    def _build(self):
        lay = QtWidgets.QVBoxLayout(self)
        lay.setSpacing(4)
        self.tp_s2_step_lbls = make_step_list(lay, 9)

        pt_ratio_grp = make_group("PT 变比参数（停机状态下确认）")
        pt_ratio_lay = QtWidgets.QVBoxLayout(pt_ratio_grp)
        pt_ratio_lay.setSpacing(4)
        pt_ratio_lay.setContentsMargins(4, 6, 4, 4)
        self._tp_s2_ratio_rows = {}
        for row_label, ratio_attr in [
            ("PT1 (Gen1侧)", "pt_gen_ratio"),
            ("PT3 (Gen2侧)", "pt3_ratio"),
            ("PT2 (母排侧)", "pt_bus_ratio"),
        ]:
            pri_default, sec_default = DEFAULT_PT_RATIO_ROWS[ratio_attr]
            pt_ratio_lay.addWidget(make_note_label(row_label, "primary"))
            rw = make_inline_row()
            rh = QtWidgets.QHBoxLayout(rw)
            rh.setContentsMargins(0, 0, 0, 0)
            rh.setSpacing(4)
            pri_spin = QtWidgets.QSpinBox()
            pri_spin.setRange(100, 100000)
            pri_spin.setValue(pri_default)
            pri_spin.setSuffix(" V")
            pri_spin.setFixedWidth(90)
            set_props(pri_spin, compactInput=True)
            sec_spin = QtWidgets.QSpinBox()
            sec_spin.setRange(1, 10000)
            sec_spin.setValue(sec_default)
            sec_spin.setSuffix(" V")
            sec_spin.setFixedWidth(78)
            set_props(sec_spin, compactInput=True)
            ratio_lbl = QtWidgets.QLabel(f"{pri_default / sec_default:.2f}")
            ratio_lbl.setFixedWidth(52)
            set_props(ratio_lbl, valueChip=True)
            ratio_lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

            def _update_ratio(_val=None, _p=pri_spin, _s=sec_spin, _l=ratio_lbl, _a=ratio_attr):
                pri = _p.value()
                sec = max(1, _s.value())
                ratio = pri / sec
                _l.setText(f"{ratio:.2f}")
                self._api.update_pt_ratio(_a, ratio)

            pri_spin.valueChanged.connect(_update_ratio)
            sec_spin.valueChanged.connect(_update_ratio)
            rh.addWidget(pri_spin)
            rh.addWidget(make_note_label(":"))
            rh.addWidget(sec_spin)
            rh.addWidget(make_note_label("="))
            rh.addWidget(ratio_lbl)
            pt_ratio_lay.addWidget(rw)
            self._tp_s2_ratio_rows[ratio_attr] = (pri_spin, sec_spin, ratio_lbl)
        lay.addWidget(pt_ratio_grp)

        lay.addWidget(make_note_label("中性点接地（应恢复为小电阻接地）:"))
        gnd_row = make_inline_row()
        gnd_h = QtWidgets.QHBoxLayout(gnd_row)
        gnd_h.setContentsMargins(0, 0, 0, 0)
        self._tp_s2_gnd_bg = QtWidgets.QButtonGroup(self)
        self._tp_s2_gnd_rbs = {}
        for label, val in [("断开", "断开"), ("小电阻", "小电阻接地"), ("直接", "直接接地")]:
            rb = QtWidgets.QRadioButton(label)
            set_props(rb, inlineRadio=True)
            rb.setChecked(self._api.sim_state.grounding_mode == val)
            rb.toggled.connect(
                lambda chk, v=val: setattr(self._api.sim_state, "grounding_mode", v) if chk else None
            )
            self._tp_s2_gnd_bg.addButton(rb)
            gnd_h.addWidget(rb)
            self._tp_s2_gnd_rbs[val] = rb
        lay.addWidget(gnd_row)

        make_gen_block(lay, owner=self, api=self._api, gen_refs=self.gen_refs, step_key="s2", gen_id=1)
        lay.addWidget(make_note_label("Gen2 起机后保持断路器断开（提供PT3参考）", "warning", italic=True))
        make_gen_block(lay, owner=self, api=self._api, gen_refs=self.gen_refs, step_key="s2", gen_id=2)

        self.tp_s2_probe_lbl = make_feedback_label("当前表笔: 未放置")
        set_props(self.tp_s2_probe_lbl, feedbackText=True, tone="warning")
        lay.addWidget(self.tp_s2_probe_lbl)

        lay.addWidget(make_note_label("按相位快速记录（A→AB，B→BC，C→CA）:"))
        rrow = make_inline_row()
        rh = QtWidgets.QHBoxLayout(rrow)
        rh.setContentsMargins(0, 0, 0, 0)
        rh.setSpacing(4)
        self.tp_s2_rec_btns = {}
        phase_to_pair = {"A": "AB", "B": "BC", "C": "CA"}
        for ph in ("A", "B", "C"):
            pair = phase_to_pair[ph]
            btn = make_button(self, f"记录 {pair}", "#1d4ed8")
            btn.clicked.connect(lambda _, p=ph, pa=pair: self._tp_s2_record(p, pa))
            rh.addWidget(btn)
            self.tp_s2_rec_btns[ph] = btn
        lay.addWidget(rrow)

        lay.addWidget(make_note_label("调节发电机使各 PT 一次侧线电压均达到 10.5 kV:", "primary"))
        self._tp_s2_fap = {
            1: make_gen_fap_block(lay, api=self._api, gen_id=1),
            2: make_gen_fap_block(lay, api=self._api, gen_id=2),
        }

        if self._show_blackbox_dialog is not None:
            add_blackbox_section(
                lay,
                owner=self,
                api=self._api,
                show_blackbox_dialog=self._show_blackbox_dialog,
            )
        if self._show_load_share_cabinet_dialog is not None:
            add_load_share_cabinet_section(
                lay,
                owner=self,
                show_load_share_cabinet_dialog=self._show_load_share_cabinet_dialog,
            )

        self.tp_s2_fb_lbl = make_feedback_label("请按步骤列表操作")
        lay.addWidget(self.tp_s2_fb_lbl)

    def _tp_s2_record(self, phase, pair):
        sim = self._api.sim_state
        n1 = sim.probe1_node or ""
        pt_name = n1.split("_")[0] if n1.startswith("PT") else None
        if pt_name:
            self._api.record_pt_voltage_measurement(pt_name, pair)
        else:
            self._api.pt_voltage_check_state.feedback = "请先将表笔放在某一 PT 的两相端子上，再点击记录。"
            self._api.pt_voltage_check_state.feedback_color = "red"

    def on_enter(self) -> None:
        pass

    def reset(self) -> None:
        pass

    def refresh(self, rs, step: int) -> None:
        sim = self._api.sim_state
        in_mode = self._api.pt_voltage_check_state.started
        for lbl, (text, done) in zip(self.tp_s2_step_lbls, self._api.get_pt_voltage_check_steps()):
            set_step_list_label(lbl, text, done, in_mode)
        for val, rb in self._tp_s2_gnd_rbs.items():
            rb.blockSignals(True)
            rb.setChecked(sim.grounding_mode == val)
            rb.blockSignals(False)
        n1, n2 = sim.probe1_node, sim.probe2_node
        if n1 and n2:
            self.tp_s2_probe_lbl.setText(f"当前表笔: {n1} ↔ {n2}")
            set_props(self.tp_s2_probe_lbl, feedbackText=True, tone="info")
        else:
            self.tp_s2_probe_lbl.setText("当前表笔: 未放置")
            set_props(self.tp_s2_probe_lbl, feedbackText=True, tone="warning")

        any_running = sim.gen1.running or sim.gen2.running
        for pri_spin, sec_spin, ratio_lbl in self._tp_s2_ratio_rows.values():
            pri_spin.setEnabled(not any_running)
            sec_spin.setEnabled(not any_running)
            p, s = pri_spin.value(), max(1, sec_spin.value())
            ratio_lbl.setText(f"{p / s:.2f}")

        for gid, entry_map in self._tp_s2_fap.items():
            gen = sim.gen1 if gid == 1 else sim.gen2
            for attr, (sl, entry) in entry_map.items():
                scale = 10 if attr in ("freq", "phase_deg") else 1
                if not sl.isSliderDown():
                    sl.blockSignals(True)
                    sl.setValue(int(getattr(gen, attr) * scale))
                    sl.blockSignals(False)
                if not entry.hasFocus():
                    entry.setText(f"{getattr(gen, attr):.1f}")

        state = self._api.pt_voltage_check_state
        set_feedback_label(self.tp_s2_fb_lbl, state.feedback, state.feedback_color)
