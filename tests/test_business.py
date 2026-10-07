"""业务层测试：直接检查资料、范围、统计值和持久化状态。

这里不启动 AgentScope，便于单独判断业务函数是否正确。
每个测试使用临时数据库，不修改用户运行服务时保存的数据。
"""

import asyncio

import pytest

from cnlc_agent.business import BusinessError, BusinessService, BusinessStore, MockWell, SelectionRequest


@pytest.fixture
def context(tmp_path):
    """每个用例建立样本井、临时存储和修订号为 1 的全井选择。"""
    well, store = MockWell(), BusinessStore(tmp_path / "business.sqlite3")
    store.set_selection("owner", "session", SelectionRequest(top_depth_m=2000, bottom_depth_m=2120, expected_revision=0), well)
    return well, store, BusinessService(store, well, "owner", "session")


def test_fixture_matches_business_material(context):
    """核对样本的业务约定，避免 Mock 资料与技术设计不一致。"""
    well, _, _ = context
    summary = well.summary()
    assert summary["well_id"] == "WELL_MOCK_PLOT_001"
    assert summary["sample_count"] == 1201
    assert len(summary["raw_curve_names"]) == 12
    assert summary["result_curve_count"] == 8
    assert summary["interval_count"] == 20
    assert summary["null_counts"]["GR"] == 4
    assert summary["null_counts"]["AC"] == 10
    # 还检查所有曲线长度与采样步长，不能只看概要中的点数。
    assert all(len(c["values"]) == 1201 for c in well.data["raw_data"]["curves"].values())
    assert all(round(b - a, 6) == .1 for a, b in zip(well.depths, well.depths[1:]))


@pytest.mark.parametrize("top,bottom,code", [(1999, 2100, "OUT_OF_RANGE"), (2000, 2121, "OUT_OF_RANGE"),
                                           (2010, 2000, "INVALID_RANGE"), (2000, 2000, "INVALID_RANGE")])
def test_selection_rejects_invalid_range_without_update(context, top, bottom, code):
    """四组参数分别检查顶深越界、底深越界、逆序范围和零长度范围。"""
    well, store, _ = context
    with pytest.raises(BusinessError) as exc:
        store.set_selection("owner", "session", SelectionRequest(top_depth_m=top, bottom_depth_m=bottom, expected_revision=1), well)
    assert exc.value.code == code
    # 拒绝之后仍保留旧选择，不能生成新修订号。
    assert store.selection("owner", "session")["revision"] == 1


def test_stale_selection_is_rejected_at_write_and_tool_execution(context):
    """先把选择变为修订号 2，再分别用旧修订号修改选择和执行统计。"""
    well, store, service = context
    request = SelectionRequest(top_depth_m=2001, bottom_depth_m=2002, expected_revision=1)
    store.set_selection("owner", "session", request, well)
    for operation in [lambda: store.set_selection("owner", "session", request, well), lambda: service.statistics(1)]:
        with pytest.raises(BusinessError) as exc:
            operation()
        assert exc.value.code == "STALE_SELECTION"


def test_interval_query_preserves_mock_boundaries(context):
    """窄范围查询仍返回完整原始层段，并区分层号不存在与层段不在范围内。"""
    well, store, service = context
    store.set_selection("owner", "session", SelectionRequest(top_depth_m=2001, bottom_depth_m=2002, expected_revision=1), well)
    result = service.query(2, 1)
    assert result["is_mock"] is True
    assert result["intervals"][0]["top_depth_m"] == 2000
    assert result["intervals"][0]["bottom_depth_m"] == 2004.2
    with pytest.raises(BusinessError, match="不存在") as exc:
        service.query(2, 999)
    assert exc.value.code == "INTERVAL_NOT_FOUND"
    with pytest.raises(BusinessError) as exc:
        service.query(2, 20)
    assert exc.value.code == "INTERVAL_OUTSIDE_SELECTION"


def test_statistics_computes_data_and_excludes_nulls(context):
    """独立计算参考均值，并检查空值、双端包含和未知曲线拒绝。"""
    well, store, service = context
    result = service.statistics(1, "GR")
    # 用 sum/len 得出参考值，核对业务函数的 fmean 结果。
    values = [v for v in well.data["raw_data"]["curves"]["GR"]["values"] if v is not None]
    assert result["sample_count"] == 1201
    assert result["valid_count"] == 1197
    assert result["null_count"] == 4
    assert result["mean"] == pytest.approx(sum(values) / len(values))
    store.set_selection("owner", "session", SelectionRequest(top_depth_m=2000, bottom_depth_m=2001, expected_revision=1), well)
    # 2000～2001 m 每 0.1 m 一点，包含两端时应有 11 点。
    assert service.statistics(2)["sample_count"] == 11
    with pytest.raises(BusinessError) as exc:
        service.statistics(2, "NOT_A_CURVE")
    assert exc.value.code == "CURVE_NOT_FOUND"


def test_business_context_is_owner_and_session_scoped(context):
    """只有相同 owner/session 组合能读取已保存的选择。"""
    _, store, _ = context
    assert store.selection("other", "session") is None
    assert store.selection("owner", "other") is None
    with pytest.raises(BusinessError) as exc:
        store.require_selection("other", "session", 1)
    assert exc.value.code == "SELECTION_REQUIRED"


def test_dataset_version_change_does_not_reuse_old_selection(context):
    """模拟资料标识变化，检查旧选择不会被用于新资料。"""
    well, _, service = context
    well.revision = "another-dataset-version"
    with pytest.raises(BusinessError) as exc:
        service.statistics(1)
    assert exc.value.code == "DATASET_VERSION_CONFLICT"


async def test_failure_preserves_previous_success(context):
    """先成功、再预设失败，检查两次记录并存且旧成功结果不被覆盖。"""
    _, store, service = context
    success = await service.slow_statistics(1, delay_seconds=0)
    failed = await service.slow_statistics(1, delay_seconds=0, fail=True)
    assert success["status"] == "SUCCEEDED"
    assert failed["status"] == "FAILED"
    runs = store.runs("owner", "session")
    assert runs[0]["result"] == success["result"]
    assert runs[1]["error"]["code"] == "MOCK_FAILURE"
    assert store.runs("other", "session") == []


async def test_local_cancellation_is_unknown_not_external_cancel(context):
    """取消本地等待协程，检查保存 UNKNOWN 而不是宣称外部作业已取消。"""
    _, store, service = context
    task = asyncio.create_task(service.slow_statistics(1, delay_seconds=1))
    # 让出一次执行权，确保工具进入等待且 RUNNING 已写入数据库。
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert store.runs("owner", "session")[0]["status"] == "UNKNOWN"


def test_restart_keeps_selection_and_marks_lost_work_unknown(context):
    """复用同一数据库模拟恢复，保留选择并把遗留运行标为 UNKNOWN。"""
    _, store, _ = context
    run = store.start_run("owner", "session", "slow_mock_statistics", store.selection("owner", "session"))
    restarted = BusinessStore(store.path)
    assert restarted.recover_unfinished() == 1
    assert restarted.selection("owner", "session")["revision"] == 1
    recovered = restarted.runs("owner", "session")[0]
    assert recovered["run_id"] == run["run_id"]
    assert recovered["status"] == "UNKNOWN"
    # 第二次恢复不应再次处理已标记的运行。
    assert restarted.recover_unfinished() == 0
