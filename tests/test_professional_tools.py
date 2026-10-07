"""独立专业工具的参数、结果归属与报告前检查。"""

import json

import pytest

from cnlc_agent.agent.tools import make_tools
from cnlc_agent.business import BusinessService, BusinessStore, MockWell


PROFESSIONAL_TOOLS = (
    "get_well_data", "check_data_completeness", "check_curve_quality",
    "identify_lithology", "evaluate_petrophysics", "calculate_sw",
    "identify_fluid", "classify_layer", "merge_intervals",
    "validate_interpretation", "prepare_report",
)


@pytest.fixture
def context(tmp_path):
    well = MockWell()
    store = BusinessStore(tmp_path / "business.sqlite3")
    service = BusinessService(store, well, "owner", "session")
    arguments = {
        "well_id": well.well_id, "dataset_revision": well.revision,
        "top_depth_m": 2000, "bottom_depth_m": 2001,
    }
    return well, store, service, arguments


async def call(service, name, **arguments):
    tool = next((t for t in make_tools(service, include_test_tools=False) if t.name == name), None)
    assert tool is not None, f"专业工具未开放：{name}"
    result = await tool.call(**arguments)
    return json.loads(result.content[0].text)


async def test_well_data_query_needs_no_selection_and_returns_requested_raw_points(context):
    _, store, service, scope = context
    result = await call(service, "get_well_data", **scope, curve_names=["GR"])
    assert result["status"] == "SUCCESS"
    assert result["output"]["well_id"] == "WELL_MOCK_PLOT_001"
    points = result["output"]["curve_data"]["curves"]["GR"]["points"]
    assert len(points) == 11
    assert points[0]["depth_m"] == 2000
    assert points[-1]["depth_m"] == 2001
    assert store.selection("owner", "session") is None
    assert store.runs("owner", "session") == []


@pytest.mark.parametrize("name", PROFESSIONAL_TOOLS[1:-1])
async def test_each_professional_tool_is_independently_callable(context, name):
    _, store, service, scope = context
    result = await call(service, name, **scope)
    assert result["status"] == "SUCCESS"
    assert result["context"]["top_depth_m"] == 2000
    assert result["context"]["bottom_depth_m"] == 2001
    assert result["result_id"]
    assert store.runs("owner", "session") == []
    if name == "merge_intervals":
        assert [row["layer_no"] for row in result["output"]["result"]["intervals"]] == [1]
        assert result["output"]["result"]["intervals"][0]["bottom_depth_m"] == 2004.2
    if name in {"identify_lithology", "evaluate_petrophysics", "calculate_sw"}:
        assert result["output"]["result"]["curve_data"]["depths"] == [2000 + i / 10 for i in range(11)]
        assert result["fixture_scope"]["bottom_depth_m"] == 2120


@pytest.mark.parametrize("override,code", [
    ({"well_id": "OTHER_WELL"}, "WELL_NOT_FOUND"),
    ({"dataset_revision": "stale"}, "DATASET_VERSION_CONFLICT"),
    ({"bottom_depth_m": 2121}, "OUT_OF_RANGE"),
    ({"bottom_depth_m": 2000}, "INVALID_RANGE"),
])
async def test_direct_tools_reject_wrong_object_version_or_range(context, override, code):
    _, _, service, scope = context
    result = await call(service, "identify_lithology", **{**scope, **override})
    assert result["status"] == "ERROR"
    assert result["code"] == code


async def test_completeness_check_reports_missing_required_curve(context):
    well, _, service, scope = context
    del well.data["raw_data"]["curves"]["RT"]
    result = await call(service, "check_data_completeness", **scope)
    assert result["status"] == "BLOCKED"
    assert result["output"]["missing_curves"] == ["RT"]


@pytest.mark.parametrize("name,key", [
    ("identify_lithology", "lithology"), ("merge_intervals", "intervals"),
    ("check_curve_quality", "qc"),
])
async def test_missing_fixture_is_blocked_instead_of_claiming_success(context, name, key):
    well, _, service, scope = context
    del well.data["outputs"][key]
    result = await call(service, name, **scope)
    assert result["status"] == "BLOCKED"


async def test_unconfigured_completeness_rules_do_not_pass(context):
    well, _, service, scope = context
    del well.data["requirements"]
    result = await call(service, "check_data_completeness", **scope)
    assert result["status"] == "BLOCKED"
    assert result["output"]["rules_configured"] is False


async def test_required_curve_with_no_values_in_scope_does_not_pass(context):
    well, _, service, scope = context
    well.data["raw_data"]["curves"]["RT"]["values"] = [None] * 1201
    result = await call(service, "check_data_completeness", **scope)
    assert result["status"] == "BLOCKED"
    assert result["output"]["missing_data_curves"] == ["RT"]


async def test_partial_validation_conflict_returns_warning(context):
    well, _, service, scope = context
    well.data["validation"]["validation_status"] = "PARTIAL_CONFLICT"
    result = await call(service, "validate_interpretation", **scope)
    assert result["status"] == "WARNING"


@pytest.mark.parametrize("status", ["FAILED", "BLOCKED", "UNKNOWN", "WARNING"])
async def test_fixture_business_status_is_not_overwritten_by_tool_success(context, status):
    well, _, service, scope = context
    well.data["outputs"]["lithology"]["status"] = status
    result = await call(service, "identify_lithology", **scope)
    assert result["status"] == status


async def test_validation_conflict_requires_review_and_cannot_feed_report(context):
    well, _, service, scope = context
    well.data["validation"]["validation_status"] = "SERIOUS_CONFLICT"
    result = await call(service, "validate_interpretation", **scope)
    assert result["status"] == "REVIEW_REQUIRED"
    checked = await call(service, "prepare_report", **scope, input_result_ids=[result["result_id"]])
    assert checked["status"] == "ERROR"
    assert checked["code"] == "DEPENDENCY_NOT_READY"


async def test_result_references_reject_other_owner_session_and_range(context):
    well, store, service, scope = context
    first = await call(service, "identify_lithology", **scope)
    for owner, session in [("other", "session"), ("owner", "other")]:
        other = BusinessService(store, well, owner, session)
        rejected = await call(other, "evaluate_petrophysics", **scope, input_result_ids=[first["result_id"]])
        assert rejected["code"] == "RESULT_NOT_FOUND"
    rejected = await call(service, "evaluate_petrophysics", **{**scope, "bottom_depth_m": 2002}, input_result_ids=[first["result_id"]])
    assert rejected["code"] == "RESULT_CONTEXT_CONFLICT"


@pytest.mark.parametrize("validation,expected_status", [("CONSISTENT", "SUCCESS"), ("PARTIAL_CONFLICT", "WARNING")])
async def test_report_check_requires_all_actual_results_and_survives_restart(context, validation, expected_status):
    well, store, service, scope = context
    well.data["validation"]["validation_status"] = validation
    empty = await call(service, "prepare_report", **scope)
    assert empty["status"] == "BLOCKED"
    assert "读取井资料" in empty["output"]["unresolved_steps"]
    ids = []
    for name in PROFESSIONAL_TOOLS[:-1]:
        result = await call(service, name, **scope, input_result_ids=ids) if name != "get_well_data" else await call(service, name, **scope)
        assert result["status"] in {"SUCCESS", "WARNING"}
        ids.append(result["result_id"])
    restarted = BusinessService(BusinessStore(store.path), well, "owner", "session")
    checked = await call(restarted, "prepare_report", **scope, input_result_ids=ids)
    assert checked["status"] == expected_status
    assert checked["output"]["structural_check"] == "PASS"
    assert checked["output"]["unresolved_steps"] == []
    assert checked["input_result_ids"] == ids
    if expected_status == "WARNING":
        assert checked["output"]["warnings"][0]["tool_name"] == "validate_interpretation"


async def test_well_summary_reference_can_support_narrow_scope(context):
    _, _, service, scope = context
    summary = await call(service, "get_well_data")
    result = await call(service, "check_data_completeness", **scope, input_result_ids=[summary["result_id"]])
    assert result["status"] == "SUCCESS"


@pytest.mark.parametrize("curve_name", ["", " "])
async def test_blank_curve_names_do_not_expand_to_all_curves(context, curve_name):
    _, _, service, scope = context
    result = await call(service, "get_well_data", **scope, curve_names=[curve_name])
    assert result["status"] == "ERROR"
    assert result["code"] == "INVALID_INPUT"


async def test_well_overview_does_not_depend_on_derived_interval_fixture(context):
    well, _, service, _ = context
    del well.data["outputs"]["intervals"]
    result = await call(service, "get_well_data")
    assert result["status"] == "SUCCESS"
    assert result["output"]["sample_count"] == 1201
    assert result["output"]["interval_count"] is None


@pytest.mark.parametrize("name,key,fixture", [
    ("identify_lithology", "lithology", {}),
    ("identify_lithology", "lithology", {"result": None}),
    ("identify_lithology", "lithology", {"result": {}}),
    ("check_curve_quality", "qc", {"result": None}),
    ("check_curve_quality", "qc", {"result": {"quality": "UNKNOWN"}}),
    ("merge_intervals", "intervals", {"result": {}}),
    ("merge_intervals", "intervals", {"result": {"intervals": None}}),
    ("merge_intervals", "intervals", {"result": {"intervals": "invalid"}}),
    ("merge_intervals", "intervals", {"result": {"intervals": [{}]}}),
    ("identify_lithology", "lithology", {"result": {"lithology": "砂岩", "curve_data": {"depths": [2000], "curves": {"SAND": {"values": []}}}}}),
])
async def test_invalid_fixtures_are_unusable_and_do_not_raise(context, name, key, fixture):
    well, _, service, scope = context
    well.data["outputs"][key] = fixture
    result = await call(service, name, **scope)
    assert result["status"] in {"BLOCKED", "UNKNOWN"}
    assert result["can_continue"] is False
    checked = await call(service, "prepare_report", **scope, input_result_ids=[result["result_id"]])
    assert checked["code"] == "DEPENDENCY_NOT_READY"
