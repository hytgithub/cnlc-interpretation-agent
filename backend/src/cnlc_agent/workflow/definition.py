"""固定演示流程及可用场景定义。"""

STEPS = (
    ("data_preparation", "资料准备", "DATA_PREP"),
    ("data_completeness", "资料完整性检查", "PREPROCESS"),
    ("curve_quality", "曲线质量检查", "PREPROCESS"),
    ("lithology_identification", "岩性识别", "INTERPRET"),
    ("petrophysical_evaluation", "物性评价", "INTERPRET"),
    ("sw_and_fluid_identification", "Sw 与流体识别", "INTERPRET"),
    ("layer_classification", "层分类", "INTERPRET"),
    ("interval_merging", "层段整理", "INTERPRET"),
    ("interpretation_validation", "解释验证", "INTERPRET"),
    ("report_readiness_check", "报告前检查", "INTERPRET"),
)

SCENARIOS = {
    "baseline": "基线演示",
    "recommended_missing": "推荐资料缺失告警",
    "required_missing": "必需曲线缺失阻断",
    "tool_failure": "岩性识别 Mock 工具失败",
    "provider_unknown": "外部操作结果未知演示",
    "serious_conflict": "解释验证严重冲突复核",
    "insufficient_evidence": "解释验证证据不足复核",
}
