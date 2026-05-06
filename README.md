# ThreePhase 三相电并网仿真教学系统

基于 PyQt5 的高压机组并网操作培训桌面应用。当前主流程为隔离母排模式，覆盖五步并网测试、错误场景注入、物理接线黑盒修复、考核模式评分和基础回归测试。

详细实现背景见 [context.md](context.md)，长期维护清单见 [MAINTENANCE_CHECKLIST.md](MAINTENANCE_CHECKLIST.md)。

## 快速开始

当前验证环境：Python 3.11.9。

```bash
pip install PyQt5 matplotlib numpy pytest
python app/main.py
```

运行测试：

```bash
python -m pytest
```

当前回归基线：36 项测试通过。

## 项目结构

```text
ThreePhase/
├── app/
│   ├── main.py                  # 应用入口、PowerSyncController
│   └── controller_signals.py    # Controller 到 UI 的信号总线
├── domain/
│   ├── models.py                # GeneratorState、SimulationState
│   ├── test_states.py           # 五步测试状态
│   ├── fault_scenarios.py       # E01-E14 故障场景
│   ├── assessment.py            # 考核事件、会话、成绩数据结构
│   └── constants.py             # 物理常量
├── services/
│   ├── physics_engine.py        # 物理引擎入口
│   ├── _physics_*.py            # 波形、仲裁、保护、测量 Mixin
│   ├── loop_test_service.py     # 第一步回路测试
│   ├── pt_voltage_check_service.py
│   ├── pt_phase_check_service.py
│   ├── pt_exam_service.py
│   ├── sync_test_service.py
│   ├── fault_manager.py
│   └── scoring/                 # 考核评分规则
├── ui/
│   ├── main_window.py
│   ├── test_panel.py
│   ├── panels/
│   ├── tabs/
│   └── widgets/
├── tests/
├── README.md
└── context.md
```

## 架构概览

```text
PowerSyncUI
  ↑ render_visuals(RenderState)
  ↓ 用户操作
PowerSyncController
  ├── SimulationState
  ├── PhysicsEngine
  ├── FaultManager
  ├── AssessmentCoordinator
  └── 五步测试 Service
```

`SimulationState` 是运行态数据源；`PhysicsEngine` 每帧更新波形、母排仲裁、断路器保护和测量值；五步测试 Service 负责记录、校验和流程推进；UI 只负责展示和采集操作。

## 当前状态

- 已启用 E01-E14；E15/E16 暂时禁用。
- 第一步回路测试已扩展为 `AA/BB/CC/AB/AC/BC` 六组记录。
- E03 可通过 PT3 接线盒二次侧极性标识修复。
- E04 可通过右侧控制台恢复 PT3 额定变比 `11000:193` 修复。
- 第五步完成后会稳定双机到 `50Hz / 10500V / 0°`，并重置波形历史。
- 中性点接地断开显示只隐藏电阻下方三条竖线的下段，保留汇合线、汇合点和电阻连接。
- 考核模式使用 33 个计分点，成绩单由 `services/scoring/` 规则生成。

## 五步测试流程

| 步骤 | 服务 | 核心目标 |
|------|------|----------|
| 1. 回路导通测试 | `LoopTestService` | `AA/BB/CC` 同相导通，`AB/AC/BC` 异相隔离 |
| 2. PT 电压检查 | `PtVoltageCheckService` | PT1/PT2/PT3 三相线电压在额定容差内 |
| 3. PT 相序检查 | `PtPhaseCheckService` | PT1/PT3 相序显示正序、反序或异常 |
| 4. PT 压差考核 | `PtExamService` | 比较机组侧 PT 与母排侧 PT2 的二次相电压矢量差 |
| 5. 同期功能测试 | `SyncTestService` | Gen2 自动追踪 Gen1，满足同期条件后合闸 |

第四步压差计算口径：

```python
gen_ph = gen_line / sqrt(3)
bus_ph = bus_line / sqrt(3)
same_phase = abs(gen_ph - bus_ph)
cross_phase = sqrt(gen_ph**2 + bus_ph**2 + gen_ph * bus_ph)
```

E03 的 PT3 A 相极性反接会改变压差口径：同相变为 `gen_ph + bus_ph`，跨相变为 `sqrt(gen_ph**2 + bus_ph**2 - gen_ph * bus_ph)`。

## 故障场景

| 场景 | 状态 | 故障内容 | 主要检出点 | 修复入口 |
|------|------|----------|------------|----------|
| E01 | 启用 | Gen1 A/B 相接线互换 | 步骤 1、3、4；第五步事故拦截 | 第五步事故弹窗 |
| E02 | 启用 | Gen2 B/C 相接线互换 | 步骤 1、3、4；第五步事故拦截 | G2 机端黑盒 / 事故弹窗 |
| E03 | 启用 | PT3 A 相极性反接 | 步骤 2、3、4；未修复时第五步事故拦截 | PT3 接线盒极性标识 |
| E04 | 启用 | PT3 实际变比 `11000:93` | 步骤 2、4 | 控制台 PT3 变比恢复 `11000:193` |
| E05-E14 | 启用 | Gen1/PT1 接线矩阵故障 | 步骤 1、3、4 | G1/PT1 黑盒渐进式修复 |
| E15-E16 | 禁用 | Gen2 过电压、强行非同期合闸 | 开发中 | 暂无 |

黑盒修复为渐进式：保存某个接线盒后会先写回运行态；只有当前场景涉及的全部可修复目标恢复正常，才会自动清除故障。

## 流程模式

| 模式 | 行为 |
|------|------|
| `teaching` | 教学模式，允许带异常继续收集证据 |
| `engineering` | 工程模式，要求当前步骤合格后才能推进 |
| `assessment` | 考核模式，弱化提示，记录事件流，第四步闭环后生成成绩单 |

E01/E02 的真实修复入口保留在第五步事故弹窗；E03 优先通过 PT3 接线盒修复；E04 通过变比面板修复，不走黑盒门禁。

## UI 入口

- 主窗口：`ui/main_window.py`
- 右侧控制面板：`ui/panels/control_panel.py`
- 测试模式面板：`ui/test_panel.py`
- 母排拓扑：`ui/tabs/circuit_tab/`
- 黑盒接线图：`ui/widgets/pt_wiring_widget.py`、`ui/widgets/gen_wiring_widget.py`

## 测试覆盖

当前测试集中覆盖：

- 考核评分快照
- 黑盒修复编排
- E04 PT3 变比修复
- 第一步六组回路记录
- 物理引擎快照
- 第三步相序判定
- 第五步完成态稳定

常用命令：

```bash
python -m pytest
git -c core.whitespace=cr-at-eol diff --check
```

## 手动录入测试方法

手动录入入口走各 service 的 `origin="manual"` 路径，调用方必须传结构化读数，不能传 `reading`。最小 smoke：

```python
ctrl.loop_svc.record_loop_measurement("AA", origin="manual", continuity="closed")
ctrl.pt_voltage_svc.record_pt_voltage_measurement("PT2", "AB", origin="manual", voltage_sec=105.0)
ctrl.pt_phase_svc.record_phase_sequence("PT1", "ABC", origin="manual")
ctrl.pt_exam_svc.record_pt_diff_measurement(1, "A", "A", origin="manual", voltage_sec=0.0)
```

执行前仍需满足对应步骤的流程前置条件；manual 路径会跳过虚拟表笔位置和 physics 读数校验。hardware 路径在相同结构化读数基础上还必须传 `timestamp` 和 `instrument_id`。

UI 测试面板的四个测量步骤已提供“虚拟表笔录入 / 手动录入（真实仪表）”切换。切到手动录入后，按指引测量对应端子并填写读数，记录仍写入同一个 records dict，可与虚拟表笔记录混用。

启动时若仍看到 matplotlib 字体缓存警告，可忽略；缓存目录已统一指向系统临时目录下的 `matplotlib_threephase`。
