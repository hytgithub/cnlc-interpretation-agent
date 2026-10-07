"""有界运行摘要，避免向模型传递完整曲线输出。"""


def run_summary(run: dict) -> dict:
    """移除样本曲线和专业输出，只保留运行列表与 Agent 可用状态。"""
    fields = (
        "run_id",
        "session_id",
        "well_id",
        "dataset_revision",
        "scenario_id",
        "scenario_name",
        "status",
        "message",
        "source",
        "is_mock",
        "created_at",
        "finished_at",
        "result_revision_id",
        "report_revision_id",
    )
    return {key: run[key] for key in fields if key in run}
