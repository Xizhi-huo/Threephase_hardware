"""
ui/test_panel.py
合闸前测试模式协调器组件
"""

from typing import Callable, Optional, Protocol

from PyQt5 import QtCore, QtWidgets

from domain.assessment import AssessmentEventType
from ui.tabs._step_style import apply_badge_tone as _apply_badge_tone, set_props as _set_props
from ui.widgets.step_panels import LoopTestPanel, PtExamPanel, PtPhaseCheckPanel, PtVoltageCheckPanel, SyncTestPanel
from ui.widgets.step_panels._dialogs import (
    show_assessment_result_dialog,
    show_blackbox_dialog,
    show_blackbox_required_dialog,
    show_load_share_cabinet_dialog,
    show_random_fault_identification_dialog,
)
from ui.widgets.load_share_cabinet_widget import LoadShareCabinetState
from ui.widgets.step_panels._panel_builders import (
    build_test_panel_bottom_bar,
    build_test_panel_scroll_skeleton,
    build_test_panel_status_area,
    build_test_panel_step_dots,
    build_test_panel_title_bar,
    dispatch_step_action,
    refresh_tp_bottom,
    refresh_tp_gen_refs,
    tp_dot_style,
)


class TestPanelAPI(Protocol):
    __test__ = False

    @property
    def sim_state(self) -> object: ...
    @property
    def loop_test_state(self) -> object: ...
    @property
    def pt_voltage_check_state(self) -> object: ...
    @property
    def pt_phase_check_state(self) -> object: ...
    @property
    def pt_exam_states(self) -> object: ...
    @property
    def sync_test_state(self) -> object: ...
    @property
    def physics(self) -> object: ...
    @property
    def test_flow_mode(self) -> str: ...
    @test_flow_mode.setter
    def test_flow_mode(self, value: str) -> None: ...
    def capture_test_entry_state(self) -> None: ...
    def restore_test_entry_state(self) -> None: ...
    def reset_for_scenario(self, scenario_id: str) -> None: ...
    def inject_fault(self, fault_id: str) -> None: ...
    def enter_loop_test_mode(self) -> None: ...
    def exit_loop_test_mode(self) -> None: ...
    def start_pt_voltage_check(self) -> None: ...
    def stop_pt_voltage_check(self) -> None: ...
    def start_pt_phase_check(self) -> None: ...
    def stop_pt_phase_check(self) -> None: ...
    def start_pt_exam(self, gen_id: int) -> None: ...
    def stop_pt_exam(self, gen_id: int) -> None: ...
    def start_sync_test(self) -> None: ...
    def stop_sync_test(self) -> None: ...
    def reset_loop_test(self) -> None: ...
    def reset_pt_voltage_check(self) -> None: ...
    def reset_pt_phase_check(self) -> None: ...
    def reset_pt_exam(self, gen_id: int) -> None: ...
    def reset_sync_test(self) -> None: ...
    def finalize_loop_test(self) -> None: ...
    def finalize_pt_voltage_check(self) -> None: ...
    def finalize_pt_phase_check(self) -> None: ...
    def finalize_all_pt_exams(self) -> None: ...
    def finalize_sync_test(self) -> None: ...
    def record_loop_measurement(self, pair: str) -> None: ...
    def record_pt_voltage_measurement(self, pt_name: str, pair: str) -> None: ...
    def record_current_pt_measurement(self, gen_id: int) -> None: ...
    def record_all_pt_measurements_quick(self) -> None: ...
    def record_sync_round(self, round_no: int) -> None: ...
    def update_pt_ratio(self, attr: str, ratio: float) -> None: ...
    def get_loop_test_steps(self) -> list: ...
    def get_pt_voltage_check_steps(self) -> list: ...
    def get_pt_phase_check_steps(self) -> list: ...
    def get_pt_exam_steps(self, gen_id: int) -> list: ...
    def get_sync_test_steps(self) -> list: ...
    def is_loop_test_complete(self) -> bool: ...
    def is_pt_voltage_check_complete(self) -> bool: ...
    def is_pt_phase_check_complete(self) -> bool: ...
    def is_sync_test_complete(self) -> bool: ...
    def allow_admin_shortcuts(self) -> bool: ...
    def can_use_pt_exam_quick_record(self) -> bool: ...
    def should_show_fault_detected_banner(self) -> bool: ...
    def can_advance_with_fault(self) -> bool: ...
    def should_hold_at_step4_when_wiring_fault_unrepaired(self) -> bool: ...
    def has_unrepaired_wiring_fault(self) -> bool: ...
    def is_assessment_mode(self) -> bool: ...
    def start_assessment_session(self, scenario_id: str, *, preset_mode: str) -> None: ...
    def append_assessment_event(self, event_type, **kwargs) -> None: ...
    def get_test_progress_snapshot(self, step: int, pre_step5_repair_triggered: bool) -> object: ...
    def finish_assessment_session_if_ready(self, step: int) -> object: ...
    def mark_assessment_result_shown(self) -> None: ...
    def submit_random_fault_identification(self, scene_id: str) -> None: ...
    def can_inspect_blackbox(self) -> bool: ...
    def can_repair_in_blackbox(self) -> bool: ...
    def get_blackbox_runtime_state(self, target: str) -> object: ...
    def apply_blackbox_repair_attempt(self, **kwargs) -> object: ...
    def toggle_engine(self, gen_id: int) -> None: ...
    def toggle_breaker(self, gen_id: int) -> None: ...
    def record_phase_sequence(self, pt_name: str, seq: str) -> bool: ...


class TestPanelWidget(QtWidgets.QWidget):
    __test__ = False

    def __init__(
        self,
        api: TestPanelAPI,
        *,
        on_show_test_panel: Callable[[bool], None],
        on_set_current_tab: Callable[[int], None],
        on_set_step_tabs_visible: Callable[[bool], None],
        on_toggle_multimeter: Callable[[], None],
        on_force_multimeter_off: Callable[[], None],
        on_connect_phase_seq_meter: Callable[[str], None],
        on_disconnect_phase_seq_meter: Callable[[], None],
        on_restore_runtime_ui: Callable[[], None],
        get_phase_seq_meter_sequence: Callable[[], str],
        get_phase_wiring_status: Callable[[], str],
        get_phase_wiring_active_pt: Callable[[], str | None],
        
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._api = api
        self._host_show_test_panel: Callable[[bool], None] = on_show_test_panel
        self._host_set_current_tab: Callable[[int], None] = on_set_current_tab
        self._host_set_step_tabs_visible: Callable[[bool], None] = on_set_step_tabs_visible
        self._host_toggle_multimeter: Callable[[], None] = on_toggle_multimeter
        self._host_force_multimeter_off: Callable[[], None] = on_force_multimeter_off
        self._host_connect_phase_seq_meter: Callable[[str], None] = on_connect_phase_seq_meter
        self._host_disconnect_phase_seq_meter: Callable[[], None] = on_disconnect_phase_seq_meter
        self._host_restore_runtime_ui: Callable[[], None] = on_restore_runtime_ui
        self._host_get_phase_seq_meter_sequence: Callable[[], str] = get_phase_seq_meter_sequence
        self._host_get_phase_wiring_status: Callable[[], str] = get_phase_wiring_status
        self._host_get_phase_wiring_active_pt: Callable[[], str | None] = get_phase_wiring_active_pt
        self.test_panel = self
        self._pre_test_scenario_id: str = ""
        self._pre_test_flow_mode: str = "teaching"
        self._pre_test_preset_mode: str = "normal"
        self._load_share_cabinet_state = LoadShareCabinetState()
        self._setup_test_panel()


    def set_pretest_config(self, scenario_id: str, flow_mode: str, preset_mode: str) -> None:
        self._pre_test_scenario_id = scenario_id
        self._pre_test_flow_mode = flow_mode
        self._pre_test_preset_mode = preset_mode

    def is_test_mode_active(self) -> bool:
        return getattr(self, "_test_mode_active", False)

    def _setup_test_panel(self):
        self._test_mode_active = False
        self._tp_admin_mode = False
        self._tp_forced_step = None
        self._tp_gen_refs = {}
        self._tp_last_step = None
        self.setFixedWidth(520)
        _set_props(self, testPanelRoot=True, panelSurface=True)
        self.setVisible(False)
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        top, self.tp_btn_reset, self.tp_btn_admin = build_test_panel_title_bar(
            self,
            on_reset=self._on_tp_reset_step,
            on_toggle_admin=self._on_tp_toggle_admin,
            on_exit=self.exit_test_mode,
        )
        root.addWidget(top)

        step_bar, self.tp_step_btns = build_test_panel_step_dots(self, on_step_clicked=self._on_tp_step_btn_clicked)
        root.addWidget(step_bar)

        scroll, scroll_content, content_layout = build_test_panel_scroll_skeleton()
        status = build_test_panel_status_area(self, content_layout, on_toggle_multimeter=self._on_toggle_multimeter)
        self._tp_fault_banner = status["fault_banner"]
        self.tp_bus_lbl = status["bus_lbl"]
        self._tp_mm_btn = status["mm_btn"]
        self.tp_meter_lbl = status["meter_lbl"]

        self._tp_step_panels = {
            1: LoopTestPanel(
                self._api,
                get_current_test_step=self._current_test_step,
                is_step_complete=self._is_step_complete,
                on_toggle_multimeter=self._on_toggle_multimeter,
                show_blackbox_dialog=self._show_blackbox_dialog,
                show_load_share_cabinet_dialog=self._show_load_share_cabinet_dialog,
                parent=scroll_content,
            ),
            2: PtVoltageCheckPanel(
                self._api,
                get_current_test_step=self._current_test_step,
                is_step_complete=self._is_step_complete,
                on_toggle_multimeter=self._on_toggle_multimeter,
                show_blackbox_dialog=self._show_blackbox_dialog,
                show_load_share_cabinet_dialog=self._show_load_share_cabinet_dialog,
                parent=scroll_content,
            ),
            3: PtPhaseCheckPanel(
                self._api,
                get_current_test_step=self._current_test_step,
                is_step_complete=self._is_step_complete,
                on_connect_phase_seq_meter=self._on_connect_phase_seq_meter,
                on_disconnect_phase_seq_meter=self._on_disconnect_phase_seq_meter,
                get_phase_seq_meter_sequence=self._get_phase_seq_meter_sequence,
                get_phase_wiring_status=self._get_phase_wiring_status,
                get_phase_wiring_active_pt=self._get_phase_wiring_active_pt,
                on_force_multimeter_off=self._on_force_multimeter_off,
                show_blackbox_dialog=self._show_blackbox_dialog,
                show_load_share_cabinet_dialog=self._show_load_share_cabinet_dialog,
                parent=scroll_content,
            ),
            4: PtExamPanel(
                self._api,
                get_current_test_step=self._current_test_step,
                is_step_complete=self._is_step_complete,
                on_toggle_multimeter=self._on_toggle_multimeter,
                show_blackbox_dialog=self._show_blackbox_dialog,
                show_load_share_cabinet_dialog=self._show_load_share_cabinet_dialog,
                parent=scroll_content,
            ),
            5: SyncTestPanel(
                self._api,
                get_current_test_step=self._current_test_step,
                is_step_complete=self._is_step_complete,
                show_load_share_cabinet_dialog=self._show_load_share_cabinet_dialog,
                parent=scroll_content,
            ),
        }
        self._tp_step_grps = self._tp_step_panels
        for panel in self._tp_step_panels.values():
            self._tp_gen_refs.update(panel.gen_refs)
            content_layout.addWidget(panel)
        self._tp_s2_ratio_rows = self._tp_step_panels[2]._tp_s2_ratio_rows
        self._tp_s4_bg = self._tp_step_panels[4]._tp_s4_bg
        self._tp_s4_quick_btn = self._tp_step_panels[4]._tp_s4_quick_btn
        content_layout.addStretch()
        scroll.setWidget(scroll_content)
        root.addWidget(scroll, 1)

        bottom, self.tp_btn_start, self.tp_btn_complete = build_test_panel_bottom_bar(
            self,
            on_start=self._on_tp_start_step,
            on_complete=self._on_tp_complete_step,
        )
        root.addWidget(bottom)

    def enter_test_mode(self):
        self._api.capture_test_entry_state()
        scenario_id = getattr(self, "_pre_test_scenario_id", "")
        self._api.test_flow_mode = getattr(self, "_pre_test_flow_mode", "teaching")
        self._load_share_cabinet_state.reset_defaults()
        self._api.reset_for_scenario(scenario_id)
        self._test_mode_active = True
        self._assessment_last_logged_step = None
        self._pre_step5_repair_triggered = False
        self._tp_last_step = None
        for panel in self._tp_step_panels.values():
            panel.reset()
        self._host_show_test_panel(True)
        self.setVisible(True)
        self.tp_btn_admin.setVisible(self._api.allow_admin_shortcuts())
        self._tp_s4_quick_btn.setVisible(self._api.can_use_pt_exam_quick_record())
        if not self._api.allow_admin_shortcuts():
            self._tp_admin_mode = False
            self.tp_btn_admin.setChecked(False)
            self._tp_forced_step = None
        self._api.start_assessment_session(scenario_id, preset_mode=getattr(self, "_pre_test_preset_mode", "specified"))
        self._host_set_current_tab(1)
        if not self._api.sim_state.loop_test_mode:
            self._api.enter_loop_test_mode()

    def exit_test_mode(self):
        self._host_disconnect_phase_seq_meter()
        self._api.restore_test_entry_state()
        self._test_mode_active = False
        self._tp_last_step = None
        self._tp_admin_mode = False
        self._tp_forced_step = None
        self._pre_step5_repair_triggered = False
        self._assessment_last_logged_step = None
        for panel in self._tp_step_panels.values():
            panel.reset()
        self.setVisible(False)
        self._host_show_test_panel(False)
        self._host_set_step_tabs_visible(False)
        self._host_restore_runtime_ui()

    def _on_tp_reset_step(self):
        step = self._current_test_step()
        dispatch_step_action(self._api, step, "reset", gen_id=max(1, self._tp_s4_bg.checkedId()))
        self._tp_step_panels[step].reset()

    def _on_tp_start_step(self):
        dispatch_step_action(self._api, self._current_test_step(), "start")

    def _on_tp_complete_step(self):
        step = self._current_test_step()
        before_complete = self._is_step_complete(step)
        dispatch_step_action(self._api, step, "complete")
        if step == 2:
            self._on_force_multimeter_off()
        elif step == 3 and self._api.pt_phase_check_state.completed:
            self._tp_step_panels[3].reset()
        after_complete = self._is_step_complete(step)
        self._api.append_assessment_event(
            AssessmentEventType.STEP_FINALIZE_ATTEMPTED,
            step=step,
            allowed=after_complete,
            mode=self._api.test_flow_mode,
        )
        if after_complete and not before_complete:
            self._api.append_assessment_event(AssessmentEventType.STEP_COMPLETED, step=step)
        elif not after_complete:
            self._api.append_assessment_event(
                AssessmentEventType.ADVANCE_BLOCKED,
                step=step,
                from_step=step,
                to_step=min(step + 1, 5),
                reason="step_finalize_rejected",
            )

    def _on_tp_toggle_admin(self, checked):
        if checked and not self._api.allow_admin_shortcuts():
            self.tp_btn_admin.setChecked(False)
            return
        self._tp_admin_mode = checked
        self.tp_btn_admin.setText("🔧 管理员 ✓" if checked else "🔧 管理员")
        if checked:
            for btn in self.tp_step_btns:
                btn.setCursor(QtCore.Qt.PointingHandCursor)
        else:
            self._tp_forced_step = None
            for btn in self.tp_step_btns:
                btn.setChecked(False)
                btn.setCursor(QtCore.Qt.ArrowCursor)
        self._host_set_step_tabs_visible(checked)
        self._tp_s4_quick_btn.setVisible(checked or self._api.is_assessment_mode())

    def _update_fault_banner(self):
        fc = self._api.sim_state.fault_config
        if not self._api.should_show_fault_detected_banner():
            self._tp_fault_banner.setVisible(False)
            return
        if not (fc.active and fc.scenario_id):
            self._tp_fault_banner.setVisible(False)
            return
        if fc.repaired:
            text, tone = "✅ 故障已修复，请继续按正常流程完成剩余步骤", "success"
        elif fc.detected:
            text = (
                "🔍 已发现异常证据 | 请继续完成所有测试步骤，记录全部数据后将在第五步前统一进行检修"
                if self._api.can_advance_with_fault()
                else "🔍 已发现异常证据 | 当前流程模式要求先排除故障并复测合格，再继续后续步骤"
            )
            tone = "warning"
        else:
            text = "⚠ 故障训练模式已启用 | 请按正常流程测试，通过测量数据发现并定位异常"
            tone = "danger"
        _set_props(self._tp_fault_banner, stepBanner=True, tone=tone)
        self._tp_fault_banner.setText(text)
        self._tp_fault_banner.setVisible(True)

    def _on_tp_step_btn_clicked(self, step_num: int):
        if not self._tp_admin_mode:
            return
        self._tp_forced_step = None if self._tp_forced_step == step_num else step_num
        for i, btn in enumerate(self.tp_step_btns, start=1):
            btn.setChecked(self._tp_forced_step == i)

    def _auto_test_step(self) -> int:
        if not self._api.is_loop_test_complete():
            return 1
        if not self._api.is_pt_voltage_check_complete():
            return 2
        if not self._api.is_pt_phase_check_complete():
            return 3
        if self._api.should_hold_at_step4_when_wiring_fault_unrepaired() and self._api.has_unrepaired_wiring_fault():
            return 4
        if not (self._api.pt_exam_states[1].completed and self._api.pt_exam_states[2].completed):
            return 4
        return 5

    def _current_test_step(self) -> int:
        return self._tp_forced_step if self._tp_admin_mode and self._tp_forced_step is not None else self._auto_test_step()

    def _is_step_complete(self, step: int) -> bool:
        return {
            1: self._api.is_loop_test_complete(),
            2: self._api.is_pt_voltage_check_complete(),
            3: self._api.is_pt_phase_check_complete(),
            4: self._api.pt_exam_states[1].completed and self._api.pt_exam_states[2].completed,
            5: self._api.is_sync_test_complete(),
        }.get(step, False)

    def _on_toggle_multimeter(self):
        self._host_toggle_multimeter()

    def _on_force_multimeter_off(self):
        self._host_force_multimeter_off()

    def _on_connect_phase_seq_meter(self, pt_name: str):
        self._host_connect_phase_seq_meter(pt_name)
        self._host_set_current_tab(1)

    def _on_disconnect_phase_seq_meter(self):
        self._host_disconnect_phase_seq_meter()

    def _get_phase_seq_meter_sequence(self):
        return self._host_get_phase_seq_meter_sequence()
    
    def _get_phase_wiring_status(self) -> str:
        return self._host_get_phase_wiring_status()
    
    def _get_phase_wiring_active_pt(self) -> str | None:
        return self._host_get_phase_wiring_active_pt()

    def _show_assessment_result_dialog(self, result):
        show_assessment_result_dialog(self, result)

    def _show_random_fault_identification_dialog(self):
        show_random_fault_identification_dialog(self, submit_guess=self._api.submit_random_fault_identification)

    def _show_blackbox_required_dialog(self, fc):
        show_blackbox_required_dialog(self, is_assessment=self._api.is_assessment_mode(), scene_id=fc.scenario_id)

    def _show_blackbox_dialog(self, target):
        if not self._api.can_inspect_blackbox():
            return
        self._api.append_assessment_event(AssessmentEventType.BLACKBOX_OPENED, step=self._current_test_step(), target=target)
        show_blackbox_dialog(self, api=self._api, step=self._current_test_step(), target=target)

    def _show_load_share_cabinet_dialog(self) -> None:
        show_load_share_cabinet_dialog(self, self._load_share_cabinet_state)

    def render(self, rs):
        self._render_test_panel(rs)

    def _render_test_panel(self, rs):
        if not self._test_mode_active:
            return
        sim = self._api.sim_state
        step = self._current_test_step()
        self.tp_btn_admin.setVisible(self._api.allow_admin_shortcuts())
        self._tp_s4_quick_btn.setVisible(self._api.can_use_pt_exam_quick_record())
        if self._assessment_last_logged_step != step:
            self._api.append_assessment_event(AssessmentEventType.STEP_ENTERED, step=step)
            self._assessment_last_logged_step = step
        if not self._api.allow_admin_shortcuts():
            self._tp_admin_mode = False
            self.tp_btn_admin.setChecked(False)
            self._tp_forced_step = None
        auto_step = self._auto_test_step()
        for s, btn in enumerate(self.tp_step_btns, start=1):
            style = "admin_active" if self._tp_admin_mode and s == step else "admin_idle" if self._tp_admin_mode else "done" if s < auto_step else "active" if s == auto_step else "idle"
            btn.setStyleSheet(tp_dot_style(style))
        for s, grp in self._tp_step_grps.items():
            grp.setVisible(s == step)
        if self._tp_last_step != step:
            self._tp_step_panels[step].on_enter()
            self._tp_last_step = step

        self.tp_bus_lbl.setText(getattr(self._api.physics, "bus_status_msg", "母排: --"))
        _apply_badge_tone(self.tp_bus_lbl, "success" if getattr(self._api.physics, "bus_live", False) else "warning")
        self._update_fault_banner()

        fc = sim.fault_config
        progress = self._api.get_test_progress_snapshot(step, getattr(self, "_pre_step5_repair_triggered", False))
        if progress.block_before_step5 and not getattr(self, "_pre_step5_repair_triggered", False):
            self._pre_step5_repair_triggered = True
            if progress.should_emit_assessment_gate_event:
                self._api.append_assessment_event(
                    AssessmentEventType.ASSESSMENT_GATE_BLOCKED,
                    step=4,
                    scene_id=fc.scenario_id,
                    reason="unrepaired_wiring_before_step5",
                )
            if progress.should_show_blackbox_required_dialog:
                self._show_blackbox_required_dialog(fc)
        elif not self._api.has_unrepaired_wiring_fault():
            self._pre_step5_repair_triggered = False

        mm_visible = step != 3
        self._tp_mm_btn.setVisible(mm_visible)
        self.tp_meter_lbl.setVisible(mm_visible)
        if sim.multimeter_mode:
            self.tp_meter_lbl.setText(f"万用表: {getattr(self._api.physics, 'meter_reading', '--')}")
            _set_props(self.tp_meter_lbl, stepStatus=True, mutedText=False)
        else:
            self.tp_meter_lbl.setText("万用表: 关闭")
            _set_props(self.tp_meter_lbl, stepStatus=True, mutedText=True)

        refresh_tp_gen_refs(self, self._tp_gen_refs, sim, step)
        refresh_tp_bottom(self, self._api, self.tp_btn_start, self.tp_btn_complete, step, sim)
        self._tp_step_panels[step].refresh(rs, step)

        if progress.random_fault_guess_required:
            self._show_random_fault_identification_dialog()
        result = self._api.finish_assessment_session_if_ready(step)
        if result is not None:
            self._show_assessment_result_dialog(result)
            self._api.mark_assessment_result_shown()
