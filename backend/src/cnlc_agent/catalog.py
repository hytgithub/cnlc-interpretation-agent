"""测井原型的能力目录，区分模型入口、内部业务、Provider 和框架工具。"""

from dataclasses import asdict, dataclass

from .contracts.agent_tools import INTERACTIVE_SCHEMAS, ProfessionalInput, WellDataInput
from .contracts.plotting import CurvePlotInput


@dataclass(frozen=True)
class Capability:
    """提供工作台和智能体共用的能力描述，不代表该能力已具备真实算法。"""

    capability_id: str
    name: str
    category: str
    caller: str
    status: str
    description: str
    steps: tuple[str, ...] = ()
    is_mock: bool = True
    input_schema: dict | None = None
    output_schema: dict | None = None
    read_only: bool = True
    adapter_binding: str | None = None


# 业务逻辑工具契约对应源项目的十项专业能力映射。
# 专业能力直接开放给模型；完整流程由 Skill 组织。适配器当前使用样本。
PROFESSIONAL_TOOLS = (
    Capability(
        "get_well_data",
        "读取井资料",
        "professional_business",
        "Agent / Skill",
        "MOCK_ONLY",
        "读取井概要、曲线目录和资料版本。",
        ("data_preparation",),
        read_only=False,
    ),
    Capability(
        "check_data_completeness",
        "资料完整性检查",
        "professional_business",
        "Agent / Skill",
        "MOCK_ONLY",
        "依据资料要求检查必需曲线，返回缺失项和继续条件。",
        ("data_completeness",),
        read_only=False,
    ),
    Capability(
        "check_curve_quality",
        "曲线质量检查",
        "professional_business",
        "Agent / Skill",
        "MOCK_ONLY",
        "读取预设 QC 结果，不执行曲线校正。",
        ("curve_quality",),
        read_only=False,
    ),
    Capability(
        "identify_lithology",
        "岩性识别",
        "professional_business",
        "Agent / Skill",
        "MOCK_ONLY",
        "读取样本预设岩性输出。",
        ("lithology_identification",),
        read_only=False,
    ),
    Capability(
        "evaluate_petrophysics",
        "物性评价",
        "professional_business",
        "Agent / Skill",
        "MOCK_ONLY",
        "读取样本预设物性输出。",
        ("petrophysical_evaluation",),
        read_only=False,
    ),
    Capability(
        "calculate_sw",
        "含水饱和度结果",
        "professional_business",
        "Agent / Skill",
        "MOCK_ONLY",
        "读取样本预设 Sw 输出，不推导公式。",
        ("sw_and_fluid_identification",),
        read_only=False,
    ),
    Capability(
        "identify_fluid",
        "流体识别结果",
        "professional_business",
        "Agent / Skill",
        "MOCK_ONLY",
        "读取样本预设流体输出。",
        ("sw_and_fluid_identification",),
        read_only=False,
    ),
    Capability(
        "classify_layer",
        "层分类结果",
        "professional_business",
        "Agent / Skill",
        "MOCK_ONLY",
        "读取样本预设分类输出。",
        ("layer_classification",),
        read_only=False,
    ),
    Capability(
        "merge_intervals",
        "层段结果",
        "professional_business",
        "Agent / Skill",
        "MOCK_ONLY",
        "读取样本预设层段，不重新计算厚度。",
        ("interval_merging",),
        read_only=False,
    ),
    Capability(
        "validate_interpretation",
        "解释验证结果",
        "professional_business",
        "Agent / Skill",
        "MOCK_ONLY",
        "读取样本预设验证状态。",
        ("interpretation_validation",),
        read_only=False,
    ),
    Capability(
        "prepare_report",
        "报告前检查",
        "professional_business",
        "Agent / Skill",
        "MOCK_ONLY",
        "执行结构与步骤完整性检查，不生成报告。",
        ("report_readiness_check",),
        read_only=False,
    ),
)

INTERACTIVE_TOOLS = (
    Capability('query_interval_results', '已有层段解释结果查询', 'interactive_business', 'Agent / Skill', 'MOCK_ONLY', '只读资料或保存的层段结果，不执行层段整理。'),
    Capability('get_processing_parameters', '处理参数查询', 'interactive_business', 'Agent / Skill', 'MOCK_ONLY', '读取参数定义、当前值和修订号。'),
    Capability('update_processing_parameters', '处理参数修改', 'interactive_business', 'Agent / Skill', 'MOCK_ONLY', '校验参数并保存修订，返回受影响结果。', read_only=False),
    Capability('rerun_step', '指定步骤重跑', 'interactive_business', 'Agent / Skill', 'MOCK_ONLY', '按实际参数快照仅执行目标步骤并保留新结果。', read_only=False),
    Capability('plot_curves', '测井曲线绘图', 'interactive_business', 'Agent / Skill', 'MOCK_ONLY', '读取指定范围的原始或已有结果曲线，生成多道SVG图表，不执行专业处理。', read_only=False),
)
AGENT_ENTRY_TOOLS = tuple(item.capability_id for item in PROFESSIONAL_TOOLS + INTERACTIVE_TOOLS)

# 一次 Provider 批次可以支撑多个 Workflow 内部业务结果。
# 新项目目前没有公司服务契约或凭据，所以都处于待接入状态。
PROVIDER_BATCHES = (
    Capability(
        "company_analysis",
        "资料分析批次",
        "provider_batch",
        "Provider Adapter",
        "CONTRACT_PENDING",
        "源项目批次名称；当前新项目未接入。",
        ("data_preparation",),
        False,
    ),
    Capability(
        "company_preprocessing",
        "预处理批次",
        "provider_batch",
        "Provider Adapter",
        "CONTRACT_PENDING",
        "源项目批次名称；当前新项目未接入。",
        ("curve_quality",),
        False,
    ),
    Capability(
        "company_interpretation",
        "解释批次",
        "provider_batch",
        "Provider Adapter",
        "CONTRACT_PENDING",
        "一次底层调用可映射多个专业结果；当前新项目未接入。",
        ("lithology_identification", "petrophysical_evaluation", "sw_and_fluid_identification", "layer_classification", "interval_merging", "interpretation_validation"),
        False,
    ),
    Capability(
        "company_report",
        "报告批次",
        "provider_batch",
        "Provider Adapter",
        "CONTRACT_PENDING",
        "源项目批次名称；当前新项目未接入。",
        ("report_readiness_check",),
        False,
    ),
)

LOCAL_COMPONENTS = (
    Capability(
        "data_requirements",
        "资料完整性检查",
        "local_component",
        "Workflow",
        "MOCK_ONLY",
        "依据样本自带 requirements 检查，不外推为通用规则。",
        ("data_completeness",),
    ),
    Capability(
        "validation_agent",
        "解释证据验证",
        "local_component",
        "Workflow",
        "MOCK_ONLY",
        "消费样本预设 validation 输出；不进行模型判断。",
        ("interpretation_validation",),
    ),
    Capability(
        "report_assembler",
        "报告组装",
        "local_component",
        "业务服务",
        "MOCK_ONLY",
        "按结果版本生成演示或诊断 Markdown。",
        ("REPORT",),
    ),
)

FRAMEWORK_TOOLS = (
    "TaskCreate",
    "TaskGet",
    "TaskList",
    "TaskUpdate",
    "ToolStop",
    "Skill",
)

TEST_ONLY_TOOLS = ("slow_mock_statistics",)


def capability_manifest(include_test_tools: bool = False) -> dict:
    """返回有边界的能力目录；框架和测试工具另列，避免混入业务工具。"""
    groups = {
        "agent_entry": [
            {
                "tool_name": name,
                "category": "agent_entry",
                "caller": "AgentScope Agent",
                "status": "MOCK_ONLY",
                "is_mock": True,
                "read_only": name in {'query_interval_results', 'get_processing_parameters'},
                "input_schema": ({**INTERACTIVE_SCHEMAS, 'plot_curves': CurvePlotInput}.get(name, WellDataInput if name == "get_well_data" else ProfessionalInput)).model_json_schema(),
                "output_schema": {"type": "object", "required": ["status", "is_mock"]},
            }
            for name in AGENT_ENTRY_TOOLS
        ],
        "professional_business": [
            asdict(item) for item in PROFESSIONAL_TOOLS
        ],
        "interactive_business": [asdict(item) for item in INTERACTIVE_TOOLS],
        "provider_batches": [asdict(item) for item in PROVIDER_BATCHES],
        "local_components": [asdict(item) for item in LOCAL_COMPONENTS],
        "framework_tools": [
            {
                "tool_name": name,
                "category": "framework_control",
                "caller": "AgentScope",
                "status": "FRAMEWORK",
            }
            for name in FRAMEWORK_TOOLS
        ],
        "test_only": [
            {
                "tool_name": name,
                "category": "test_only",
                "caller": "Prototype verification",
                "status": "TEST_ONLY",
                "exposed_to_workbench": False,
                "exposed_to_agent": include_test_tools,
            }
            for name in TEST_ONLY_TOOLS
        ],
    }
    return {
        "profile": "local_mock",
        "groups": groups,
        "formal_publication_enabled": False,
        "real_provider_enabled": False,
    }
