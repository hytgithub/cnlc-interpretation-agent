"""基于运行及版本事实组装 Markdown 演示和诊断报告。"""


def render_report(run: dict, steps: list[dict], result: dict | None) -> str:
    """生成带版本和 Mock 标签的 Markdown 演示或诊断报告。"""
    lines = [
        f"# 测井解释{'演示' if result else '诊断'}报告",
        "",
        f"- 运行：`{run['run_id']}`",
        f"- 井：`{run['well_id']}`",
        f"- 场景：{run['scenario_name']}",
        f"- 状态：`{run['status']}`",
        f"- 结果版本：`{result['result_revision_id'] if result else '无'}`",
        "- 来源：Mock 样本预设输出；不构成正式专业结论。",
        "",
        "## 步骤记录",
        "",
    ]
    lines.extend(
        f"- {step['title']}：`{step['status']}`" for step in steps
    )
    lines += ["", "## 未完成或告警", ""]
    found = False
    for step in steps:
        for warning in step.get("warnings", []):
            found = True
            lines.append(f"- {step['title']}：{warning['message']}")
        for error in step.get("errors", []):
            found = True
            lines.append(f"- {step['title']}：{error['message']}")
    if not found:
        lines.append("- 无")
    return "\n".join(lines) + "\n"
