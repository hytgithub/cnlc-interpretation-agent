"""保护职责拆分前后的流程终态、产物绑定与会话隔离。"""

import pytest
from cnlc_agent.business import BusinessStore, MockWell, SelectionRequest
from cnlc_agent.workflow import MockWorkflow, WorkflowStore


@pytest.fixture
def workflow_context(tmp_path):
    well = MockWell()
    business = BusinessStore(tmp_path / "business.sqlite3")
    selection = business.set_selection(
        "owner",
        "session",
        SelectionRequest(top_depth_m=2000, bottom_depth_m=2120, expected_revision=0),
        well,
    )
    store = WorkflowStore(business)
    return MockWorkflow(store, well), store, selection


@pytest.mark.parametrize(
    "scenario,status,last_step,report_type",
    [
        ("baseline", "SUCCESS", "report_readiness_check", "DEMO"),
        ("recommended_missing", "WARNING", "report_readiness_check", "DEMO"),
        ("required_missing", "BLOCKED", "data_completeness", "DIAGNOSTIC"),
        ("tool_failure", "FAILED", "lithology_identification", "DIAGNOSTIC"),
        ("provider_unknown", "BLOCKED", "lithology_identification", "DIAGNOSTIC"),
        ("serious_conflict", "REVIEW_REQUIRED", "interpretation_validation", "DIAGNOSTIC"),
        ("insufficient_evidence", "REVIEW_REQUIRED", "interpretation_validation", "DIAGNOSTIC"),
    ],
)
def test_scenario_stops_at_gate_and_binds_report(
    workflow_context, scenario, status, last_step, report_type
):
    workflow, store, selection = workflow_context
    run = workflow.start("owner", "session", selection, scenario)
    saved = store.get_run("owner", "session", run["run_id"])
    assert saved["status"] == status
    assert saved["steps"][-1]["step_id"] == last_step
    assert saved["report"]["report_type"] == report_type
    assert saved["report"]["run_id"] == run["run_id"]
    assert saved["report"]["result_revision_id"] == saved["result_revision_id"]
    assert "样本预设输出" in saved["report"]["content"]
    assert saved["provider_calls"] == []
    results = store.list_results("owner", "session")
    if report_type == "DEMO":
        assert len(results) == 1
        assert results[0]["result_revision_id"] == saved["result_revision_id"]
    else:
        assert results == []
        assert saved["result_revision_id"] is None


def test_diagnostic_run_preserves_previous_result_and_owner(workflow_context):
    workflow, store, selection = workflow_context
    success = workflow.start("owner", "session", selection, "baseline")
    workflow.start("owner", "session", selection, "tool_failure")
    results = store.list_results("owner", "session")
    assert len(results) == 1
    assert results[0]["result_revision_id"] == success["result_revision_id"]
    for owner, session in [("other", "session"), ("owner", "other")]:
        assert store.get_run(owner, session, success["run_id"]) is None
        assert store.get_result(owner, session, success["result_revision_id"]) is None
        assert store.get_report(owner, session, success["report_revision_id"]) is None
        assert store.list_results(owner, session) == []
