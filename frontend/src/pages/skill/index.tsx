import { Blocks, Plug, TriangleAlert } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';

import { HubPanel } from './hub-panel';
import { MinePanel } from './installed-panel';
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
import { useSkillHubs } from '@/hooks/useSkillHubs.ts';
import { useSkills } from '@/hooks/useSkills.ts';
import { useTranslation } from '@/i18n/useI18n';
import { avatarTint } from '@/utils/common';

export function SkillHubPage() {
	const { t } = useTranslation();
	const navigate = useNavigate();
	// No `hubId` in the URL means the "mine" tab, which is the default.
	const { hubId } = useParams<{ hubId?: string }>();
	const { hubs, loading: hubsLoading, error: hubsError, refetch } = useSkillHubs();
	// Loaded page-wide, not per panel: the hub view needs it to mark cards
	// as already installed, and the "mine" view to list them.
	const { skills, loading: skillsLoading, refetch: refetchSkills, remove } = useSkills();
	const installedNames = new Set(skills.map((skill) => skill.name));

	return (
		<div className="flex size-full p-2 gap-2">
			<Sidebar collapsible="none" className="rounded-[22px]">
				<SidebarHeader className="flex flex-col p-[20px_18px_14px] gap-y-1">
					<div className="text-xl font-medium tracking-[-0.02em] text-foreground">
						{t('common.skill-hub')}
					</div>
					<div className="text-text-tertiary text-xs">{t('skill.subtitle')}</div>
				</SidebarHeader>
				<SidebarContent>
					<SidebarGroup className="mt-6 px-2 py-0">
						<SidebarGroupLabel>{t('common.mine')}</SidebarGroupLabel>
						<SidebarGroupContent>
							<SidebarMenu>
								<SidebarMenuItem>
									<SidebarMenuButton isActive={!hubId} onClick={() => navigate('/skill')}>
										<Plug />
										<span className="min-w-0 flex-1 truncate">{t('common.my-skill')}</span>
										<span className="font-mono text-[10px] text-text-data">{skills.length}</span>
									</SidebarMenuButton>
								</SidebarMenuItem>
							</SidebarMenu>
						</SidebarGroupContent>
					</SidebarGroup>

					<SidebarGroup className="mt-5 px-2 py-0">
						<SidebarGroupLabel className="justify-between">
							{t('skill.hubsLabel')}
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
										<EmptyTitle>{t('skill.loadFailedTitle')}</EmptyTitle>
										<EmptyDescription>{t('skill.loadFailedDescription')}</EmptyDescription>
									</EmptyHeader>
									<EmptyContent>
										<Button variant="outline" size="sm" onClick={refetch}>
											{t('skill.retry')}
										</Button>
									</EmptyContent>
								</Empty>
							) : hubs.length === 0 ? (
								<Empty className="border-none py-4 min-h-40">
									<EmptyHeader>
										<EmptyMedia variant="icon">
											<Blocks />
										</EmptyMedia>
										<EmptyTitle>{t('skill.noHubsTitle')}</EmptyTitle>
										<EmptyDescription>{t('skill.noHubsDescription')}</EmptyDescription>
									</EmptyHeader>
								</Empty>
							) : (
								<SidebarMenu>
									{hubs.map((hub) => (
										<SidebarMenuItem key={hub.hub_id}>
											<SidebarMenuButton
												isActive={hubId === hub.hub_id}
												onClick={() => navigate(`/skill/${hub.hub_id}`)}
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
						onInstalled={refetchSkills}
					/>
				) : (
					<MinePanel skills={skills} loading={skillsLoading} onRemove={remove} />
				)}
			</main>
		</div>
	);
}
