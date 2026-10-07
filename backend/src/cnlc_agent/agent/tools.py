"""将独立专业业务能力注册为模型可直接调用的工具。"""

from agentscope.permission import PermissionBehavior, PermissionDecision
from agentscope.tool import FunctionTool
from pydantic import ValidationError

from ..business.errors import BusinessError
from ..business.professional import ProfessionalService
from ..business.interactive import InteractiveService
from ..business.plotting import CurvePlotService
from ..business.service import BusinessService
from ..contracts.agent_tools import INTERACTIVE_SCHEMAS, ProfessionalInput, SlowInput, WellDataInput
from ..contracts.plotting import CurvePlotInput
from .responses import chunk


DESCRIPTIONS = {
    "get_well_data": "读取井概要、资料版本、原始曲线名录和空值概要。well_id、dataset_revision 可省略以使用当前井和当前资料版本；top_depth_m 与 bottom_depth_m 必须同时提供，单位 m、基准 MD。读取曲线点时还必须提供 curve_names。返回实际使用的井和资料版本，以及请求的概要或曲线数据。无需先设置会话范围。",
    "check_data_completeness": "检查指定井段的资料完整性。必填范围字段为 well_id、dataset_revision、top_depth_m、bottom_depth_m（深度单位 m，基准 MD）；input_result_ids 用于引用已取得的前置结果。返回必需曲线、缺失项和是否满足继续条件。",
    "check_curve_quality": "检查指定井段的曲线质量。必填范围字段为 well_id、dataset_revision、top_depth_m、bottom_depth_m（m、MD）；input_result_ids 引用本次检查所依赖的前置结果；expected_parameter_revision 可选，用于校验处理参数版本。返回质量结果和判断依据。",
    "identify_lithology": "识别指定井段的岩性。必填范围字段为 well_id、dataset_revision、top_depth_m、bottom_depth_m（m、MD）；input_result_ids 引用已取得的前置结果，可选 expected_parameter_revision 校验参数版本。返回岩性结果和依据。",
    "evaluate_petrophysics": "评价指定井段的泥质、孔隙度、渗透率等物性。必填范围字段为 well_id、dataset_revision、top_depth_m、bottom_depth_m（m、MD）；input_result_ids 引用已取得的前置结果，可选 expected_parameter_revision 校验参数版本。返回物性结果和依据。",
    "calculate_sw": "计算指定井段的含水饱和度 Sw。必填范围字段为 well_id、dataset_revision、top_depth_m、bottom_depth_m（m、MD）；input_result_ids 引用已取得的前置结果，可选 expected_parameter_revision 校验参数版本。返回 Sw 结果及其引用信息。",
    "identify_fluid": "识别指定井段的流体类型。必填范围字段为 well_id、dataset_revision、top_depth_m、bottom_depth_m（m、MD）；input_result_ids 引用已取得的前置结果，特别是需要使用的 Sw 结果；可选 expected_parameter_revision 校验参数版本。返回流体识别结果与证据。",
    "classify_layer": "对指定井段进行层分类。必填范围字段为 well_id、dataset_revision、top_depth_m、bottom_depth_m（m、MD）；input_result_ids 引用已取得的前置结果，可选 expected_parameter_revision 校验参数版本。返回分类结果和依据。",
    "merge_intervals": "整理指定范围内相交的层段并计算厚度，保留原始层界。必填范围字段为 well_id、dataset_revision、top_depth_m、bottom_depth_m（m、MD）；input_result_ids 引用已取得的前置结果，可选 expected_parameter_revision 校验参数版本。返回整理后的层段。",
    "validate_interpretation": "验证指定井段的解释结果。必填范围字段为 well_id、dataset_revision、top_depth_m、bottom_depth_m（m、MD）；input_result_ids 应包含待验证的实际结果 ID，可选 expected_parameter_revision 校验参数版本。返回一致性、冲突及复核状态。",
    "prepare_report": "执行报告生成前的就绪检查。必填范围字段为 well_id、dataset_revision、top_depth_m、bottom_depth_m（m、MD）；input_result_ids 必须列出本流程实际取得的结果 ID，工具据此检查前置结果是否完整且可用。只返回检查结果，不生成报告正文。",
    "query_interval_results": "只读查询已有层段解释结果。必填范围字段为 well_id、dataset_revision、top_depth_m、bottom_depth_m（m、MD）；可选 result_id 指定已有版本，layer_no 按原始层号筛选。省略 result_id 时读取资料中的已有层段结果；不启动处理。",
    "get_processing_parameters": "读取指定井、资料版本、井段和步骤的参数定义与当前设置。必填范围字段为 well_id、dataset_revision、top_depth_m、bottom_depth_m（m、MD）和 step_id。返回参数名、类型、单位、允许值、当前值及修订号。",
    "update_processing_parameters": "更新指定步骤的处理参数。范围字段同 get_processing_parameters；step_id 指定步骤，expected_revision 填 get_processing_parameters 返回的 revision，changes 为参数名到值的非空映射。仅接受定义中声明的参数、类型和单位。返回新修订号与受影响结果；只保存设置，不执行重跑。",
    "rerun_step": "按指定参数版本只重跑一个步骤。必填范围字段为 well_id、dataset_revision、top_depth_m、bottom_depth_m（m、MD）、step_id 和 expected_parameter_revision；input_result_ids 填入实际前置结果 ID。Sw 与流体识别步骤会先计算 Sw 再识别流体。不覆盖历史结果，也不自动重跑其他步骤。",
    "plot_curves": "绘制指定井段的 SVG 多道测井曲线图。必填范围字段为 well_id、dataset_revision、top_depth_m、bottom_depth_m（m、MD）；curve_names 为 1 至 8 个实际曲线名，每条曲线单独一轨；result_id 可选，省略时绘制原始曲线，提供时只读取该结果中的曲线；log_curve_names 可选，列出要使用对数横轴的曲线，且必须是 curve_names 的子集。深度向下、空值断线。返回 chart（格式、读取地址和道数）并供界面显示和下载。绘图不执行专业处理；当前不支持 PNG、曲线叠加或高亮标注。",
}


def make_tools(service: BusinessService, *, include_test_tools: bool = False, agent_id: str | None = None):
    """注册模型可调用工具。

    各工具的参数说明由 Pydantic input_schema 提供；DESCRIPTIONS 说明用途、
    范围单位、引用字段及返回内容。专业工具逐项执行，不提交整套 Workflow。
    """
    professional = ProfessionalService(service)
    interactive = InteractiveService(service)
    plotting = CurvePlotService(service)
    allow = PermissionDecision(
        PermissionBehavior.ALLOW, "允许当前用户和会话内的专业业务操作。"
    )

    def make_entry(name, schema):
        def invoke(**arguments):
            try:
                request = schema.model_validate(arguments)
                if name == 'plot_curves':
                    from urllib.parse import urlencode, quote
                    payload = plotting.create(request)
                    plot_url = f'/business/sessions/{quote(service.session, safe="")}/plots/{payload["plot_id"]}'
                    if agent_id is not None:
                        plot_url += '?' + urlencode({'agent_id': agent_id})
                    # The model receives the actual presentation contract too;
                    # artifact_id is an internal filename, not a download URL.
                    payload.pop('artifact_id', None)
                    payload['chart'] = {'format': 'svg', 'url': plot_url, 'display': 'inline',
                                        'track_count': len(payload['tracks']), 'overlays': []}
                    metadata = {'curve_plot': {'url': plot_url, 'plot_id': payload['plot_id'], 'width': payload['width'], 'height': payload['height']}}
                    return chunk(payload, metadata=metadata)
                if name in INTERACTIVE_SCHEMAS:
                    payload = getattr(interactive, name)(request)
                else:
                    payload = professional.get_well_data(request) if name == "get_well_data" else professional.execute(name, request)
                return chunk(payload)
            except ValidationError as error:
                return chunk({"status": "ERROR", "code": "INVALID_INPUT", "message": str(error), "is_mock": True})
            except BusinessError as error:
                return chunk(error.payload())

        return FunctionTool(
            func=invoke, name=name, input_schema=schema,
            description=DESCRIPTIONS[name], is_read_only=name in {'query_interval_results', 'get_processing_parameters'}, permission=allow,
        )

    schemas = {**INTERACTIVE_SCHEMAS, 'plot_curves': CurvePlotInput}
    tools = [make_entry(name, schemas.get(name, WellDataInput if name == "get_well_data" else ProfessionalInput)) for name in DESCRIPTIONS]
    if include_test_tools:
        # 仅显式开启的框架验证路径保留耗时测试，不进入默认业务工具集。
        async def slow_mock_statistics(
            expected_selection_revision: int, curve_name: str = "GR",
            delay_seconds: float = 10.5, fail: bool = False,
        ):
            """后台通知验证专用：按当前选择修订号读取曲线统计，可设置模拟耗时或失败。"""
            try:
                return chunk(await service.slow_statistics(expected_selection_revision, curve_name, delay_seconds, fail))
            except BusinessError as error:
                return chunk(error.payload())

        tools.append(FunctionTool(
            func=slow_mock_statistics, input_schema=SlowInput,
            description="仅用于后台通知验证的耗时测试工具。",
            is_read_only=False, permission=allow,
        ))
    return tools
