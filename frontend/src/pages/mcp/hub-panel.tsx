import { Blocks, Check, Download, TriangleAlert } from 'lucide-react';
import { useCallback, useState } from 'react';

import { CardItem } from './card-item';
import { MCPDetailBody } from './detail-body';
import type { HubInfo, MCPCard } from '@/api';
import { hubApi } from '@/api';
import { InstallMCPDialog } from '@/components/dialog/InstallMCPDialog.tsx';
import { ResourceDetailDrawer } from '@/components/drawer/ResourceDetailDrawer.tsx';
import { LoadMore } from '@/components/hub/LoadMore.tsx';
import { ResourcePanel } from '@/components/hub/ResourcePanel.tsx';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar.tsx';
import { Button } from '@/components/ui/button.tsx';
import {
	Empty,
	EmptyContent,
	EmptyDescription,
	EmptyHeader,
	EmptyMedia,
	EmptyTitle,
} from '@/components/ui/empty.tsx';
import { ItemGroup } from '@/components/ui/item.tsx';
import { Spinner } from '@/components/ui/spinner.tsx';
import { useMCPHubCards } from '@/hooks/useMCPHubCards.ts';
import { useResourceDrawer } from '@/hooks/useResourceDrawer.ts';
import { useTranslation } from '@/i18n/useI18n';
import { avatarTint } from '@/utils/common';

export interface HubPanelProps {
	hubId: string;
	hub?: HubInfo;
	installedNames: Set<string>;
	onInstalled: () => void;
}

export function HubPanel({ hubId, hub, installedNames, onInstalled }: HubPanelProps) {
	const { t } = useTranslation();
	const [query, setQuery] = useState('');
	const [installing, setInstalling] = useState<MCPCard | null>(null);
	// Read once per mount: reading the clock during render is impure, and
	// a browse session is far shorter than the units this rounds to.
	const [now] = useState(() => Date.now() / 1000);
	// The list already carries everything the drawer shows, but the detail
	// endpoint is where a hub may fill in more.
	const drawer = useResourceDrawer(
		useCallback((card) => hubApi.mcp.getCard(card.hub_id as string, (card as MCPCard).id), []),
	);
	const { cards, loading, loadingMore, error, hasMore, loadMore, refetch } = useMCPHubCards(
		hubId,
		query,
	);

	return (
		// Falls back to the raw id while the hub list is still loading.
		<ResourcePanel
			title={hub?.display_name ?? hubId}
			description={hub?.description}
			icon={
				<Avatar className="rounded-md">
					<AvatarImage src={hub?.icon_url ?? undefined} alt={hub?.display_name ?? hubId} />
					<AvatarFallback className="rounded-md" style={avatarTint(hubId)}>
						{(hub?.display_name ?? hubId).slice(0, 1).toUpperCase()}
					</AvatarFallback>
				</Avatar>
			}
			search={{
				value: query,
				onChange: setQuery,
				placeholder: t('mcp.searchPlaceholder'),
			}}
		>
			<div className="flex flex-col gap-y-4">
				{loading ? (
					<div className="flex justify-center py-10">
						<Spinner />
					</div>
				) : error ? (
					<Empty className="border-none py-10">
						<EmptyHeader>
							<EmptyMedia variant="icon">
								<TriangleAlert />
							</EmptyMedia>
							<EmptyTitle>{t('mcp.loadFailedTitle')}</EmptyTitle>
							<EmptyDescription>{t('mcp.loadFailedDescription')}</EmptyDescription>
						</EmptyHeader>
						<EmptyContent>
							<Button variant="outline" size="sm" onClick={refetch}>
								{t('mcp.retry')}
							</Button>
						</EmptyContent>
					</Empty>
				) : cards.length === 0 ? (
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
						{cards.map((card) => (
							<CardItem
								key={`${card.hub_id}:${card.id}`}
								card={card}
								installed={installedNames.has(card.name)}
								now={now}
								onInstall={() => setInstalling(card)}
								onOpen={() => drawer.open(card)}
							/>
						))}
					</ItemGroup>
				)}

				{/* Cursor pagination — no page numbers and no total to show. */}
				{hasMore && <LoadMore shown={cards.length} loading={loadingMore} onLoad={loadMore} />}
			</div>

			<ResourceDetailDrawer
				skill={drawer.opened}
				loading={drawer.loading}
				onOpenChange={(open) => {
					if (!open) drawer.close();
				}}
				body={<MCPDetailBody card={drawer.opened as MCPCard | null} />}
				action={
					<Button
						disabled={drawer.opened !== null && installedNames.has(drawer.opened.name)}
						onClick={() => {
							// One overlay at a time: the install form replaces
							// the drawer rather than stacking on top of it.
							setInstalling(drawer.opened as MCPCard);
							drawer.close();
						}}
					>
						{drawer.opened && installedNames.has(drawer.opened.name) ? <Check /> : <Download />}
						{t(
							drawer.opened && installedNames.has(drawer.opened.name)
								? 'mcp.installed'
								: 'mcp.install',
						)}
					</Button>
				}
			/>

			<InstallMCPDialog
				card={installing}
				onOpenChange={(open) => {
					if (!open) setInstalling(null);
				}}
				onInstalled={onInstalled}
			/>
		</ResourcePanel>
	);
}
