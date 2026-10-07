"""处理设置由适配器声明，按井段及步骤持久化，结果保留使用时的快照。"""
import math

from .errors import BusinessError


class ProcessingSettings:
    def __init__(self, service):
        self.service = service

    def read(self, context, step):
        definitions = self.service.well.data.get('processing_parameters', {}).get(step, {})
        saved = self.service.store.processing_parameters(self.service.owner, self.service.session, context, step)
        return {
            'status': 'SUCCESS', 'context': context, 'step_id': step,
            'revision': saved['revision'] if saved else 0,
            'parameters': saved['parameters'] if saved else {k: v['default'] for k, v in definitions.items()},
            'definitions': definitions, 'definition_source': 'sample.processing_parameters',
            'is_mock': True,
        }

    def update(self, context, step, expected_revision, changes):
        current = self.read(context, step)
        for name, value in changes.items():
            definition = current['definitions'].get(name)
            if definition is None:
                raise BusinessError('UNKNOWN_PARAMETER', '步骤未声明参数：' + name)
            valid = type(value) in {int, float} and math.isfinite(value)
            if valid and 'exclusiveMinimum' in definition:
                valid = value > definition['exclusiveMinimum']
            if not valid:
                raise BusinessError('INVALID_PARAMETER', '参数类型或允许值不符合定义：' + name)
        updated = self.service.store.update_processing_parameters(
            self.service.owner, self.service.session, context, step, expected_revision,
            current['parameters'], changes,
        )
        return {**current, **updated}

    def check_revision(self, snapshot, expected):
        if expected is not None and snapshot['revision'] != expected:
            raise BusinessError('PARAMETER_VERSION_CONFLICT', '参数版本已变化，请重新读取后修改或执行。')

    def result_is_current(self, result, seen=None):
        """修改影响本步和实际引用它的后续结果；历史正文仍可读取。"""
        seen = set() if seen is None else seen
        result_id = result['result_id']
        if result_id in seen:
            return False
        seen = seen | {result_id}
        # 上一版本保存的结果没有参数快照，按未修改的默认版本 0 处理。
        snapshot = result.get('parameter_snapshot') or {'revision': 0}
        current = self.read(result['context'], result['step_id'])
        if snapshot['revision'] != current['revision']:
            return False
        for reference in result.get('input_result_ids', []):
            parent = self.service.store.tool_result(self.service.owner, self.service.session, reference)
            if parent is None or not self.result_is_current(parent, seen):
                return False
        return True

    def affected_by_change(self, result, context, step, revision, seen=None):
        """只报告本次设置及其实际依赖，其他井段此前过期的结果不混入。"""
        seen = set() if seen is None else seen
        if result['result_id'] in seen:
            return False
        seen = seen | {result['result_id']}
        snapshot = result.get('parameter_snapshot') or {'revision': 0}
        if result['context'] == context and result['step_id'] == step and snapshot['revision'] < revision:
            return True
        for reference in result.get('input_result_ids', []):
            parent = self.service.store.tool_result(self.service.owner, self.service.session, reference)
            if parent is not None and self.affected_by_change(parent, context, step, revision, seen):
                return True
        return False
