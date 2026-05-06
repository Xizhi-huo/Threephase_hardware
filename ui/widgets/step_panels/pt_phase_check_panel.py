from typing import Callable, Optional, TYPE_CHECKING

from PyQt5 import QtCore, QtWidgets

from ui.tabs.circuit_tab import PhaseWiringStatus
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


class PtPhaseCheckPanel(QtWidgets.QGroupBox):
    def __init__(
        self,
        api: "TestPanelAPI",
        *,
        get_current_test_step: Callable[[], int],
        is_step_complete: Callable[[int], bool],
        on_connect_phase_seq_meter: Optional[Callable[[str], None]] = None,
        on_disconnect_phase_seq_meter: Optional[Callable[[], None]] = None,
        get_phase_seq_meter_sequence: Optional[Callable[[], str]] = None,
        get_phase_wiring_status: Optional[Callable[[], PhaseWiringStatus]] = None,
        get_phase_wiring_active_pt: Optional[Callable[[], str | None]] = None,
        on_force_multimeter_off: Optional[Callable[[], None]] = None,
        show_load_share_cabinet_dialog: Optional[Callable[[], None]] = None,
        show_blackbox_dialog: Optional[Callable[[str], None]] = None,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__("第三步：PT 相序检查", parent)
        self._api = api
        self._get_current_test_step = get_current_test_step
        self._is_step_complete = is_step_complete
        self._on_connect_phase_seq_meter: Optional[Callable[[str], None]] = on_connect_phase_seq_meter
        self._on_disconnect_phase_seq_meter: Optional[Callable[[], None]] = on_disconnect_phase_seq_meter
        self._get_phase_seq_meter_sequence: Optional[Callable[[], str]] = get_phase_seq_meter_sequence
        self._get_phase_wiring_status: Optional[Callable[[], PhaseWiringStatus]] = get_phase_wiring_status
        self._get_phase_wiring_active_pt: Optional[Callable[[], str | None]] = get_phase_wiring_active_pt
        self._on_force_multimeter_off: Optional[Callable[[], None]] = on_force_multimeter_off
        self._show_load_share_cabinet_dialog: Optional[Callable[[], None]] = show_load_share_cabinet_dialog
        self._show_blackbox_dialog: Optional[Callable[[str], None]] = show_blackbox_dialog
        self.gen_refs: dict[str, object] = {}
        self._tp_s3_rec_btns: dict[str, QtWidgets.QPushButton] = {}
        self._build()

    def _build(self):
        lay = QtWidgets.QVBoxLayout(self)
        lay.setSpacing(4)
        self.tp_s3_step_lbls = make_step_list(lay, 7)
        lay.addWidget(make_note_label("Gen2 需起机，断路器保持断开", "warning", italic=True))
        make_gen_block(lay, owner=self, api=self._api, gen_refs=self.gen_refs, step_key="s3", gen_id=2)

        lay.addWidget(make_note_label("相序仪（在母排图右侧查看转盘与指示灯）:"))
        psm_row = make_inline_row()
        psm_h = QtWidgets.QHBoxLayout(psm_row)
        psm_h.setContentsMargins(0, 0, 0, 0)
        psm_h.setSpacing(6)
        for pt_name, bg in [("PT1", "#1d4ed8"), ("PT3", "#7c3aed")]:
            btn = make_button(self, f"📡 接入 {pt_name}", bg)
            btn.clicked.connect(lambda _, pt=pt_name: self._on_connect_psm(pt))
            psm_h.addWidget(btn)
        btn_disc = make_button(self, "断开", "#64748b")
        btn_disc.clicked.connect(self._on_disconnect_psm)
        psm_h.addWidget(btn_disc)
        lay.addWidget(psm_row)

        lay.addWidget(make_note_label("记录相序结果:"))
        rec_row = make_inline_row()
        rec_h = QtWidgets.QHBoxLayout(rec_row)
        rec_h.setContentsMargins(0, 0, 0, 0)
        rec_h.setSpacing(6)
        self._tp_s3_rec_btns = {}
        for pt_name, bg in [("PT1", "#1d4ed8"), ("PT3", "#7c3aed")]:
            btn = make_button(self, f"记录 {pt_name}", bg)
            btn.setEnabled(False)
            btn.clicked.connect(lambda _, pt=pt_name: self._on_record_psm(pt))
            rec_h.addWidget(btn)
            self._tp_s3_rec_btns[pt_name] = btn
        lay.addWidget(rec_row)

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

        self.tp_s3_fb_lbl = make_feedback_label("请先接入相序仪查看结果，再点击记录")
        set_props(self.tp_s3_fb_lbl, feedbackText=True, tone="neutral")
        lay.addWidget(self.tp_s3_fb_lbl)

    def _phase_wiring_status(self) -> PhaseWiringStatus:
        return self._get_phase_wiring_status() if self._get_phase_wiring_status else PhaseWiringStatus.IDLE
    
    def _phase_wiring_active_pt(self) -> str | None:
        return self._get_phase_wiring_active_pt() if self._get_phase_wiring_active_pt else None

    def _refresh_record_buttons(self) -> None:
        status = self._phase_wiring_status()
        active_pt = self._phase_wiring_active_pt()
        for pt_name, btn in self._tp_s3_rec_btns.items():
            btn.setEnabled(
                status == PhaseWiringStatus.READY
                and active_pt == pt_name
            )

    def on_enter(self) -> None:
        if self._on_force_multimeter_off is not None:
            self._on_force_multimeter_off()

    def reset(self) -> None:
        self._on_disconnect_psm()

    def _on_connect_psm(self, pt_name: str):
        if self._on_connect_phase_seq_meter is not None:
            self._on_connect_phase_seq_meter(pt_name)
        self._refresh_record_buttons()
        set_feedback_label(
            self.tp_s3_fb_lbl,
            f"相序仪已切换到{pt_name}, 请在母排拓扑页点击{pt_name}_A / {pt_name}_B / {pt_name}_C 完成三点接线。",
            "orange",
        )

    def _on_disconnect_psm(self):
        if self._on_disconnect_phase_seq_meter is not None:
            self._on_disconnect_phase_seq_meter()
        self._refresh_record_buttons()
        set_feedback_label(self.tp_s3_fb_lbl, "相序仪已断开,可重新接入。", "#64748b")

    def _on_record_psm(self, pt_name: str):
        if self._phase_wiring_status() != PhaseWiringStatus.READY or self._phase_wiring_active_pt() != pt_name:
            set_feedback_label(self.tp_s3_fb_lbl, "请先完成当前 PT 的三点接线，再记录结果。", "orange")
            return

        seq = self._get_phase_seq_meter_sequence() if self._get_phase_seq_meter_sequence else "unknown"
        if seq == "unknown":
            set_feedback_label(self.tp_s3_fb_lbl, "相序仪结果尚未就绪, 请先完成接线。", "orange")
            return

        ok = self._api.record_phase_sequence(pt_name, seq)
        state = self._api.pt_phase_check_state
        set_feedback_label(self.tp_s3_fb_lbl, state.feedback, state.feedback_color)

    def refresh(self, rs, step: int) -> None:
        in_mode = self._api.pt_phase_check_state.started
        for lbl, (text, done) in zip(self.tp_s3_step_lbls, self._api.get_pt_phase_check_steps()):
            set_step_list_label(lbl, text, done, in_mode)

        self._refresh_record_buttons()

        status = self._phase_wiring_status()
        active_pt = self._phase_wiring_active_pt()
        state = self._api.pt_phase_check_state

        if status == PhaseWiringStatus.WIRING and active_pt:
            set_feedback_label(
                self.tp_s3_fb_lbl,
                f"{active_pt} 正在接线中，请在母排拓扑页完成 {active_pt}_A / {active_pt}_B / {active_pt}_C 三点连接。",
                "orange",
            )
            return

        elif status == PhaseWiringStatus.READY and active_pt:
            set_feedback_label(
                self.tp_s3_fb_lbl,
                f"{active_pt} 三点接线已完成，请查看相序仪结果后点击“记录 {active_pt}”。",
                "#2563eb",
            )
            return

        set_feedback_label(self.tp_s3_fb_lbl, state.feedback, state.feedback_color)
