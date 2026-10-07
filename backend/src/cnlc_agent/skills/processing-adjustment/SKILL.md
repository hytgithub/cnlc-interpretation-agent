---
name: processing-adjustment
description: 用户要求读取或修改处理参数、重新执行指定步骤或调整井段后处理时使用。
---

# 参数调整与指定步骤重跑

1. 明确井、资料版本、MD 顶底深（m）和 `step_id`。必要时用 `get_well_data` 补充井和版本。缺少范围或步骤时澄清。
2. 用 `get_processing_parameters` 读取目标范围和步骤的 `definitions`、`parameters` 与 `revision`。只采用工具声明的字段、单位和允许值；未声明的参数不能自行编造。
3. 用户要求修改时调用 `update_processing_parameters`，传入相同上下文、当前 `expected_revision` 和 `changes`。采样间隔字段以定义为准；当前声明为 `sampling_interval_m`，单位 m。只要求修改时完成后即返回。
4. 用户同时要求重跑时，修改成功后调用 `rerun_step`，传入同一上下文、同一 `step_id` 和更新实际返回的 `expected_parameter_revision`。仅重跑时使用参数读取返回的修订号。
5. 前置结果必须是真实取得的 `input_result_ids`。工具拒绝缺失、失败或过期引用时停止，不自动执行用户未要求的其他阶段。含水饱和度与流体识别阶段内按 `calculate_sw` → `identify_fluid` 执行，前者不可继续时停止后者。
6. 版本冲突时重新读取当前设置并说明冲突，不重复提交旧修订号，不擅自覆盖并发修改。
7. 根据实际执行的工具、结果正文、参数快照和执行说明汇报完成情况；参数保存不表示计算完成，调用成功不代表数值重新计算。新结果引用仅在内部保留供后续调用，历史不覆盖。
8. 修改返回的 `affected_result_ids` 表示需要重新评估的既有结果。只重跑选定步骤；用户要求继续后续解释时再按常规测井解释 Skill 的阶段和依赖顺序组织，不宣布单步重跑已完成全流程。

面向用户的答复使用自然中文说明“读取了什么、修改或重跑了什么、结果如何、是否需要后续操作”。不要展示 `step_id`、修订号、`result_id`、`affected_result_ids` 等机器字段或 UUID；用户明确询问这些技术信息时再解释。流程内部仍须使用工具实际返回的修订号和结果引用。
