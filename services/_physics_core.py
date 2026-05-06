"""
services/_physics_core.py
波形生成与历史缓冲 Mixin ── PhysicsEngine 的波形核心职责。
"""

import math
from typing import TYPE_CHECKING, cast

import numpy as np

from domain.constants import MAX_POINTS, GRID_FREQ, GRID_AMP, XS

if TYPE_CHECKING:
    from domain.models import SimulationState

# 线电压 RMS → 峰值相电压转换系数
_PEAK = math.sqrt(2.0 / 3.0)


class WaveformMixin:
    """三相波形生成、历史缓冲与相量坐标计算。"""

    if TYPE_CHECKING:
        animation_time: float
        fixed_t: np.ndarray
        wave_sample_dt: float
        history_initialized: bool
        plot_data: dict[str, float | np.ndarray]
        bus_reference_gen: int | None
        bus_live: bool

    def reset_wave_history(self) -> None:
        self.plot_data = {}
        self.history_initialized = False

    def _control_speed_factor(self, sim: "SimulationState") -> float:
        return max(sim.sim_speed, 0.05)

    @staticmethod
    def _three_phase_samples(
        base_angle,
        amp,
        shift_b,
        shift_c,
        prefix,
    ) -> dict[str, float | np.ndarray]:
        # amp 为线电压 RMS；转换为峰值相电压后再做 sin 波形
        peak = amp * _PEAK
        return {
            f'{prefix}a': peak * np.sin(base_angle),
            f'{prefix}b': peak * np.sin(base_angle + shift_b),
            f'{prefix}c': peak * np.sin(base_angle + shift_c),
        }

    def _build_wave_history(
        self,
        w_bus,
        w_g1,
        w_g2,
        p_bus,
        p_g1,
        p_g2,
        bus_a,
        a1,
        a2,
        shift_b,
        shift_c,
    ) -> dict[str, np.ndarray]:
        hist_t = self.animation_time - self.fixed_t[::-1]
        result: dict[str, np.ndarray] = {}
        result.update(cast(dict[str, np.ndarray], self._three_phase_samples(
            w_bus * hist_t + p_bus, bus_a, -2*np.pi/3, +2*np.pi/3, 'g')))
        result.update(cast(dict[str, np.ndarray], self._three_phase_samples(
            w_g1  * hist_t + p_g1,  a1,   -2*np.pi/3, +2*np.pi/3, 'g1')))
        result.update(cast(dict[str, np.ndarray], self._three_phase_samples(
            w_g2  * hist_t + p_g2,  a2,    shift_b,    shift_c,    'g2')))
        result['ic1'] = np.zeros(MAX_POINTS)
        result['ic2'] = np.zeros(MAX_POINTS)
        return result

    def _append_history_sample(self, key, value) -> None:
        series = cast(np.ndarray, self.plot_data[key])
        series[:-1] = series[1:]
        series[-1] = value

    def _get_instant_samples(
        self,
        sample_time,
        w_bus,
        w_g1,
        w_g2,
        p_bus,
        p_g1,
        p_g2,
        bus_a,
        a1,
        a2,
        shift_b,
        shift_c,
    ) -> dict[str, float | np.ndarray]:
        result = {}
        result.update(self._three_phase_samples(
            w_bus * sample_time + p_bus, bus_a, -2*np.pi/3, +2*np.pi/3, 'g'))
        result.update(self._three_phase_samples(
            w_g1  * sample_time + p_g1,  a1,   -2*np.pi/3, +2*np.pi/3, 'g1'))
        result.update(self._three_phase_samples(
            w_g2  * sample_time + p_g2,  a2,    shift_b,    shift_c,    'g2'))
        return result

    def _advance_time(self, sim) -> float:
        prev_animation_time = self.animation_time
        if not sim.paused:
            self.animation_time += 0.002 * sim.sim_speed
        return prev_animation_time

    def _update_actual_amplitudes(self, sim) -> tuple[float, float]:
        speed_factor = self._control_speed_factor(sim)
        for generator in (sim.gen1, sim.gen2):
            target_amp = generator.amp if generator.running else 0.0
            if generator.mode == "auto" and not generator.breaker_closed:
                generator.actual_amp = target_amp
            else:
                climb_speed = 185.0 * sim.gov_gain * speed_factor
                if generator.actual_amp < target_amp:
                    generator.actual_amp = min(target_amp, generator.actual_amp + climb_speed)
                elif generator.actual_amp > target_amp:
                    generator.actual_amp = max(target_amp, generator.actual_amp - climb_speed)
        return sim.gen1.actual_amp, sim.gen2.actual_amp

    def _compute_wave_state(self, sim, is_isolated, g1_on_bus, g2_on_bus, a1, a2) -> dict[str, float]:
        w_g1 = 2 * np.pi * sim.gen1.freq
        w_g2 = 2 * np.pi * sim.gen2.freq
        p_g1 = np.radians(sim.gen1.phase_deg)
        p_g2 = np.radians(sim.gen2.phase_deg)

        if is_isolated:
            if g1_on_bus and g2_on_bus:
                if self.bus_reference_gen == 2:
                    bus_w, bus_p, bus_a = w_g2, p_g2, a2
                else:
                    bus_w, bus_p, bus_a = w_g1, p_g1, a1
            elif g1_on_bus:
                bus_w, bus_p, bus_a = w_g1, p_g1, a1
            elif g2_on_bus:
                bus_w, bus_p, bus_a = w_g2, p_g2, a2
            else:
                bus_w, bus_p, bus_a = 2 * np.pi * GRID_FREQ, 0.0, 0.0
        else:
            bus_w, bus_p, bus_a = 2 * np.pi * GRID_FREQ, 0.0, GRID_AMP

        if sim.rotate_phasor:
            ang_bus = bus_w * self.animation_time + bus_p
            ang_g1 = w_g1 * self.animation_time + p_g1
            ang_g2 = w_g2 * self.animation_time + p_g2
        else:
            ang_bus = bus_p if is_isolated and not self.bus_live else 0.0
            ang_g1 = (w_g1 - bus_w) * self.animation_time + p_g1 - bus_p
            ang_g2 = (w_g2 - bus_w) * self.animation_time + p_g2 - bus_p

        return {
            'w_g1': w_g1, 'w_g2': w_g2,
            'p_g1': p_g1, 'p_g2': p_g2,
            'bus_w': bus_w, 'bus_p': bus_p, 'bus_a': bus_a,
            'ang_bus': ang_bus, 'ang_g1': ang_g1, 'ang_g2': ang_g2,
            # ga/g1a/g2a_sample 为峰值相电压，供电流保护计算使用
            'ga_sample':  bus_a * _PEAK * np.sin(bus_w * self.animation_time + bus_p),
            'g1a_sample': a1    * _PEAK * np.sin(w_g1  * self.animation_time + p_g1),
            'g2a_sample': a2    * _PEAK * np.sin(w_g2  * self.animation_time + p_g2),
        }

    def _update_wave_history(
        self,
        prev_animation_time,
        wave_state,
        a1,
        a2,
        shift_b,
        shift_c,
        g1_connected,
        g2_connected,
    ) -> None:
        if not self.history_initialized or not self.plot_data:
            self.plot_data = cast(dict[str, float | np.ndarray], self._build_wave_history(
                wave_state['bus_w'], wave_state['w_g1'], wave_state['w_g2'],
                wave_state['bus_p'], wave_state['p_g1'], wave_state['p_g2'],
                wave_state['bus_a'], a1, a2, shift_b, shift_c,
            ))
            self.history_initialized = True
            return

        interval_dt = max(self.animation_time - prev_animation_time, self.wave_sample_dt)
        sample_count = max(1, int(np.ceil(interval_dt / self.wave_sample_dt)))
        sample_times = np.linspace(prev_animation_time + interval_dt / sample_count, self.animation_time, sample_count)

        for sample_time in sample_times:
            samples = self._get_instant_samples(
                sample_time, wave_state['bus_w'], wave_state['w_g1'], wave_state['w_g2'],
                wave_state['bus_p'], wave_state['p_g1'], wave_state['p_g2'],
                wave_state['bus_a'], a1, a2, shift_b, shift_c,
            )
            self._append_history_sample('ga', samples['ga'])
            self._append_history_sample('gb', samples['gb'])
            self._append_history_sample('gc', samples['gc'])
            self._append_history_sample('g1a', samples['g1a'])
            self._append_history_sample('g1b', samples['g1b'])
            self._append_history_sample('g1c', samples['g1c'])
            self._append_history_sample('g2a', samples['g2a'])
            self._append_history_sample('g2b', samples['g2b'])
            self._append_history_sample('g2c', samples['g2c'])
            self._append_history_sample('ic1', (samples['g1a'] - samples['ga']) / XS if g1_connected else 0.0)
            self._append_history_sample('ic2', (samples['g2a'] - samples['ga']) / XS if g2_connected else 0.0)

    def _update_plot_metadata(self, wave_state, a1, a2, shift_b, shift_c) -> None:
        self.plot_data.update({
            'ang_grid': wave_state['ang_bus'],
            'ang_g1':   wave_state['ang_g1'],
            'ang_g2':   wave_state['ang_g2'],
            'a1': a1, 'a2': a2,
            'shift_b': shift_b, 'shift_c': shift_c,
        })
