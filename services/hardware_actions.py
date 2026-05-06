from __future__ import annotations

import math
from typing import Callable, Protocol

from domain.assessment import AssessmentEventType
from domain.constants import GRID_FREQ, GRID_AMP
from domain.enums import BreakerPosition
from domain.models import GeneratorState, SimulationState


class _PhysicsBusView(Protocol):
    bus_live: bool
    bus_phase: float
    bus_reference_gen: int | None


class HardwareActions:
    def __init__(
        self,
        *,
        sim_state: SimulationState,
        get_physics: Callable[[], _PhysicsBusView],
        is_loop_test_complete: Callable[[], bool],
        is_pt_voltage_check_complete: Callable[[], bool],
        is_pt_phase_check_complete: Callable[[], bool],
        is_pt_exam_recorded: Callable[[int], bool],
        is_sync_test_complete: Callable[[], bool],
        is_sync_test_active: Callable[[], bool],
        is_pt_exam_started: Callable[[int], bool],
        append_assessment_event: Callable,
        set_pt_exam_feedback: Callable[[int, str, str], None],
        request_ui_tab: Callable[[int], None],
        show_warning: Callable[[str, str], None],
        show_e01_accident_dialog: Callable[[], None],
        show_e02_accident_dialog: Callable[[], None],
        show_e03_accident_dialog: Callable[[], None],
    ):
        self._sim_state = sim_state
        self._get_physics = get_physics
        self._is_loop_test_complete = is_loop_test_complete
        self._is_pt_voltage_check_complete = is_pt_voltage_check_complete
        self._is_pt_phase_check_complete = is_pt_phase_check_complete
        self._is_pt_exam_recorded = is_pt_exam_recorded
        self._is_sync_test_complete = is_sync_test_complete
        self._is_sync_test_active = is_sync_test_active
        self._is_pt_exam_started = is_pt_exam_started
        self._append_assessment_event = append_assessment_event
        self._set_pt_exam_feedback = set_pt_exam_feedback
        self._request_ui_tab = request_ui_tab
        self._show_warning = show_warning
        self._show_e01_accident_dialog = show_e01_accident_dialog
        self._show_e02_accident_dialog = show_e02_accident_dialog
        self._show_e03_accident_dialog = show_e03_accident_dialog

    def get_preclose_flow_blockers(self, gen_id) -> list[tuple[str, list[str]]]:
        sections = []
        loop_done = self._is_loop_test_complete()

        if not loop_done:
            # 第一步未完成：同时列出所有后续步骤，让用户一次看到全部要求
            sections.append(("第一步：回路连通性测试", ["三相回路连通性测试尚未完成"]))
            if not self._is_pt_voltage_check_complete():
                sections.append(("第二步：PT 单体线电压检查", ["PT1/PT2/PT3 线电压检查尚未完成"]))
            if not self._is_pt_phase_check_complete():
                sections.append(("第三步：PT 相序检查", ["PT1/PT3 相序检查尚未完成"]))
            if not self._is_pt_exam_recorded(2):
                sections.append(("第四步：PT 二次端子压差考核（Gen 2）",
                                 ["Gen 2 三相 PT 二次端子压差尚未全部记录"]))
            if not self._is_sync_test_complete() and not self._is_sync_test_active():
                sections.append(("第五步：同步功能测试",
                                 ["同步功能测试尚未完成（需完成两轮同步跟踪记录）"]))
        elif gen_id == 1:
            # Gen1 合闸：若母排已由 Gen2 供电，Gen1 也必须先完成同期测试
            physics = self._get_physics()
            bus_live = getattr(physics, 'bus_live', False)
            bus_ref = getattr(physics, 'bus_reference_gen', None)
            if bus_live and bus_ref == 2:
                if not self._is_sync_test_complete() and not self._is_sync_test_active():
                    sections.append(("第五步：同步功能测试",
                                     ["母排当前由 Gen 2 供电，Gen 1 合闸前需完成同步功能测试"]))
        elif gen_id == 2:
            # 第一步已完成；Gen1 已建立母排参考，Gen2 需完成第二至五步
            if not self._is_pt_voltage_check_complete():
                sections.append(("第二步：PT 单体线电压检查", ["PT1/PT2/PT3 线电压检查尚未完成"]))
            if not self._is_pt_phase_check_complete():
                sections.append(("第三步：PT 相序检查", ["PT1/PT3 相序检查尚未完成"]))
            if not self._is_pt_exam_recorded(2):
                sections.append(("第四步：PT 二次端子压差考核（Gen 2）",
                                 ["Gen 2 三相 PT 二次端子压差尚未全部记录"]))
            # 同步测试进行中（Gen2 需合闸作第二轮基准）不拦截
            if not self._is_sync_test_complete() and not self._is_sync_test_active():
                sections.append(("第五步：同步功能测试",
                                 ["同步功能测试尚未完成（需完成两轮同步跟踪记录）"]))
        return sections

    def _should_enforce_pt_exam_before_close(self) -> bool:
        return self._sim_state.grounding_mode != "断开"

    def _should_limit_close_to_selected_pt_target(self) -> bool:
        sim = self._sim_state
        return (
            sim.grounding_mode == "小电阻接地" and
            sim.gen1.mode == "manual" and
            sim.gen2.mode == "manual" and
            not self._is_sync_test_complete() and
            self._is_pt_exam_started(1)
        )

    def instant_sync(self) -> None:
        # 若母排已带电，相位必须跟随母排当前动态相角，不能强行清零
        # （bus_phase 由物理引擎实时维护，单位为弧度）
        physics = self._get_physics()
        if getattr(physics, 'bus_live', False):
            target_phase_deg = math.degrees(physics.bus_phase)
        else:
            target_phase_deg = 0.0   # 母排无电时建立参考，0° 合法
        for gen in (self._sim_state.gen1, self._sim_state.gen2):
            gen.freq = GRID_FREQ
            gen.amp = GRID_AMP
            gen.phase_deg = target_phase_deg

    def toggle_engine(self, gen_id: int) -> None:
        gen = self._get_generator_state(gen_id)
        if not gen.running and gen.mode != "manual":
            self._on_engine_blocked(
                gen_id,
                "起机条件不满足",
                f"Gen {gen_id} 只有在手动工作模式下才能起机。\n请先将工作模式切换为“手动”，再执行起机。"
            )
            return
        gen.running = not gen.running

    def _on_engine_blocked(self, gen_id: int, title: str, message: str) -> None:
        self._show_warning(title, message)

    def _on_breaker_blocked(self, gen_id: int, title: str, message: str) -> None:
        """合闸被拦截时的 UI 响应钩子。由 UI 层覆写以控制弹窗和 Tab 跳转。
        控制器本身只负责状态，不直接操作视图。"""
        self._request_ui_tab(5)
        self._show_warning(title, message)

    def toggle_breaker(self, gen_id: int) -> None:
        generator = self._get_generator_state(gen_id)
        if generator.breaker_closed:
            generator.breaker_closed = False
            return
        # ── 拦截：Gen1 考核期间禁止 Gen2 合闸 ─────────────────────────────
        if gen_id == 2 and self._should_limit_close_to_selected_pt_target():
            self._set_pt_exam_feedback(
                1,
                "当前第四步正在测试 Gen 1，请先完成 Gen 1 的 PT 二次端子压差测试，再合闸 Gen 2。",
                "red"
            )
            self._on_breaker_blocked(
                gen_id,
                "当前机组不允许合闸",
                "第四步 PT 测试当前锁定在 Gen 1。\n请先完成 Gen 1 的测试，再合闸 Gen 2。"
            )
            return
        # ── 拦截：E01/E02/E03 故障未修复时 Gen2 工作位合闸（仅第五步同步测试中）→ 并网事故 ──
        fc = self._sim_state.fault_config
        if (gen_id == 2
                and generator.breaker_position == BreakerPosition.WORKING
                and fc.active and not fc.repaired
                and self._is_sync_test_active()):
            if fc.scenario_id == 'E01':
                self._append_assessment_event(AssessmentEventType.HAZARD_ACTION, step=5, action='close_gen2_breaker', reason='E01 accident')
                self._show_e01_accident_dialog()
                return
            elif fc.scenario_id == 'E02':
                self._append_assessment_event(AssessmentEventType.HAZARD_ACTION, step=5, action='close_gen2_breaker', reason='E02 accident')
                self._show_e02_accident_dialog()
                return
            elif fc.scenario_id == 'E03':
                self._append_assessment_event(AssessmentEventType.HAZARD_ACTION, step=5, action='close_gen2_breaker', reason='E03 accident')
                self._show_e03_accident_dialog()
                return
        # ── 拦截：工作位合闸前置流程检查 ───────────────────────────────────
        if (generator.breaker_position == BreakerPosition.WORKING
                and self._should_enforce_pt_exam_before_close()):
            blocker_sections = self.get_preclose_flow_blockers(gen_id)
            if blocker_sections:
                msg_lines = ["隔离母排模式下合闸前流程尚未完成，当前不能合闸："]
                for section_title, items in blocker_sections:
                    msg_lines.append(f"\n{section_title}")
                    msg_lines.extend(f"{i}. {item}" for i, item in enumerate(items, 1))
                warn_msg = "\n".join(msg_lines)
                self._set_pt_exam_feedback(
                    gen_id, warn_msg.replace("\n", "；"), "red")
                self._on_breaker_blocked(gen_id, "合闸前步骤未完成", warn_msg)
                return
        generator.cmd_close = True

    def _get_generator_state(self, gen_id) -> GeneratorState:
        return self._sim_state.gen1 if gen_id == 1 else self._sim_state.gen2
