"""
services/_physics_arbitration.py
母排仲裁与自动同步 Mixin ── PhysicsEngine 的仲裁职责。
"""

import random
from typing import Callable, TYPE_CHECKING

import numpy as np

from domain.constants import GRID_FREQ, GRID_AMP
from domain.enums import BreakerPosition

if TYPE_CHECKING:
    from domain.models import SimulationState
    from domain.test_states import PtVoltageCheckState


class ArbitrationMixin:
    """母排基准解析、死母线首台投入与并网自动相角捕获。"""

    if TYPE_CHECKING:
        bus_freq: float
        bus_amp: float
        bus_phase: float
        bus_source: int | str | None
        bus_live: bool
        bus_status_msg: str
        bus_reference_msg: str
        bus_reference_gen: int | None
        first_ready: int | None
        dead_bus_timer: float
        frame_dt: float
        arb_msg: str
        arb_color: str
        _get_pt_voltage_check_state: Callable[[], PtVoltageCheckState | None]
        _is_sync_test_active: Callable[[], bool]

        def _control_speed_factor(self, sim: "SimulationState") -> float: ...

    def auto_adjust_local(self, generator, sim, target_freq, target_amp) -> None:
        if generator.breaker_closed:
            return

        speed_factor = self._control_speed_factor(sim)
        err_f = target_freq - generator.freq
        step_f = 0.005 * sim.sync_gain * speed_factor
        if abs(err_f) > step_f:
            generator.freq = round(generator.freq + np.sign(err_f) * step_f, 3)
        else:
            generator.freq = target_freq

        err_a = target_amp - generator.amp
        step_a = 6.0 * sim.sync_gain * speed_factor
        if abs(err_a) > step_a:
            generator.amp = round(generator.amp + np.sign(err_a) * step_a, 1)
        else:
            generator.amp = target_amp

    def auto_adjust_phase(self, generator, sim, target_phase_deg) -> None:
        phase_error = generator.phase_deg - target_phase_deg
        # 圆周最短角：将误差折叠到 (-180, 180]
        phase_error = (phase_error + 180.0) % 360.0 - 180.0
        step_p = 0.5 * sim.sync_gain * self._control_speed_factor(sim)
        if abs(phase_error) > step_p:
            new_deg = generator.phase_deg - np.sign(phase_error) * step_p
        else:
            new_deg = target_phase_deg
        # 归一化到 (-180°, 180°]，避免相位值无限漂移
        generator.phase_deg = round(((new_deg + 180.0) % 360.0) - 180.0, 1)

    def _resolve_bus_reference_gen(self, g1_on_bus, g2_on_bus) -> int | None:
        if not g1_on_bus and not g2_on_bus:
            self.bus_reference_gen = None
        elif self.bus_reference_gen == 1 and g1_on_bus:
            pass  # 基准不变，保持 Gen1
        elif self.bus_reference_gen == 2 and g2_on_bus:
            pass  # 基准不变，保持 Gen2
        elif g1_on_bus:
            self.bus_reference_gen = 1
        elif g2_on_bus:
            self.bus_reference_gen = 2
        return self.bus_reference_gen

    def _update_bus_reference(self, sim, is_isolated) -> dict[str, object]:
        g1_on_bus = (sim.gen1.breaker_position == BreakerPosition.WORKING) and sim.gen1.breaker_closed
        g2_on_bus = (sim.gen2.breaker_position == BreakerPosition.WORKING) and sim.gen2.breaker_closed

        if is_isolated:
            reference_gen = self._resolve_bus_reference_gen(g1_on_bus, g2_on_bus)
            if reference_gen == 1 and g1_on_bus:
                self.bus_freq = sim.gen1.freq
                self.bus_amp = sim.gen1.actual_amp
                self.bus_phase = np.radians(sim.gen1.phase_deg)
                self.bus_source = 1 if not g2_on_bus else "both"
                self.bus_live = True
                self.bus_reference_msg = "参考基准: Gen 1"
                if g2_on_bus:
                    self.bus_status_msg = f"母排: 以 Gen 1 为基准并联运行 ({self.bus_freq:.1f}Hz, {self.bus_amp:.0f}V)"
                else:
                    self.bus_status_msg = f"母排: Gen 1 独立供电 ({self.bus_freq:.1f}Hz, {self.bus_amp:.0f}V)"
            elif reference_gen == 2 and g2_on_bus:
                self.bus_freq = sim.gen2.freq
                self.bus_amp = sim.gen2.actual_amp
                self.bus_phase = np.radians(sim.gen2.phase_deg)
                self.bus_source = 2 if not g1_on_bus else "both"
                self.bus_live = True
                self.bus_reference_msg = "参考基准: Gen 2"
                if g1_on_bus:
                    self.bus_status_msg = f"母排: 以 Gen 2 为基准并联运行 ({self.bus_freq:.1f}Hz, {self.bus_amp:.0f}V)"
                else:
                    self.bus_status_msg = f"母排: Gen 2 独立供电 ({self.bus_freq:.1f}Hz, {self.bus_amp:.0f}V)"
            else:
                self.bus_freq = 0.0
                self.bus_amp = 0.0
                self.bus_phase = 0.0
                self.bus_source = None
                self.bus_live = False
                self.bus_status_msg = "母排: 无电 (死母线)"
                self.bus_reference_msg = "参考基准: 无"
                self.bus_reference_gen = None
        else:
            self.bus_freq = GRID_FREQ
            self.bus_amp = GRID_AMP
            self.bus_phase = 0.0
            self.bus_source = "grid"
            self.bus_live = True
            self.bus_status_msg = f"母排: 电网供电 ({GRID_FREQ}Hz)"
            self.bus_reference_msg = "参考基准: 外部电网"
            self.bus_reference_gen = None

        return {
            'g1_on_bus': g1_on_bus,
            'g2_on_bus': g2_on_bus,
            'ref_freq': self.bus_freq if self.bus_live else GRID_FREQ,
            'ref_amp': self.bus_amp if self.bus_live else GRID_AMP,
            'reference_gen': self.bus_reference_gen,
        }

    def _handle_dead_bus_selection(self, sim, mode1, mode2, g1_ready, g2_ready) -> None:
        frame_dt = max(getattr(self, 'frame_dt', 0.033), 0.0)
        if g1_ready and mode1 == "auto" and self.first_ready != 2:
            self.first_ready = 1
        elif g2_ready and mode2 == "auto" and self.first_ready != 1:
            self.first_ready = 2
        else:
            self.first_ready = None
            self.dead_bus_timer = 0.0
            self.arb_msg, self.arb_color = "🔍 仲裁器: 等待机组建立额定电压与频率...", "#00ffff"

        if self.first_ready == 1:
            self.dead_bus_timer += frame_dt * sim.sim_speed
            remaining = sim.first_start_time - self.dead_bus_timer
            if remaining <= 0:
                sim.gen1.phase_deg = 0.0
                sim.gen1.breaker_closed = True
                self.dead_bus_timer = 0.0
                self.first_ready = None
                self.arb_msg, self.arb_color = "🟢 仲裁: Gen 1 首台投入，建立母排基准！", "#00ff00"
            else:
                self.arb_msg, self.arb_color = f"⏳ 仲裁: Gen 1 达标, 准备投入死母线, 延时 {max(0, int(remaining + 1))}s", "#ffcc00"
        elif self.first_ready == 2:
            self.dead_bus_timer += frame_dt * sim.sim_speed
            remaining = sim.first_start_time - self.dead_bus_timer
            if remaining <= 0:
                sim.gen2.phase_deg = 0.0
                sim.gen2.breaker_closed = True
                self.dead_bus_timer = 0.0
                self.first_ready = None
                self.arb_msg, self.arb_color = "🟢 仲裁: Gen 2 首台投入，建立母排基准！", "#00ff00"
            else:
                self.arb_msg, self.arb_color = f"⏳ 仲裁: Gen 2 达标, 准备投入死母线, 延时 {max(0, int(remaining + 1))}s", "#ffcc00"

    def _handle_live_bus_sync(self, sim, mode1, mode2) -> None:
        fc = sim.fault_config
        # E03: PT3 A 相极性反接，同期装置以反相位置为目标，自动收敛至 180° 错误相位
        _e03 = (fc.active and not fc.repaired and fc.scenario_id == 'E03')

        all_synced = True
        target_phase_deg = np.degrees(self.bus_phase)
        if not sim.gen1.breaker_closed and mode1 == "auto" and sim.gen1.running:
            self.auto_adjust_phase(sim.gen1, sim, target_phase_deg)
            self.arb_msg, self.arb_color = "⚙️ 仲裁: 母线带电，Gen 1 正在捕获相角打同期...", "#ffcc00"
            all_synced = False
        if not sim.gen2.breaker_closed and mode2 == "auto" and sim.gen2.running:
            if _e03:
                # E03 故障：PT3 A 相极性反接导致参考相角反相 180°，
                # 同期装置将 Gen2 驱向错误的 180° 目标相位
                self.auto_adjust_phase(sim.gen2, sim, target_phase_deg + 180.0)
                if all_synced:
                    self.arb_msg, self.arb_color = (
                        "⚠️ 故障: PT3 A相极性反接，同期相角偏差180°，无法完成自动同期！", "#ff4444")
            else:
                self.auto_adjust_phase(sim.gen2, sim, target_phase_deg)
                if all_synced:
                    self.arb_msg, self.arb_color = "⚙️ 仲裁: 母线带电，Gen 2 正在捕获相角打同期...", "#ffcc00"
            all_synced = False
        # E03 手动模式同样需要显示警告
        if _e03 and not sim.gen2.breaker_closed and sim.gen2.running and mode2 != "auto":
            self.arb_msg, self.arb_color = (
                "⚠️ 故障: PT3 A相极性反接，同期相角偏差180°，无法完成自动同期！", "#ff4444")
            all_synced = False
        if all_synced and (sim.gen1.breaker_closed or mode1 != "auto") and (sim.gen2.breaker_closed or mode2 != "auto"):
            self.arb_msg, self.arb_color = "✅ 仲裁器: 全部机组并联运行", "#00ff00"

    def _update_arbitration(self, sim, g1_on_bus, g2_on_bus, ref_freq, ref_amp) -> None:
        mode1 = sim.gen1.mode
        mode2 = sim.gen2.mode

        if sim.remote_start_signal and not sim.paused:
            if mode1 == "auto" and not sim.gen1.running:
                sim.gen1.running = True
                sim.gen1.amp = ref_amp
                sim.gen1.freq = ref_freq
                sim.gen1.actual_amp = ref_amp
            if mode2 == "auto" and not sim.gen2.running:
                sim.gen2.running = True
                sim.gen2.amp = ref_amp
                sim.gen2.freq = ref_freq
                sim.gen2.actual_amp = ref_amp
        else:
            if mode1 == "auto" and sim.gen1.running:
                sim.gen1.running = False
                sim.gen1.breaker_closed = False
            if mode2 == "auto" and sim.gen2.running:
                sim.gen2.running = False
                sim.gen2.breaker_closed = False

        if sim.paused:
            return

        if mode1 == "auto" and sim.gen1.running:
            self.auto_adjust_local(sim.gen1, sim, ref_freq, ref_amp)
        if mode2 == "auto" and sim.gen2.running:
            self.auto_adjust_local(sim.gen2, sim, ref_freq, ref_amp)

        g1_ready = (abs(sim.gen1.freq - GRID_FREQ) < 0.2) and (abs(sim.gen1.actual_amp - GRID_AMP) < 185.0)
        g2_ready = (abs(sim.gen2.freq - GRID_FREQ) < 0.2) and (abs(sim.gen2.actual_amp - GRID_AMP) < 185.0)

        if sim.remote_start_signal:
            if not (g1_on_bus or g2_on_bus):
                if not self._is_sync_test_active():
                    self._handle_dead_bus_selection(sim, mode1, mode2, g1_ready, g2_ready)
                else:
                    self.dead_bus_timer = 0.0
                    self.first_ready = None
            else:
                self._handle_live_bus_sync(sim, mode1, mode2)
        else:
            self.arb_msg, self.arb_color = "🛠️ 仲裁器: 待命 (请闭合远程启动信号)", "#00ff00"
            self.dead_bus_timer = 0.0
            self.first_ready = None

        # ── 第二步特殊追踪：Gen2 追 Gen1，Gen1 小幅抖动 ──────────────────────
        _FREQ_LO, _FREQ_HI = 49.85, 50.15    # Gen1 频率范围 Hz
        _AMP_LO,  _AMP_HI  = 10395.0, 10605.0  # Gen1 幅值范围 V
        # Gen2 慢速追踪步长（秒级响应，约 0.3 Hz/s、15 V/s、0.6°/s）
        _TRK_F  = 0.01     # Hz/帧
        _TRK_A  = 0.5      # V/帧
        _TRK_P  = 0.02     # °/帧
        pt_voltage_check_state = self._get_pt_voltage_check_state()
        pvc_active = (
            pt_voltage_check_state is not None
            and pt_voltage_check_state.started
            and not pt_voltage_check_state.completed
        )
        if pvc_active and not sim.paused:
            # Gen1 有界随机游走，模拟真实发电机微小波动
            if sim.gen1.running:
                sim.gen1.freq = round(
                    max(_FREQ_LO, min(_FREQ_HI,
                        sim.gen1.freq + random.uniform(-0.02, 0.02))), 3)
                # 幅值：随机游走 + 断路器闭合后向额定值的弱收敛偏置（0.5 V/帧）
                _amp_jitter = random.uniform(-5.0, 5.0)
                if sim.gen1.breaker_closed:
                    _amp_err = GRID_AMP - sim.gen1.amp
                    _amp_jitter += min(abs(_amp_err), 0.5) * (1 if _amp_err >= 0 else -1)
                sim.gen1.amp = round(
                    max(_AMP_LO, min(_AMP_HI,
                        sim.gen1.amp + _amp_jitter)), 1)
                # 相位不施加抖动
            # Gen2 起机且断路器断开时，以秒级步长慢速追赶 Gen1
            if sim.gen2.running and not sim.gen2.breaker_closed:
                for _gen, _target, _step, _attr in (
                    (sim.gen2, sim.gen1.freq,      _TRK_F, 'freq'),
                    (sim.gen2, sim.gen1.amp,       _TRK_A, 'amp'),
                    (sim.gen2, sim.gen1.phase_deg, _TRK_P, 'phase_deg'),
                ):
                    _cur = getattr(_gen, _attr)
                    _err = _target - _cur
                    # 相位属性需圆周最短角折叠
                    if _attr == 'phase_deg':
                        _err = (_err + 180.0) % 360.0 - 180.0
                    if abs(_err) <= _step:
                        _new = round(_target, 3)
                    else:
                        _new = round(_cur + (1 if _err > 0 else -1) * _step, 3)
                    # 相位归一化到 (-180°, 180°]
                    if _attr == 'phase_deg':
                        _new = round(((_new + 180.0) % 360.0) - 180.0, 3)
                    setattr(_gen, _attr, _new)
