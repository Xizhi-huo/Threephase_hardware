# 维护与重构清单 v2

最后更新：`2026-04-28`

用途：
- 给人看：明确当前项目的维护边界、阶段目标、已完成进度。
- 给 AI 看：后续新对话先读本文件，再决定下一轮该做什么，不再重复讨论方向。

## 1. 维护边界总原则

### 1.1 总目标
- 当前阶段 `不新增功能`。
- 当前阶段只做两类事：
  - 提高代码可读性
  - 提高代码可靠性
- 重构的终极目的：`剥离 UI 与业务/物理/评分逻辑`，使核心引擎可独立测试，UI 可被整体替换。

### 1.2 文件大小参考标准

| 等级 | 标准 | 行动 |
|---|---|---|
| 健康 | `<= 500` 行 | 无需操作 |
| 需要审查 | `501 - 800` 行 | 评估是否存在多职责 |
| 必须拆分 | `> 800` 行 | 列入本轮或下轮攻坚目标 |

说明：
- 纯数据声明文件（如 `fault_scenarios.py`、`styles.py`）不适用此标准，除非其中混入了逻辑代码。
- 行数下降是接口隔离的副产品，不是目标本身。**核心度量标准是"模块间接口是否隔离"。**
- 大文件基线使用脚本入口：`python scripts/report_large_files.py --top 10`。

### 1.3 工程边界红线
- 不再往大文件里继续堆新逻辑。
- 不再新增上帝类。
- 不再新增巨石函数（单函数 > 80 行应审查）。
- 不再新增 `physics -> ui` 的直接调用。
- 不再新增 `controller -> 具体 UI 控件` 的直接写入。
- 不再新增大范围 `try/except Exception` 静默吞异常。
- 不再新增长期保留的过渡死代码。
- 每次重构必须同步删除旧实现，不能长期双轨并存。
- Controller 只负责命令下发和编排，禁止 `ctrl.xxxWidget.setText()/setValue()` 一类直接控件写入。
- 重构核心逻辑前，必须先具备最小黑盒回归验证能力；没有验证保护的重构，不进入核心逻辑。

### 1.4 接口隔离原则
- Service 不再新增对 `self._ctrl` 的穿透式属性访问（如 `self._ctrl.sim_state.gen1.xxx`）。
- 每个 Service 的公开方法应只接收它真正需要的数据，而非整个 ctrl。
- 过渡期做法：新增或修改的 Service 方法，优先改为显式参数传入，旧方法暂时保留。
- 最终目标：Service 的构造函数只接收自己负责的 State 切片 + 有限的回调接口，不再持有 ctrl 引用。
- 验证方式：新增的 Service 方法中 `self._ctrl` 引用数不增长。

### 1.5 单向数据流规范

严格的数据流方向：

```
User Action (槽函数)
    │
    ▼
Controller.command_xxx()        ← UI 只调用 Controller 的命令方法
    │
    ▼
Service / PhysicsEngine         ← Controller 委托给 Service 处理
    │
    ▼
State 对象变更                  ← Service 只写入自己负责的 State
    │
    ▼
_tick() → build_render_state()  → RenderState
    │
    ▼
UI.render_visuals(rs)           ← UI 只从 RenderState 读取并刷新
```

违禁模式（新代码中禁止）：
- UI 槽函数里直接修改 `sim_state`。
- Service 里读取其他 Service 的状态。
- UI 里调用 Service 的内部方法。
- 任何组件绕过 Controller 直接修改状态。

所有后端计算结果只能写入 `SimulationState / RenderState / AssessmentResult` 这类状态对象。
UI 只能读取状态刷新自己，不能反向污染业务状态。

### 1.6 每轮迭代固定动作
- 每轮有且只有一个主攻目标。做深做透，不蜻蜓点水。
- 新实现落地后，同轮就删旧实现。
- 每轮结束必须更新本文件（§9 轮次历史 + §10 下一轮起点）。
- 每轮结束必须通过回归清单（§8）验证。

### 1.7 禁止事项
- 禁止"顺手加功能"。
- 禁止"只抽函数，不删旧逻辑"。
- 禁止"因为赶进度继续把逻辑塞回 `app/main.py` 或 `ui/test_panel.py`"。
- 禁止"只搬方法，不定义接口边界"。每次拆分的第一步是定义新模块的输入/输出边界，再动手搬代码。
- 禁止"未记录进度就结束本轮重构"。

---

## 2. 当前高风险文件基线

| 文件 | 行数 | 状态 | 核心问题 |
|---|---:|---|---|
| `ui/test_panel.py` | 510 | 需要审查 | 测试模式协调器已显著瘦身，但仍承担较多装配与步骤联动 |
| `app/main.py` | 502 | 需要审查 | Controller 已完成 Phase 1 收尾，保留编排与少量 UI 胶水 |
| `ui/tabs/waveform_tab.py` | 729 | 需要审查 | 波形图、相量图、同期表与仪表盘逻辑集中在同一组件 |
| `services/assessment_service.py` | 399 | 健康 | 评分系统已完成模块化 + 类型化 + 单域快照保护，Phase 2 已闭环 |
| `ui/main_window.py` | 528 | 需要审查 | 9-Mixin 继承入口，待迁移为组合式 |
| `domain/fault_scenarios.py` | 520 | 纯数据，暂缓 | 纯场景定义字典，不含逻辑 |
| `services/pt_exam_service.py` | 385 | 健康，观察 | 48 处 `self._ctrl` 引用需逐步收口 |
| `services/_physics_measurement.py` | 372 | 健康，观察 | 保持稳定 |
| `services/pt_phase_check_service.py` | 345 | 健康，观察 | 37 处 `self._ctrl` 引用需逐步收口 |

说明：
- 当前主要结构热点：`ui/tabs/waveform_tab.py`、`ui/main_window.py`、`ui/widgets/step_panels/_panel_builders.py`。
- **耦合度指标比行数更重要**。各文件的 `self._ctrl` / `self.ctrl` 引用数是关键度量。

### 当前耦合度基线（2026-04-09）

| 层 | 文件 | `ctrl` 引用数 |
|---|---|---:|
| services | `pt_exam_service.py` | 48 |
| services | `fault_manager.py` | 39 |
| services | `pt_phase_check_service.py` | 37 |
| services | `sync_test_service.py` | 26 |
| services | `pt_voltage_check_service.py` | 23 |
| services | `loop_test_service.py` | 20 |
| services | `assessment_service.py` | 0 |
| ui | `test_panel.py` | 111 |
| ui | `pt_exam_tab.py` | 20 |
| ui | `sync_test_tab.py` | 16 |
| ui | `loop_test_tab.py` | 14 |
| ui | `control_panel.py` | 12 |
| ui | 其余 Tab | 各 5-10 |

---

## 3. 当前总体进度

| 项目 | 当前状态 |
|---|---|
| 当前阶段 | `R49-Round2` 已完成（`ui/styles.py` 已拆为 `ui/styles/` 子包，`build_app_stylesheet()` 规范化输出哈希保持不变，`apply_app_theme()` API 未改）。 |
| 已完成的高/严重问题 | 历史主线 `C1`、`C2(第一步)`、`H1`、`H2`、`H3`、`H4`、`H5` 已完成；上一轮修复计划范围内的任务已于 `R48-Round1 ~ R49-Round2` 全部收口。 |
| 当前最大风险文件 | `ui/tabs/waveform_tab.py`(729)、`ui/main_window.py`(657)、`ui/tabs/circuit_tab/_draw_topology.py`(537)、`ui/test_panel.py`(510) |
| 下一轮默认起点 | `R49-Round3`：`ui/tabs/waveform_tab.py` 结构审查与职责拆分预研（先梳理绘图 / 指标卡 / 同期判据边界，不改视觉与业务语义） |

---

## 4. 重构路线图

### R48 Review 收口轮次（当前）

- [x] Round 1：机械小修 + 死分支清除（`C1 / M2 / M3 / M7 / m1 / m2 / m6`）
- [x] Round 2：封装边界和小型接口收口（`M4 / M5 / m7`）
- [x] Round 3：运行时鲁棒性和异常处理（`M8 / m5`，必要时顺带局部收口 `m4`）
- [x] Round 4：`ui/tabs/circuit_tab.py` 结构性拆分（`M6`）
- [x] Deferred A：`services/` 返回类型标注专项（建立统一统计口径，覆盖率 `37.0% -> 100.0%`）
- [x] Deferred B：`ui/styles.py` 拆分专项（已拆为 `ui/styles/` 子包，保留 `apply_app_theme()` / `build_app_stylesheet()` 导入兼容）

说明：
- Phase 4 主线和此前的 service/self._ctrl 收口已经闭环；R48 起转入低风险 review 收口轮次。
- `services/` 返回类型标注专项与 `ui/styles.py` 拆分专项均已完成；后续若继续推进，转入新的 UI 结构审查轮次。

### Phase 0: 安全网建设（1-2 轮）

**目标：** 在不动任何核心逻辑的前提下，建立最小回归保护网。这是后续所有重构的前提。

- [x] **PhysicsEngine 可脱离 UI 独立实例化**
  - 构造一个不含 UI 的最小 ctrl 替身（只含 `sim_state` + `pt_phase_orders` 等纯数据属性）
  - 验证 `PhysicsEngine(stub).update_physics()` + `build_render_state()` 可以独立运行
  - 如果不行，先修到能独立实例化（这本身就是在解耦）
- [x] **PhysicsEngine 快照测试**
  - 创建 `tests/test_physics_snapshot.py`
  - 基线场景 1：正常状态（双机空载）→ `tests/snapshots/physics_normal.json`
  - 基线场景 2：E01 故障注入后 → `tests/snapshots/physics_fault_E01.json`
  - RenderState 序列化为 JSON，float 精度小数点后 4 位
  - 首次运行生成基线，后续比对差异
- [x] **AssessmentService 快照测试**
  - 创建 `tests/test_assessment_snapshot.py`
  - 基线场景 1：正常满分流程 → `tests/snapshots/assessment_normal.json`
  - 基线场景 2：随机故障考核流程 → `tests/snapshots/assessment_fault_random.json`
  - 构造固定的 `AssessmentSession`（预填事件流），调用 `build_result(session, context)` 比对输出
- [x] **Mixin 属性交叉引用扫描**
  - 列出每个 Mixin 创建的 `self.xxx` 属性
  - 标注哪些属性被其他 Mixin 访问
  - 曾输出为 UI Mixin 依赖扫描文档
  - 这是 Phase 3 UI 组件化的前置依赖图；Tab 组件化完成后该历史文档已移除，不再作为当前维护入口

完成标准：
- `pytest tests/` 可以跑通，物理和评分快照全部 PASS。
- PhysicsEngine 可以不依赖 PyQt5 实例化。
- Mixin 属性依赖图已完成历史扫描；当前 UI 已迁移到独立 QWidget 组件，不再维护旧 Mixin 依赖图。

### Phase 1: Controller 瘦身 — 接口隔离（3-5 轮）

**目标：** 把 `PowerSyncController` 从上帝类收回到纯编排层。关键不是"搬方法"，而是"定义接口边界"。

- [x] **拆出 `FlowModeManager`**
  - 将 `FlowModePolicy` + `FLOW_MODE_POLICIES` 字典 + 30+ 个 `flow_policy_flag` 包装方法移出
  - 输入接口：`test_flow_mode: str`
  - 输出接口：`FlowModePolicy` 查询
  - Controller 持有实例，只转发查询
- [x] **拆出 `AssessmentCoordinator`**
  - 将考核会话生命周期管理（`start/finish/capture_snapshot/submit_guess` 等）移出
  - 输入接口：`AssessmentSession` + `SimulationState`（只读快照）+ 各步骤 `completed` 状态
  - 输出接口：`AssessmentResult` + 事件列表
  - 本轮落地策略：**允许**持有 `ctrl` 引用，仅做“搬走实现、Controller 保留转发壳”
  - 后续收口目标：Phase 4 再逐步移除 `ctrl` 直连，改为显式状态/接口注入
- [x] **拆出 `BlackboxRepairHandler`**
  - 将 `get_blackbox_runtime_state` / `apply_blackbox_repair_attempt` 及相关方法移出
  - 输入接口：`fault_config` + `blackbox_orders` + `pt_phase_orders`
  - 输出接口：`BlackboxRepairOutcome`
  - 修复结果通过返回值传回 Controller，由 Controller 写入状态
  - 本轮落地策略：**允许**持有 `ctrl` 引用，仅做“搬走实现、Controller 保留转发壳”
  - 后续收口目标：Phase 4 再逐步移除 `ctrl` 直连，改为显式状态/接口注入
- [x] **拆出 `PhaseOrderResolver`**
  - 将 `resolve_pt_node_plot_key` / `get_pt_phase_sequence` / `resolve_loop_node_phase` 移出
  - 输入接口：`pt_phase_orders` + `blackbox_orders` + `fault_config`(只读)
  - 输出接口：纯函数返回值
  - 本轮落地策略：**允许**持有 `ctrl` 引用，仅做“搬走实现、Controller 保留转发壳”
  - 后续收口目标：Phase 4 再逐步移除 `ctrl` 直连，改为显式状态/接口注入
- [x] **拆出 `HardwareActions`**
  - 将发电机启停、断路器合分、即时同期动作移出
  - 输入接口：`SimulationState`（读写）
  - 输出接口：状态变更直接写入传入的 State 对象
  - 本轮落地策略：**允许**持有 `ctrl` 引用，仅做“搬走实现、Controller 保留转发壳”
  - 后续收口目标：Phase 4 再逐步移除 `ctrl` 直连，改为显式状态/接口注入
- [x] **删除 Controller 中已迁出的旧方法**
  - 不保留纯转发壳层（如 `def is_loop_test_complete(self): return self._loop_svc.is_loop_test_complete()`）
  - UI 直接调用对应 Service 的方法，或通过 Controller 暴露的有限接口
  - 第 15 轮已完成第一阶段：`HardwareActions`、`PhaseOrderResolver`、`BlackboxRepairHandler`、`FaultManager`、`LoopTestService`、`PtVoltageCheckService`、`PtPhaseCheckService`、`PtExamService`、`SyncTestService` 相关纯转发壳已删除
  - 第 16 轮已完成第二阶段：`FlowModeManager`、`AssessmentCoordinator` 相关纯转发壳已删除；`AssessmentService` 句柄已公开化
- [x] **每步完成后跑快照测试验证**

完成标准：
- `app/main.py` 降到 ~600 行以下。
- Controller 中不再堆叠策略查询、考核生命周期、黑盒修复、相序解析四类实现细节。
- 新拆出的模块之间无直接引用，只通过 Controller 编排。
- 快照测试全部 PASS。

### Phase 2: 评分系统模块化（2-3 轮）

**目标：** `assessment_service.py` 变成可独立测试的评分管道。

- [x] **定义 `AssessmentContext` dataclass**
  - 将 `build_result()` 中从 `self._ctrl` 读取的所有数据（loop_records、voltage_records 等）封装为一个 dataclass
  - Controller 在调用 `build_result()` 之前打包好 Context 传入
  - `build_result(session, context)` 不再访问 `self._ctrl`
- [x] **评分事件常量化**
  - 消除 `build_result()` 内部的魔法字符串（`"fault_detected"` / `"step_entered"` 等）
  - 集中到 `domain/assessment.py` 的常量类中
- [x] **按评分域拆分为纯函数模块**
  - `services/scoring/discipline.py` — A 类：流程纪律评分
  - `services/scoring/step_quality.py` — B/C/D/E 类：步骤 1-4 质量评分
  - `services/scoring/fault_diagnosis.py` — F 类：故障定位评分
  - `services/scoring/blackbox_efficiency.py` — G/H 类：黑盒与效率评分
  - 每个模块暴露纯函数：`score_xxx(context) -> List[AssessmentScoreItem]`
- [x] **`score_context` 改为 `ScoringContext` dataclass**
  - `services/scoring/context.py` 已落地 `@dataclass(frozen=True)` 的 `ScoringContext`
  - 4 个评分域模块已从 `ctx["xxx"]` 切换为 `ctx.xxx`
  - 评分阶段所需的 4 个原闭包已迁入 `services/scoring/_common.py`，改为独立纯函数
- [x] **`assessment_service.py` 主文件降到 <= 500 行**
  - 主文件只做组装：调用各评分域函数，合并结果
- [x] **为每个评分域补充独立快照测试**

完成标准：
- `build_result()` 只做组装，不含具体评分逻辑。
- 每个评分域能单独阅读、修改、测试。
- `assessment_service.py` 中 `self._ctrl` 引用数 = 0。
- 快照测试全部 PASS。

### Phase 3: UI 组件化 — 告别 Mixin（5-8 轮）

**目标：** `PowerSyncUI` 从 9-Mixin 深度继承变成组合式装配。

#### 迁移策略

每个 Tab 从 Mixin 变为独立的 `QWidget` 子类：
- 定义该 Tab 需要的最小 Protocol 接口
- Controller 实现该 Protocol
- `PowerSyncUI` 实例化独立 Tab，而非继承 Mixin
- 迁移完成后从继承链中删除对应 Mixin

#### 迁移顺序（从简到繁）

- [x] **概念验证：`LoopTestTab`（14 处 ctrl 引用）**
  - 从 `LoopTestTabMixin` 改为独立 `QWidget` 子类
  - 定义 `LoopTestTabAPI(Protocol)`：`get_loop_test_state()` / `record_loop_measurement()` / `is_loop_test_complete()`
  - 从 `PowerSyncUI` 继承链中删除 `LoopTestTabMixin`
  - 验证全流程正常
- [x] **`PtVoltageCheckTab`（10 处 ctrl 引用）**
- [x] **`PtPhaseCheckTab`（10 处 ctrl 引用）**
- [x] **`SyncTestTab`（16 处 ctrl 引用）**
- [x] **`PtExamTab`（20 处 ctrl 引用）**
- [x] **`WaveformTab`（5 处 ctrl 引用，注意 matplotlib canvas 生命周期）**
- [x] **`CircuitTab`（10 处 ctrl 引用）**
- [x] **`ControlPanel`（12 处 ctrl 引用）**
  - R45 已完成组件化与瘦身：`ui/panels/control_panel.py` 从 `776` 行降到 `328` 行，新增 `ui/widgets/control_panel/` 子包承接 `GeneratorCard / RunControlsPage / ParamControlsPage`
  - 12 处 `self.ctrl.sim_state.*` 读写按 §5.2 例外条款保留；3 处 `c.hw.*` 直连已改为宿主回调注入组件
- [x] **`TestPanel`（111 处 ctrl 引用）— 最后做，最复杂**
  - R30 已把骨架迁移为单体 `TestPanelWidget(QWidget)`，`_GenWiringWidget` / `_PTWiringWidget` 外提到 `ui/widgets/`
  - R31 按 Step1~5 继续把 `_build_step*` / `_refresh_tp_step*` 外提为 5 个独立 `QGroupBox` 子面板，`ui/test_panel.py` 收敛为 677 行的协调器
  - 子面板只通过 `TestPanelAPI + 构造注入回调` 协作，零 `self.ctrl`、零 service 穿透、零反向寻址
  - 剩余收口：`ui/test_panel.py` 还需从 677 降到 ≤ 500（抽顶部栏/步骤点/底部按钮构建函数到 `_panel_builders.py`）

#### TestPanel 子拆分明细

R30/R31 实际落点为 `ui/widgets/step_panels/`（不是最初规划的 `ui/test_steps/`）：

- [x] `ui/widgets/step_panels/loop_test_panel.py` — 第一步 UI 与交互（R31）
- [x] `ui/widgets/step_panels/pt_voltage_check_panel.py` — 第二步 UI 与交互（R31）
- [x] `ui/widgets/step_panels/pt_phase_check_panel.py` — 第三步 UI 与交互（R31）
- [x] `ui/widgets/step_panels/pt_exam_panel.py` — 第四步 UI 与交互（R31）
- [x] `ui/widgets/step_panels/sync_test_panel.py` — 第五步 UI 与交互（R31）
- [x] `ui/widgets/step_panels/_panel_builders.py::show_blackbox_dialog` / `show_blackbox_required_dialog` — 黑盒弹窗逻辑（R31；可在 R32 继续拆成独立 `_dialogs` 子模块）
- [x] `ui/widgets/step_panels/_panel_builders.py::show_assessment_result_dialog` / `show_random_fault_identification_dialog` — 成绩单与结果弹窗（R31；同上）
- [x] `ui/widgets/step_panels/_panel_builders.py::make_group/make_button/make_note_label/...` — 公共按钮、提示、文本助手（R31）
- [x] 将步骤业务判断从 UI 中迁回状态/服务层，UI 只读取状态
  - 已由 Phase 4 主线收口：R33–R44 完成 service/physics 显式依赖化与状态回写边界梳理，R43 落地最小信号试点，R45–R47 继续完成控制面板组件化、状态真值源收口与清理轮。

完成标准：
- `PowerSyncUI` 业务层面的 UI 不再使用 Mixin 多重继承，改为组合式装配。
  允许保留 **至多 1 个纯 UI 宿主构造层 Mixin**（当前为 `WidgetBuilderMixin`），
  但必须同时满足 §7.5 「纯构造层 Mixin 例外条款」全部项目，否则必须在下一轮
  降级为独立 `QWidget` 或 `ControlPanelBuilder` facade。
  - R32 状态：已按方案 B 收口；`WidgetBuilderMixin` 本体零改动，且 §5.2 守门扫描结果 = 0。
- `ui/test_panel.py` 主文件降到 <= 500 行。
  - R32 状态：`478` 行，已达标。
- 每个 Tab 组件是独立的 `QWidget`，可脱离其他 Tab 理解。
  - R31 状态：已达标（7 个 Tab + TestPanelWidget + 5 个 Step 子面板全部独立 `QWidget` / `QGroupBox`）。
- 新增 UI 逻辑落在拆出的子模块中，不回写主文件。
  - R32 状态：已达标；`_dialogs/` 子包已独立承接 4 个对话框函数。

### Phase 4: Service 显式依赖化 + 通信标准化（R33–R44，共 12 轮）

**目标：** 消除 service 层对 controller 的黑箱依赖，建立清晰的显式注入边界；最后引入 Signal/Slot 通信管道。

- [x] **R33–R42：逐个 service 消除 `self._ctrl`**（339 处 → 0）
  - 默认使用构造注入，按"先小后大、先纯 service 后编排器、再汇聚器"顺序
  - 详细轮次计划见 §10
- [x] **R43：引入 `ControllerSignals(QObject)` + 分阶段 render 迁移（阶段 1 已完成；阶段 2 仅最小试点达成；阶段 3 未执行）**
  - 前置条件：所有 service 的 `self._ctrl` = 0
  - 核心信号：`render_state_updated(RenderState)` / `step_state_changed(int, object)` / `assessment_finished(AssessmentResult)`
  - 分阶段迁移，不一次性全切
- [x] **R44：physics 层 `self.ctrl` 清理，完成 Phase 4 真正收官**
  - 目标文件：`services/physics_engine.py`、`services/_physics_measurement.py`、`services/_physics_arbitration.py`、`services/_physics_protection.py`
  - 核心目标：将 repo 级 `grep -rn "self\._ctrl\|self\.ctrl" services/ | wc -l` 从当前残留值收口到 `0`
- [ ] **收口旧键名兼容逻辑**
  - 清理历史命名债务
- [x] **收口状态真值源**
  - R46 已完成：新增 `domain/phase_order_state.py`，将 `pt_phase_orders`、4 组 blackbox order 与 `pt_blackbox_mode` 收口为单一状态容器
  - `PT3 ← g2_blackbox_order`、`PT1/PT2 ← PT1 黑盒 + g1_blackbox_order` 已以 `apply_*` 具名派生方法显式化
- [x] **`_BoolProxy` / 4 处 `_ctrl` 历史残留清理**
  - R46 已完成：删除 `app/main.py` 中 `_BoolProxy`、`_pt_blackbox_mode_proxy` 与 `pt_blackbox_mode` 兼容壳，仓内 `self._ctrl` 基线归零
- [x] **死 import / 死代码清理**
  - R47 已完成：`app/main.py` 与 3 个 service 文件中已确认未使用的 import 已清理；疑似私有 dead code 仅登记为候选，未在本轮物理删除
- [x] **`domain/` 类型标注补齐**
  - R47 已完成：`domain/` 当前函数/方法返回标注已全覆盖；`AssessmentContext.from_snapshot_and_ctrl(...)` 的 controller 形参已补到具名 Protocol
  - `services/` 全量类型标注仍留给独立专项轮，不在本轮范围内
- [x] **历史注释整理**
  - R47 已完成：清理 `app/main.py` 中与旧 `ctrl` 访问路径不符的历史性说明，保留仍解释“为什么这样写”的注释

完成标准：
- UI 与 Controller 之间通过 Signal/Slot 通信，无直接属性访问。
- 所有 Service 的 `self._ctrl` 引用数 = 0。
- 核心文件基本满足 `<= 500` 行。
- 主体架构边界清晰，新人可以在 30 分钟内理解系统分层。

---

## 5. 优先删除清单

| 优先级 | 删除对象 | 原因 |
|---|---|---|
| P1 | 已迁出后仅剩转发意义的旧方法 | 防止 Controller 继续变回上帝类 |
| P1 | 重复评分 helper 或旧评分拼装残留 | 防止评分系统继续臃肿 |
| P1 | `ui/test_panel.py` 中已被新子模块取代的旧步骤逻辑 | 防止步骤逻辑双轨并存 |
| P2 | 旧键名兼容回退逻辑 | 防止参数读取双轨并存 |
| P2 | 仅为过渡保留的旧 UI 包装方法 | 防止主窗口继续变胖 |

规则：新实现落地后，同轮就删旧实现。

### 5.1 组件化轮新增硬门禁：悬空宿主调用扫描

每轮组件化结束后必须执行：

```bash
grep -rn "_on_toggle_\(loop\|pt_voltage\|pt_phase\|sync\)" ui/
```

结果必须只出现在组件自身文件内（`ui/tabs/*_tab.py`），不得出现在 `ui/test_panel.py`、`ui/main_window.py` 或其他兄弟模块。

说明：
- R22 验收时遗漏了 `test_panel.py` 对宿主私有方法的调用，导致 step 1 切换抛 `AttributeError`，R26 补修。
- 后续组件化轮必须执行此扫描，防止同类回归。

### 5.2 WidgetBuilderMixin 例外守门扫描

每轮结束必须执行（基于仓库实际 `self.ctrl` 命名）：

```bash
grep -nE "self\.ctrl\.(flow_mgr|loop_svc|pt_voltage_svc|pt_phase_svc|pt_exam_svc|sync_svc|assessment_coord|fault_mgr|blackbox_handler|hw)\b" \
    ui/panels/control_panel.py
```

结果必须**为空**。任何 service / coordinator / hardware 层直连 = §7.5 例外条款失效 = 下一轮必须把 `WidgetBuilderMixin` 降级为独立 `QWidget` 或 `ControlPanelBuilder` facade。

别名直连也必须执行（封堵 `c = self.ctrl` 后再 `c.hw.*` / `c.flow_mgr.*` 等路径）：

```bash
grep -nE "\bc\.(hw|flow_mgr|loop_svc|pt_voltage_svc|pt_phase_svc|pt_exam_svc|sync_svc|assessment_coord|fault_mgr|blackbox_handler)\b" \
    ui/panels/control_panel.py ui/widgets/control_panel/*.py
```

结果同样必须**为空**。

说明：
- `self.ctrl.sim_state.*` 写入（如 `sim_state.multimeter_mode = checked`）与读取是被允许的“UI 参数层同步”，不计入本扫描。
- R32 建立此门时，现状 `ui/panels/control_panel.py` 结果 = 0，即 compliant。

---

## 6. 核心引擎快照测试规范

### 6.1 测试目录结构

```
tests/
├── snapshots/
│   ├── physics_normal.json
│   ├── physics_fault_E01.json
│   ├── assessment_normal.json
│   └── assessment_fault_random.json
├── test_physics_snapshot.py
└── test_assessment_snapshot.py
```

### 6.2 物理引擎快照流程
1. 构造最小 ctrl 替身（只含 `sim_state` + `pt_phase_orders` 等纯数据属性，不含 UI）。
2. 调用 `PhysicsEngine(stub).update_physics()` + `build_render_state()`。
3. 将 `RenderState` 序列化为 JSON（float 精度到小数点后 4 位）。
4. 首次运行生成基线文件，后续运行比对差异。

### 6.3 评分快照流程
1. 构造固定的 `AssessmentSession`，预填确定性事件流。
2. 调用 `AssessmentService.build_result(session, context)`。
3. 将 `AssessmentResult` 序列化比对。

### 6.4 何时必须跑
- 任何修改 `services/` 或 `domain/` 下文件的轮次。
- 快照不通过 = 要么是 Bug，要么需要更新基线并说明原因。
- 没有通过快照测试，不算完成本轮重构。

---

## 7. Mixin → 组合式组件 迁移规范

### 7.1 最终目标
`PowerSyncUI` 不再使用 Mixin 多重继承，改为组合式装配。

### 7.2 迁移模式

每个 Tab 从 Mixin 变为独立的 `QWidget` 子类：

```python
# 旧模式（Mixin，所有 self.xxx 共享命名空间）
class LoopTestTabMixin:
    def _build_loop_test_tab(self):
        self.loop_xxx = ...        # 污染宿主命名空间
        self.ctrl.xxx()            # 穿透式访问

# 新模式（独立 QWidget，隔离命名空间）
class LoopTestTab(QWidget):
    def __init__(self, api: LoopTestTabAPI):
        self._api = api            # 只接收最小接口
        self._loop_xxx = ...       # 属性自己持有
```

### 7.3 PowerSyncUI 最终形态

```python
class PowerSyncUI(QMainWindow):
    def __init__(self, ctrl):
        # ...
        self._waveform_tab = WaveformTab(ctrl)
        self._circuit_tab = CircuitTab(ctrl)
        self._loop_test_tab = LoopTestTab(ctrl)
        # ... 其余 Tab
        self.tab_widget.addTab(self._waveform_tab, "波形/相量")
        self.tab_widget.addTab(self._circuit_tab, "母排拓扑")
        # ...

    def render_visuals(self, rs: RenderState):
        self._waveform_tab.update_from(rs)
        self._circuit_tab.update_from(rs)
        # ...
```

### 7.4 过渡期规则
- 新增的 Tab 组件必须用独立 `QWidget` 类实现。
- 旧 Mixin 暂时保留，按 Phase 3 顺序逐个迁移。
- 每迁移完一个 Mixin，从继承链中删除。
- 不允许新增"宿主对象隐式共享一切状态"的 Mixin。

### 7.5 纯构造层 Mixin 例外条款

`PowerSyncUI` 至多保留 1 个纯 UI 宿主构造层 Mixin（当前为 `WidgetBuilderMixin`），必须同时满足下列全部条款：

1. **零 service 层穿透**：
   - **允许**：通过 `self.ctrl.sim_state.*` 做 UI 参数同步（读/写），以及通过构造出的 chrome 控件句柄让主窗口 / 其它组件消费。
   - **禁止**：`self.ctrl.flow_mgr` / `loop_svc` / `pt_voltage_svc` / `pt_phase_svc` / `pt_exam_svc` / `sync_svc` / `assessment_coord` / `fault_mgr` / `blackbox_handler` / `hw` 等 service / coordinator / hardware 层直连。
   - 硬门：§5.2 扫描结果必须 = 0。
2. **仅构造 chrome 级控件**：只构造主窗口右侧栏 / 状态标签 / 场景选择 / 万用表 checkbox 等 chrome 层控件，不得构造任何步骤测试流程相关 UI（Step1~5 面板、测试模式生命周期控件等）。
3. **不得被独立 Tab 反向依赖**：任何 `ui/tabs/*_tab.py` / `ui/widgets/step_panels/*.py` 不得出现 `self.parent().multimeter_cb` 或类似的反向寻址；其需要消费的 host 属性必须通过主窗口装配时的构造期回调或显式 `@property` 注入。
4. **host 属性通过白名单暴露**：Mixin 构造出的共享属性（如 `multimeter_cb` / `bus_status_lbl` / `ctrl_container` 等）只能由主窗口显式消费；主窗口不得把“宿主对象上有这个属性”作为隐式契约下放给子组件。
5. **行数上限**：`ui/panels/control_panel.py` 行数 ≤ 900。超过时必须按职责再切。

违反任一条 = 下一轮必须立即降级。

---

## 8. 固定回归清单

每轮重构后，至少人工验证以下项目：

| 回归项 | 必查内容 |
|---|---|
| 正常场景全流程 | 五步流程可完成；最终成绩单 `total_score >= 80`；`veto_reason` 为空 |
| 指定故障流程 | 指定故障注入、检测、修复、成绩单正常；修复后相关故障状态已清除 |
| 随机故障考核流程 | 随机场景判定、第四步前后门禁、成绩单正常；场景判错时额外扣 `10` 分 |
| 黑盒修复流程 | 黑盒打开、保存接线、复测、修复闭环正常；考核模式不直接泄露修复结果 |
| 成绩单流程 | `score_items / penalties / metrics / summary` 正常显示；总分与扣分说明一致 |
| 事故弹窗流程 | `E01/E02/E03` 在预期触发点弹出；点击修复后可继续流程 |
| 同期与波形页 | UI 能正常刷新，不出现明显回归；无参考源时 `Δf/ΔV/Δθ` 显示 `--` |

说明：没有完成上述回归，不算完成本轮重构。

### 8.1 核心逻辑测试原则
- 重构 `Assessment / Physics / Arbitration / Protection / Fault` 相关核心逻辑前，必须先补最小黑盒测试。
- 黑盒测试优先级：
  1. `输入事件流 -> AssessmentResult`
  2. `给定 SimulationState -> 仲裁/保护输出`
  3. `故障注入 -> 修复 -> 状态恢复`
- 没有测试保护，不进入大规模核心逻辑重构。

---

## 9. 已完成进度与轮次历史

### 已完成
- `C1`：物理层不再直接弹事故对话框，改为帧末统一消费。
- `C2（第一步）`：已拆出 `services/fault_manager.py`。
- `H1`：`_tick()` 已拆成物理异常边界与渲染异常边界，并增加连续失败可见提示。
- `H2`：三套事故对话框已收口为 `_show_accident_dialog(...)`，旧 `_legacy` 已删除。
- `H3`：控制器不再直接切换 `tab_widget` 或直接写入 PT3 变比控件，改为 UI 请求消费。
- `H4`：`assessment_service.build_result()` 已拆成 helper 化结构。
- `H5`：死母线倒计时已改为使用真实 `frame_dt`，不再写死 `0.033`。

### 当前未完成但已明确方向
- Phase 3：已关闭（R32 收口完成）。
- Phase 4 主线（R33–R44）及其后续 cleanups（R45–R49-Round2）已闭环；计划内 deferred 已清零。后续若继续推进，优先进入新的 UI 结构审查轮次，候选主目标为 `ui/tabs/waveform_tab.py`、`ui/main_window.py` 与 `ui/widgets/step_panels/_panel_builders.py`。

### 第 49 轮 (2026-04-28)：R49-Round2（`ui/styles.py` 拆分专项）
- 本轮唯一主攻目标：在不改任何颜色、间距、字重、控件视觉表现和宿主调用方式的前提下，将原 `ui/styles.py` 单文件主题入口拆为 `ui/styles/` 子包，同时保持 `apply_app_theme()` / `build_app_stylesheet()` API 与行为不变。
- 实际完成：
  - 已将原 `ui/styles.py` 物理拆分为 `ui/styles/` 子包，落地文件为：
    - `ui/styles/__init__.py`
    - `ui/styles/_theme_palette.py`
    - `ui/styles/_panels.py`
    - `ui/styles/_dialogs.py`
    - `ui/styles/_inputs.py`
    - `ui/styles/_misc.py`
    - `ui/styles/_buttons.py`
  - `ui/styles/__init__.py` 继续暴露 `APP_QSS`、`LIGHT_THEME`、`build_app_stylesheet()`、`apply_app_theme()`；`ui/main_window.py` 的 `from ui.styles import apply_app_theme` 无需改动即可继续工作。
  - 原单文件 `ui/styles.py` 已删除；拆分后样式域按 panels / dialogs / misc / buttons / inputs 固定分块，样式数值与选择器顺序保持不变。
- 接口变化：
  - 运行时公共导入面保持不变：`from ui.styles import apply_app_theme, build_app_stylesheet`
  - `_load_qdarkstyle_base()` 的 fallback 行为保持不变；未引入新主题 token、未新增 dark theme 分支。
- 规模与结构变化：
  - 原 `ui/styles.py` 行数：`1007`
  - 拆分后单文件行数：
    - `ui/styles/__init__.py = 51`
    - `ui/styles/_theme_palette.py = 27`
    - `ui/styles/_panels.py = 491`
    - `ui/styles/_dialogs.py = 37`
    - `ui/styles/_inputs.py = 197`
    - `ui/styles/_misc.py = 67`
    - `ui/styles/_buttons.py = 164`
  - 单文件样式风险已解除；拆分后最大单文件为 `_panels.py = 491`，回到健康阈值内。
- 验证结果：
  - G1 PASS：`.\\.venv\\Scripts\\python.exe -m pytest -q` = `15 passed`
  - G2 PASS：拆分前后 `build_app_stylesheet()` 规范化输出哈希一致，`sha256 = 6b4c53e960cf5046d36ed092bb308010d79af4587841aba9463d4bef5492984d`
  - G3 PASS：offscreen 下已完成 `QApplication -> PowerSyncController()` 最小启动与 `apply_app_theme()` 烟测，结果为 `controller_ok / theme_ok`
  - G4 PASS：`from ui.styles import apply_app_theme, build_app_stylesheet`、`APP_QSS`、`LIGHT_THEME` 导入兼容验证通过
- 范围与边界：
  - 本轮源码改动仅落在 `ui/styles/**` 与 checklist 本身；未改 `app/**`、`domain/**`、`services/**`、`tests/**`
  - README 旧路径引用在本轮源码完成后已单独完成文档同步清理；当前保留的低优先级项转为 `pt_phase_check_tab.py` 对 `_qs` 的跨模块私有依赖
- 下一轮起点：
  - `R49-Round3`：`ui/tabs/waveform_tab.py` 结构审查与职责拆分预研

### 第 49 轮 (2026-04-28)：R49-Round1（`services/` 返回类型标注专项）
- 本轮唯一主攻目标：在不改任何业务逻辑、控制流和 UI 行为的前提下，为 `services/` 目录建立统一、可复现的返回类型标注覆盖率统计口径，并将覆盖率提升到 `>= 90%`。
- 实际完成：
  - 新增 `scripts/check_annotation_coverage.py`，统计口径固定为：排除 `__init__ / __post_init__ / dunder`，计入私有方法、`@staticmethod`、`@classmethod`、嵌套 helper。
  - `services/` 返回类型标注覆盖率已从 `68/184 = 37.0%` 提升到 `184/184 = 100.0%`。
  - 已补齐返回标注的文件包括：
    - `services/phase_order_resolver.py`
    - `services/hardware_actions.py`
    - `services/fault_manager.py`
    - `services/blackbox_repair_handler.py`
    - `services/assessment_coordinator.py`
    - `services/assessment_service.py`
    - `services/loop_test_service.py`
    - `services/pt_voltage_check_service.py`
    - `services/pt_phase_check_service.py`
    - `services/pt_exam_service.py`
    - `services/sync_test_service.py`
    - `services/_physics_arbitration.py`
    - `services/_physics_core.py`
    - `services/_physics_measurement.py`
    - `services/_physics_protection.py`
    - `services/physics_engine.py`
- 删除了哪些旧代码：
  - 无；本轮只新增统计脚本，并在既有函数/方法上补 `-> ...` 返回标注与少量 `typing` import，不删除业务实现。
- 接口变化：
  - 运行时公共接口无变化；仅新增 `scripts/check_annotation_coverage.py` 作为静态质量入口。
  - `services/` 各文件的运行时行为、参数列表、状态读写路径与数值公式均保持不变。
- 耦合度变化：
  - `self._ctrl / self.ctrl` 基线保持不变，`services/` 仍为 `0`。
  - 本轮不涉及依赖注入边界、UI 耦合或业务编排收口。
- 验证结果：
  - G1 PASS：`.\\.venv\\Scripts\\python.exe -m pytest -q` = `15 passed`
  - G2 PASS：`py -3.11 scripts\\check_annotation_coverage.py services` = `184/184 = 100.0%`，退出码 `0`
  - G3 PASS：`py -3.11 -m py_compile` 已覆盖本轮白名单内全部改动文件与统计脚本
  - G4 PASS：本轮源码改动仅落在 `services/**/*.py`、`scripts/check_annotation_coverage.py` 与 checklist 本身；未改 `app/main.py`、`ui/**`、`tests/**`
- 下一轮起点：
  - `R49-Round2`：`ui/styles.py` 拆分专项

### 第 48 轮 (2026-04-28)：R48-Round4（CircuitTab 结构性拆分）
- 本轮唯一主攻目标：只处理顶部 review 中 `M6` 对应的结构性拆分，不混入新的 UI 行为调整、物理逻辑变更或样式专项。
- 实际完成：
  - 已将原单文件 `ui/tabs/circuit_tab.py` 拆为子包 `ui/tabs/circuit_tab/`，并落成 4 个模块：
    - `__init__.py`：保留 `CircuitTabAPI`、`CircuitTab(QWidget)`、`_build()`、`render()`、`redraw_canvas()`、`rebuild_circuit_diagram()`
    - `_phase_wiring.py`：承接 `PhaseWiringStatus`、`PhaseWiringSession`、相序仪接入/断开、三点接线点击与高亮渲染
    - `_record_tables.py`：承接 Step1~Step5 记录表构建与刷新
    - `_draw_topology.py`：承接拓扑绘制、CT/断路器/发电机/PT/接地与万用表渲染
  - `ui/_phase_wiring_state.py` 已整体迁入 `ui/tabs/circuit_tab/_phase_wiring.py` 并物理删除；`ui/panels/control_panel.py` 与 `ui/widgets/step_panels/pt_phase_check_panel.py` 已同步改到新导入路径。
  - `ui/tabs/pt_phase_check_tab.py` 仍通过 `from ui.tabs.circuit_tab import _qs` 取色；本轮已在子包入口 `__init__.py` 重新导出 `_qs`，保证旧消费路径不变。
  - `ui/main_window.py` 顶部架构说明中的 `CircuitTab` 路径已同步改为 `ui/tabs/circuit_tab/`，避免继续指向不存在的旧文件。
- 接口变化：
  - 外部导入面保持不变：`from ui.tabs.circuit_tab import CircuitTab`
  - `CircuitTab` 对宿主公开的方法保持不变：`render()`、`rebuild_circuit_diagram()`、`redraw_canvas()`、`get_phase_wiring_status()`、`get_phase_wiring_active_pt()`、`connect_phase_seq_meter()`、`disconnect_phase_seq_meter()`、`handle_phase_wiring_click()`
  - mixin 之间未互相导入，也不存在子模块反向导入 `ui.tabs.circuit_tab.__init__`
- 规模与耦合变化：
  - 原 `ui/tabs/circuit_tab.py` 单体文件行数：`1078`
  - 拆分后子包总行数：`989`
  - 单文件上限实测：
    - `__init__.py = 98`
    - `_phase_wiring.py = 133`
    - `_record_tables.py = 275`
    - `_draw_topology.py = 483`
  - 4 个目标文件均落在 Round4 提示词约束上限内。
- 验证结果：
  - G1 PASS：`pytest -q` 通过，结果为 `15 passed`
  - G2 PASS：`py -3.11 -m py_compile` 已覆盖 `ui/tabs/circuit_tab/` 4 个新文件、`ui/panels/control_panel.py`、`ui/widgets/step_panels/pt_phase_check_panel.py`、`ui/main_window.py`、`ui/tabs/pt_phase_check_tab.py`
  - G3 PASS：`from ui._phase_wiring_state` 在生产路径中已清零，旧文件 `ui/_phase_wiring_state.py` 已删除
  - G4 PASS：4 个新文件行数全部低于 Round4 设定上限，且拆分后总行数 `989 < 1078`
  - G5 PASS：offscreen 下已完成 `PowerSyncController()` 启动、`PT1` 三点接线走到 `ready`、以及 step 3/4/5 场景下 `CircuitTab.render(ctrl.physics.build_render_state())` 烟测，结果为 `round4_smoke_ok`
  - G6 PASS：`__init__.py` 负责汇总 mixin；`_phase_wiring.py`、`_record_tables.py`、`_draw_topology.py` 之间无互相导入
  - G7 PARTIAL：当前工作区不是 git repo，无法做提示词里建议的“拆分前后 5 帧快照逐帧比对”；本轮仅完成 offscreen 结构烟测与接口回归验证
- 范围与边界：
  - 本轮源码改动落在 `ui/tabs/circuit_tab/`、`ui/panels/control_panel.py`、`ui/widgets/step_panels/pt_phase_check_panel.py`、`ui/main_window.py` 与 checklist 本身
  - 未改 `app/**`、`domain/**`、`services/**`、`tests/**` 的行为逻辑

### 第 48 轮 (2026-04-28)：R48-Round3（运行时鲁棒性 + 异常处理）
- 本轮唯一主攻目标：只处理顶部 review 中会影响运行时诊断与可恢复性的 `M8 / m5`，并顺带收口本轮触及行的局部空格风格 `m4`；不改 physics 计算路径、不改 `_tick()` 主体顺序。
- 实际完成：
  - `app/main.py` 已在 `PowerSyncController` 类上新增 `_TICK_FAILURE_THRESHOLD = 5`，并将 `_handle_tick_failure()` 改为两段式处理：第 3 次连续失败只提示 statusBar，第 5 次连续失败直接 `stop()` 定时器并显示“物理引擎已熔断停止”。
  - `_clear_tick_failure_state()` 语义保持不变：只要成功完成一帧 render，仍会清空状态栏消息、连续失败计数和 `_tick_error_notified` 标志。
  - `ui/tabs/circuit_tab.py::_place_phase_seq_meter()` 已移除整段 `try / except Exception`，改为显式哨兵判断 `xlim/ylim` 是否退化为零跨度；合法退化时居中放置，相反真实 matplotlib 异常将继续向上抛出并交由 Round3 的 tick 熔断接住。
  - `ui/tabs/circuit_tab.py` 已修正 `event.inaxes != self.ax_circuit` 的缺空格问题，并清理本轮触及片段内的空白行空格；`ui/widgets/step_panels/pt_phase_check_panel.py` 中本轮触及的 3 处 trailing whitespace 也已清掉。
- 范围与边界：
  - 本轮源码改动仅落在 `app/main.py`、`ui/tabs/circuit_tab.py`、`ui/widgets/step_panels/pt_phase_check_panel.py` 与 checklist 本身。
  - 未改 `services/**`、`domain/**`、`tests/**`、其他 `ui/**` 文件；未动 `markersize = ...` 这类未在本轮提示词覆盖范围内的历史格式问题。
- 验证结果：
  - G1 PASS：`pytest -q` 通过，结果为 `15 passed`。
  - G2 PASS：`py -3.11 -m py_compile app/main.py ui/tabs/circuit_tab.py ui/widgets/step_panels/pt_phase_check_panel.py` 通过。
  - G3 PASS：offscreen 下已通过脚本注入 `RuntimeError("test")` 验证 tick 熔断路径：连续失败 3 次后 statusBar 出现“连续失败 3 次”，第 5 次后 `_timer.isActive() == False` 且 statusBar 切换为“物理引擎已熔断停止”。
  - G4 PASS：offscreen 下已 monkeypatch `ax_circuit.get_xlim/get_ylim` 为零跨度返回值，调用 `_place_phase_seq_meter()` 后相序仪按画布中心坐标放置成功，无异常抛出。
  - G5 PARTIAL：当前工作区不是 git repo，无法做正式 diff 边界校验；按本轮实际编辑记录，改动范围已限制在白名单文件 + checklist。

### 第 48 轮 (2026-04-27)：R48-Round2（封装边界 + 小型接口收口）
- 本轮唯一主攻目标：只处理顶部 review 中“已经有 public 意图，但内部仍穿透私有实现”的 3 项收口：`M4 / M5 / m7`，不触碰同步算法、公差参数与 `circuit_tab.py` 结构性拆分。
- 实际完成：
  - `services/sync_test_service.py` 已将私有 `_is_gen_synced(...)` 提升为公共 `is_gen_synced(...)`，并同步替换 service 内部 4 处自调用；`tests/support/stubs.py` 中的同名 stub 也已切换到公共名。
  - `app/main.py` 中 controller wrapper `is_gen_synced(...)` 已改为调用 `self.sync_svc.is_gen_synced(...)`，生产路径不再穿透 service 私有接口。
  - `ui/widgets/phase_seq_meter.py` 已新增公共 `current_sequence()`，只在 `_status == "connected"` 时透传 `_sequence`，其余状态统一返回 `"unknown"`。
  - `ui/main_window.py` 已改用 `self.phase_seq_meter.current_sequence()`，不再通过 `getattr(..., "_sequence", ...)` 读取 widget 私有状态。
  - 新增 `ui/_phase_wiring_state.py`，定义 `PhaseWiringStatus(StrEnum)`；`ui/tabs/circuit_tab.py`、`ui/panels/control_panel.py`、`ui/widgets/step_panels/pt_phase_check_panel.py` 已统一切到枚举值消费，不再在相序接线链路上裸比较 `"idle" / "wiring" / "ready"`。
- 范围与边界：
  - 本轮源码改动仅落在 `services/sync_test_service.py`、`tests/support/stubs.py`、`app/main.py`、`ui/widgets/phase_seq_meter.py`、`ui/main_window.py`、`ui/_phase_wiring_state.py`、`ui/tabs/circuit_tab.py`、`ui/panels/control_panel.py`、`ui/widgets/step_panels/pt_phase_check_panel.py` 与 checklist 本身。
  - 未改同步算法本身，`freq_tol / amp_tol / phase_tol` 保持不变；未触碰 `domain/**` 与其他 `services/**` / `ui/**`。
- 验证结果：
  - G1 PASS：`pytest -q` 通过，结果为 `15 passed`，无新增 warning。
  - G2 PASS：`py -3.11 -m py_compile services/sync_test_service.py tests/support/stubs.py app/main.py ui/widgets/phase_seq_meter.py ui/main_window.py ui/_phase_wiring_state.py ui/tabs/circuit_tab.py ui/panels/control_panel.py ui/widgets/step_panels/pt_phase_check_panel.py` 通过。
  - G3 PARTIAL：`rg -n '_is_gen_synced' app services tests ui` 为 `0` 命中；`rg -n 'getattr\\(self\\.phase_seq_meter, "_sequence"' ui` 为 `0` 命中；相序接线链路相关文件中的裸状态字符串已清零。但若按 `rg -n '"idle"|"wiring"|"ready"' ui` 全量执行，仍会命中 `ui/test_panel.py`、`ui/widgets/multimeter_widget.py`、`ui/widgets/step_panels/_panel_builders.py` 等与本轮白名单无关的历史字面量，因此仅能按“目标链路收口完成”判定通过。
  - G4 PASS：offscreen 下已完成 `PowerSyncController()` 启动 + `PT1` 接入 + 三点接线烟测，`PhaseWiringStatus` 状态流转与 Round1 一致。
  - G5 PASS：offscreen 下已验证 `phase_seq_meter.connect_pt("PT3", "FAULT")` 后 `current_sequence()` 返回 `"FAULT"`，并成功进入 `record_phase_sequence("PT3", "FAULT")` 路径。
  - G6 PARTIAL：当前工作区不是 git repo，无法做正式 diff 边界校验；按本轮实际编辑记录，改动范围已限制在白名单文件 + checklist。

### 第 48 轮 (2026-04-27)：R48-Round1（机械小修 + 死分支清理）
- 本轮唯一主攻目标：只处理顶部 review 中已确认安全、机械、低风险的 7 项小修：`C1 / M2 / M3 / M7 / m1 / m2 / m6`，不触碰 `services/**`、`domain/**`、`tests/**` 业务逻辑。
- 实际完成：
  - `app/main.py` 已删除硬编码 `False` 的 `get_pt_blackbox_mode()` wrapper，并清理重复的“PT 节点解析辅助”section 注释。
  - `ui/tabs/circuit_tab.py` 已完整删除 PT 黑盒渲染残留链路：`CircuitTabAPI.get_pt_blackbox_mode()`、局部变量 `pt_blackbox_mode`、内嵌 `draw_pt_blackbox_symbol()`、以及 PT1/PT2/PT3 上所有相关分支；`rebuild_circuit_diagram()` 的过期 docstring 已同步改为通用重绘说明。
  - `ui/tabs/circuit_tab.py` 已修正相序仪 `freq` 选择条件：`PT1/PT2 -> gen1`、`PT3 -> gen2`；三点接线结果标签绿色已统一为 `#2ecc71`。
  - `ui/test_panel.py` 已为 `TestPanelAPI` / `TestPanelWidget` 增加 `__test__ = False`，用于阻止 pytest 将生产类误收集为测试类。
  - `ui/widgets/step_panels/pt_phase_check_panel.py` 已删除未使用的 `_pt_recorded()` 与注释残留 `#and not self._pt_recorded(pt_name)`。
  - `ui/tabs/circuit_tab.py` 已删除 `__init__` 中冗余的 `_psm_terminal_markers` 初始化，仅保留 `_draw_circuit_content()` 内的真实重建点。
- 范围与边界：
  - 本轮源码改动仅落在 `app/main.py`、`ui/tabs/circuit_tab.py`、`ui/test_panel.py`、`ui/widgets/step_panels/pt_phase_check_panel.py` 与 checklist 本身。
  - `services/**`、`domain/**`、`tests/**`、其他 `ui/**` 文件均未修改。
- 验证结果：
  - G1 PASS：`pytest -q` 已跑通为 `15 passed`，且输出中 `0` 次 `PytestCollectionWarning`。
  - G2 PASS：`python -m py_compile app/main.py ui/tabs/circuit_tab.py ui/test_panel.py ui/widgets/step_panels/pt_phase_check_panel.py` 通过。
  - G3 PASS：`rg -n 'pt_blackbox_mode|on_pt_blackbox_toggle|reshuffle_pt_phase_orders|get_pt_blackbox_mode|set_g2_terminal_fault|draw_pt_blackbox_symbol' app domain services ui tests` 在生产代码路径下 `0` 命中。
  - G4 PASS：offscreen 启动 `PowerSyncController()` 无 `AttributeError / ImportError / Traceback`。
  - G5 AUTO PASS / MANUAL PENDING：offscreen 下已完成 `PT1 -> 断开 -> PT3 -> 断开` 的相序仪切换烟测，无异常；真实 GUI 手动冒烟待用户确认。
  - G6 PARTIAL：当前工作区不是 git repo，无法正式执行 diff 范围校验；按本轮实际编辑记录，改动范围已限制在白名单 4 个源码文件 + checklist。

### 第 47 轮 (2026-04-20)：死 import 清理 + `domain/` 类型标注补齐 + 历史注释整理
- 本轮唯一主攻目标：在不改动任何业务逻辑、签名与 UI 行为的前提下，完成一轮低风险机械清理，收口未使用 import、补齐 `domain/` 类型标注、清理已不成立的历史注释。
- 实际完成：
  - `app/main.py` 已删除未使用 import：`Any`、`Dict`、`Optional`、`SystemMode`、`StepProgressSnapshot`、`BlackboxRepairOutcome`、`FlowModePolicy`。
  - `services/_physics_arbitration.py` 已删除未使用 `SystemMode`；`services/_physics_measurement.py` 已删除未使用 `BreakerPosition`；`services/pt_voltage_check_service.py` 已删除未使用 `_PHASE_PAIR_LABEL`。
  - `domain/assessment.py` 已补齐唯一缺失的参数类型入口：为 `AssessmentContext.from_snapshot_and_ctrl(...)` 引入具名 `Protocol`，将 `ctrl` 形参标注为 `_AssessmentControllerLike`。
  - `domain/` 当前函数/方法返回标注已保持全覆盖；本轮未对 `domain/phase_order_state.py` 的业务接口做任何改动。
  - `app/main.py` 顶部架构说明、controller 类说明与状态区块注释已更新为与 R44–R46 之后的真实结构一致，不再保留“physics 通过 ctrl 读写”这类旧表述。
- 范围与边界：
  - 本轮未触碰 `ui/**`、`adapters/**`、`tests/**` 既有用例，也未改动除 3 个白名单文件外的其他 `services/**`。
  - 疑似私有 dead code 仅登记为候选，未在本轮物理删除，以避免误删风险。
- 验证结果：
  - G1 PASS：`/Users/promise/opt/anaconda3/envs/power_gui/bin/python -m pytest -q` = `16 passed`
  - G2 PASS：`py_compile app/main.py domain/*.py services/_physics_arbitration.py services/_physics_measurement.py services/pt_voltage_check_service.py` 通过
  - G3 PASS：参考清单中的死 import 已清理完毕
  - G4 PASS：`from __future__ import annotations` 现存语义指令未被误删
  - G5 PASS：`domain/` 当前函数/方法返回标注覆盖率维持全覆盖（`assessment.py 5/5`、`phase_order_state.py 12/12`，其余文件无函数定义）
  - G6 PASS：R45 / R46 基线未退化（`control_panel.py = 328`，全仓 `self._ctrl = 0`，`services/` 下 `self._ctrl | self.ctrl = 0`）
  - G7 PASS：`PhaseOrderState` 接口数量与命名保持不变
  - G8 PASS：diff 仅集中在 `app/main.py`、3 个白名单 service、`domain/assessment.py` 与 checklist；无函数体业务逻辑改动
  - G9 PASS：offscreen 启动无 `AttributeError / ImportError / Traceback`
  - G10 PASS：未越权文件扫描通过
- 后续建议：
  - 本轮完成后，“耦合清理 + UI 组件化 + 状态真值源收口 + 清理轮”这条主线已经收尾。
  - 后续若继续推进，优先级建议为：`ui/tabs/waveform_tab.py` 结构审查、`ui/main_window.py` 结构审查、`ui/widgets/step_panels/_panel_builders.py` 拆分。

### 第 46 轮 (2026-04-20)：状态真值源收口（`PhaseOrderState`）+ `_BoolProxy` 残留清理
- 本轮唯一主攻目标：将散落在 `PowerSyncController` 上的 6 个相序/黑盒容器属性收口为单一状态容器，并清理 `app/main.py` 中 `_BoolProxy` 留下的 4 处 `_ctrl` 历史残留。
- 实际完成：
  - 新增 `domain/phase_order_state.py`，定义 `PhaseOrderState`，集中持有：
    - `pt_phase_orders`
    - `g1_blackbox_order`
    - `g2_blackbox_order`
    - `pt1_pri_blackbox_order`
    - `pt1_sec_blackbox_order`
    - `pt_blackbox_mode`
  - `PowerSyncController.__init__` 已改为只创建 `self.phase_order_state = PhaseOrderState.default()`；原 6 个属性初始化已删除。
  - controller 已通过 `@property / setter` 保持 `pt_phase_orders / g1_blackbox_order / g2_blackbox_order / pt1_pri_blackbox_order / pt1_sec_blackbox_order / pt_blackbox_mode_val` 对外访问面不变；setter 统一改为**原地覆盖同一 list/dict 引用**。
  - `reshuffle_pt_phase_orders()`、`reset_pt_phase_orders()`、`reset_blackbox_orders()`、`set_g2_terminal_fault()`、`on_pt_blackbox_toggle()`、`get_pt_blackbox_mode()` 已下沉为 `phase_order_state` 方法委托；controller 仅保留 `rebuild_circuit_view()` 等副作用。
  - 两处隐式派生已显式化：
    - `apply_g2_blackbox_to_pt3()`
    - `apply_pt1_blackbox_to_pt_phases(pt1_net_order)`
  - `services/blackbox_repair_handler.py` 现保留 `sync_*` 业务编排入口，但写相序 dict 的实现已改为调用 `phase_order_state.apply_*`。
  - `_BoolProxy`、`_pt_blackbox_mode_proxy` 与 `pt_blackbox_mode` 兼容壳已物理删除；`pt_blackbox_mode_val` 仍通过 property 兼容既有读写路径。
- 行为与不变式说明：
  - 本轮核心变化是“整体替换容器”收口为“原地覆盖同一引用”；经全仓 grep 核对，`app/ui/services` 内不存在缓存 `ctrl.pt_phase_orders / g*_blackbox_order / pt1_*_blackbox_order / pt_blackbox_mode_val` 的写法，因此未破坏既有不变式。
  - `services/` 层 `self._ctrl | self.ctrl` 继续保持 `0`；R45 控制面板 baseline 未退化。
- 验证结果：
  - G1 PASS：`grep -rnE "self\._ctrl\b" app/ ui/ services/ domain/ adapters/ | wc -l = 0`
  - G2 PASS：`services/` 下 `self._ctrl | self.ctrl = 0`
  - G3 PASS：`_BoolProxy` / `_pt_blackbox_mode_proxy` / `pt_blackbox_mode.get()` 全仓清零
  - G4 PASS：`PhaseOrderState` 已在 `domain/phase_order_state.py` 定义并在 `app/main.py` import + 实例化
  - G5 PASS：未发现缓存 6 个容器引用的 `self._x = ctrl.xxx` 型写法
  - G7 PASS：`apply_g2_blackbox_to_pt3` / `apply_pt1_blackbox_to_pt_phases` 可发现且已被 `blackbox_repair_handler.sync_*` 调用
  - G9 PASS：`/Users/promise/opt/anaconda3/envs/power_gui/bin/python -m pytest -q` = `16 passed`
  - G10 PASS：`py_compile` 通过；`PhaseOrderState.default()` 输出默认 `PT1/PT2/PT3` 正序
  - G11 PASS：offscreen 启动无 `AttributeError / ImportError / Traceback`
- 下一轮建议：
  - R47：死代码 / 重复 UI / 旧注释块清理 + `domain/services` 类型标注补齐

### 第 45 轮 (2026-04-20)：Phase 3 收尾（`ControlPanel` 组件化与瘦身）
- 本轮唯一主攻目标：把 `ui/panels/control_panel.py` 从 776 行的宿主构造层大文件拆分为薄入口，并在不引入新 `self._ctrl` / `self.ctrl.<svc>` 穿透的前提下完成 `GeneratorCard / RunControlsPage / ParamControlsPage` 三分组件化。
- 实际完成：
  - 新增 `ui/widgets/control_panel/__init__.py`
  - 新增 `ui/widgets/control_panel/_widget_tokens.py`
  - 新增 `ui/widgets/control_panel/generator_card.py`
  - 新增 `ui/widgets/control_panel/run_controls.py`
  - 新增 `ui/widgets/control_panel/param_controls.py`
  - `ui/panels/control_panel.py` 已收敛为 Mixin 薄入口，负责标题、页切换、`QStackedWidget` 装配、故障预设对话框与宿主联动；原 Page0 / Page1 / `_build_gen_panel()` 主体均已迁入独立组件。
  - 三处别名形式直连服务已清零：`c.hw.instant_sync`、`c.hw.toggle_engine(...)`、`c.hw.toggle_breaker(...)` 均改为宿主侧窄口径回调注入组件。
  - 宿主属性契约保持不变：`btn_engine1/2`、`btn_breaker1/2`、`status1_lbl/status2_lbl`、`_gen1/_gen2_entry_map`、`bus_status_lbl`、`sim_speed_label`、`pause_btn` 等既有入口仍可通过 `self.<name>` 访问。
  - `_update_generator_buttons()` 保留在 Mixin，内部改为委托两张 `GeneratorCard.refresh()`，未破坏 `ui/main_window.py` 的既有调用点。
- 耦合与规模变化：
  - `ui/panels/control_panel.py` 行数 `776 -> 328`
  - 新组件文件行数：`generator_card.py = 192`、`run_controls.py = 156`、`param_controls.py = 143`、`_widget_tokens.py = 57`
- 验证结果：
  - G1 PASS：`ui/panels/control_panel.py` 当前 `328` 行（≤ 500）
  - G2 PASS：`self.ctrl.(flow_mgr|...|hw)` 扫描 = 0
  - G3 PASS：别名扫描 `c.(hw|flow_mgr|...)` 在 `control_panel.py` 与 `ui/widgets/control_panel/*.py` 中 = 0
  - G4 PASS：新组件文件内无 `ctrl` / `.hw.` 直连
  - G8 PASS（services 基线）：`grep -rnE "self\._ctrl|self\.ctrl\b" services/ | wc -l = 0`
  - G9 PASS：`/Users/promise/opt/anaconda3/envs/power_gui/bin/python -m pytest` = `13 passed`
  - G10 PASS（功能性烟测）：offscreen 启动可正常构建控制面板；未出现 `AttributeError`、导入循环或缺失控件契约
- 下一轮建议：
  - R46：状态真值源收口（`pt_phase_orders` 派生关系、`blackbox_order` 隐式同步）
  - R47：死代码 / 重复 UI / 旧注释块清理 + `domain/services` 类型标注补齐

### 第 44 轮 (2026-04-20)：Phase 4 真正收官（physics 层 `self.ctrl` 清零）
- 本轮唯一主攻目标：将 physics 层 4 个文件中的 `self.ctrl` 全部替换为显式 keyword-only 构造注入，使 `services/` 目录下 `self._ctrl | self.ctrl` 最终归零。
- 实际完成：
  - `services/physics_engine.py` 已改为 10 参 keyword-only 构造注入：`sim_state`、`flow_mgr`、`phase_resolver`、`sync_svc`、`get_pt_phase_orders()`、`get_loop_test_state()`、`get_pt_voltage_check_state()`、`is_sync_test_active()`、`mark_fault_detected()`、`queue_accident_dialog()`。
  - `services/_physics_arbitration.py`、`services/_physics_measurement.py`、`services/_physics_protection.py` 内原有 `self.ctrl.*` 路径已全部替换为 `self._sim_state`、`self._flow_mgr`、`self._phase_resolver`、`self._sync_svc`、3 个 accessor、1 个 query callback 与 2 个 behavior callback。
  - `services/_physics_core.py` 经核对本来就是 `0` 处 `self.ctrl`，本轮未改动。
  - `app/main.py` 已仅在 `self.physics = PhysicsEngine(...)` 构造处完成适配；未改动 `_tick`、`build_render_state()`、`render_visuals`、`ControllerSignals` 或任何 UI 路径。
- 删除了哪些旧代码：
  - 删除 `PhysicsEngine.__init__(self, ctrl)` 与 `self.ctrl = ctrl`。
  - 删除 physics 层 4 个文件内全部 31 处 `self.ctrl` 访问。
- 接口变化：
  - `PhysicsEngine` 构造函数改为 keyword-only 10 参依赖注入。
  - `update_physics()` / `build_render_state()` 方法签名保持不变。
- 耦合度变化：
  - `services/physics_engine.py`、`services/_physics_arbitration.py`、`services/_physics_measurement.py`、`services/_physics_protection.py` 的 `self.ctrl` 总量 `31 -> 0`。
  - `services/` 目录下 repo 级 `self._ctrl | self.ctrl` 总量 `31 -> 0`。
  - Phase 4 全阶段累计耦合度：`339 -> 0`，真正收官。
- 快照测试：PASS（`/Users/promise/opt/anaconda3/envs/power_gui/bin/python -m pytest tests/ -q`，13/13 通过）
- 回归清单：PASS（范围检查、repo 级 grep 清零、`py_compile`、offscreen 单帧 physics 冒烟全部通过）
- 下一轮起点：Phase 4 已真正收官；后续视 UX/性能反馈决定是否启动 R43 阶段 3（轮询压缩）或进入新阶段

### 第 43 轮 (2026-04-20)：Phase 4 信号层骨架落地（`ControllerSignals(QObject)` 引入 + 阶段 2 最小试点）
- 本轮唯一主攻目标：在不改动 `_tick -> render_visuals` 主路径的前提下，引入 controller → UI 信号骨架，并完成 2 个最小、纯文本/状态类 UI 消费者试点。
- 实际完成：
  - 新增 `app/controller_signals.py`，集中声明 2 个 controller → UI 信号：`step_changed(int, int)`、`assessment_mode_changed(bool)`。
  - `PowerSyncController` 已在构造早期创建 `self.signals = ControllerSignals()`；UI 构造前即可完成信号暴露。
  - `assessment_mode_changed` 已接入 controller `test_flow_mode` setter：当流程模式切换导致“是否为考核模式”发生变化时触发 emit。
  - `step_changed` 已接入 controller `get_test_progress_snapshot(step, ...)` 这一单点观测入口：当测试面板推导出的当前步骤发生变化时，仅在新旧 step 不同的情况下 emit。
  - `ui/main_window.py` 已接入两个 slot：`_on_step_changed(old_step, new_step)`、`_on_assessment_mode_changed(is_assessment)`，并将它们落地为主窗口底部状态栏的两个纯文本状态徽标。
  - `render_visuals` 主渲染链保持原样，`_tick` 周期、`build_render_state()`、waveform / circuit / phasor / matplotlib canvas 相关逻辑均未改动。
  - `app/main.py` 除 `ControllerSignals` 导入外，仅在 `PowerSyncController` 内补了最小构造适配与 emit 逻辑；`services/**`、`tests/**`、`domain/**`、`adapters/**` 均保持零改动。
  - 阶段 3（`_tick` 压缩 / 轮询降频 / `render_visuals` 瘦身）本轮未执行，明确留待后续独立立项。
- 删除了哪些旧代码：
  - 无大规模删除；本轮目标是建立信号层骨架与最小试点，而非压缩 render 路径。
- 接口变化：
  - 新增 `app/controller_signals.py` 与 `PowerSyncController.signals`。
  - 公开 Service API 保持不变；controller 仍保留现有主循环与 UI 入口。
- 阶段结果：
  - `ControllerSignals` 已成功落地；Phase 4 的 signal 骨架已建立，但阶段 2 仅完成“新增顶层状态徽标”的最小试点，尚未真正迁移既有 `render_visuals` 轮询消费者。
  - Phase 4 service 层 `self._ctrl` 总量继续保持 `0`。
  - repo 级 `grep -rn "self\._ctrl\|self\.ctrl" services/` 仍因 physics 相关模块保留 `31` 处 `self.ctrl` 命中，因此 Phase 4 最终收官点推迟到 R44。
- 快照测试：PASS（`/Users/promise/opt/anaconda3/envs/power_gui/bin/python -m pytest tests/ -q`，13/13 通过）
- 回归清单：PASS（范围检查、`py_compile`、offscreen 导入冒烟、service 层 `self._ctrl` 归零检查全部通过）
- 下一轮起点：Phase 4 — Round 44：physics 层（`physics_engine.py` / `_physics_*.py`）`self.ctrl` 清理，完成真正收官

### 第 42 轮 (2026-04-20)：Phase 4 第十轮（`assessment_coordinator.py` 显式依赖注入，Phase 4 service 收口）
- 本轮唯一主攻目标：将 `services/assessment_coordinator.py` 中的 61 处 `self._ctrl` 全部替换为显式构造注入；本轮是 Phase 4 service 层的收口点。
- 实际完成：
  - `AssessmentCoordinator` 已改为 keyword-only 19 参构造注入（Phase 4 新高）。
  - 稳定对象直接注入：`sim_state`、`flow_mgr`、`assessment_svc`。
  - accessor 回调：`get_fault_mgr()`、`get_assessment_session()`、`get_loop_test_state()`、`get_pt_voltage_check_state()`、`get_pt_phase_check_state()`、`get_pt_exam_states()`、4 个 blackbox order 访问器。
  - setter 回调：`set_assessment_session()`、`set_last_fault_detected()`；两者分别用于整体替换考核 session 和写回 `_last_fault_detected`。
  - 查询回调：`is_loop_test_complete()`、`is_pt_voltage_check_complete()`、`is_pt_phase_check_complete()`。
  - 行为回调：`build_assessment_context()`，在 `app/main.py` 内封装对 `AssessmentContext.from_snapshot_and_ctrl(snapshot, self)` 的调用，从而将 ctrl 依赖约束在适配层。
  - `app/main.py` 已仅在 `AssessmentCoordinator(...)` 构造处完成适配，并在顶部新增 `AssessmentContext` 导入；`tests/**`、`ui/**`、其他 `services/**` 全部保持零改动。
- 删除了哪些旧代码：
  - 删除 `AssessmentCoordinator.__init__(self, ctrl)` 与 `self._ctrl = ctrl`。
  - 删除文件内全部 61 处 `self._ctrl.*` 直接访问。
- 接口变化：
  - `AssessmentCoordinator` 构造函数改为 19 参 keyword-only 依赖注入。
  - 公开方法签名保持不变；controller 仍通过既有桥接方法驱动考核会话生命周期。
- 耦合度变化：
  - `services/assessment_coordinator.py` 的 `self._ctrl` 引用数 `61 -> 0`。
  - Phase 4 service 层 `self._ctrl` 总量 `61 -> 0`，service 子阶段收口。
- 快照测试：PASS（`/Users/promise/opt/anaconda3/envs/power_gui/bin/python -m pytest tests/ -q`，13/13 通过）
- 回归清单：PASS（范围检查、`py_compile`、offscreen 导入冒烟、伪黑箱扫描全部通过）
- 下一轮起点：Phase 4 — Round 43：`ControllerSignals(QObject)` 引入 + 分阶段 render 迁移

### 第 41 轮 (2026-04-20)：Phase 4 第九轮（`pt_exam_service.py` 显式依赖注入）
- 本轮唯一主攻目标：将 `services/pt_exam_service.py` 中的 `self._ctrl` 全部替换为显式构造注入，在大型 step service 上继续验证“稳定对象 + 单 accessor 状态字典 + 查询回调 + 行为回调 + 私有方法内联”组合可控。
- 实际完成：
  - `PtExamService` 已改为 keyword-only 8 参构造注入：`sim_state`、`flow_mgr`、`get_physics()`、`get_pt_exam_states()`、`is_loop_test_complete()`、`is_pt_voltage_check_complete()`、`is_pt_phase_check_complete()`、`append_assessment_event()`。
  - `pt_exam_states` 作为 `{1: PtExamState, 2: PtExamState}` 稳定字典，使用单一 accessor 注入；`reset_pt_exam()` 仅按键替换条目，因此未新增 setter，`start/stop/finalize/quick record` 等路径均通过当前 dict 访问。
  - `physics` 因 controller 初始化顺序晚于 `pt_exam_svc` 创建，继续按 `get_physics()` accessor callback 延迟求值；`record_pt_diff_measurement()` 与 `record_all_pt_measurements_quick()` 两处均已收口为单次 `physics = self._get_physics()` 复用。
  - 第一、二、三步前置门禁全部改为 query callback；`assessment_coord.append_assessment_event()` 已改为行为回调。
  - controller 私有桥接 `_get_generator_state(gen_id)` 已按 R39 既定模式在 service 内部重新定义为私有方法，仅依赖已注入的 `sim_state`。
  - `app/main.py` 已仅在 `PtExamService(...)` 构造处完成适配；`tests/**`、`ui/**`、其他 `services/**` 全部保持零改动。
- 删除了哪些旧代码：
  - 删除 `PtExamService.__init__(self, ctrl)` 与 `self._ctrl = ctrl`。
  - 删除文件内全部 49 处 `self._ctrl.*` 直接访问。
- 接口变化：
  - `PtExamService` 的构造函数改为 keyword-only 8 参依赖注入。
  - 公开方法签名保持不变；controller 仍通过既有入口驱动第四步测量与完成逻辑。
- 耦合度变化：
  - `services/pt_exam_service.py` 的 `self._ctrl` 引用数 `49 -> 0`。
  - Phase 4 service 层 `self._ctrl` 总量 `110 -> 61`。
- 快照测试：PASS（`/Users/promise/opt/anaconda3/envs/power_gui/bin/python -m pytest tests/ -q`，13/13 通过）
- 回归清单：PASS（范围检查、`py_compile`、offscreen 导入冒烟、伪黑箱扫描全部通过）
- 下一轮起点：Phase 4 — Round 42：`assessment_coordinator.py` 显式依赖注入

### 第 40 轮 (2026-04-20)：Phase 4 第八轮（`pt_phase_check_service.py` 显式依赖注入）
- 本轮唯一主攻目标：将 `services/pt_phase_check_service.py` 中的 `self._ctrl` 全部替换为显式构造注入，在大型 step service 上验证“直接注入 + accessor / setter + 查询回调 + 行为回调”组合继续可控。
- 实际完成：
  - `services/pt_phase_check_service.py` 已改为 keyword-only 构造注入，不再持有 `ctrl`；当前依赖为 `sim_state`、`flow_mgr`、`get_physics()`、`get_pt_phase_check_state()`、`set_pt_phase_check_state()`、`is_loop_test_complete()`、`is_pt_voltage_check_complete()`、`append_assessment_event()`、`mark_fault_detected()`、`set_pt_phase_check_feedback()`、`record_pt_phase_check_result()`、`mark_pt_phase_check_completed()`。
  - `pt_phase_check_state` 因会在 `reset_pt_phase_check()` 中整体替换，已改为 accessor + setter callback 注入；`started`、`completed`、`records`、`result`、`feedback`、`feedback_color` 等读写路径均保持原业务语义。
  - `physics` 因 controller 初始化顺序约束晚于 `pt_phase_svc` 创建，继续按 accessor callback（`get_physics()`）延迟求值；`meter_phase_match`、`meter_reading` 已通过同一次 accessor 取值复用。
  - 第一、二步门禁已改为 `is_loop_test_complete()` / `is_pt_voltage_check_complete()` 查询回调；评估事件记录、故障标记、第三步反馈、记录写回、完成标记均已改为细粒度行为回调。
  - `app/main.py` 已仅在 `PtPhaseCheckService(...)` 构造处完成适配；`tests/**`、`ui/**`、其他 `services/**` 均保持零改动。
- 删除了哪些旧代码：
  - 删除 `PtPhaseCheckService.__init__(self, ctrl)` 与 `self._ctrl = ctrl`。
  - 删除 `pt_phase_check_service.py` 内全部 38 处 `self._ctrl.*` 直接访问。
- 接口变化：
  - `PtPhaseCheckService` 的构造函数改为 keyword-only 显式依赖注入，当前共 12 个参数。
  - 公开方法签名保持不变；controller 仍通过既有桥接方法暴露第三步反馈、记录写回和完成标记。
- 耦合度变化：
  - `services/pt_phase_check_service.py` 的 `self._ctrl` 引用数 `38 -> 0`。
  - Phase 4 service 层 `self._ctrl` 总量 `148 -> 110`。
- 快照测试：PASS（`/Users/promise/opt/anaconda3/envs/power_gui/bin/python -m pytest tests/ -q`，13/13 通过）
- 回归清单：PASS（范围检查、`py_compile`、offscreen 导入冒烟、伪黑箱扫描全部通过）
- 下一轮起点：Phase 4 — Round 41：`pt_exam_service.py` 显式依赖注入

### 第 39 轮 (2026-04-17)：Phase 4 第七轮（`hardware_actions.py` 显式依赖注入）
- 本轮唯一主攻目标：将 `services/hardware_actions.py` 中的 `self._ctrl` 全部替换为显式构造注入，在 Phase 4 耦合面最杂的动作编排器上验证“直接注入 + accessor 回调 + 7 种 query 回调 + 7 种行为回调 + 私有方法内联”的极限组合。
- 实际完成：
  - `services/hardware_actions.py` 已改为 keyword-only 构造注入，不再持有 `ctrl`；当前依赖为 `sim_state`（直接注入）、`get_physics()`（accessor 回调）、7 个 query 回调（`is_loop_test_complete`、`is_pt_voltage_check_complete`、`is_pt_phase_check_complete`、`is_pt_exam_recorded`、`is_sync_test_complete`、`is_sync_test_active`、`is_pt_exam_started`）、7 个行为回调（`append_assessment_event`、`set_pt_exam_feedback`、`request_ui_tab`、`show_warning`、`show_e01_accident_dialog`、`show_e02_accident_dialog`、`show_e03_accident_dialog`）。
  - `_get_generator_state(gen_id)` 不再经 controller 私有方法调用，已内联为 `HardwareActions` 自身的私有方法，仅依赖已注入的 `sim_state`。
  - 所有 UI 交互（`show_warning`、3 个事故对话框）均改为行为回调，`HardwareActions` 不再持有或穿透 `self._ctrl.ui`。
  - `is_sync_test_active()` 原为 controller 自身方法，已改为 query 回调注入；`pt_exam_states[gen_id].started` 状态读取已改为 `is_pt_exam_started(gen_id)` query 回调。
  - `app/main.py` 已仅在 `HardwareActions(...)` 构造处完成适配；`tests/**`、`ui/**`、其他 `services/**` 均保持零改动。
- 删除了哪些旧代码：
  - 删除 `HardwareActions.__init__(self, ctrl)` 与 `self._ctrl = ctrl`。
  - 删除 `hardware_actions.py` 内全部 35 处 `self._ctrl.*` 直接访问。
- 接口变化：
  - `HardwareActions` 的构造函数改为 keyword-only 显式依赖注入，当前共 16 个参数（Phase 4 最高记录）。
  - 公开方法签名保持不变；controller 仍通过既有薄转发方法暴露硬件动作。
- 耦合度变化：
  - `services/hardware_actions.py` 的 `self._ctrl` 引用数 `35 -> 0`。
  - Phase 4 service 层 `self._ctrl` 总量 `183 -> 148`。
- 快照测试：PASS（`/Users/promise/opt/anaconda3/envs/power_gui/bin/python -m pytest tests/ -q`，13/13 通过）
- 回归清单：PASS（范围检查、`py_compile`、offscreen 导入冒烟、伪黑箱扫描全部通过）
- 下一轮起点：Phase 4 — Round 40：`pt_phase_check_service.py` 显式依赖注入

### 第 38 轮 (2026-04-17)：Phase 4 第六轮（`fault_manager.py` 显式依赖注入）
- 本轮唯一主攻目标：将 `services/fault_manager.py` 中的 `self._ctrl` 全部替换为显式构造注入，在故障管理器上验证“直接注入 + 行为回调 + setter 回调 + accessor 回调 + 4 对 blackbox order accessor/setter + 内联 reset”组合。
- 实际完成：
  - `services/fault_manager.py` 已改为 keyword-only 构造注入，不再持有 `ctrl`；当前依赖为 `sim_state`、`blackbox_handler`、`append_assessment_event()`、`request_pt_ratio_row_update()`、`set_last_fault_detected()`、`get_pt_phase_orders()`、以及 4 组 blackbox order 的 accessor + setter callback。
  - `blackbox_handler` 因 controller 初始化顺序正确（先于 `fault_mgr` 创建），已采用直接注入而非 accessor callback。
  - `reset_blackbox_orders()` 不再经 controller 调用，已内联为 `_reset_blackbox_orders()` 私有方法，利用已注入的 4 个 setter 将列表重置为 `['A', 'B', 'C']`。
  - `_last_fault_detected` 的写入已改为 setter callback（`set_last_fault_detected`），不再直接写 controller 私有属性。
  - `assessment_coord.append_assessment_event` 已改为行为回调注入；`app/main.py` 已仅在 `FaultManager(...)` 构造处完成适配；`tests/**`、`ui/**`、其他 `services/**` 均保持零改动。
- 删除了哪些旧代码：
  - 删除 `FaultManager.__init__(self, ctrl)` 与 `self._ctrl = ctrl`。
  - 删除 `fault_manager.py` 内全部 40 处 `self._ctrl.*` 直接访问。
- 接口变化：
  - `FaultManager` 的构造函数改为 keyword-only 显式依赖注入，当前共 14 个参数。
  - 公开方法签名保持不变；controller 仍通过既有薄转发方法暴露故障管理动作。
- 耦合度变化：
  - `services/fault_manager.py` 的 `self._ctrl` 引用数 `40 -> 0`。
  - Phase 4 service 层 `self._ctrl` 总量 `223 -> 183`。
- 快照测试：PASS（`/Users/promise/opt/anaconda3/envs/power_gui/bin/python -m pytest tests/ -q`，13/13 通过）
- 回归清单：PASS（范围检查、`py_compile`、offscreen 导入冒烟、伪黑箱扫描全部通过）
- 下一轮起点：Phase 4 — Round 39：`hardware_actions.py` 显式依赖注入

### 第 37 轮 (2026-04-17)：Phase 4 第五轮（`blackbox_repair_handler.py` 显式依赖注入）
- 本轮唯一主攻目标：将 `services/blackbox_repair_handler.py` 中的 `self._ctrl` 全部替换为显式构造注入，在首个编排类 service 上验证“大量可变状态双向读写 + 行为回调 + 协作者 accessor”组合是否可控。
- 实际完成：
  - `services/blackbox_repair_handler.py` 已改为 keyword-only 构造注入，不再持有 `ctrl`；当前依赖为 `sim_state`、`flow_mgr`、`get_fault_mgr()`、`append_assessment_event()`、`get_pt_phase_orders()`、以及 4 组 blackbox order 的 accessor + setter callback。
  - `fault_mgr` 因 controller 初始化顺序约束晚于 `blackbox_handler` 创建，已按 accessor callback（`get_fault_mgr()`）延迟求值；`repair_fault(...)` 不再经 controller 薄转发，而是通过 `self._get_fault_mgr().repair_fault(...)` 直接调用。
  - `pt_phase_orders` 虽在 handler 创建前已存在，但运行期会在 reset 流程中整体替换，已改为 accessor callback；handler 通过 `self._get_pt_phase_orders()` 取得当前 dict 后直接更新 `PT1/PT2/PT3` 条目。
  - `g1_blackbox_order`、`g2_blackbox_order`、`pt1_pri_blackbox_order`、`pt1_sec_blackbox_order` 四个列表已全部改为 accessor + setter callback，避免捕获会被整体替换的裸 list 引用。
  - `app/main.py` 已仅在 `BlackboxRepairHandler(...)` 构造处完成适配；`tests/**`、`ui/**`、其他 `services/**` 均保持零改动。
- 删除了哪些旧代码：
  - 删除 `BlackboxRepairHandler.__init__(self, ctrl)` 与 `self._ctrl = ctrl`。
  - 删除 `blackbox_repair_handler.py` 内全部 36 处 `self._ctrl.*` 直接访问。
- 接口变化：
  - `BlackboxRepairHandler` 的构造函数改为 keyword-only 显式依赖注入，当前共 13 个参数（为 Phase 4 迄今最多的一轮）。
  - 公开方法签名保持不变；controller 仍通过既有薄转发方法暴露黑盒相关动作。
- 耦合度变化：
  - `services/blackbox_repair_handler.py` 的 `self._ctrl` 引用数 `36 -> 0`。
  - Phase 4 service 层 `self._ctrl` 总量 `259 -> 223`。
- 快照测试：PASS（`/Users/promise/opt/anaconda3/envs/power_gui/bin/python -m pytest tests/ -q`，13/13 通过）
- 回归清单：PASS（范围检查、`py_compile`、offscreen 导入冒烟、伪黑箱扫描全部通过）
- 下一轮起点：Phase 4 — Round 38：`fault_manager.py` 显式依赖注入

### 第 36 轮 (2026-04-17)：Phase 4 第四轮（`pt_voltage_check_service.py` 显式依赖注入）
- 本轮唯一主攻目标：将 `services/pt_voltage_check_service.py` 中的 `self._ctrl` 全部替换为显式构造注入，在第一个中型 step service 上继续验证 R35 已稳定下来的状态/accessor/query callback 组合。
- 实际完成：
  - `services/pt_voltage_check_service.py` 已改为 keyword-only 构造注入，不再持有 `ctrl`；当前依赖为 `sim_state`、`flow_mgr`、`get_physics()`、`get_pt_voltage_check_state()`、`set_pt_voltage_check_state()`、`is_loop_test_complete()`、`append_assessment_event()`。
  - `pt_voltage_check_state` 因会在 `reset_pt_voltage_check()` 中整体替换，已改为 accessor + setter callback 注入；`started`、`feedback`、`feedback_color`、`completed`、`records` 等状态读写均直接落到 `PtVoltageCheckState`。
  - `physics` 因 controller 初始化顺序约束，继续采用 accessor callback（`get_physics()`）延迟求值；`meter_voltage`、`meter_status`、`meter_reading` 的读取路径保持原业务语义不变。
  - 前置步骤门禁 `loop_svc.is_loop_test_complete()` 已改为 query callback；`flow_mgr` 作为稳定协作者直接注入；`assessment_coord.append_assessment_event` 已改为行为回调注入。
  - `app/main.py` 已仅在 `PtVoltageCheckService(...)` 构造处完成适配；`tests/**`、`ui/**`、其他 `services/**` 均保持零改动。
- 删除了哪些旧代码：
  - 删除 `PtVoltageCheckService.__init__(self, ctrl)` 与 `self._ctrl = ctrl`。
  - 删除 `pt_voltage_check_service.py` 内全部 24 处 `self._ctrl.*` 直接访问。
- 接口变化：
  - `PtVoltageCheckService` 的构造函数改为 keyword-only 显式依赖注入。
  - 公开方法签名保持不变；controller 仍通过 `self.pt_voltage_svc.xxx()` 做薄转发。
- 耦合度变化：
  - `services/pt_voltage_check_service.py` 的 `self._ctrl` 引用数 `24 -> 0`。
  - Phase 4 service 层 `self._ctrl` 总量 `283 -> 259`。
- 快照测试：PASS（`/Users/promise/opt/anaconda3/envs/power_gui/bin/python -m pytest tests/ -q`，13/13 通过）
- 回归清单：PASS（范围检查、`py_compile`、offscreen 导入冒烟、伪黑箱扫描全部通过）
- 下一轮起点：Phase 4 — Round 37：`blackbox_repair_handler.py` 显式依赖注入

### 第 35 轮 (2026-04-17)：Phase 4 第三轮（`sync_test_service.py` 显式依赖注入）
- 本轮唯一主攻目标：将 `services/sync_test_service.py` 中的 `self._ctrl` 全部替换为显式构造注入，继续验证 R34 的三类依赖拆分在另一类带状态门禁的 service 中可横向复用。
- 实际完成：
  - `services/sync_test_service.py` 已改为 keyword-only 构造注入，不再持有 `ctrl`；当前依赖为 `sim_state`、`flow_mgr`、`fault_mgr`、`get_physics()`、`get_sync_test_state()`、`set_sync_test_state()`、`is_loop_test_complete()`、`is_pt_voltage_check_complete()`、`is_pt_phase_check_complete()`、`is_pt_exam_recorded()`。
  - `sync_test_state` 因会在 `reset_sync_test()` 中整体替换，已改为 accessor + setter callback 注入；`started`、`feedback`、`feedback_color`、`round1_done`、`round2_done`、`completed` 等状态写入均直接落到 `SyncTestState`。
  - 四个前置步骤门禁查询已改为 query callback 注入，不再经 `self._ctrl.loop_svc` / `pt_voltage_svc` / `pt_phase_svc` / `pt_exam_svc` 穿透。
  - `flow_mgr` 与 `fault_mgr` 已作为稳定协作者直接注入；`physics` 因 controller 初始化顺序约束，继续采用 accessor callback（`get_physics()`）延迟求值。
  - `app/main.py` 已仅在 `SyncTestService(...)` 构造处完成适配；`tests/**`、`ui/**`、其他 `services/**` 均保持零改动。
- 删除了哪些旧代码：
  - 删除 `SyncTestService.__init__(self, ctrl)` 与 `self._ctrl = ctrl`。
  - 删除 `sync_test_service.py` 内全部 27 处 `self._ctrl.*` 直接访问。
- 接口变化：
  - `SyncTestService` 的构造函数改为 keyword-only 显式依赖注入。
  - 公开方法签名保持不变；controller 仍通过 `self.sync_svc.xxx()` 做薄转发。
- 耦合度变化：
  - `services/sync_test_service.py` 的 `self._ctrl` 引用数 `27 -> 0`。
  - Phase 4 service 层 `self._ctrl` 总量 `310 -> 283`。
- 快照测试：PASS（`/Users/promise/opt/anaconda3/envs/power_gui/bin/python -m pytest tests/ -q`，13/13 通过）
- 回归清单：PASS（范围检查、`py_compile`、offscreen 导入冒烟、伪黑箱扫描全部通过）
- 下一轮起点：Phase 4 — Round 36：`pt_voltage_check_service.py` 显式依赖注入

### 第 34 轮 (2026-04-17)：Phase 4 第二轮（`loop_test_service.py` 显式依赖注入）
- 本轮唯一主攻目标：将 `services/loop_test_service.py` 中的 `self._ctrl` 全部替换为显式构造注入，并在第一个带副作用的 service 上验证“状态注入 + 协作者注入 + 副作用回调注入”三类模式可复用。
- 实际完成：
  - `services/loop_test_service.py` 已改为 keyword-only 构造注入，不再持有 `ctrl`；当前依赖为 `sim_state`、`flow_mgr`、`get_physics()`、`get_loop_test_state()`、`set_loop_test_state()`、`append_assessment_event()`、`exit_loop_test_mode()`。
  - `loop_test_state` 因会在 `reset_loop_test()` 中整体替换，已改为 accessor + setter callback 注入；`set_loop_test_feedback`、`record_loop_test_result`、`mark_loop_test_completed` 三个 controller 薄转发已直接内联为对 `loop_test_state` 的状态写入。
  - `assessment_coord.append_assessment_event` 已改为 callback 注入；`flow_mgr` 改为直接注入稳定协作者引用。
  - `physics` 本轮采用 accessor callback（`get_physics()`）而非直接引用注入，以延迟求值规避 controller 初始化顺序问题；业务读取路径保持不变。
  - `app/main.py` 已仅在 `LoopTestService(...)` 构造处完成适配；`tests/**`、`ui/**`、其他 `services/**` 均保持零改动。
- 删除了哪些旧代码：
  - 删除 `LoopTestService.__init__(self, ctrl)` 与 `self._ctrl = ctrl`。
  - 删除 `loop_test_service.py` 内全部 21 处 `self._ctrl.*` 直接访问。
- 接口变化：
  - `LoopTestService` 的构造函数改为 keyword-only 显式依赖注入。
  - 公开方法签名保持不变；controller 仍通过 `self.loop_svc.xxx()` 做薄转发。
- 耦合度变化：
  - `services/loop_test_service.py` 的 `self._ctrl` 引用数 `21 -> 0`。
  - Phase 4 service 层 `self._ctrl` 总量 `331 -> 310`。
- 快照测试：PASS（`/Users/promise/opt/anaconda3/envs/power_gui/bin/python -m pytest tests/ -q`，13/13 通过）
- 回归清单：PASS（范围检查、`py_compile`、offscreen 导入冒烟、伪黑箱扫描全部通过）
- 下一轮起点：Phase 4 — Round 35：`sync_test_service.py` 显式依赖注入（继续验证 R34 的三类注入模式可横向复用）

### 第 33 轮 (2026-04-17)：Phase 4 第一轮（`phase_order_resolver.py` 显式依赖注入试点）
- 本轮唯一主攻目标：将 `services/phase_order_resolver.py` 中的 `self._ctrl` 全部替换为显式构造注入，建立 Phase 4 后续轮次复用的标准注入模式。
- 实际完成：
  - `services/phase_order_resolver.py` 已改为 keyword-only 构造注入，不再持有 `ctrl`；当前构造依赖为 `sim_state`、`get_pt_phase_orders()`、`get_g2_blackbox_order()`。
  - `sim_state` 采用直接引用注入；`pt_phase_orders` 与 `g2_blackbox_order` 因运行期可能被整体替换，改为 accessor callback 注入，避免捕获过期裸引用。
  - 公开方法 `resolve_pt_node_plot_key()`、`get_pt_phase_sequence()`、`resolve_loop_node_phase()` 的签名与调用方式保持不变，`services/_physics_measurement.py` 等现有调用链零改动。
  - `app/main.py` 与 `tests/support/stubs.py` 已同步适配新的 `PhaseOrderResolver(...)` 构造签名，均改为显式依赖传入，不再传 `self`。
  - 本轮标准模式已落地：**默认使用构造注入；稳定状态对象可直接注入；可变叶子对象使用 accessor callback；禁止伪 controller 替身。**
- 删除了哪些旧代码：
  - 删除 `PhaseOrderResolver.__init__(self, ctrl)` 与 `self._ctrl = ctrl`。
  - 删除 `phase_order_resolver.py` 内全部 8 处 `self._ctrl.*` 直接访问。
- 接口变化：
  - `PhaseOrderResolver` 的构造函数改为 keyword-only 显式依赖注入。
  - 3 个公开方法的方法名与参数签名保持不变；外部仍通过 `ctrl.phase_resolver.xxx()` 调用。
- 耦合度变化：
  - `services/phase_order_resolver.py` 的 `self._ctrl` 引用数 `8 -> 0`。
  - Phase 4 service 层 `self._ctrl` 总量 `339 -> 331`。
- 快照测试：PASS（`/Users/promise/opt/anaconda3/envs/power_gui/bin/python -m pytest tests/ -q`，13/13 通过）
- 回归清单：PASS（范围检查、`py_compile`、offscreen 导入冒烟、伪黑箱扫描全部通过）
- 下一轮起点：Phase 4 — Round 34：`loop_test_service.py` 显式依赖注入（验证状态 + 协作者 + 副作用回调三类注入可复用）

### 第 32 轮 (2026-04-16)：Phase 3 收口（方案 B + TestPanel 瘦身 + `_dialogs` 外提）
- 本轮唯一主攻目标：正式拍板保留 `WidgetBuilderMixin` 作为“纯 UI 宿主构造层”例外，同时完成 `ui/test_panel.py` 二次瘦身与 `ui/widgets/step_panels/_dialogs/` 子包外提，关闭 Phase 3。
- 实际完成：
  - `MAINTENANCE_CHECKLIST.md` 已按方案 B 修订：§4 完成标准改为“业务层面 UI 不再使用 Mixin 多重继承，但允许至多 1 个纯 UI 宿主构造层 Mixin”；新增 §5.2 守门扫描与 §7.5 例外条款。
  - `ui/test_panel.py` 已从 `677` 行降到 `478` 行；顶部栏、步骤点、滚动骨架、状态区、底部按钮条、`tp_dot_style`、`refresh_tp_gen_refs`、`refresh_tp_bottom` 与步骤动作查表分发均已迁入 `ui/widgets/step_panels/_panel_builders.py`。
  - `ui/widgets/step_panels/_dialogs/` 子包已落地，4 个对话框函数已从 `_panel_builders.py` 迁出：`show_assessment_result_dialog`、`show_random_fault_identification_dialog`、`show_blackbox_required_dialog`、`show_blackbox_dialog`。
  - `ui/widgets/step_panels/_panel_builders.py` 已瘦身至 `347` 行，只保留 builders / shared helpers / refresh helpers / `STEP_ACTION_TABLE` / `dispatch_step_action`。
  - `WidgetBuilderMixin` 本体、主窗口装配、controller、5 个 Step 子面板、各 Tab 与服务层文件均保持零改动。
- 删除了哪些旧代码：
  - 删除 `_panel_builders.py` 内原有 4 个对话框函数定义。
  - 删除 `ui/test_panel.py` 内本地 `_tp_dot_style`、`_refresh_tp_gen_refs`、`_refresh_tp_bottom` 与长 if/elif 步骤动作分发链。
- 接口变化：
  - 无新增公开接口；`TestPanelAPI` 签名保持不变。
  - `ui/test_panel.py` 中的对话框入口函数身份保持不变，只改为薄 wrapper 转调 `_dialogs` 子包。
- 耦合度变化：
  - `ui/test_panel.py` 继续从“协调器 + 少量 chrome 构建”收敛为更纯的协调器。
  - `_panel_builders.py` 不再承担对话框职责；对话框 import 链现在只由 `ui/test_panel.py` 直连 `_dialogs/`，符合协调器持有与派发规则。
  - Phase 3 结束时仓库仅剩 1 个 Mixin：`WidgetBuilderMixin`，并已被例外条款与守门扫描锁定边界。
- 快照测试：PASS（`/Users/promise/opt/anaconda3/envs/power_gui/bin/python -m pytest tests/ -q`，13/13 通过）
- 回归清单：PASS（结构扫描、`py_compile`、offscreen 导入冒烟全部通过；手动 GUI 冒烟已由用户确认完成）
- 下一轮起点：Phase 4 — Round 33：`phase_order_resolver.py` 显式依赖注入试点，建立 Phase 4 标准模式（详见 §10）

### 第 31 轮 (2026-04-16)：Phase 3-9（TestPanelWidget 步骤子面板解构）
- 本轮唯一主攻目标：按 Step1~5 将 `TestPanelWidget` 的 build + refresh 继续外提为独立 `QGroupBox` 子面板，保留 `ui/test_panel.py` 作为协调器，不改服务层、不改主窗口装配。
- 实际完成：
  - 新增 `ui/widgets/step_panels/` 包及 7 个文件：`__init__.py`、`_panel_builders.py`、`loop_test_panel.py`、`pt_voltage_check_panel.py`、`pt_phase_check_panel.py`、`pt_exam_panel.py`、`sync_test_panel.py`。
  - `ui/test_panel.py` 已瘦身为 `677` 行协调器组件，仅保留测试模式生命周期、顶部栏/步骤点/底部操作条、step 分发、共享状态刷新与 assessment/random-fault/blackbox 对话框薄包装。
  - `_build_step1~5`、`_refresh_tp_step1~5`、`_on_connect_psm` / `_on_disconnect_psm` / `_on_record_psm`、`_tp_s2_record`、以及 `_make_*` / `_tone_from_color` 这组共享构建方法已全部从 `ui/test_panel.py` 中移除。
  - 5 个 Step 面板均改为只通过 `TestPanelAPI + 构造注入回调` 协作，子面板内 `self.ctrl`、service 穿透与 `parent()/window()` 反向寻址均为 0 命中。
  - `_GenWiringWidget` / `_PTWiringWidget` 继续保留在 `ui/widgets/`，黑盒对话框与 wiring widget 交互通过 `_panel_builders.py` 的模块级 helper 复用，未改类名、未改构造签名、未改绘制逻辑。
- 删除了哪些旧代码：
  - 删除 `ui/test_panel.py` 中 Step1~5 的原地构建与刷新实现。
  - 删除 `ui/test_panel.py` 中原有的组装辅助方法族（`_make_grp` / `_make_btn` / `_make_step_list` / `_make_gen_block` / `_make_gen_fap_block` 等）。
- 接口变化：
  - `TestPanelAPI` 签名未变；Round 30 既有主窗口装配与 controller 薄转发全部复用。
  - 新增 5 个子面板统一对外接口：`refresh(rs, step)` / `reset()` / `on_enter()`。
- 耦合度变化：
  - `ui/test_panel.py` 行数 `2232 -> 677`。
  - `TestPanelWidget` 从“大而全单文件”收敛为“协调器 + 5 个 Step 子面板 + 1 个共享构建器”。
  - 仓库中 `Mixin` 只剩 `WidgetBuilderMixin` 1 个，符合 Phase 3 收尾目标。
- 快照测试：PASS（`/Users/promise/opt/anaconda3/envs/power_gui/bin/python -m pytest tests/ -q`，13/13 通过）
- 回归清单：PASS（`py_compile`、`offscreen` 导入冒烟、G1–G13 结构/扫描硬门全部通过；人工 GUI 冒烟已由用户确认完成，覆盖启动 → 进入测试模式 → Step1~5 推进/完成/重置 → admin 跳步 → 黑盒必修门禁 → 成绩单 → 退出并重入）
- R31 验收审计结论：代码/自动化/结构审计全部通过；手动 GUI 冒烟由用户声明完成；最终判定 `第 31 轮可视为完成`。
- 下一轮起点：Phase 3 收口 R32 — ①Mixin 方案 A/B 决策；②`ui/test_panel.py` 677 → ≤ 500（抽顶部栏/步骤点/底部按钮构建到 `_panel_builders.py`）；③`_panel_builders.py` 770 行拆出 `_dialogs` 子模块。完成后进入 Phase 4。

### 第 30 轮 (2026-04-16)：Phase 3-8（TestPanelWidget 骨架拆分 + Wiring Widget 外提）
- 本轮唯一主攻目标：只落地方案 A，将 `TestPanelMixin` 迁移为单体 `TestPanelWidget`，并先把 `_GenWiringWidget` / `_PTWiringWidget` 外提到 `ui/widgets/`；**明确禁止启动 Step1~5 子面板拆分**。
- 实际完成：
  - `ui/widgets/gen_wiring_widget.py` 与 `ui/widgets/pt_wiring_widget.py` 已新增，`_GenWiringWidget` / `_PTWiringWidget` 原样外提；`ui/test_panel.py` 仅保留 import 与 3 处实例化点。
  - `ui/test_panel.py` 已删除 `TestPanelMixin`，新增 `TestPanelAPI(Protocol)` 与 `TestPanelWidget(QWidget)`；原 `_setup_test_panel`、`_render_test_panel`、`_refresh_tp_*`、`_on_tp_*`、管理员/黑盒/考核弹窗逻辑全部迁入组件内部。
  - `ui/main_window.py` 已从基类列表中移除 `TestPanelMixin`，当前主窗口只保留 `WidgetBuilderMixin + QMainWindow`；`render_visuals()` 中原 `self._render_test_panel(p)` 已收口为 `self._test_panel_widget.render(p)`。
  - 主窗口已通过 `enter_test_mode()` / `exit_test_mode()`、`test_panel` property 以及 `on_show_test_panel` / `on_set_current_tab` / `on_set_step_tabs_visible` / `on_toggle_multimeter` / `on_force_multimeter_off` / `on_connect_phase_seq_meter` / `on_disconnect_phase_seq_meter` / `get_phase_seq_meter_sequence` 八个构造期回调，保住旧调用面与宿主 UI 协调。
  - `ui/tabs/_step_style.py` 已新增 `apply_badge_tone(widget, tone)`，`TestPanelWidget` 不再依赖 `WidgetBuilderMixin` 的宿主样式方法；原 `self._set_props` / `self._apply_button_tone` / `self._apply_badge_tone` 已统一切到 `_step_style` 模块级 helper。
  - `app/main.py` 已补齐本轮所需 Controller 薄转发，包括管理员捷径、故障推进门禁、assessment 事件流、blackbox 运行态、PT 电压/相序完成度、相序记录、硬件开关量等接口，`ui/test_panel.py` 内对 `flow_mgr` / `loop_svc` / `pt_voltage_svc` / `pt_phase_svc` / `pt_exam_svc` / `sync_svc` / `assessment_coord` / `fault_mgr` / `blackbox_handler` / `hw` 的直接穿透均已收口为 `self._api.xxx`。
- 删除了哪些旧代码：
  - 删除 `ui/test_panel.py` 中整套 `TestPanelMixin` 类定义。
  - 删除 `ui/test_panel.py` 内嵌的 `_GenWiringWidget` / `_PTWiringWidget` 类定义。
- 接口变化：
  - `PowerSyncUI` 的 UI Mixin 继承链从 2 个减至 1 个，仅剩 `WidgetBuilderMixin`。
  - 新增 `TestPanelAPI`，以显式接口承接原先散落在 `self.ctrl.*` 上的步骤状态、动作、考核、故障、硬件与物理层访问。
  - 保留 `PowerSyncUI.enter_test_mode()` / `exit_test_mode()` 与 `test_panel` 兼容入口，避免 `app/main.py` 与宿主装配层调用方式变化。
- 耦合度变化：
  - `ui/test_panel.py` 内部 `self.ctrl.flow_mgr` / `loop_svc` / `pt_voltage_svc` / `pt_phase_svc` / `pt_exam_svc` / `sync_svc` / `assessment_coord` / `fault_mgr` / `blackbox_handler` / `hw` 穿透访问已收敛为 0。
  - `WidgetBuilderMixin` 被明确保留在宿主构造层，不再和本轮 TestPanel 迁移耦合推进；Round 31 只继续处理 `TestPanelWidget` 自身的步骤子面板解构。
  - `ui/test_panel.py` 行数已由 `2423` 降到 `2222`；主风险仍在，但已经从“宿主大 Mixin”变成“单组件大文件”，可在下一轮继续按 Step1~5 精细下沉。
- 快照测试：PASS（`/Users/promise/opt/anaconda3/envs/power_gui/bin/python -m pytest tests/ -q`，13/13 通过）
- 回归清单：PARTIAL（自动化 grep / `py_compile` / `pytest` 全通过；真实 GUI 全流程冒烟待补，尤其要覆盖进入测试模式、Step 1~5 进退、管理员模式、随机故障识别弹窗与黑盒修复对话框）
- 下一轮起点：Phase 3 — Round 31：`TestPanelWidget` 步骤子面板解构（继续下沉 `_build_step1~5` 与 `_refresh_tp_step1~5`，目标把 `ui/test_panel.py` 压到可维护规模）

### 第 29 轮 (2026-04-15)：Phase 3-7（WidgetBuilderMixin / TestPanelMixin 组件化评估）
- 本轮唯一主攻目标：对 `WidgetBuilderMixin` 与 `TestPanelMixin` 做数据化评估，给出 Round 30 / Round 31 的单一明确执行方案，不做源码重构。
- 实际完成：
  - 已完成 `WidgetBuilderMixin` 数据画像：文件 `776` 行，`self.ctrl.` 穿透 `12` 处；但其构建出的宿主属性面很大，至少包括 `multimeter_cb`、`bus_status_lbl`、`bus_reference_lbl`、`arbitrator_lbl`、`relay_lbl`、`status1_lbl`、`status2_lbl`、`ctrl_layout`、`ctrl_inner` 等，并被 `ui/main_window.py`、`ui/test_panel.py`、步骤 Tab 回调广泛消费。
  - 已完成 `TestPanelMixin` 数据画像：文件 `2423` 行，`self.ctrl.` 穿透 `114` 处，实例方法 `62` 个；职责已确认横跨构建、测试模式生命周期、步骤动作分发、记录转发、管理员/故障弹窗、逐帧渲染刷新、内嵌 wiring widget 七大类。
  - 已确认 `TestPanelMixin` 的跨 Mixin / 宿主依赖面：直接依赖 `multimeter_cb`、`ctrl_container`、`tab_widget`、`phase_seq_meter`、`connect_phase_seq_meter()`、`disconnect_phase_seq_meter()`，并大量复用 `_apply_button_tone()`、`_apply_badge_tone()`、`_set_props()` 等宿主样式 helper。
  - 已完成三方案比较：单体 `TestPanelWidget`、按步骤子面板拆分、按职责分层浅组件化；最终推荐“两轮法”——Round 30 先抽 `TestPanelWidget` 骨架并外提 `_GenWiringWidget` / `_PTWiringWidget`，Round 31 再按步骤子面板继续解构。
  - 已明确结论：`WidgetBuilderMixin` 本轮后暂不做独立 QWidget 组件化，保留为宿主构造层；如后续仍需降耦，只考虑降级为 `ControlPanelBuilder / Facade` 形态，不单开一轮做激进搬迁。
- 删除了哪些旧代码：
  - 无。本轮是评估轮，只更新 `MAINTENANCE_CHECKLIST.md`。
- 接口变化：
  - 本轮无接口变更。
  - 下一轮建议新增 `TestPanelAPI`，显式收口 `sim_state` / 步骤状态快照 / 测试模式动作 / 评估事件 / 黑盒状态查询等当前散落在 `self.ctrl.*` 上的访问面。
- 耦合度变化：
  - 代码耦合本轮未变；但剩余高风险面已从“两个都要拆”收敛为“主拆 `test_panel.py`，`WidgetBuilderMixin` 先稳住宿主属性面”。
  - `ui/test_panel.py` 已被正面确认为 Phase 3 收尾主战场，`WidgetBuilderMixin` 则被降级为边界整理问题，而不是主组件化目标。
- 快照测试：PASS（`/Users/promise/opt/anaconda3/envs/power_gui/bin/python -m pytest tests/ -q`，13/13 通过）
- 回归清单：BASELINE（本轮无 `.py` 改动；记录现状基线并完成评估，不做额外 GUI 重构验收）
- 下一轮起点：Phase 3 — Round 30：`TestPanelWidget` 骨架拆分 + `_GenWiringWidget` / `_PTWiringWidget` 外提（`WidgetBuilderMixin` 暂保留）

### 第 28 轮 (2026-04-15)：Phase 3-6（WaveformTab / CircuitTab 组件化）
- 本轮唯一主攻目标：将 `WaveformTabMixin` 与 `CircuitTabMixin` 同步迁移为独立 `QWidget` 组件，收敛 `PowerSyncUI` 继承链，并保住 matplotlib 画布生命周期与外部调用兼容面。
- 实际完成：
  - `ui/tabs/waveform_tab.py` 已彻底改写：删除 `WaveformTabMixin`，新增 `WaveformTabAPI(Protocol)` 与 `WaveformTab(QWidget)`，`Figure / FigureCanvas / ax_* / line_* / phasor_*` 全部收回组件实例持有。
  - `ui/tabs/circuit_tab.py` 已彻底改写：删除 `CircuitTabMixin`，保留模块级 `_qs(...)` 供 `pt_phase_check_tab.py` 继续导入，同时新增 `CircuitTabAPI(Protocol)` 与 `CircuitTab(QWidget)`。
  - `app/main.py` 已补齐 3 个薄转发：`get_pt_blackbox_mode()`、`get_pt_phase_sequence()`、`is_assessment_mode()`；原有 `is_loop_test_complete()` 直接复用。
  - `ui/main_window.py` 已从基类列表中删除 `WaveformTabMixin` 与 `CircuitTabMixin`，当前只保留 `WidgetBuilderMixin + TestPanelMixin + QMainWindow`。
  - `render_visuals()` 中原先分散的 10 个波形/拓扑私有渲染入口已合并为 `self._waveform_tab.render(rs)` 与 `self._circuit_tab.render(p)` 两次转发。
  - 主窗口已保留 `rebuild_circuit_diagram()`、`connect_phase_seq_meter()`、`disconnect_phase_seq_meter()` 等价转发，并补了 `ax_circuit` / `canvas2` / `phase_seq_meter` 兼容属性，确保 `app/main.py`、`ui/test_panel.py`、`WidgetBuilderMixin._on_circuit_click()` 调用方式不变。
- 删除了哪些旧代码：
  - 删除 `ui/tabs/waveform_tab.py` 中整套 Mixin 实现。
  - 删除 `ui/tabs/circuit_tab.py` 中整套 Mixin 实现。
  - 删除 `ui/main_window.py` 中对 `_setup_tab_waveforms()`、`_setup_tab_circuit()`、`_init_lines()` 以及 10 个波形/拓扑私有渲染入口的直接依赖。
- 接口变化：
  - `WaveformTab` 通过 `WaveformTabAPI` 读取 `sim_state + physics`，本轮保留 `physics` property 是为了原样保留 `fixed_deg / bus_freq / bus_phase` 三处读取点，避免再人为拆出一层非必要包装后改变渲染边界。
  - `CircuitTab` 通过 `CircuitTabAPI` 读取 `sim_state`、各步骤状态切片与 4 个只读查询接口，不再暴露 `flow_mgr` / `loop_svc` / `phase_resolver` 等 service 对象。
  - `PowerSyncUI` 的 UI Mixin 继承链从 4 个减至 2 个，Phase 3 只剩 `WidgetBuilderMixin` 与 `TestPanelMixin` 待收口。
- 耦合度变化：
  - `WaveformTab` / `CircuitTab` 内部 `self.ctrl` 穿透访问已收敛为 0。
  - `PowerSyncUI` 不再直接持有 Waveform/Circuit 的 matplotlib 初始化与渲染细节，主窗口职责进一步缩回到装配与少量兼容转发。
- 快照测试：PASS（`/Users/promise/opt/anaconda3/envs/power_gui/bin/python -m pytest tests/ -q`，13/13 通过）
- 回归清单：PASS（自动化回归 13/13、`py_compile` 通过；人工 GUI 冒烟已覆盖：Tab 0 波形/相量首屏渲染正常、Tab 1 母排拓扑首屏渲染正常、resize 后两处画布重绘无残影且相量指针不跳；第一步进入/退出、第四步 PT 记录、第五步同步流程手动走读无回归）
- 下一轮起点：Phase 3 — Round 29：`WidgetBuilderMixin / TestPanelMixin` 组件化评估（最终两轮收尾）

### 第 27 轮 (2026-04-15)：Phase 3-5（PtExamTab 组件化）
- 本轮唯一主攻目标：将 `PtExamTabMixin` 改造为独立 `QWidget` 组件，延续 Phase 3 的组件化迁移范式。
- 实际完成：
  - `ui/tabs/pt_exam_tab.py` 已彻底改写：删除 `PtExamTabMixin`，新增 `PtExamTabAPI(Protocol)` 与 `PtExamTab(QWidget)`。
  - `PtExamTab` 已通过最小接口 `self._api` 与 controller 交互；同层 UI 协调通过 `on_open_circuit_tab` / `on_toggle_multimeter` 两个回调注入。
  - `app/main.py` 为第四步流程补了 3 个薄转发方法：`get_pt_exam_steps()`、`get_generator_state()`、`get_current_pt_exam_phase_match()`。
  - `ui/main_window.py` 已从基类列表中删除 `PtExamTabMixin`，改为组合装配 `self._pt_exam_tab = PtExamTab(...)`，并将渲染路径切换为 `self._pt_exam_tab.render(p)`。
  - 第四步状态文本、步骤列表和 9 组记录标签已统一切到 `ui.tabs._step_style` 的共享 helper，不再保留本地内联 `setStyleSheet(...)` 与 `_BTN` 常量。
- 删除了哪些旧代码：
  - 删除 `ui/tabs/pt_exam_tab.py` 中整套 Mixin 实现与宿主命名空间属性写入方式。
- 接口变化：
  - PtExamTab 不再隐式依赖 `PowerSyncUI` 宿主状态；改为显式依赖 `PtExamTabAPI + 2 个 UI 回调`。
  - `PowerSyncUI` 的 Mixin 继承链从 5 个 UI Mixin 减至 4 个。
- 耦合度变化：
  - `PtExamTab` 内部 `self.ctrl` / `self.pt_exam_svc` / `_get_generator_state` / `_get_current_pt_phase_match` 引用已收敛为 0。
  - Phase 3 的组件化范式已连续在前五个步骤 Tab 上复用成功。
- 快照测试：PASS（`/Users/promise/opt/anaconda3/envs/power_gui/bin/python -m pytest tests/ -q`，13/13 通过）
- 回归清单：PARTIAL（自动化回归通过；完整人工点击第四步流程仍需在可交互 GUI 环境补做）
- 下一轮起点：Phase 3 — Round 28：`WaveformTab / CircuitTab` 组件化

### 第 26 轮 (2026-04-15)：Phase 3（`test_panel.py` 宿主残留调用热修复）
- 本轮唯一主攻目标：修复 `ui/test_panel.py` 对第一步旧宿主私有方法的残留调用，并补上后续组件化轮的审计门禁。
- 实际完成：
  - `ui/test_panel.py` 中 `_on_tp_start_step()` 的 `step == 1` 分支已改为直接通过 `self.ctrl.sim_state.loop_test_mode + enter/exit_loop_test_mode()` 驱动。
  - 修复后，第一步开始/退出测试不再依赖 `PowerSyncUI._on_toggle_loop_test_mode()` 这一已被 R22 移除的宿主私有方法。
  - `MAINTENANCE_CHECKLIST.md` §5 已新增“悬空宿主调用扫描”硬门禁，要求后续组件化轮强制执行 `_on_toggle_*` 搜索。
- 删除了哪些旧代码：
  - 删除 `ui/test_panel.py` 中对 `_on_toggle_loop_test_mode()` 的宿主残留调用。
- 接口变化：
  - 无新增接口；仅将 `test_panel.py` 的第一步切换逻辑对齐到现有 controller 公开能力。
- 耦合度变化：
  - `test_panel.py` 不再依赖已迁移步骤组件对应的宿主私有方法。
  - 本轮属于 R22 验收遗漏回归的最小范围热修复，不改变当前 5-Mixin 基线。
- 快照测试：PASS（`/Users/promise/opt/anaconda3/envs/power_gui/bin/python -m pytest tests/ -q`，13/13 通过）
- 回归清单：PARTIAL（自动化回归通过；step 1-5 的完整手动 GUI 冒烟仍需在可交互 GUI 环境补做）
- 下一轮起点：Phase 3 — Round 27：`PtExamTab` 组件化

### 第 25 轮 (2026-04-15)：Phase 3-4（SyncTestTab 组件化）
- 本轮唯一主攻目标：将 `SyncTestTabMixin` 改造为独立 `QWidget` 组件，延续 Phase 3 的组件化迁移范式。
- 实际完成：
  - `ui/tabs/sync_test_tab.py` 已彻底改写：删除 `SyncTestTabMixin`，新增 `SyncTestTabAPI(Protocol)` 与 `SyncTestTab(QWidget)`。
  - `SyncTestTab` 已通过最小接口 `self._api` 与 controller 交互；同层 UI 协调通过 `on_open_waveform_tab` 回调注入。
  - `app/main.py` 为第五步流程补了 3 个薄转发方法：`get_sync_test_steps()`、`is_sync_test_complete()`、`is_gen_synced()`。
  - `ui/main_window.py` 已从基类列表中删除 `SyncTestTabMixin`，改为组合装配 `self._sync_test_tab = SyncTestTab(...)`，并将渲染路径切换为 `self._sync_test_tab.render(p)`。
  - 第五步状态文本、步骤列表和两轮记录标签已统一切到 `ui.tabs._step_style` 的共享 helper，不再保留本地内联 `setStyleSheet(...)`。
- 删除了哪些旧代码：
  - 删除 `ui/tabs/sync_test_tab.py` 中整套 Mixin 实现与宿主命名空间属性写入方式。
- 接口变化：
  - SyncTestTab 不再隐式依赖 `PowerSyncUI` 宿主状态；改为显式依赖 `SyncTestTabAPI + 1 个 UI 回调`。
  - `PowerSyncUI` 的 Mixin 继承链从 6 个 UI Mixin 减至 5 个。
- 耦合度变化：
  - `SyncTestTab` 内部 `self.ctrl` / `self.sync_svc` 引用已收敛为 0。
  - Phase 3 的组件化范式已连续在前四个步骤 Tab 上复用成功。
- 快照测试：PASS（`/Users/promise/opt/anaconda3/envs/power_gui/bin/python -m pytest tests/ -q`，13/13 通过）
- 回归清单：PARTIAL（自动化回归通过；完整人工点击第五步流程仍需在可交互 GUI 环境补做）
- 下一轮起点：Phase 3 — Round 26：`PtExamTab` 组件化

### 第 24 轮 (2026-04-15)：Phase 3-3（PtPhaseCheckTab 组件化）
- 本轮唯一主攻目标：将 `PtPhaseCheckTabMixin` 改造为独立 `QWidget` 组件，延续 Phase 3 的组件化迁移范式。
- 实际完成：
  - `ui/tabs/pt_phase_check_tab.py` 已彻底改写：删除 `PtPhaseCheckTabMixin`，新增 `PtPhaseCheckTabAPI(Protocol)` 与 `PtPhaseCheckTab(QWidget)`。
  - `PtPhaseCheckTab` 已通过最小接口 `self._api` 与 controller 交互；同层 UI 协调通过 `on_open_circuit_tab` / `on_toggle_multimeter` 两个回调注入。
  - `app/main.py` 为第三步流程补了 1 个薄转发方法：`get_pt_phase_check_steps()`。
  - `ui/main_window.py` 已从基类列表中删除 `PtPhaseCheckTabMixin`，改为组合装配 `self._pt_phase_check_tab = PtPhaseCheckTab(...)`，并将渲染路径切换为 `self._pt_phase_check_tab.render(p)`。
  - 第三步色调映射继续复用 `ui.tabs._step_style.tone_from_color()`；`meter_phase_match` 的三态颜色分支仍保留 `_qs(...)` fallback。
- 删除了哪些旧代码：
  - 删除 `ui/tabs/pt_phase_check_tab.py` 中整套 Mixin 实现与宿主命名空间属性写入方式。
- 接口变化：
  - PtPhaseCheckTab 不再隐式依赖 `PowerSyncUI` 宿主状态；改为显式依赖 `PtPhaseCheckTabAPI + 2 个 UI 回调`。
  - `PowerSyncUI` 的 Mixin 继承链从 7 个 UI Mixin 减至 6 个。
- 耦合度变化：
  - `PtPhaseCheckTab` 内部 `self.ctrl` / `self.pt_phase_svc` 引用已收敛为 0。
  - Phase 3 的组件化范式已连续在前三个步骤 Tab 上复用成功。
- 快照测试：PASS（`/Users/promise/opt/anaconda3/envs/power_gui/bin/python -m pytest tests/ -q`，13/13 通过）
- 回归清单：PARTIAL（自动化回归通过；组件级离屏实例化与 render 校验通过，完整人工点击第三步流程仍需在可交互 GUI 环境补做）
- 下一轮起点：Phase 3 — Round 25：`SyncTestTab` 组件化

### 第 23 轮 (2026-04-14)：Phase 3-2（PtVoltageCheckTab 组件化）
- 本轮唯一主攻目标：将 `PtVoltageCheckTabMixin` 改造为独立 `QWidget` 组件，延续 Phase 3 的组件化迁移范式。
- 实际完成：
  - `ui/tabs/pt_voltage_check_tab.py` 已彻底改写：删除 `PtVoltageCheckTabMixin`，新增 `PtVoltageCheckTabAPI(Protocol)` 与 `PtVoltageCheckTab(QWidget)`。
  - `PtVoltageCheckTab` 已通过最小接口 `self._api` 与 controller 交互；同层 UI 协调通过 `on_open_circuit_tab` / `on_toggle_multimeter` 两个回调注入。
  - `app/main.py` 为第二步流程补了 1 个薄转发方法：`get_pt_voltage_check_steps()`。
  - `ui/main_window.py` 已从基类列表中删除 `PtVoltageCheckTabMixin`，改为组合装配 `self._pt_voltage_check_tab = PtVoltageCheckTab(...)`，并将渲染路径切换为 `self._pt_voltage_check_tab.render(p)`。
  - 第二步颜色映射已统一复用 `ui.tabs._step_style.tone_from_color()`，未在组件内重复造一套样式辅助。
- 删除了哪些旧代码：
  - 删除 `ui/tabs/pt_voltage_check_tab.py` 中整套 Mixin 实现与宿主命名空间属性写入方式。
- 接口变化：
  - PtVoltageCheckTab 不再隐式依赖 `PowerSyncUI` 宿主状态；改为显式依赖 `PtVoltageCheckTabAPI + 2 个 UI 回调`。
  - `PowerSyncUI` 的 Mixin 继承链从 8 个 UI Mixin 减至 7 个。
- 耦合度变化：
  - `PtVoltageCheckTab` 内部 `self.ctrl` / `self.pt_voltage_svc` 引用已收敛为 0。
  - 第二阶段组件化继续沿用“独立 QWidget 自持状态 + 最小 Protocol 接口”的固定范式。
- 快照测试：PASS（`/Users/promise/opt/anaconda3/envs/power_gui/bin/python -m pytest tests/ -q`，13/13 通过）
- 回归清单：PARTIAL（自动化回归通过；组件级离屏实例化与 render 校验通过，完整人工点击第二步流程仍需在可交互 GUI 环境补做）
- 下一轮起点：Phase 3 — Round 24：`PtPhaseCheckTab` 组件化

### 第 22 轮 (2026-04-14)：Phase 3-1（LoopTestTab 组件化概念验证）
- 本轮唯一主攻目标：将 `LoopTestTabMixin` 改造为独立 `QWidget` 组件，作为 Phase 3 的范式试点。
- 实际完成：
  - `ui/tabs/loop_test_tab.py` 已彻底改写：删除 `LoopTestTabMixin`，新增 `LoopTestTabAPI(Protocol)` 与 `LoopTestTab(QWidget)`。
  - `LoopTestTab` 已通过最小接口 `self._api` 与 controller 交互；同层 UI 协调通过 `on_open_circuit_tab` / `on_toggle_multimeter` 两个回调注入。
  - `app/main.py` 为第一步流程补了 3 个薄转发方法：`get_loop_test_steps()`、`get_current_loop_phase_match()`、`is_loop_test_complete()`。
  - `ui/main_window.py` 已从基类列表中删除 `LoopTestTabMixin`，改为组合装配 `self._loop_test_tab = LoopTestTab(...)`，并将渲染路径切换为 `self._loop_test_tab.render(p)`。
  - `ui/tabs/_step_style.py` 已补充通用按钮 tone fallback 与 `tone_from_color()`，支撑独立 QWidget 复用步骤页样式辅助。
- 删除了哪些旧代码：
  - 删除 `ui/tabs/loop_test_tab.py` 中整套 Mixin 实现与宿主命名空间属性写入方式。
- 接口变化：
  - LoopTestTab 不再隐式依赖 `PowerSyncUI` 宿主状态；改为显式依赖 `LoopTestTabAPI + 2 个 UI 回调`。
  - `PowerSyncUI` 的 Mixin 继承链从 9 个 UI Mixin 减至 8 个。
- 耦合度变化：
  - `LoopTestTab` 内部 `self.ctrl` / `self.loop_svc` 引用已收敛为 0。
  - 第一阶段组件化已从“宿主共享命名空间”切换为“独立 QWidget 自持状态”模式。
- 快照测试：PASS（`/Users/promise/opt/anaconda3/envs/power_gui/bin/python -m pytest tests/ -q`，13/13 通过）
- 回归清单：PARTIAL（自动化回归通过；离屏启动级冒烟已尝试，完整人工点按流程需在可交互 GUI 环境补做）
- 下一轮起点：Phase 3 — Round 23：`PtVoltageCheckTab` 组件化

### 第 21 轮 (2026-04-14)：Phase 2-4（评分域独立快照测试）
- 本轮唯一主攻目标：为四个评分域各自建立输入/输出级别的独立快照测试，补齐 Phase 2 的最后一块安全网。
- 实际完成：
  - 新增 `tests/support/scoring_fixtures.py`，手动构造 `NORMAL_CONTEXT` / `FAULT_CONTEXT` 两套 `ScoringContext` 夹具，不依赖 `AssessmentService` 组装路径。
  - 新增 4 个评分域测试文件：`tests/test_scoring_discipline.py`、`tests/test_scoring_step_quality.py`、`tests/test_scoring_fault_diagnosis.py`、`tests/test_scoring_blackbox_efficiency.py`。
  - 为四个评分域各补 2 份 JSON 快照基线（normal / fault），共新增 8 份 `tests/snapshots/scoring_*.json`。
  - 保持整链路评分快照测试不变，新增测试只覆盖评分域纯函数输入/输出。
- 删除了哪些旧代码：
  - 删除本文件顶部遗留的 Round 21 任务提示词，恢复 checklist 作为唯一长期事实来源的入口形态。
- 接口变化：
  - 无生产代码接口变化；仅新增测试侧 `ScoringContext` 夹具工厂与 4 组评分域独立快照。
- 耦合度变化：
  - 生产代码零耦合变化；评分系统的测试颗粒度从“整链路”补齐到“整链路 + 单评分域”双层保护。
- 快照测试：PASS（`pytest tests/ -q`，13/13 通过）
- 回归清单：PASS（原 5 条 + 新 8 条快照均通过；既有 `assessment_*.json` 基线无改动）
- 下一轮起点：Phase 3 — UI 组件化（告别 Mixin），从 `LoopTestTab` 概念验证开始

### 第 20 轮 (2026-04-14)：Phase 2-3（`score_context` 改为 `ScoringContext` dataclass）
- 本轮唯一主攻目标：将 dict 型 `score_context` 升级为 `@dataclass(frozen=True) ScoringContext`，并把 4 个闭包抽成共享纯函数。
- 实际完成：
  - 在 `services/scoring/context.py` 新增 `ScoringContext`，显式收口评分阶段使用的 33 个数据字段，并补入 `step_enter_events` 这一处原先被闭包隐式捕获的隐藏依赖。
  - 在 `services/scoring/_common.py` 新增 `count_present`、`trio_completion_score`、`nine_group_completion_score`、`first_step_index` 4 个纯函数，与原闭包行为保持一致。
  - 4 个评分域模块已统一改签为 `score_xxx(ctx: ScoringContext)`，所有 `ctx["xxx"]` 访问已切换为 `ctx.xxx`。
  - `services/assessment_service.py` 中 `score_context = {...}` 已改为构造 `ScoringContext(...)`，并删除主文件内 4 个闭包定义。
- 删除了哪些旧代码：
  - 删除 `services/assessment_service.py` 中 `first_step_index`、`trio_completion_score`、`nine_group_completion_score`、`count_present` 四处本地定义。
  - 删除 dict 版 `score_context` 组装结构及其对闭包的隐式注入。
- 接口变化：
  - 评分域模块签名从 `score_xxx(ctx: dict)` 改为 `score_xxx(ctx: ScoringContext)`。
  - `ScoringContext` 只承载数据字段，不包含方法与 `Callable` 字段；闭包能力全部改由 `_common.py` 中的纯函数显式提供。
- 耦合度变化：
  - `services/assessment_service.py` 行数 `429 -> 399`
  - `services/scoring/_common.py` 行数 `46 -> 79`
  - 新增 `services/scoring/context.py` `43` 行
  - `services/scoring/discipline.py` `107` 行
  - `services/scoring/step_quality.py` `296` 行
  - `services/scoring/fault_diagnosis.py` `106` 行
  - `services/scoring/blackbox_efficiency.py` `186` 行
- 快照测试：PASS（`python -m pytest tests/ -q -p no:cacheprovider`，5/5 通过）
- 回归清单：PASS（`services/scoring/*.py` 中 `ctx["` 搜索结果为 0；`services/assessment_service.py` 中 4 个原闭包定义搜索结果为 0；`tests/snapshots/` 无改动）
- 下一轮起点：Phase 2-4（可选）— 评分域独立快照测试；或转入 Phase 3 — UI 组件化（由 Round 21 决策）

### 第 18 轮 (2026-04-13)：Phase 2-1（评分事件常量化 + AssessmentContext 建立）
- 本轮唯一主攻目标：为 `AssessmentService` 建立事件常量与 `AssessmentContext` 输入边界，切断 `build_result()` 对 ctrl 的入口依赖。
- 实际完成：
  - 在 `domain/assessment.py` 新增 `AssessmentEventType` 常量类，集中定义评分事件类型。
  - 在 `domain/assessment.py` 新增 `AssessmentContext` dataclass，并落地 `from_snapshot_and_ctrl(snapshot, ctrl)`。
  - `services/assessment_service.py` 的 `build_result()` 已改签为 `build_result(session, context)`。
  - `services/assessment_coordinator.py` 与 `tests/test_assessment_snapshot.py` 已统一通过 `AssessmentContext.from_snapshot_and_ctrl(...)` 调用评分入口。
  - 真实生产路径与快照构造路径中的事件类型读取/主要入队点已改为常量引用。
- 删除了哪些旧代码：
  - 删除 `AssessmentService.build_result()` 入口段中基于 `self._ctrl` 的 13 处兜底读取。
  - 删除 `AssessmentService.__init__(self, ctrl)` 的 ctrl 依赖，改为无参构造。
- 接口变化：
  - `AssessmentService.build_result(session)` -> `AssessmentService.build_result(session, context)`
  - `AssessmentContext` 仅封装评分入口原本依赖 ctrl 兜底读取的记录/完成态/故障修复状态，不额外扩张边界。
- 耦合度变化：
  - `services/assessment_service.py` 中 `self._ctrl` 引用数 `13 -> 0`
  - `services/assessment_service.py` 行数 `791 -> 784`
- 快照测试：PASS（`python -m pytest tests/ -q -p no:cacheprovider`，5/5 通过）
- 回归清单：PASS（评分结果与现有快照基线保持一致，`tests/snapshots/` 无改动）
- 下一轮起点：Phase 2-2 — 按评分域拆分为纯函数模块（`services/scoring/` 子包）

### 第 19 轮 (2026-04-14)：Phase 2-2（按评分域拆分为纯函数模块）
- 本轮唯一主攻目标：将 `AssessmentService` 从单体评分器收口为“组装器 + 4 个评分域纯函数模块”。
- 实际完成：
  - 新增 `services/scoring/` 子包与 5 个文件：`_common.py`、`discipline.py`、`step_quality.py`、`fault_diagnosis.py`、`blackbox_efficiency.py`
  - 建立 `make_score_item(...)` 纯函数，替代原 `add_score_item` / `add_penalty` 闭包语义
  - 已将 A/B/C/D/E/F/G/H 八段评分逻辑按评分域迁出，`build_result()` 改为顺序组装 4 个评分器返回值
  - 已删除 `AssessmentService` 中全部 `_score_*` 方法，以及 `score_context` 中闭包注入键
- 删除了哪些旧代码：
  - 删除 `services/assessment_service.py` 中 8 个 `_score_xxx` 方法
  - 删除 `build_result()` 内的 `add_score_item` / `add_penalty` 两个闭包
- 接口变化：
  - `services/scoring/discipline.py` → `score_discipline(ctx)`
  - `services/scoring/step_quality.py` → `score_step_quality(ctx)`
  - `services/scoring/fault_diagnosis.py` → `score_fault_diagnosis(ctx)`
  - `services/scoring/blackbox_efficiency.py` → `score_blackbox_efficiency(ctx)`
  - `score_context` 仍保持 dict，留待下一轮做 `ScoringContext` dataclass 化
- 耦合度变化：
  - `services/assessment_service.py` 行数 `784 -> 429`
  - `services/scoring/__init__.py` `11` 行
  - `services/scoring/_common.py` `46` 行
  - `services/scoring/discipline.py` `107` 行
  - `services/scoring/step_quality.py` `299` 行
  - `services/scoring/fault_diagnosis.py` `105` 行
  - `services/scoring/blackbox_efficiency.py` `185` 行
- 快照测试：PASS（`python -m pytest tests/ -q -p no:cacheprovider`，5/5 通过）
- 回归清单：PASS（评分结果与现有快照基线保持一致，`tests/snapshots/` 无改动）
- 下一轮起点：Phase 2-3 — ScoringContext dataclass 化

### 第 16 轮 (2026-04-13)：Phase 1 收尾（第二阶段：FlowMgr / AssessmentCoord / AssessmentService 公开化 + 剩余壳清理）
- 本轮唯一主攻目标：公开 `flow_mgr / assessment_coord / assessment_svc`，删除 Controller 中剩余的流程策略与考核生命周期转发壳
- 实际完成：
  - 将 `self._flow_mgr`、`self._assessment_coord`、`self._assessment_svc` 分别公开为 `self.flow_mgr`、`self.assessment_coord`、`self.assessment_svc`
  - UI、服务层、测试替身中的旧调用点已改为 `ctrl.<service>.method(...)`
  - `tests/support/stubs.py` 已同步 `flow_mgr` 与 `assessment_coord` 公开句柄，保留原有直接方法签名
- 删除了哪些旧代码：
  - `app/main.py` 中 `FlowModeManager` 相关 21 个纯转发壳
  - `app/main.py` 中 `AssessmentCoordinator` 相关 11 个纯转发壳
  - 本轮共清理剩余纯转发壳 32 个
- 接口变化：
  - Controller 不再承担流程策略与考核生命周期查询/命令的转发职责
  - `AssessmentService` 仅完成句柄公开化，内部实现保持不变，Phase 2 再拆
- 耦合度变化：
  - `app/main.py` 行数 `483 -> 502`
  - Controller 已完成 12 个服务句柄的公开化与壳清理，正式退回编排层
- 快照测试：PASS（`python -m pytest tests/ -v -p no:cacheprovider`，5/5 通过）
- 回归清单：PASS（按服务族逐步推进并持续回归）
- 下一轮起点：Phase 2 — 定义 `AssessmentContext` 并切断评分对 ctrl 的依赖

### 第 15 轮 (2026-04-13)：Phase 1 收尾（第一阶段：9 个服务句柄公开化 + 纯转发壳清理）
- 本轮唯一主攻目标：只处理 9 个低频/局部服务句柄，不触碰 `FlowModeManager`、`AssessmentCoordinator`、`AssessmentService`
- 实际完成：
  - 将 `hw`、`phase_resolver`、`blackbox_handler`、`fault_mgr`、`loop_svc`、`pt_voltage_svc`、`pt_phase_svc`、`pt_exam_svc`、`sync_svc` 公开化
  - UI 与跨服务调用点已改为 `ctrl.<service>.method(...)`
  - `tests/support/stubs.py` 已补齐本轮涉及的公开服务句柄，保留原有直接方法签名
  - `FlowMgr / AssessmentCoord / AssessmentService` 零改动，留待下一轮
- 删除了哪些旧代码：
  - `app/main.py` 中上述 9 组服务对应的 34 个纯转发壳
  - 其中包含硬件动作、相序解析、黑盒修复、故障门禁、Loop/PT/Sync 五步测试查询壳
- 接口变化：
  - Controller 不再对这 9 组能力提供旧的 `ctrl.method(...)` 壳入口
  - 外部统一改为 `ctrl.<service>.method(...)`
- 耦合度变化：
  - `app/main.py` 行数 `725 -> 483`
  - Controller 主文件已低于 500 行，四类已迁出能力的旧壳层基本清空
- 快照测试：PASS（按批次持续执行 `python -m pytest tests/ -v -p no:cacheprovider`，最终 5/5 通过）
- 回归清单：PASS（每完成一组服务句柄都跑一次快照）
- 下一轮起点：Phase 1 收尾（第二阶段）— 公开 `FlowMgr` / `AssessmentCoord` 并删除剩余壳层

### 第 14 轮 (2026-04-10)：Phase 1 第五步（拆出 HardwareActions）
- 本轮唯一主攻目标：将发电机启停、断路器合分、即时同期三类硬件动作从 Controller 中独立出去
- 实际完成：
  - 新增 `services/hardware_actions.py`
  - 将 `get_preclose_flow_blockers`、`instant_sync`、`toggle_engine`、`toggle_breaker` 及 4 个私有辅助方法迁入独立硬件动作模块
  - `PowerSyncController` 新增 `self._hw = HardwareActions(self)`
  - `app/main.py` 中 4 个对外硬件动作方法已改为转发壳，外部调用者零改动
  - 明确保留 `toggle_pause()` 在 Controller，不把直接操作 UI 控件的方法带入服务模块
- 删除了哪些旧代码：
  - `app/main.py` 中直接实现的合闸前流程检查、即时同期、发电机启停、断路器合分逻辑
  - `app/main.py` 中私有 helper：`_should_enforce_pt_exam_before_close`、`_should_limit_close_to_selected_pt_target`、`_on_engine_blocked`、`_on_breaker_blocked`
- 接口变化：
  - 新增 `HardwareActions(ctrl)`，本轮允许持有 ctrl
  - Controller 对外仍通过 `get_preclose_flow_blockers()`、`instant_sync()`、`toggle_engine()`、`toggle_breaker()` 提供原签名接口
- 耦合度变化：
  - `app/main.py` 行数 `849 -> 725`
  - 硬件动作实现细节已从 Controller 主文件移出
- 快照测试：PASS（`python -m pytest tests/ -v -p no:cacheprovider`）
- 回归清单：PASS（以快照测试为本轮核心回归）
- 下一轮起点：Phase 1 收尾 — 删除 Controller 中已迁出的纯转发壳层

### 第 13 轮 (2026-04-10)：Phase 1 第四步（拆出 PhaseOrderResolver）
- 本轮唯一主攻目标：将 PT 节点解析、相序判定、回路节点相位解析从 Controller 中独立出去
- 实际完成：
  - 新增 `services/phase_order_resolver.py`
  - 将 `resolve_pt_node_plot_key`、`get_pt_phase_sequence`、`resolve_loop_node_phase` 迁入独立解析器
  - `PowerSyncController` 新增 `self._phase_resolver = PhaseOrderResolver(self)`
  - `app/main.py` 中原有 3 个相序解析方法已改为转发壳，外部调用者零改动
  - `tests/support/stubs.py` 新增 `self._phase_resolver = PhaseOrderResolver(self)`，并将 3 个旧手工实现替换为转发壳
- 删除了哪些旧代码：
  - `app/main.py` 中直接实现的 PT 节点解析、相序判定、回路节点相位解析逻辑
  - `tests/support/stubs.py` 中对应 3 个方法的手工实现
- 接口变化：
  - 新增 `PhaseOrderResolver(ctrl)`，本轮允许持有 ctrl
  - Controller 与 ControllerStub 对外方法签名保持不变，仍通过 `resolve_xxx()` / `get_pt_phase_sequence()` 调用
- 耦合度变化：
  - `app/main.py` 行数 `910 -> 849`
  - 相序解析实现细节已从 Controller 主文件移出
- 快照测试：PASS（`python -m pytest tests/ -v -p no:cacheprovider`）
- 回归清单：PASS（以快照测试为本轮核心回归）
- 下一轮起点：Phase 1 — 拆出 `HardwareActions`

### 第 12 轮 (2026-04-10)：Phase 1 第三步（拆出 BlackboxRepairHandler）
- 本轮唯一主攻目标：将黑盒运行态构造、黑盒修复执行、黑盒到相序同步从 Controller 中独立出去
- 实际完成：
  - 新增 `services/blackbox_repair_handler.py`
  - 将 `BlackboxRepairOutcome`、`get_blackbox_runtime_state`、`apply_blackbox_repair_attempt`、`_compute_pt1_net_order`、`sync_pt1_blackbox_to_phase_orders`、`sync_g2_blackbox_to_phase_orders` 迁入独立处理器
  - `PowerSyncController` 新增 `self._blackbox_handler = BlackboxRepairHandler(self)`
  - `app/main.py` 中对外暴露的 4 个黑盒相关方法已改为转发壳，`set_g2_terminal_fault()` 继续通过 Controller 转发调用同步方法
- 删除了哪些旧代码：
  - `app/main.py` 顶部内嵌的 `BlackboxRepairOutcome` dataclass
  - `app/main.py` 中直接实现的黑盒修复与黑盒到相序同步逻辑
  - `app/main.py` 中私有 helper `_compute_pt1_net_order`
- 接口变化：
  - 新增 `BlackboxRepairHandler(ctrl)`，本轮允许持有 ctrl
  - Controller 对外方法签名保持不变，外部仍通过 `ctrl.xxx()` 调用
- 耦合度变化：
  - `app/main.py` 行数 `1076 -> 910`
  - 黑盒修复实现细节已从 Controller 主文件移出
- 快照测试：PASS（`python -m pytest tests/ -v -p no:cacheprovider`）
- 回归清单：PASS（以快照测试为本轮核心回归）
- 下一轮起点：Phase 1 — 拆出 `PhaseOrderResolver`

### 第 11 轮 (2026-04-10)：Phase 1 第二步（拆出 AssessmentCoordinator）
- 本轮唯一主攻目标：将考核会话生命周期与测试进度门禁从 Controller 中独立出去
- 实际完成：
  - 新增 `services/assessment_coordinator.py`
  - 将 `StepProgressSnapshot` 与 11 个考核会话/门禁方法迁入独立协调器
  - `PowerSyncController` 新增 `self._assessment_coord = AssessmentCoordinator(self)`
  - `app/main.py` 中原有 11 个方法已改为转发壳，外部调用者零改动
  - `self.assessment_session` 字段仍保留在 Controller 上，继续作为真值源
- 删除了哪些旧代码：
  - `app/main.py` 中内嵌的 `StepProgressSnapshot` dataclass
  - `app/main.py` 中直接实现的考核会话生命周期与测试进度门禁逻辑
- 接口变化：
  - 新增 `AssessmentCoordinator(ctrl)`，本轮允许持有 ctrl
  - Controller 对外方法签名保持不变，仍通过 `ctrl.xxx()` 调用
- 耦合度变化：
  - `app/main.py` 行数 `1276 -> 1076`
  - 考核会话实现细节已从 Controller 主文件移出
- 快照测试：PASS（`python -m pytest tests/ -v -p no:cacheprovider`）
- 回归清单：PASS（以快照测试为本轮核心回归）
- 下一轮起点：Phase 1 — 拆出 `BlackboxRepairHandler`

### 第 10 轮 (2026-04-09)：Phase 1 第一步（拆出 FlowModeManager）
- 本轮唯一主攻目标：将 flow mode 策略定义与查询从 Controller 中独立出去
- 实际完成：
  - 新增 `services/flow_mode_manager.py`
  - 将 `FlowModePolicy`、`FLOW_MODE_POLICIES`、flow mode 查询方法移入独立模块
  - `PowerSyncController` 改为持有 `self._flow_mgr`
  - 保留 Controller 上的同名转发方法，外部调用者零改动
  - `test_flow_mode` 改为通过 Controller 属性代理到 `FlowModeManager`
  - `tests/support/stubs.py` 已补齐 `FlowModeManager` 替身接入
- 删除了哪些旧代码：
  - `app/main.py` 中内嵌的 `FlowModePolicy`
  - `app/main.py` 中内嵌的 `FLOW_MODE_POLICIES`
  - `app/main.py` 中直接实现的 flow mode 策略查询逻辑
- 接口变化：
  - 新增 `FlowModeManager(test_flow_mode: str)` 纯查询模块
  - `PowerSyncController.test_flow_mode` 改为代理属性，对外接口不变
- 耦合度变化：
  - flow mode 策略定义已从 Controller 主文件剥离
  - 外部 UI / Service 调用点零改动
  - `app/main.py` 行数 `1340 -> 1276`
- 快照测试：PASS（`python -m pytest tests/ -v -p no:cacheprovider`）
- 回归清单：PASS（以快照测试为本轮核心回归）
- 下一轮起点：Phase 1 — 拆出 `AssessmentCoordinator`

### 第 9 轮 (2026-04-09)：Phase 0 收尾（Mixin 属性交叉引用扫描）
- 本轮唯一主攻目标：输出 UI Mixin 属性交叉引用扫描，闭环 Phase 0
- 实际完成：
  - 新增 UI Mixin 依赖扫描文档（历史产物；Tab 组件化完成后已移除）
  - 扫描 `main_window + 9 个 Mixin` 的显式 `self.xxx` 创建属性
  - 输出共享属性交叉引用表
  - 统计各 Mixin 的 `self.ctrl` 使用次数
  - 给出 Phase 3 的迁移顺序与拆分风险点
- 删除了哪些旧代码：无（本轮只做静态分析文档）
- 接口变化：无业务接口变化
- 耦合度变化：无代码耦合变化；已形成 UI 继承链依赖基线，后续可按图拆分
- 快照测试：未执行（本轮未修改业务代码）
- 回归清单：未执行（本轮未修改业务代码）
- 下一轮起点：Phase 1 — 拆出 `FlowModeManager`

### 第 8 轮 (2026-04-09)：Phase 0 安全网建设（快照测试）
- 本轮唯一主攻目标：为 PhysicsEngine 和 AssessmentService 建立最小回归安全网
- 实际完成：
  - 新增 `tests/support/stubs.py`，构造无 UI 的 `ControllerStub`
  - 新增 `tests/test_physics_snapshot.py`
  - 新增 `tests/test_assessment_snapshot.py`
  - 生成 4 份快照基线：`physics_normal.json`、`physics_fault_E01.json`、`assessment_normal.json`、`assessment_fault_random.json`
- 删除了哪些旧代码：无（本轮只新增测试，不动业务逻辑）
- 接口变化：无业务接口变化；仅新增测试侧替身与快照序列化工具
- 耦合度变化：
  - 已验证 `PhysicsEngine` 可脱离 PyQt5/UI 实例化并运行
  - 已验证 `AssessmentService.build_result()` 可在最小 ctrl 替身下独立运行
- 快照测试：PASS（`python -m pytest tests/`）
- 回归清单：PASS（基于快照与测试入口验证）
- 下一轮起点：Phase 0 收尾扫描完成后进入 Phase 1

### 早期摘要（第 1 - 4 轮）
- 已完成：`C1`、`C2（第一步）`、`H1`、`H2`
- 关键结果：
  - 切断 `physics -> ui` 事故弹窗直连
  - 拆出 `FaultManager`
  - `_tick()` 拆成物理 / 渲染两个异常边界
  - `E01/E02/E03` 事故弹窗收口为统一入口，并删除 `_legacy` 死代码

### 第 5 轮：控制器与 UI 解耦
- 本轮目标：去掉控制器对具体 UI 控件的直接写入
- 实际完成：`H3`
- 删除了哪些旧代码：E04 中对 PT3 比率控件的直接写入
- 当前阻塞：评分主函数仍过长
- 下一轮起点：修 `H4`

### 第 6 轮：评分主函数第一阶段拆分
- 本轮目标：拆 `build_result()` 巨石函数
- 实际完成：`H4（第一步）`
- 删除了哪些旧代码：无功能删除，完成 helper 化收口
- 当前阻塞：评分系统仍未按文件拆开
- 下一轮起点：修 `H5`

### 第 7 轮：仲裁时间步长修复
- 本轮目标：去掉死母线倒计时中的固定 `0.033`
- 实际完成：`H5`
- 删除了哪些旧代码：移除死母线逻辑里的固定帧时间假设
- 当前阻塞：主文件体积依旧过大
- 下一轮起点：Phase 0 安全网建设

---

## 10. 下一轮默认起点 — 后续收口路线图

### 最新默认起点（R49-Round3）

- 主目标：启动 `ui/tabs/waveform_tab.py` 结构审查与职责拆分预研，在不改波形绘制、同期判据、指标卡视觉和宿主调用方式的前提下，先梳理“图表初始化 / 波形渲染 / 同期表渲染 / 仪表盘状态”四类边界，为后续物理拆分做准备。
- 优先顺序：
  - 先输出 `waveform_tab.py` 的职责地图，明确哪些函数属于 figure/canvas 初始化，哪些属于 render path，哪些属于 badge / metric card / criteria widget 构造。
  - 再识别最适合先拆出的纯 helper 区块，优先考虑 `_make_*` 组件工厂、轴样式助手和同步判据格式化函数。
  - 预研轮只做边界梳理与最小可拆分方案，不顺手改视觉、不顺手改 physics 数据来源。
- 明确后移：
  - README 的 `ui/styles.py` 旧路径文案单独作为文档清理项处理，不与 `waveform_tab.py` 结构轮次混合。
  - `ui/main_window.py` 与 `_panel_builders.py` 的结构专项继续后移，作为 `waveform_tab.py` 之后的候选轮次。

### 总体目标

Phase 4 的目标不是"继续 UI 组件化"，而是：

- 把各 service 内部的 `self._ctrl` / `self.ctrl` 依赖，逐步改成**显式构造注入**
- 让 service 的输入边界变清晰：状态依赖、协作者依赖、副作用回调依赖
- 最后在依赖边界已经显式化的前提下，引入 `ControllerSignals(QObject)`，把部分 `render_visuals` / UI 更新路径从 `_tick` 轮询迁移到 signal 驱动

核心原则：

1. **先建立标准注入模式，再逐轮复制**
2. **每轮只打一个主战场**
3. **先小后大，先纯 service 后编排器，再汇聚器**
4. **Signal/Slot 放到所有 service 显式依赖化之后再做**
5. **R43 之后不再碰"service 还依赖 controller 黑箱"这种旧模式**

### 注入模式标准（Phase 4 全程适用）

1. **默认风格：构造注入**
   - 多方法 service（`loop_test_service.py` 等）一律用构造注入
   - 极小无状态 helper（如 `phase_order_resolver.py`）也使用轻量构造注入，保持范式一致
2. **可变叶子对象：注入容器或 accessor，不注入裸列表**
   - 如 `g2_blackbox_order`（会被整体替换）→ 注入持有它的容器引用，或 accessor callback（`get_g2_blackbox_order()`）
   - 如 `sim_state`（只被原地修改）→ 可直接注入引用
3. **禁止把旧 `ctrl` 换名为别的"大黑箱对象"**
   - 不允许创建 `ServiceDeps` / `ServiceContext` 之类的伪 controller 替身
   - 依赖聚合对象仅在参数 > 5 时允许，且必须字段明确、冻结
4. **`app/main.py` 构造区释放阀**
   - 如果 `PowerSyncController.__init__` 中 service 构造区超过 50 行，允许提取为 `_build_services()` 私有工厂方法
   - 暂不引入独立 factory 类/模块

### 通用实施规则

**每轮只允许改：**
- 目标 service 文件
- `app/main.py` 中该 service 的构造处
- `MAINTENANCE_CHECKLIST.md`

**默认禁止：**
- `ui/**`
- `services/**` 中与本轮无关的文件
- `domain/**`、`adapters/**`、`tests/**`

**每轮硬门统一保留：**
- `pytest tests/ -q` 必须仍是 `13 passed`
- 目标 service 中 `self._ctrl` / `self.ctrl` 的引用数 = 0
- 不允许把旧 `ctrl` 直接换名为别的"大黑箱对象"
- Checklist 必须记录"本轮建立/复用的注入模式"

### 轮次计划

| 轮次 | 目标文件 | `self._ctrl` 数 | 行数 | 定位 |
|---|---|---:|---:|---|
| R33 | `phase_order_resolver.py` | 8 | 61 | 模式建立（最小验证，已完成） |
| R34 | `loop_test_service.py` | 21 | 216 | 小型 service + 首次副作用注入（已完成） |
| R35 | `sync_test_service.py` | 27 | 224 | 小型 service（验证模式可复用，已完成） |
| R36 | `pt_voltage_check_service.py` | 24 | 291 | 中型 service（已完成） |
| R37 | `blackbox_repair_handler.py` | 36 | 214 | 编排类 service 试点（已完成） |
| R38 | `fault_manager.py` | 40 | 150 | 故障管理（已完成） |
| R39 | `hardware_actions.py` | 35 | 149 | 动作编排器（已完成） |
| R40 | `pt_phase_check_service.py` | 38 | 346 | 大型 step service（已完成） |
| R41 | `pt_exam_service.py` | 49 | 386 | 大型 step service（已完成） |
| R42 | `assessment_coordinator.py` | 61 | 250 | 最重汇聚器（Phase 4 service 收口，已完成） |
| R43 | `ControllerSignals` + render 迁移 | — | — | 已完成（阶段 1 + 阶段 2 试点；阶段 3 未执行） |
| R44 | `physics_engine.py` + `_physics_*.py` | 31 | — | 已完成（physics 层 `self.ctrl` 清理，Phase 4 真正收官） |
| R45 | `ui/panels/control_panel.py` + `ui/widgets/control_panel/*` | 12 + 3 别名直连 | 776 | 已完成（Phase 3 收尾，组件化与瘦身） |
| R46 | `domain/phase_order_state.py` + `app/main.py` + `services/blackbox_repair_handler.py` | 状态真值源收口 + `_BoolProxy` 清理 | — | 已完成 |
| R47 | `app/main.py` + `domain/assessment.py` + 3 个白名单 service | cleanup round | — | 已完成（死 import 清理 + `domain/` 类型标注补齐 + 历史注释整理） |

### R33：模式建立（最小验证，已完成）

**目标文件**：`services/phase_order_resolver.py`（8 处 `self._ctrl`，61 行）

**任务**：
- 把 `self._ctrl` 拆成显式构造注入（`sim_state`、`get_pt_phase_orders`、`get_g2_blackbox_order`）
- 在 `app/main.py` 构造处适配
- 在 Checklist 记录"Phase 4 标准注入模式"

**结果**：
- 已完成；`phase_order_resolver.py` 当前 `self._ctrl` = 0
- 标准模式已确认：
  1. 默认使用 keyword-only 构造注入
  2. 稳定状态对象（如 `sim_state`）可直接注入引用
  3. 可变叶子对象（如会整体替换的 `dict/list`）使用 accessor callback
  4. 禁止引入 `Deps/Context/Facade` 伪 controller 替身
- 本轮回归：`pytest 13 passed`

### R34–R36：小 → 中型 step service

按 R33 建立的模式逐个改造。从 R34 开始正式验证三类注入（状态 + 协作者 + 副作用回调）能否稳定复用。

**R34 结果**：
- 已完成；`loop_test_service.py` 当前 `self._ctrl` = 0
- 已验证三类依赖拆分可在真实带副作用的 service 中共存：
  1. 状态注入：`sim_state`
  2. 稳定协作者注入：`flow_mgr`
  3. accessor / setter 注入：`loop_test_state`
  4. 副作用回调注入：`append_assessment_event()`、`exit_loop_test_mode()`
- 构造顺序存在约束时，稳定对象允许使用 accessor callback 延迟求值；R34 中 `physics` 即按此规则处理
- 本轮回归：`pytest 13 passed`

**R35 结果**：
- 已完成；`sync_test_service.py` 当前 `self._ctrl` = 0
- 三类依赖拆分已在第二个带状态门禁的 service 中复用成功：
  1. 状态注入：`sim_state`
  2. 稳定协作者注入：`flow_mgr`、`fault_mgr`
  3. accessor / setter 注入：`sync_test_state`
  4. query callback 注入：四个前序步骤完成度检查
- 受初始化顺序约束的稳定对象继续使用 accessor callback；R35 中 `physics` 仍按 `get_physics()` 处理
- 本轮回归：`pytest 13 passed`

**R36 结果**：
- 已完成；`pt_voltage_check_service.py` 当前 `self._ctrl` = 0
- 在第一个中型 step service 上继续验证了 R35 已稳定下来的显式注入组合：
  1. 状态注入：`sim_state`
  2. 稳定协作者注入：`flow_mgr`
  3. accessor / setter 注入：`pt_voltage_check_state`
  4. query callback：`is_loop_test_complete()`
  5. 行为回调：`append_assessment_event()`
- 受初始化顺序约束的稳定对象继续使用 accessor callback；R36 中 `physics` 仍按 `get_physics()` 处理
- 本轮回归：`pytest 13 passed`

**R37 结果**：
- 已完成；`blackbox_repair_handler.py` 当前 `self._ctrl` = 0
- Phase 4 首个编排类 service 已验证“稳定状态 + 稳定协作者 + accessor/setter + 行为回调”的高参数量组合仍然可控：
  1. 稳定状态注入：`sim_state`
  2. 稳定协作者注入：`flow_mgr`
  3. accessor 回调：`get_fault_mgr()`、`get_pt_phase_orders()`
  4. accessor / setter：4 组 blackbox order 列表
  5. 行为回调：`append_assessment_event()`
- 初始化顺序晚于 handler 的稳定对象继续使用 accessor callback；R37 中 `fault_mgr` 因此改为 `get_fault_mgr()`
- 本轮回归：`pytest 13 passed`

### R38–R39：编排器 / 管理器 / 动作层

**R38 结果**：
- 已完成；`fault_manager.py` 当前 `self._ctrl` = 0
- 在故障管理器上验证了“直接注入 + 行为回调 + setter 回调 + accessor 回调 + 4 对 accessor/setter + 内联 reset”组合可控：
  1. 直接注入：`sim_state`、`blackbox_handler`
  2. 行为回调：`append_assessment_event()`、`request_pt_ratio_row_update()`
  3. setter 回调：`set_last_fault_detected()`
  4. accessor：`get_pt_phase_orders()`
  5. accessor / setter：4 组 blackbox order 列表
- `reset_blackbox_orders()` 已在 service 内部内联为 `_reset_blackbox_orders()`，不再经 controller 薄转发
- 本轮回归：`pytest 13 passed`

**R39 结果**：
- 已完成；`hardware_actions.py` 当前 `self._ctrl` = 0
- Phase 4 参数数量最高（16 个），验证了在耦合面最杂的动作编排器上“1 直接注入 + 1 accessor + 7 query + 7 行为”组合仍可控
- `_get_generator_state(gen_id)` 已在 service 内部内联为私有方法，不再经 controller 私有方法穿透
- 所有 UI 交互（`show_warning`、3 个事故对话框）均改为延迟求值行为回调，因 `ui` 在 controller 初始化中晚于 `hw` 创建
- 本轮回归：`pytest 13 passed`

### R40–R42：大型 service + 汇聚器

**R40 结果**：
- 已完成；`pt_phase_check_service.py` 当前 `self._ctrl` = 0
- 已在大型 step service 上验证了“2 个稳定对象直接注入 + 2 个 accessor / setter + 2 个查询回调 + 5 个行为回调”组合仍然可控
- `physics` 因 controller 初始化顺序约束，继续采用 `get_physics()` accessor callback；`pt_phase_check_state` 因 reset 会整体替换，继续采用 accessor + setter callback
- 本轮回归：`pytest 13 passed`

**R41 结果**：
- 已完成；`pt_exam_service.py` 当前 `self._ctrl` = 0
- 已在大型 step service 上验证了“2 个稳定对象直接注入 + 1 个 physics accessor + 1 个状态字典 accessor + 3 个查询回调 + 1 个行为回调 + 私有方法内联”组合仍然可控
- `pt_exam_states` 作为稳定 dict 仅使用单一 accessor 注入，未为按键替换条目额外引入 setter；`_get_generator_state(gen_id)` 已在 service 内部内联
- 本轮回归：`pytest 13 passed`

**R42 结果**：
- 已完成；`assessment_coordinator.py` 当前 `self._ctrl` = 0
- Phase 4 service 参数数量新高（19 个），但已验证“3 个稳定对象直接注入 + 10 个 accessor/setter + 3 个查询回调 + 1 个行为回调 + main.py 适配层 ctrl 封装”在最重汇聚器上仍可控
- `build_assessment_context()` 已将 `AssessmentContext.from_snapshot_and_ctrl(snapshot, self)` 的 ctrl 依赖封装在 `main.py` lambda 内，service 本体不再直接感知 controller
- Phase 4 service 层 `self._ctrl` 总量已从 `61 -> 0`，service 子阶段收口；下一轮进入 R43 信号层
- 本轮回归：`pytest 13 passed`

- R40、R41、R42、R43、R44 已完成；Phase 4 已真正收官
- R45、R46、R47 已完成；后续轮次不再预先排期，按需立项

### R43：ControllerSignals 引入 + 分阶段 render 迁移

前置条件：R33–R42 全部完成，所有 service 的 `self._ctrl` = 0。

**阶段 1**：建立信号层
- 新增 `ControllerSignals(QObject)`
- controller 在关键状态变化点发出信号
- 暂保留原 `_tick → render_visuals` 作为 fallback

**阶段 2**：迁最清晰的消费者
- 优先迁移文本状态标签、step 完成事件、局部 UI 更新点
- 暂不动 waveform / phasor / circuit 全链路

**阶段 3**：评估轮询压缩
- 当 signals 已稳定覆盖主要 UI 变更后，决定是否保留 `_tick` 低频兜底或进一步压缩 `render_visuals`

**R43 结果**：
- 已完成；新增 `app/controller_signals.py`，当前仅声明 `step_changed(int, int)`、`assessment_mode_changed(bool)` 两个信号
- `PowerSyncController` 已在构造早期持有 `self.signals`；`assessment_mode_changed` 由 `test_flow_mode` setter 发出，`step_changed` 由 `get_test_progress_snapshot(step, ...)` 的单点观测入口发出
- `ui/main_window.py` 已新增 `_on_step_changed()`、`_on_assessment_mode_changed()` 两个 slot，并将试点落在主窗口状态栏的两个纯文本状态徽标
- `_tick` 周期、`render_visuals` 主路径、waveform / circuit / matplotlib canvas 相关逻辑均保持原样
- 阶段 2 采用最小试点形态：本轮新增的是顶层状态徽标，并未真正迁移既有 `render_visuals` 轮询消费者
- 阶段 3（轮询压缩）未执行；如后续 UX/性能反馈表明有必要，再独立立项推进

### R44：physics 层 `self.ctrl` 清理

**R44 结果**：
- 已完成；`services/physics_engine.py` 已改为 10 参 keyword-only 依赖注入，不再持有 `self.ctrl`
- `services/_physics_arbitration.py`、`services/_physics_measurement.py`、`services/_physics_protection.py` 中原有 `self.ctrl.*` 路径已全部改为直接注入对象、accessor、query callback 与 behavior callback
- `_physics_core.py` 经核对仍为 `0` 处 `self.ctrl`，本轮未涉及
- repo 级 `grep -rn "self\._ctrl\|self\.ctrl" services/ | wc -l` 已从上一轮残留值 `31` 收口到 `0`
- `app/main.py` 仅在 `PhysicsEngine(...)` 构造处完成适配；`tests/**`、`ui/**`、`domain/**`、`adapters/**` 均保持零改动

### R45：ControlPanel 组件化与瘦身

**R45 结果**：
- 已完成；`ui/panels/control_panel.py` 当前 `328` 行，已低于 §1.2 健康阈值
- 新增 `ui/widgets/control_panel/` 子包，`GeneratorCard / RunControlsPage / ParamControlsPage` 已承接原 Page0 / Page1 / 发电机子面板主体
- `WidgetBuilderMixin` 已收敛为薄入口：保留页切换装配、故障预设、宿主属性回绑与少量跨区联动
- `self.ctrl.sim_state.*` 读写仍按 §5.2 例外条款保留；`c.hw.*` 三处直连已全部改为宿主回调注入
- `pytest 13 passed`；`services/` 层 `self._ctrl | self.ctrl` 继续保持 `0`

### R46：状态真值源收口 + `_BoolProxy` 清理

**R46 结果**：
- 已完成；新增 `domain/phase_order_state.py`，`PhaseOrderState` 当前集中持有 `pt_phase_orders`、4 组 blackbox order 与 `pt_blackbox_mode`
- `PowerSyncController` 已改为 `self.phase_order_state = PhaseOrderState.default()`，并通过 `@property / setter` 维持旧公开访问面不变
- `reset_pt_phase_orders()`、`reshuffle_pt_phase_orders()`、`reset_blackbox_orders()`、`set_g2_terminal_fault()`、`on_pt_blackbox_toggle()`、`get_pt_blackbox_mode()` 已下沉为状态容器委托；容器写操作统一改为原地覆盖同一 list/dict 引用
- `apply_g2_blackbox_to_pt3()` 与 `apply_pt1_blackbox_to_pt_phases()` 已显式承接两处原先隐式派生关系；`blackbox_repair_handler.sync_*` 现通过它们落相序写侧
- `_BoolProxy`、`_pt_blackbox_mode_proxy` 与 `pt_blackbox_mode` 兼容壳已物理删除；全仓 `self._ctrl` 基线现为 `0`
- 本轮回归：`pytest -q` = `16 passed`

### 基线数据（Phase 4 启动时）

`self._ctrl` 引用总量：**339** 处（10 个 service 文件）

| 文件 | 引用数 |
|---|---:|
| `assessment_coordinator.py` | 61 |
| `pt_exam_service.py` | 49 |
| `fault_manager.py` | 40 |
| `pt_phase_check_service.py` | 38 |
| `blackbox_repair_handler.py` | 36 |
| `hardware_actions.py` | 35 |
| `sync_test_service.py` | 27 |
| `pt_voltage_check_service.py` | 24 |
| `loop_test_service.py` | 21 |
| `phase_order_resolver.py` | 8 |

已确认无需处理：`flow_mode_manager.py`（0 处）、`assessment_service.py`（0 处）

---

## 11. 每轮更新模板

后续每一轮重构结束后，必须更新 §9 的轮次历史：

```text
### 第 N 轮 (YYYY-MM-DD)：[主攻目标名]
- 本轮唯一主攻目标：
- 实际完成：
- 删除了哪些旧代码：
- 接口变化：（新模块的输入/输出边界是什么）
- 耦合度变化：（哪个文件的 ctrl 引用数下降了多少）
- 快照测试：PASS / FAIL（失败原因）
- 回归清单：PASS / FAIL
- 下一轮起点：
```

---

## 12. 本文件使用规则

- 新对话开始时，先读取本文件。
- 如需刷新大文件基线，先运行 `python scripts/report_large_files.py`。
- 先看：
  - §3 当前总体进度
  - §9 已完成进度
  - §10 下一轮默认起点
- 未经确认，不得跳过当前 Phase 直接做后续 Phase 的大范围重构。
- 每次完成后，本文件优先级高于临时对话记忆。

---
