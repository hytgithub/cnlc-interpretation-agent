import type { ToolCallWithResult } from './types';

/** Only accept the session-scoped chart route; metadata cannot redirect identity headers. */
export interface CurvePlotMetadata {
	url: string;
	plot_id: string;
	width: number;
	height: number;
}

export function parseCurvePlotMetadata(metadata: unknown): CurvePlotMetadata | null {
	if (!metadata || typeof metadata !== 'object') return null;
	const plot = (metadata as Record<string, unknown>).curve_plot;
	if (!plot || typeof plot !== 'object') return null;
	const value = plot as Record<string, unknown>;
	if (
		typeof value.url !== 'string' ||
		!/^\/business\/sessions\/[A-Za-z0-9_-]+\/plots\/[0-9a-f-]{36}(?:\?agent_id=[A-Za-z0-9_%.-]+)?$/.test(value.url) ||
		typeof value.plot_id !== 'string' ||
		typeof value.width !== 'number' || !Number.isFinite(value.width) || value.width <= 0 || value.width > 2000 ||
		typeof value.height !== 'number' || !Number.isFinite(value.height) || value.height <= 0 || value.height > 2000
	) return null;
	return { url: value.url, plot_id: value.plot_id, width: value.width, height: value.height };
}

/** Keep chart output visible even when execution details are collapsed. */
export function splitInlineCurvePlots(calls: ToolCallWithResult[]) {
	const inlinePlots: ToolCallWithResult[] = [];
	const collapsedCalls: ToolCallWithResult[] = [];
	for (const pair of calls) {
		if (pair.call.name === 'plot_curves' && pair.result?.state === 'success' && parseCurvePlotMetadata(pair.result.metadata)) {
			inlinePlots.push(pair);
		} else {
			collapsedCalls.push(pair);
		}
	}
	return { inlinePlots, collapsedCalls };
}
