import type { ThinkingBlock } from '@agentscope-ai/agentscope/message';
import { ChevronRight } from 'lucide-react';
import { useEffect, useState } from 'react';

import { Markdown } from '@/components/markdown';
import {
	Collapsible,
	CollapsibleContent,
	CollapsibleTrigger,
} from '@/components/ui/collapsible.tsx';
import { useTranslation } from '@/i18n/useI18n';
import { cn } from '@/lib/utils';
import { formatTime } from '@/utils/common';

/**
 * A thinking block with a live-ticking "thinking for Xs" header. Kept as its
 * own component so only thinking blocks pay for the per-second timer.
 */
export function ThinkingBlockView({ block }: { block: ThinkingBlock }) {
	const { t } = useTranslation();
	const isRunning = !block.finished_at;

	// Tick once per second while running so the elapsed time updates live.
	const [now, setNow] = useState(() => Date.now());
	useEffect(() => {
		if (!isRunning) return;
		const id = setInterval(() => setNow(Date.now()), 1000);
		return () => clearInterval(id);
	}, [isRunning]);

	const startMs = new Date(block.created_at).getTime();
	const endMs = isRunning ? now : new Date(block.finished_at!).getTime();
	const elapsedSeconds = Math.max(0, (endMs - startMs) / 1000);
	const elapsedText = formatTime(elapsedSeconds);
	return (
		<Collapsible>
			<CollapsibleTrigger asChild>
				<div
					className={cn(
						'group w-full flex items-center gap-2 text-left text-sm text-muted-foreground cursor-pointer',
						isRunning && 'shimmer',
					)}
				>
					<span>
						{t(elapsedText === '0s' ? 'messageBubble.thinking' : 'messageBubble.thinkingFor', {
							duration: elapsedText,
						})}
					</span>
					<ChevronRight className="hidden group-hover:flex group-data-[state=open]:flex size-3 shrink-0 transition-transform group-data-[state=open]:rotate-90" />
				</div>
			</CollapsibleTrigger>
			<CollapsibleContent asChild>
				<Markdown
					animated
					isAnimating={isRunning}
					className="text-muted-foreground bg-muted p-2 rounded text-sm"
				>
					{block.thinking}
				</Markdown>
			</CollapsibleContent>
		</Collapsible>
	);
}
