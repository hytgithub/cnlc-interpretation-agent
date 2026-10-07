import { useCallback, useEffect, useState } from 'react';

import {
	closePanelInLayout,
	loadPanelLayout,
	openPanelInLayout,
	PANEL_LAYOUT_KEY,
} from './panel-layout';
import type { PanelKey } from '@/components/panel/PanelDock';

export function usePanelLayout() {
	// Dock layout: columns laid out left→right, each holding up to 2
	// panels stacked top→bottom. Open order determines placement.
	// Persisted so leaving and returning to /chat keeps the same panels.
	const [panelLayout, setPanelLayout] = useState<PanelKey[][]>(loadPanelLayout);

	useEffect(() => {
		localStorage.setItem(PANEL_LAYOUT_KEY, JSON.stringify(panelLayout));
	}, [panelLayout]);

	// Toggle a panel open/closed from the top-bar buttons.
	const togglePanel = useCallback((key: PanelKey) => {
		setPanelLayout((layout) =>
			layout.some((column) => column.includes(key))
				? closePanelInLayout(layout, key)
				: openPanelInLayout(layout, key),
		);
	}, []);

	// Close a panel (driven by the panel's own close button).
	const closePanel = useCallback((key: PanelKey) => {
		setPanelLayout((layout) => closePanelInLayout(layout, key));
	}, []);

	const isPanelOpen = useCallback(
		(key: PanelKey) => panelLayout.some((column) => column.includes(key)),
		[panelLayout],
	);
	return { panelLayout, setPanelLayout, togglePanel, closePanel, isPanelOpen };
}
