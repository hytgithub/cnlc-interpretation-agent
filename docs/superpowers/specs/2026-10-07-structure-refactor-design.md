# 项目职责拆分设计

## 目标与范围

按用户要求先优化项目结构，每个文件尽量承担单一职责。此次改动迁移现有实现、整理依赖和拆分展示组件；保留业务行为、HTTP 路径和主要响应结构；按 2026-10-07 用户追加要求，将处理步骤标识改为语义化名称，并同步更新 Skill、提示词、文档、样本和测试。此前发现的 Skill 装配与查询契约问题另行处理，不混入本次结构重构。

按“谁负责什么、依赖谁、通过什么接口使用”决定拆分边界，不按行数机械拆文件。现有通用 UI 组件若已负责一种组件，无需拆分。前后端分别验证，每一步都保持可启动。

以用户 2026-10-07 删除代码后的工作区为基线：独立测井工作台 `static/index.html` 及 `/workbench` 专用路由已移除，当前仅保留 AgentScope React 前端。此次重构不恢复这些内容；首页在前端未构建时返回 503，SPA 回退只接受现有页面前缀，其他页面返回 404。保留这两项行为和现有包资源配置。

## 后端目标结构

保留 `backend/src/cnlc_agent` 包布局，避免影响安装入口和包内资源定位。

```text
cnlc_agent/
  app.py                         # build_app 装配及旧启动入口转发
  cli.py                         # 命令行、环境读取和 Uvicorn 启动
  runtime.py                     # 数据目录、共享服务、存储和消息总线装配
  lifecycle.py                   # 启动恢复、环境凭据初始化和关闭清理
  api/
    dependencies.py              # 会话归属检查与服务依赖
    errors.py                    # 业务错误转 HTTP 响应
    health.py                    # 健康标识及能力目录路由
    well.py                      # 井、曲线、层段、统计路由
    selection.py                 # 范围选择路由
    runs.py                      # 测试运行和解释运行路由
    results.py                   # 结果查询及比较路由
    reports.py                   # 报告查询路由
    tools.py                     # 实际工具清单路由
    frontend.py                  # 静态资源及 SPA 回退路由
  contracts/
    selection.py                 # SelectionRequest
    workflow.py                  # WorkflowRequest、ComparisonRequest
    agent_tools.py               # Agent 工具参数 Schema
  agent/
    policy.py                    # 工具允许清单及 RestrictedAgent
    middleware.py                # ContextMiddleware
    tools.py                     # FunctionTool 包装与注册
    responses.py                 # 业务结果转 ToolChunk
    models/environment.py        # 环境模型及凭据适配
    models/scripted.py           # ScriptedModel 及测试凭据
  business/
    errors.py                    # BusinessError
    tracing.py                   # call_trace
    service.py                   # 用户和会话绑定的查询业务服务
  repositories/
    business.py                  # 选择、耗时测试运行、工具清单持久化
    workflow.py                  # 流程、步骤、结果、报告持久化
  adapters/mock/
    well.py                      # MockWell：样本加载、范围校验和有界查询
    workflow_tools.py            # Fixture 专业结果适配
  workflow/
    definition.py                # STEPS、SCENARIOS
    engine.py                    # 固定流程编排、终态和产物关联
    stages.py                    # 四阶段状态汇总
  reports/renderer.py            # Markdown 演示和诊断报告生成
  catalog.py                     # 能力描述和分组目录，保留独立职责
  prompts/、skills/、data/        # 保留现有资源路径
  static/agentscope/             # React 前端构建产物
```

`app.py` 只连接对象、注册路由及生命周期，不执行统计或渲染报告。API 和 Agent 工具继续调用共用业务服务及 Workflow；仓储不依赖 FastAPI 或 AgentScope；Mock 适配不依赖 API 或模型。Workflow 使用仓储和内部工具，报告渲染只消费运行及结果事实。

保留现有 `cnlc_agent.app:main` 安装入口。旧 `framework.py`、`business`、`workflow` 导入路径通过明确的导出兼容现有测试和调用方；兼容文件只转发符号，不放业务实现。测试中对 `ScriptedModel`、`ContextMiddleware` 的补丁必须作用于同一个类对象。

## React 前端拆分

1. `api/types.ts` 拆为 `api/types/` 中的 shared、agent、session、credential、chat、workspace、hub、mcp、skill、schedule、model、knowledge、channel、health 模块；入口仅转发类型，保留 `@/api` 和 `@/api/types` 的现有使用方式。跨模块依赖使用直接的 `import type`，避免从总入口反向导入。
2. 聊天页面将会话路由和恢复、会话操作、侧栏列表、弹窗装配分开；`ChatViewport` 将面板布局算法与持久化、会话配置操作、文件输入处理、面板描述及布局渲染分开。保留 URL 作为所选会话来源、localStorage 键、SSE 接口和切换行为。
3. `ASMessageBubble` 分离工具调用配对与分组、工具组摘要、音频播放控件、思考块、内容块展示及消息外壳。工具配对规则、孤立结果和流式内容顺序保持现状。
4. 凭据页面分离模型表格、凭据详情和页面装配；模型参数弹窗分离 Schema 解析、字段控件和弹窗状态。MCP/Skill 页面分别分离资源行、详情和页面装配，保留各自安装逻辑。
5. 对其余文件检查职责，已有明确组件、hook、API 或单一功能的文件保留。避免因复用方便而新增混合职责的 `utils` 或 `common` 大文件。

## 验证与验收

- 重构前运行现有完整 Python 测试和前端构建，记录基线。
- 后端按业务存储、框架适配、Workflow、HTTP 装配顺序移动实现；每次使用现有相关测试检查行为。补充 Workflow 状态及报告版本绑定测试，保护已有行为。
- 通过业务接口检查会话建立、范围保存、曲线与层段查询、完整演示、版本比较和报告；验证首页未构建返回 503，已构建时现有 React 页面能刷新，`/workbench` 和未知页面返回 404。
- 前端运行 TypeScript/Vite 构建；检查聊天会话切换、面板布局恢复、工具结果显示、凭据与资源页面。新增纯算法测试应针对可观察行为。
- 最终运行 `uv run --extra prototype pytest -q`、`pnpm --dir frontend build`，检查包资源和导入依赖；报告已有失败与重构导致的失败。
- README 及现有技术方案同步实际目录和阅读入口，不新增任务完成总结。
- 现有工作区包含大量未跟踪文件和用户文档删除记录。执行时保留这些状态，避免以 clean/reset 恢复工作区；不把用户既有内容混入重构提交。

验收标准：以用户删除代码后的行为为准；实现归属可从目录和模块说明识别；业务层没有框架依赖；接口、工具包装、存储和报告各自独立；前端页面主要承担装配职责；完整测试与构建结果可复核。

## 追加要求：步骤标识

处理步骤使用便于理解的语义化标识。更新工具契约、流程定义、能力目录、Fixture 键和引用方；面向用户的报告与未完成步骤列表显示中文名称。流程顺序、执行门控和专业能力行为保持不变。历史数据库兼容需依据项目实际持久化情况核对。
