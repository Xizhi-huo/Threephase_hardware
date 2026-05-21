from typing import Callable, List

from domain.assessment import AssessmentEventType
from domain.constants import DEFAULT_PT3_RATIO, DEFAULT_PT_RATIO_ROWS, E04_PT3_RATIO, E04_PT3_RATIO_ROW
from domain.fault_scenarios import SCENARIOS


class FaultManager:
    def __init__(
        self,
        *,
        sim_state,
        blackbox_handler,
        append_assessment_event: Callable,
        request_pt_ratio_row_update: Callable,
        set_last_fault_detected: Callable[[bool], None],
        get_pt_phase_orders: Callable[[], dict],
        get_g1_blackbox_order: Callable[[], list],
        set_g1_blackbox_order: Callable[[list], None],
        get_g2_blackbox_order: Callable[[], list],
        set_g2_blackbox_order: Callable[[list], None],
        get_pt1_pri_blackbox_order: Callable[[], list],
        set_pt1_pri_blackbox_order: Callable[[list], None],
        get_pt1_sec_blackbox_order: Callable[[], list],
        set_pt1_sec_blackbox_order: Callable[[list], None],
        get_pt2_sec_blackbox_order: Callable[[], list],
        set_pt2_sec_blackbox_order: Callable[[list], None],
    ):
        self._sim_state = sim_state
        self._blackbox_handler = blackbox_handler
        self._append_assessment_event = append_assessment_event
        self._request_pt_ratio_row_update = request_pt_ratio_row_update
        self._set_last_fault_detected = set_last_fault_detected
        self._get_pt_phase_orders = get_pt_phase_orders
        self._get_g1_blackbox_order = get_g1_blackbox_order
        self._set_g1_blackbox_order = set_g1_blackbox_order
        self._get_g2_blackbox_order = get_g2_blackbox_order
        self._set_g2_blackbox_order = set_g2_blackbox_order
        self._get_pt1_pri_blackbox_order = get_pt1_pri_blackbox_order
        self._set_pt1_pri_blackbox_order = set_pt1_pri_blackbox_order
        self._get_pt1_sec_blackbox_order = get_pt1_sec_blackbox_order
        self._set_pt1_sec_blackbox_order = set_pt1_sec_blackbox_order
        self._get_pt2_sec_blackbox_order = get_pt2_sec_blackbox_order
        self._set_pt2_sec_blackbox_order = set_pt2_sec_blackbox_order

    def has_unrepaired_wiring_fault(self) -> bool:
        relevant_orders = self._get_repairable_wiring_orders()
        if not relevant_orders:
            return False
        normal_order = ['A', 'B', 'C']
        return any(order != normal_order for order in relevant_orders)

    def all_repairable_wiring_targets_normal(self) -> bool:
        relevant_orders = self._get_repairable_wiring_orders()
        if not relevant_orders:
            return False
        normal_order = ['A', 'B', 'C']
        return all(order == normal_order for order in relevant_orders)

    def fault_has_repairable_wiring_targets(self) -> bool:
        fc = self._sim_state.fault_config
        if not fc.active:
            return False
        return any(
            fc.params.get(key) is not None
            for key in (
                'g1_blackbox_order',
                'pt1_pri_blackbox_order',
                'p1_pri_blackbox_order',
                'pt1_sec_blackbox_order',
                'pt2_sec_blackbox_order',
                'g2_blackbox_order',
            )
        )

    def _get_repairable_wiring_orders(self) -> List[list]:
        fc = self._sim_state.fault_config
        if not (fc.active and not fc.repaired):
            return []

        relevant_orders = []
        if fc.params.get('g1_blackbox_order') is not None:
            relevant_orders.append(self._get_g1_blackbox_order())
        if (fc.params.get('pt1_pri_blackbox_order') is not None
                or fc.params.get('p1_pri_blackbox_order') is not None):
            relevant_orders.append(self._get_pt1_pri_blackbox_order())
        if fc.params.get('pt1_sec_blackbox_order') is not None:
            relevant_orders.append(self._get_pt1_sec_blackbox_order())
        if fc.params.get('pt2_sec_blackbox_order') is not None:
            relevant_orders.append(self._get_pt2_sec_blackbox_order())
        if fc.params.get('g2_blackbox_order') is not None:
            relevant_orders.append(self._get_g2_blackbox_order())
        return relevant_orders

    def inject_fault(self, scenario_id: str) -> None:
        """注入故障场景（由管理员在训练前设置）。scenario_id='' 清除故障。"""
        fc = self._sim_state.fault_config
        fc.scenario_id = scenario_id
        fc.active = bool(scenario_id)
        fc.detected = False
        fc.repaired = False
        self._set_last_fault_detected(False)
        scenario = SCENARIOS.get(scenario_id, {})
        fc.params = dict(scenario.get('params', {}))

        self._sim_state.fault_reverse_bc = False
        self._reset_blackbox_orders()
        self._reset_pt3_ratio()

        if scenario_id == 'E01':
            pt_phase_orders = self._get_pt_phase_orders()
            pt_phase_orders['PT1'] = ['B', 'A', 'C']
            pt_phase_orders['PT2'] = ['B', 'A', 'C']
            self._set_g1_blackbox_order(['B', 'A', 'C'])
        elif scenario_id == 'E02':
            self._set_g2_blackbox_order(['A', 'C', 'B'])
            self._blackbox_handler.sync_g2_blackbox_to_phase_orders()
        elif scenario_id == 'E04':
            self._sim_state.pt3_ratio = E04_PT3_RATIO
            self._request_pt_ratio_row_update('pt3_ratio', *E04_PT3_RATIO_ROW)

        self._set_g1_blackbox_order(list(
            fc.params.get('g1_blackbox_order', self._get_g1_blackbox_order())
        ))
        self._set_g2_blackbox_order(list(
            fc.params.get('g2_blackbox_order', self._get_g2_blackbox_order())
        ))
        self._set_pt1_pri_blackbox_order(list(
            fc.params.get(
                'pt1_pri_blackbox_order',
                fc.params.get('p1_pri_blackbox_order', self._get_pt1_pri_blackbox_order()),
            )
        ))
        self._set_pt1_sec_blackbox_order(list(
            fc.params.get('pt1_sec_blackbox_order', self._get_pt1_sec_blackbox_order())
        ))
        self._set_pt2_sec_blackbox_order(list(
            fc.params.get('pt2_sec_blackbox_order', self._get_pt2_sec_blackbox_order())
        ))

        pt1_order = fc.params.get('pt1_phase_order')
        if pt1_order:
            self._get_pt_phase_orders()['PT1'] = list(pt1_order)

        swap = fc.params.get('g1_loop_swap')
        if swap and scenario_id != 'E01':
            p1, p2 = swap
            new_pt2 = list(self._get_pt_phase_orders()['PT2'])
            i1 = ('A', 'B', 'C').index(p1)
            i2 = ('A', 'B', 'C').index(p2)
            new_pt2[i1], new_pt2[i2] = new_pt2[i2], new_pt2[i1]
            self._get_pt_phase_orders()['PT2'] = new_pt2

        if scenario_id == 'E02':
            self._blackbox_handler.sync_g2_blackbox_to_phase_orders()
        needs_pt1_sync = any(
            fc.params.get(key) is not None
            for key in (
                'g1_blackbox_order',
                'pt1_phase_order',
                'pt1_pri_blackbox_order',
                'p1_pri_blackbox_order',
                'pt1_sec_blackbox_order',
            )
        )
        needs_pt2_sync = fc.params.get('pt2_sec_blackbox_order') is not None
        if needs_pt1_sync:
            self._blackbox_handler.sync_pt1_blackbox_to_phase_orders()
        elif needs_pt2_sync:
            self._blackbox_handler.sync_pt2_blackbox_to_phase_orders()

    def repair_fault(self, step: int = 4, source: str = 'repair_fault') -> None:
        """学员完成虚拟修复后调用，消除故障效果并重置检测标志。"""
        fc = self._sim_state.fault_config
        sid = fc.scenario_id
        fc.repaired = True
        fc.detected = False
        self._append_assessment_event(
            AssessmentEventType.FAULT_REPAIRED, step=step, scene_id=sid, source=source
        )
        self._reset_blackbox_orders()

        if sid == 'E01':
            pt_phase_orders = self._get_pt_phase_orders()
            pt_phase_orders['PT1'] = ['A', 'B', 'C']
            pt_phase_orders['PT2'] = ['A', 'B', 'C']
        elif sid == 'E02':
            self._sim_state.fault_reverse_bc = False
            self._get_pt_phase_orders()['PT3'] = ['A', 'B', 'C']
        elif sid == 'E04':
            self._reset_pt3_ratio()

        if fc.params.get('pt1_phase_order') is not None:
            self._get_pt_phase_orders()['PT1'] = ['A', 'B', 'C']
        if fc.params.get('g1_loop_swap') is not None:
            self._get_pt_phase_orders()['PT2'] = ['A', 'B', 'C']
        if fc.params.get('pt2_sec_blackbox_order') is not None:
            self._get_pt_phase_orders()['PT2'] = ['A', 'B', 'C']

    def maybe_repair_pt_ratio_fault(
        self,
        ratio_attr: str,
        ratio: float,
        *,
        step: int = 2,
        source: str = 'pt_ratio_panel',
    ) -> bool:
        """E04 在 PT3 变比恢复到额定值后才清除故障。"""
        fc = self._sim_state.fault_config
        if not (
            ratio_attr == 'pt3_ratio'
            and fc.active
            and not fc.repaired
            and fc.scenario_id == 'E04'
        ):
            return False
        if abs(float(ratio) - DEFAULT_PT3_RATIO) > 1e-6:
            return False
        self.repair_fault(step=step, source=source)
        return True

    def _reset_blackbox_orders(self) -> None:
        normal = ['A', 'B', 'C']
        self._set_g1_blackbox_order(list(normal))
        self._set_g2_blackbox_order(list(normal))
        self._set_pt1_pri_blackbox_order(list(normal))
        self._set_pt1_sec_blackbox_order(list(normal))
        self._set_pt2_sec_blackbox_order(list(normal))

    def _reset_pt3_ratio(self) -> None:
        pri, sec = DEFAULT_PT_RATIO_ROWS['pt3_ratio']
        self._sim_state.pt3_ratio = DEFAULT_PT3_RATIO
        self._request_pt_ratio_row_update('pt3_ratio', pri, sec)
