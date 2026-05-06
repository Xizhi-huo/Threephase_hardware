from PyQt5 import QtCore, QtWidgets

from domain.constants import TRIP_CURRENT

from ui.widgets.control_panel._widget_tokens import (
    apply_badge_tone,
    apply_button_tone,
    apply_toggle_tone,
    make_slider,
    slider_row,
)


class ParamControlsPage(QtWidgets.QWidget):
    def __init__(
        self,
        *,
        sim_state,
        on_toggle_pause,
        on_instant_sync,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.sim_state = sim_state
        self.on_toggle_pause_cb = on_toggle_pause
        self.on_instant_sync_cb = on_instant_sync
        self._build()

    def _build(self):
        self.setObjectName("controlPage1")
        self.setProperty("panelSurface", True)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(8)
        layout.setAlignment(QtCore.Qt.AlignTop)

        speed_group = QtWidgets.QGroupBox("⏱️ 仿真全局时间流速")
        speed_layout = QtWidgets.QVBoxLayout(speed_group)
        self.sim_speed_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.sim_speed_slider.setRange(5, 1000)
        self.sim_speed_slider.setValue(int(self.sim_state.sim_speed * 100))
        self.sim_speed_label = QtWidgets.QLabel(f"速度: {self.sim_state.sim_speed:.2f}×")
        self.sim_speed_slider.valueChanged.connect(self._on_sim_speed_changed)
        speed_layout.addWidget(self.sim_speed_label)
        speed_layout.addWidget(self.sim_speed_slider)
        layout.addWidget(speed_group)

        param_group = QtWidgets.QGroupBox("🎛️ PCC核心参数整定 (Parameter Setup)")
        param_layout = QtWidgets.QFormLayout(param_group)

        self.gov_gain_slider = make_slider(10, 200, int(self.sim_state.gov_gain * 100))
        self.gov_gain_label = QtWidgets.QLabel(f"{self.sim_state.gov_gain:.2f}")
        self.gov_gain_slider.valueChanged.connect(self._on_gov_gain_changed)
        param_layout.addRow("调速增益(Gov):", slider_row(self.gov_gain_slider, self.gov_gain_label))

        self.sync_gain_slider = make_slider(50, 800, int(self.sim_state.sync_gain * 100))
        self.sync_gain_label = QtWidgets.QLabel(f"{self.sim_state.sync_gain:.1f}")
        self.sync_gain_slider.valueChanged.connect(self._on_sync_gain_changed)
        param_layout.addRow("同步增益(Sync):", slider_row(self.sync_gain_slider, self.sync_gain_label))

        self.first_start_slider = make_slider(0, 30, self.sim_state.first_start_time)
        self.first_start_label = QtWidgets.QLabel(f"{self.sim_state.first_start_time}s")
        self.first_start_slider.valueChanged.connect(self._on_first_start_changed)
        param_layout.addRow("死母线投入延时:", slider_row(self.first_start_slider, self.first_start_label))

        layout.addWidget(param_group)

        # self.droop_cb = QtWidgets.QCheckBox("启用 P-f / Q-V 下垂控制 (自适应平衡)")
        # self.droop_cb.setChecked(self.sim_state.droop_enabled)
        # apply_toggle_tone(self.droop_cb, "warning")
        # self.droop_cb.toggled.connect(lambda value: setattr(self.sim_state, "droop_enabled", value))
        # layout.addWidget(self.droop_cb)

        self.rotate_phasor_cb = QtWidgets.QCheckBox("相量图：绝对参考系 (电网旋转)")
        self.rotate_phasor_cb.setChecked(self.sim_state.rotate_phasor)
        apply_toggle_tone(self.rotate_phasor_cb, "primary")
        self.rotate_phasor_cb.toggled.connect(lambda value: setattr(self.sim_state, "rotate_phasor", value))
        layout.addWidget(self.rotate_phasor_cb)

        self.relay_lbl = QtWidgets.QLabel(f"🛡️ 继电保护系统: 监控中 (阈值 {TRIP_CURRENT}A)")
        apply_badge_tone(self.relay_lbl, "primary")
        self.relay_lbl.setAlignment(QtCore.Qt.AlignCenter)
        self.relay_lbl.setWordWrap(True)
        self.relay_lbl.setMinimumHeight(40)
        layout.addWidget(self.relay_lbl)

        self.instant_btn = QtWidgets.QPushButton("⚡ 紧急一键强行合闸")
        apply_button_tone(self.instant_btn, "danger", hero=True)
        self.instant_btn.clicked.connect(self.on_instant_sync_cb)
        layout.addWidget(self.instant_btn)

        self.pause_btn = QtWidgets.QPushButton("⏸ 暂停整个物理空间")
        apply_button_tone(self.pause_btn, "warning", hero=True)
        self.pause_btn.clicked.connect(self.on_toggle_pause_cb)
        layout.addWidget(self.pause_btn)

        layout.addStretch()

    def _on_sim_speed_changed(self, value):
        speed = value / 100.0
        self.sim_state.sim_speed = speed
        self.sim_speed_label.setText(f"速度: {speed:.2f}×")

    def _on_gov_gain_changed(self, value):
        result = value / 100.0
        self.sim_state.gov_gain = result
        self.gov_gain_label.setText(f"{result:.2f}")

    def _on_sync_gain_changed(self, value):
        result = value / 100.0
        self.sim_state.sync_gain = result
        self.sync_gain_label.setText(f"{result:.1f}")

    def _on_first_start_changed(self, value):
        self.sim_state.first_start_time = value
        self.first_start_label.setText(f"{value}s")
