"""
services/sync_test_service.py
同步功能测试服务
"""

from typing import Callable

from domain.constants import GRID_FREQ, GRID_AMP
from domain.enums import BreakerPosition
from domain.test_states import SyncTestState


class SyncTestService:
    """
    同步功能测试业务逻辑。
    状态以 SyncTestState dataclass 持有，避免裸字典的字段漂移。
    """

    def __init__(
        self,
        *,
        sim_state,
        flow_mgr,
        fault_mgr,
        get_physics: Callable[[], object],
        get_sync_test_state: Callable[[], SyncTestState],
        set_sync_test_state: Callable[[SyncTestState], None],
        is_loop_test_complete: Callable[[], bool],
        is_pt_voltage_check_complete: Callable[[], bool],
        is_pt_phase_check_complete: Callable[[], bool],
        is_pt_exam_recorded: Callable[[int], bool],
    ):
        self._sim_state = sim_state
        self._flow_mgr = flow_mgr
        self._fault_mgr = fault_mgr
        self._get_physics = get_physics
        self._get_sync_test_state = get_sync_test_state
        self._set_sync_test_state = set_sync_test_state
        self._is_loop_test_complete = is_loop_test_complete
        self._is_pt_voltage_check_complete = is_pt_voltage_check_complete
        self._is_pt_phase_check_complete = is_pt_phase_check_complete
        self._is_pt_exam_recorded = is_pt_exam_recorded

    # ── 状态工厂 ──────────────────────────────────────────────────────────────
    def create_sync_test_state(self) -> SyncTestState:
        return SyncTestState()

    def start_sync_test(self) -> None:
        self._get_sync_test_state().started = True

    def stop_sync_test(self) -> None:
        self._get_sync_test_state().started = False

    def _set_sync_test_feedback(self, message, color='#444444') -> None:
        state = self._get_sync_test_state()
        state.feedback = message
        state.feedback_color = color

    def is_gen_synced(self, follower, master, freq_tol=0.5, amp_tol=500.0, phase_tol=15.0) -> bool:
        """判断 follower 是否已同步到 master 的频率、幅值和相位（三个值均在容差内）。"""
        phase_diff = abs(follower.phase_deg - master.phase_deg)
        phase_diff = min(phase_diff, 360.0 - phase_diff)
        return (abs(follower.freq - master.freq) < freq_tol and
                abs(follower.amp - master.amp) < amp_tol and
                phase_diff < phase_tol)

    def _are_both_synced(self, freq_tol=0.5, amp_tol=500.0, phase_tol=15.0) -> bool:
        """判断两台发电机三个值（频率、幅值、相位）差值是否均在允许范围内。"""
        gen1, gen2 = self._sim_state.gen1, self._sim_state.gen2
        phase_diff = abs(gen1.phase_deg - gen2.phase_deg)
        phase_diff = min(phase_diff, 360.0 - phase_diff)
        return (abs(gen1.freq - gen2.freq) < freq_tol and
                abs(gen1.amp - gen2.amp) < amp_tol and
                phase_diff < phase_tol)

    def get_sync_test_steps(self) -> list[tuple[str, bool]]:
        sim = self._sim_state
        gen1, gen2 = sim.gen1, sim.gen2
        p = self._get_physics()
        state = self._get_sync_test_state()

        loop_done = self._is_loop_test_complete()
        pt_voltage_done = self._is_pt_voltage_check_complete()
        pt_phase_done = self._is_pt_phase_check_complete()
        pt_done = self._is_pt_exam_recorded(1) and self._is_pt_exam_recorded(2)

        r1_master_ok = (gen1.breaker_closed and
                        gen1.breaker_position == BreakerPosition.WORKING and
                        gen1.mode == "manual")
        r1_follower_ok = gen2.mode == "auto"
        r1_synced = (r1_master_ok and r1_follower_ok and
                     self.is_gen_synced(gen2, gen1))

        r2_master_ok = (gen2.breaker_closed and
                        gen2.breaker_position == BreakerPosition.WORKING and
                        gen2.mode == "manual" and
                        getattr(p, 'bus_reference_gen', None) == 2)
        r2_follower_ok = gen1.mode == "auto"
        r2_synced = (r2_master_ok and r2_follower_ok and
                     self.is_gen_synced(gen1, gen2))

        steps = [
            ("1. 前提：第一步回路连通性测试已完成",
             loop_done),
            ("2. 前提：第二步 PT 单体线电压检查已完成",
             pt_voltage_done),
            ("3. 前提：第三步 PT 相序检查已完成",
             pt_phase_done),
            ("4. 前提：第四步 PT 二次端子压差测试已完成（Gen1 & Gen2）",
             pt_done),
            ("5. [第一轮] 将 Gen 1 切至手动模式并在工作位置合闸（建立母排电压）",
             r1_master_ok or state.round1_done),
            ("6. [第一轮] 将 Gen 2 切至自动（Auto）同步追踪模式",
             r1_follower_ok or state.round1_done),
            ("7. [第一轮] 等待 Gen 2 三值（频率/幅值/相位）均与 Gen 1 匹配后记录",
             r1_synced or state.round1_done),
            ("8. [第一轮] 记录结果：Gen 1 基准 → Gen 2 同步完成",
             state.round1_done),
            ("9. [第二轮] 断开 Gen 1，将 Gen 2 切至手动模式并合闸（互换基准）",
             r2_master_ok or state.round2_done),
            ("10. [第二轮] 将 Gen 1 切至自动（Auto）同步追踪模式",
             r2_follower_ok or state.round2_done),
            ("11. [第二轮] 等待 Gen 1 三值（频率/幅值/相位）均与 Gen 2 匹配后记录",
             r2_synced or state.round2_done),
            ("12. [第二轮] 记录结果：Gen 2 基准 → Gen 1 同步完成",
             state.round2_done),
        ]
        if state.completed:
            return [(text, True) for text, _ in steps]
        return steps

    def record_sync_round(self, round_num) -> None:
        sim = self._sim_state
        gen1, gen2 = sim.gen1, sim.gen2
        p = self._get_physics()
        state = self._get_sync_test_state()

        # ── 门禁：必须先点击"开始第五步测试" ──────────────────────────────
        if not state.started:
            self._set_sync_test_feedback(
                '请先点击"开始第五步测试"，再进行同步功能记录。', "red")
            return

        if not self._is_loop_test_complete():
            self._set_sync_test_feedback("请先完成第一步【回路连通性测试】。", "red")
            return
        if not self._is_pt_voltage_check_complete():
            self._set_sync_test_feedback("请先完成第二步【PT 单体线电压检查】。", "red")
            return
        if not self._is_pt_phase_check_complete():
            self._set_sync_test_feedback("请先完成第三步【PT 相序检查】。", "red")
            return
        if not (self._is_pt_exam_recorded(1) and self._is_pt_exam_recorded(2)):
            self._set_sync_test_feedback(
                "请先完成第四步【PT 二次端子压差测试】（Gen1 和 Gen2 均需完成）。", "red")
            return
        if (self._flow_mgr.should_block_step5_until_blackbox_fixed()
                and self._fault_mgr.has_unrepaired_wiring_fault()):
            self._set_sync_test_feedback(
                "请先修复未恢复的黑盒接线故障，再进行第五步【同步功能测试】。", "red")
            return

        if round_num == 1:
            if not (gen1.breaker_closed and
                    gen1.breaker_position == BreakerPosition.WORKING and
                    gen1.mode == "manual"):
                self._set_sync_test_feedback(
                    "请先将 Gen 1 切至手动模式并在工作位置合闸，建立母排电压。", "red")
                return
            if gen2.mode != "auto":
                self._set_sync_test_feedback(
                    "请先将 Gen 2 切至自动（Auto）同步模式。", "red")
                return
            if not self.is_gen_synced(gen2, gen1):
                df = abs(gen2.freq - gen1.freq)
                dv = abs(gen2.amp - gen1.amp)
                dp = abs(gen2.phase_deg - gen1.phase_deg)
                dp = min(dp, 360.0 - dp)
                self._set_sync_test_feedback(
                    f"Gen 2 尚未同步完成（Δf={df:.2f} Hz，ΔV={dv:.0f} V，Δθ={dp:.1f}°），"
                    "请开启自动追踪后等待三个值均收敛再记录。",
                    "red")
                return
            state.round1_done = True
            self._set_sync_test_feedback(
                "第一轮记录成功：Gen 1 作基准，Gen 2 同步功能正常。"
                "请断开 Gen 1，互换角色进行第二轮测试。", "#006600")

        elif round_num == 2:
            if not state.round1_done:
                self._set_sync_test_feedback(
                    "请先完成第一轮测试并记录，再进行第二轮。", "red")
                return
            if not (gen2.breaker_closed and
                    gen2.breaker_position == BreakerPosition.WORKING and
                    gen2.mode == "manual" and
                    getattr(p, 'bus_reference_gen', None) == 2):
                self._set_sync_test_feedback(
                    "请先断开 Gen 1，将 Gen 2 切至手动模式并在工作位置合闸作为新基准。", "red")
                return
            if gen1.mode != "auto":
                self._set_sync_test_feedback(
                    "请先将 Gen 1 切至自动（Auto）同步模式。", "red")
                return
            if not self.is_gen_synced(gen1, gen2):
                df = abs(gen1.freq - gen2.freq)
                dv = abs(gen1.amp - gen2.amp)
                dp = abs(gen1.phase_deg - gen2.phase_deg)
                dp = min(dp, 360.0 - dp)
                self._set_sync_test_feedback(
                    f"Gen 1 尚未同步完成（Δf={df:.2f} Hz，ΔV={dv:.0f} V，Δθ={dp:.1f}°），"
                    "请开启自动追踪后等待三个值均收敛再记录。",
                    "red")
                return
            state.round2_done = True
            self._set_sync_test_feedback(
                "第二轮记录成功：Gen 2 作基准，Gen 1 同步功能正常。两台发电机同步功能测试全部完成！",
                "#006600")

    def reset_sync_test(self) -> None:
        self._set_sync_test_state(self.create_sync_test_state())

    def is_sync_test_complete(self) -> bool:
        """用户已点击"完成第五步测试"才返回 True，用于解锁合闸约束。"""
        return self._get_sync_test_state().completed

    def is_sync_test_rounds_done(self) -> bool:
        """两轮记录均已完成（但用户可能尚未点击完成按钮）。"""
        state = self._get_sync_test_state()
        return state.round1_done and state.round2_done

    def finalize_sync_test(self) -> None:
        if not self.is_sync_test_rounds_done():
            self._set_sync_test_feedback(
                '请先完成并记录两轮同步测试，再点击“完成第五步测试”。', "red")
            return
        # 自动将两台发电机切至自动模式，并恢复额定参数（50 Hz / GRID_AMP / 相位 0°）
        self._sim_state.remote_start_signal = True
        for gen in (self._sim_state.gen1, self._sim_state.gen2):
            gen.mode = "auto"
            gen.running = True
            gen.breaker_position = BreakerPosition.WORKING
            gen.breaker_closed = True
            gen.cmd_close = False
            gen.freq = GRID_FREQ
            gen.amp = GRID_AMP
            gen.actual_amp = GRID_AMP
            gen.phase_deg = 0.0
        self._get_sync_test_state().completed = True
        self._set_sync_test_feedback(
            "第五步【同步功能测试】已确认完成，两台发电机已自动切至 Auto 模式并恢复额定参数，"
            "系统恢复正常自动合闸逻辑。", "#006600")

    def get_sync_test_blockers(self) -> list[str]:
        return [text for text, done in self.get_sync_test_steps() if not done]
