from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


def _default_phase_orders() -> Dict[str, List[str]]:
    return {
        "PT1": ["A", "B", "C"],
        "PT2": ["A", "B", "C"],
        "PT3": ["A", "B", "C"],
    }


def _default_order() -> List[str]:
    return ["A", "B", "C"]


@dataclass
class PhaseOrderState:
    pt_phase_orders: Dict[str, List[str]] = field(default_factory=_default_phase_orders)
    g1_blackbox_order: List[str] = field(default_factory=_default_order)
    g2_blackbox_order: List[str] = field(default_factory=_default_order)
    pt1_pri_blackbox_order: List[str] = field(default_factory=_default_order)
    pt1_sec_blackbox_order: List[str] = field(default_factory=_default_order)
    pt2_sec_blackbox_order: List[str] = field(default_factory=_default_order)

    @classmethod
    def default(cls) -> "PhaseOrderState":
        return cls()

    def _overwrite_phase(self, pt_name: str, values: List[str]) -> None:
        target = self.pt_phase_orders.get(pt_name)
        if isinstance(target, list):
            target[:] = list(values)
        else:
            self.pt_phase_orders[pt_name] = list(values)

    def reset_pt_phase_orders(self) -> None:
        for pt_name, values in _default_phase_orders().items():
            self._overwrite_phase(pt_name, values)

    def reset_blackbox_orders(self) -> None:
        normal = _default_order()
        self.g1_blackbox_order[:] = normal
        self.g2_blackbox_order[:] = normal
        self.pt1_pri_blackbox_order[:] = normal
        self.pt1_sec_blackbox_order[:] = normal
        self.pt2_sec_blackbox_order[:] = normal

    def apply_g2_blackbox_to_pt3(self) -> None:
        """派生: PT3 ← g2_blackbox_order（整列覆盖）。"""
        self._overwrite_phase("PT3", self.g2_blackbox_order)

    def _compose_order(self, upstream_order: List[str], terminal_order: List[str]) -> List[str]:
        labels = ("A", "B", "C")
        return [upstream_order[labels.index(label)] for label in terminal_order]

    def apply_pt2_blackbox_to_pt2(self) -> None:
        """派生: PT2 ← g1_blackbox_order × PT2 二次侧黑盒。"""
        self._overwrite_phase(
            "PT2",
            self._compose_order(self.g1_blackbox_order, self.pt2_sec_blackbox_order),
        )

    def apply_pt1_blackbox_to_pt_phases(self, pt1_net_order: List[str]) -> None:
        """派生: PT2 ← 母排PT净相序；PT1 ← pt1_net_order。"""
        self.apply_pt2_blackbox_to_pt2()
        self._overwrite_phase("PT1", pt1_net_order)
