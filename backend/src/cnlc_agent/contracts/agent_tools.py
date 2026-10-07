"""模型可见工具的输入参数契约。"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class WellDataInput(BaseModel):
    """井概要无需范围；原始曲线查询必须明确范围和曲线。"""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    well_id: str | None = Field(default=None, description="井标识。省略时读取服务端当前井。")
    dataset_revision: str | None = Field(default=None, description="期望资料版本。省略时读取当前版本。")
    top_depth_m: float | None = Field(default=None, description="顶深，MD，m。与底深同时提供。")
    bottom_depth_m: float | None = Field(default=None, description="底深，MD，m。与顶深同时提供。")
    curve_names: list[Annotated[str, Field(min_length=1, pattern=r"\S")]] | None = Field(default=None, min_length=1, description="要读取的原始曲线名；名称不能为空，提供时必须指定井段。")

    @model_validator(mode="after")
    def validate_scope(self):
        if (self.top_depth_m is None) != (self.bottom_depth_m is None):
            raise ValueError("顶深和底深必须同时提供。")
        if self.curve_names is not None and self.top_depth_m is None:
            raise ValueError("读取曲线数据必须明确顶深和底深。")
        return self


class ScopeInput(BaseModel):
    """专业工具的目标范围。

    每次调用都显式指定井、资料版本和测深范围（MD）；工具不读取或修改
    会话中的当前范围选择。深度字段单位为米（m）。
    """

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    well_id: str = Field(min_length=1, description="目标井标识，来自井资料。")
    dataset_revision: str = Field(min_length=1, description="目标资料版本，来自井资料。")
    top_depth_m: float = Field(description="目标井段顶深，MD，m。")
    bottom_depth_m: float = Field(description="目标井段底深，MD，m。")

class ProfessionalInput(ScopeInput):
    input_result_ids: list[str] = Field(default_factory=list, description="前置专业工具实际返回的 result_id 列表，用于核对结果归属、版本、范围及可用状态；没有前置结果时传空列表。不要自行编造 ID。")
    expected_parameter_revision: int | None = Field(default=None, ge=0, description="期望使用的处理参数修订号；提供时服务端校验该版本，省略时使用当前参数版本。该字段不是资料版本号。")


class IntervalResultInput(ScopeInput):
    result_id: str | None = Field(default=None, min_length=1, description="已有层段整理工具返回的结果 ID；提供时读取该版本，省略时查询资料中已有的层段结果。此查询不会启动处理。")
    layer_no: int | None = Field(default=None, ge=1, description="可选的原始层号筛选条件，必须大于等于 1；按已有结果中的层号筛选，不会因查询范围而重新编号。")


StepId = Literal['data_preparation', 'data_completeness', 'curve_quality', 'lithology_identification', 'petrophysical_evaluation', 'sw_and_fluid_identification', 'layer_classification', 'interval_merging', 'interpretation_validation', 'report_readiness_check']


class ProcessingParameterInput(ScopeInput):
    step_id: StepId = Field(description="要读取或修改参数、或要重跑的步骤 ID。只接受枚举值；参数按井、资料版本、井段和步骤分别保存。")


class UpdateProcessingParameterInput(ProcessingParameterInput):
    expected_revision: int = Field(ge=0, description="乐观并发校验用的参数修订号；填写 get_processing_parameters 返回的 revision。参数已被其他调用修改时，本次更新会被拒绝。")
    changes: dict[str, object] = Field(min_length=1, description="要更新的参数名到新值的映射，例如 {\"sampling_interval_m\": 0.2}。参数名、数据类型和单位必须与 get_processing_parameters 返回的定义一致；至少提供一项。")


class RerunStepInput(ProcessingParameterInput):
    expected_parameter_revision: int = Field(ge=0, description="本次重跑必须使用的参数修订号；填写读取或更新参数工具实际返回的 revision，过期时重跑会被拒绝。")
    input_result_ids: list[str] = Field(default_factory=list, description="本次重跑依赖的前置结果 ID 列表，必须来自实际工具返回。没有前置结果时传空列表；缺失或已过期的 ID 不能猜测或替换。")


INTERACTIVE_SCHEMAS = {
    'query_interval_results': IntervalResultInput,
    'get_processing_parameters': ProcessingParameterInput,
    'update_processing_parameters': UpdateProcessingParameterInput,
    'rerun_step': RerunStepInput,
}


class RevisionInput(BaseModel):
    """依赖当前会话范围选择的工具输入。

    与独立专业工具的显式井段参数不同，这类工具必须引用已存在的会话选择。
    """

    model_config = ConfigDict(extra="forbid")
    expected_selection_revision: int = Field(
        ge=1, description="服务端当前选择修订号。过期修订号会被拒绝。"
    )


class SelectionInput(BaseModel):
    """用户明确指定的当前会话井段范围；深度单位为米，基准为测深（MD）。"""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    top_depth_m: float = Field(description="选择顶深，单位 m，测深 MD。")
    bottom_depth_m: float = Field(description="选择底深，单位 m，测深 MD。")


class IntervalInput(RevisionInput):
    layer_no: int | None = Field(
        default=None, ge=1, description="要查询的原始样本层号，必须大于等于 1；省略时返回所选井段内全部相交层段。"
    )


class StatisticsInput(RevisionInput):
    curve_name: str = Field(default="GR", description="要统计的原始曲线名，例如 GR；省略时使用 GR。")


class SlowInput(StatisticsInput):
    """仅框架验证使用的耗时测试输入，不属于专业解释参数。"""

    delay_seconds: float = Field(default=10.5, ge=0, le=15, allow_inf_nan=False, description="模拟工具执行的等待秒数，范围 0 到 15 秒，默认 10.5 秒；只用于后台通知验证。")
    fail: bool = Field(
        default=False, description="预设测试失败。该参数只用于原型验证。"
    )
