"""将内部专业工具映射到 Mock Fixture 输出。"""

import json

from ...business.errors import BusinessError
from .well import MockWell


class MockWorkflowTools:
    """Workflow 内部业务工具适配器；不实现 AgentScope ToolBase，也不调用 Provider。"""

    FIXTURES = {
        "check_curve_quality": "qc",
        "identify_lithology": "lithology",
        "evaluate_petrophysics": "petrophysics",
        "calculate_sw": "sw",
        "identify_fluid": "fluid",
        "classify_layer": "classification",
        "merge_intervals": "intervals",
        "validate_interpretation": "validation",
    }

    def __init__(self, well: MockWell):
        self.well = well

    def invoke(
        self, tool_code: str, *, unresolved_steps: list[str] | None = None
    ) -> dict:
        """按稳定的内部业务工具名称读取对应样本 Fixture 并保存来源。"""
        if tool_code == "get_well_data":
            output = self.well.summary()
            source = "mock_well_manifest"
        elif tool_code == "prepare_report":
            unresolved = unresolved_steps or []
            output = {
                "structural_check": "PASS" if not unresolved else "INCOMPLETE",
                "unresolved_steps": unresolved,
                "note": "结构检查通过不代表专业解释结果已验收。",
            }
            source = "workflow_step_records"
        elif tool_code in self.FIXTURES:
            key = self.FIXTURES[tool_code]
            output = self._fixture_output(key)
            source = output.get("source", "sample_fixture:" + key)
        else:
            raise BusinessError(
                "WORKFLOW_TOOL_NOT_FOUND", "Workflow 内部业务工具未登记：" + tool_code
            )
        return {
            "tool_code": tool_code,
            "execution_mode": "MOCK",
            "status": "SUCCESS",
            "source": source,
            "is_mock": True,
            "provider_batch_id": None,
            "output": output,
        }

    def failed(self, tool_code: str, code: str, message: str) -> dict:
        """返回可追踪的预设工具失败，不修改 Fixture 或历史结果。"""
        return {
            "tool_code": tool_code,
            "execution_mode": "MOCK",
            "status": "FAILED",
            "source": "configured_failure_scenario",
            "is_mock": True,
            "provider_batch_id": None,
            "error": {"code": code, "message": message},
        }

    def _fixture_output(self, key: str) -> dict:
        """取出一项样本预设输出并复制，避免调用方修改共享样本对象。"""
        raw = self.well.data.get("outputs", {}).get(key)
        if raw is None and key == "validation":
            raw = self.well.data.get("validation")
        if raw is None:
            return {
                "status": "UNAVAILABLE",
                "is_mock": True,
                "source": "missing_fixture",
                "result": None,
            }
        return json.loads(json.dumps(raw, ensure_ascii=False))
