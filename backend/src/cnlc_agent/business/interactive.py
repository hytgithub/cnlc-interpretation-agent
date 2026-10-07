"""已有层段查询、参数修改和指定步骤执行；复用独立专业能力。"""
from copy import deepcopy

from ..contracts.agent_tools import ProfessionalInput, WellDataInput
from .errors import BusinessError
from .professional import ProfessionalService, TOOL_STEPS, _valid_result
from .settings import ProcessingSettings


class InteractiveService:
    def __init__(self, service):
        self.service = service
        self.professional = ProfessionalService(service)
        self.settings = ProcessingSettings(service)

    def context(self, request):
        return self.professional._context(request.well_id, request.dataset_revision,
                                          request.top_depth_m, request.bottom_depth_m)

    def query_interval_results(self, request):
        context = self.context(request)
        if request.result_id is None:
            rows = deepcopy(self.service.well.intervals)
            source = self.service.well.data['outputs']['intervals'].get('source', 'sample.intervals')
            if not _valid_result('merge_intervals', {'intervals': rows}):
                raise BusinessError('INVALID_RESULT', '已有层段结果结构无效。')
            status = self.service.well.data['outputs']['intervals'].get('status', 'SUCCESS')
            if status not in {'SUCCESS', 'WARNING', 'FAILED', 'BLOCKED', 'ERROR', 'UNKNOWN', 'REVIEW_REQUIRED'}:
                status = 'UNKNOWN'
            result_id, result_context, current = None, context, True
            metadata = {'result_version': self.service.well.revision, 'source_kind': 'dataset'}
        else:
            saved = self.service.store.tool_result(self.service.owner, self.service.session, request.result_id)
            if saved is None:
                raise BusinessError('RESULT_NOT_FOUND', '结果不存在或不属于当前会话。')
            if saved['tool_name'] != 'merge_intervals':
                raise BusinessError('RESULT_TYPE_CONFLICT', '该结果引用不是层段整理结果。')
            previous = saved['context']
            if any(previous[k] != context[k] for k in ('well_id', 'dataset_revision')) or not (
                previous['top_depth_m'] <= context['top_depth_m'] < context['bottom_depth_m'] <= previous['bottom_depth_m']
            ):
                raise BusinessError('RESULT_CONTEXT_CONFLICT', '查询范围或资料版本与已有结果不一致。')
            result = saved['output'].get('result')
            if not _valid_result('merge_intervals', result):
                raise BusinessError('RESULT_UNAVAILABLE', '该版本没有可查询的层段结果。')
            rows = deepcopy(result['intervals'])
            source, result_id, result_context = saved['source'], saved['result_id'], previous
            status, current = saved['status'], self.settings.result_is_current(saved)
            metadata = {k: saved[k] for k in ('fixture_scope', 'scope_note', 'parameter_snapshot') if k in saved}
            metadata['source_kind'] = 'saved_result'
        rows = [row for row in rows if row['bottom_depth_m'] > context['top_depth_m']
                and row['top_depth_m'] < context['bottom_depth_m']
                and (request.layer_no is None or row.get('layer_no') == request.layer_no)]
        return {'status': 'SUCCESS', 'context': context, 'result_context': result_context,
                'result_id': result_id, 'source': source, 'result_status': status,
                'is_current': current, 'is_mock': True, 'output': {'intervals': rows}, **metadata}

    def get_processing_parameters(self, request):
        return self.settings.read(self.context(request), request.step_id)

    def update_processing_parameters(self, request):
        context = self.context(request)
        result = self.settings.update(context, request.step_id, request.expected_revision, request.changes)
        result['affected_result_ids'] = [row['result_id'] for row in self.service.store.tool_results(
            self.service.owner, self.service.session)
            if self.settings.affected_by_change(row, context, request.step_id, result['revision'])]
        result['requires_rerun'] = True
        return result

    def rerun_step(self, request):
        context = self.context(request)
        snapshot = self.settings.read(context, request.step_id)
        self.settings.check_revision(snapshot, request.expected_parameter_revision)
        # 操作仅执行选定阶段；含水饱和度与流体识别阶段包含两项有顺序依赖的能力。
        names = [name for name, step in TOOL_STEPS.items() if step == request.step_id]
        ids, results = list(request.input_result_ids), []
        self.professional._inputs(context, ids)
        status = 'SUCCESS'
        for name in names:
            if name == 'get_well_data':
                result = self.professional.get_well_data(WellDataInput(**context_for_schema(context)))
            else:
                result = self.professional.execute(name, ProfessionalInput(
                    **context_for_schema(context), input_result_ids=ids,
                    expected_parameter_revision=request.expected_parameter_revision,
                ))
            results.append(result)
            if not result['can_continue']:
                status = result['status']
                break
            if result['status'] == 'WARNING':
                status = 'WARNING'
            ids.append(result['result_id'])
        return {'status': status, 'can_continue': status in {'SUCCESS', 'WARNING'},
                'step_id': request.step_id, 'context': context,
                'executed_tools': [r['tool_name'] for r in results], 'results': results,
                'parameter_snapshot': snapshot, 'is_mock': True,
                'result_values_recomputed': False,
                'execution_note': '按指定步骤重新调用当前适配器并保存新结果；预设专业数值未重新计算。'}


def context_for_schema(context):
    return {k: context[k] for k in ('well_id', 'dataset_revision', 'top_depth_m', 'bottom_depth_m')}
