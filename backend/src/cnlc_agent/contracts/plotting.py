"""曲线显示契约；显示选项不会修改专业输入。"""
from typing import Annotated

from pydantic import Field, model_validator

from .agent_tools import ScopeInput

CurveName = Annotated[str, Field(min_length=1, pattern=r'\S')]


class CurvePlotInput(ScopeInput):
    curve_names: list[CurveName] = Field(min_length=1, max_length=8, description='要绘制的实际曲线名，每条曲线单独一轨，最多8条。')
    result_id: str | None = Field(default=None, min_length=1, description='已有工具结果引用。省略时绘制原始资料；提供时只读取该结果中的曲线。')
    log_curve_names: list[CurveName] = Field(default_factory=list, max_length=8, description='使用对数横轴的曲线名，必须属于curve_names；其他曲线使用线性横轴。')

    @model_validator(mode='after')
    def check_log_names(self):
        if not set(self.log_curve_names) <= set(self.curve_names):
            raise ValueError('对数轴曲线必须属于本次绘制的曲线。')
        return self
