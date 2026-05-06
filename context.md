# ThreePhase 项目上下文文档

> 供新对话快速理解项目全貌，可直接作为 Claude 对话开头的参考材料。详细的用户文档见 README.md。

---

## 项目简介

**三相电并网仿真教学系统**（ThreePhase Synchronization Training System）

基于 PyQt5 的桌面应用，模拟高压机组并网前的"隔离母排"操作流程，供电力系统操作员培训使用。系统包含完整的物理仿真、交互式测量工具、五步测试工作流，以及 14 个错误场景训练模块（E15/E16 暂时禁用，代码已注释保留）。

**入口**：`python app/main.py`（从项目根目录运行）

---

## 目录结构

```
ThreePhase/
├── app/
│   ├── main.py              # 应用入口、PowerSyncController（总控制器）
│   └── controller_signals.py # Controller → UI 信号总线（R43）
├── domain/                  # 领域模型与常量
│   ├── constants.py         # 物理参数（电压、频率、阻抗等）
│   ├── enums.py             # 系统模式、断路器状态枚举
│   ├── models.py            # GeneratorState、SimulationState 数据类
│   ├── assessment.py        # 考核模式事件 / 会话 / 成绩结果数据结构
│   ├── test_states.py       # 各步骤状态类（LoopTestState 等）
│   ├── fault_scenarios.py   # 错误场景定义（当前启用 E01-E14，E15/E16 已注释禁用）
│   └── node_map.py          # 测量节点坐标
├── services/                # 业务逻辑与物理引擎
│   ├── physics_engine.py    # 物理引擎主类（Mixin 组合）
│   ├── _physics_core.py     # 波形生成 Mixin
│   ├── _physics_arbitration.py  # 母线仲裁与同步 Mixin
│   ├── _physics_protection.py   # 继电保护与断路器逻辑 Mixin
│   ├── _physics_measurement.py  # PT/万用表测量 Mixin
│   ├── loop_test_service.py     # 第1步：回路导通测试
│   ├── pt_voltage_check_service.py  # 第2步：PT电压检查
│   ├── pt_phase_check_service.py    # 第3步：PT相序检查
│   ├── pt_exam_service.py           # 第4步：PT压差考核
│   ├── sync_test_service.py         # 第5步：同期功能测试
│   ├── fault_manager.py             # 故障注入/修复与可修复接线目标管理
│   ├── blackbox_repair_handler.py   # 黑盒修复编排器
│   ├── hardware_actions.py          # 启停机/合闸等硬件动作编排
│   ├── assessment_coordinator.py    # 考核会话汇聚与闭环判定
│   └── assessment_service.py        # 考核模式自动评分与成绩汇总
├── ui/                      # PyQt5 用户界面（Mixin 拼装）
│   ├── main_window.py       # PowerSyncUI 主窗口
│   ├── styles/              # 浅色主题入口与全局 QSS 设计令牌子包
│   ├── test_panel.py        # 测试模式控制面板主控（含第1~5步控制台）
│   ├── panels/
│   │   └── control_panel.py # 右侧控制面板 Mixin
│   ├── tabs/
│   │   ├── _step_style.py   # 步骤页通用样式辅助
│   │   ├── waveform_tab.py      # Tab 0: 波形 & 相量图
│   │   ├── circuit_tab/         # Tab 1: 母线拓扑子包（入口 + 相序/记录表/绘图）
│   │   ├── loop_test_tab.py     # Tab 2: 回路测试 UI
│   │   ├── pt_voltage_check_tab.py  # Tab 3: PT电压检查 UI
│   │   ├── pt_phase_check_tab.py    # Tab 4: PT相序 UI
│   │   ├── pt_exam_tab.py           # Tab 5: PT压差 UI
│   │   └── sync_test_tab.py         # Tab 6: 同期测试 UI
│   └── widgets/
│       ├── multimeter_widget.py # 数字万用表 UI（QPainter绘制）
│       └── phase_seq_meter.py   # 相序计 UI
├── adapters/
│   └── render_state.py      # RenderState 数据类（UI渲染快照）
├── README.md                # GitHub 项目文档
└── context.md               # Claude 对话上下文摘要
```

---

## 架构概览

```
PowerSyncUI (View - 多 Mixin)
        ↑ render_visuals(RenderState)
        ↑ ControllerSignals（R43 最小试点）
        ↓ 用户操作事件
PowerSyncController (Application Layer - app/main.py)
  - 持有 SimulationState（唯一数据源）
  - 持有 PhysicsEngine 实例
  - 持有 FaultManager（故障注入/修复与接线目标判断）
  - 持有 AssessmentCoordinator（考核会话、事件与闭环汇聚）
  - 持有 5 个测试服务实例
  - 33ms 定时器驱动主循环
        ↑ build_render_state()
        ↓ update_physics()
PhysicsEngine（4个Mixin组合）
  ├─ WaveformMixin:      三相正弦波形生成
  ├─ ArbitrationMixin:   母线仲裁 & 自动同步（类PLL）
  ├─ ProtectionMixin:    继电保护 & 断路器联锁
  └─ MeasurementMixin:   PT二次侧电压 & 万用表读数
        ↑ 读取 sim_state
        ↓ 更新测量值
Domain Models
  - GeneratorState: 频率、幅值、相位、断路器状态
  - SimulationState: 双机状态、故障配置、接地模式
  - FaultConfig: 故障场景注入参数
```

## 当前维护状态（截至 2026-04 最新功能同步）

- **Phase 4 已真正收官。** R33–R44 已完成，`services/` 目录下 repo 级 `self._ctrl | self.ctrl` 计数已归零。
- `R49-Round2` 已完成 `ui/styles/` 子包化：主题入口从单文件 `ui/styles.py` 收敛为 `ui/styles/`，`apply_app_theme()` / `build_app_stylesheet()` 导入面保持不变。
- 业务 service 与 physics 层都已完成显式依赖注入收口；physics 不再持有 `ctrl`，service 不再持有 `self._ctrl`。
- R43 已建立 `ControllerSignals(QObject)` 骨架，并在主窗口状态栏落地两个最小文本试点；`_tick -> render_visuals` 仍保留为默认渲染路径，阶段 3（轮询压缩）尚未执行。
- R44 已把事故链路收口为 `queue_accident_dialog(...)` 行为回调，物理层不再直接弹 UI 模态对话框。
- 第一步回路测试已扩展为六组记录：`AA/BB/CC` 同相导通、`AB/AC/BC` 异相隔离；测试页、测试面板快捷按钮和母排拓扑记录表均已同步。
- E03/E04 已具备考核模式可完成的修复路径：E03 通过 PT3 接线盒二次侧极性标识修复，E04 通过右侧控制台 PT3 变比恢复额定值修复。
- 第五步完成后会稳定双机并联状态并重置波形历史；第二步 PT 电压跟踪在完成后停止，避免后续步骤断路器抖动。
- 母排拓扑中性点断开显示只隐藏三条竖线下段，保留上段、横向汇合线、汇合点、到电阻的竖线和电阻本体。
- 当前自动化回归：`python -m pytest` 共 30 项通过。
- **注意**：Phase 4 收官不等于整份维护清单全部完成；旧键名兼容、状态真值源收口、死代码/重复 UI 清理、类型标注等后续项仍待推进。

---

## 核心数据模型

### GeneratorState（domain/models.py）
| 字段 | 含义 |
|------|------|
| `freq` | 发电机频率（Hz） |
| `amp` | 输出电压幅值（V，线电压RMS） |
| `phase_deg` | 相位（度） |
| `mode` | 手动/自动 |
| `breaker_closed` | 主断路器状态 |
| `running` | 是否启机 |

### SimulationState（domain/models.py）
| 字段 | 含义 |
|------|------|
| `gen1`, `gen2` | 两台发电机状态 |
| `system_mode` | 当前系统模式（目前仅启用 ISOLATED_BUS 隔离母排） |
| `fault_config` | 当前激活的故障场景配置 |
| `fault_reverse_bc` | Gen2 B/C相内部反相兼容标志（当前主要保留给手动陷阱开关） |
| `pt_gen_ratio` | PT1（Gen1侧）变比，默认 11000/193 ≈ 56.99；步骤2可配置 |
| `pt3_ratio` | PT3（Gen2侧）变比，默认 11000/193 ≈ 56.99；E04注入时改为 11000/93 ≈ 118.28 |
| `pt_bus_ratio` | PT2（母排侧）变比，默认 10500/105 = 100；二次侧额定 105V |
| `grounding_mode` | "小电阻接地" / "断开" |
| `probe1_node`, `probe2_node` | 万用表表笔位置 |
| `loop_test_mode` | 第1步回路测试专用模式 |

**PT变比分离设计**：PT1与PT3各用独立字段（`pt_gen_ratio` / `pt3_ratio`），是为了支持E04场景（仅PT3变比错误，PT1保持正确）。步骤2控制台分三行分别显示并可独立修改。

---

## 五步测试工作流

| 步骤 | 服务类 | 电气状态 | 核心验证 |
|------|--------|----------|----------|
| 1. 回路导通测试 | `LoopTestService` | 双机手动/工作位/合闸/未启机，拆除接地电阻 | AA/BB/CC 同相导通；AB/AC/BC 异相隔离；检出相序接线错误 |
| 2. PT电压检查 | `PtVoltageCheckService` | Gen1并网，Gen2运行但断路器分闸 | PT1/PT2/PT3三相线电压，±15%容差（额定10.5kV） |
| 3. PT相序检查 | `PtPhaseCheckService` | 同步骤2 | PT1/PT3相序表仅显示正序 / 反序 / 异常；记录链路不再向学员暴露具体三字母顺序 |
| 4. PT压差考核 | `PtExamService` | 分两个子测试（Gen1/Gen2交替上母线） | 9对PT端子间向量压差；验证同期就绪 |
| 5. 同期功能测试 | `SyncTestService` | Gen2自动模式追踪Gen1 | Δf<0.5Hz，ΔV<500V，Δθ<15°收敛后合闸 |

### 第一步特殊行为
- `LoopTestState.records` 默认键为 `AA / BB / CC / AB / AC / BC`
- `AA / BB / CC` 期望导通 `≈0Ω`
- `AB / AC / BC` 期望断路 `∞Ω`
- 跨相断路是正常结果，记录时以 `passed=True` 写入；跨相异常导通才会触发回路异常判断
- 母排拓扑页第一步记录表已同步为六行，并按 `passed` 字段着色

### 第二步特殊行为（_physics_arbitration.py）
- Gen1 以 ±0.02Hz / ±5V 随机游走模拟真实抖动（仅 Auto 模式）
- Gen2 以秒级步长慢速追赶 Gen1（仅 Auto 模式）
- **手动模式下两台机组均不受自动追踪影响，学员可自由调参**
- 第二步测试面板的滑块加有 `sl.isSliderDown()` 保护，拖动时不被每帧渲染覆盖

### 第四步 PT 压差公式
- 机组侧 PT：Gen1 使用 PT1，Gen2 使用 PT3；母排侧固定使用 PT2
- 相电压换算：`gen_ph = gen_line / sqrt(3)`，`bus_ph = bus_line / sqrt(3)`
- 同相压差：`abs(gen_ph - bus_ph)`
- 跨相压差：`sqrt(gen_ph² + bus_ph² + gen_ph·bus_ph)`
- E03 PT3 A 相极性反接：同相为 `gen_ph + bus_ph`，跨相为 `sqrt(gen_ph² + bus_ph² - gen_ph·bus_ph)`

---

## 错误场景（domain/fault_scenarios.py）

> 当前启用 E01–E14，E15/E16（原E05/E06）代码已注释禁用（开发中）。
> E01/E02 为 Gen2/PT3 侧接线场景；E05–E14 为 Gen1/PT1 侧接线矩阵场景。

### 非接线类故障（E01–E04）

| 编号 | 状态 | 故障内容 | 检出步骤 | 第五步行为 | 风险等级 |
|------|------|----------|----------|------------|----------|
| E01 | ✅ 启用 | Gen1 A/B相接线互换 | 步骤1（回路断路）+ 步骤3（相序异常）+ 步骤4（压差矩阵异常） | Gen2合闸触发**致命事故弹窗** | recoverable |
| E02 | ✅ 启用 | Gen2 B/C相接线互换 | 步骤1（回路断路）+ 步骤3（相序异常）+ 步骤4（压差矩阵异常） | Gen2合闸触发**致命事故弹窗** | recoverable |
| E03 | ✅ 启用 | PT3 A相极性反接 | 步骤2（PT3_AB/CA≈106V标红）+ 步骤3（PT3_A相位不匹配）+ 步骤4（A行压差异常）；可在 PT3 接线盒修复极性 | 未修复时 Gen2追踪收敛至180°错误相位；强行合闸触发**致命事故弹窗** | accident |
| E04 | ✅ 启用 | PT3实际变比11000:93（≈118.28），额定应为11000:193（≈56.99） | 步骤2（PT3二次侧≈88V标红）+ 步骤4（PT3各行压差偏小）；可在控制台恢复 PT3 额定变比修复 | 无事故弹窗 | recoverable |

### Gen1/PT1 接线矩阵场景（E05–E14）

信号链：Gen1 → [G节点] → Bus → [P1节点] → PT1一次侧 → [P2节点] → PT1二次侧

| 编号 | 状态 | 场景名 | G节点 | P1节点 | P2节点 | pt1_phase_order | 步骤1 | 步骤3 | 步骤4 | 诊断难度 |
|------|------|--------|-------|--------|--------|----------------|-------|-------|-------|---------|
| E05 | ✅ 启用 | 反反反(同) | A↔B | A↔B | A↔B | BAC | ❌断路 | ❌逆序 | ⚠️A端0V陷阱 | 中 |
| E06 | ✅ 启用 | 正反正 | 正 | A↔B | 正 | BAC | ✅ | ❌逆序 | ❌全相183V | 中 |
| E07 | ✅ 启用 | 正正反 | 正 | 正 | A↔B | BAC | ✅ | ❌逆序 | ❌全相183V | 中（同E06，需拆检区分） |
| E08 | ✅ 启用 | 正反反(同)·完全隐性 | 正 | A↔B | A↔B | ABC(隐) | ✅ | ✅假正序 | ✅假0V | 🔴最高（四步全过） |
| E09 | ✅ 启用 | 反正反(同) | A↔B | 正 | A↔B | ABC(隐) | ❌断路 | ✅假正序 | ❌全相183V | 高 |
| E10 | ✅ 启用 | 反反正(同) | A↔B | A↔B | 正 | ABC(隐) | ❌断路 | ✅假正序 | ❌全相183V | 高（同E09，需拆检区分） |
| E11 | ✅ 启用 | 正反反(不同) | 正 | A↔B | B↔C | CAB | ✅ | ✅假正序 | ❌三相全183V | 🔴最高（步骤四唯一出路） |
| E12 | ✅ 启用 | 反正反(不同) | A↔B | 正 | B↔C | CAB | ❌断路 | ✅假正序 | ⚠️A端0V陷阱/B端183V | 极高 |
| E13 | ✅ 启用 | 反反正(不同) | A↔B | B↔C | 正 | CAB | ❌断路 | ✅假正序 | ⚠️A端0V陷阱/B端183V | 极高（同E12，需拆检区分） |
| E14 | ✅ 启用 | BAC×ACB×CAB三级互消 | BAC | B↔C | CAB | ABC(隐) | ❌断路 | ✅假正序 | ⚠️C端0V陷阱/A/B端183V | 极高 |

> 表中 `G / P1 / P2` 列表示“本级接线置换”的场景定义，不是黑盒逐级传播后的实际显示结果。
> 例如 `E12`：场景定义为 `G = BAC`、`P1 = 正`、`P2 = B↔C`，但按黑盒传播规则，PT1 一次侧实际显示结果应为 `BAC`，PT1 二次侧最终显示结果应为 `BCA`。

### 暂时禁用

| 编号 | 故障内容 |
|------|---------|
| E15（原E05）| Gen2过电压（13000V，AVR故障） |
| E16（原E06）| Gen2相角追踪禁用（强制非同期合闸） |

### E04 场景详解（关键设计）

E04 的核心：PT3 **硬件实际变比** 为 118.28，但**额定铭牌**应为 56.99。系统注入E04时：
- `sim.pt3_ratio` 设为 118.28（控制台同步显示 11000:93，让学员看到真实变比）
- 物理测量也用 118.28，二次侧输出 ≈ 10500/118.28 ≈ **88.8V**
- **阈值比较使用额定变比 56.99**（在 `_physics_measurement.py` 和 `pt_voltage_check_service.py` 中均做特殊处理）：阈值范围 8925/56.99 ≈ 156.6V ~ 211.9V，88.8V 远低于下限 → **红色[异常]**
- 检测触发：`meter_status == 'danger'` 时置 `fc.detected = True`
- 记录表格：`primary_v = meter_v_sec × 56.99 ≈ 5060V`，不在 [8925, 12075]V → 表格也标红
- 反馈文本中"偏离额定"显示动态计算的额定二次侧值（PT3为184V，PT2为105V），不再硬编码
- 学员在右侧控制台把 PT3 变比恢复为额定 `11000:193` 后，`FaultManager.maybe_repair_pt_ratio_fault()` 会自动清除 E04，并要求重新记录受影响的 PT3 数据

### E01 / E02 / E03 事故触发机制（关键设计）

E01/E02/E03 均在步骤1~4可被检出，但 E01/E02 不在进入步骤5时弹修复对话框。E03 已可通过 PT3 接线盒提前修复极性；若未修复，事故仍在 Gen2 断路器合闸瞬间触发，有**两层拦截**：

**第一层（UI层，app/main.py `toggle_breaker()`）**：
```python
# 仅当 is_sync_test_active()（步骤5同期测试进行中）才拦截手动合闸
if fc.scenario_id == 'E01': show_e01_accident_dialog(); return
if fc.scenario_id == 'E02': show_e02_accident_dialog(); return
if fc.scenario_id == 'E03': show_e03_accident_dialog(); return
# → cmd_close 不被设置，合闸请求被完全阻断
```

**第二层（物理层，_physics_protection.py `_update_breaker_state()`）**：
```python
# 兜底：sync_ok=True 分支（E01/E02/E03 auto 合闸拦截）
if fc.scenario_id == 'E01': queue_accident_dialog('E01')
elif fc.scenario_id == 'E02': queue_accident_dialog('E02')
elif fc.scenario_id == 'E03': queue_accident_dialog('E03')
# → 物理层只登记待显示事故；帧末再统一弹窗

# 额外：E03 sync_ok=False 分支（180°相位差时 manual 强行合闸）
if fc.scenario_id == 'E03': queue_accident_dialog('E03')
# → 物理层统一排队事故；帧末由 controller/UI 统一消费
```

弹窗说明：事故原因、可见异常现象、修复方法。学员选"修复故障"→ `repair_fault()` → 可继续第五步。

- `ui/main_window.py::_check_fault_detection()` 现在对 `danger_level == 'accident'` 的场景直接返回，只保留检测状态与横幅，不在步骤 1~4 提前弹修复框。
- 因此 E01/E02 的修复入口统一保留在第五步真实事故弹窗；E03 优先通过 PT3 接线盒极性修复，事故弹窗只作为未修复时兜底。
- 事故弹窗链路已改为“物理层排队、主循环帧末消费”，避免物理更新过程中直接进入模态对话框。

**事故场景步骤 1~4 弹窗策略**：
- `_check_fault_detection()`（main_window.py）不再在检测阶段弹修复框；事故场景只保留异常数据与状态更新
- `test_panel.py` 第五步前修复关卡会排除 `('E01','E02')` 这类事故合闸修复场景；E03 通过 PT3 接线盒极性修复路径处理
- 结果：步骤 1~4 学员只看到异常测量值与流程提示；事故仅在步骤 5 合闸触发

**E03 工程原理**：PT3 A 相极性反接使同期装置参考角偏差 180°。`_handle_live_bus_sync` 中 E03 激活时，`auto_adjust_phase` 目标改为 `target_phase_deg + 180°`，Gen2 收敛至反相位置；sync_ok=False，仲裁器显示红色警告。学员若仍强行合闸，触发事故弹窗。

**E01/E02 工程原理**：自动同步以 A 相参考角收敛（Δf/ΔV/Δθ 均满足），同期仪误判条件满足，但 E01 合闸后 A/B 错相 120° 短路，E02 合闸后 B/C 跨相 120° 短路。物理引擎单相等效电路无法计算跨相电流，故在保护层硬编码拦截。

### 故障注入机制（通用流程）
1. 教师在右侧控制面板选择故障场景
2. `FaultConfig` 注入 `SimulationState`（及 `g2_blackbox_order` / `fault_reverse_bc` 等专属标志）
3. `PhysicsEngine` 读取故障参数扭曲测量值
4. UI 轮询 `fault_config.detected` 标志，更新横幅提示
5. 第五步前黑盒门禁会检查运行态黑盒状态；只要当前场景仍有未恢复的物理接线，就会停留在第四步并弹出“必须先去黑盒修复”的提示，不能直接进入同步测试
   - E05–E14：检查 `g1_blackbox_order` / `pt1_pri_blackbox_order` / `pt1_sec_blackbox_order`
   - E02：检查 `g2_blackbox_order`
6. 黑盒内实际修复完成 → `repair_fault()` → `repaired = True`，允许继续测试
7. E01/E02 例外：修复时机在第五步合闸事故弹窗内；E03 可在 PT3 接线盒提前修复极性，事故弹窗仅作为未修复兜底

### 流程模式策略（teaching / engineering / assessment）

- 控制器在 `app/main.py` 中统一维护 `FLOW_MODE_POLICIES`，`test_flow_mode` 通过策略表映射到一组流程规则。
- `FLOW_MODE_POLICIES` 的值已收敛为 `FlowModePolicy` 强类型配置；控制器通过属性访问读取策略，不再依赖裸字典 `get()`。
- Service / UI 不再直接散落写“教学模式 / 工程模式 / 考核模式”判断，改为读取控制器语义接口：
  - `can_advance_with_fault()`
  - `should_block_step5_until_blackbox_fixed()`
  - `should_hold_at_step4_when_wiring_fault_unrepaired()`
  - `should_show_fault_detected_banner()`
  - `can_inspect_blackbox()` / `can_repair_in_blackbox()`
- 当前三模式的核心差异：
  - `teaching`：发现异常后，只要本步测量项做完，就允许完成该步并继续收集证据
  - `engineering`：要求本步结果合格后才能完成并推进
  - `assessment`：要求本步结果合格后才能推进；弱化横幅与诊断提示；记录完整过程事件；第四步闭环完成后自动结算成绩，第五步不计分
    - 在第一步回路测试未完成前，母排拓扑图默认隐藏发电机与母排之间的连线；第一步完成后自动恢复显示
    - 随机故障考核在第四步成绩单弹出前会先要求学员提交最终场景判断
    - 第四步未完成时点击“完成第四步测试”不再给缺项提示，直接记入违规推进事件并进入评分
- 当前三模式保持一致的策略：
  - 都要求先完成本步规定测量项
  - 存在可修复黑盒目标的场景要求第五步前完成真实修复；E01/E02 仍保留第五步事故弹窗修复入口，E03 优先走 PT3 极性修复
  - 都允许黑盒查看与交互修复
- `assessment` 模式的附加约束：
  - 管理员快捷按钮禁用
  - 结果以 `AssessmentSession` + `AssessmentResult` 表达
  - 评分范围限定在步骤1~4与黑盒修复闭环
  - 场景选择弹窗已改为“故障场景滚动列表 + 固定流程模式区”，三种模式选项始终可见

### 考核模式实现落点

- 数据结构：
  - `domain/assessment.py`
    - `AssessmentEvent`
    - `AssessmentPenalty`
    - `AssessmentSession`
    - `AssessmentResult`
- 控制器：
  - `app/main.py`
    - 维护 `assessment_session`
    - 提供 `start_assessment_session()` / `append_assessment_event()` / `finish_assessment_session()`
    - 提供 `mark_fault_detected(step, source, ...)`，在真实发现点统一记录故障事件
    - 在黑盒修复完成、事故误操作时补记事件
    - 结算前冻结 `state_snapshot`，供评分稳定读取
- 评分服务：
  - `services/assessment_service.py`
    - 根据事件流与 `AssessmentSession.state_snapshot` 计算总分、分项满分、完整计分点、扣分项、否决原因、统计指标
    - 当前采用 **33 个细分计分点** 的 100 分制：
      - 流程纪律 16
      - 第一步回路测试 10
      - 第二步 PT 电压检查 12
      - 第三步 PT 相序检查 12
      - 第四步压差考核 16
      - 异常识别与故障定位 14
      - 黑盒修复 12
      - 效率与规范性 8
    - 33 个计分点按 `A1-H2` 输出到成绩单详细表，覆盖步骤顺序、各步记录完整性、显性/隐性故障识别、定位、黑盒修复与效率控制；第一步现在对应 `B1-B7`，其中 `B1-B6` 分别对应 `AA/BB/CC/AB/AC/BC` 六组回路记录
    - `E08` 这类隐性故障若依赖第四步闭环门禁后才发现问题，会丢失“隐性故障识别 / 定位不依赖系统门禁”等关键分项，不再可能满分
    - `measurement_invalid` 事件流已接入步骤 1~4 的无效记录路径，现用于 `D3`、`E3`、`H2` 等细分计分点
    - 黑盒定位与修复评分已升级为层级级目标：`G1.terminal`、`PT1.primary`、`PT1.secondary`、`G2.terminal`
    - 额外扣分当前包括：前两步每打开一次 PT 黑盒额外扣 10 分；随机故障考核最终场景判断错误额外扣 10 分
- UI 入口：
  - `ui/panels/control_panel.py`：在场景选择弹窗中提供 `assessment` 模式
  - `ui/test_panel.py`：记录步骤进入、完成尝试、黑盒操作，并在第四步闭环完成时弹出表格化成绩单
  - `ui/test_panel.py::_on_record_psm()` 已改为通过控制器 `record_phase_sequence()` 调用 `PtPhaseCheckService.record_phase_sequence()`，UI 不再直接改第三步记录状态或直接设置 `fault_config.detected`
  - `ui/main_window.py`：考核模式下的第四步闭环门禁提示改为弱提示，只提示“当前考核尚未闭环”，不再泄露具体故障位置

### 考核闭环判定补充

- `is_assessment_closed_loop_ready()` 现在只会对“存在可修复黑盒目标”的场景强制要求 `fault_config.repaired == True`
- 因此像 E04 这类非黑盒接线故障不会卡在黑盒门禁；学员需在右侧控制台把 PT3 变比恢复为额定 `11000:193`，重新记录正常数据后再完成考核闭环
- 考核模式下，步骤 1 / 3 与物理万用表故障提示都会通过 `should_show_diagnostic_hints()` 自动降级为非定位性提示，系统只给状态，不直接给出接线位置答案

### 考核模式当前记录的核心事件

- `assessment_started`
- `step_entered`
- `step_finalize_attempted`
- `step_completed`
- `advance_blocked`
- `measurement_recorded`
- `fault_detected`
- `blackbox_opened`
- `blackbox_swap`
- `blackbox_confirm_attempted`
- `fault_repaired`
- `hazard_action`
- `assessment_finished`
- `fault_detected` 不再由 `_tick()` 用 `step=0` 补记，评分中的“首次发现异常步骤”现在按真实检测步骤统计
- E01/E02 的事故弹窗修复入口现在按 `step=5` 记录 `fault_repaired`，不再误记为第四步修复；E03 优先通过 PT3 接线盒极性标识提前修复，若未修复才走第五步事故兜底

### Gen1/PT1 接线矩阵注入机制（E05–E14，通用参数驱动）

**params 字段**：
- `pt1_phase_order`（必填）：PT1 二次侧净相序，如 `['B','A','C']`（BAC）或 `['A','B','C']`（隐性正序）。注入时写入 `pt_phase_orders['PT1']`，修复时还原为 `['A','B','C']`。
- `g1_loop_swap`（可选）：Gen1 机端对调端子对，如 `('A','B')`。
- `g1_blackbox_order`（可选）：G1 机端接线盒黑盒图显示用，有 G1 换相的场景才有。
- `p1_pri_blackbox_order`（可选）：PT1 一次侧本级接线置换（黑盒图显示用）。
- `pt2_sec_blackbox_order`（可选）：PT1 二次侧本级接线置换（黑盒图显示用）。

**三处关键注入（`inject_fault`）**：
```python
# 1. PT1 端子相序（净效果）
pt1_order = fc.params.get('pt1_phase_order')
if pt1_order:
    pt_phase_orders['PT1'] = list(pt1_order)

# 2. Gen1 换相同步影响母排（Bus）：Gen1 A↔B → Bus_A 载 B 相
#    E01 已在上方显式设置 PT2，此处跳过避免二次交换覆盖 E01 的设定
swap = fc.params.get('g1_loop_swap')
if swap and scenario_id != 'E01':
    p1, p2 = swap
    new_pt2 = list(pt_phase_orders['PT2'])
    new_pt2[i1], new_pt2[i2] = new_pt2[i2], new_pt2[i1]
    pt_phase_orders['PT2'] = new_pt2

# 3. E01 专属：Gen1 A/B 对调同时更新 PT1 和 PT2
if scenario_id == 'E01':
    pt_phase_orders['PT1'] = ['B', 'A', 'C']
    pt_phase_orders['PT2'] = ['B', 'A', 'C']
```
> **设计原因**：若仅更新 PT1 而不更新 PT2，步骤四 cross-PT 压差计算会将 Bus 端子误判为 A 相，导致 E05 的"0V陷阱"变成 183V，E09/E10/E14 的 183V 异常变成 0V，E12/E13 的"A端0V陷阱"消失。
>
> **E01 double-swap bug（已修复）**：E01 params 含 `g1_loop_swap: ('A','B')`，如果通用 swap 块不加 `scenario_id != 'E01'` 守卫，会在 E01 显式设置 `PT2=['B','A','C']` 之后再次交换，将其还原成 `['A','B','C']`。守卫已加入。

**`g1_blackbox_order` 是 G1 机端物理接线的运行态真值源**：
- `inject_fault` 写入（E01/E05-E14）
- 黑盒修复对话框写入（用户手动调整后）
- `repair_fault` 重置为 `['A','B','C']`
- `resolve_loop_node_phase` 直接读取（不再从 `g1_loop_swap` 参数推导）：
```python
def resolve_loop_node_phase(self, node_name):
    _, gen_name, terminal = node_name.split('_', 2)
    if gen_name == 'G1':
        idx = ('A', 'B', 'C').index(terminal)
        return self.pt_phase_orders['PT2'][idx]
    if gen_name == 'G2':
        idx = ('A', 'B', 'C').index(terminal)
        return self.g2_blackbox_order[idx]
    return terminal
```

**步骤一断路检测**（`_physics_measurement.py`）：
```python
# E01/E02 硬编码 + E05–E14 通用（凡有 g1_loop_swap 的场景）
if fc.params.get('g1_loop_swap') or fc.params.get('g2_loop_swap'):
    fc.detected = True   # 回路断路时触发
```
触发场景：E05 / E09 / E10 / E12 / E13 / E14。

**步骤四异相检测**（`_physics_measurement.py`）：
```python
# E05–E14 通用：PT1 端子与 Bus 相位不匹配时触发
elif (gen_pt_name == 'PT1'
      and fc.params.get('pt1_phase_order') is not None
      and not is_same_phase):
    self._mark_fault_detected(step=4, source='pt_exam_measurement', ...)
```
覆盖 E06 / E07 / E11（步骤一无断路，仅步骤四能暴露）。
E08（pt1_phase_order=['A','B','C'] 且无 g1_loop_swap）永远不触发——完全隐性设计。

**第三步相序仪快捷记录语义**（`ui/test_panel.py::_on_record_psm` → `PowerSyncController.record_phase_sequence()` → `PtPhaseCheckService.record_phase_sequence()`）：
- 读取相序仪当前三字母结果，如 `ABC` / `BCA` / `CAB` / `ACB`
- 对 `PT1_A/PT1_B/PT1_C` 或 `PT3_*` 三条记录逐相写入：
  - `actual_phase = seq[index]`
  - `phase_match = (actual_phase == 期望端子名)`
- 因此 `BCA` / `CAB` 虽属于正序组，但会被记录成“端子错位失败”，不再被简化成三相全对

**各场景步骤四预期电压**：
| 场景 | Bus_A | PT1_A | A端压差 | B端压差 | C端压差 |
|------|-------|-------|---------|---------|---------|
| E05 | B相 | B相 | **0V** (陷阱) | **0V** (陷阱) | 0V |
| E06 | A相 | B相 | **183V** ❌ | 183V ❌ | 0V |
| E07 | A相 | B相 | **183V** ❌ | 183V ❌ | 0V |
| E09/E10 | B相 | A相 | **183V** ❌ | 183V ❌ | 0V |
| E11 | A相 | B相 | **183V** ❌ | 183V ❌ | 183V ❌ |
| E12/E13 | B相 | B相 | **0V** (陷阱) | 183V ❌ | 183V ❌ |
| E14 | B相 | A相 | **183V** ❌ | 183V ❌ | **0V** (陷阱) |
| E08 | A相 | A相 | 0V ✅ | 0V ✅ | 0V ✅ |

---

## 物理引擎关键算法

### 每帧更新顺序（33ms/帧）
```
_update_bus_reference()     → 确定母线参考源（Gen1 or Gen2）
_update_arbitration()       → 自动同步调节（PLL式）
_advance_time()             → 推进仿真时间
_update_actual_amplitudes() → 电压斜坡上升（调速器模型）
_compute_wave_state()       → 角频率、相位计算
_update_protection_state()  → 计算线路电流，过流检测（300A跳闸）
_apply_droop_control()      → 频率下垂调节
_update_wave_history()      → 更新200点波形缓冲
_update_breaker_logic()     → 联锁执行、保护跳闸、E01/E02事故拦截
_update_pt_measurements()   → PT二次侧电压（含相序映射）
_update_multimeter()        → 万用表读数（probe1 ↔ probe2）
```

### 自动同步控制（ArbitrationMixin）
```python
error_freq  = gen2.freq     - bus_freq
error_amp   = gen2.amp      - bus_amp
error_phase = (gen2.phase_deg - bus_phase_deg) % 360°

gen2.freq     += K_sync * error_freq
gen2.amp      += K_sync * error_amp
gen2.phase_deg += K_sync * error_phase

# 三者同时在容差内（0.5Hz / 500V / 15°）→ 允许合闸
```

### PT相序映射与压差计算
```python
# 正常: pt_phase_orders = ['A','B','C']
# E02故障: g2_blackbox_order=['A','C','B'] → PT3端子B→C相、C→B相
actual_phase = _resolve_terminal_actual_phase(pt_name, terminal)

# 【第二步 intra-PT 线电压】通用相量差公式（_compute_intra_pt_voltage）：
# gen_ph = pt_line_v / √3
# angle1 = _PHASE_ANGLES[phase1]，E03 PT3 A端子: angle += π（极性反接）
# meter_v = |gen_ph·e^(jθ1) − gen_ph·e^(jθ2)|
# 正常/E01/E02: 两相角差120° → √3·gen_ph = pt_line_v（不变）
# E03 PT3_AB/CA: 角差60° → gen_ph = pt_line_v/√3 ≈ 106V（偏低标红）
# E03 PT3_BC: 不含A端子，角差120° → 正常
#
# E04 阈值特殊处理（_physics_measurement.py 和 pt_voltage_check_service.py）：
# 即使 sim.pt3_ratio=118.28，阈值计算强制用额定变比56.99
# → 阈值下限 8925/56.99≈156.6V，测量≈88.8V → 红色[异常]

# 【第四步 cross-PT 压差】
# 同相压差: abs(gen_ph - bus_ph)
# 异相压差: sqrt(gen_ph² + bus_ph² + gen_ph·bus_ph)  [cos120°=-0.5]
# E03极性反接AA: gen_ph+bus_ph（≈166V）;  E03极性反接AB/AC: sqrt(V1²+V2²-V1·V2)（≈92V）
```

---

## 关键常量（domain/constants.py）

| 常量 | 值 | 单位 | 用途 |
|------|----|------|------|
| `GRID_FREQ` | 50.0 | Hz | 额定频率 |
| `GRID_AMP` | 10500.0 | V | 额定线电压（RMS） |
| `XS` | 1.0 | Ω | 线路等效阻抗 |
| `TRIP_CURRENT` | 300.0 | A | 继电保护跳闸阈值 |
| `CT_RATIO` | 100:1 | — | 电流互感器变比 |
| `MAX_POINTS` | 200 | 点 | 示波器缓冲深度 |
| `KP_DROOP` | 0.0005 | — | 有功下垂系数 |
| `KQ_DROOP` | 0.0002 | — | 无功下垂系数 |

---

## UI 架构

`PowerSyncUI` 由9个 Mixin 组合：

| Mixin | 职责 |
|-------|------|
| `WidgetBuilderMixin` | 右侧控制面板（系统模式、接地、故障选择） |
| `WaveformTabMixin` | Tab 0：波形图 & 相量图（matplotlib） |
| `CircuitTabMixin` | Tab 1：母线拓扑 & 测量点（最大文件，~970行） |
| `LoopTestTabMixin` | Tab 2：回路测试 |
| `PtVoltageCheckTabMixin` | Tab 3：PT电压检查 |
| `PtPhaseCheckTabMixin` | Tab 4：PT相序 |
| `PtExamTabMixin` | Tab 5：PT压差 |
| `SyncTestTabMixin` | Tab 6：同期测试 |
| `TestPanelMixin` | 测试模式竖向控制栏（替换右侧面板，含第1~5步控制台） |

### UI 现代化（2026-04）

当前 UI 改造策略已经统一为：继续使用 `PyQt5 + QWidget`，在现有界面层级上做浅色主题现代化迭代，不切换到新的控件框架。

- **设计基线**
  - 浅色优先，当前不做深色主题
  - 中性专业风
  - 标准信息密度
  - 青蓝主色
  - 8px 圆角
  - 保留原生系统标题栏
- **实现方式**
  - `ui/styles/` 子包负责全局主题入口、设计令牌、组件 QSS 分块和语义属性样式
  - `ui/main_window.py` 在主窗口启动时统一加载主题
  - `ui/panels/control_panel.py` 通过属性驱动的辅助方法统一按钮、卡片、badge、toggle 外观
  - `ui/tabs/_step_style.py` 提供步骤页壳层、按钮、动态文本、记录值等公共样式 helper
  - `ui/test_panel.py` 已把说明文字、反馈文本、行容器、管理员区、弹窗骨架等高频样式收敛为语义 helper
- **当前已完成的覆盖范围**
  - 主窗口、主 Tab、右侧控制面板
  - `test_panel.py` 的顶部栏、底部栏、故障横幅、步骤反馈、管理员区、成绩单弹窗、黑盒弹窗
  - Tab 2～6 步骤页公共壳层与主要动作按钮
  - 第 1/2/3 步动态文本、反馈标签、记录值、状态提示
- **保留的局部特殊样式**
  - 步骤圆点按钮
  - 少量成绩单动态强调卡片
  - 个别 PT 分组提示色块
  - 少量探针提示文本
- **当前边界**
  - matplotlib 图表区主要完成外围容器和主题接入，绘图区本身尚未进行更深层统一
  - 整体主题系统已稳定，但如果后续要做深色主题，还需要补完整套 light/dark token 切换

### 测试模式面板（test_panel.py）重要细节
- 进入测试模式：`ctrl_container.setVisible(False)`，`test_panel.setVisible(True)`
- 每步控制台由 `_build_step1~5` 构建，`_refresh_tp_step1~5` 每帧刷新
- **管理员模式**：开启后 Tab 2~6 可见，步骤点可手动跳转
- **第二步变比控制台**：PT1/PT3/PT2 分三行独立显示，`_tp_s2_ratio_rows` 字典存储各行控件引用（键为 `'pt_gen_ratio'`/`'pt3_ratio'`/`'pt_bus_ratio'`），**该属性挂在 `self.ui`（PowerSyncUI实例）上，不在 `self.ui.test_panel`（QWidget）上**
- **第四步快捷按钮** `⚡ 快捷记录全部18组`：管理员模式与考核模式均显示，调用 `record_all_pt_measurements_quick()`，跳过逐组表笔测量直接写入 Gen1+Gen2 共18组压差
- **现阶段重构收敛**：
  - 第四步后进入第五步前的黑盒门禁判断已下沉到 `PowerSyncController.get_test_progress_snapshot()`
  - 考核模式第四步闭环后的自动结算已下沉到 `PowerSyncController.finish_assessment_session_if_ready()`
  - 黑盒确认修复后的运行态写回、事件记录、自动清故障判断已下沉到 `PowerSyncController.apply_blackbox_repair_attempt()`
  - `test_panel.py` 仍负责 UI 采集与渲染，但不再直接承担这三类核心业务决策

### 第一步回路测试 UI 变更
- **路径动画已注释**（`ui/tabs/circuit_tab/` 子包内绘图实现）：绿色流动球（导通）与红色 X 符号（断路）的路径动画全部注释，图面连线无任何动态变化。
- 学员**只能**通过万用表面板读数（`0.0 Ω` = 导通，`不导通` = 断路）判断通断，不再有视觉外挂提示。
- 第一阶段测试页、测试模式控制台与母排拓扑页记录表均显示六组记录：`AA / BB / CC / AB / AC / BC`。
- 动画相关 Plot 对象（`loop_anim_wire_ok` 等）保留但始终为空，`_clear_loop_anim()` 方法保留。

### 物理接线黑盒检查（`_add_blackbox_section` / `_show_blackbox_dialog`）

**位置**：黑盒检查区通过 `_add_blackbox_section(lay)` 帮助函数插入，**在第 1～4 步控制台均显示**（之前仅第四步）。共 4 个按钮：G1 机端接线 / G2 机端接线 / PT1 接线盒 / PT3 接线盒，点击弹出图形化接线图对话框（`_show_blackbox_dialog(target)`）。

**交互修复设计**（渐进式修复，非一次性全清）：
- G1 / G2 / PT1 / PT3 对话框支持点击互换接线，用户可在任意步骤随时打开修复
- 点击底部保存按钮后：
  1. 更新对应运行态黑盒状态与相序（G1→PT2，G2→PT3，PT1→PT1，PT3→PT3）
  2. 记录 `blackbox_swap` / `blackbox_confirm_attempted`
  3. 若当前场景所有可修复目标均恢复到 `['A','B','C']`，自动调用 `repair_fault()`
  4. 考核模式下不再显示“修复成功 / 仍异常 / 继续检查其他位置”等结果提示，只保留“接线已保存，请返回外部流程复测”的中性反馈

**渐进修复路径示例**（E05 三处均为 A↔B）：
1. 步骤 1 AA/BB 断路 → 开 G1 对话框，把 U/V 接线柱调回正序 → PT2=ABC → 步骤 1 回路恢复导通 → 可完成步骤 1
2. 步骤 3 PT1 逆序 → 开 PT1 对话框，把 a2/b2 调回正序 → PT1=ABC → 步骤 3 相序正常 → 可完成步骤 3
3. G1 / PT1 一次侧 / PT1 二次侧三处物理状态都恢复 ABC → `repair_fault()` 自动触发

**数据来源**（有故障活跃且未修复时优先读控制器运行态黑盒状态）：
- G1 `mapping`：`ctrl.g1_blackbox_order`；`pt_phase_orders['PT2']` 为同步后的派生结果
- PT1 `pri_order`：`ctrl.pt1_pri_blackbox_order`
- PT1 `sec_order`：`ctrl.pt1_sec_blackbox_order`
- PT 黑盒显示采用“逐级传播”模型：PT1 下方输入相序直接继承 `ctrl.g1_blackbox_order`，一次侧输出再叠加 `ctrl.pt1_pri_blackbox_order`，二次侧输出继续叠加 `ctrl.pt1_sec_blackbox_order`；除母排固定端子位置外，不再把每层输入重置为 `ABC`
- UI 语义进一步固定为：底部输入电缆显示上游实际来相，`A1/B1/C1` 显示一次侧传播后的实际相别，`A2/B2/C2` 显示二次侧传播后的实际相别，最上方测量端仅将二次侧当前结果垂直引出
- G2 `mapping`：`ctrl.g2_blackbox_order`；终端接线级错误会同步写入 `pt_phase_orders['PT3']`
- PT3 `pri_order`：默认 `ABC`；`sec_order` = `pt_phase_orders['PT3']`；E03 通过 `sec_polarity=[-1,1,1]` 呈现 A 相二次极性反接
- E03 激活时 PT3 对话框显示二次侧极性标识，考核 / 工程 / 教学模式均可点击极性标记恢复为 `+++`
- 第五步前修复关卡与 `SyncTestService.record_sync_round()` 都会调用 `ctrl.has_unrepaired_wiring_fault()`；只要当前场景所涉及的可修复黑盒目标未恢复 `ABC`，系统就停留在第四步并提示先去黑盒修复，同时也禁止记录第五步
  - `g1_blackbox_order` / `pt1_pri_blackbox_order` / `pt1_sec_blackbox_order`
  - `g2_blackbox_order`（E02）

**新增 params 字段**（`fault_scenarios.py` E05–E14）：
| 键 | 含义 |
|----|------|
| `g1_blackbox_order` | G1 机端接线柱实际相序（黑盒图显示用） |
| `p1_pri_blackbox_order` | PT1 一次侧本级接线置换 |
| `pt2_sec_blackbox_order` | PT1 二次侧本级接线置换 |

**G1 / G2 发电机端子盒**（`_GenWiringWidget`）：
- 上方：3 个固定彩色圆 = 内部绕组（A黄 / B绿 / C红），位置永远固定
- 下方：3 个方块 = 输出接线柱（U / V / W）
- 连线根据 `mapping = {terminal: actual_phase}` 动态绘制；错接时线段交叉
- G1 / G2 均支持点击两节点互换（`interactive=True`）
- 可变状态存储在 widget 内部 `_order`，`get_order()` 返回当前排列

**PT1 / PT3 接线盒**（`_PTWiringWidget`，六点式）：
- 上方：测量端口 A/B/C；上半连线：二次侧 a2/b2/c2 → 测量端口（`sec_order`，可交互）
- 中间：变压器铁芯虚线框（固定）
- 下方：电缆 A/B/C；下半连线：电缆 → 一次侧端子 A1/B1/C1（`pri_order`）
- `interactive_pri=True` / `interactive_sec=True` 分别允许点击任意两个一次侧 / 二次侧端子互换；`get_pri_order()` / `get_sec_order()` 返回当前排列
- 点击高亮：被选中节点蓝色边框标记

**绘图逻辑关键**（两个 widget 共用）：
- 固定相位列：xs[0]=A, xs[1]=B, xs[2]=C
- 连线颜色 = 该线传输的相色（A黄/B绿/C红）
- 交叉判断：当 `src_x ≠ dst_x` 时线段对角，即为错接可视化

### 快捷记录实现（pt_exam_service.py）
```python
def record_all_pt_measurements_quick(self):
    # 检查前三步完成 + 第四步已开始
    # 直接读取 physics.pt1_v / pt2_v / pt3_v
    # 对 Gen1+Gen2 各9组 (gen_term × bus_phase) 计算压差
    # 使用与 _update_multimeter 完全相同的公式（含E03极性修正）
    # 一次性写入 pt_exam_states[1/2].records
```

---

## 项目当前状态

- **2026-04 UI 现代化收敛**：
  - 主题路线已固定为“浅色主题 + 语义属性 QSS + 渐进式改造”，当前不做深色主题。
  - `ui/styles/` 已完成子包化，继续保持 `apply_app_theme()` / `build_app_stylesheet()` 入口不变；`ui/tabs/_step_style.py` 已作为步骤页公共样式层加入。
  - 右侧控制面板、测试面板、步骤页壳层和主要弹窗已完成第一轮统一；后续若继续迭代，重点应转到 matplotlib 绘图区和截图级细节微调。

- **2026-04 黑盒接线逻辑校正**：
  - G1 / PT1 黑盒对话框优先显示控制器运行态黑盒状态，不再优先读取 `fault_scenarios.py` 的静态 `params`。
  - G1 物理真值源是 `ctrl.g1_blackbox_order`；`pt_phase_orders['PT2']` 是同步后的派生结果，供回路与测量计算使用。
  - PT1 物理真值源是 `ctrl.pt1_pri_blackbox_order` 与 `ctrl.pt1_sec_blackbox_order`；`pt_phase_orders['PT1']` 是净相序结果，不等同于 PT1 盒内物理接线。
  - PT1 黑盒已支持一次侧、二次侧分别点击互换修复；旧文档中“仅二次侧可修复”的描述已失效。
  - 自动清故障条件已改为三个物理黑盒状态都回到 `['A','B','C']`，而不是仅看 `pt_phase_orders['PT1']` / `['PT2']` 是否恢复正常。
  - E06 / E10 的 PT1 二次侧黑盒状态为正常 `['A','B','C']`，错误仅在 PT1 一次侧；这是本轮重新校正后的场景事实。
  - 第三步相序仪快捷记录已改为按真实序列逐相判定，`BCA/CAB` 不再被误记为三相全对。
  - 第五步前和第五步记录时都会检查运行态黑盒是否仍未恢复；E08 这类隐性接线故障现在会被卡在第四步，必须先在黑盒中完成实际修复，不能再穿透到同步测试。

- **2026-04 架构收敛（进行中）**：
  - 已新增 `services/fault_manager.py`，将故障注入/修复和“可修复接线目标”判断从 `PowerSyncController` 中拆出；控制器目前保留同名转发接口，外部调用无需调整。
  - `_tick()` 已拆为“物理更新”和“渲染/UI”两个异常边界；连续失败达到 3 次时，主窗口状态栏会显示非模态错误提示。
- E01/E02/E03 事故弹窗已不再由物理层直接调用，而是通过待显示队列在帧末统一消费。
- E01/E02/E03 的事故弹窗 UI 已收口到 `ui/main_window.py::_show_accident_dialog(...)` 公共壳层，外部只保留三个轻量包装方法，避免继续维护三套重复对话框实现。
- 旧的 `_show_e01/_show_e02/_show_e03_accident_dialog_legacy` 死代码已删除，事故弹窗现在只有一套实际实现。
- 控制器不再直接切换 `tab_widget` 或直接写入 PT3 变比数字框；改为登记待处理的 UI 请求，由 `PowerSyncUI` 在 `render_visuals()` / `show_warning()` 中统一消费。
- `services/assessment_service.py::build_result()` 已拆为“上下文准备 + 分类评分 helper + 汇总组装”三段；评分规则、额外扣分逻辑和 `AssessmentResult` 输出结构保持原样。
- 死母线首台投入倒计时已改为使用真实帧间隔：控制器在 `_tick()` 中记录 `frame_dt` 并注入 `PhysicsEngine`，`_physics_arbitration.py` 用该 `dt` 取代硬编码 `0.033` 来累加 `dead_bus_timer`。
- 长期维护与去屎山化重构进度统一记录在 [MAINTENANCE_CHECKLIST.md](MAINTENANCE_CHECKLIST.md)，该文件现已覆盖：总体进度、轮次历史、固定回归清单、UI 解耦阶段、核心逻辑测试原则、未来 UI 替换关系说明、大文件统计脚本入口，以及 `ctrl` 耦合治理 / Mixin 治理方向；后续迭代默认先更新该文件。

- **已完成并验证**：隔离母排模式完整五步骤仿真；E01 / E02 场景全步骤测试通过；E03 可通过 PT3 接线盒极性标识提前修复；E04 可通过右侧控制台 PT3 变比恢复为 `11000:193` 后清故障
- **已实现并纳入回归**：第一步 `AA/BB/CC/AB/AC/BC` 六组回路记录与母排拓扑记录表；第五步完成后双机稳定到 `50Hz / 10500V / 0°` 并重置波形历史；中性点接地断开时只隐藏电阻下方三条竖线的下段
- **已完成并验证**：E05–E14 物理注入与物理接线黑盒渐进式交互修复（通用参数驱动，含下列修复）
- **最新实现**：
  - 黑盒接线检查按钮下移至**第 1～4 步全局显示**（`_add_blackbox_section` 帮助函数）
  - `_GenWiringWidget` / `_PTWiringWidget` 支持**点击互换**交互修复（两次点击互换节点）
  - `_PTWiringWidget` 已支持二次侧极性显示与交互；E03 的 `-++` 可在 PT3 接线盒中直接恢复为 `+++`
  - E04 的 PT3 变比修复已接入 `FaultManager.maybe_repair_pt_ratio_fault()`，用户在右侧控制台恢复额定变比后会清除故障并要求重新记录受影响数据
  - **渐进式修复逻辑**：`_on_confirm()` 仅在当前场景所有“可修复黑盒目标”均还原为 `['A','B','C']` 后才调用 `repair_fault()`；G1/PT1 与 G2 黑盒都会纳入该判断；单组件修复后提示"继续检查其他位置"，不立即清除故障
  - `resolve_loop_node_phase` 仍直接读取 `pt_phase_orders['PT2']`，但该值已由 `sync_pt1_blackbox_to_phase_orders()` 从运行态黑盒状态同步生成，不再应被理解为唯一物理真值源
  - **E01 double-swap bug 修复**：`inject_fault` 中 `g1_loop_swap` 通用块加 `scenario_id != 'E01'` 守卫，防止覆盖 E01 显式设置的 PT2
  - `fault_scenarios.py` E05–E14 新增 `g1_blackbox_order` / `p1_pri_blackbox_order` / `pt2_sec_blackbox_order` params 供黑盒图静态显示
  - 第三步 `_on_record_psm()` 已从“按正逆序组记全局布尔”改为“按真实三字母结果逐相写入 `phase_match`”
  - `has_unrepaired_wiring_fault()` 已作为第五步前门禁与 `SyncTestService` 兜底条件；第五步前弹窗现为阻断提示，不再直接调用 `repair_fault()`
  - `teaching / engineering / assessment` 三模式差异已收敛到控制器 `FLOW_MODE_POLICIES`，业务层统一通过语义接口读取策略
  - `FLOW_MODE_POLICIES` 当前已类型化为 `FlowModePolicy`
  - `loop_test_service.py` 与 `pt_phase_check_service.py` 已先完成一层收敛：通过控制器语义方法写回状态，而不是直接散落修改 dataclass 字段
  - 控制器新增最小只读/编排接口：`get_test_progress_snapshot()`、`get_blackbox_runtime_state()`、`finish_assessment_session_if_ready()`、`apply_blackbox_repair_attempt()`
  - G2 机端黑盒已从“仅查看”改为终端接线级可交互修复；E02 通过 `g2_blackbox_order` 与 `pt_phase_orders['PT3']` 同步表达
  - 场景选择弹窗已改为可滚动场景列表，底部固定显示 `teaching / engineering / assessment` 三种流程模式选项
  - 旧的 E06 force-close 入口、仲裁死分支与相关误导性注释已清理
- **暂时禁用（代码已注释保留，开发中）**：
  - E15（原E05）：Gen2过电压（AVR故障），步骤2/4/5
  - E16（原E06）：强行非同期合闸，步骤5

---

## 依赖

```
PyQt5       # GUI框架
matplotlib  # 波形/相量/拓扑图绘制
numpy       # 数值计算
```
## 2026-04-09 Phase 0 安全网进度

- 已新增 `tests/` 目录和快照测试入口：
  - `tests/test_physics_snapshot.py`
  - `tests/test_assessment_snapshot.py`
  - `tests/support/stubs.py`
  - `tests/support/snapshots.py`
- 已验证：
  - `PhysicsEngine` 可在无 UI 的 `ControllerStub` 下运行 `update_physics()` + `build_render_state()`
  - `AssessmentService.build_result()` 可在最小替身控制器下独立运行
- 已生成快照基线：
  - `tests/snapshots/physics_normal.json`
  - `tests/snapshots/physics_fault_E01.json`
  - `tests/snapshots/assessment_normal.json`
  - `tests/snapshots/assessment_fault_random.json`
- 当前测试命令：
  - `python -m pytest tests/`
- Phase 0 已闭环；旧 UI Mixin 依赖扫描文档已随 Tab 组件化完成移除，当前不再维护 `/docs/` 下的 Mixin 映射文件
