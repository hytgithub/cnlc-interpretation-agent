import { countDiffStats, getResultDiff } from './tool-renderers/_shared';
import type { TFunction, ToolCallWithResult } from './tool-renderers/types';

export const MCP_TOOL_PREFIX = 'mcp__';

// Task-management tools are all surfaced under one "updated todos" summary.
export const TODO_TOOLS = new Set(['TaskGet', 'TaskUpdate', 'TaskList', 'TaskCreate']);

/**
 * Bucket a group's calls into per-category counts and total inserted/deleted
 * lines (from Edit/Write result diffs), then build the localized collapsible
 * title. Categories are appended in a fixed order — Bash, Read, Edit/Write,
 * Search (Grep/Glob), Todo, MCP — each omitted when its count is zero. If
 * nothing matches a known category, a generic "called N tools" fallback is used.
 */
export function summarizeToolGroup(calls: ToolCallWithResult[], t: TFunction) {
	let nBash = 0;
	let nRead = 0;
	let nEdit = 0;
	let nSearch = 0;
	let nTodo = 0;
	let nMCP = 0;
	const skillNames: string[] = [];
	let insertions = 0;
	let deletions = 0;

	for (const { call, result } of calls) {
		const name = call.name;
		if (name === 'Bash') {
			nBash += 1;
		} else if (name === 'Read') {
			nRead += 1;
		} else if (name === 'Edit' || name === 'Write') {
			nEdit += 1;
			// Sum the real +/- line changes from the backend-provided diff.
			const diff = result ? getResultDiff(result) : undefined;
			if (diff) {
				const stats = countDiffStats(diff);
				insertions += stats.insertions;
				deletions += stats.deletions;
			}
		} else if (name === 'Grep' || name === 'Glob') {
			nSearch += 1;
		} else if (TODO_TOOLS.has(name)) {
			nTodo += 1;
		} else if (name === 'Skill') {
			try {
				const input = JSON.parse(call.input) as { skill?: unknown };
				if (typeof input.skill === 'string' && input.skill.trim()) {
					skillNames.push(
						input.skill === 'conventional-log-interpretation'
							? t('tool.summary.conventionalInterpretationSkill')
							: input.skill,
					);
				}
			} catch {
				// Keep the generic Skill label when the call input is incomplete.
			}
		} else if (name.startsWith(MCP_TOOL_PREFIX)) {
			nMCP += 1;
		}
	}

	const parts: string[] = [];
	if (nBash > 0) parts.push(t('tool.summary.bash', { count: nBash }));
	if (nRead > 0) parts.push(t('tool.summary.read', { count: nRead }));
	if (nEdit > 0) parts.push(t('tool.summary.edit', { count: nEdit }));
	if (nSearch > 0) parts.push(t('tool.summary.search', { count: nSearch }));
	if (nTodo > 0) parts.push(t('tool.summary.todo', { count: nTodo }));
	if (nMCP > 0) parts.push(t('tool.summary.mcp', { count: nMCP }));
	if (skillNames.length > 0) {
		parts.push(t('tool.summary.skills', { names: [...new Set(skillNames)].join(t('tool.summary.separator')) }));
	}

	const joined =
		parts.length > 0
			? parts.join(t('tool.summary.separator'))
			: t('tool.summary.fallback', { count: calls.length });
	// Sentence-case only the very first letter (each i18n part is lower-cased
	// so commas don't introduce mid-sentence capitals in English; a no-op for
	// scripts without letter case such as Chinese).
	const title = joined.length > 0 ? joined[0].toUpperCase() + joined.slice(1) : joined;

	return { title, insertions, deletions };
}
