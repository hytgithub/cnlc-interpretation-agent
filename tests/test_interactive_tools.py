"""查询不计算，设置版本可追溯，单步重跑保留历史。"""
import json

import pytest

from cnlc_agent.agent.tools import make_tools
from cnlc_agent.business import BusinessService, BusinessStore, MockWell


@pytest.fixture
def context(tmp_path):
    well = MockWell()
    store = BusinessStore(tmp_path / 'business.sqlite3')
    service = BusinessService(store, well, 'owner', 'session')
    scope = dict(well_id=well.well_id, dataset_revision=well.revision,
                 top_depth_m=2000, bottom_depth_m=2001)
    return well, store, service, scope


async def call(service, name, **arguments):
    tool = next((t for t in make_tools(service) if t.name == name), None)
    assert tool is not None, f'缺少交互工具：{name}'
    response = await tool.call(**arguments)
    return json.loads(response.content[0].text)


async def test_query_existing_intervals_does_not_create_processing_result(context):
    _, store, service, scope = context
    result = await call(service, 'query_interval_results', **scope, layer_no=1)
    assert result['status'] == 'SUCCESS'
    assert result['output']['intervals'][0]['bottom_depth_m'] == 2004.2
    with store.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM tool_results').fetchone()[0] == 0
    assert store.selection('owner', 'session') is None


async def test_query_saved_interval_version_keeps_original_result(context):
    well, store, service, scope = context
    original = await call(service, 'merge_intervals', **scope)
    well.data['outputs']['intervals']['result']['intervals'] = []
    result = await call(service, 'query_interval_results', **scope, result_id=original['result_id'])
    assert result['result_id'] == original['result_id']
    assert result['output']['intervals'][0]['layer_no'] == 1
    assert store.tool_result('owner', 'session', original['result_id']) == original
    foreign = BusinessService(store, well, 'other', 'session')
    rejected = await call(foreign, 'query_interval_results', **scope, result_id=original['result_id'])
    assert rejected['code'] == 'RESULT_NOT_FOUND'


async def test_parameter_update_and_rerun_use_persisted_snapshot_and_keep_history(context):
    well, store, service, scope = context
    params = await call(service, 'get_processing_parameters', **scope, step_id='curve_quality')
    assert params['parameters']['sampling_interval_m'] == 0.1
    old = await call(service, 'check_curve_quality', **scope)
    changed = await call(service, 'update_processing_parameters', **scope, step_id='curve_quality',
                         expected_revision=params['revision'], changes={'sampling_interval_m': 0.2})
    assert changed['revision'] == 1
    assert changed['parameters']['sampling_interval_m'] == 0.2
    assert old['result_id'] in changed['affected_result_ids']
    restarted = BusinessService(BusinessStore(store.path), well, 'owner', 'session')
    rerun = await call(restarted, 'rerun_step', **scope, step_id='curve_quality', expected_parameter_revision=1)
    assert rerun['executed_tools'] == ['check_curve_quality']
    new = rerun['results'][0]
    assert new['parameter_snapshot']['revision'] == 1
    assert new['parameter_snapshot']['parameters']['sampling_interval_m'] == 0.2
    assert new['result_id'] != old['result_id']
    assert store.tool_result('owner', 'session', old['result_id']) == old
    assert rerun['result_values_recomputed'] is False


@pytest.mark.parametrize('changes', [{'unknown': 2}, {'sampling_interval_m': 0},
                                      {'sampling_interval_m': True}, {'sampling_interval_m': '0.2'}])
async def test_invalid_parameter_changes_leave_settings_untouched(context, changes):
    _, _, service, scope = context
    rejected = await call(service, 'update_processing_parameters', **scope, step_id='curve_quality',
                          expected_revision=0, changes=changes)
    assert rejected['status'] == 'ERROR'
    current = await call(service, 'get_processing_parameters', **scope, step_id='curve_quality')
    assert current['revision'] == 0
    assert current['parameters']['sampling_interval_m'] == 0.1


async def test_stale_parameter_updates_and_reruns_are_rejected(context):
    _, _, service, scope = context
    await call(service, 'update_processing_parameters', **scope, step_id='curve_quality',
               expected_revision=0, changes={'sampling_interval_m': 0.2})
    for name, extra in [('update_processing_parameters', {'expected_revision': 0, 'changes': {'sampling_interval_m': 0.3}}),
                        ('rerun_step', {'expected_parameter_revision': 0})]:
        rejected = await call(service, name, **scope, step_id='curve_quality', **extra)
        assert rejected['code'] == 'PARAMETER_VERSION_CONFLICT'


async def test_changed_parameters_make_dependent_results_unusable(context):
    _, _, service, scope = context
    qc = await call(service, 'check_curve_quality', **scope)
    lithology = await call(service, 'identify_lithology', **scope, input_result_ids=[qc['result_id']])
    await call(service, 'update_processing_parameters', **scope, step_id='curve_quality',
               expected_revision=0, changes={'sampling_interval_m': 0.2})
    result = await call(service, 'evaluate_petrophysics', **scope, input_result_ids=[lithology['result_id']])
    assert result['code'] == 'STALE_RESULT'


async def test_rerun_sw_and_fluid_calls_only_two_tools_and_records_dependency(context):
    _, store, service, scope = context
    result = await call(service, 'rerun_step', **scope, step_id='sw_and_fluid_identification', expected_parameter_revision=0)
    assert result['executed_tools'] == ['calculate_sw', 'identify_fluid']
    assert result['results'][1]['input_result_ids'] == [result['results'][0]['result_id']]
    assert store.runs('owner', 'session') == []


async def test_rerun_stops_at_blocked_result(context):
    well, _, service, scope = context
    del well.data['outputs']['sw']
    result = await call(service, 'rerun_step', **scope, step_id='sw_and_fluid_identification', expected_parameter_revision=0)
    assert result['status'] == 'BLOCKED'
    assert result['executed_tools'] == ['calculate_sw']
    assert result['can_continue'] is False


async def test_parameter_impact_is_limited_to_changed_scope_and_its_dependencies(context):
    _, _, service, scope = context
    other_scope = {**scope, 'bottom_depth_m': 2002}
    other = await call(service, 'check_curve_quality', **other_scope)
    await call(service, 'update_processing_parameters', **other_scope, step_id='curve_quality',
               expected_revision=0, changes={'sampling_interval_m': 0.3})
    local = await call(service, 'check_curve_quality', **scope)
    dependent = await call(service, 'identify_lithology', **scope, input_result_ids=[local['result_id']])
    changed = await call(service, 'update_processing_parameters', **scope, step_id='curve_quality',
                         expected_revision=0, changes={'sampling_interval_m': 0.2})
    assert set(changed['affected_result_ids']) == {local['result_id'], dependent['result_id']}
    assert other['result_id'] not in changed['affected_result_ids']
    other_settings = await call(service, 'get_processing_parameters', **other_scope, step_id='curve_quality')
    assert other_settings['parameters']['sampling_interval_m'] == 0.3


async def test_parameter_settings_are_isolated_by_owner_and_session(context):
    well, store, service, scope = context
    await call(service, 'update_processing_parameters', **scope, step_id='curve_quality',
               expected_revision=0, changes={'sampling_interval_m': 0.2})
    for owner, session in [('other', 'session'), ('owner', 'other')]:
        current = await call(BusinessService(store, well, owner, session),
                             'get_processing_parameters', **scope, step_id='curve_quality')
        assert current['revision'] == 0
        assert current['parameters']['sampling_interval_m'] == 0.1


async def test_missing_layer_does_not_trigger_processing(context):
    _, store, service, scope = context
    result = await call(service, 'query_interval_results', **scope, layer_no=99)
    assert result['output']['intervals'] == []
    with store.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM tool_results').fetchone()[0] == 0


@pytest.mark.parametrize('status', ['FAILED', 'WARNING', 'UNKNOWN'])
async def test_dataset_query_preserves_existing_result_status(context, status):
    well, _, service, scope = context
    well.data['outputs']['intervals']['status'] = status
    result = await call(service, 'query_interval_results', **scope)
    assert result['status'] == 'SUCCESS'  # 查询成功不改变原结果的处理状态。
    assert result['result_status'] == status


async def test_legacy_result_without_snapshot_becomes_stale_after_first_update(context):
    _, store, service, scope = context
    old = await call(service, 'check_curve_quality', **scope)
    legacy_payload = {k: v for k, v in old.items() if k not in {'parameter_snapshot', 'result_id'}}
    legacy = store.save_tool_result('owner', 'session', legacy_payload)
    await call(service, 'update_processing_parameters', **scope, step_id='curve_quality',
               expected_revision=0, changes={'sampling_interval_m': 0.2})
    result = await call(service, 'identify_lithology', **scope, input_result_ids=[legacy['result_id']])
    assert result['code'] == 'STALE_RESULT'
