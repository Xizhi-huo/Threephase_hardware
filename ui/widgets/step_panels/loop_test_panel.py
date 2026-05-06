from typing import Callable, Optional, TYPE_CHECKING

from PyQt5 import QtCore, QtWidgets

from domain.test_states import LOOP_TEST_RECORD_KEYS
from ui.widgets.manual_entry import LoopManualEntryWidget
from ui.widgets.step_panels._panel_builders import (
    add_blackbox_section,
    add_load_share_cabinet_section,
    make_button,
    make_feedback_label,
    make_gen_block,
    make_inline_row,
    make_note_label,
    make_step_list,
    set_feedback_label,
    set_props,
    set_step_list_label,
)

if TYPE_CHECKING:
    from ui.test_panel import TestPanelAPI


class LoopTestPanel(QtWidgets.QGroupBox):
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
        super().__init__("第一步：回路连通性测试", parent)
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
        self.tp_s1_step_lbls = make_step_list(lay, 7)

        lay.addWidget(make_note_label("中性点接地:"))
        gnd_row = make_inline_row()
        gnd_h = QtWidgets.QHBoxLayout(gnd_row)
        gnd_h.setContentsMargins(0, 0, 0, 0)
        self._tp_gnd_bg = QtWidgets.QButtonGroup(self)
        self._tp_gnd_rbs = {}
        for label, val in [("断开", "断开"), ("小电阻", "小电阻接地"), ("直接", "直接接地")]:
            rb = QtWidgets.QRadioButton(label)
            set_props(rb, inlineRadio=True)
            rb.setChecked(self._api.sim_state.grounding_mode == val)
            rb.toggled.connect(
                lambda chk, v=val: setattr(self._api.sim_state, "grounding_mode", v) if chk else None
            )
            self._tp_gnd_bg.addButton(rb)
            gnd_h.addWidget(rb)
            self._tp_gnd_rbs[val] = rb
        lay.addWidget(gnd_row)

        lay.addWidget(make_note_label("⚠ 回路检查期间勿起机，仅合闸即可", "warning", italic=True))
        make_gen_block(
            lay,
            owner=self,
            api=self._api,
            gen_refs=self.gen_refs,
            step_key="s1",
            gen_id=1,
            mode_options=[("停机", "stop"), ("手动", "manual")],
            show_pos=True,
            show_engine=False,
        )
        make_gen_block(
            lay,
            owner=self,
            api=self._api,
            gen_refs=self.gen_refs,
            step_key="s1",
            gen_id=2,
            mode_options=[("停机", "stop"), ("手动", "manual")],
            show_pos=True,
            show_engine=False,
        )

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

        self.tp_s1_rec_btns = {}
        quick_note = make_note_label("回路测试快速记录（需先开启万用表）:")
        lay.addWidget(quick_note)
        self._simulated_entry_widgets.append(quick_note)
        for pairs in (LOOP_TEST_RECORD_KEYS[:3], LOOP_TEST_RECORD_KEYS[3:]):
            rrow = make_inline_row()
            rh = QtWidgets.QHBoxLayout(rrow)
            rh.setContentsMargins(0, 0, 0, 0)
            rh.setSpacing(4)
            for pair in pairs:
                btn = make_button(self, pair, "#1d4ed8")
                btn.clicked.connect(lambda _, p=pair: self._api.record_loop_measurement(p))
                rh.addWidget(btn)
                self.tp_s1_rec_btns[pair] = btn
            lay.addWidget(rrow)
            self._simulated_entry_widgets.append(rrow)

        self.manual_widget = LoopManualEntryWidget(self)
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

        self.tp_s1_fb_lbl = make_feedback_label("请按步骤列表操作")
        lay.addWidget(self.tp_s1_fb_lbl)

    def _set_manual_mode(self, manual: bool) -> None:
        self._manual_mode = manual
        for widget in self._simulated_entry_widgets:
            widget.setVisible(not manual)
        self.manual_widget.setVisible(manual)

    def _on_manual_submitted(self, kwargs: dict) -> None:
        try:
            self._api.record_loop_measurement(**kwargs)
        except ValueError as exc:
            self.manual_widget._show_input_error(str(exc))
            return
        state = self._api.loop_test_state
        set_feedback_label(self.tp_s1_fb_lbl, state.feedback, state.feedback_color)

    def on_enter(self) -> None:
        pass

    def reset(self) -> None:
        pass

    def refresh(self, rs, step: int) -> None:
        sim = self._api.sim_state
        in_mode = sim.loop_test_mode
        for lbl, (text, done) in zip(self.tp_s1_step_lbls, self._api.get_loop_test_steps()):
            set_step_list_label(lbl, text, done, in_mode)
        for val, rb in self._tp_gnd_rbs.items():
            rb.blockSignals(True)
            rb.setChecked(sim.grounding_mode == val)
            rb.blockSignals(False)
        active = in_mode and sim.multimeter_mode
        for btn in self.tp_s1_rec_btns.values():
            btn.setEnabled(active and not self._manual_mode)
        state = self._api.loop_test_state
        set_feedback_label(self.tp_s1_fb_lbl, state.feedback, state.feedback_color)
