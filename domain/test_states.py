"""
domain/test_states.py
五步测试流程的状态 dataclass 定义。

将原来散布在各 service 工厂方法中的裸字典替换为类型安全的 dataclass，
消除字段漂移风险，使 IDE 可以进行静态补全和类型检查。
"""

from dataclasses import dataclass, field
from typing import Dict, Optional


LOOP_TEST_RECORD_KEYS = ('AA', 'BB', 'CC', 'AB', 'AC', 'BC')


@dataclass
class LoopTestState:
    """第一步：回路连通性测试状态"""
    records: Dict[str, Optional[dict]] = field(
        default_factory=lambda: {k: None for k in LOOP_TEST_RECORD_KEYS}
    )
    completed: bool = False
    feedback: str = (
        "请先断开中性点小电阻，将两台发电机切至手动模式并合闸（不要起机），"
        "再用万用表通断挡逐相测试（万用表靠自身电池注入微小电流判断回路是否连通）。"
    )
    feedback_color: str = '#444444'


_PT_VOLTAGE_CHECK_KEYS = (
    'PT1_AB', 'PT1_BC', 'PT1_CA',
    'PT2_AB', 'PT2_BC', 'PT2_CA',
    'PT3_AB', 'PT3_BC', 'PT3_CA',
)

_PHASE_PAIR_LABEL = {
    frozenset({'A', 'B'}): 'AB',
    frozenset({'B', 'C'}): 'BC',
    frozenset({'C', 'A'}): 'CA',
}


@dataclass
class PtVoltageCheckState:
    """第二步：PT 单体线电压检查状态"""
    records: Dict[str, Optional[dict]] = field(
        default_factory=lambda: {k: None for k in _PT_VOLTAGE_CHECK_KEYS}
    )
    completed: bool = False
    started: bool = False
    feedback: str = (
        "请先完成第一步回路检查，然后恢复小电阻接地，将 Gen1 并入母排，"
        "启动 Gen2（不合闸），开启万用表，分别测量 PT1/PT2/PT3 各相线电压。"
    )
    feedback_color: str = '#444444'


@dataclass
class PtExamState:
    """第四步：PT 二次端子压差考核状态（每台发电机各一份）"""
    records: Dict[str, Optional[dict]] = field(
        default_factory=lambda: {f'{g}{b}': None for g in 'ABC' for b in 'ABC'}
    )
    completed: bool = False
    started: bool = False
    feedback: str = (
        "请先恢复小电阻接地，并将机组并入母排后，"
        "在母排拓扑页完成全部 9 组 PT 端子矢量压差测量（AA~CC）。"
    )
    feedback_color: str = '#444444'


_PT_PHASE_CHECK_KEYS = ('PT1', 'PT3')


@dataclass
class PtPhaseCheckState:
    """第三步：PT 相序检查状态"""
    records: Dict[str, Optional[dict]] = field(
        default_factory=lambda: {k: None for k in _PT_PHASE_CHECK_KEYS}
    )
    completed: bool = False
    started: bool = False
    result: Optional[str] = None   # 'pass' | 'fail' | None
    feedback: str = (
        "请先完成前两步，然后恢复小电阻接地，将 Gen1 并入母排，"
        "起机 Gen2（不合闸），分别接入相序仪至 PT1 和 PT3 检查相序。"
    )
    feedback_color: str = '#444444'


@dataclass
class SyncTestState:
    """第五步：同步功能测试状态"""
    round1_done: bool = False   # Gen1 基准 → Gen2 同步
    round2_done: bool = False   # Gen2 基准 → Gen1 同步
    completed: bool = False
    started: bool = False
    feedback: str = "请先完成第一步（回路测试）至第四步（PT压差测试），再进行同步功能测试。"
    feedback_color: str = '#444444'
