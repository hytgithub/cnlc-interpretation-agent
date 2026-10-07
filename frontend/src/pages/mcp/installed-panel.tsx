import { Blocks, Pencil, Plug, Trash2 } from 'lucide-react';
import { useState } from 'react';

import type { MCPView } from '@/api';
import { ResourcePanel } from '@/components/hub/ResourcePanel.tsx';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar.tsx';
import { Button } from '@/components/ui/button.tsx';
import {
	Empty,
	EmptyDescription,
	EmptyHeader,
	EmptyMedia,
	EmptyTitle,
} from '@/components/ui/empty.tsx';
import {
	Item,
	ItemActions,
	ItemContent,
	ItemDescription,
	ItemGroup,
	ItemMedia,
	ItemTitle,
} from '@/components/ui/item.tsx';
import { Spinner } from '@/components/ui/spinner.tsx';
import { useTranslation } from '@/i18n/useI18n';
import { avatarTint } from '@/utils/common';

export interface MinePanelProps {
	mcps: MCPView[];
	loading: boolean;
	onEdit: (mcp: MCPView) => void;
	onRemove: (mcpId: string) => void;
}

export function MinePanel({ mcps, loading, onEdit, onRemove }: MinePanelProps) {
	const { t } = useTranslation();
	const [query, setQuery] = useState('');

	// Filtered client-side: the library is the user's own and small, so a
	// round trip per keystroke would buy nothing.
	const needle = query.trim().toLowerCase();
	const shown = needle
		? mcps.filter((mcp) =>
				[mcp.name, mcp.display_name ?? '', mcp.description, ...mcp.tags].some((field) =>
					field.toLowerCase().includes(needle),
				),
			)
		: mcps;

	return (
		<ResourcePanel
			title={t('common.my-mcp')}
			description={t('mcp.mineDescription')}
			icon={<Plug className="size-5 text-muted-foreground" />}
			search={
				// Hidden while there is nothing to search through.
				mcps.length > 0
					? {
							value: query,
							onChange: setQuery,
							placeholder: t('mcp.mineSearchPlaceholder'),
						}
					: undefined
			}
		>
			{loading ? (
				<div className="flex justify-center py-10">
					<Spinner />
				</div>
			) : mcps.length === 0 ? (
				<Empty className="border-none py-10">
					<EmptyHeader>
						<EmptyMedia variant="icon">
							<Plug />
						</EmptyMedia>
						<EmptyTitle>{t('mcp.mineEmptyTitle')}</EmptyTitle>
						<EmptyDescription>{t('mcp.mineEmptyDescription')}</EmptyDescription>
					</EmptyHeader>
				</Empty>
			) : shown.length === 0 ? (
				<Empty className="border-none py-10">
					<EmptyHeader>
						<EmptyMedia variant="icon">
							<Blocks />
						</EmptyMedia>
						<EmptyTitle>{t('mcp.noCardsTitle')}</EmptyTitle>
						<EmptyDescription>{t('mcp.noCardsDescription')}</EmptyDescription>
					</EmptyHeader>
				</Empty>
			) : (
				<ItemGroup className="gap-0">
					{shown.map((mcp) => (
						<Item key={mcp.id}>
							<ItemMedia>
								<Avatar className="rounded-md">
									<AvatarImage
										src={mcp.icon_url ?? undefined}
										alt={mcp.display_name || mcp.name}
										loading="lazy"
									/>
									<AvatarFallback className="rounded-md" style={avatarTint(mcp.name)}>
										{(mcp.display_name || mcp.name).slice(0, 1).toUpperCase()}
									</AvatarFallback>
								</Avatar>
							</ItemMedia>

							<ItemContent>
								<ItemTitle>
									<span className="font-medium">{mcp.display_name || mcp.name}</span>
									{mcp.author && (
										<span className="text-xs text-muted-foreground">@{mcp.author}</span>
									)}
									{mcp.is_stateful && (
										<span key={'state'} className="text-xs text-muted-foreground/60">
											#{t('mcp.stateful')}
										</span>
									)}
									{mcp.tags.slice(0, 4).map((tag) => (
										<span key={tag} className="text-xs text-muted-foreground/60">
											#{tag}
										</span>
									))}
								</ItemTitle>
								<ItemDescription className="line-clamp-1">{mcp.description}</ItemDescription>
							</ItemContent>

							<ItemActions className="gap-1">
								{mcp.version && (
									<span className="text-xs text-muted-foreground whitespace-nowrap">
										{mcp.version}
									</span>
								)}
								{mcp.hub_id && mcp.card_id && (
									<Button
										size="icon-sm"
										variant="ghost"
										className="text-muted-foreground"
										onClick={() => onEdit(mcp)}
										title={t('common.edit')}
									>
										<Pencil />
									</Button>
								)}
								<Button
									size="icon-sm"
									variant="ghost"
									className="text-muted-foreground"
									onClick={() => onRemove(mcp.id)}
									title={t('common.delete')}
								>
									<Trash2 />
								</Button>
							</ItemActions>
						</Item>
					))}
				</ItemGroup>
			)}
		</ResourcePanel>
	);
}
