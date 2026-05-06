from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from domain.assessment import AssessmentEventType
from domain.models import SimulationState
from services.fault_manager import FaultManager
from services.flow_mode_manager import FlowModeManager

_NORMAL_ORDER = ['A', 'B', 'C']
_NORMAL_POLARITY = [1, 1, 1]


@dataclass(frozen=True)
class BlackboxRepairOutcome:
    target: str
    component_correct: bool
    fault_cleared: bool
    message: str
    message_color: str
    disable_repair_button: bool = False


class BlackboxRepairHandler:
    def __init__(
        self,
        *,
        sim_state: SimulationState,
        flow_mgr: FlowModeManager,
        get_fault_mgr: Callable[[], FaultManager],
        append_assessment_event: Callable,
        get_pt_phase_orders: Callable[[], dict],
        get_g1_blackbox_order: Callable[[], list],
        set_g1_blackbox_order: Callable[[list], None],
        get_g2_blackbox_order: Callable[[], list],
        set_g2_blackbox_order: Callable[[list], None],
        get_pt1_pri_blackbox_order: Callable[[], list],
        set_pt1_pri_blackbox_order: Callable[[list], None],
        get_pt1_sec_blackbox_order: Callable[[], list],
        set_pt1_sec_blackbox_order: Callable[[list], None],
        apply_g2_blackbox_to_pt3: Callable[[], None],
        apply_pt1_blackbox_to_pt_phases: Callable[[list], None],
    ):
        self._sim_state = sim_state
        self._flow_mgr = flow_mgr
        self._get_fault_mgr = get_fault_mgr
        self._append_assessment_event = append_assessment_event
        self._get_pt_phase_orders = get_pt_phase_orders
        self._get_g1_blackbox_order = get_g1_blackbox_order
        self._set_g1_blackbox_order = set_g1_blackbox_order
        self._get_g2_blackbox_order = get_g2_blackbox_order
        self._set_g2_blackbox_order = set_g2_blackbox_order
        self._get_pt1_pri_blackbox_order = get_pt1_pri_blackbox_order
        self._set_pt1_pri_blackbox_order = set_pt1_pri_blackbox_order
        self._get_pt1_sec_blackbox_order = get_pt1_sec_blackbox_order
        self._set_pt1_sec_blackbox_order = set_pt1_sec_blackbox_order
        self._apply_g2_blackbox_to_pt3 = apply_g2_blackbox_to_pt3
        self._apply_pt1_blackbox_to_pt_phases = apply_pt1_blackbox_to_pt_phases

    def get_blackbox_runtime_state(self, target: str) -> dict:
        fault_config = self._sim_state.fault_config
        fault_active = bool(fault_config.active and not fault_config.repaired)
        pt_phase_orders = self._get_pt_phase_orders()
        if target == 'G1':
            return {
                'fault_active': fault_active,
                'order': list(
                    self._get_g1_blackbox_order()
                    if fault_active else pt_phase_orders.get('PT2', ['A', 'B', 'C'])
                ),
                'repair_target': 'G1' if self._flow_mgr.can_repair_in_blackbox() else None,
            }
        if target == 'G2':
            return {
                'fault_active': fault_active,
                'order': list(
                    self._get_g2_blackbox_order()
                    if fault_active else pt_phase_orders.get('PT3', ['A', 'B', 'C'])
                ),
                'repair_target': 'G2' if self._flow_mgr.can_repair_in_blackbox() else None,
            }
        if target == 'PT1':
            if fault_active:
                pri_input_order = list(self._get_g1_blackbox_order())
                pri_order = list(self._get_pt1_pri_blackbox_order())
                sec_order = list(self._get_pt1_sec_blackbox_order())
            else:
                pri_input_order = ['A', 'B', 'C']
                pri_order = ['A', 'B', 'C']
                sec_order = ['A', 'B', 'C']
            return {
                'fault_active': fault_active,
                'pri_input_order': pri_input_order,
                'pri_order': pri_order,
                'sec_order': sec_order,
                'repair_target': 'PT1' if self._flow_mgr.can_repair_in_blackbox() else None,
            }
        if target == 'PT3':
            pri_input_order = ['A', 'B', 'C']
            if self._sim_state.fault_reverse_bc:
                pri_input_order = ['A', 'C', 'B']
            sec_polarity = [-1, 1, 1] if (
                fault_active
                and fault_config.scenario_id == 'E03'
                and fault_config.params.get('pt3_a_reversed')
            ) else list(_NORMAL_POLARITY)
            return {
                'fault_active': fault_active,
                'pri_input_order': pri_input_order,
                'pri_order': list(_NORMAL_ORDER),
                'sec_order': list(pt_phase_orders.get('PT3', _NORMAL_ORDER)),
                'sec_polarity': sec_polarity,
                'repair_target': 'PT3' if self._flow_mgr.can_repair_in_blackbox() else None,
            }
        raise ValueError(f"Unsupported blackbox target: {target}")

    def apply_blackbox_repair_attempt(
            self,
            target: str,
            step: int,
            *,
            initial_order=None,
            new_order=None,
            initial_pri_order=None,
            new_pri_order=None,
            initial_sec_order=None,
            new_sec_order=None,
            initial_sec_polarity=None,
            new_sec_polarity=None) -> BlackboxRepairOutcome:
        component_correct = False
        touched_layers = []

        if target == 'G1':
            if initial_order is not None and list(new_order) != list(initial_order):
                self._append_assessment_event(
                    AssessmentEventType.BLACKBOX_SWAP,
                    step=step,
                    target='G1',
                    layer='terminal',
                    from_order=list(initial_order),
                    to_order=list(new_order),
                )
                touched_layers.append('terminal')
            self._set_g1_blackbox_order(list(new_order))
            self.sync_pt1_blackbox_to_phase_orders()
            component_correct = (list(new_order) == ['A', 'B', 'C'])
        elif target == 'G2':
            if initial_order is not None and list(new_order) != list(initial_order):
                self._append_assessment_event(
                    AssessmentEventType.BLACKBOX_SWAP,
                    step=step,
                    target='G2',
                    layer='terminal',
                    from_order=list(initial_order),
                    to_order=list(new_order),
                )
                touched_layers.append('terminal')
            self._set_g2_blackbox_order(list(new_order))
            self.sync_g2_blackbox_to_phase_orders()
            component_correct = (list(new_order) == ['A', 'B', 'C'])
        elif target == 'PT1':
            if initial_pri_order is not None and list(new_pri_order) != list(initial_pri_order):
                self._append_assessment_event(
                    AssessmentEventType.BLACKBOX_SWAP,
                    step=step,
                    target='PT1',
                    layer='primary',
                    from_order=list(initial_pri_order),
                    to_order=list(new_pri_order),
                )
                touched_layers.append('primary')
            if initial_sec_order is not None and list(new_sec_order) != list(initial_sec_order):
                self._append_assessment_event(
                    AssessmentEventType.BLACKBOX_SWAP,
                    step=step,
                    target='PT1',
                    layer='secondary',
                    from_order=list(initial_sec_order),
                    to_order=list(new_sec_order),
                )
                touched_layers.append('secondary')
            self._set_pt1_pri_blackbox_order(list(new_pri_order))
            self._set_pt1_sec_blackbox_order(list(new_sec_order))
            self.sync_pt1_blackbox_to_phase_orders()
            component_correct = (
                list(new_pri_order) == ['A', 'B', 'C']
                and list(new_sec_order) == ['A', 'B', 'C']
            )
        elif target == 'PT3':
            if initial_sec_order is not None and list(new_sec_order) != list(initial_sec_order):
                self._append_assessment_event(
                    AssessmentEventType.BLACKBOX_SWAP,
                    step=step,
                    target='PT3',
                    layer='secondary',
                    from_order=list(initial_sec_order),
                    to_order=list(new_sec_order),
                )
                touched_layers.append('secondary')
            if (
                initial_sec_polarity is not None
                and new_sec_polarity is not None
                and list(new_sec_polarity) != list(initial_sec_polarity)
            ):
                self._append_assessment_event(
                    AssessmentEventType.BLACKBOX_SWAP,
                    step=step,
                    target='PT3',
                    layer='polarity',
                    from_order=list(initial_sec_polarity),
                    to_order=list(new_sec_polarity),
                )
                touched_layers.append('polarity')
            pt3_order = self._get_pt_phase_orders().setdefault('PT3', ['A', 'B', 'C'])
            pt3_order[:] = list(new_sec_order)
            fault_config = self._sim_state.fault_config
            e03_polarity_fault = (
                fault_config.active
                and not fault_config.repaired
                and fault_config.scenario_id == 'E03'
            )
            if new_sec_polarity is None:
                polarity_correct = not e03_polarity_fault
            else:
                polarity_correct = list(new_sec_polarity) == _NORMAL_POLARITY
            component_correct = (
                list(new_sec_order) == _NORMAL_ORDER
                and polarity_correct
            )
        else:
            raise ValueError(f"Unsupported blackbox repair target: {target}")

        self._append_assessment_event(
            AssessmentEventType.BLACKBOX_CONFIRM_ATTEMPTED,
            step=step,
            target=target,
            layers=touched_layers,
            success=bool(component_correct),
        )

        if not component_correct:
            return BlackboxRepairOutcome(
                target=target,
                component_correct=False,
                fault_cleared=False,
                message="X 接线仍有错误，请重新调整后再提交。",
                message_color="#dc2626",
            )

        fault_config = self._sim_state.fault_config
        fault_active = bool(fault_config.active and not fault_config.repaired)
        fault_cleared = False
        disable_repair_button = False
        fault_mgr = self._get_fault_mgr()
        if (
            fault_active
            and target == 'PT3'
            and fault_config.scenario_id == 'E03'
        ):
            fault_mgr.repair_fault(step=step, source='PT3_polarity_blackbox')
            fault_cleared = True
            disable_repair_button = True
            message = "OK PT3 A 相极性已恢复，故障已清除。请关闭黑盒后重新测量。"
            message_color = "#15803d"
        elif (
            fault_active
            and fault_mgr.all_repairable_wiring_targets_normal()
            and self._flow_mgr.should_auto_clear_fault_only_when_all_blackboxes_normal()
        ):
            fault_mgr.repair_fault(step=step, source=f'{target}_blackbox')
            fault_cleared = True
            disable_repair_button = True
            message = "OK 全部接线均已修复，故障已完全清除。"
            message_color = "#15803d"
        else:
            message = "OK 此处接线已修复。请关闭并检查其他位置的接线。"
            message_color = "#0369a1"

        return BlackboxRepairOutcome(
            target=target,
            component_correct=True,
            fault_cleared=fault_cleared,
            message=message,
            message_color=message_color,
            disable_repair_button=disable_repair_button,
        )

    def _compute_pt1_net_order(
        self,
        bus_order=None,
        pri_order=None,
        sec_order=None,
    ) -> list[str]:
        labels = ('A', 'B', 'C')
        bus_order = list(bus_order if bus_order is not None else self._get_g1_blackbox_order())
        pri_order = list(pri_order if pri_order is not None else self._get_pt1_pri_blackbox_order())
        sec_order = list(sec_order if sec_order is not None else self._get_pt1_sec_blackbox_order())

        primary_actual = [bus_order[labels.index(cable_label)] for cable_label in pri_order]
        return [primary_actual[labels.index(sec_label)] for sec_label in sec_order]

    def sync_pt1_blackbox_to_phase_orders(self) -> None:
        """派生同步: PT2 ← g1_blackbox_order；PT1 ← PT1 黑盒净相序。"""
        self._apply_pt1_blackbox_to_pt_phases(self._compute_pt1_net_order())

    def sync_g2_blackbox_to_phase_orders(self) -> None:
        """派生同步: PT3 ← g2_blackbox_order。"""
        self._apply_g2_blackbox_to_pt3()
