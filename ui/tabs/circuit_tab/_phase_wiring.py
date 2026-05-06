from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from domain.node_map import NODES


class PhaseWiringStatus(StrEnum):
    IDLE = "idle"
    WIRING = "wiring"
    READY = "ready"


@dataclass
class PhaseWiringSession:
    active_pt: str | None = None
    wired: set[str] = field(default_factory=set)


class PhaseWiringMixin:
    def _place_phase_seq_meter(self) -> None:
        mw, mh = self.phase_seq_meter.width(), self.phase_seq_meter.height()
        bbox = self.ax_circuit.get_position()
        xlim = self.ax_circuit.get_xlim()
        ylim = self.ax_circuit.get_ylim()
        cw, ch = self.canvas2.width(), self.canvas2.height()
        if xlim[1] == xlim[0] or ylim[1] == ylim[0]:
            px, py = cw // 2, ch // 2
        else:
            ax_fx = (0.50 - xlim[0]) / (xlim[1] - xlim[0])
            ax_fy = (0.72 - ylim[0]) / (ylim[1] - ylim[0])
            fig_fx = bbox.x0 + ax_fx * (bbox.x1 - bbox.x0)
            fig_fy = bbox.y0 + ax_fy * (bbox.y1 - bbox.y0)
            px = int(fig_fx * cw)
            py = int((1.0 - fig_fy) * ch)

        mx = px - mw // 2
        my = py - mh // 2
        self.phase_seq_meter.move(mx, my)
        self.phase_seq_meter.setVisible(True)
        self.phase_seq_meter.raise_()

    def get_phase_wiring_status(self) -> PhaseWiringStatus:
        if self._phase_wiring.active_pt is None:
            return PhaseWiringStatus.IDLE
        if self._phase_wiring.wired == {"A", "B", "C"}:
            return PhaseWiringStatus.READY
        return PhaseWiringStatus.WIRING

    def get_phase_wiring_active_pt(self) -> str | None:
        return self._phase_wiring.active_pt

    def _phase_target_nodes(self) -> tuple[str, ...]:
        pt_name = self._phase_wiring.active_pt
        if pt_name not in ("PT1", "PT3"):
            return ()
        return tuple(f"{pt_name}_{phase}" for phase in ("A", "B", "C"))

    def connect_phase_seq_meter(self, pt_name: str) -> None:
        pt_name = pt_name.upper()
        self._phase_wiring.active_pt = pt_name
        self._phase_wiring.wired.clear()

        self.phase_seq_meter.set_waiting(pt_name, 0, 3)
        sim = self._api.sim_state
        freq = sim.gen1.freq if pt_name in ("PT1", "PT2") else sim.gen2.freq
        self.phase_seq_meter.set_freq(freq)
        self._place_phase_seq_meter()
        self._psm_result_lbl.setVisible(False)
        self.canvas2.draw_idle()

    def disconnect_phase_seq_meter(self) -> None:
        self._phase_wiring.active_pt = None
        self._phase_wiring.wired.clear()
        self.phase_seq_meter.disconnect()
        self.phase_seq_meter.setVisible(False)
        self._psm_result_lbl.setVisible(False)
        self.canvas2.draw_idle()

    def _show_phase_seq_result(self, pt_name: str, seq: str) -> None:
        self.phase_seq_meter.connect_pt(pt_name, seq)
        self._place_phase_seq_meter()

        if seq in {"ABC", "BCA", "CAB"}:
            color, label = "#2ecc71", "正序"
        elif seq == "FAULT":
            color, label = "#f39c12", "不平衡/故障"
        else:
            color, label = "#e74c3c", "反序"

        self._psm_result_lbl.setText(f"{pt_name} -> {label}")
        self._psm_result_lbl.setStyleSheet(
            f"color:{color}; font-size:10px;"
            " background: rgba(30, 39, 46, 200);"
            " border-radius: 4px;"
            " padding: 2px 6px;"
        )
        self._psm_result_lbl.adjustSize()

        mw, mh = self.phase_seq_meter.width(), self.phase_seq_meter.height()
        px = self.phase_seq_meter.x() + mw // 2
        py = self.phase_seq_meter.y() + mh
        lw = self._psm_result_lbl.width()
        self._psm_result_lbl.move(max(0, px - lw // 2), py + 4)
        self._psm_result_lbl.setVisible(True)
        self._psm_result_lbl.raise_()
        self.canvas2.draw_idle()

    def handle_phase_wiring_click(self, event) -> bool:
        if self.get_phase_wiring_status() != PhaseWiringStatus.WIRING:
            return False
        if event.inaxes != self.ax_circuit or event.xdata is None or event.ydata is None:
            return True

        closest_node = None
        min_dist = 0.04
        for node_name in self._phase_target_nodes():
            x, y = NODES[node_name][:2]
            dist = ((event.xdata - x) ** 2 + (event.ydata - y) ** 2) ** 0.5
            if dist < min_dist:
                closest_node = node_name
                min_dist = dist

        if closest_node is None:
            return True

        phase = closest_node.rsplit("_", 1)[1]
        if phase not in self._phase_wiring.wired:
            self._phase_wiring.wired.add(phase)
            self.phase_seq_meter.set_waiting(
                self._phase_wiring.active_pt,
                len(self._phase_wiring.wired),
                3,
            )
            if self._phase_wiring.wired == {"A", "B", "C"}:
                seq = self._api.get_pt_phase_sequence(self._phase_wiring.active_pt)
                self._show_phase_seq_result(self._phase_wiring.active_pt, seq)

        self.canvas2.draw_idle()
        return True

    def _render_phase_wiring(self) -> None:
        active_pt = self._phase_wiring.active_pt
        wired = self._phase_wiring.wired

        for node_name, pack in self._psm_terminal_markers.items():
            pt_name, phase = node_name.split("_", 1)
            is_target = (
                active_pt == pt_name
                and self.get_phase_wiring_status() in {
                    PhaseWiringStatus.WIRING,
                    PhaseWiringStatus.READY,
                }
            )
            is_wired = is_target and phase in wired

            pack["ring"].set_visible(is_target)
            pack["fill"].set_visible(is_wired)


__all__ = ["PhaseWiringMixin", "PhaseWiringSession", "PhaseWiringStatus"]
