from dataclasses import dataclass, field
from typing import Optional

from domain.constants import DEFAULT_PT_BUS_RATIO, DEFAULT_PT_GEN_RATIO, DEFAULT_PT3_RATIO
from domain.enums import BreakerPosition, SystemMode


@dataclass
class FaultConfig:
    """
    当前注入的故障场景配置。
    scenario_id = '' 表示无故障（正常模式）。
    """
    scenario_id: str = ""
    active: bool = False
    detected: bool = False      # 物理引擎检测到学员触碰了故障证据，UI 轮询此标志弹窗
    repaired: bool = False      # 学员完成虚拟修复后置 True
    params: dict = field(default_factory=dict)


@dataclass
class GeneratorState:

    "单台发电机当前的状态"

    freq: float
    amp: float      # 电压幅值
    phase_deg: float
    mode: str = "stop"
    running: bool = False
    breaker_closed: bool = False
    breaker_position: str = BreakerPosition.DISCONNECTED
    cmd_close: bool = False
    actual_amp: float = 0.0


@dataclass
class SimulationState:

    "整个仿真系统当前的状态"

    gen1: GeneratorState
    gen2: GeneratorState
    system_mode: str = SystemMode.ISOLATED_BUS
    rotate_phasor: bool = True
    sim_speed: float = 0.3
    # droop_enabled: bool = False
    sync_gain: float = 1.0
    gov_gain: float = 0.75
    first_start_time: int = 10
    multimeter_mode: bool = False
    fault_reverse_bc: bool = False
    remote_start_signal: bool = False
    paused: bool = False
    auto_sync_active: bool = False
    sync_target: Optional[str] = None
    feeder_position: str = BreakerPosition.DISCONNECTED
    feeder_closed: bool = False
    grounding_mode: str = "小电阻接地"
    probe1_node: Optional[str] = None
    probe2_node: Optional[str] = None
    loop_test_mode: bool = False        # 第一步回路检查模式：允许不起机合闸，跳过失压联锁
    pt_gen_ratio: float = DEFAULT_PT_GEN_RATIO   # PT1 (Gen1侧) 变比（可由用户在第二步修改）
    pt3_ratio:   float = DEFAULT_PT3_RATIO       # PT3 (Gen2侧) 变比（可由用户在第二步修改）
    pt_bus_ratio: float = DEFAULT_PT_BUS_RATIO   # PT2 母排侧变比（10500:105 = 100，二次侧额定 105V）
    show_gen_wires: bool = True              # 是否显示机柜内接线（False = 黑盒模式，隐藏连线）
    fault_config: FaultConfig = field(default_factory=FaultConfig)
