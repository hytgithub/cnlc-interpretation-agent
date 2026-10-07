import { Blocks, Check, Download, TriangleAlert } from 'lucide-react';
import { useCallback, useState } from 'react';

import { CardItem } from './card-item';
import type { HubInfo, SkillCard } from '@/api';
import { hubApi } from '@/api';
import { ApiError } from '@/api/client';
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
import { useResourceDrawer } from '@/hooks/useResourceDrawer.ts';
import { useSkillHubCards } from '@/hooks/useSkillHubCards.ts';
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
	const [installingId, setInstallingId] = useState<string | null>(null);
	const drawer = useResourceDrawer(
		useCallback(
			(skill) => hubApi.skill.getCard(skill.hub_id as string, (skill as SkillCard).id),
			[],
		),
	);
	// Read once per mount: reading the clock during render is impure, and
	// a browse session is far shorter than the units this rounds to.
	const [now] = useState(() => Date.now() / 1000);
	const { cards, loading, loadingMore, error, hasMore, loadMore, refetch } = useSkillHubCards(
		hubId,
		query,
	);

	// A skill needs no configuration, so there is nothing to ask for —
	// unlike an MCP install, this goes straight through without a dialog.
	const handleInstall = async (card: SkillCard) => {
		setInstallingId(card.id);
		try {
			await hubApi.skill.install(card.hub_id, card.id);
			onInstalled();
		} catch (e) {
			// A 409 already surfaced as a toast from the client.
			if (!(e instanceof ApiError)) throw e;
		} finally {
			setInstallingId(null);
		}
	};

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
				placeholder: t('skill.searchPlaceholder'),
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
							<EmptyTitle>{t('skill.loadFailedTitle')}</EmptyTitle>
							<EmptyDescription>{t('skill.loadFailedDescription')}</EmptyDescription>
						</EmptyHeader>
						<EmptyContent>
							<Button variant="outline" size="sm" onClick={refetch}>
								{t('skill.retry')}
							</Button>
						</EmptyContent>
					</Empty>
				) : cards.length === 0 ? (
					<Empty className="border-none py-10">
						<EmptyHeader>
							<EmptyMedia variant="icon">
								<Blocks />
							</EmptyMedia>
							<EmptyTitle>{t('skill.noCardsTitle')}</EmptyTitle>
							<EmptyDescription>{t('skill.noCardsDescription')}</EmptyDescription>
						</EmptyHeader>
					</Empty>
				) : (
					<ItemGroup className="gap-0">
						{cards.map((card) => (
							<CardItem
								key={`${card.hub_id}:${card.id}`}
								card={card}
								installed={installedNames.has(card.name)}
								installing={installingId === card.id}
								now={now}
								onInstall={() => handleInstall(card)}
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
				action={
					<Button
						disabled={
							drawer.opened !== null &&
							(installedNames.has(drawer.opened.name) ||
								installingId === (drawer.opened as SkillCard).id)
						}
						onClick={() => drawer.opened && handleInstall(drawer.opened as SkillCard)}
					>
						{drawer.opened && installedNames.has(drawer.opened.name) ? <Check /> : <Download />}
						{t(
							drawer.opened && installedNames.has(drawer.opened.name)
								? 'skill.installed'
								: 'skill.install',
						)}
					</Button>
				}
			/>
		</ResourcePanel>
	);
}
