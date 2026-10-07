import type { DataBlock, TextBlock } from '@agentscope-ai/agentscope/message';
import { ChevronRight, FileText, FileVideo2 } from 'lucide-react';
import * as mime from 'mime-types';

import { ThinkingBlockView } from './thinking-block';
import type { ExtendedContentBlock } from './tool-call-groups';
import { summarizeToolGroup } from './tool-group-summary';
import { renderToolCall } from './tool-renderers';
import { DiffStats } from './tool-renderers/_shared';
import { splitInlineCurvePlots } from './tool-renderers/curve-plot-data';
import { Markdown } from '@/components/markdown';
import {
	Attachment,
	AttachmentContent,
	AttachmentDescription,
	AttachmentMedia,
	AttachmentTitle,
} from '@/components/ui/attachment.tsx';
import {
	Collapsible,
	CollapsibleContent,
	CollapsibleTrigger,
} from '@/components/ui/collapsible.tsx';
import { useTranslation } from '@/i18n/useI18n';
import { cn } from '@/lib/utils';

export interface ASBlockProps {
	block: ExtendedContentBlock;
}

export function ASBlock({ block, ...props }: ASBlockProps) {
	const { t } = useTranslation();

	switch (block.type) {
		case 'text':
			return (
				<Markdown animated isAnimating={!block.finished_at} {...props}>
					{block.text}
				</Markdown>
			);
		case 'data': {
			const dataType = block.source.media_type.split('/')[0];
			if (dataType === 'audio') return null;
			const data =
				block.source.type === 'url'
					? block.source.url
					: `data:${block.source.media_type};base64,${block.source.data}`;
			switch (dataType) {
				case 'image':
					return (
						<Attachment>
							<AttachmentMedia variant={'image'}>
								<img src={data} alt={block.name || 'Uploaded image'} />
							</AttachmentMedia>
							<AttachmentContent>
								<AttachmentTitle>{block.name}</AttachmentTitle>
								<AttachmentDescription>
									{(mime.extension(block.source.media_type) || 'bin').toUpperCase()}
								</AttachmentDescription>
							</AttachmentContent>
						</Attachment>
					);
				case 'video':
					return (
						<Attachment>
							<AttachmentMedia variant={'icon'}>
								<FileVideo2 />
							</AttachmentMedia>
							<AttachmentContent>
								<AttachmentTitle>{block.name}</AttachmentTitle>
								<AttachmentDescription>
									{(mime.extension(block.source.media_type) || 'bin').toUpperCase()}
								</AttachmentDescription>
							</AttachmentContent>
						</Attachment>
					);
				default:
					// Unknown files
					return (
						<Attachment>
							<AttachmentMedia variant={'icon'}>
								<FileText />
							</AttachmentMedia>
							<AttachmentContent>
								<AttachmentTitle>{block.name}</AttachmentTitle>
								<AttachmentDescription>
									{(mime.extension(block.source.media_type) || 'bin').toUpperCase()}
								</AttachmentDescription>
							</AttachmentContent>
						</Attachment>
					);
			}
		}
		case 'thinking':
			return <ThinkingBlockView block={block} />;
		case 'hint': {
			// Parse source: try JSON, fall back to plain string, default to t('common.message').
			let hintLabel: string;
			let hintSublabel: string | null = null;

			if (block.source) {
				try {
					const parsed = JSON.parse(block.source) as {
						label?: string;
						sublabel?: string;
					};
					// Both halves go through the same i18n table, falling
					// back to the raw text for sources it doesn't cover.
					hintLabel = parsed.label
						? t(`messageBubble.hintSource.${parsed.label.toLowerCase()}`, {
								defaultValue: parsed.label,
							})
						: block.source;
					hintSublabel = parsed.sublabel
						? t(`messageBubble.hintSource.${parsed.sublabel.toLowerCase().replace(/\s+/g, '_')}`, {
								defaultValue: parsed.sublabel,
							})
						: null;
				} catch {
					hintLabel = block.source;
				}
			} else {
				hintLabel = t('common.message');
			}
			const items: (TextBlock | DataBlock)[] =
				typeof block.hint === 'string'
					? [
							{
								type: 'text',
								id: `${block.id}-text`,
								text: block.hint,
								created_at: block.created_at,
							},
						]
					: block.hint;
			return (
				<Collapsible>
					<CollapsibleTrigger asChild>
						<div
							className={cn(
								'group w-full flex gap-2 items-center text-sm text-muted-foreground cursor-pointer hover:text-primary',
								!block.finished_at && 'shimmer',
							)}
						>
							<span>{hintLabel + (hintSublabel ? ` - ${hintSublabel}` : '')}</span>
							<ChevronRight className="size-3 shrink-0 transition-transform group-data-[state=open]:rotate-90" />
						</div>
					</CollapsibleTrigger>
					<CollapsibleContent className="bg-muted p-2 rounded text-sm">
						{items.map((item, index) => (
							<ASBlock block={item} key={index} />
						))}
					</CollapsibleContent>
				</Collapsible>
			);
		}
		case 'tool_call_group': {
			const { inlinePlots, collapsedCalls } = splitInlineCurvePlots(block.calls);
			const { title, insertions, deletions } = summarizeToolGroup(collapsedCalls, t);
			const hasRunningCall = collapsedCalls.some((c) => !c.result || c.result.state === 'running');
			return (
				<>
				{collapsedCalls.length > 0 && <Collapsible defaultOpen={false}>
					<CollapsibleTrigger asChild>
						<div
							className={cn(
								'group w-full flex gap-2 items-center text-sm text-muted-foreground cursor-pointer hover:text-primary',
								hasRunningCall && 'shimmer',
							)}
						>
							<span>{title}</span>
							<ChevronRight className="size-3 shrink-0 transition-transform group-data-[state=open]:rotate-90" />
							<DiffStats insertions={insertions} deletions={deletions} />
						</div>
					</CollapsibleTrigger>
					<CollapsibleContent className="flex flex-col w-full gap-y-1 bg-muted p-2 rounded text-sm text-muted-foreground">
						{collapsedCalls.map((pair) => renderToolCall(pair, t))}
					</CollapsibleContent>
				</Collapsible>}
				{inlinePlots.map((pair) => renderToolCall(pair, t))}
				</>
			);
		}

		default:
			return null;
	}
}
