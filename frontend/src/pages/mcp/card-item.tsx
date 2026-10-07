import { Check, Download } from 'lucide-react';

import type { MCPCard } from '@/api';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar.tsx';
import { Badge } from '@/components/ui/badge.tsx';
import { Button } from '@/components/ui/button.tsx';
import {
	Item,
	ItemActions,
	ItemContent,
	ItemDescription,
	ItemMedia,
	ItemTitle,
} from '@/components/ui/item.tsx';
import { useTranslation } from '@/i18n/useI18n';
import { cn } from '@/lib/utils';
import { avatarTint, formatTime } from '@/utils/common';

export interface CardItemProps {
	card: MCPCard;
	installed: boolean;
	/** "Now" in epoch seconds, pinned by the panel so every row in a
	 *  render agrees and the age does not shift on unrelated re-renders. */
	now: number;
	onInstall: () => void;
	onOpen: () => void;
}

export function CardItem({ card, installed, now, onInstall, onOpen }: CardItemProps) {
	const { t } = useTranslation();

	return (
		<Item
			className={cn(
				'cursor-pointer items-start rounded-none border-l-2 py-[13px] pr-[18px] pl-4 hover:bg-row-hover',
				// The left rule is the "installed" marker. Only the icon
				// dims with it — fading the whole row would drop the
				// description to a 2.4:1 contrast ratio.
				installed ? 'border-l-foreground' : 'border-l-transparent',
			)}
			onClick={onOpen}
		>
			<ItemMedia className={cn('translate-y-0', installed && 'opacity-55')}>
				<Avatar className="rounded-md">
					<AvatarImage
						src={card.icon_url ?? undefined}
						alt={card.display_name || card.name}
						loading="lazy"
					/>
					<AvatarFallback className="rounded-md" style={avatarTint(card.name)}>
						{(card.display_name || card.name).slice(0, 1).toUpperCase()}
					</AvatarFallback>
				</Avatar>
			</ItemMedia>

			<ItemContent>
				{/* Name, author, tags — each step lighter than the last, so
				    the eye lands on the name first. */}
				<ItemTitle>
					<span className="font-medium">{card.display_name || card.name}</span>
					{card.author && <span className="text-xs text-muted-foreground">@{card.author}</span>}
					{card.auth === 'inputs' && (
						// Sans, not mono: this one is a warning meant for a
						// person, while the tags below are machine metadata.
						<Badge className="rounded-full border-0 bg-amber-600/10 px-2 py-0.5 text-[10.5px] font-normal text-amber-700">
							{t('mcp.needsConfig')}
						</Badge>
					)}
					{card.tags.slice(0, 4).map((tag) => (
						<Badge
							key={tag}
							variant="secondary"
							className="rounded-full bg-secondary px-1.75 py-0.5 font-mono text-[10px] font-normal text-text-tertiary"
						>
							{tag}
						</Badge>
					))}
				</ItemTitle>
				<ItemDescription className="line-clamp-1">{card.description}</ItemDescription>
			</ItemContent>

			<ItemActions className="items-center gap-3 self-center">
				<span className="font-mono text-[10px] text-text-data whitespace-nowrap">
					{card.updated_at
						? now - card.updated_at < 3600
							? t('skill.updatedRecently')
							: t('skill.updatedAgo', {
									ago: formatTime(now - card.updated_at, {
										leadingUnitOnly: true,
									}),
								})
						: null}
				</span>
				<div className="flex h-8 items-center gap-2">
					{/* Explicit null check: a hub reporting 0 installs is
					    saying something, one that does not count them is not. */}
					{card.installs != null && (
						<span className="inline-flex items-center gap-1 font-mono text-[10px] text-text-data">
							<Download className="size-3" />
							{card.installs.toLocaleString()}
						</span>
					)}
					{installed ? (
						// A state, not an action — a disabled button would
						// still read as something you could have clicked.
						<span className="flex h-7 items-center gap-x-[5px] rounded-full bg-surface-muted px-3 text-[11.5px] text-muted-foreground">
							<Check className="size-3" />
							{t('mcp.installed')}
						</span>
					) : (
						<Button
							className="h-7 rounded-full px-3.5 text-xs font-normal hover:opacity-86"
							// Installing straight from the row must not also
							// open the drawer behind it.
							onClick={(e) => {
								e.stopPropagation();
								onInstall();
							}}
						>
							{t('mcp.install')}
						</Button>
					)}
				</div>
			</ItemActions>
		</Item>
	);
}
