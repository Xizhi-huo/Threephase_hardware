"""右侧控制面板装配入口。"""

import random as _random

from PyQt5 import QtCore, QtWidgets

from domain.fault_scenarios import SCENARIOS
from domain.node_map import NODES
from ui.tabs.circuit_tab import PhaseWiringStatus
from ui.widgets.control_panel import GeneratorCard, ParamControlsPage, RunControlsPage
from ui.widgets.control_panel._widget_tokens import (
    apply_badge_tone,
    apply_button_tone,
    apply_toggle_tone,
    refresh_widget_styles,
    set_props,
)


class WidgetBuilderMixin:
    """为 PowerSyncUI 提供控制面板装配与宿主联动。"""

    @staticmethod
    def _refresh_widget_styles(*widgets):
        refresh_widget_styles(*widgets)

    @staticmethod
    def _set_props(widget, **props):
        set_props(widget, **props)

    def _apply_button_tone(self, button, tone="primary", *, hero=False, secondary=False, muted=False):
        apply_button_tone(button, tone, hero=hero, secondary=secondary, muted=muted)

    def _apply_badge_tone(self, widget, tone="neutral"):
        apply_badge_tone(widget, tone)

    def _apply_toggle_tone(self, widget, tone="primary"):
        apply_toggle_tone(widget, tone)

    def _sync_fault_preset_buttons(self, active_key: str):
        mapping = {
            "normal": self._fp_btn_normal,
            "random": self._fp_btn_random,
            "choose": self._fp_btn_choose,
        }
        for key, btn in mapping.items():
            btn.setChecked(key == active_key)
        self._refresh_widget_styles(*mapping.values())

    def _build_control_panel(self):
        ctrl = self.ctrl

        title = QtWidgets.QLabel("⚡ 并网仿真教学系统")
        self._set_props(title, sidebarTitle=True)
        title.setAlignment(QtCore.Qt.AlignCenter)
        self.ctrl_layout.addWidget(title)

        switcher_w = QtWidgets.QWidget()
        switcher_w.setObjectName("panelSwitcher")
        switcher_w.setProperty("toolbarStrip", True)
        sw_lay = QtWidgets.QHBoxLayout(switcher_w)
        sw_lay.setContentsMargins(0, 0, 0, 0)
        sw_lay.setSpacing(8)

        self._cp_btn_run = QtWidgets.QPushButton("▶ 运行控制")
        self._cp_btn_param = QtWidgets.QPushButton("⚙ 参数设置")
        for btn in (self._cp_btn_run, self._cp_btn_param):
            btn.setFixedHeight(36)
            self._set_props(btn, segment=True, segmentTone="primary")
            btn.setCheckable(True)
            sw_lay.addWidget(btn)
        self._cp_btn_run.setChecked(True)
        self.ctrl_layout.addWidget(switcher_w)

        self._cp_stack = QtWidgets.QStackedWidget()
        self.ctrl_layout.addWidget(self._cp_stack, 1)

        run_page = RunControlsPage(
            sim_state=ctrl.sim_state,
            on_fp_set=self._on_fp_set,
            on_fp_random=self._on_fp_random,
            on_fp_choose=self._on_fp_choose,
            on_enter_test_mode=self.enter_test_mode,
        )
        on_instant_sync = lambda: getattr(ctrl, "hw").instant_sync()
        param_page = ParamControlsPage(
            sim_state=ctrl.sim_state,
            on_toggle_pause=ctrl.toggle_pause,
            on_instant_sync=on_instant_sync,
        )
        gen1_card = GeneratorCard(
            sim_state=ctrl.sim_state,
            gen_id=1,
            on_toggle_engine=ctrl.toggle_engine,
            on_toggle_breaker=ctrl.toggle_breaker,
        )
        gen2_card = GeneratorCard(
            sim_state=ctrl.sim_state,
            gen_id=2,
            on_toggle_engine=ctrl.toggle_engine,
            on_toggle_breaker=ctrl.toggle_breaker,
        )
        run_page.add_generator_card(gen1_card)
        run_page.add_generator_card(gen2_card)
        self._cp_stack.addWidget(run_page)
        self._cp_stack.addWidget(param_page)

        def _switch(idx):
            self._cp_stack.setCurrentIndex(idx)
            self._cp_btn_run.setChecked(idx == 0)
            self._cp_btn_param.setChecked(idx == 1)

        self._cp_btn_run.clicked.connect(lambda: _switch(0))
        self._cp_btn_param.clicked.connect(lambda: _switch(1))

        self._run_controls_page = run_page
        self._param_controls_page = param_page
        self._gen1_card = gen1_card
        self._gen2_card = gen2_card

        self._mode_bg = run_page.mode_bg
        self._fp_btn_normal = run_page.fp_btn_normal
        self._fp_btn_random = run_page.fp_btn_random
        self._fp_btn_choose = run_page.fp_btn_choose
        self._fp_status_lbl = run_page.fp_status_lbl
        self.btn_enter_test_mode = run_page.btn_enter_test_mode
        self.bus_status_lbl = run_page.bus_status_lbl
        self.bus_reference_lbl = run_page.bus_reference_lbl
        self.arbitrator_lbl = run_page.arbitrator_lbl
        self._gnd_bg = run_page.gnd_bg
        self._gr_bg = run_page.gnd_bg
        self.remote_start_cb = run_page.remote_start_cb
        self.multimeter_cb = run_page.multimeter_cb
        self.show_gen_wires_cb = run_page.show_gen_wires_cb

        self.btn_engine1 = gen1_card.engine_btn
        self.btn_engine2 = gen2_card.engine_btn
        self.btn_breaker1 = gen1_card.breaker_btn
        self.btn_breaker2 = gen2_card.breaker_btn
        self.status1_lbl = gen1_card.status_lbl
        self.status2_lbl = gen2_card.status_lbl
        self._gen1_entry_map = gen1_card.entry_map
        self._gen2_entry_map = gen2_card.entry_map
        self._gen1_mode_bg = gen1_card.mode_bg
        self._gen2_mode_bg = gen2_card.mode_bg
        self._gen1_pos_bg = gen1_card.pos_bg
        self._gen2_pos_bg = gen2_card.pos_bg

        self.sim_speed_slider = param_page.sim_speed_slider
        self.sim_speed_label = param_page.sim_speed_label
        self.gov_gain_slider = param_page.gov_gain_slider
        self.gov_gain_label = param_page.gov_gain_label
        self.sync_gain_slider = param_page.sync_gain_slider
        self.sync_gain_label = param_page.sync_gain_label
        self.first_start_slider = param_page.first_start_slider
        self.first_start_label = param_page.first_start_label
        # self.droop_cb = param_page.droop_cb
        self.rotate_phasor_cb = param_page.rotate_phasor_cb
        self.relay_lbl = param_page.relay_lbl
        self.pause_btn = param_page.pause_btn

        self._pre_test_scenario_id = ""
        self._pre_test_flow_mode = "teaching"
        self._pre_test_preset_mode = "normal"
        self._sync_fault_preset_buttons("normal")
        self._refresh_pretest_status_label()

    def _on_fp_set(self, scenario_id: str):
        self._pre_test_scenario_id = scenario_id
        self._pre_test_preset_mode = "choose" if scenario_id else "normal"
        if not scenario_id:
            # 正常模式不走考核流程，回到默认教学模式，避免管理员入口残留隐藏。
            self._pre_test_flow_mode = "teaching"
        self._sync_fault_preset_buttons(self._pre_test_preset_mode)
        self._refresh_pretest_status_label()

    def _refresh_pretest_status_label(self):
        mode_text = self._flow_mode_label(self._pre_test_flow_mode)
        scenario_id = self._pre_test_scenario_id
        if self._pre_test_preset_mode == "random":
            self._fp_status_lbl.setText(
                f"已选: 随机故障（进入测试后自动注入，内容对学员保密）\n流程模式: {mode_text}"
            )
            self._apply_badge_tone(self._fp_status_lbl, "danger")
            return
        if not scenario_id:
            self._fp_status_lbl.setText(f"已选: 正常模式（无故障注入）\n流程模式: {mode_text}")
            self._apply_badge_tone(self._fp_status_lbl, "warning")
            return
        info = SCENARIOS.get(scenario_id, {})
        self._fp_status_lbl.setText(
            f"已选: {scenario_id} — {info.get('label', '')}\n{info.get('title', '')}\n流程模式: {mode_text}"
        )
        self._apply_badge_tone(self._fp_status_lbl, "danger")

    def _on_fp_random(self):
        fault_ids = [sid for sid in SCENARIOS if sid]
        self._pre_test_scenario_id = _random.choice(fault_ids)
        self._pre_test_preset_mode = "random"
        self._pre_test_flow_mode = "assessment"
        self._sync_fault_preset_buttons(self._pre_test_preset_mode)
        self._refresh_pretest_status_label()

    def _on_fp_choose(self):
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("指定故障场景")
        dlg.setModal(True)
        dlg.resize(500, 620)

        lay = QtWidgets.QVBoxLayout(dlg)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(6)

        hdr = QtWidgets.QLabel("选择要注入的故障场景\n（进入测试模式后学员不可见具体场景信息）")
        self._apply_badge_tone(hdr, "primary")
        hdr.setWordWrap(True)
        lay.addWidget(hdr)

        current_id = self._pre_test_scenario_id
        btn_grp = QtWidgets.QButtonGroup(dlg)
        colors = {None: "#64748b", "I": "#dc2626", "II": "#d97706", "III": "#2563eb", "IV": "#7c3aed"}
        scene_scroll = QtWidgets.QScrollArea()
        scene_scroll.setWidgetResizable(True)
        scene_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scene_wrap = QtWidgets.QWidget()
        scene_lay = QtWidgets.QVBoxLayout(scene_wrap)
        scene_lay.setContentsMargins(0, 0, 0, 0)
        scene_lay.setSpacing(4)
        for sid, info in SCENARIOS.items():
            color = colors.get(info.get("category"), "#64748b")
            cat_tag = f"[{info['label']}]  " if info.get("category") else ""
            rb = QtWidgets.QRadioButton(f"{cat_tag}{info['title']}")
            rb.setProperty("scenario_id", sid)
            rb.setStyleSheet(f"color:{color}; font-size:12px; padding:2px 0;")
            if sid == current_id:
                rb.setChecked(True)
            btn_grp.addButton(rb)
            scene_lay.addWidget(rb)
        scene_lay.addStretch()
        scene_scroll.setWidget(scene_wrap)
        lay.addWidget(scene_scroll, 1)

        mode_grp = QtWidgets.QGroupBox("流程模式")
        mode_lay = QtWidgets.QVBoxLayout(mode_grp)
        mode_lay.setContentsMargins(8, 6, 8, 6)
        mode_lay.setSpacing(4)
        mode_hint = QtWidgets.QLabel(
            "教学模式允许带故障继续后续步骤；工程模式要求当前步骤合格后才能进入下一步；"
            "考核模式在第四步闭环完成时自动结算成绩，第五步不计分。"
        )
        mode_hint.setWordWrap(True)
        mode_hint.setProperty("mutedText", True)
        mode_lay.addWidget(mode_hint)
        rb_teaching = QtWidgets.QRadioButton("教学模式")
        rb_engineering = QtWidgets.QRadioButton("工程模式")
        rb_assessment = QtWidgets.QRadioButton("考核模式")
        rb_teaching.setChecked(self._pre_test_flow_mode == "teaching")
        rb_engineering.setChecked(self._pre_test_flow_mode == "engineering")
        rb_assessment.setChecked(self._pre_test_flow_mode == "assessment")
        mode_lay.addWidget(rb_teaching)
        mode_lay.addWidget(rb_engineering)
        mode_lay.addWidget(rb_assessment)
        lay.addWidget(mode_grp)

        brow = QtWidgets.QHBoxLayout()
        btn_cancel = QtWidgets.QPushButton("取消")
        btn_ok = QtWidgets.QPushButton("确认")
        btn_cancel.setProperty("secondary", True)
        self._apply_button_tone(btn_ok, "primary")
        btn_cancel.clicked.connect(dlg.reject)
        btn_ok.clicked.connect(dlg.accept)
        brow.addStretch()
        brow.addWidget(btn_cancel)
        brow.addWidget(btn_ok)
        lay.addLayout(brow)

        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            selected_id = ""
            for btn in btn_grp.buttons():
                if btn.isChecked():
                    selected_id = btn.property("scenario_id")
                    break
            self._pre_test_flow_mode = (
                "engineering" if rb_engineering.isChecked() else
                "assessment" if rb_assessment.isChecked() else
                "teaching"
            )
            self._on_fp_set(selected_id)
        else:
            self._sync_fault_preset_buttons(self._pre_test_preset_mode)

    @staticmethod
    def _flow_mode_label(mode: str) -> str:
        return {
            "teaching": "教学模式",
            "engineering": "工程模式",
            "assessment": "考核模式",
        }.get(mode, "教学模式")

    def _on_circuit_click(self, event):
        if self._circuit_tab.get_phase_wiring_status() == PhaseWiringStatus.WIRING:
            if self._circuit_tab.handle_phase_wiring_click(event):
                return
        
        if not self.ctrl.sim_state.multimeter_mode:
            return
        if event.inaxes != self.ax_circuit or event.xdata is None or event.ydata is None:
            return
        
        closest_node = None
        min_dist = 0.04
        for name, data in NODES.items():
            dist = ((event.xdata - data[0]) ** 2 + (event.ydata - data[1]) ** 2) ** 0.5
            if dist < min_dist:
                closest_node = name
                min_dist = dist

        if closest_node:
            sim = self.ctrl.sim_state
            if sim.probe1_node is None:
                sim.probe1_node = closest_node
            elif sim.probe2_node is None and closest_node != sim.probe1_node:
                sim.probe2_node = closest_node
            else:
                sim.probe1_node = closest_node
                sim.probe2_node = None

    def _update_generator_buttons(self):
        for card in (self._gen1_card, self._gen2_card):
            card.refresh()
