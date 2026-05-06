from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple
import numpy as np


@dataclass
class RenderState:
    # waveform / plot data
    plot_data: Dict[str, Any] = field(default_factory=dict)
    fixed_deg: Optional[np.ndarray] = None
    # bus
    bus_live: bool = False
    bus_amp: float = 0.0
    bus_source: int | str | None = None
    bus_reference_gen: int | None = None
    bus_status_msg: str = ""
    bus_reference_msg: str = ""
    # breakers
    brk1_text: str = ""
    brk1_bg: str = "gray"
    brk1_visual: bool = False
    color_sw1: str = "gray"
    brk2_text: str = ""
    brk2_bg: str = "gray"
    brk2_visual: bool = False
    color_sw2: str = "gray"
    # arbitrator / relay
    arb_msg: str = ""
    arb_color: str = "gray"
    relay_msg: str = ""
    relay_color: str = "gray"
    # CT readings
    i1_rms: float = 0.0
    ip1: float = 0.0
    iq1: float = 0.0
    i2_rms: float = 0.0
    ip2: float = 0.0
    iq2: float = 0.0
    circ_msg: str = ""
    circ_color: str = "gray"
    # grounding / PT
    ground_msg: str = ""
    ground_color: str = "gray"
    pt1_v: float = 0.0
    pt2_v: float = 0.0
    pt3_v: float = 0.0
    # multimeter
    meter_reading: str = "万用表未开启"
    meter_color: str = "black"
    meter_voltage: Optional[float] = None
    meter_status: str = "idle"
    meter_nodes: Optional[Tuple[str, str]] = None
    meter_phase_match: Optional[bool] = None
