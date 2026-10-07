"""从已保存步骤推导四阶段状态。"""


def summarize_stages(steps: list[dict]) -> list[dict]:
    """从步骤事实汇总四阶段状态，不维护容易失真的第二份状态。"""
    groups = (
        ("DATA_PREP", "资料准备", ("data_preparation",)),
        ("PREPROCESS", "预处理与质量控制", ("data_completeness", "curve_quality")),
        (
            "INTERPRET",
            "专业解释与验证",
            ("lithology_identification", "petrophysical_evaluation", "sw_and_fluid_identification", "layer_classification", "interval_merging", "interpretation_validation", "report_readiness_check"),
        ),
        ("REPORT", "报告生成", ()),
    )
    by_step = {step["step_id"]: step["status"] for step in steps}
    priority = (
        "FAILED",
        "BLOCKED",
        "REVIEW_REQUIRED",
        "RUNNING",
        "PENDING",
        "WARNING",
        "SUCCESS",
    )
    output = []
    for stage_id, name, step_ids in groups:
        statuses = [by_step[step_id] for step_id in step_ids if step_id in by_step]
        status = next(
            (candidate for candidate in priority if candidate in statuses), "PENDING"
        )
        output.append(
            {
                "stage_id": stage_id,
                "name": name,
                "status": status,
                "step_ids": list(step_ids),
                "completed_steps": sum(x in {"SUCCESS", "WARNING"} for x in statuses),
                "total_steps": len(step_ids),
            }
        )
    return output
