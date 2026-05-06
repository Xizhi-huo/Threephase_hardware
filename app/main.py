"""
app/main.py  ──  PyQt5 版本
三相电并网仿真教学系统 · 控制器层 + 程序入口

架构说明
────────
PowerSyncController   唯一数据源 (SimulationState) + 编排层
  ├─ LoopTestService          第一步：回路连通性测试业务逻辑
  ├─ PtVoltageCheckService    第二步：PT 单体线电压检查业务逻辑
  ├─ PtPhaseCheckService      第三步：PT 相序检查业务逻辑
  ├─ PtExamService            第四步：PT 二次端子压差考核业务逻辑
  └─ SyncTestService          第五步：同步功能测试业务逻辑
PhysicsEngine         物理计算，通过显式注入依赖读写状态，build_render_state() 输出快照
PowerSyncUI           视图，通过 ctrl 引用读写状态，render_visuals(rs) 消费 RenderState
QTimer                每 33ms 驱动主循环
"""

import os
import tempfile

os.environ.setdefault(
    "MPLCONFIGDIR",
    os.path.join(tempfile.gettempdir(), "matplotlib_threephase"),
)

import sys
import random
import traceback
import time
from copy import deepcopy

# 将项目根目录加入 sys.path，确保 domain/services/ui 包可以被找到
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5 import QtWidgets, QtCore

from domain.assessment import AssessmentContext
from domain.constants import DEFAULT_PT_RATIO_ROWS, GRID_AMP
from domain.models import GeneratorState, SimulationState, FaultConfig
from domain.phase_order_state import PhaseOrderState
from app.controller_signals import ControllerSignals
from services.assessment_service import AssessmentService
from services.assessment_coordinator import AssessmentCoordinator
from services.blackbox_repair_handler import BlackboxRepairHandler
from services.fault_manager import FaultManager
from services.hardware_actions import HardwareActions
from services.physics_engine import PhysicsEngine
from services.loop_test_service import LoopTestService
from services.pt_voltage_check_service import PtVoltageCheckService
from services.pt_phase_check_service import PtPhaseCheckService
from services.pt_exam_service import PtExamService
from services.sync_test_service import SyncTestService
from services.flow_mode_manager import FlowModeManager
from services.phase_order_resolver import PhaseOrderResolver
from ui.main_window import PowerSyncUI


class PowerSyncController:
    """
    编排层控制器。
    持有 sim_state（唯一数据源）、四个业务服务、physics 和 ui。
    所有测试业务逻辑委托给对应 Service；控制器只保留：
      · 状态字典的所有权（供 UI 直接读取）
      · PT 节点解析辅助（供 physics 与 UI 侧桥接调用）
      · 硬件控制动作（toggle_engine / toggle_breaker 等）
      · loop_test_mode 开关（跨步骤共用）
    """

    _TICK_FAILURE_THRESHOLD = 5

    def __init__(self):
        # ── 随机初始状态 ──────────────────────────────────────────────────
        init_amp1   = round(random.uniform(9500.0, 11500.0), 1)
        init_phase1 = round(random.uniform(-180.0, 180.0), 1)
        init_freq1  = round(random.uniform(48.0, 52.0), 1)
        init_amp2   = round(random.uniform(9500.0, 11500.0), 1)
        init_phase2 = round(random.uniform(-180.0, 180.0), 1)
        init_freq2  = round(random.uniform(48.0, 52.0), 1)

        # ── 唯一数据源 ────────────────────────────────────────────────────
        self.sim_state = SimulationState(
            gen1=GeneratorState(freq=init_freq1, amp=init_amp1, phase_deg=init_phase1),
            gen2=GeneratorState(freq=init_freq2, amp=init_amp2, phase_deg=init_phase2),
        )

        self.phase_order_state = PhaseOrderState.default()
        self.flow_mgr = FlowModeManager()
        self.signals = ControllerSignals()
        self._last_reported_test_step = 1
        self.test_flow_mode = 'teaching'
        self.assessment_session = None
        self._last_fault_detected = False
        self._pending_accident_scene_id = None
        self._pending_ui_tab_index = None
        self._pending_pt_ratio_row_updates = {}
        self._consecutive_tick_failures = 0
        self._tick_error_notified = False
        self._last_tick_perf = time.perf_counter()
        self._test_entry_state_snapshot = None

        # ── 业务服务（显式构造注入；controller 保留状态所有权与桥接辅助）───
        self.assessment_svc       = AssessmentService()
        self.assessment_coord     = AssessmentCoordinator(
            sim_state=self.sim_state,
            flow_mgr=self.flow_mgr,
            assessment_svc=self.assessment_svc,
            get_fault_mgr=lambda: self.fault_mgr,
            get_assessment_session=lambda: self.assessment_session,
            set_assessment_session=lambda session: setattr(self, 'assessment_session', session),
            set_last_fault_detected=lambda v: setattr(self, '_last_fault_detected', v),
            get_loop_test_state=lambda: self.loop_test_state,
            get_pt_voltage_check_state=lambda: self.pt_voltage_check_state,
            get_pt_phase_check_state=lambda: self.pt_phase_check_state,
            get_pt_exam_states=lambda: self.pt_exam_states,
            get_g1_blackbox_order=lambda: self.g1_blackbox_order,
            get_g2_blackbox_order=lambda: self.g2_blackbox_order,
            get_pt1_pri_blackbox_order=lambda: self.pt1_pri_blackbox_order,
            get_pt1_sec_blackbox_order=lambda: self.pt1_sec_blackbox_order,
            is_loop_test_complete=lambda: self.loop_svc.is_loop_test_complete(),
            is_pt_voltage_check_complete=lambda: self.pt_voltage_svc.is_pt_voltage_check_complete(),
            is_pt_phase_check_complete=lambda: self.pt_phase_svc.is_pt_phase_check_complete(),
            build_assessment_context=lambda snapshot: AssessmentContext.from_snapshot_and_ctrl(snapshot, self),
        )
        self.blackbox_handler     = BlackboxRepairHandler(
            sim_state=self.sim_state,
            flow_mgr=self.flow_mgr,
            get_fault_mgr=lambda: self.fault_mgr,
            append_assessment_event=self.assessment_coord.append_assessment_event,
            get_pt_phase_orders=lambda: self.pt_phase_orders,
            get_g1_blackbox_order=lambda: self.g1_blackbox_order,
            set_g1_blackbox_order=lambda val: setattr(self, 'g1_blackbox_order', val),
            get_g2_blackbox_order=lambda: self.g2_blackbox_order,
            set_g2_blackbox_order=lambda val: setattr(self, 'g2_blackbox_order', val),
            get_pt1_pri_blackbox_order=lambda: self.pt1_pri_blackbox_order,
            set_pt1_pri_blackbox_order=lambda val: setattr(self, 'pt1_pri_blackbox_order', val),
            get_pt1_sec_blackbox_order=lambda: self.pt1_sec_blackbox_order,
            set_pt1_sec_blackbox_order=lambda val: setattr(self, 'pt1_sec_blackbox_order', val),
            apply_g2_blackbox_to_pt3=self.phase_order_state.apply_g2_blackbox_to_pt3,
            apply_pt1_blackbox_to_pt_phases=self.phase_order_state.apply_pt1_blackbox_to_pt_phases,
        )
        self.phase_resolver       = PhaseOrderResolver(
            sim_state=self.sim_state,
            get_pt_phase_orders=lambda: self.pt_phase_orders,
            get_g2_blackbox_order=lambda: self.g2_blackbox_order,
        )
        self.hw                   = HardwareActions(
            sim_state=self.sim_state,
            get_physics=lambda: self.physics,
            is_loop_test_complete=lambda: self.loop_svc.is_loop_test_complete(),
            is_pt_voltage_check_complete=lambda: self.pt_voltage_svc.is_pt_voltage_check_complete(),
            is_pt_phase_check_complete=lambda: self.pt_phase_svc.is_pt_phase_check_complete(),
            is_pt_exam_recorded=lambda gen_id: self.pt_exam_svc.is_pt_exam_recorded(gen_id),
            is_sync_test_complete=lambda: self.sync_svc.is_sync_test_complete(),
            is_sync_test_active=lambda: self.is_sync_test_active(),
            is_pt_exam_started=lambda gen_id: self.pt_exam_states[gen_id].started,
            append_assessment_event=self.assessment_coord.append_assessment_event,
            set_pt_exam_feedback=lambda gen_id, msg, color: self.pt_exam_svc._set_pt_exam_feedback(gen_id, msg, color),
            request_ui_tab=self.request_ui_tab,
            show_warning=lambda title, msg: self.ui.show_warning(title, msg),
            show_e01_accident_dialog=lambda: self.ui.show_e01_accident_dialog(),
            show_e02_accident_dialog=lambda: self.ui.show_e02_accident_dialog(),
            show_e03_accident_dialog=lambda: self.ui.show_e03_accident_dialog(),
        )
        self.fault_mgr            = FaultManager(
            sim_state=self.sim_state,
            blackbox_handler=self.blackbox_handler,
            append_assessment_event=self.assessment_coord.append_assessment_event,
            request_pt_ratio_row_update=self.request_pt_ratio_row_update,
            set_last_fault_detected=lambda v: setattr(self, '_last_fault_detected', v),
            get_pt_phase_orders=lambda: self.pt_phase_orders,
            get_g1_blackbox_order=lambda: self.g1_blackbox_order,
            set_g1_blackbox_order=lambda val: setattr(self, 'g1_blackbox_order', val),
            get_g2_blackbox_order=lambda: self.g2_blackbox_order,
            set_g2_blackbox_order=lambda val: setattr(self, 'g2_blackbox_order', val),
            get_pt1_pri_blackbox_order=lambda: self.pt1_pri_blackbox_order,
            set_pt1_pri_blackbox_order=lambda val: setattr(self, 'pt1_pri_blackbox_order', val),
            get_pt1_sec_blackbox_order=lambda: self.pt1_sec_blackbox_order,
            set_pt1_sec_blackbox_order=lambda val: setattr(self, 'pt1_sec_blackbox_order', val),
        )
        self.loop_svc             = LoopTestService(
            sim_state=self.sim_state,
            flow_mgr=self.flow_mgr,
            get_physics=lambda: self.physics,
            get_loop_test_state=lambda: self.loop_test_state,
            set_loop_test_state=lambda state: setattr(self, 'loop_test_state', state),
            append_assessment_event=self.assessment_coord.append_assessment_event,
            exit_loop_test_mode=self.exit_loop_test_mode,
            mark_fault_detected=self.assessment_coord.mark_fault_detected,
        )
        self.pt_voltage_svc       = PtVoltageCheckService(
            sim_state=self.sim_state,
            flow_mgr=self.flow_mgr,
            get_physics=lambda: self.physics,
            get_pt_voltage_check_state=lambda: self.pt_voltage_check_state,
            set_pt_voltage_check_state=lambda state: setattr(self, 'pt_voltage_check_state', state),
            is_loop_test_complete=lambda: self.loop_svc.is_loop_test_complete(),
            append_assessment_event=self.assessment_coord.append_assessment_event,
        )
        self.pt_phase_svc         = PtPhaseCheckService(
            sim_state=self.sim_state,
            flow_mgr=self.flow_mgr,
            get_physics=lambda: self.physics,
            get_pt_phase_check_state=lambda: self.pt_phase_check_state,
            set_pt_phase_check_state=lambda state: setattr(self, 'pt_phase_check_state', state),
            is_loop_test_complete=lambda: self.loop_svc.is_loop_test_complete(),
            is_pt_voltage_check_complete=lambda: self.pt_voltage_svc.is_pt_voltage_check_complete(),
            append_assessment_event=self.assessment_coord.append_assessment_event,
            mark_fault_detected=self.assessment_coord.mark_fault_detected,
            set_pt_phase_check_feedback=self.set_pt_phase_check_feedback,
            mark_pt_phase_check_completed=self.mark_pt_phase_check_completed,
        )
        self.pt_exam_svc          = PtExamService(
            sim_state=self.sim_state,
            flow_mgr=self.flow_mgr,
            get_physics=lambda: self.physics,
            get_pt_exam_states=lambda: self.pt_exam_states,
            is_loop_test_complete=lambda: self.loop_svc.is_loop_test_complete(),
            is_pt_voltage_check_complete=lambda: self.pt_voltage_svc.is_pt_voltage_check_complete(),
            is_pt_phase_check_complete=lambda: self.pt_phase_svc.is_pt_phase_check_complete(),
            append_assessment_event=self.assessment_coord.append_assessment_event,
        )
        self.sync_svc             = SyncTestService(
            sim_state=self.sim_state,
            flow_mgr=self.flow_mgr,
            fault_mgr=self.fault_mgr,
            get_physics=lambda: self.physics,
            get_sync_test_state=lambda: self.sync_test_state,
            set_sync_test_state=lambda state: setattr(self, 'sync_test_state', state),
            is_loop_test_complete=lambda: self.loop_svc.is_loop_test_complete(),
            is_pt_voltage_check_complete=lambda: self.pt_voltage_svc.is_pt_voltage_check_complete(),
            is_pt_phase_check_complete=lambda: self.pt_phase_svc.is_pt_phase_check_complete(),
            is_pt_exam_recorded=lambda gen_id: self.pt_exam_svc.is_pt_exam_recorded(gen_id),
        )

        # ── 状态 dataclass（UI 直接读取，服务通过显式注入回写）──────────
        self.loop_test_state         = self.loop_svc.create_loop_test_state()
        self.pt_voltage_check_state  = self.pt_voltage_svc.create_pt_voltage_check_state()
        self.pt_phase_check_state    = self.pt_phase_svc.create_pt_phase_check_state()
        self.pt_exam_states          = {
            1: self.pt_exam_svc.create_pt_exam_state(),
            2: self.pt_exam_svc.create_pt_exam_state(),
        }
        self.sync_test_state         = self.sync_svc.create_sync_test_state()

        # ── 物理引擎 ──────────────────────────────────────────────────────
        self.physics = PhysicsEngine(
            sim_state=self.sim_state,
            flow_mgr=self.flow_mgr,
            phase_resolver=self.phase_resolver,
            sync_svc=self.sync_svc,
            get_pt_phase_orders=lambda: self.pt_phase_orders,
            get_loop_test_state=lambda: self.loop_test_state,
            get_pt_voltage_check_state=lambda: self.pt_voltage_check_state,
            is_sync_test_active=self.is_sync_test_active,
            mark_fault_detected=self.assessment_coord.mark_fault_detected,
            queue_accident_dialog=self.queue_accident_dialog,
        )

        # ── UI 窗口 ───────────────────────────────────────────────────────
        self.ui = PowerSyncUI(self)

        # ── 主循环定时器（33ms ≈ 30fps）──────────────────────────────────
        self._timer = QtCore.QTimer()
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    @property
    def pt_phase_orders(self):
        return self.phase_order_state.pt_phase_orders

    @pt_phase_orders.setter
    def pt_phase_orders(self, value):
        incoming = value or {}
        for pt_name in ("PT1", "PT2", "PT3"):
            next_order = list(incoming.get(pt_name, ["A", "B", "C"]))
            current_order = self.phase_order_state.pt_phase_orders.get(pt_name)
            if isinstance(current_order, list):
                current_order[:] = next_order
            else:
                self.phase_order_state.pt_phase_orders[pt_name] = next_order

    @property
    def g1_blackbox_order(self):
        return self.phase_order_state.g1_blackbox_order

    @g1_blackbox_order.setter
    def g1_blackbox_order(self, value):
        self.phase_order_state.g1_blackbox_order[:] = list(value)

    @property
    def g2_blackbox_order(self):
        return self.phase_order_state.g2_blackbox_order

    @g2_blackbox_order.setter
    def g2_blackbox_order(self, value):
        self.phase_order_state.g2_blackbox_order[:] = list(value)

    @property
    def pt1_pri_blackbox_order(self):
        return self.phase_order_state.pt1_pri_blackbox_order

    @pt1_pri_blackbox_order.setter
    def pt1_pri_blackbox_order(self, value):
        self.phase_order_state.pt1_pri_blackbox_order[:] = list(value)

    @property
    def pt1_sec_blackbox_order(self):
        return self.phase_order_state.pt1_sec_blackbox_order

    @pt1_sec_blackbox_order.setter
    def pt1_sec_blackbox_order(self, value):
        self.phase_order_state.pt1_sec_blackbox_order[:] = list(value)

    @property
    def test_flow_mode(self):
        return self.flow_mgr.test_flow_mode

    @test_flow_mode.setter
    def test_flow_mode(self, value: str):
        old_is_assessment = self.flow_mgr.is_assessment_mode()
        self.flow_mgr.test_flow_mode = value
        new_is_assessment = self.flow_mgr.is_assessment_mode()
        if old_is_assessment != new_is_assessment:
            self.signals.assessment_mode_changed.emit(new_is_assessment)

    def _emit_step_changed_if_needed(self, new_step: int):
        old_step = self._last_reported_test_step
        if new_step == old_step:
            return
        self._last_reported_test_step = new_step
        self.signals.step_changed.emit(old_step, new_step)

    def update_pt_ratio(self, ratio_attr: str, ratio: float):
        if ratio_attr not in {'pt_gen_ratio', 'pt3_ratio', 'pt_bus_ratio'}:
            raise ValueError(f"Unsupported PT ratio attribute: {ratio_attr}")
        setattr(self.sim_state, ratio_attr, ratio)
        repaired = self.fault_mgr.maybe_repair_pt_ratio_fault(
            ratio_attr,
            ratio,
            step=2,
            source=f'{ratio_attr}_panel',
        )
        if repaired:
            self._reset_fault_affected_records_after_repair(self.sim_state.fault_config.scenario_id)

    def _reset_fault_affected_records_after_repair(self, scenario_id: str) -> None:
        if scenario_id not in ('E03', 'E04'):
            return

        voltage_state = self.pt_voltage_check_state
        for key in ('PT3_AB', 'PT3_BC', 'PT3_CA'):
            voltage_state.records[key] = None
        voltage_state.completed = False
        voltage_state.feedback = "PT3 故障已修复，请重新测量并记录 PT3 三组线电压。"
        voltage_state.feedback_color = '#0369a1'

        phase_state = self.pt_phase_check_state
        phase_state.records['PT3'] = None
        phase_state.completed = False
        phase_state.result = None
        phase_state.feedback = "PT3 故障已修复，请重新记录 PT3 相序。"
        phase_state.feedback_color = '#0369a1'

        pt3_exam_state = self.pt_exam_states[2]
        for key in pt3_exam_state.records:
            pt3_exam_state.records[key] = None
        pt3_exam_state.completed = False
        pt3_exam_state.feedback = "PT3 故障已修复，请重新完成 Gen2/PT3 压差测量。"
        pt3_exam_state.feedback_color = '#0369a1'

        if scenario_id == 'E03':
            self.sync_test_state = self.sync_svc.create_sync_test_state()

    def reset_pt_ratios_to_defaults(self):
        for ratio_attr, (pri_value, sec_value) in DEFAULT_PT_RATIO_ROWS.items():
            setattr(self.sim_state, ratio_attr, pri_value / sec_value)
            self.request_pt_ratio_row_update(ratio_attr, pri_value, sec_value)

    def capture_test_entry_state(self):
        """保存进入测试前的完整运行态，用于退出测试时恢复原状。"""
        if self._test_entry_state_snapshot is not None:
            return
        self._test_entry_state_snapshot = {
            "sim_state": deepcopy(self.sim_state),
            "phase_order_state": deepcopy(self.phase_order_state),
            "loop_test_state": deepcopy(self.loop_test_state),
            "pt_voltage_check_state": deepcopy(self.pt_voltage_check_state),
            "pt_phase_check_state": deepcopy(self.pt_phase_check_state),
            "pt_exam_states": deepcopy(self.pt_exam_states),
            "sync_test_state": deepcopy(self.sync_test_state),
            "test_flow_mode": self.test_flow_mode,
            "assessment_session": deepcopy(self.assessment_session),
            "last_fault_detected": self._last_fault_detected,
            "pending_accident_scene_id": self._pending_accident_scene_id,
            "pending_ui_tab_index": self._pending_ui_tab_index,
            "pending_pt_ratio_row_updates": deepcopy(self._pending_pt_ratio_row_updates),
            "last_reported_test_step": self._last_reported_test_step,
        }

    def restore_test_entry_state(self):
        """退出测试时恢复进入测试前的仿真、步骤、故障和考核状态。"""
        snapshot = self._test_entry_state_snapshot
        if snapshot is None:
            return

        saved_sim = deepcopy(snapshot["sim_state"])
        self.sim_state.__dict__.clear()
        self.sim_state.__dict__.update(saved_sim.__dict__)

        saved_phase = snapshot["phase_order_state"]
        for pt_name, order in saved_phase.pt_phase_orders.items():
            self.phase_order_state.pt_phase_orders[pt_name][:] = list(order)
        self.phase_order_state.g1_blackbox_order[:] = list(saved_phase.g1_blackbox_order)
        self.phase_order_state.g2_blackbox_order[:] = list(saved_phase.g2_blackbox_order)
        self.phase_order_state.pt1_pri_blackbox_order[:] = list(saved_phase.pt1_pri_blackbox_order)
        self.phase_order_state.pt1_sec_blackbox_order[:] = list(saved_phase.pt1_sec_blackbox_order)

        self.loop_test_state = deepcopy(snapshot["loop_test_state"])
        self.pt_voltage_check_state = deepcopy(snapshot["pt_voltage_check_state"])
        self.pt_phase_check_state = deepcopy(snapshot["pt_phase_check_state"])
        self.pt_exam_states = deepcopy(snapshot["pt_exam_states"])
        self.sync_test_state = deepcopy(snapshot["sync_test_state"])

        self.test_flow_mode = snapshot["test_flow_mode"]
        self.assessment_session = deepcopy(snapshot["assessment_session"])
        self._last_fault_detected = snapshot["last_fault_detected"]
        self._pending_accident_scene_id = snapshot["pending_accident_scene_id"]
        self._pending_ui_tab_index = snapshot["pending_ui_tab_index"]
        self._pending_pt_ratio_row_updates = deepcopy(snapshot["pending_pt_ratio_row_updates"])
        self._last_reported_test_step = snapshot["last_reported_test_step"]
        self._test_entry_state_snapshot = None

        try:
            self.rebuild_circuit_view()
        except Exception:
            traceback.print_exc()

    def get_pt_phase_sequence(self, pt_name):
        return self.phase_resolver.get_pt_phase_sequence(pt_name)

    def is_assessment_mode(self):
        return self.flow_mgr.is_assessment_mode()

    def allow_admin_shortcuts(self):
        return self.flow_mgr.allow_admin_shortcuts()

    def can_use_pt_exam_quick_record(self):
        return self.flow_mgr.can_use_pt_exam_quick_record()

    def should_show_fault_detected_banner(self):
        return self.flow_mgr.should_show_fault_detected_banner()

    def can_advance_with_fault(self):
        return self.flow_mgr.can_advance_with_fault()

    def should_hold_at_step4_when_wiring_fault_unrepaired(self):
        return self.flow_mgr.should_hold_at_step4_when_wiring_fault_unrepaired()

    def has_unrepaired_wiring_fault(self):
        return self.fault_mgr.has_unrepaired_wiring_fault()

    def can_inspect_blackbox(self):
        return self.flow_mgr.can_inspect_blackbox()

    def can_repair_in_blackbox(self):
        return self.flow_mgr.can_repair_in_blackbox()

    def start_assessment_session(self, scenario_id: str, *, preset_mode: str):
        return self.assessment_coord.start_assessment_session(scenario_id, preset_mode=preset_mode)

    def append_assessment_event(self, event_type, **kwargs):
        return self.assessment_coord.append_assessment_event(event_type, **kwargs)

    def get_test_progress_snapshot(self, step: int, pre_step5_repair_triggered: bool):
        self._emit_step_changed_if_needed(step)
        return self.assessment_coord.get_test_progress_snapshot(step, pre_step5_repair_triggered)

    def finish_assessment_session_if_ready(self, step: int):
        return self.assessment_coord.finish_assessment_session_if_ready(step)

    def mark_assessment_result_shown(self):
        return self.assessment_coord.mark_assessment_result_shown()

    def submit_random_fault_identification(self, scene_id: str):
        return self.assessment_coord.submit_random_fault_identification(scene_id)

    def get_blackbox_runtime_state(self, target: str):
        return self.blackbox_handler.get_blackbox_runtime_state(target)

    def apply_blackbox_repair_attempt(self, *args, **kwargs):
        outcome = self.blackbox_handler.apply_blackbox_repair_attempt(*args, **kwargs)
        if getattr(outcome, 'fault_cleared', False):
            self._reset_fault_affected_records_after_repair(self.sim_state.fault_config.scenario_id)
        return outcome

    def toggle_engine(self, gen_id: int):
        return self.hw.toggle_engine(gen_id)

    def toggle_breaker(self, gen_id: int):
        return self.hw.toggle_breaker(gen_id)

    def request_ui_tab(self, tab_index: int):
        self._pending_ui_tab_index = tab_index

    def consume_requested_ui_tab(self):
        tab_index = self._pending_ui_tab_index
        self._pending_ui_tab_index = None
        return tab_index

    def request_pt_ratio_row_update(self, ratio_attr: str, pri_value: int, sec_value: int):
        self._pending_pt_ratio_row_updates[ratio_attr] = (pri_value, sec_value)

    def consume_requested_pt_ratio_row_updates(self):
        updates = dict(self._pending_pt_ratio_row_updates)
        self._pending_pt_ratio_row_updates.clear()
        return updates

    # ════════════════════════════════════════════════════════════════════════
    # 小型辅助（被 UI 或多个服务直接调用）
    # ════════════════════════════════════════════════════════════════════════
    def _get_generator_state(self, gen_id):
        return self.sim_state.gen1 if gen_id == 1 else self.sim_state.gen2

    def set_pt_phase_check_feedback(self, message, color='#444444'):
        self.pt_phase_check_state.feedback = message
        self.pt_phase_check_state.feedback_color = color

    def mark_pt_phase_check_completed(self):
        self.pt_phase_check_state.completed = True

    # ════════════════════════════════════════════════════════════════════════
    # 第一步：回路连通性测试 — 委托给 LoopTestService
    # ════════════════════════════════════════════════════════════════════════
    def record_loop_measurement(self, pair):
        self.loop_svc.record_loop_measurement(pair, origin="simulated")

    def finalize_loop_test(self):
        self.loop_svc.finalize_loop_test()

    def reset_loop_test(self):
        self.loop_svc.reset_loop_test()
        self.exit_loop_test_mode()

    def enter_loop_test_mode(self):
        """进入第一步回路检查模式：跳过失压联锁，允许不起机合闸。"""
        self.sim_state.loop_test_mode = True

    def get_loop_test_steps(self):
        return self.loop_svc.get_loop_test_steps()

    def get_current_loop_phase_match(self):
        return self.loop_svc._get_current_loop_phase_match()

    def get_current_loop_pair(self):
        return self.loop_svc.get_current_loop_pair()

    def is_loop_test_complete(self):
        return self.loop_svc.is_loop_test_complete()

    def exit_loop_test_mode(self):
        """退出第一步回路检查模式：恢复失压联锁保护，未起机或未建压的断路器自动断开。"""
        self.sim_state.loop_test_mode = False
        # 失压联锁：未起机 或 电压幅值低于 20% 额定（仿真中未励磁/未起机均满足此条件）
        _voltage_threshold = GRID_AMP * 0.2
        for gen in (self.sim_state.gen1, self.sim_state.gen2):
            if gen.breaker_closed and (not gen.running or gen.amp < _voltage_threshold):
                gen.breaker_closed = False
    # ════════════════════════════════════════════════════════════════════════
    # 第二步：PT 单体线电压检查 — 委托给 PtVoltageCheckService
    # ════════════════════════════════════════════════════════════════════════
    def record_pt_voltage_measurement(self, pt_name, phase_pair):
        self.pt_voltage_svc.record_pt_voltage_measurement(pt_name, phase_pair, origin="simulated")

    def finalize_pt_voltage_check(self):
        self.pt_voltage_svc.finalize_pt_voltage_check()

    def reset_pt_voltage_check(self):
        self.pt_voltage_svc.reset_pt_voltage_check()

    def start_pt_voltage_check(self):
        self.pt_voltage_svc.start_pt_voltage_check()

    def stop_pt_voltage_check(self):
        self.pt_voltage_svc.stop_pt_voltage_check()

    def get_pt_voltage_check_steps(self):
        return self.pt_voltage_svc.get_pt_voltage_check_steps()

    def is_pt_voltage_check_complete(self):
        return self.pt_voltage_svc.is_pt_voltage_check_complete()

    # ════════════════════════════════════════════════════════════════════════
    # 第三步：PT 相序检查 — 委托给 PtPhaseCheckService
    # ════════════════════════════════════════════════════════════════════════
    def record_pt_phase_check(self, pt_name, phase):
        self.pt_phase_svc.record_pt_phase_check(pt_name, phase)

    def finalize_pt_phase_check(self):
        self.pt_phase_svc.finalize_pt_phase_check()

    def start_pt_phase_check(self):
        self.pt_phase_svc.start_pt_phase_check()

    def stop_pt_phase_check(self):
        self.pt_phase_svc.stop_pt_phase_check()

    def reset_pt_phase_check(self):
        self.pt_phase_svc.reset_pt_phase_check()

    def get_pt_phase_check_steps(self):
        return self.pt_phase_svc.get_pt_phase_check_steps()

    def is_pt_phase_check_complete(self):
        return self.pt_phase_svc.is_pt_phase_check_complete()

    def record_phase_sequence(self, pt_name: str, seq: str):
        return self.pt_phase_svc.record_phase_sequence(pt_name, seq, origin="simulated")

    # ════════════════════════════════════════════════════════════════════════
    # 第四步：PT 二次端子压差考核 — 委托给 PtExamService
    # ════════════════════════════════════════════════════════════════════════
    def reset_pt_exam(self, gen_id=None):
        self.pt_exam_svc.reset_pt_exam(gen_id)

    def record_pt_diff_measurement(self, gen_id, gen_phase, bus_phase):
        self.pt_exam_svc.record_pt_diff_measurement(gen_id, gen_phase, bus_phase, origin="simulated")

    def record_current_pt_measurement(self, gen_id):
        """记录当前表笔位置对应的 PT 压差（由测试面板"记录当前"按钮调用）。"""
        matched = self.pt_exam_svc._get_current_pt_phase_match(gen_id)
        if matched is None:
            self.pt_exam_svc._set_pt_exam_feedback(
                gen_id, "表笔未放置在有效 PT 端子上，请在母排拓扑页放置表笔后再记录。", "red")
            return
        self.pt_exam_svc.record_pt_diff_measurement(gen_id, matched[0], matched[1], origin="simulated")

    def finalize_all_pt_exams(self):
        self.pt_exam_svc.finalize_all_pt_exams()

    def record_all_pt_measurements_quick(self):
        self.pt_exam_svc.record_all_pt_measurements_quick()

    def start_pt_exam(self, gen_id):
        self.pt_exam_svc.start_pt_exam(gen_id)

    def stop_pt_exam(self, gen_id):
        self.pt_exam_svc.stop_pt_exam(gen_id)

    def get_pt_exam_steps(self, gen_id):
        return self.pt_exam_svc.get_pt_exam_steps(gen_id)

    def get_generator_state(self, gen_id):
        return self._get_generator_state(gen_id)

    def get_current_pt_exam_phase_match(self, gen_id):
        return self.pt_exam_svc._get_current_pt_phase_match(gen_id)

    # ════════════════════════════════════════════════════════════════════════
    # 第五步：同步功能测试 — 委托给 SyncTestService
    # ════════════════════════════════════════════════════════════════════════
    def record_sync_round(self, round_num):
        self.sync_svc.record_sync_round(round_num)

    def is_sync_test_active(self):
        """同步测试已开始但尚未最终完成——此期间屏蔽自动合闸。"""
        return self.sync_test_state.started and not self.sync_test_state.completed

    def finalize_sync_test(self):
        was_completed = self.sync_svc.is_sync_test_complete()
        self.sync_svc.finalize_sync_test()
        if not was_completed and self.sync_svc.is_sync_test_complete():
            self.physics.reset_wave_history()

    def reset_sync_test(self):
        self.sync_svc.reset_sync_test()

    def start_sync_test(self):
        self.sync_svc.start_sync_test()

    def stop_sync_test(self):
        self.sync_svc.stop_sync_test()

    def get_sync_test_steps(self):
        return self.sync_svc.get_sync_test_steps()

    def is_sync_test_complete(self):
        return self.sync_svc.is_sync_test_complete()

    def is_gen_synced(self, gen_a, gen_b):
        return self.sync_svc.is_gen_synced(gen_a, gen_b)

    def queue_accident_dialog(self, scene_id: str):
        if self._pending_accident_scene_id is None:
            self._pending_accident_scene_id = scene_id

    def _consume_pending_accident_dialog(self):
        scene_id = self._pending_accident_scene_id
        self._pending_accident_scene_id = None
        if scene_id == 'E01':
            self.ui.show_e01_accident_dialog()
        elif scene_id == 'E02':
            self.ui.show_e02_accident_dialog()
        elif scene_id == 'E03':
            self.ui.show_e03_accident_dialog()

    def _handle_tick_failure(self, stage: str):
        self._consecutive_tick_failures += 1
        traceback.print_exc()
        if self._consecutive_tick_failures == 3 and not self._tick_error_notified:
            self.ui.statusBar().showMessage(
                f"物理帧更新连续失败 {self._consecutive_tick_failures} 次（阶段: {stage}），请检查控制台错误日志。"
            )
            self._tick_error_notified = True
        if (
            self._consecutive_tick_failures >= self._TICK_FAILURE_THRESHOLD
            and self._timer.isActive()
        ):
            self._timer.stop()
            self.ui.statusBar().showMessage(
                f"物理引擎已熔断停止（阶段: {stage}，连续失败 {self._consecutive_tick_failures} 次）。"
            )

    def _clear_tick_failure_state(self):
        if self._consecutive_tick_failures > 0:
            self.ui.statusBar().clearMessage()
        self._consecutive_tick_failures = 0
        self._tick_error_notified = False

    def toggle_pause(self):
        self.sim_state.paused = not self.sim_state.paused
        self.ui.pause_btn.setText(
            "▶ 恢复物理时空" if self.sim_state.paused else "⏸ 暂停整个物理空间"
        )
        self.ui._apply_button_tone(
            self.ui.pause_btn,
            "success" if self.sim_state.paused else "warning",
            hero=True,
        )

    def reset_blackbox_orders(self):
        self.phase_order_state.reset_blackbox_orders()

    def rebuild_circuit_view(self):
        self.ui.rebuild_circuit_diagram()

    # ════════════════════════════════════════════════════════════════════════
    # 故障训练模式（FaultConfig 管理）
    # ════════════════════════════════════════════════════════════════════════
    def inject_fault(self, scenario_id: str):
        self.fault_mgr.inject_fault(scenario_id)

    def repair_fault(self, step: int = 4, source: str = 'repair_fault'):
        self.fault_mgr.repair_fault(step=step, source=source)

    def reset_for_scenario(self, scenario_id: str):
        """
        完整重置：停机 → 清空所有测试状态 → 注入新故障。
        管理员选定场景后调用，学员在全新状态下开始训练。
        """
        sim = self.sim_state
        # 1. 停止发电机，断路器复位
        sim.gen1.running = False
        sim.gen2.running = False
        sim.gen1.breaker_closed = False
        sim.gen2.breaker_closed = False
        sim.gen1.cmd_close = False
        sim.gen2.cmd_close = False
        sim.loop_test_mode = False

        # 2. 重置所有步骤状态
        self.loop_test_state        = self.loop_svc.create_loop_test_state()
        self.pt_voltage_check_state = self.pt_voltage_svc.create_pt_voltage_check_state()
        self.pt_phase_check_state   = self.pt_phase_svc.create_pt_phase_check_state()
        self.pt_exam_states = {
            1: self.pt_exam_svc.create_pt_exam_state(),
            2: self.pt_exam_svc.create_pt_exam_state(),
        }
        self.sync_test_state = self.sync_svc.create_sync_test_state()

        # 3. 恢复 PT 相序与默认变比（inject_fault 会再按场景设置）
        self.phase_order_state.reset_pt_phase_orders()
        self.phase_order_state.reset_blackbox_orders()
        self.reset_pt_ratios_to_defaults()
        self.sim_state.fault_reverse_bc = False

        # 4. 注入新故障
        self.inject_fault(scenario_id)
        self._last_fault_detected = False

        # 5. 刷新电路图
        try:
            self.rebuild_circuit_view()
        except Exception:
            traceback.print_exc()

    # ════════════════════════════════════════════════════════════════════════
    # 主循环（QTimer 每 33ms 触发）
    # ════════════════════════════════════════════════════════════════════════
    def _tick(self):
        now_perf = time.perf_counter()
        frame_dt = max(0.0, now_perf - self._last_tick_perf)
        self._last_tick_perf = now_perf
        try:
            self.physics.frame_dt = frame_dt
            self.physics.update_physics()
            fc = self.sim_state.fault_config
            self._last_fault_detected = bool(fc.detected)
            rs = self.physics.build_render_state()
        except Exception:
            self._handle_tick_failure("physics")
            return

        try:
            self.ui.render_visuals(rs)
            self._consume_pending_accident_dialog()
            self._clear_tick_failure_state()
        except Exception:
            self._handle_tick_failure("render")


# ════════════════════════════════════════════════════════════════════════════
# 程序入口
# ════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    # Windows HiDPI
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass

    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")

    ctrl = PowerSyncController()
    ctrl.ui.showMaximized()

    sys.exit(app.exec_())
