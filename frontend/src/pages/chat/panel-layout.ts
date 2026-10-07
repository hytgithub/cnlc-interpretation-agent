import type { PanelKey } from '@/components/panel/PanelDock';

/** Maximum number of panels stacked in a single dock column. */
export const MAX_PANELS_PER_COLUMN = 2;

/** localStorage key holding the dock layout across page navigations. */
export const PANEL_LAYOUT_KEY = 'chat_panel_layout';

// Typed as a full Record so adding a PanelKey without listing it here
// is a compile error rather than a silently unrestorable panel.
export const KNOWN_PANELS: Record<PanelKey, true> = {
	plan: true,
	mcp: true,
	skill: true,
	permission: true,
	knowledge: true,
	team: true,
};

/**
 * Restore the persisted dock layout, dropping anything that is no
 * longer a known panel (keys get renamed/removed across releases).
 *
 * @returns The stored layout, or an empty one when absent or corrupt.
 */
export function loadPanelLayout(): PanelKey[][] {
	try {
		const parsed: unknown = JSON.parse(localStorage.getItem(PANEL_LAYOUT_KEY) ?? '[]');
		if (!Array.isArray(parsed)) return [];
		return parsed
			.map((column: unknown) =>
				Array.isArray(column) ? column.filter((key): key is PanelKey => key in KNOWN_PANELS) : [],
			)
			.filter((column) => column.length > 0);
	} catch {
		return [];
	}
}

/**
 * Insert a panel into the dock layout. Scans columns left to right and
 * appends to the first one with spare room; if every column is full a
 * new rightmost column is created. No-op when the panel is already
 * open.
 *
 * @param layout - The current column/panel arrangement.
 * @param key - The panel to open.
 * @returns A new layout array (the input is never mutated).
 */
export function openPanelInLayout(layout: PanelKey[][], key: PanelKey): PanelKey[][] {
	if (layout.some((column) => column.includes(key))) return layout;
	const targetIndex = layout.findIndex((column) => column.length < MAX_PANELS_PER_COLUMN);
	if (targetIndex === -1) return [...layout, [key]];
	return layout.map((column, index) => (index === targetIndex ? [...column, key] : column));
}

/**
 * Remove a panel from the dock layout, dropping its column entirely if
 * it becomes empty.
 *
 * @param layout - The current column/panel arrangement.
 * @param key - The panel to close.
 * @returns A new layout array (the input is never mutated).
 */
export function closePanelInLayout(layout: PanelKey[][], key: PanelKey): PanelKey[][] {
	return layout
		.map((column) => column.filter((panelKey) => panelKey !== key))
		.filter((column) => column.length > 0);
}
