"""解释提交及结果比较请求契约。"""

from pydantic import BaseModel, ConfigDict, Field


class WorkflowRequest(BaseModel):
    """工作台或智能体提交的固定 Mock 场景请求。"""

    model_config = ConfigDict(extra="forbid")
    expected_selection_revision: int = Field(ge=1)
    scenario_id: str = "baseline"


class ComparisonRequest(BaseModel):
    """比较同一会话内两个已保存的结果版本。"""

    model_config = ConfigDict(extra="forbid")
    left_result_revision_id: str
    right_result_revision_id: str
