# 常规测井智能体

本项目当前交付 AgentScope 接入原型。模型可以直接调用专业业务工具，独立查询井信息、原始曲线和层段，或按常规测井解释 Skill 依次执行十项专业处理。底层使用一口合成样本井。业务 HTTP 接口保留范围选择、原始曲线统计、固定场景演示、结果版本比较和演示/诊断报告。

## 工具边界

| 层 | 定义与调用方 |
|---|---|
| 模型可直接调用的专业工具 | `get_well_data`、`check_data_completeness`、`check_curve_quality`、`identify_lithology`、`evaluate_petrophysics`、`calculate_sw`、`identify_fluid`、`classify_layer`、`merge_intervals`、`validate_interpretation`、`prepare_report`。单项任务按需调用，完整解释由 Skill 组织。 |
| 查询与交互工具 | `query_interval_results` 读取已有层段版本；`get_processing_parameters` 读取参数定义和当前设置；`update_processing_parameters` 校验并保存设置；`rerun_step` 使用明确的参数修订号只重跑指定步骤；`plot_curves` 绘制原始或已有结果的多道曲线，聊天界面显示并下载 SVG。 |
| 完整解释 Skill | `conventional-log-interpretation` 规定十项处理的顺序、结果引用和继续条件；含水饱和度与流体识别包含两次工具调用。 |
| HTTP 演示 Workflow | 保留固定场景编排、步骤记录和演示/诊断报告；不作为模型的流程提交入口。 |
| Provider 批次 | `company_analysis`、`company_preprocessing`、`company_interpretation`、`company_report`；新项目中均为 `CONTRACT_PENDING`，尚未发出公司服务调用。 |
| 本地规则与组件 | 资料完整性检查按样本 `requirements` 检查；报告前检查 `prepare_report` 做结构检查；`ReportAssembler` 生成绑定版本的 Markdown 报告。 |
| 框架/测试工具 | AgentScope 计划工具、`ToolStop`、Skill 查看器和 `slow_mock_statistics` 分别标记；耗时测试工具默认不进入运行服务的 Agent 清单。 |

完整解释包含十个专业步骤，对应十一项可独立调用的专业能力；另有五项查询与交互能力。工具直接接收井、资料版本和井段参数，无需先创建会话选择。专业执行返回持久化的 `result_id`，后续工具通过 `input_result_ids` 检查归属、版本、范围、参数和可用状态。查询已有层段不创建新处理结果。`prepare_report` 根据实际引用检查前置结果齐全，不接受模型自行声明步骤完成。

处理调整由 `processing-adjustment` Skill 指导。参数按当前用户、会话、井、资料版本、井段和步骤保存，修改使用修订号校验；计算结果记录实际使用的参数快照。修改影响本步及实际引用它的后续结果，过期结果保留以供查看，但不能继续作为处理输入。重跑只执行指定步骤，含水饱和度与流体识别阶段内先计算 Sw 后识别流体，不覆盖历史、不自动重跑后续阶段。

样本适配器目前仅为曲线质量检查声明 `sampling_interval_m`（正数，m），可验证“将采样间隔改为 0.2 m 后重新执行曲线质量检查”。它保存并传递设置，不对预设曲线执行重采样或专业重算；其他专业参数须由业务适配器声明后开放。重跑返回 `result_values_recomputed=false` 和执行说明。

当前专业解释数据仍来自样本预设 Fixture。返回的 `fixture_scope` 与 `scope_note` 区分完整样本汇总值和请求井段；曲线点按井段筛选，层段保留相交的原始层界。原始曲线统计仍由 HTTP 接口实际计算。系统提示词只规定通用职责，流程顺序放在 Skill 中。

绘图调用接收明确井段及 `curve_names`，可用 `log_curve_names` 指定对数横轴；最多八道，深度向下增加，空值断线。默认读取原始资料，指定 `result_id` 时只绘制该版本的已有曲线。历史结果可绘制并标明过期，绘图不启动专业处理。图表保存在业务数据目录的 `plots/`，模型只接收摘要与引用；界面通过会话归属保护的接口读取文件。

成功图表直接显示在会话正文，不随工具详情折叠；重新加载历史消息也保留展示。工具返回 `chart` 的实际 SVG 格式、会话读取地址和道数，每条曲线独占一道；当前不提供 PNG、曲线轨道合并或解释高亮标注，模型不得按内部产物ID编造下载路径。

完整能力目录：`GET /business/capabilities`。当前实现边界见下文“数据与状态”；详细设计见[技术框架方案](docs/详细技术框架方案.md)。

## 启动

使用 Python 3.12、uv、Node.js 和 pnpm。先构建 AgentScope 官方前端，再启动后端：

```sh
uv sync --locked --extra prototype --python python3.12
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend build
uv run --extra prototype cnlc-prototype
```

打开 `http://127.0.0.1:8000/` 使用 AgentScope 前端，`http://127.0.0.1:8000/docs` 查看接口。

首次打开 AgentScope 前端时，后端地址与本地演示用户已预填。服务启动时读取项目根目录 `.env`；当 `MODEL_NAME` 和 `MODEL_API_KEY` 已配置，AgentScope 会自动显示一个环境模型凭据并为新会话选择该模型。真实 API Key 只保留在服务进程环境中，不写入 AgentScope 数据库。模型调用会把用户输入和必要上下文发送到 `MODEL_BASE_URL` 指定的服务，并可能产生费用。

前端开发模式：先启动后端，再运行 `pnpm --dir frontend dev` 并打开 `http://127.0.0.1:5173/`。Vite 会把 AgentScope API 请求代理到 `127.0.0.1:8000`。Agent Prompt 从包内 Markdown 读取，四个 AgentScope Skill 以原生 Toolkit Skill 目录注册，模型通过 `Skill` 工具按需读取。首页需要已构建的 AgentScope 前端；未构建时返回 503。

耗时后台通知工具仅用于框架验证。需要手动演示时，设置 `CNLC_ENABLE_TEST_TOOLS=1` 后启动，或运行：

```sh
uv run --extra prototype cnlc-prototype --enable-test-tools
```

现有 HTTP 演示脚本也可使用：

```sh
uv run --extra prototype python scripts/demo.py
```

该脚本使用 JSON 测试指令，分别调用井概要、原始曲线和层段查询。默认工具集包含专业工具和 Skill；耗时测试工具仅在显式开启时加入。

## 数据与状态

- 样本为 `WELL_MOCK_PLOT_001`，深度 2000～2120 m，1201 个点、20 条曲线和 20 个预设层段。
- 会话范围选择使用会话归属检查和乐观修订号；曲线接口保留空值。
- Mock Workflow 记录阶段、步骤、内部逻辑工具运行和 Fixture 来源。当前没有真实 Provider 调用，`provider_batch_id` 保持空值。
- 成功或告警运行产生新的 Mock 结果版本。失败、阻断和复核运行生成诊断报告，不覆盖已有结果。
- 资料完整性检查的资料要求来自单井样本，不能外推为通用专业规则。解释验证的冲突场景是状态演示，不表示真实验证。
- 正式报告、结果发布、局部专业重算、外部作业取消和真实公司工具均未开放。

业务查询接口需要 `X-User-ID` 测试身份与 `agent_id`。该身份仅供本地验证，不能用于生产认证。存储是本地 SQLite，消息总线默认使用 fakeredis；PostgreSQL、独立 Redis 与生产部署尚未完成。

## 验证

运行自动测试：

```sh
uv run --extra prototype pytest -q
```

## 代码结构与阅读入口

```text
backend/src/cnlc_agent/
  app.py、runtime.py、lifecycle.py、cli.py  # 装配、资源、生命周期、启动
  api/                                    # HTTP 路由、归属依赖与错误转换
  agent/                                  # 工具包装、上下文、允许清单与模型适配
  contracts/                              # 请求与工具参数 Schema
  business/                               # 业务查询、错误、调用关联与版本比较
  repositories/                           # SQLite 持久化
  adapters/mock/                          # 样本资料与专业结果 Fixture
  workflow/                               # 流程定义、编排、阶段与运行摘要
  reports/                                # Markdown 报告组装
  prompts/、skills/、data/                 # 提示词、任务指南与样本资源
frontend/src/
  api/types/                              # 按业务领域组织的 API 类型
  pages/chat/                             # 聊天页面、会话状态、导航和面板
  pages/credential/、mcp/、skill/           # 页面装配及各自展示组件
  components/chat/                        # 消息、工具组、音频和思考块展示
```

建议从 `app.py` 的 `build_app()` 开始阅读。独立专业能力看 `business/professional.py`，HTTP 查询看 `business/service.py`，HTTP 演示流程看 `workflow/engine.py`，模型工具注册看 `agent/tools.py`。`framework.py` 以及 `business`、`workflow` 包入口保留旧导入兼容，新代码直接导入职责模块。

前端 `pages/chat/index.tsx` 和 `ChatViewport.tsx` 负责页面装配；会话配置、面板布局、附件转换分别在对应 hook 或独立模块中。`api/types.ts` 保留类型导出入口，定义位于 `api/types/`。

前端纯逻辑回归测试：`pnpm --dir frontend test`。后端完整测试仍使用上述 `pytest` 命令。

## 项目文档

Codex 开发流程见根目录 [AGENTS.md](AGENTS.md)。重大迭代在修改代码前，按以下顺序逐份完整读取文档：

1. 本 README：项目现状、工具边界、启动与验证方法、代码入口。
2. [项目目标概要](docs/项目目标概要.md)：建设目标与范围。
3. [产品需求文档](docs/产品需求文档.md)：业务需求与流程。
4. [项目评估概要](docs/项目评估概要.md)：评估方法与验收依据。
5. [技术框架设计](docs/技术框架设计.md)：总体架构与组件职责。
6. [详细技术框架方案](docs/详细技术框架方案.md)：接口、状态、存储与实施约束。
7. 本次迭代指定的设计文档（如已存在，位于 `docs/superpowers/specs/`）。
8. 本次迭代指定的实施计划（如已存在，位于 `docs/superpowers/plans/`）。

每份文档按正文顺序读取到末尾，长文件分段读取并补齐被截断的内容。完成后核对相关代码、契约、业务 Skill 和测试，说明需求依据、关键约束及文档与实现的差异，再按实施计划推进。历史迭代文档按本次任务的引用与影响范围补读。

重大迭代计划保留关键约束、决策依据、完成项、验证结果与下一步。恢复任务时读取计划并检查当前 Git 状态，补读相关原文；具体规则见 `AGENTS.md`。

文档优先维护上述设计文档和本 README。常规开发、修复和验证完成后，不自动新增任务说明、实施记录、验证记录或总结文档；仅在用户明确要求或确有必要时新增。
