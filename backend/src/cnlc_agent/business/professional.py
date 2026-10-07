"""可独立调用的专业业务能力与结果引用检查。"""

import math

from ..adapters.mock.workflow_tools import MockWorkflowTools
from ..catalog import PROFESSIONAL_TOOLS
from ..contracts.agent_tools import ProfessionalInput, WellDataInput
from .errors import BusinessError
from .settings import ProcessingSettings


TOOL_STEPS = {item.capability_id: item.steps[0] for item in PROFESSIONAL_TOOLS}
STEP_TITLES = {step: capability.name for capability in PROFESSIONAL_TOOLS for step in capability.steps}

RESULT_FIELDS = {
    "check_curve_quality": ("quality",),
    "identify_lithology": ("lithology",),
    "evaluate_petrophysics": ("vsh", "porosity", "permeability"),
    "calculate_sw": ("water_saturation",),
    "identify_fluid": ("fluid_type",),
    "classify_layer": ("layer_type",),
    "merge_intervals": ("intervals",),
    "validate_interpretation": ("summary",),
}


def _valid_result(tool_name, result):
    """验证实际会被消费的字段，异常响应不能成为可继续的成果。"""
    if not isinstance(result, dict) or any(result.get(field) is None for field in RESULT_FIELDS[tool_name]):
        return False
    if tool_name == "merge_intervals":
        rows = result["intervals"]
        if not isinstance(rows, list) or any(
            not isinstance(row, dict) or any(
                type(row.get(key)) not in {int, float} or not math.isfinite(row[key])
                for key in ("top_depth_m", "bottom_depth_m")
            ) for row in rows
        ):
            return False
    if "curve_data" in result:
        data = result["curve_data"]
        if not isinstance(data, dict) or not isinstance(data.get("depths"), list) or not isinstance(data.get("curves"), dict):
            return False
        if any(type(depth) not in {int, float} or not math.isfinite(depth) for depth in data["depths"]):
            return False
        if any(
            not isinstance(curve, dict) or not isinstance(curve.get("values"), list)
            or len(curve["values"]) != len(data["depths"])
            for curve in data["curves"].values()
        ):
            return False
    return True


class ProfessionalService:
    """使用现有资料适配器；完整流程顺序由 Skill 组织。"""

    def __init__(self, service):
        self.service = service
        self.well = service.well
        self.adapter = MockWorkflowTools(self.well)
        self.settings = ProcessingSettings(service)

    def _context(self, well_id, dataset_revision, top, bottom):
        well_id = self.well.well_id if well_id is None else well_id
        if well_id != self.well.well_id:
            raise BusinessError("WELL_NOT_FOUND", "井不存在。")
        if dataset_revision is not None and dataset_revision != self.well.revision:
            raise BusinessError("DATASET_VERSION_CONFLICT", "资料版本已变化，请重新读取井资料。")
        if top is not None:
            self.well.validate_range(well_id, top, bottom)
        return {
            "well_id": well_id, "dataset_revision": self.well.revision,
            "top_depth_m": top, "bottom_depth_m": bottom,
            "depth_reference": "MD", "depth_unit": "m",
        }

    def _inputs(self, context, result_ids):
        results = []
        for result_id in dict.fromkeys(result_ids):
            result = self.service.store.tool_result(self.service.owner, self.service.session, result_id)
            if result is None:
                raise BusinessError("RESULT_NOT_FOUND", "前置结果不存在或不属于当前会话。")
            if result['tool_name'] not in TOOL_STEPS:
                raise BusinessError('RESULT_TYPE_CONFLICT', '图表产物不能替代专业处理结果。')
            previous = result["context"]
            identity_matches = all(previous[k] == context[k] for k in ("well_id", "dataset_revision"))
            # 全井概要可支撑井段检查。其他结果必须匹配相同范围。
            summary = result["tool_name"] == "get_well_data" and previous["top_depth_m"] is None
            range_matches = all(previous[k] == context[k] for k in ("top_depth_m", "bottom_depth_m"))
            if not identity_matches or not (summary or range_matches):
                raise BusinessError("RESULT_CONTEXT_CONFLICT", "前置结果的井、资料版本或井段与本次操作不一致。")
            if result["status"] not in {"SUCCESS", "WARNING"}:
                raise BusinessError("DEPENDENCY_NOT_READY", "前置结果失败、阻断或需要复核，不能继续依赖该结果。")
            if not self.settings.result_is_current(result):
                raise BusinessError("STALE_RESULT", "前置结果采用的参数或依赖已过期，请指定必要步骤重新处理。")
            results.append(result)
        return results

    def _save(self, tool_name, context, output, *, status="SUCCESS", input_result_ids=(), source=None, fixture_scope=None, parameter_snapshot=None):
        payload = {
            "status": status, "tool_name": tool_name, "step_id": TOOL_STEPS[tool_name],
            "context": context, "output": output,
            "input_result_ids": list(input_result_ids),
            "can_continue": status in {"SUCCESS", "WARNING"},
            "source": source or output.get("source", "sample.requirements"),
            "is_mock": True,
            "parameter_snapshot": parameter_snapshot or self.settings.read(context, TOOL_STEPS[tool_name]),
        }
        if fixture_scope is not None:
            payload["fixture_scope"] = fixture_scope
            payload["scope_note"] = "曲线点及相交层段按请求井段筛选；预设汇总值仍来自完整样本，未按井段重算。"
        return self.service.store.save_tool_result(self.service.owner, self.service.session, payload)

    def get_well_data(self, request: WellDataInput):
        context = self._context(request.well_id, request.dataset_revision, request.top_depth_m, request.bottom_depth_m)
        output = self.well.summary()
        if request.curve_names is not None:
            curves = {}
            for name in dict.fromkeys(request.curve_names):
                curves.update(self.well.curves(request.top_depth_m, request.bottom_depth_m, name)["curves"])
            output["curve_data"] = {"depth_unit": "m", "depth_reference": "MD", "curves": curves}
        return self._save("get_well_data", context, output, source=output["source"])

    def execute(self, tool_name: str, request: ProfessionalInput):
        context = self._context(request.well_id, request.dataset_revision, request.top_depth_m, request.bottom_depth_m)
        inputs = self._inputs(context, request.input_result_ids)
        parameter_snapshot = self.settings.read(context, TOOL_STEPS[tool_name])
        self.settings.check_revision(parameter_snapshot, request.expected_parameter_revision)
        status = "SUCCESS"
        fixture_scope = None
        if tool_name == "check_data_completeness":
            requirements = self.well.data.get("requirements", {})
            required = list(requirements.get("required_curves", []))
            available = list(self.well.data["raw_data"]["curves"])
            missing = [name for name in required if name not in available]
            configured = bool(required)
            missing_data = [
                name for name in required if name in available
                and not any(
                    value is not None
                    for depth, value in zip(self.well.depths, self.well.data["raw_data"]["curves"][name]["values"], strict=True)
                    if request.top_depth_m <= depth <= request.bottom_depth_m
                )
            ]
            output = {
                "required_curves": required, "available_curves": available,
                "missing_curves": missing,
                "missing_data_curves": missing_data, "rules_configured": configured,
                "recommended_sources": requirements.get("recommended_sources", []),
                "rule_source": "sample.requirements", "is_general_rule": False,
            }
            status = "BLOCKED" if missing or missing_data or not configured else "SUCCESS"
        elif tool_name == "prepare_report":
            completed = {result["tool_name"] for result in inputs}
            warnings = [
                {"tool_name": result["tool_name"], "result_id": result["result_id"],
                 "source": result["source"], "output": result["output"]}
                for result in inputs if result["status"] == "WARNING"
            ]
            unresolved = list(dict.fromkeys(
                STEP_TITLES[step] for name, step in TOOL_STEPS.items()
                if name != "prepare_report" and name not in completed
            ))
            output = {
                "structural_check": "INCOMPLETE" if unresolved else "PASS",
                "unresolved_steps": unresolved,
                "completed_tools": sorted(completed),
                "warnings": warnings,
                "source": "tool_result_records",
                "note": "报告前结构检查不代表专业验收，也不生成报告正文。",
            }
            status = "BLOCKED" if unresolved else "WARNING" if warnings else "SUCCESS"
        else:
            tool_run = self.adapter.invoke(tool_name)
            output = tool_run["output"]
            fixture_scope = self._context(self.well.well_id, self.well.revision, self.well.depths[0], self.well.depths[-1])
            status = output.get("status", tool_run["status"])
            if status == "UNAVAILABLE":
                status = "BLOCKED"
            elif status not in {"SUCCESS", "WARNING", "FAILED", "BLOCKED", "REVIEW_REQUIRED", "UNKNOWN", "ERROR"}:
                status = "UNKNOWN"
            result = output.get("result")
            if status in {"SUCCESS", "WARNING"} and not _valid_result(tool_name, result):
                status = "BLOCKED"
                output["errors"] = [{"code": "INVALID_RESULT", "message": "工具未返回完整的业务结果。"}]
            if status in {"SUCCESS", "WARNING"} and tool_name == "validate_interpretation":
                validation = output.get("validation_status")
                if validation == "PARTIAL_CONFLICT":
                    status = "WARNING"
                elif validation != "CONSISTENT":
                    status = "REVIEW_REQUIRED"
            elif status in {"SUCCESS", "WARNING"} and tool_name == "check_curve_quality":
                quality = result["quality"]
                if quality in {"FAIL", "FAILED", "BLOCKED"}:
                    status = "BLOCKED"
                elif quality in {"WARN", "WARNING"}:
                    status = "WARNING"
                elif quality not in {"MOCK_PASS", "PASS", "SUCCESS"}:
                    status = "UNKNOWN"
            curve_data = result.get("curve_data") if status in {"SUCCESS", "WARNING"} else None
            if curve_data:
                indices = [i for i, depth in enumerate(curve_data["depths"]) if request.top_depth_m <= depth <= request.bottom_depth_m]
                curve_data["depths"] = [curve_data["depths"][i] for i in indices]
                for curve in curve_data["curves"].values():
                    curve["values"] = [curve["values"][i] for i in indices]
            if tool_name == "merge_intervals" and status in {"SUCCESS", "WARNING"}:
                output["result"]["intervals"] = [
                    row for row in output["result"]["intervals"]
                    if row["bottom_depth_m"] > request.top_depth_m
                    and row["top_depth_m"] < request.bottom_depth_m
                ]
        return self._save(
            tool_name, context, output, status=status,
            input_result_ids=request.input_result_ids, fixture_scope=fixture_scope,
            parameter_snapshot=parameter_snapshot,
        )
