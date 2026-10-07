# 单一职责结构重构实施计划

> 执行方式：在当前会话按 executing-plans 连续实施。用户已确认更新后的设计并要求优化。

**Goal:** 拆分混合职责，保持用户删除独立工作台后的业务行为。
**Architecture:** 保留 Python src 包布局和外部导入兼容；分离 HTTP、Agent、业务、存储、Mock、Workflow、报告。React 按业务类型、状态逻辑和展示组件拆分。
**Tech Stack:** Python 3.12、AgentScope 2.0.9、FastAPI、SQLite、React、TypeScript、Vite。
**Spec:** ../specs/2026-10-07-structure-refactor-design.md

## 全局约束

- 不恢复独立工作台；保留首页 503、未知页面 404 的现有行为。
- 本次结构重构阶段保持 HTTP 路径、响应、数据库和 Skill 行为；后续按用户追加要求将步骤标识语义化。
- 现有未跟踪代码保留在当前目录，新分支 codex/structure-refactor；不提交用户既有内容。
- 只迁移实现与接口依赖，不加入真实 Provider、队列或新的业务功能。
- 各旧入口转发同一类或函数对象，保留测试补丁和包资源位置。

## 任务与验证

### 1. 业务、存储与流程

- [x] 补充 tests/test_workflow.py，保护七种演示场景的终态、结果版本、报告绑定及归属隔离；在原实现运行。
- [x] 分离 business/errors.py、tracing.py、service.py、contracts/selection.py、repositories/business.py、adapters/mock/well.py。
- [x] 分离 workflow/definition.py、engine.py、stages.py、repositories/workflow.py、adapters/mock/workflow_tools.py、reports/renderer.py；流程通过仓储读取步骤，不直接访问 SQL。
- [x] 原 business/workflow 导入由包入口转发；运行业务和流程测试。

### 2. Agent 接入及服务装配

- [x] 分离 agent/policy.py、middleware.py、tools.py、responses.py、models/environment.py、models/scripted.py、contracts/agent_tools.py；framework.py 只做兼容导出。
- [x] 分离 runtime.py、lifecycle.py、cli.py、contracts/workflow.py；app.py 只装配。
- [x] API 按井查询、选择、运行、结果、报告、工具、健康和静态前端拆分；会话归属与异常处理各自独立。
- [x] 曲线投影和版本比较算法归属业务模块，路由只解析参数与转换错误。
- [x] 运行 uv run --extra prototype pytest -q；验证首页、React 回退和已删除入口。

### 3. React 类型与组件

- [x] api/types.ts 按领域移动至 api/types/，保留原导入入口。
- [x] 拆分聊天面板布局、会话操作、附件处理、侧栏及弹窗；保留 URL、localStorage、SSE 和状态切换规则。
- [x] 拆分消息工具分组、音频、思考块、内容块和消息外壳。
- [x] 拆分凭据详情与模型表格、模型参数 Schema 和字段、MCP/Skill 资源展示组件。
- [x] 检查其他文件职责；职责明确的组件保留。运行 pnpm --dir frontend exec tsc -b --pretty false。

### 4. 验收

- [x] README 和现有技术方案同步目录及阅读入口。
- [x] 完整 Python 测试、前端构建、包资源检查、浏览器基本交互验证。
- [x] 审核依赖方向、兼容导出、服务生命周期、前端导入及错误分支；必要修正后再验证。

## 重点风险

旧导入路径与 monkeypatch 必须仍指向同一对象；资源路径必须从根包定位；路由签名要保留 agent_id 和身份检查；报告与结果归属保持一致；组件迁移不能更改 hook 顺序或会话切换时的 SSE 生命周期。


### 5. 用户追加的步骤标识调整

- [x] 将十项步骤标识统一改为语义化名称，覆盖工具契约、流程定义、能力目录、样本 Fixture、测试与说明文档。
- [x] 更新 Skill 与系统提示词，使用中文步骤名称和顺序说明；报告及未完成步骤列表显示中文名称。
- [x] 添加启动时 SQLite 历史步骤标识迁移；检查当前工作区数据库并完成迁移。

实施说明：当前工作区的 SQLite 已存在两次旧流程记录，启动迁移已更新历史步骤键与 JSON 载荷。此轮未运行测试。
