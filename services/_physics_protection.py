"""
services/_physics_protection.py
继电保护、垂降控制、环流监控与断路器逻辑 Mixin ── PhysicsEngine 的保护职责。
"""

import math
from typing import Callable, TYPE_CHECKING

import numpy as np

from domain.constants import (
    TRIP_CURRENT,
    CT_RATIO,
    GRID_FREQ,
    GRID_AMP,
    SYNC_FREQ_OK_HZ,
    SYNC_VOLT_OK_V,
    SYNC_PHASE_OK_DEG,
    XS,
    # KP_DROOP,
    # KQ_DROOP,
)
from domain.enums import BreakerPosition

if TYPE_CHECKING:
    from domain.models import SimulationState
    from services.sync_test_service import SyncTestService

# 线电压 RMS → 峰值相电压转换系数（与 _physics_core 中保持一致）
_PEAK = math.sqrt(2.0 / 3.0)


def _heat_color(rms: float) -> str:
    """根据电流 RMS 值返回热力颜色字符串（绿→橙→红）。"""
    ratio = min(rms / TRIP_CURRENT, 1.0)
    r = int(255 * ratio)
    g = int(200 * (1 - ratio))
    return f'#{r:02x}{g:02x}00'


class ProtectionMixin:
    """继电保护、垂降控制、环流监控与断路器状态机。"""

    if TYPE_CHECKING:
        animation_time: float
        bus_live: bool
        i1_rms: float
        ip1: float
        iq1: float
        i2_rms: float
        ip2: float
        iq2: float
        relay_msg: str
        relay_color: str
        circ_msg: str
        circ_color: str
        color_sw1: str
        color_sw2: str
        flash_frames1: int
        flash_frames2: int
        _sim_state: SimulationState
        _sync_svc: SyncTestService
        _is_sync_test_active: Callable[[], bool]
        _queue_accident_dialog: Callable[[str], None]

    def _apply_engine_trip_interlocks(self, sim) -> None:
        if sim.loop_test_mode:
            return
        if sim.gen1.breaker_closed and not sim.gen1.running:
            sim.gen1.breaker_closed = False
            self.relay_msg, self.relay_color = "⚠️ 保护: Gen 1 引擎停机失压，断路器自动脱扣！", "orange"
        if sim.gen2.breaker_closed and not sim.gen2.running:
            sim.gen2.breaker_closed = False
            self.relay_msg, self.relay_color = "⚠️ 保护: Gen 2 引擎停机失压，断路器自动脱扣！", "orange"

    def _update_protection_state(
        self,
        sim,
        wave_state,
        a1,
        a2,
        g1_connected,
        g2_connected,
    ) -> dict[str, float]:
        delta1 = wave_state['ang_g1'] - wave_state['ang_bus']
        delta2 = wave_state['ang_g2'] - wave_state['ang_bus']

        if g1_connected:
            # g1a_sample/ga_sample 已是峰值相电压，直接相减得环流峰值
            self.i1_rms = abs((wave_state['g1a_sample'] - wave_state['ga_sample']) / XS)
            # a1/a2 为线电压 RMS，乘以 _PEAK 转为峰值相电压后计算功率电流
            self.ip1 = _PEAK * (a1 * np.sin(delta1)) / XS
            self.iq1 = _PEAK * (a1 * np.cos(delta1) - wave_state['bus_a']) / XS
        else:
            self.i1_rms = self.ip1 = self.iq1 = 0.0

        if g2_connected:
            self.i2_rms = abs((wave_state['g2a_sample'] - wave_state['ga_sample']) / XS)
            self.ip2 = _PEAK * (a2 * np.sin(delta2)) / XS
            self.iq2 = _PEAK * (a2 * np.cos(delta2) - wave_state['bus_a']) / XS
        else:
            self.i2_rms = self.ip2 = self.iq2 = 0.0

        self.relay_msg, self.relay_color = (
            f"🛡️ 继电保护监控中 (跳闸阈值: 一次侧 {TRIP_CURRENT}A / CT二次侧 {TRIP_CURRENT/CT_RATIO:.1f}A)",
            "blue"
        )
        # 只有 Gen2 真正并入一次系统（工作位 + 合闸）才触发反相告警
        if (sim.gen2.breaker_closed and
                sim.gen2.breaker_position == BreakerPosition.WORKING and
                sim.fault_reverse_bc):
            self.relay_msg, self.relay_color = (
                "⚠️ 警告：Gen2 B/C相序接反！合闸后产生短路电流！（模拟中无保护器，实际系统将立即跳闸）",
                "red"
            )
        if self.i1_rms > TRIP_CURRENT:
            sim.gen1.breaker_closed = False
            self.flash_frames1 = 0
            self.relay_msg, self.relay_color = "💥 保护: Gen 1 环流过大，跳闸！", "red"
        if self.i2_rms > TRIP_CURRENT:
            sim.gen2.breaker_closed = False
            sim.auto_sync_active = False
            self.flash_frames2 = 0
            self.relay_msg, self.relay_color = "💥 保护: Gen 2 环流过大，跳闸！", "red"
        return {'delta1': delta1, 'delta2': delta2}

    # def _apply_droop_control(self, sim):
        # 电压限幅基于额定幅值 ±15%，确保高压系统下垂控制不会把幅值压到低压区间
    #     _amp_min = GRID_AMP * 0.85
    #     _amp_max = GRID_AMP * 1.15
        # 垂降控制仅作用于真正并入一次系统的机组（工作位 + 合闸）
    #     g1_on_bus = (sim.gen1.breaker_position == BreakerPosition.WORKING and
    #                  sim.gen1.breaker_closed)
    #     g2_on_bus = (sim.gen2.breaker_position == BreakerPosition.WORKING and
    #                  sim.gen2.breaker_closed)
    #     if sim.droop_enabled and not sim.paused:
    #         if g1_on_bus:
    #             sim.gen1.freq = max(48.0, min(52.0, sim.gen1.freq - KP_DROOP * self.ip1))
    #             sim.gen1.amp = max(_amp_min, min(_amp_max, sim.gen1.amp - KQ_DROOP * self.iq1))
    #         if g2_on_bus:
    #             sim.gen2.freq = max(48.0, min(52.0, sim.gen2.freq - KP_DROOP * self.ip2))
    #             sim.gen2.amp = max(_amp_min, min(_amp_max, sim.gen2.amp - KQ_DROOP * self.iq2))

    def _update_circulating_current(self, sim, a1, a2, delta1, delta2) -> None:
        # 仅当两台机组均真正并入一次母排（工作位 + 合闸）时才存在机间环流
        g1_on_bus = (sim.gen1.breaker_position == BreakerPosition.WORKING and
                     sim.gen1.breaker_closed)
        g2_on_bus = (sim.gen2.breaker_position == BreakerPosition.WORKING and
                     sim.gen2.breaker_closed)
        if g1_on_bus and g2_on_bus:
            t = self.animation_time
            w1 = 2 * np.pi * sim.gen1.freq
            w2 = 2 * np.pi * sim.gen2.freq
            p1 = np.radians(sim.gen1.phase_deg)
            p2 = np.radians(sim.gen2.phase_deg)

            ang1 = w1 * t + p1
            ang2 = w2 * t + p2
            # a1/a2 为线电压 RMS → 转为峰值相电压后计算环流相量
            e1_r, e1_i = a1 * _PEAK * np.cos(ang1), a1 * _PEAK * np.sin(ang1)
            e2_r, e2_i = a2 * _PEAK * np.cos(ang2), a2 * _PEAK * np.sin(ang2)

            i12_r = (e1_r - e2_r) / (2 * XS)
            i12_i = (e1_i - e2_i) / (2 * XS)
            i12_rms = np.sqrt(i12_r**2 + i12_i**2) / np.sqrt(2)

            freq_diff = sim.gen1.freq - sim.gen2.freq
            amp_diff = a1 - a2

            if abs(freq_diff) > 0.05:
                dir_str = ">>> 有功 >>>" if freq_diff > 0 else "<<< 有功 <<<"
            elif abs(amp_diff) > 50:
                dir_str = ">>> 无功 >>>" if amp_diff > 0 else "<<< 无功 <<<"
            else:
                dir_str = "<-> 平衡 <->"

            self.circ_msg = (f"机组环流: Gen1 {dir_str} Gen2 | "
                             f"CT二次: {i12_rms / CT_RATIO:.3f}A | "
                             f"Δf={freq_diff:+.2f}Hz  ΔU={amp_diff:+.0f}V")
            self.circ_color = _heat_color(i12_rms)
        else:
            self.circ_msg, self.circ_color = "机组间未形成直接环流回路", "gray"

    def _update_breaker_state(self, generator, gen_id, a_value, delta, ref_freq, ref_amp, is_isolated) -> None:
        diff_deg = abs((np.degrees(delta) % 360 + 360) % 360)
        if diff_deg > 180:
            diff_deg -= 360

        text_attr   = 'brk1_text'    if gen_id == 1 else 'brk2_text'
        bg_attr     = 'brk1_bg'      if gen_id == 1 else 'brk2_bg'
        visual_attr = 'brk1_visual'  if gen_id == 1 else 'brk2_visual'
        flash_attr  = 'flash_frames1' if gen_id == 1 else 'flash_frames2'

        sync_ok = True if is_isolated and not self.bus_live else (
            abs(generator.freq - ref_freq) <= SYNC_FREQ_OK_HZ and
            abs(ref_amp - a_value) <= SYNC_VOLT_OK_V and
            abs(diff_deg) <= SYNC_PHASE_OK_DEG
        )

        if generator.mode == "stop":
            generator.breaker_closed = False
            generator.cmd_close = False
        elif generator.mode == "auto":
            sync_test_active = self._is_sync_test_active()
            if is_isolated and not self.bus_live:
                if (not sync_test_active and
                        abs(generator.freq - GRID_FREQ) < 0.1 and
                        abs(GRID_AMP - a_value) <= 185.0 and
                        not generator.breaker_closed):
                    generator.breaker_closed = True
            else:
                if (self._sync_svc.is_sync_test_complete()
                        and abs(generator.freq - ref_freq) < 0.1
                        and abs(ref_amp - a_value) <= 185.0
                        and abs(diff_deg) <= 1.5
                        and not generator.breaker_closed):
                    # E01/E02/E03 故障：Gen2 工作位自动合闸到带电母线时触发事故弹窗
                    # 注：此处 else 分支已保证 bus_live=True；is_sync_test_complete() 保证非第一步
                    fc = self._sim_state.fault_config
                    if (gen_id == 2
                            and generator.breaker_position == BreakerPosition.WORKING
                            and fc.active and not fc.repaired):
                        if fc.scenario_id == 'E01':
                            self._queue_accident_dialog('E01')
                        elif fc.scenario_id == 'E02':
                            self._queue_accident_dialog('E02')
                        elif fc.scenario_id == 'E03':
                            self._queue_accident_dialog('E03')
                        else:
                            generator.breaker_closed = True
                    else:
                        generator.breaker_closed = True
            generator.cmd_close = False
        elif generator.mode == "manual" and generator.cmd_close:
            generator.cmd_close = False
            if not generator.breaker_closed:
                test_mode = getattr(self._sim_state, 'loop_test_mode', False)
                if generator.breaker_position != BreakerPosition.WORKING or sync_ok or test_mode:
                    # E01/E02/E03 故障：Gen2 工作位手动合闸到带电母线时触发事故弹窗
                    fc = self._sim_state.fault_config
                    if (gen_id == 2
                            and generator.breaker_position == BreakerPosition.WORKING
                            and fc.active and not fc.repaired
                            and self.bus_live
                            and not test_mode):
                        if fc.scenario_id == 'E01':
                            self._queue_accident_dialog('E01')
                        elif fc.scenario_id == 'E02':
                            self._queue_accident_dialog('E02')
                        elif fc.scenario_id == 'E03':
                            self._queue_accident_dialog('E03')
                        else:
                            generator.breaker_closed = True
                    else:
                        generator.breaker_closed = True
                else:
                    # E03 故障：sync_ok=False（180° 相位差），强行合闸触发事故弹窗
                    fc = self._sim_state.fault_config
                    if (gen_id == 2
                            and generator.breaker_position == BreakerPosition.WORKING
                            and fc.active and not fc.repaired
                            and fc.scenario_id == 'E03'
                            and self.bus_live
                            and not test_mode):
                        self._queue_accident_dialog('E03')
                    else:
                        self.relay_msg, self.relay_color = (
                            f"非同期合闸爆炸！频差:{abs(generator.freq-ref_freq):.1f}Hz, "
                            f"压差:{abs(ref_amp-a_value):.0f}V, 角差:{abs(diff_deg):.0f}°", "red"
                        )
                        setattr(self, text_attr, "断路器: 炸毁")
                        setattr(self, bg_attr, "red")
                        setattr(self, visual_attr, False)

        if generator.breaker_closed:
            if generator.breaker_position == BreakerPosition.WORKING:
                setattr(self, text_attr, "一次侧: 并网运行 (工作位)")
                setattr(self, bg_attr, "green")
                setattr(self, visual_attr, True)
            elif generator.breaker_position == BreakerPosition.TEST:
                setattr(self, text_attr, "二次侧: 模拟闭合 (试验位)")
                setattr(self, bg_attr, "#ffaa00")
                setattr(self, visual_attr, False)
            else:
                setattr(self, text_attr, "无效: 触头闭合 (脱开位)")
                setattr(self, bg_attr, "gray")
                setattr(self, visual_attr, False)
            setattr(self, flash_attr, 0)
            return

        if self.bus_live and abs(generator.freq - ref_freq) < 0.2 and abs(ref_amp - a_value) <= 185.0 and abs(diff_deg) <= 5.0:
            setattr(self, flash_attr, 15)
        if getattr(self, flash_attr) > 0:
            setattr(self, flash_attr, getattr(self, flash_attr) - 1)
            setattr(self, text_attr, f"Gen{gen_id}: ⚡ 同期条件满足，可合闸")
            setattr(self, bg_attr, "orange")
            setattr(self, visual_attr, False)
        else:
            setattr(self, text_attr, f"断路器: OPEN ({generator.breaker_position})")
            setattr(self, bg_attr, "gray")
            setattr(self, visual_attr, False)

    def _update_breaker_logic(self, sim, delta1, delta2, a1, a2, ref_freq, ref_amp, is_isolated) -> None:
        self.color_sw1 = _heat_color(self.i1_rms)
        self.color_sw2 = _heat_color(self.i2_rms)
        self._update_breaker_state(sim.gen1, 1, a1, delta1, ref_freq, ref_amp, is_isolated)
        self._update_breaker_state(sim.gen2, 2, a2, delta2, ref_freq, ref_amp, is_isolated)
