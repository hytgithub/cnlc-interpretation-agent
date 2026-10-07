import 'streamdown/styles.css';

import { ReplyFinishedReason } from '@agentscope-ai/agentscope/event';
import type { DataBlock, Msg, TextBlock, ToolCallBlock } from '@agentscope-ai/agentscope/message';
import { ArrowDown, ArrowUp, CheckCircle, Loader2, TriangleAlert } from 'lucide-react';
import { memo, useEffect, useState } from 'react';

import { AudioInlineControl } from './audio-block';
import { ASBlock } from './content-block';
import { CopyButton } from './copy-button';
import { groupToolCalls } from './tool-call-groups';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { AttachmentGroup } from '@/components/ui/attachment.tsx';
import { Badge } from '@/components/ui/badge';
import { Bubble, BubbleContent } from '@/components/ui/bubble.tsx';
import { Message, MessageContent, MessageFooter } from '@/components/ui/message';
import { useTranslation } from '@/i18n/useI18n';
import { formatNumber, formatTime } from '@/utils/common';

interface MessageBubbleProps {
	message: Msg;
	onUserConfirm: (
		toolCallBlock: ToolCallBlock,
		confirm: boolean,
		replyId: string,
		rules?: ToolCallBlock['suggested_rules'],
	) => void;
}

/**
 * A message bubble component that displays a chat message.
 *
 * Running state is derived from `message.finished_at`: a missing or null
 * `finished_at` means the agent is still producing this reply. The bottom
 * status row shows a single left-aligned badge laid out as
 * `[state-icon] [duration] [↑in ↓out]`:
 *   - State icon: spinning `Loader2` while running, static `CheckCircle`
 *     once finished.
 *   - Duration is `now - created_at` while running (ticking each second),
 *     `finished_at - created_at` once complete.
 *   - Token counts only appear once `usage` is populated with non-zero
 *     values — typically after the message finishes.
 *
 * When `content` is empty and the message is still running, the bubble
 * body is omitted entirely so only the bottom status row renders.
 */
function ASMessageBubbleComponent({ message }: MessageBubbleProps) {
	const isUser = message.role === 'user';
	const { t } = useTranslation();

	const isRunning = !message.finished_at;
	const hasUsage =
		!!message.usage &&
		((message.usage.input_tokens ?? 0) > 0 || (message.usage.output_tokens ?? 0) > 0);

	// Tick once per second while running so the elapsed time updates live.
	const [now, setNow] = useState(() => Date.now());
	useEffect(() => {
		if (!isRunning) return;
		const id = setInterval(() => setNow(Date.now()), 1000);
		return () => clearInterval(id);
	}, [isRunning]);

	// Audio data blocks are rendered in the footer;
	// For role="user" messages, the data blocks are rendered as attachments in the
	// footer, while for role="assistant" messages, the data is rendered in its
	// original position
	const audioBlocks = message.content.filter(
		(b): b is DataBlock => b.type === 'data' && b.source.media_type.split('/')[0] === 'audio',
	);

	const blocks = groupToolCalls(message.content);

	// What the copy button hands over — the prose of the message, without
	// the tool calls and attachments around it.
	const plainText = message.content
		.filter((b): b is TextBlock => b.type === 'text')
		.map((b) => b.text)
		.join('\n\n');

	const startMs = new Date(message.created_at).getTime();
	const endMs = isRunning ? now : new Date(message.finished_at!).getTime();
	const elapsedSeconds = Math.max(0, (endMs - startMs) / 1000);
	const elapsedText = formatTime(elapsedSeconds);

	return (
		<Message align={isUser ? 'end' : 'start'} data-role={message.role}>
			<MessageContent>
				{blocks
					.filter((block) => block.type !== 'data')
					.map((block, index) => (
						<Bubble key={index} variant={isUser ? 'muted' : 'ghost'}>
							<BubbleContent>
								<ASBlock block={block} />
							</BubbleContent>
						</Bubble>
					))}
				{message.finished_reason === ReplyFinishedReason.ERROR && (
					<Alert
						variant="destructive"
						className="m-2 w-[calc(100%-1rem)] border-red-200 bg-red-50 text-destructive dark:border-red-900 dark:bg-red-950 dark:text-red-50"
					>
						<TriangleAlert />
						<AlertTitle>{t('messageBubble.error.title')}</AlertTitle>
						<AlertDescription>
							{t(`messageBubble.error.${message.error?.type ?? 'unknown'}`, {
								defaultValue: message.error?.message ?? t('messageBubble.error.unknown'),
							})}
						</AlertDescription>
					</Alert>
				)}
				<AttachmentGroup className="max-w-full">
					{blocks
						.filter((block) => block.type === 'data')
						.map((block, index) => (
							<ASBlock block={block} key={index} />
						))}
				</AttachmentGroup>
				{message.role === 'user' ? (
					plainText && (
						<MessageFooter>
							<CopyButton text={plainText} />
						</MessageFooter>
					)
				) : (
					<MessageFooter className="gap-1 font-mono">
						<Badge
							variant="secondary"
							aria-label={isRunning ? t('messageBubble.running') : undefined}
						>
							{isRunning ? (
								<Loader2 data-icon="inline-start" className="animate-spin" />
							) : (
								<CheckCircle data-icon="inline-start" />
							)}
							<span className="tabular-nums tracking-tighter">{elapsedText}</span>
							{hasUsage && (
								<>
									<ArrowUp data-icon="inline-start" className="ml-1" />
									<span className="tabular-nums">
										{formatNumber(message.usage?.input_tokens ?? 0)}
									</span>
									<ArrowDown data-icon="inline-start" className="ml-1" />
									<span className="tabular-nums">
										{formatNumber(message.usage?.output_tokens ?? 0)}
									</span>
								</>
							)}
							{audioBlocks.map((block) => (
								<AudioInlineControl key={block.id} block={block} />
							))}
						</Badge>
						{plainText && <CopyButton text={plainText} />}
					</MessageFooter>
				)}
			</MessageContent>
		</Message>
	);
}

/**
 * Memoised: a streaming reply publishes a new `Msg` object on every delta
 * (see ``useMessages``) while the messages around it keep their identity,
 * so only the bubble that actually changed re-renders. A message mutated
 * in place would therefore *not* repaint — new content has to arrive as a
 * new object.
 */
export const ASMessageBubble = memo(ASMessageBubbleComponent);
export { ASBlock } from './content-block';
