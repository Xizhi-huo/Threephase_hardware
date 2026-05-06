"""
ui/tabs/circuit_tab package
母排拓扑图 Tab（独立 QWidget 组件）
"""

from __future__ import annotations

from typing import Callable, Dict, Protocol

from PyQt5 import QtCore, QtWidgets

from ui.matplotlib_config import configure_matplotlib

configure_matplotlib()

from matplotlib.figure import Figure

from ui.tabs.waveform_tab import MplCanvas
from ui.widgets.multimeter_widget import MultimeterWidget
from ui.widgets.phase_seq_meter import PhaseSeqMeterWidget

from ._draw_topology import DrawTopologyMixin
from ._phase_wiring import PhaseWiringMixin, PhaseWiringSession, PhaseWiringStatus
from ._record_tables import RecordTablesMixin


class CircuitTabAPI(Protocol):
    @property
    def sim_state(self) -> object: ...

    @property
    def pt_phase_orders(self) -> object: ...

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

    def get_pt_phase_sequence(self, name: str): ...

    def is_assessment_mode(self) -> bool: ...

    def is_loop_test_complete(self) -> bool: ...


class CircuitTab(
    PhaseWiringMixin,
    RecordTablesMixin,
    DrawTopologyMixin,
    QtWidgets.QWidget,
):
    def __init__(
        self,
        api: CircuitTabAPI,
        *,
        sidebar_badges: Dict[str, QtWidgets.QLabel],
        apply_badge_tone: Callable[[QtWidgets.QWidget, str], None],
        on_circuit_click: Callable[[object], None],
        is_test_mode_active: Callable[[], bool],
        get_current_test_step: Callable[[], int],
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._api = api
        self._sidebar_badges = sidebar_badges
        self._apply_badge_tone_cb = apply_badge_tone
        self._on_circuit_click = on_circuit_click
        self._is_test_mode_active_cb = is_test_mode_active
        self._get_current_test_step_cb = get_current_test_step
        self._phase_wiring: PhaseWiringSession = PhaseWiringSession()
        self._build()

    def _build(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.fig2 = Figure(figsize=(8, 6), dpi=100)
        self.ax_circuit = self.fig2.add_subplot(111)
        self.fig2.tight_layout(pad=1.2)
        self.canvas2 = MplCanvas(self.fig2)
        layout.addWidget(self.canvas2)

        self.phase_seq_meter = PhaseSeqMeterWidget(self.canvas2)
        self.phase_seq_meter.setVisible(False)

        self.multimeter_widget = MultimeterWidget(self.canvas2)
        self.multimeter_widget.setVisible(False)

        self._psm_result_lbl = QtWidgets.QLabel("", self.canvas2)
        self._psm_result_lbl.setAlignment(QtCore.Qt.AlignCenter)
        self._psm_result_lbl.setWordWrap(True)
        self._psm_result_lbl.setStyleSheet(
            "color:#ecf0f1; font-size:10px; background:rgba(30,39,46,200);"
            " border-radius:4px; padding:2px 6px;"
        )
        self._psm_result_lbl.setVisible(False)

        self.canvas2.mpl_connect("button_press_event", self._on_circuit_click)
        self._loop_anim_offset = 0.0
        self._draw_circuit_content()

    def render(self, p) -> None:
        self._render_ct_readings(p)
        self._render_bus_status(p)
        self._render_breakers(p)
        self._render_phase_wiring()
        self._render_generators()
        self._render_gen_wire_visibility()
        self._render_grounding_and_pt(p)
        self._render_multimeter(p)
        self._render_pt_record_tables(p)

    def redraw_canvas(self) -> None:
        self.canvas2.draw_idle()

    def rebuild_circuit_diagram(self) -> None:
        """重绘拓扑图（由 ctrl 调用）。"""
        self._draw_circuit_content()
        self.canvas2.draw()


__all__ = ["CircuitTab", "CircuitTabAPI", "PhaseWiringStatus"]
