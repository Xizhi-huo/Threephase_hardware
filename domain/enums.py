# ========== 系统运行模式枚举 ==========
class SystemMode:
    ISOLATED_BUS = "隔离母排"     # 无外部电网，母排由首台并入的机组建立电压
    ISLAND = "孤岛运行"           # (预留) 脱网后的负载-发电平衡模式
    GRID_TIED = "并网运行"        # (预留) 外接无穷大电网，经典同期并网
    BLACKSTART = "黑启动"         # (预留) 全站失电后的恢复启动流程


AVAILABLE_MODES = [
    SystemMode.ISOLATED_BUS,
    SystemMode.ISLAND,
    SystemMode.GRID_TIED,
    SystemMode.BLACKSTART,
]


# 断路器物理位置枚举
class BreakerPosition:
    DISCONNECTED = "脱开位置"    # 绝缘测试用
    TEST = "试验位置"            # 单机调试二次回路用
    WORKING = "工作位置"         # 并网用
