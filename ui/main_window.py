"""
ui/main_window.py  -  PyQt5 主窗口（组装入口）
三相电并网仿真教学系统 · 视图层

架构
----
PowerSyncUI 通过“Mixin + 独立 QWidget 组件”装配各区域：

  WidgetBuilderMixin  (ui/panels/control_panel.py)
    - 右侧控制面板的所有 QWidget 构建 + 槽函数

  WaveformTab        (ui/tabs/waveform_tab.py)
    - Tab0（波形/相量）的独立 QWidget 组件

  CircuitTab         (ui/tabs/circuit_tab/)
    - Tab1（母排拓扑）的独立 QWidget 组件

  LoopTestTab          (ui/tabs/loop_test_tab.py)
    - Tab2（回路测试）的独立 QWidget 组件

  PtVoltageCheckTab      (ui/tabs/pt_voltage_check_tab.py)
    - Tab3（PT 线电压检查）的独立 QWidget 组件

  PtPhaseCheckTab    (ui/tabs/pt_phase_check_tab.py)
    - Tab4（PT 相序检查）的独立 QWidget 组件

  PtExamTab         (ui/tabs/pt_exam_tab.py)
    - Tab5（PT 考核）的独立 QWidget 组件

  SyncTestTab        (ui/tabs/sync_test_tab.py)
    - Tab6（同步测试）的独立 QWidget 组件

本文件只负责：
  - 窗口框架（QMainWindow）
  - 中央布局（Tab 区 + 控制面板滚动区）
  - 装配独立 Tab 组件
  - show_warning 等少量顶层接口
"""

from PyQt5 import QtWidgets, QtCore, QtGui

from ui.styles import apply_app_theme
from ui.panels.control_panel import WidgetBuilderMixin
from ui.tabs.waveform_tab import WaveformTab
from ui.tabs.circuit_tab import CircuitTab
from ui.tabs.loop_test_tab import LoopTestTab
from ui.tabs.pt_voltage_check_tab import PtVoltageCheckTab
from ui.tabs.pt_phase_check_tab import PtPhaseCheckTab
from ui.tabs.pt_exam_tab import PtExamTab
from ui.tabs.sync_test_tab import SyncTestTab
from ui.test_panel import TestPanelWidget


class PowerSyncUI(
    WidgetBuilderMixin,
    QtWidgets.QMainWindow,
):
    """
    主窗口，装配右侧控制面板与已独立化的 Tab 组件。
    实例化后调用 showMaximized() 即可运行。
    """

    def __init__(self, ctrl):
        super().__init__()
        self.ctrl = ctrl
        self.setWindowTitle("三相电并网仿真教学系统 (PyQt5)")

        # 全屏/resize 防抖：resize 期间暂停 canvas 重绘，避免卡死
        self._resize_timer = QtCore.QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(150)
        self._resize_timer.timeout.connect(self._on_resize_done)
        self._is_resizing = False

        # -- 中央 Widget + 水平主布局 ----------------------------------------
        central = QtWidgets.QWidget()
        central.setObjectName("appRoot")
        self.setCentralWidget(central)
        h_layout = QtWidgets.QHBoxLayout(central)
        h_layout.setContentsMargins(12, 12, 12, 12)
        h_layout.setSpacing(12)

        # -- 左侧：Tab 区 ------------------------------------------------------
        self.tab_widget = QtWidgets.QTabWidget()
        self.tab_widget.setObjectName("mainTabWidget")
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.tabBar().setExpanding(False)
        self.tab_widget.tabBar().setElideMode(QtCore.Qt.ElideRight)
        h_layout.addWidget(self.tab_widget, stretch=1)

        # -- 右侧：控制面板（固定宽度 + 垂直滚动） ------------------------------
        ctrl_container = QtWidgets.QScrollArea()
        ctrl_container.setObjectName("controlSidebarScroll")
        ctrl_container.setFixedWidth(520)
        ctrl_container.setWidgetResizable(True)
        ctrl_container.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.ctrl_inner = QtWidgets.QWidget()
        self.ctrl_inner.setObjectName("controlSidebar")
        self.ctrl_inner.setProperty("panelSurface", True)
        ctrl_container.setWidget(self.ctrl_inner)
        h_layout.addWidget(ctrl_container)
        self.ctrl_container = ctrl_container  # 保存引用，供 test_panel 切换显示

        self.ctrl_layout = QtWidgets.QVBoxLayout(self.ctrl_inner)
        self.ctrl_layout.setAlignment(QtCore.Qt.AlignTop)
        self.ctrl_layout.setContentsMargins(0, 0, 0, 0)
        self.ctrl_layout.setSpacing(8)

        # -- 构建各区域 --------------------------------------------------------
        self._build_control_panel()           # <- WidgetBuilderMixin
        self._waveform_tab = WaveformTab(self.ctrl, parent=self)
        self.tab_widget.addTab(self._waveform_tab, " 📊 实时波形与同期表 ")
        self._circuit_tab = CircuitTab(
            self.ctrl,
            sidebar_badges={
                "bus_status_lbl": self.bus_status_lbl,
                "bus_reference_lbl": self.bus_reference_lbl,
                "arbitrator_lbl": self.arbitrator_lbl,
                "relay_lbl": self.relay_lbl,
                "status1_lbl": self.status1_lbl,
                "status2_lbl": self.status2_lbl,
            },
            apply_badge_tone=self._apply_badge_tone,
            on_circuit_click=self._on_circuit_click,
            is_test_mode_active=self._is_test_mode_active,
            get_current_test_step=self._current_test_step,
            parent=self,
        )
        self.tab_widget.addTab(self._circuit_tab, " ⚡ 母排拓扑与环流监测 ")
        self._loop_test_tab = LoopTestTab(
            self.ctrl,
            on_open_circuit_tab=lambda: self.tab_widget.setCurrentIndex(1),
            on_toggle_multimeter=lambda: self.multimeter_cb.setChecked(
                not self.multimeter_cb.isChecked()
            ),
        )
        self.tab_widget.addTab(self._loop_test_tab, " 🔌 第一步：回路连通性测试 ")
        self._pt_voltage_check_tab = PtVoltageCheckTab(
            self.ctrl,
            on_open_circuit_tab=lambda: self.tab_widget.setCurrentIndex(1),
            on_toggle_multimeter=lambda: self.multimeter_cb.setChecked(
                not self.multimeter_cb.isChecked()
            ),
        )
        self.tab_widget.addTab(self._pt_voltage_check_tab, " 📏 第二步：PT线电压检查 ")
        self._pt_phase_check_tab = PtPhaseCheckTab(
            self.ctrl,
            on_open_circuit_tab=lambda: self.tab_widget.setCurrentIndex(1),
            on_toggle_multimeter=lambda: self.multimeter_cb.setChecked(
                not self.multimeter_cb.isChecked()
            ),
        )
        self.tab_widget.addTab(self._pt_phase_check_tab, " 🔀 第三步：PT相序检查 ")
        self._pt_exam_tab = PtExamTab(
            self.ctrl,
            on_open_circuit_tab=lambda: self.tab_widget.setCurrentIndex(1),
            on_toggle_multimeter=lambda: self.multimeter_cb.setChecked(
                not self.multimeter_cb.isChecked()
            ),
        )
        self.tab_widget.addTab(self._pt_exam_tab, " 🧪 第四步：PT二次端子压差测试")
        self._sync_test_tab = SyncTestTab(
            self.ctrl,
            on_open_waveform_tab=lambda: self.tab_widget.setCurrentIndex(0),
        )
        self.tab_widget.addTab(self._sync_test_tab, " ⚡ 第五步：同步功能测试")

        # -- 全局主题 + Tab 整理 -----------------------------------------------
        apply_app_theme(QtWidgets.QApplication.instance())
        self.tab_widget.setTabText(0, "📊 实时波形与同期表")
        # 步骤 Tab 2-6 由测试模式按需显示，初始隐藏
        for _i in range(2, 7):
            try:
                self.tab_widget.setTabVisible(_i, False)
            except AttributeError:
                pass  # Qt < 5.15 fallback: 无 setTabVisible

        # -- 竖向测试控制条（测试模式时替换右侧控制台） -------------------------
        self._test_panel_widget = TestPanelWidget(
            self.ctrl,
            on_show_test_panel=lambda active: self.ctrl_container.setVisible(not active),
            on_set_current_tab=lambda idx: self.tab_widget.setCurrentIndex(idx),
            on_set_step_tabs_visible=lambda active: [
                self.tab_widget.setTabVisible(i, active) for i in range(2, 7)
            ],
            on_toggle_multimeter=lambda: self.multimeter_cb.setChecked(
                not self.multimeter_cb.isChecked()
            ),
            on_force_multimeter_off=lambda: self.multimeter_cb.setChecked(False),
            on_connect_phase_seq_meter=lambda pt: self.connect_phase_seq_meter(pt),
            on_disconnect_phase_seq_meter=lambda: self.disconnect_phase_seq_meter(),
            on_restore_runtime_ui=self.restore_pre_test_ui_state,
            get_phase_seq_meter_sequence=lambda: self.phase_seq_meter.current_sequence(),
            get_phase_wiring_status=lambda: self._circuit_tab.get_phase_wiring_status(),
            get_phase_wiring_active_pt=lambda: self._circuit_tab.get_phase_wiring_active_pt(),

            parent=self,
        )
        h_layout.addWidget(self._test_panel_widget)   # 加入主布局（初始隐藏）
        self._init_signal_trial_status_widgets()
        self._connect_controller_signals()

    # -- resize 防抖回调 -------------------------------------------------------
    def resizeEvent(self, event: QtGui.QResizeEvent):
        self._is_resizing = True
        self._resize_timer.start()
        super().resizeEvent(event)

    def _on_resize_done(self):
        self._is_resizing = False

    def _init_signal_trial_status_widgets(self):
        status = self.statusBar()
        self._step_status_chip = QtWidgets.QLabel("当前步骤：第 1 步")
        self._mode_status_chip = QtWidgets.QLabel("流程模式：教学/工程")
        for chip in (self._step_status_chip, self._mode_status_chip):
            chip.setStyleSheet(
                "padding:2px 8px; border:1px solid #cbd5e1; border-radius:10px; color:#334155;"
            )
            status.addPermanentWidget(chip)

    def _connect_controller_signals(self):
        self.ctrl.signals.step_changed.connect(self._on_step_changed)
        self.ctrl.signals.assessment_mode_changed.connect(self._on_assessment_mode_changed)
        self._on_step_changed(0, self._current_test_step())
        self._on_assessment_mode_changed(self.ctrl.is_assessment_mode())

    @QtCore.pyqtSlot(int, int)
    def _on_step_changed(self, old_step: int, new_step: int):
        del old_step
        self._step_status_chip.setText(f"当前步骤：第 {new_step} 步")

    @QtCore.pyqtSlot(bool)
    def _on_assessment_mode_changed(self, is_assessment: bool):
        text = "流程模式：考核" if is_assessment else "流程模式：教学/工程"
        tone = "#92400e" if is_assessment else "#334155"
        self._mode_status_chip.setText(text)
        self._mode_status_chip.setStyleSheet(
            "padding:2px 8px; border:1px solid #cbd5e1; border-radius:10px;"
            f" color:{tone};"
        )

    @property
    def test_panel(self):
        return self._test_panel_widget

    def _is_test_mode_active(self):
        panel = getattr(self, "_test_panel_widget", None)
        return panel.is_test_mode_active() if panel is not None else False

    def _current_test_step(self):
        panel = getattr(self, "_test_panel_widget", None)
        return panel._current_test_step() if panel is not None else 1

    @property
    def ax_circuit(self):
        return self._circuit_tab.ax_circuit

    @property
    def canvas2(self):
        return self._circuit_tab.canvas2

    @property
    def phase_seq_meter(self):
        return self._circuit_tab.phase_seq_meter

    def _draw_waveform_canvases(self):
        self._waveform_tab.redraw_canvases()

    def rebuild_circuit_diagram(self):
        self._circuit_tab.rebuild_circuit_diagram()

    def connect_phase_seq_meter(self, pt_name: str) -> None:
        self._circuit_tab.connect_phase_seq_meter(pt_name)
        self.tab_widget.setCurrentIndex(1)

    def disconnect_phase_seq_meter(self):
        self._circuit_tab.disconnect_phase_seq_meter()

    def enter_test_mode(self):
        self.capture_pre_test_ui_state()
        self._test_panel_widget.set_pretest_config(
            getattr(self, "_pre_test_scenario_id", ""),
            getattr(self, "_pre_test_flow_mode", "teaching"),
            getattr(self, "_pre_test_preset_mode", "normal"),
        )
        self._test_panel_widget.enter_test_mode()

    def exit_test_mode(self):
        self._test_panel_widget.exit_test_mode()

    def capture_pre_test_ui_state(self):
        self._pre_test_ui_state = {
            "tab_index": self.tab_widget.currentIndex(),
            "control_panel_visible": self.ctrl_container.isVisible(),
            "control_stack_index": self._cp_stack.currentIndex(),
        }

    def restore_pre_test_ui_state(self):
        state = getattr(self, "_pre_test_ui_state", None) or {}
        self.sync_runtime_controls_from_state()
        self.ctrl_container.setVisible(state.get("control_panel_visible", True))
        self._cp_stack.setCurrentIndex(state.get("control_stack_index", 0))
        self._cp_btn_run.setChecked(self._cp_stack.currentIndex() == 0)
        self._cp_btn_param.setChecked(self._cp_stack.currentIndex() == 1)
        tab_index = state.get("tab_index", 0)
        if 0 <= tab_index < self.tab_widget.count():
            self.tab_widget.setCurrentIndex(tab_index)
        self._pre_test_ui_state = None

    def sync_runtime_controls_from_state(self):
        sim = self.ctrl.sim_state
        self._sync_button_group(self._mode_bg, sim.system_mode)
        self._sync_button_group(self._gnd_bg, sim.grounding_mode)
        for checkbox, value in (
            (self.remote_start_cb, sim.remote_start_signal),
            (self.multimeter_cb, sim.multimeter_mode),
            (self.show_gen_wires_cb, sim.show_gen_wires),
        ):
            checkbox.blockSignals(True)
            checkbox.setChecked(bool(value))
            checkbox.blockSignals(False)
        self.pause_btn.setText(
            "▶ 恢复物理时空" if sim.paused else "⏸ 暂停整个物理空间"
        )
        self._apply_button_tone(
            self.pause_btn,
            "success" if sim.paused else "warning",
            hero=True,
        )
        self._gen1_card.refresh()
        self._gen2_card.refresh()

    @staticmethod
    def _sync_button_group(group, value):
        for button in group.buttons():
            if button.property("value") != value:
                continue
            button.blockSignals(True)
            button.setChecked(True)
            button.blockSignals(False)
            break

    def _consume_controller_ui_requests(self):
        tab_index = self.ctrl.consume_requested_ui_tab()
        if tab_index is not None:
            self.tab_widget.setCurrentIndex(tab_index)

        ratio_updates = self.ctrl.consume_requested_pt_ratio_row_updates()
        if not ratio_updates:
            return

        rows = getattr(self._test_panel_widget, '_tp_s2_ratio_rows', {})
        for ratio_attr, (pri_value, sec_value) in ratio_updates.items():
            row = rows.get(ratio_attr)
            if not row:
                continue
            pri_spin, sec_spin, ratio_lbl = row
            pri_spin.blockSignals(True)
            sec_spin.blockSignals(True)
            pri_spin.setValue(pri_value)
            sec_spin.setValue(sec_value)
            pri_spin.blockSignals(False)
            sec_spin.blockSignals(False)
            ratio_lbl.setText(f"{pri_value / max(1, sec_value):.2f}")

    # -- 渲染主入口（每帧由 QTimer 驱动） -------------------------------------
    def render_visuals(self, rs):
        self._consume_controller_ui_requests()
        p = rs

        self._waveform_tab.render(rs)
        self._circuit_tab.render(p)
        # _render_circuit_quick_record 已移除（记录功能集中在右侧测试条）
        self._loop_test_tab.render(p)
        self._pt_voltage_check_tab.render(p)
        self._pt_phase_check_tab.render(p)
        self._sync_test_tab.render(p)
        self._pt_exam_tab.render(p)
        self._update_generator_buttons()
        self._test_panel_widget.render(p)
        self._check_fault_detection()

        # resize/全屏动画期间跳过 canvas 重绘，防止卡死
        if self._is_resizing:
            return

        idx = self.tab_widget.currentIndex()
        if idx == 0:
            self._draw_waveform_canvases()
        elif idx == 1:
            self._circuit_tab.redraw_canvas()

    # -- 故障检测轮询（每帧 render_visuals 末尾调用） --------------------------
    def _check_fault_detection(self):
        """
        轮询 fault_config.detected 标志。

        策略：
          - accident 场景：不在检测阶段提前弹窗，统一保留到步骤五真实合闸事故通道
          - recoverable 场景：仅通过横幅提示学员继续测试；
            修复统一延迟到第五步前，由测试面板门禁逻辑触发。
        """
        fc = self.ctrl.sim_state.fault_config
        if not (fc.active and fc.detected and not fc.repaired):
            self._fault_dialog_open = False
            return
        if getattr(self, '_fault_dialog_open', False):
            return
        from domain.fault_scenarios import SCENARIOS
        info = SCENARIOS.get(fc.scenario_id, {})
        if info.get('danger_level') == 'accident':
            return
        # 其他故障：横幅已更新，等待步骤五关卡触发修复

    def _show_blackbox_required_dialog(self, fc):
        """步骤五前发现黑盒接线未修复时，提示学员先回到黑盒中完成物理修复。"""
        from domain.fault_scenarios import SCENARIOS

        info = SCENARIOS.get(fc.scenario_id, {})
        dlg = QtWidgets.QDialog(self)
        is_assessment = getattr(self.ctrl, "is_assessment_mode", lambda: False)()
        dlg.setWindowTitle("⚠️ 当前流程尚未闭环" if is_assessment else "⚠️ 仍有接线故障未修复")
        dlg.setModal(True)
        dlg.resize(500, 300)

        lay = QtWidgets.QVBoxLayout(dlg)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(10)

        if is_assessment:
            title_text = "当前考核尚未闭环"
        else:
            title_text = info.get('title', '故障') + " — 需先完成黑盒修复"
        title_lbl = QtWidgets.QLabel(title_text)
        title_lbl.setStyleSheet("font-size:14px; font-weight:bold; color:#991b1b;")
        lay.addWidget(title_lbl)

        if is_assessment:
            hint_text = (
                "当前考核仍未满足结束条件，暂不能继续后续流程。\n\n"
                "请根据前四步已获得的测量结果继续排查并完成闭环。"
                "如需进一步确认，可进入黑盒检查，但系统不会提供具体故障位置提示。"
            )
        else:
            hint_text = (
                "当前仍存在未恢复的物理接线错误，不能进入第五步【同步功能测试】。\n\n"
                "请先回到当前流程中的黑盒检查区，完成相关接线修复。"
                "只有当相关接线全部恢复为正确顺序后，系统才会自动允许进入第五步。"
            )
        hint = QtWidgets.QLabel(hint_text)
        hint.setWordWrap(True)
        hint.setStyleSheet(
            "font-size:12px; color:#1f2937; background:#fff7ed;"
            " border:1px solid #fdba74; border-radius:4px; padding:8px;")
        lay.addWidget(hint)

        if not is_assessment:
            symptom_lbl = QtWidgets.QLabel("【当前已记录的异常现象】\n" + info.get('symptom', ''))
            symptom_lbl.setWordWrap(True)
            symptom_lbl.setStyleSheet(
                "font-size:11px; color:#374151; background:#fef3c7;"
                " padding:6px; border-radius:4px;")
            lay.addWidget(symptom_lbl)

        btn_ok = QtWidgets.QPushButton("知道了")
        btn_ok.setStyleSheet(
            "background:#334155; color:white; font-weight:bold; padding:6px 14px;")
        btn_ok.clicked.connect(dlg.accept)
        lay.addWidget(btn_ok, alignment=QtCore.Qt.AlignRight)

        dlg.exec_()

    def _show_accident_dialog(
        self,
        *,
        window_title: str,
        main_text: str,
        fault_loc_html: str,
        consequence_html: str,
        symptom_text: str,
        repair_hint_html: str,
        repair_source: str,
        dialog_height: int = 520,
    ):
        from PyQt5.QtCore import Qt

        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle(window_title)
        dlg.setModal(True)
        dlg.setWindowModality(Qt.ApplicationModal)
        dlg.setWindowFlags(
            Qt.Dialog
            | Qt.CustomizeWindowHint
            | Qt.WindowTitleHint
            | Qt.WindowStaysOnTopHint
        )
        dlg.resize(620, dialog_height)

        lay = QtWidgets.QVBoxLayout(dlg)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(12)

        banner = QtWidgets.QLabel("🚨  致命事故  🚨")
        banner.setAlignment(Qt.AlignCenter)
        banner.setStyleSheet(
            "background:#7f1d1d; color:#fef2f2; font-size:20px;"
            " font-weight:bold; padding:10px; border-radius:6px;"
        )
        lay.addWidget(banner)

        main_lbl = QtWidgets.QLabel(main_text)
        main_lbl.setAlignment(Qt.AlignCenter)
        main_lbl.setWordWrap(True)
        main_lbl.setStyleSheet(
            "font-size:16px; font-weight:bold; color:#991b1b; padding:6px;"
        )
        lay.addWidget(main_lbl)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea{border:2px solid #fca5a5; border-radius:4px; background:white;}"
        )
        inner = QtWidgets.QWidget()
        inner_lay = QtWidgets.QVBoxLayout(inner)
        inner_lay.setContentsMargins(12, 12, 12, 12)
        inner_lay.setSpacing(10)

        detail_title = QtWidgets.QLabel("【详细事故分析】")
        detail_title.setStyleSheet(
            "font-size:13px; font-weight:bold; color:#7f1d1d;"
        )
        inner_lay.addWidget(detail_title)

        fault_loc = QtWidgets.QLabel(fault_loc_html)
        fault_loc.setWordWrap(True)
        fault_loc.setStyleSheet("font-size:12px; color:#1e293b;")
        inner_lay.addWidget(fault_loc)

        consequence = QtWidgets.QLabel(consequence_html)
        consequence.setWordWrap(True)
        consequence.setStyleSheet("font-size:12px; color:#1e293b;")
        inner_lay.addWidget(consequence)

        symptom_box = QtWidgets.QLabel(symptom_text)
        symptom_box.setWordWrap(True)
        symptom_box.setStyleSheet(
            "font-size:11px; color:#374151; background:#fef3c7;"
            " padding:8px; border-radius:4px;"
        )
        inner_lay.addWidget(symptom_box)

        repair_hint = QtWidgets.QLabel(repair_hint_html)
        repair_hint.setWordWrap(True)
        repair_hint.setStyleSheet(
            "font-size:12px; color:#14532d; background:#dcfce7;"
            " padding:8px; border-radius:4px;"
        )
        inner_lay.addWidget(repair_hint)
        inner_lay.addStretch()

        scroll.setWidget(inner)
        lay.addWidget(scroll, 1)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.setSpacing(10)

        btn_repair = QtWidgets.QPushButton("🔧 修复故障，继续第五步测试")
        btn_repair.setStyleSheet(
            "background:#15803d; color:white; font-size:14px;"
            " font-weight:bold; padding:8px 20px; border-radius:4px;"
        )
        btn_repair.clicked.connect(
            lambda: (self.ctrl.repair_fault(step=5, source=repair_source), dlg.accept())
        )

        btn_record = QtWidgets.QPushButton("📋 确认事故已记录")
        btn_record.setStyleSheet(
            "background:#dc2626; color:white; font-size:13px;"
            " padding:8px 16px; border-radius:4px;"
        )
        btn_record.clicked.connect(dlg.accept)

        btn_row.addWidget(btn_repair)
        btn_row.addWidget(btn_record)
        lay.addLayout(btn_row)

        dlg.exec_()

    def show_e01_accident_dialog(self):
        self._show_accident_dialog(
            window_title="⚡ [致命事故] 非同期并网跳闸！",
            main_text="发电机 Gen2 发生非同期合闸，相间短路！\n机组已紧急停机！",
            fault_loc_html="<b>故障定位：</b>Gen1 出线 A、B 相序反接。",
            consequence_html=(
                "<b>动作后果：</b>同期装置单相（C 相）条件满足误发合闸指令，"
                "导致 A、B 错相 120° 短路，产生巨大非同期冲击电流，"
                "定子绕组及大轴严重受损。"
            ),
            symptom_text=(
                "【学员可见异常现象】\n"
                "第一步：AA 回路 ∞Ω（断路），BB 回路 ∞Ω（断路），CC 回路正常。\n"
                "第三步：PT1 相序仪显示反序。\n"
                "第四步：PT1_A↔PT2_B 压差 ≈ 0V，PT1_A↔PT2_A 压差 ≈ 146V。"
            ),
            repair_hint_html=(
                "<b>修复方法：</b>将 Gen1 接线盒内 A 相与 B 相端子重新对调接回原位，"
                "然后重新执行同步并网操作。"
            ),
            repair_source="E01_accident_dialog",
        )

    def show_e02_accident_dialog(self):
        self._show_accident_dialog(
            window_title="⚡ [致命事故] 跨相短路跳闸！",
            main_text="发电机 Gen2 合闸瞬间发生跨相短路！\n机组已紧急停机！",
            fault_loc_html="<b>故障定位：</b>Gen2 出线 B、C 相序反接。",
            consequence_html=(
                "<b>动作后果：</b>同期装置以 A 相为基准判定条件满足并发出合闸指令，"
                "但 Gen2 B 端子实接 C 相绕组、C 端子实接 B 相绕组，"
                "合闸瞬间 B/C 两相与母线形成 120° 跨相短路，"
                "产生巨大冲击电流，定子绕组及大轴严重受损。"
            ),
            symptom_text=(
                "【学员可见异常现象（合闸前已有预警）】\n"
                "第一步：BB 回路 ∞Ω（断路），CC 回路 ∞Ω（断路），AA 回路正常。\n"
                "第三步：PT3 相序仪显示反序。\n"
                "第四步：PT3_B↔PT2_C 压差 ≈ 0V，PT3_B↔PT2_B 压差 ≈ 146V。"
            ),
            repair_hint_html=(
                "<b>修复方法：</b>将 Gen2 接线盒内 B 相与 C 相端子重新对调接回原位，"
                "然后重新执行同步并网操作。"
            ),
            repair_source="E02_accident_dialog",
        )

    def show_e03_accident_dialog(self):
        self._show_accident_dialog(
            window_title="⚡ [致命事故] PT3极性错误导致非同期合闸！",
            main_text=(
                "PT3 A 相极性反接导致同期装置相角基准错误！\n"
                "Gen2 以 180° 反相位置合闸，发生非同期冲击！机组已紧急停机！"
            ),
            fault_loc_html=(
                "<b>故障定位：</b>PT3 A 相二次端子 K/k 极性反接，实际输出 −V<sub>A</sub>。"
            ),
            consequence_html=(
                "<b>动作后果：</b>同期装置以 PT3 A 相作为相角参考，极性反接使参考角偏差 180°。"
                "自动同期将 Gen2 驱向反相位置后误判“相角差 = 0°”发出合闸指令，"
                "合闸瞬间 Gen2 与母线实际相位差约 180°，产生巨大非同期冲击电流，"
                "定子绕组及大轴严重受损。"
            ),
            symptom_text=(
                "【学员可见异常现象（合闸前已有预警）】\n"
                "第二步：PT3_AB ≈ 106V（应≈184V，标红异常）；PT3_CA ≈ 106V（标红异常）。\n"
                "第三步：PT3 相序仪显示“故障/不平衡”（A 相极性反相）。\n"
                "第四步：PT3_A↔PT2_A ≈ 166V（应≈0V），PT3_A↔PT2_B/C ≈ 92V（应≈146V）。\n"
                "第五步：同期仪相位差持续显示约 180°，仲裁器报 PT3 A相极性异常。"
            ),
            repair_hint_html=(
                "<b>修复方法：</b>将 PT3 A 相二次端子 K/k 对调，恢复正确极性后"
                "重新执行同步并网操作。"
            ),
            repair_source="E03_accident_dialog",
            dialog_height=540,
        )


    # -- 对外接口（ctrl 调用） -----------------------------------------------
    def show_warning(self, title: str, message: str):
        self._consume_controller_ui_requests()
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setModal(True)
        dialog.resize(560, 360)

        layout = QtWidgets.QVBoxLayout(dialog)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        title_lbl = QtWidgets.QLabel(title)
        title_lbl.setStyleSheet("font-size:14px; font-weight:bold; color:#8b0000;")
        layout.addWidget(title_lbl)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: 1px solid #cccccc; background: white; }")

        content = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(content)
        content_layout.setContentsMargins(10, 10, 10, 10)

        msg_lbl = QtWidgets.QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        msg_lbl.setStyleSheet("font-size:12px; color:#222222;")
        msg_lbl.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        content_layout.addWidget(msg_lbl)
        content_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok)
        btn_box.accepted.connect(dialog.accept)
        layout.addWidget(btn_box)

        dialog.exec_()
