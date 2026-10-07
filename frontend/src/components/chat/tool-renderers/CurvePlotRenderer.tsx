import { getResultText, parseInput, toolArgClass, toolLabelClass } from './_shared';
import { parseCurvePlotMetadata } from './curve-plot-data';
import { CurvePlotView } from './CurvePlotView';
import { defaultRenderBody } from './DefaultRenderer';
import type { ToolRenderer } from './types';

export const CurvePlotRenderer: ToolRenderer = {
	getDisplayName: () => '绘制测井曲线',
	renderHeader: pair => {
		const names = parseInput(pair.call.input).curve_names;
		return <><span className={toolLabelClass}>绘制测井曲线</span><span className={toolArgClass}>{Array.isArray(names) ? names.join('、') : ''}</span></>;
	},
	renderBody: (pair, t) => {
		const plot = parseCurvePlotMetadata(pair.result?.metadata);
		if (!plot) return defaultRenderBody(pair, t);
		return <CurvePlotView plot={plot} summary={getResultText(pair.result)} />;
	},
};
