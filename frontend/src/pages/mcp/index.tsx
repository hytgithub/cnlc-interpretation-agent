import { Blocks, Plug, TriangleAlert } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { HubPanel } from './hub-panel';
import { MinePanel } from './installed-panel';
import type { MCPCard, MCPView } from '@/api';
import { hubApi } from '@/api';
import { InstallMCPDialog } from '@/components/dialog/InstallMCPDialog.tsx';
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
import {
	Sidebar,
	SidebarContent,
	SidebarGroup,
	SidebarGroupContent,
	SidebarGroupLabel,
	SidebarHeader,
	SidebarMenu,
	SidebarMenuButton,
	SidebarMenuItem,
} from '@/components/ui/sidebar.tsx';
import { Spinner } from '@/components/ui/spinner.tsx';
import { useMCPHubs } from '@/hooks/useMCPHubs.ts';
import { useMCPs } from '@/hooks/useMCPs.ts';
import { useTranslation } from '@/i18n/useI18n';
import { avatarTint } from '@/utils/common';

export function MCPHubPage() {
	const { t } = useTranslation();
	const navigate = useNavigate();
	// No `hubId` in the URL means the "mine" tab, which is the default.
	const { hubId } = useParams<{ hubId?: string }>();
	const { hubs, loading: hubsLoading, error: hubsError, refetch } = useMCPHubs();
	// Loaded page-wide, not per panel: the hub view needs it to mark cards
	// as already installed, and the "mine" view to list them.
	const { mcps, loading: mcpsLoading, refetch: refetchMcps, remove } = useMCPs();
	const installedNames = new Set(mcps.map((mcp) => mcp.name));
	// Editing re-opens the install form against the originating card, so
	// the card has to be fetched before the dialog can render its inputs.
	const [editing, setEditing] = useState<MCPView | null>(null);
	const [editingCard, setEditingCard] = useState<MCPCard | null>(null);

	useEffect(() => {
		if (!editing?.hub_id || !editing.card_id) return;
		let current = true;
		hubApi.mcp
			.getCard(editing.hub_id, editing.card_id)
			.then((card) => {
				if (current) setEditingCard(card);
			})
			.catch(() => {
				// The hub is gone or the card was dropped; the dialog stays
				// shut and the toast from the client says why.
				if (current) setEditing(null);
			});
		return () => {
			current = false;
		};
	}, [editing]);

	return (
		<div className="flex size-full p-2 gap-2">
			<Sidebar collapsible="none" className="rounded-[22px]">
				<SidebarHeader className="flex flex-col p-[20px_18px_14px] gap-y-1">
					<div className="text-xl font-medium tracking-[-0.02em] text-foreground">
						{t('common.mcp-hub')}
					</div>
					<div className="text-text-tertiary text-xs">{t('mcp.subtitle')}</div>
				</SidebarHeader>
				<SidebarContent>
					<SidebarGroup className="mt-6 px-2 py-0">
						<SidebarGroupLabel>{t('common.mine')}</SidebarGroupLabel>
						<SidebarGroupContent>
							<SidebarMenu>
								<SidebarMenuItem>
									<SidebarMenuButton isActive={!hubId} onClick={() => navigate('/mcp')}>
										<Plug />
										<span className="min-w-0 flex-1 truncate">{t('common.my-mcp')}</span>
										<span className="font-mono text-[10px] text-text-data">{mcps.length}</span>
									</SidebarMenuButton>
								</SidebarMenuItem>
							</SidebarMenu>
						</SidebarGroupContent>
					</SidebarGroup>

					<SidebarGroup className="mt-5 px-2 py-0">
						<SidebarGroupLabel className="justify-between">
							{t('mcp.hubsLabel')}
							{hubs.length > 0 && (
								<span className="text-[10px] text-text-data font-mono">{hubs.length}</span>
							)}
						</SidebarGroupLabel>
						<SidebarGroupContent>
							{hubsLoading ? (
								<div className="flex justify-center py-4">
									<Spinner />
								</div>
							) : hubsError ? (
								// Distinct from the empty state on purpose: a
								// failed request otherwise reads as "no hubs
								// configured", pointing at the wrong problem.
								<Empty className="border-none py-4 min-h-40">
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
							) : hubs.length === 0 ? (
								<Empty className="border-none py-4 min-h-40">
									<EmptyHeader>
										<EmptyMedia variant="icon">
											<Blocks />
										</EmptyMedia>
										<EmptyTitle>{t('mcp.noHubsTitle')}</EmptyTitle>
										<EmptyDescription>{t('mcp.noHubsDescription')}</EmptyDescription>
									</EmptyHeader>
								</Empty>
							) : (
								<SidebarMenu>
									{hubs.map((hub) => (
										<SidebarMenuItem key={hub.hub_id}>
											<SidebarMenuButton
												isActive={hubId === hub.hub_id}
												onClick={() => navigate(`/mcp/${hub.hub_id}`)}
												title={hub.description}
											>
												<Avatar className="size-4 rounded-sm">
													<AvatarImage src={hub.icon_url ?? undefined} alt={hub.display_name} />
													<AvatarFallback
														className="rounded-sm text-[10px]"
														style={avatarTint(hub.hub_id)}
													>
														{hub.display_name.slice(0, 1).toUpperCase()}
													</AvatarFallback>
												</Avatar>
												<span className="min-w-0 flex-1 truncate">{hub.display_name}</span>
											</SidebarMenuButton>
										</SidebarMenuItem>
									))}
								</SidebarMenu>
							)}
						</SidebarGroupContent>
					</SidebarGroup>
				</SidebarContent>
			</Sidebar>

			<main className="flex-1 min-w-0 min-h-0 overflow-hidden rounded-[22px] bg-card shadow-panel">
				{hubId ? (
					// Remount on hub change so the panel's query box resets.
					<HubPanel
						key={hubId}
						hubId={hubId}
						hub={hubs.find((h) => h.hub_id === hubId)}
						installedNames={installedNames}
						onInstalled={refetchMcps}
					/>
				) : (
					<MinePanel mcps={mcps} loading={mcpsLoading} onEdit={setEditing} onRemove={remove} />
				)}
			</main>

			<InstallMCPDialog
				card={editing ? editingCard : null}
				editing={editing}
				onOpenChange={(open) => {
					if (!open) {
						setEditing(null);
						setEditingCard(null);
					}
				}}
				onInstalled={refetchMcps}
			/>
		</div>
	);
}
