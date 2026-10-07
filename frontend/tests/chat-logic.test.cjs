const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const ts = require('typescript');

// Exercise the real pure TypeScript modules without adding a browser test dependency.
function load(file) {
	const source = fs.readFileSync(path.resolve(__dirname, '../src', file), 'utf8');
	const code = ts.transpileModule(source, {
		compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2023 },
	}).outputText;
	const module = { exports: {} };
	new Function('module', 'exports', 'require', code)(module, module.exports, require);
	return module.exports;
}

const { openPanelInLayout, closePanelInLayout, loadPanelLayout } = load(
	'pages/chat/panel-layout.ts',
);
const { groupToolCalls } = load('components/chat/tool-call-groups.ts');
const { resolveType, extractDefaults } = load('components/popover/model-parameter-schema.ts');
const { processChatFile, getAllowedInputTypes } = load('pages/chat/input-media.ts');

test('opening a panel fills the next available column without mutating the layout', () => {
	const layout = [['plan', 'mcp'], ['skill']];
	assert.deepEqual(openPanelInLayout(layout, 'knowledge'), [
		['plan', 'mcp'],
		['skill', 'knowledge'],
	]);
	assert.deepEqual(layout, [['plan', 'mcp'], ['skill']]);
	assert.strictEqual(openPanelInLayout(layout, 'skill'), layout);
	assert.deepEqual(openPanelInLayout([['plan', 'mcp']], 'team'), [['plan', 'mcp'], ['team']]);
});

test('closing a panel removes empty columns and preserves other panels', () => {
	assert.deepEqual(closePanelInLayout([['plan'], ['mcp', 'skill']], 'plan'), [['mcp', 'skill']]);
	assert.deepEqual(closePanelInLayout([['plan', 'skill']], 'skill'), [['plan']]);
});

test('stored panel layouts discard obsolete panels and recover from corrupt data', () => {
	const previous = Object.getOwnPropertyDescriptor(global, 'localStorage');
	try {
		Object.defineProperty(global, 'localStorage', {
			configurable: true,
			writable: true,
			value: { getItem: () => JSON.stringify([['plan', 'obsolete'], [], ['skill']]) },
		});
		assert.deepEqual(loadPanelLayout(), [['plan'], ['skill']]);
		global.localStorage = { getItem: () => 'not JSON' };
		assert.deepEqual(loadPanelLayout(), []);
	} finally {
		if (previous) Object.defineProperty(global, 'localStorage', previous);
		else delete global.localStorage;
	}
});

test('tool results pair by id even when concurrent calls finish in reverse order', () => {
	const callA = { type: 'tool_call', id: 'a', name: 'Read', input: '{}' };
	const callB = { type: 'tool_call', id: 'b', name: 'Bash', input: '{}' };
	const resultB = { type: 'tool_result', id: 'b', name: 'Bash', content: [] };
	const resultA = { type: 'tool_result', id: 'a', name: 'Read', content: [] };
	const groups = groupToolCalls([callA, callB, resultB, resultA]);
	assert.equal(groups.length, 1);
	assert.equal(groups[0].type, 'tool_call_group');
	assert.deepEqual(groups[0].calls, [
		{ call: callA, result: resultA },
		{ call: callB, result: resultB },
	]);
});

test('text separates tool groups and orphan results remain visible', () => {
	const text = { type: 'text', text: 'Explanation' };
	const orphan = { type: 'tool_result', id: 'lost', name: 'Read', content: [] };
	const groups = groupToolCalls([
		{ type: 'tool_call', id: 'a', name: 'Read', input: '{}' },
		text,
		{ type: 'tool_call', id: 'b', name: 'Bash', input: '{}' },
		orphan,
	]);
	assert.equal(groups.length, 4);
	assert.strictEqual(groups[1], text);
	assert.equal(groups[3].calls[0].call.id, 'lost');
	assert.strictEqual(groups[3].calls[0].result, orphan);
});

test('parameter schemas resolve nullable scalar types and retain falsy defaults', () => {
	assert.deepEqual(resolveType({ anyOf: [{ type: 'null' }, { type: 'integer', enum: [0, 1] }] }), {
		type: 'integer',
		enumValues: [0, 1],
	});
	assert.deepEqual(
		extractDefaults({
			properties: {
				zero: { default: 0 },
				disabled: { default: false },
				empty: { default: '' },
				absent: {},
			},
		}),
		{ zero: 0, disabled: false, empty: '' },
	);
});

test('file inputs preserve text, media bytes and local file references', async () => {
	const text = await processChatFile(new File(['hello'], 'notes.txt', { type: 'text/plain' }));
	assert.equal(text.type, 'text');
	assert.equal(text.text, '[File: notes.txt]\nhello');
	const image = await processChatFile(
		new File([new Uint8Array([1, 2, 3])], 'image.png', { type: 'image/png' }),
	);
	assert.deepEqual(image.source, { type: 'base64', media_type: 'image/png', data: 'AQID' });
	const local = new File([], 'local.pdf', { type: 'application/pdf' });
	local.path = '/tmp/local.pdf';
	assert.deepEqual((await processChatFile(local)).source, {
		type: 'url',
		url: 'file:///tmp/local.pdf',
		media_type: 'application/pdf',
	});
	assert.deepEqual(
		getAllowedInputTypes(['image/png', 'text/plain', 'application/pdf', 'application/json']),
		['image/png', 'text/plain', 'application/pdf'],
	);
});

const { parseCurvePlotMetadata, splitInlineCurvePlots } = load('components/chat/tool-renderers/curve-plot-data.ts');

test('curve plots accept the owned artifact route and preserve chart dimensions', () => {
	const plot = { url: '/business/sessions/session-1/plots/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee?agent_id=agent-1',
		plot_id: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee', width: 492, height: 740 };
	assert.deepEqual(parseCurvePlotMetadata({ curve_plot: plot }), plot);
});

test('curve plot metadata cannot redirect authenticated requests or use invalid dimensions', () => {
	const plot = { url: '/business/sessions/session-1/plots/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
		plot_id: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee', width: 492, height: 740 };
	for (const url of ['https://example.com/chart', '//example.com/chart', '/workspace/file',
		'/business/sessions/s/plots/../../secret', `${plot.url}&other=1`]) {
		assert.equal(parseCurvePlotMetadata({ curve_plot: { ...plot, url } }), null);
	}
	for (const width of [0, -1, Infinity, '492']) {
		assert.equal(parseCurvePlotMetadata({ curve_plot: { ...plot, width } }), null);
	}
	assert.equal(parseCurvePlotMetadata(null), null);
});

test('completed curve plots leave the collapsed tool group and remain inline after reload', () => {
	const call = { type: 'tool_call', name: 'plot_curves', id: 'plot-call', input: '{}' };
	const metadata = { curve_plot: { url: '/business/sessions/session-1/plots/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
		plot_id: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee', width: 492, height: 740 } };
	const result = { type: 'tool_result', name: 'plot_curves', id: call.id, state: 'success', metadata, content: [] };
	const query = { call: { name: 'get_well_data', id: 'query' } };
	const groups = groupToolCalls(JSON.parse(JSON.stringify([call, result])));
	const pair = groups[0].calls[0];
	assert.deepEqual(splitInlineCurvePlots([query, pair]), { inlinePlots: [pair], collapsedCalls: [query] });
	assert.deepEqual(splitInlineCurvePlots([pair]), { inlinePlots: [pair], collapsedCalls: [] });
	for (const pending of [
		{ call },
		{ call, result: { ...result, metadata: {} } },
		{ call, result: { ...result, state: 'error' } },
		{ call: { ...call, name: 'get_well_data' }, result },
	]) {
		assert.deepEqual(splitInlineCurvePlots([pending]), { inlinePlots: [], collapsedCalls: [pending] });
	}
});
