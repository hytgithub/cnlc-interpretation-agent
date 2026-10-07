"""绘图使用实际曲线和来源，保留空值断线，并隔离图表访问。"""
import json
import math
import re
import xml.etree.ElementTree as ET

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


async def invoke(service, name, **arguments):
    tool = next((t for t in make_tools(service) if t.name == name), None)
    assert tool is not None, f'缺少绘图工具：{name}'
    chunk = await tool.call(**arguments)
    return json.loads(chunk.content[0].text), chunk


async def test_plot_raw_curves_produces_real_svg_without_selection_or_processing(context):
    _, store, service, scope = context
    payload, chunk = await invoke(service, 'plot_curves', **scope, curve_names=['GR', 'RT'])
    assert payload['status'] == 'SUCCESS'
    assert payload['tracks'][0]['sample_count'] == 11
    assert payload['depth_direction'] == 'down'
    assert 'curve_plot' in chunk.metadata
    with store.connect() as db:
        records = [json.loads(row[0]) for row in db.execute('SELECT payload FROM tool_results')]
    assert [r['tool_name'] for r in records] == ['plot_curves']
    assert store.selection('owner', 'session') is None
    assert store.runs('owner', 'session') == []
    from cnlc_agent.business.plotting import CurvePlotService
    path = CurvePlotService(service).artifact(payload['plot_id'])
    root = ET.parse(path).getroot()
    assert len(root.findall('.//{*}path')) == 2
    text = ''.join(root.itertext())
    assert 'GR' in text and 'RT' in text and 'MD' in text
    assert len(chunk.content[0].text) < 4000
    assert 'points' not in chunk.content[0].text


async def test_plot_null_values_break_line_and_zero_is_a_real_value(context):
    well, _, service, scope = context
    well.data['raw_data']['curves']['GR']['values'][:3] = [0, None, 3]
    scope = {**scope, 'bottom_depth_m': 2000.2}
    payload, _ = await invoke(service, 'plot_curves', **scope, curve_names=['GR'])
    from cnlc_agent.business.plotting import CurvePlotService
    root = ET.parse(CurvePlotService(service).artifact(payload['plot_id'])).getroot()
    assert payload['tracks'][0]['valid_count'] == 2
    assert payload['tracks'][0]['null_count'] == 1
    paths = root.findall('.//{*}path')
    assert all('L' not in path.attrib['d'] for path in paths)
    assert len(root.findall('.//{*}circle')) == 2


async def test_plot_saved_derived_curve_uses_original_reference_and_range(context):
    well, store, service, scope = context
    original, _ = await invoke(service, 'evaluate_petrophysics', **scope)
    names = list(original['output']['result']['curve_data']['curves'])
    payload, _ = await invoke(service, 'plot_curves', **scope, curve_names=names, result_id=original['result_id'])
    assert payload['source_result_id'] == original['result_id']
    assert payload['tracks'][0]['sample_count'] == 11
    assert store.tool_result('owner', 'session', original['result_id']) == original
    other = BusinessService(store, well, 'other', 'session')
    rejected, _ = await invoke(other, 'plot_curves', **scope, curve_names=names, result_id=original['result_id'])
    assert rejected['code'] == 'RESULT_NOT_FOUND'


@pytest.mark.parametrize('overrides,code', [
    ({'curve_names': ['MISSING']}, 'CURVE_NOT_FOUND'),
    ({'dataset_revision': 'old'}, 'DATASET_VERSION_CONFLICT'),
    ({'bottom_depth_m': 2121}, 'OUT_OF_RANGE'),
    ({'curve_names': []}, 'INVALID_INPUT'),
    ({'curve_names': [' ']}, 'INVALID_INPUT'),
    ({'log_curve_names': ['RT']}, 'INVALID_INPUT'),
])
async def test_invalid_plot_requests_do_not_save_artifacts(context, overrides, code):
    _, store, service, scope = context
    payload, _ = await invoke(service, 'plot_curves', **{**scope, 'curve_names': ['GR'], **overrides})
    assert payload['code'] == code
    with store.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM tool_results').fetchone()[0] == 0


async def test_log_scale_does_not_replace_nonpositive_values(context):
    well, _, service, scope = context
    well.data['raw_data']['curves']['RT']['values'][:11] = [0, -1] + [10] * 9
    payload, _ = await invoke(service, 'plot_curves', **scope, curve_names=['RT'], log_curve_names=['RT'])
    assert payload['status'] == 'WARNING'
    assert payload['tracks'][0]['nonpositive_count'] == 2
    assert payload['tracks'][0]['scale'] == 'log'
    assert well.data['raw_data']['curves']['RT']['values'][0] == 0


async def test_plot_artifact_is_persistent_and_owner_scoped(context):
    well, store, service, scope = context
    payload, _ = await invoke(service, 'plot_curves', **scope, curve_names=['GR'])
    from cnlc_agent.business.plotting import CurvePlotService
    restarted = BusinessService(BusinessStore(store.path), well, 'owner', 'session')
    assert CurvePlotService(restarted).artifact(payload['plot_id']).is_file()
    from cnlc_agent.business.errors import BusinessError
    for owner, session in [('other', 'session'), ('owner', 'other')]:
        with pytest.raises(BusinessError) as error:
            CurvePlotService(BusinessService(store, well, owner, session)).artifact(payload['plot_id'])
        assert error.value.code == 'PLOT_NOT_FOUND'


async def test_plot_result_cannot_substitute_for_professional_input(context):
    _, _, service, scope = context
    plot, _ = await invoke(service, 'plot_curves', **scope, curve_names=['GR'])
    rejected, _ = await invoke(service, 'identify_lithology', **scope, input_result_ids=[plot['plot_id']])
    assert rejected['code'] == 'RESULT_TYPE_CONFLICT'


async def test_plot_saved_history_reports_expired_parameters(context):
    _, _, service, scope = context
    raw, _ = await invoke(service, 'get_well_data', **scope, curve_names=['GR'])
    qc, _ = await invoke(service, 'check_curve_quality', **scope)
    derived, _ = await invoke(service, 'evaluate_petrophysics', **scope, input_result_ids=[qc['result_id']])
    await invoke(service, 'update_processing_parameters', **scope, step_id='curve_quality', expected_revision=0,
                 changes={'sampling_interval_m': 0.2})
    name = next(iter(derived['output']['result']['curve_data']['curves']))
    plot, _ = await invoke(service, 'plot_curves', **scope, curve_names=[name], result_id=derived['result_id'])
    assert plot['status'] == 'WARNING'
    assert plot['is_current'] is False
    assert plot['source_result_id'] == derived['result_id']
    raw_plot, _ = await invoke(service, 'plot_curves', **scope, curve_names=['GR'], result_id=raw['result_id'])
    assert raw_plot['tracks'][0]['sample_count'] == 11


@pytest.mark.parametrize('values', [[1], [float('inf')] * 1201, ['3'] * 1201])
async def test_invalid_curve_samples_return_error_instead_of_invalid_svg(context, values):
    well, _, service, scope = context
    well.data['raw_data']['curves']['GR']['values'] = values
    result, _ = await invoke(service, 'plot_curves', **scope, curve_names=['GR'])
    assert result['code'] == 'INVALID_CURVE_DATA'


@pytest.mark.parametrize('values,scale', [
    ([-1e308, 0, 1e308], 'linear'),
    ([1e308] * 3, 'linear'),
    ([1e308] * 3, 'log'),
    ([5e-324, 1, 1e308], 'log'),
])
async def test_finite_extreme_values_produce_finite_coordinates(context, values, scale):
    well, _, service, scope = context
    well.data['raw_data']['curves']['GR']['values'][:3] = values
    payload, _ = await invoke(service, 'plot_curves', **{**scope, 'bottom_depth_m': 2000.2},
                              curve_names=['GR'], log_curve_names=['GR'] if scale == 'log' else [])
    assert payload['status'] == 'SUCCESS'
    from cnlc_agent.business.plotting import CurvePlotService
    root = ET.parse(CurvePlotService(service).artifact(payload['plot_id'])).getroot()
    path = root.find('.//{*}path').attrib['d']
    assert 'nan' not in path.lower() and 'inf' not in path.lower()
    coordinates = [float(n) for n in re.findall(r'-?\d+(?:\.\d+)?', path)]
    assert len(coordinates) == 6
    assert all(math.isfinite(n) for n in coordinates)
    assert all(100 <= x <= 266 for x in coordinates[::2])
    labels = [element.text for element in root.findall('.//{*}text') if element.attrib.get('y') == '91']
    assert all(math.isfinite(float(label)) for label in labels)
