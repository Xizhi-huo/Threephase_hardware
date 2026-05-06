"""
services/physics_engine.py
物理引擎 ── 通过 Mixin 组合拆分后的四个职责模块：
  · WaveformMixin       波形生成与历史缓冲   (_physics_core.py)
  · ArbitrationMixin    母排仲裁与自动同步   (_physics_arbitration.py)
  · ProtectionMixin     继电保护与断路器逻辑  (_physics_protection.py)
  · MeasurementMixin    接地、PT 测量与万用表  (_physics_measurement.py)

本文件只保留：
  · __init__（所有运行时状态的初始化）
  · update_physics（每帧主调度）
  · build_render_state（向 UI 输出 RenderState 快照）
"""

import numpy as np

from domain.constants import MAX_POINTS
from domain.enums import SystemMode
from adapters.render_state import RenderState

from services._physics_core import WaveformMixin
from services._physics_arbitration import ArbitrationMixin
from services._physics_protection import ProtectionMixin
from services._physics_measurement import MeasurementMixin


class PhysicsEngine(WaveformMixin, ArbitrationMixin, ProtectionMixin, MeasurementMixin):
    def __init__(
        self,
        *legacy_source,
        sim_state=None,
        flow_mgr=None,
        phase_resolver=None,
        sync_svc=None,
        get_pt_phase_orders=None,
        get_loop_test_state=None,
        get_pt_voltage_check_state=None,
        is_sync_test_active=None,
        mark_fault_detected=None,
        queue_accident_dialog=None,
    ):
        if legacy_source:
            if len(legacy_source) != 1:
                raise TypeError("PhysicsEngine accepts at most one legacy positional source")
            source = legacy_source[0]
            sim_state = sim_state or source.sim_state
            flow_mgr = flow_mgr or source.flow_mgr
            phase_resolver = phase_resolver or source.phase_resolver
            sync_svc = sync_svc or source.sync_svc
            get_pt_phase_orders = get_pt_phase_orders or (lambda: source.pt_phase_orders)
            get_loop_test_state = get_loop_test_state or (lambda: source.loop_test_state)
            get_pt_voltage_check_state = get_pt_voltage_check_state or (
                lambda: getattr(source, 'pt_voltage_check_state', None)
            )
            is_sync_test_active = is_sync_test_active or source.is_sync_test_active
            mark_fault_detected = mark_fault_detected or source.assessment_coord.mark_fault_detected
            queue_accident_dialog = queue_accident_dialog or source.queue_accident_dialog

        missing = [
            name for name, value in (
                ('sim_state', sim_state),
                ('flow_mgr', flow_mgr),
                ('phase_resolver', phase_resolver),
                ('sync_svc', sync_svc),
                ('get_pt_phase_orders', get_pt_phase_orders),
                ('get_loop_test_state', get_loop_test_state),
                ('get_pt_voltage_check_state', get_pt_voltage_check_state),
                ('is_sync_test_active', is_sync_test_active),
                ('mark_fault_detected', mark_fault_detected),
                ('queue_accident_dialog', queue_accident_dialog),
            )
            if value is None
        ]
        if missing:
            raise TypeError(f"PhysicsEngine missing required dependencies: {', '.join(missing)}")

        self._sim_state = sim_state
        self._flow_mgr = flow_mgr
        self._phase_resolver = phase_resolver
        self._sync_svc = sync_svc
        self._get_pt_phase_orders = get_pt_phase_orders
        self._get_loop_test_state = get_loop_test_state
        self._get_pt_voltage_check_state = get_pt_voltage_check_state
        self._is_sync_test_active = is_sync_test_active
        self._mark_fault_detected = mark_fault_detected
        self._queue_accident_dialog = queue_accident_dialog
        self.animation_time = 0.0
        self.fixed_t = np.linspace(0, 0.06, MAX_POINTS)
        self.fixed_deg = self.fixed_t * 50 * 360
        self.wave_sample_dt = self.fixed_t[1] - self.fixed_t[0]
        self.history_initialized = False
        self.frame_dt = 0.033

        self.flash_frames1 = 0
        self.flash_frames2 = 0
        self.dead_bus_timer = 0.0
        self.first_ready: int | None = None
        self.bus_reference_gen: int | None = None

        self.plot_data: dict[str, float | np.ndarray] = {}
        self.relay_msg, self.relay_color = "", "blue"
        self.arb_msg, self.arb_color = "🛠️ 仲裁器: 待机", "#00ff00"
        self.brk1_text, self.brk1_bg, self.brk1_visual = "断路器: OPEN (开路)", "gray", False
        self.brk2_text, self.brk2_bg, self.brk2_visual = "断路器: OPEN (开路)", "gray", False
        self.circ_msg, self.circ_color = "", "gray"
        self.color_sw1, self.color_sw2 = "k", "k"
        self.i1_rms, self.ip1, self.iq1 = 0, 0, 0
        self.i2_rms, self.ip2, self.iq2 = 0, 0, 0
        self.ground_msg, self.ground_color = "N线: 未接地", "gray"

        self.meter_reading = "请用表笔点击两个端子"
        self.meter_color = "black"
        self.meter_voltage: float | None = None
        self.meter_status = "idle"
        self.meter_nodes: tuple[str, str] | None = None
        self.meter_phase_match: bool | None = None

        self.bus_freq = 0.0
        self.bus_amp = 0.0
        self.bus_phase = 0.0
        self.bus_source: int | str | None = None
        self.bus_live = False
        self.bus_status_msg = "母排: 无电"
        self.bus_reference_msg = "参考基准: 无"

        self.pt1_v = 0.0
        self.pt2_v = 0.0
        self.pt3_v = 0.0

        # 多周期 RMS 滑动平均（EMA）—— 稳定电压示值
        # alpha=0.07 约 14 帧时间常数（~0.5 s @ 30fps），足够滤掉截断毛刺
        self._meter_ema_alpha: float = 0.07

    # ── 每帧主调度 ─────────────────────────────────────────────────────────
    def update_physics(self) -> None:
        sim = self._sim_state
        is_isolated = sim.system_mode == SystemMode.ISOLATED_BUS

        # 仲裁前先计算一次母线参考，供仲裁器判断当前接入关系；
        # 仲裁后再重算一次，确保本帧后续计算使用的是最终母线状态。
        pre_arbitration_bus_state = self._update_bus_reference(sim, is_isolated)
        self._update_arbitration(
            sim,
            pre_arbitration_bus_state['g1_on_bus'],
            pre_arbitration_bus_state['g2_on_bus'],
            pre_arbitration_bus_state['ref_freq'],
            pre_arbitration_bus_state['ref_amp'],
        )
        bus_state = self._update_bus_reference(sim, is_isolated)

        prev_animation_time = self._advance_time(sim)
        a1, a2 = self._update_actual_amplitudes(sim)
        self._apply_engine_trip_interlocks(sim)

        wave_state = self._compute_wave_state(sim, is_isolated, bus_state['g1_on_bus'], bus_state['g2_on_bus'], a1, a2)
        deltas = self._update_protection_state(sim, wave_state, a1, a2, bus_state['g1_on_bus'], bus_state['g2_on_bus'])
        # self._apply_droop_control(sim)
        self._update_circulating_current(sim, a1, a2, deltas['delta1'], deltas['delta2'])

        shift_b = 2 * np.pi / 3 if sim.fault_reverse_bc else -2 * np.pi / 3
        shift_c = -2 * np.pi / 3 if sim.fault_reverse_bc else 2 * np.pi / 3
        self._update_wave_history(
            prev_animation_time, wave_state, a1, a2, shift_b, shift_c,
            bus_state['g1_on_bus'], bus_state['g2_on_bus'],
        )
        self._update_grounding(sim)
        self._update_breaker_logic(
            sim, deltas['delta1'], deltas['delta2'], a1, a2,
            bus_state['ref_freq'], bus_state['ref_amp'], is_isolated,
        )
        self._update_plot_metadata(wave_state, a1, a2, shift_b, shift_c)
        self._update_pt_measurements(wave_state['bus_a'], a1, a2)
        self._update_multimeter(sim)

    # ── UI 快照输出 ────────────────────────────────────────────────────────
    def build_render_state(self) -> RenderState:
        """将物理引擎当前帧的所有渲染属性打包为 RenderState 快照，供 UI 消费。"""
        return RenderState(
            plot_data         = self.plot_data,
            fixed_deg         = self.fixed_deg,
            bus_live          = self.bus_live,
            bus_amp           = self.bus_amp,
            bus_source        = self.bus_source,
            bus_reference_gen = self.bus_reference_gen,
            bus_status_msg    = self.bus_status_msg,
            bus_reference_msg = self.bus_reference_msg,
            brk1_text         = self.brk1_text,
            brk1_bg           = self.brk1_bg,
            brk1_visual       = self.brk1_visual,
            color_sw1         = self.color_sw1,
            brk2_text         = self.brk2_text,
            brk2_bg           = self.brk2_bg,
            brk2_visual       = self.brk2_visual,
            color_sw2         = self.color_sw2,
            arb_msg           = self.arb_msg,
            arb_color         = self.arb_color,
            relay_msg         = self.relay_msg,
            relay_color       = self.relay_color,
            i1_rms            = self.i1_rms,
            ip1               = self.ip1,
            iq1               = self.iq1,
            i2_rms            = self.i2_rms,
            ip2               = self.ip2,
            iq2               = self.iq2,
            circ_msg          = self.circ_msg,
            circ_color        = self.circ_color,
            ground_msg        = self.ground_msg,
            ground_color      = self.ground_color,
            pt1_v             = self.pt1_v,
            pt2_v             = self.pt2_v,
            pt3_v             = self.pt3_v,
            meter_reading     = self.meter_reading,
            meter_color       = self.meter_color,
            meter_voltage     = self.meter_voltage,
            meter_status      = self.meter_status,
            meter_nodes       = self.meter_nodes,
            meter_phase_match = self.meter_phase_match,
        )
