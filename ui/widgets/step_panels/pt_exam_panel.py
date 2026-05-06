from typing import Callable, Optional, TYPE_CHECKING

from PyQt5 import QtCore, QtWidgets

from ui.widgets.manual_entry import PtDiffManualEntryWidget
from ui.widgets.step_panels._panel_builders import (
    add_blackbox_section,
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


class PtExamPanel(QtWidgets.QGroupBox):
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
        super().__init__("第四步：PT 二次端子压差测试", parent)
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
        self.tp_s4_step_lbls = make_step_list(lay, 5)
        make_gen_block(lay, owner=self, api=self._api, gen_refs=self.gen_refs, step_key="s4", gen_id=1)
        make_gen_block(lay, owner=self, api=self._api, gen_refs=self.gen_refs, step_key="s4", gen_id=2)
        lay.addWidget(make_note_label("调节 Gen 2 频率/幅值使 PT 二次压差趋近于零:", "primary"))
        self._tp_s4_fap = {2: make_gen_fap_block(lay, api=self._api, gen_id=2)}

        self._manual_mode = False
        self._simulated_entry_widgets: list[QtWidgets.QWidget] = []
        mode_row = make_inline_row()
        mode_lay = QtWidgets.QHBoxLayout(mode_row)
        mode_lay.setContentsMargins(0, 0, 0, 0)
        mode_lay.setSpacing(6)
        self._entry_mode_bg = QtWidgets.QButtonGroup(self)
        self._sim_mode_rb = QtWidgets.QRadioButton("虚拟表笔录入")
        self._manual_mode_rb = QtWidgets.QRadioButton("手动录入（真实仪表）")
        self._sim_mode_rb.setChecked(True)
        for rb in (self._sim_mode_rb, self._manual_mode_rb):
            set_props(rb, inlineRadio=True)
            self._entry_mode_bg.addButton(rb)
            mode_lay.addWidget(rb)
        self._manual_mode_rb.toggled.connect(lambda checked: self._set_manual_mode(bool(checked)))
        lay.addWidget(mode_row)

        target_note = make_note_label("测试对象:")
        lay.addWidget(target_note)
        self._simulated_entry_widgets.append(target_note)
        sel_row = make_inline_row()
        sh = QtWidgets.QHBoxLayout(sel_row)
        sh.setContentsMargins(0, 0, 0, 0)
        self._tp_s4_bg = QtWidgets.QButtonGroup(self)
        for txt, val in [("Gen 1", 1), ("Gen 2", 2)]:
            rb = QtWidgets.QRadioButton(txt)
            rb.setChecked(val == 1)
            set_props(rb, inlineRadio=True)
            self._tp_s4_bg.addButton(rb, val)
            sh.addWidget(rb)
        lay.addWidget(sel_row)
        self._simulated_entry_widgets.append(sel_row)

        rrow = make_inline_row()
        rh = QtWidgets.QHBoxLayout(rrow)
        rh.setContentsMargins(0, 0, 0, 0)
        btn_rec = make_button(self, "记录当前表笔位置", "#16a34a")
        btn_rec.clicked.connect(lambda: self._api.record_current_pt_measurement(max(1, self._tp_s4_bg.checkedId())))
        rh.addWidget(btn_rec)
        lay.addWidget(rrow)
        self._simulated_entry_widgets.append(rrow)

        self.manual_widget = PtDiffManualEntryWidget(self)
        self.manual_widget.submitted.connect(self._on_manual_submitted)
        self.manual_widget.setVisible(False)
        lay.addWidget(self.manual_widget)

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

        self._tp_s4_quick_btn = make_button(self, "⚡ 快捷记录全部18组", "#7c3aed")
        self._tp_s4_quick_btn.setToolTip("跳过逐组表笔测量，直接从物理引擎计算 Gen1+Gen2 全部 18 组压差并写入。")
        self._tp_s4_quick_btn.clicked.connect(lambda: self._api.record_all_pt_measurements_quick())
        self._tp_s4_quick_btn.setVisible(False)
        lay.addWidget(self._tp_s4_quick_btn)

        self.tp_s4_fb_lbl = make_feedback_label("请按步骤列表操作")
        lay.addWidget(self.tp_s4_fb_lbl)

    def _set_manual_mode(self, manual: bool) -> None:
        self._manual_mode = manual
        for widget in self._simulated_entry_widgets:
            widget.setVisible(not manual)
        self.manual_widget.setVisible(manual)
        if manual:
            self._tp_s4_quick_btn.setVisible(False)

    def _on_manual_submitted(self, kwargs: dict) -> None:
        try:
            self._api.record_pt_diff_measurement(**kwargs)
        except ValueError as exc:
            self.manual_widget._show_input_error(str(exc))
            return
        gen_id = int(kwargs.get("gen_id", max(1, self._tp_s4_bg.checkedId())))
        state = self._api.pt_exam_states[gen_id]
        set_feedback_label(self.tp_s4_fb_lbl, state.feedback, state.feedback_color)

    def on_enter(self) -> None:
        pass

    def reset(self) -> None:
        pass

    def refresh(self, rs, step: int) -> None:
        sim = self._api.sim_state
        gen_id = max(1, self._tp_s4_bg.checkedId())
        in_mode = self._api.pt_exam_states[1].started and self._api.pt_exam_states[2].started
        for lbl, (text, done) in zip(self.tp_s4_step_lbls, self._api.get_pt_exam_steps(gen_id)):
            set_step_list_label(lbl, text, done, in_mode)
        for gid, entry_map in self._tp_s4_fap.items():
            gen = sim.gen1 if gid == 1 else sim.gen2
            for attr, (sl, entry) in entry_map.items():
                scale = 10 if attr in ("freq", "phase_deg") else 1
                sl.blockSignals(True)
                sl.setValue(int(getattr(gen, attr) * scale))
                sl.blockSignals(False)
                if not entry.hasFocus():
                    entry.setText(f"{getattr(gen, attr):.1f}")
        state = self._api.pt_exam_states[gen_id]
        set_feedback_label(self.tp_s4_fb_lbl, state.feedback, state.feedback_color)
