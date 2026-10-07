"""曲线读取、图表产物和归属检查；绘图不触发专业处理。"""
import math
from pathlib import Path
from uuid import UUID, uuid4

from ..plots.log_curves import render_log_curves
from .errors import BusinessError
from .professional import ProfessionalService
from .settings import ProcessingSettings


class CurvePlotService:
    def __init__(self, service):
        self.service = service
        self.directory = service.store.path.parent / 'plots'
        self.professional = ProfessionalService(service)

    def create(self, request):
        context = self.professional._context(request.well_id, request.dataset_revision, request.top_depth_m, request.bottom_depth_m)
        current, source_status, warnings = True, 'SUCCESS', []
        if request.result_id is None:
            data = self.service.well.data['raw_data']
            source = self.service.well.summary()['source']
        else:
            saved = self.service.store.tool_result(self.service.owner, self.service.session, request.result_id)
            if saved is None:
                raise BusinessError('RESULT_NOT_FOUND', '结果不存在或不属于当前会话。')
            previous = saved['context']
            if any(previous[k] != context[k] for k in ('well_id', 'dataset_revision')) or previous['top_depth_m'] is None or not (
                previous['top_depth_m'] <= context['top_depth_m'] < context['bottom_depth_m'] <= previous['bottom_depth_m']
            ):
                raise BusinessError('RESULT_CONTEXT_CONFLICT', '绘图井段或资料版本与已有结果不一致。')
            source_status = saved['status']
            if source_status not in {'SUCCESS', 'WARNING'}:
                raise BusinessError('RESULT_UNAVAILABLE', '该结果未提供可用曲线。')
            output = saved['output']
            data = output.get('curve_data') or (output.get('result') or {}).get('curve_data')
            if not isinstance(data, dict):
                raise BusinessError('CURVE_DATA_UNAVAILABLE', '该结果没有曲线数据。')
            source = saved['source']
            current = ProcessingSettings(self.service).result_is_current(saved)
            if not current:
                warnings.append('绘制历史结果，该结果的参数或前置依赖已过期。')
            if source_status == 'WARNING':
                warnings.append('来源结果包含告警，请结合来源结果解释图表。')
        if not isinstance(data.get('curves'), dict):
            raise BusinessError('INVALID_CURVE_DATA', '曲线目录结构无效。')
        tracks = []
        for name in dict.fromkeys(request.curve_names):
            curve = data['curves'].get(name)
            if curve is None:
                raise BusinessError('CURVE_NOT_FOUND', '指定来源中没有曲线：' + name)
            if not isinstance(curve, dict) or not isinstance(curve.get('unit'), str):
                raise BusinessError('INVALID_CURVE_DATA', '曲线缺少单位或结构无效。')
            if 'points' in curve:
                points = curve['points']
                if not isinstance(points, list) or any(not isinstance(p, dict) or 'depth_m' not in p or 'value' not in p for p in points):
                    raise BusinessError('INVALID_CURVE_DATA', '曲线点结构无效。')
                points = [(p['depth_m'], p['value']) for p in points]
            else:
                depths, values = data.get('depths'), curve.get('values')
                if not isinstance(depths, list) or not isinstance(values, list) or len(depths) != len(values):
                    raise BusinessError('INVALID_CURVE_DATA', '曲线深度与采样数组不一致。')
                points = list(zip(depths, values, strict=True))
            previous_depth = None
            for depth, value in points:
                if type(depth) not in {float, int} or not math.isfinite(depth) or (previous_depth is not None and depth <= previous_depth):
                    raise BusinessError('INVALID_CURVE_DATA', '采样深度必须为递增的有限数值。')
                if value is not None and (type(value) not in {float, int} or not math.isfinite(value)):
                    raise BusinessError('INVALID_CURVE_DATA', '曲线采样必须为有限数值或空值。')
                previous_depth = depth
            points = [(d, v) for d, v in points if request.top_depth_m <= d <= request.bottom_depth_m]
            scale = 'log' if name in request.log_curve_names else 'linear'
            nonpositive = sum(v is not None and v <= 0 for _, v in points) if scale == 'log' else 0
            null_count = sum(v is None for _, v in points)
            valid_count = len(points) - null_count - nonpositive
            if nonpositive:
                warnings.append(name + ' 对数轴不绘制非正值，并在对应位置断线。')
            if valid_count == 0:
                warnings.append(name + ' 在本井段没有可绘制采样。')
            tracks.append(dict(curve_name=name, unit=curve['unit'], scale=scale, points=points,
                               sample_count=len(points), valid_count=valid_count, null_count=null_count,
                               nonpositive_count=nonpositive))
        label = source + (' · HISTORICAL' if not current else '')
        svg, width, height = render_log_curves(context, tracks, label)
        artifact_id = str(uuid4())
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.directory / (artifact_id + '.svg')
        path.write_text(svg, encoding='utf-8')
        payload = dict(status='WARNING' if warnings else 'SUCCESS', tool_name='plot_curves', step_id='PLOT',
                       context=context, source=source, source_result_id=request.result_id, source_result_status=source_status,
                       is_current=current, input_result_ids=[request.result_id] if request.result_id else [],
                       output={'chart_type': 'well_log'}, artifact_id=artifact_id, width=width, height=height,
                       depth_direction='down', tracks=[{k: v for k, v in t.items() if k != 'points'} for t in tracks],
                       warnings=warnings, is_mock=True)
        try:
            saved = self.service.store.save_tool_result(self.service.owner, self.service.session, payload)
        except Exception:
            path.unlink(missing_ok=True)
            raise
        return {**saved, 'plot_id': saved['result_id']}

    def artifact(self, plot_id):
        record = self.service.store.tool_result(self.service.owner, self.service.session, plot_id)
        if record is None or record['tool_name'] != 'plot_curves':
            raise BusinessError('PLOT_NOT_FOUND', '图表不存在或不属于当前会话。')
        path = self.directory / (str(UUID(record['artifact_id'])) + '.svg')
        if not path.is_file():
            raise BusinessError('PLOT_UNAVAILABLE', '图表文件当前不可用。')
        return path
