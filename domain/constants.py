# 用户可见量：额定线电压 RMS (V)
GRID_AMP  = 10500.0   # 10.5 kV — gen.amp 及所有 UI 控件使用此单位
GRID_FREQ = 50.0
SYNC_FREQ_OK_HZ = 0.5
SYNC_VOLT_OK_V = 490.0
SYNC_PHASE_OK_DEG = 15.0
XS = 1.0                         # 线路等效阻抗
TRIP_CURRENT = 300.0             # 高压系统继电保护跳闸阈值放大为 300A
MAX_POINTS = 200

# CT 电流互感器参数
CT_PRIMARY_A = 500.0             # CT 一次侧量程 (500A)
CT_SECONDARY_A = 5.0             # CT 二次侧标准输出 (5A 标准)
CT_RATIO = CT_PRIMARY_A / CT_SECONDARY_A  # 变比 (100:1)

# PT 变比参数。UI 行默认值、仿真默认值和故障注入都应从这里取值，避免场景切换后状态残留。
DEFAULT_PT_RATIO_ROWS = {
    "pt_gen_ratio": (11000, 193),
    "pt3_ratio": (11000, 193),
    "pt_bus_ratio": (10500, 105),
}
DEFAULT_PT_GEN_RATIO = DEFAULT_PT_RATIO_ROWS["pt_gen_ratio"][0] / DEFAULT_PT_RATIO_ROWS["pt_gen_ratio"][1]
DEFAULT_PT3_RATIO = DEFAULT_PT_RATIO_ROWS["pt3_ratio"][0] / DEFAULT_PT_RATIO_ROWS["pt3_ratio"][1]
DEFAULT_PT_BUS_RATIO = DEFAULT_PT_RATIO_ROWS["pt_bus_ratio"][0] / DEFAULT_PT_RATIO_ROWS["pt_bus_ratio"][1]

E04_PT3_RATIO_ROW = (11000, 93)
E04_PT3_RATIO = E04_PT3_RATIO_ROW[0] / E04_PT3_RATIO_ROW[1]

NEUTRAL_RESISTOR_OHMS = 10.0     # 中性点接地小电阻 (10Ω，高压机组常用)

# 下垂控制系数 (本轮已停用，保留注释便于后续恢复)
# KP_DROOP = 0.0005
# KQ_DROOP = 0.0002
