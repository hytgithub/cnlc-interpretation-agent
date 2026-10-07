"""会话范围选择请求契约。"""

from pydantic import BaseModel, ConfigDict, Field


class SelectionRequest(BaseModel):
    # 页面或演示脚本提交的选择请求。Pydantic 根据字段类型检查请求体。
    # extra="forbid" 拒绝未定义字段。allow_inf_nan=False 拒绝非有限深度值。
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    well_id: str = "WELL_MOCK_PLOT_001"
    top_depth_m: float
    bottom_depth_m: float
    # expected_revision 是调用方最后读到的“选择修订号”，不是资料版本。
    # 首次选择提交 0。成功后变为 1。再次修改要提交 1，成功后变为 2。
    expected_revision: int = Field(ge=0)
