"""固定流程编排、门控与产物关联。"""

from uuid import uuid4

from ..adapters.mock.well import MockWell
from ..adapters.mock.workflow_tools import MockWorkflowTools
from ..business.errors import BusinessError
from ..reports.renderer import render_report
from ..repositories.workflow import WorkflowStore
from ..timestamps import utc_now
from .definition import SCENARIOS, STEPS


class MockWorkflow:
    """执行固定十项处理的 Mock 演示流程；专业输出直接注明来自样本预设结果。"""

    def __init__(self, store: WorkflowStore, well: MockWell):
        self.store, self.well = store, well
        self.tools = MockWorkflowTools(well)

    def start(
        self, owner: str, session: str, selection: dict, scenario_id: str
    ) -> dict:
        """建立持久运行和十项步骤的等待记录。"""
        if scenario_id not in SCENARIOS:
            raise BusinessError("SCENARIO_NOT_CONFIGURED", "演示场景未配置。")
        run = {
            "run_id": str(uuid4()),
            "owner": owner,
            "session_id": session,
            "well_id": selection["well_id"],
            "dataset_revision": selection["dataset_revision"],
            "selection": selection,
            "scenario_id": scenario_id,
            "scenario_name": SCENARIOS[scenario_id],
            "status": "RUNNING",
            "source": "MOCK",
            "is_mock": True,
            "created_at": utc_now(),
            "finished_at": None,
        }
        self.store.insert_run(run)
        outputs: dict = {}
        status = "SUCCESS"
        message = "Mock 演示流程已执行。"

        for sequence, (step_id, title, stage_id) in enumerate(STEPS, start=1):
            step = {
                "step_id": step_id,
                "title": title,
                "stage_id": stage_id,
                "status": "RUNNING",
                "started_at": utc_now(),
                "source": "MOCK",
                "logical_tool_calls": [],
                "tool_runs": [],
                "component_calls": [],
                "output": None,
                "warnings": [],
                "errors": [],
            }
            self.store.save_step(run["run_id"], sequence, step)

            if step_id == "data_preparation":
                tool_run = self.tools.invoke("get_well_data")
                step["tool_runs"].append(tool_run)
                step["output"] = tool_run["output"]
                outputs["well"] = step["output"]
                step["logical_tool_calls"] = ["get_well_data"]
            elif step_id == "data_completeness":
                step["component_calls"] = ["data_requirements"]
                requirements = self.well.data.get("requirements", {})
                required = list(requirements.get("required_curves", []))
                available = list(self.well.data["raw_data"]["curves"].keys())
                if scenario_id == "required_missing" and required:
                    available.remove(required[0])
                missing = [name for name in required if name not in available]
                if missing:
                    step.update(
                        status="BLOCKED",
                        errors=[
                            {
                                "code": "REQUIRED_DATA_MISSING",
                                "message": "Mock 场景移除必需曲线："
                                + ", ".join(missing),
                            }
                        ],
                        output={
                            "required_curves": required,
                            "available_curves": available,
                            "missing_curves": missing,
                            "rule_source": "sample.requirements",
                            "is_general_rule": False,
                        },
                    )
                    status, message = "BLOCKED", "必需资料缺失，流程已阻断。"
                    outputs["requirements"] = step["output"]
                else:
                    warnings = (
                        [
                            {
                                "code": "RECOMMENDED_DATA_MISSING",
                                "message": "Mock 场景模拟推荐资料缺失。",
                            }
                        ]
                        if scenario_id == "recommended_missing"
                        else []
                    )
                    step.update(
                        status="WARNING" if warnings else "SUCCESS",
                        warnings=warnings,
                        output={
                            "required_curves": required,
                            "available_curves": available,
                            "missing_curves": [],
                            "recommended_sources": requirements.get(
                                "recommended_sources", []
                            ),
                            "missing_recommended_sources": ["core"] if warnings else [],
                            "rule_source": "sample.requirements",
                            "is_general_rule": False,
                        },
                    )
                    outputs["requirements"] = step["output"]
            elif step_id == "curve_quality":
                tool_run = self.tools.invoke("check_curve_quality")
                step["tool_runs"].append(tool_run)
                step["output"] = tool_run["output"]
                outputs["qc"] = step["output"]
                step["logical_tool_calls"] = ["check_curve_quality"]
            elif step_id in {"lithology_identification", "petrophysical_evaluation", "sw_and_fluid_identification", "layer_classification", "interval_merging", "interpretation_validation"}:
                if step_id == "lithology_identification" and scenario_id == "tool_failure":
                    step["tool_runs"].append(
                        self.tools.failed(
                            "identify_lithology",
                            "MOCK_TOOL_FAILURE",
                            "预设 lithology_identification 工具失败场景。",
                        )
                    )
                    step.update(
                        status="FAILED",
                        errors=[
                            {
                                "code": "MOCK_TOOL_FAILURE",
                                "message": "预设 lithology_identification 工具失败场景。",
                            }
                        ],
                    )
                    step["logical_tool_calls"] = ["identify_lithology"]
                    status, message = "FAILED", "Mock 工具失败，流程已停止。"
                elif step_id == "lithology_identification" and scenario_id == "provider_unknown":
                    step["tool_runs"].append(
                        {
                            "tool_code": "company_interpretation",
                            "execution_mode": "MOCK",
                            "status": "UNKNOWN",
                            "source": "configured_unknown_scenario",
                            "is_mock": True,
                            "is_physical_call": False,
                            "error": {
                                "code": "PROVIDER_UNKNOWN",
                                "message": "模拟外部结果未知；没有真实 Provider 请求。",
                            },
                        }
                    )
                    step.update(
                        status="BLOCKED",
                        errors=[
                            {
                                "code": "PROVIDER_UNKNOWN",
                                "message": "结果未知，不重试，也不显示为成功。",
                            }
                        ],
                    )
                    step["logical_tool_calls"] = ["identify_lithology"]
                    status, message = (
                        "BLOCKED",
                        "Mock 场景模拟外部结果未知，流程已停止且没有重试。",
                    )
                    run["provider_simulations"] = [
                        {
                            "operation": "company_interpretation",
                            "status": "UNKNOWN",
                            "is_mock": True,
                            "is_physical_call": False,
                        }
                    ]
                else:
                    names = {
                        "lithology_identification": ("lithology", ("identify_lithology",)),
                        "petrophysical_evaluation": ("petrophysics", ("evaluate_petrophysics",)),
                        "sw_and_fluid_identification": ("sw", ("calculate_sw", "identify_fluid")),
                        "layer_classification": ("classification", ("classify_layer",)),
                        "interval_merging": ("intervals", ("merge_intervals",)),
                        "interpretation_validation": ("validation", ("validate_interpretation",)),
                    }
                    key, calls = names[step_id]
                    step["logical_tool_calls"] = calls
                    results = {name: self.tools.invoke(name) for name in calls}
                    step["tool_runs"] = list(results.values())
                    data = results[calls[0]]["output"]
                    if step_id == "sw_and_fluid_identification":
                        data["fluid"] = results["identify_fluid"]["output"]
                    if step_id == "interpretation_validation":
                        validation_status = {
                            "serious_conflict": "SERIOUS_CONFLICT",
                            "insufficient_evidence": "INSUFFICIENT_EVIDENCE",
                        }.get(
                            scenario_id,
                            data.get("validation_status", "INSUFFICIENT_EVIDENCE"),
                        )
                        data["validation_status"] = validation_status
                        if validation_status in {
                            "SERIOUS_CONFLICT",
                            "INSUFFICIENT_EVIDENCE",
                        }:
                            step.update(
                                status="REVIEW_REQUIRED",
                                warnings=[
                                    {
                                        "code": validation_status,
                                        "message": "Mock 验证要求专业复核；此状态不表示解释错误。",
                                    }
                                ],
                            )
                            status, message = (
                                "REVIEW_REQUIRED",
                                "验证结果需要专业复核，未继续报告前检查。",
                            )
                    step["output"] = data
                    outputs[key] = data
            elif step_id == "report_readiness_check":
                step["component_calls"] = ["final_structure_check"]
                issues = [
                    item["title"]
                    for item in self._steps_so_far(run["run_id"])
                    if item["step_id"] != "report_readiness_check"
                    and item["status"] not in {"SUCCESS", "WARNING"}
                ]
                step["logical_tool_calls"] = ["prepare_report"]
                tool_run = self.tools.invoke("prepare_report", unresolved_steps=issues)
                step["tool_runs"] = [tool_run]
                step["output"] = tool_run["output"]
                if issues:
                    step.update(
                        status="BLOCKED",
                        errors=[
                            {"code": "STEP_INCOMPLETE", "message": "存在未完成步骤。"}
                        ],
                    )
                    status, message = "BLOCKED", "存在未完成步骤，未生成演示结果版本。"

            if step["status"] == "RUNNING":
                step["status"] = "SUCCESS"
            step["finished_at"] = utc_now()
            self.store.save_step(run["run_id"], sequence, step)
            if step["status"] in {"FAILED", "BLOCKED", "REVIEW_REQUIRED"}:
                break

        steps = self._steps_so_far(run["run_id"])
        if status == "SUCCESS" and any(step["status"] == "WARNING" for step in steps):
            status = "WARNING"
        run.update(
            status=status, message=message, finished_at=utc_now(), outputs=outputs
        )
        result_revision = None
        if status in {"SUCCESS", "WARNING"}:
            result_revision = self.store.save_result(
                owner,
                session,
                run["run_id"],
                {
                    "well_id": run["well_id"],
                    "dataset_revision": run["dataset_revision"],
                    "scenario_id": scenario_id,
                    "status": status,
                    "outputs": outputs,
                    "source_note": "专业输出来自样本预设 Fixture；不是实时算法结果。",
                },
            )
        report_type = "DEMO" if status in {"SUCCESS", "WARNING"} else "DIAGNOSTIC"
        report = self.store.save_report(
            owner,
            session,
            run["run_id"],
            report_type,
            self._render_report(run, steps, result_revision),
            result_revision["result_revision_id"] if result_revision else None,
        )
        run["report_components"] = ["ReportAssembler"]
        run["result_revision_id"] = (
            result_revision["result_revision_id"] if result_revision else None
        )
        run["report_revision_id"] = report["report_revision_id"]
        run["stages"] = self.store.stage_summary(steps)
        run["stages"][-1].update(status="SUCCESS", total_steps=1, completed_steps=1)
        self.store.update_run(run)
        run["steps"] = steps
        run["result_revision"] = result_revision
        run["report"] = report
        return run

    def _steps_so_far(self, run_id: str) -> list[dict]:
        return self.store.list_steps(run_id)

    _render_report = staticmethod(render_report)
