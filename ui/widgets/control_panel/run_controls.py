from PyQt5 import QtCore, QtWidgets

from domain.enums import AVAILABLE_MODES, SystemMode

from ui.widgets.control_panel._widget_tokens import (
    apply_badge_tone,
    apply_button_tone,
    apply_toggle_tone,
    set_props,
)


class RunControlsPage(QtWidgets.QWidget):
    def __init__(
        self,
        *,
        sim_state,
        on_fp_set,
        on_fp_random,
        on_fp_choose,
        on_enter_test_mode,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.sim_state = sim_state
        self.on_fp_set_cb = on_fp_set
        self.on_fp_random_cb = on_fp_random
        self.on_fp_choose_cb = on_fp_choose
        self.on_enter_test_mode_cb = on_enter_test_mode
        self._build()

    def _build(self):
        self.setObjectName("controlPage0")
        self.setProperty("panelSurface", True)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(8)
        layout.setAlignment(QtCore.Qt.AlignTop)

        mode_group = QtWidgets.QGroupBox("🔧 系统运行模式")
        mode_layout = QtWidgets.QVBoxLayout(mode_group)
        mode_layout.setSpacing(2)
        self.mode_bg = QtWidgets.QButtonGroup(self)
        for mode_value in AVAILABLE_MODES:
            available = mode_value == SystemMode.ISOLATED_BUS
            radio = QtWidgets.QRadioButton(mode_value if available else f"{mode_value} (待开发)")
            radio.setProperty("value", mode_value)
            radio.setEnabled(available)
            radio.setChecked(self.sim_state.system_mode == mode_value)
            radio.toggled.connect(lambda checked, v=mode_value: self._on_mode_changed(v, checked))
            self.mode_bg.addButton(radio)
            mode_layout.addWidget(radio)
        layout.addWidget(mode_group)

        fault_group = QtWidgets.QGroupBox("故障训练场景（教师预设）")
        fault_group.setProperty("cardTone", "warning")
        fault_layout = QtWidgets.QVBoxLayout(fault_group)
        fault_layout.setContentsMargins(8, 8, 8, 8)
        fault_layout.setSpacing(8)

        button_row = QtWidgets.QWidget()
        row = QtWidgets.QHBoxLayout(button_row)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        self.fp_btn_normal = QtWidgets.QPushButton("正常模式")
        self.fp_btn_random = QtWidgets.QPushButton("随机故障")
        self.fp_btn_choose = QtWidgets.QPushButton("指定场景...")
        for button, tone in (
            (self.fp_btn_normal, "primary"),
            (self.fp_btn_random, "danger"),
            (self.fp_btn_choose, "warning"),
        ):
            button.setCheckable(True)
            set_props(button, segment=True, segmentTone=tone)
        self.fp_btn_normal.clicked.connect(lambda: self.on_fp_set_cb(""))
        self.fp_btn_random.clicked.connect(self.on_fp_random_cb)
        self.fp_btn_choose.clicked.connect(self.on_fp_choose_cb)
        row.addWidget(self.fp_btn_normal, 1)
        row.addWidget(self.fp_btn_random, 1)
        row.addWidget(self.fp_btn_choose, 1)
        fault_layout.addWidget(button_row)

        self.fp_status_lbl = QtWidgets.QLabel("已选: 正常模式（无故障注入）\n流程模式: 教学模式")
        set_props(self.fp_status_lbl, mutedText=True, badge=True, tone="warning")
        self.fp_status_lbl.setWordWrap(True)
        fault_layout.addWidget(self.fp_status_lbl)
        layout.addWidget(fault_group)

        self.btn_enter_test_mode = QtWidgets.QPushButton("🔬 开始合闸前测试（进入测试模式）")
        apply_button_tone(self.btn_enter_test_mode, "primary", hero=True)
        self.btn_enter_test_mode.clicked.connect(self.on_enter_test_mode_cb)
        layout.addWidget(self.btn_enter_test_mode)

        self.bus_status_lbl = QtWidgets.QLabel("母排: 无电 (死母线)")
        apply_badge_tone(self.bus_status_lbl, "warning")
        self.bus_status_lbl.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.bus_status_lbl)

        self.bus_reference_lbl = QtWidgets.QLabel("参考基准: 无")
        apply_badge_tone(self.bus_reference_lbl, "neutral")
        self.bus_reference_lbl.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.bus_reference_lbl)

        self.arbitrator_lbl = QtWidgets.QLabel("🛠️ 仲裁器: 待机")
        apply_badge_tone(self.arbitrator_lbl, "info")
        self.arbitrator_lbl.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.arbitrator_lbl)

        grounding_group = QtWidgets.QGroupBox("🌍 中性点接地 (三相四线 N线)")
        grounding_layout = QtWidgets.QHBoxLayout(grounding_group)
        grounding_layout.setSpacing(4)
        self.gnd_bg = QtWidgets.QButtonGroup(self)
        for label, value in [("断开(绝缘测试)", "断开"), ("小电阻(10Ω)", "小电阻接地"), ("直接接地", "直接接地")]:
            radio = QtWidgets.QRadioButton(label)
            radio.setProperty("value", value)
            radio.setChecked(self.sim_state.grounding_mode == value)
            radio.toggled.connect(lambda checked, v=value: self._on_grounding_changed(v, checked))
            self.gnd_bg.addButton(radio)
            grounding_layout.addWidget(radio)
        layout.addWidget(grounding_group)

        self.remote_start_cb = QtWidgets.QCheckBox("🔌 闭合全局【远程启动】信号 (触发自动模式)")
        self.remote_start_cb.setChecked(self.sim_state.remote_start_signal)
        apply_toggle_tone(self.remote_start_cb, "success")
        self.remote_start_cb.toggled.connect(lambda value: setattr(self.sim_state, "remote_start_signal", value))
        layout.addWidget(self.remote_start_cb)

        self.multimeter_cb = QtWidgets.QCheckBox("🔌 拿取万用表 (PT压差/回路连通演示)")
        self.multimeter_cb.setChecked(self.sim_state.multimeter_mode)
        apply_toggle_tone(self.multimeter_cb, "warning")
        self.multimeter_cb.toggled.connect(self._on_multimeter_toggled)
        layout.addWidget(self.multimeter_cb)

        self.show_gen_wires_cb = QtWidgets.QCheckBox("显示发电机与母排之间的连线（取消勾选 = 黑盒模式）")
        self.show_gen_wires_cb.setChecked(self.sim_state.show_gen_wires)
        apply_toggle_tone(self.show_gen_wires_cb, "info")
        self.show_gen_wires_cb.toggled.connect(lambda value: setattr(self.sim_state, "show_gen_wires", value))
        layout.addWidget(self.show_gen_wires_cb)

        self._generator_layout = QtWidgets.QVBoxLayout()
        self._generator_layout.setContentsMargins(0, 0, 0, 0)
        self._generator_layout.setSpacing(8)
        layout.addLayout(self._generator_layout)

    def add_generator_card(self, card):
        self._generator_layout.addWidget(card)

    def _on_mode_changed(self, value, checked):
        if checked:
            self.sim_state.system_mode = value

    def _on_grounding_changed(self, value, checked):
        if checked:
            self.sim_state.grounding_mode = value

    def _on_multimeter_toggled(self, checked):
        self.sim_state.multimeter_mode = checked
