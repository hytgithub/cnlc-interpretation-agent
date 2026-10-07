import { format } from 'date-fns';
import {
	BotMessageSquare,
	Cable,
	CalendarClock,
	Ellipsis,
	type LucideIcon,
	MessageSquareDashed,
	Pencil,
	Plus,
	Settings2,
	Trash2,
	Users,
} from 'lucide-react';

import type { useChatPageState } from './useChatPageState';
import type { SessionSourceKind } from '@/api';
import { AgentDialog } from '@/components/dialog/AgentDialog';
import { AgentSelect } from '@/components/select/AgentSelect';
import { Button } from '@/components/ui/button';
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuItem,
	DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
	Empty,
	EmptyDescription,
	EmptyHeader,
	EmptyMedia,
	EmptyTitle,
} from '@/components/ui/empty';
import {
	Sidebar,
	SidebarContent,
	SidebarGroup,
	SidebarGroupContent,
	SidebarGroupLabel,
	SidebarMenu,
	SidebarMenuAction,
	SidebarMenuBadge,
	SidebarMenuButton,
	SidebarMenuItem,
} from '@/components/ui/sidebar';

/**
 * The chat page's outer shell. Responsibilities split cleanly:
 *
 * - **This component** owns *which* `(agent, session)` is being
 *   viewed. The URL is the single source of truth: every selection
 *   (agent dropdown, session row, team member, new session) is a
 *   ``navigate(...)`` call. State is derived from ``useParams``,
 *   never duplicated in React state. Renders the main left sidebar
 *   (agent picker + session list + create/rename/delete actions) and
 *   computes the ``effective`` ids to feed the chat viewport.
 * - **`ChatViewport`** owns *what* to render for that pair: messages,
 *   model selector, permission mode, workspace drawer, team sidebar.
 *
 * Splitting along this seam means switching between the leader's
 * session and a focused team member is just a prop change for the
 * viewport — the leader's session list stays anchored in this outer
 * sidebar. Driving everything off URL also gets us browser back /
 * forward, shareable links, and refresh-preserving state for free.
 *
 * @returns The chat page JSX.
 */
// Icon per session origin, shown only when a sidebar mixes sources.
const SOURCE_ICON: Record<SessionSourceKind, LucideIcon> = {
	user: BotMessageSquare,
	schedule: CalendarClock,
	channel: Cable,
	team: Users,
};

export function ChatSessionSidebar({ state }: { state: ReturnType<typeof useChatPageState> }) {
	const {
		navigate,
		urlAgentId,
		urlSessionId,
		t,
		agents,
		refetchAgents,
		sessions,
		isMobile,
		setOpenMobile,
		setEditOpen,
		setDeleteOpen,
		setRenameOpen,
		setRenameSession,
		selectedAgent,
		showSourceIcons,
		handleCreateSession,
		requestDeleteSession,
		todaySessions,
		earlierSessions,
	} = state;
	return (
		<Sidebar collapsible={isMobile ? 'offcanvas' : 'none'} className="rounded-[22px]">
			{/* Scrolling moves down to the session list below, so the
				    agent picker and the new-session button stay put. */}
			<SidebarContent className="my-2 overflow-hidden">
				<SidebarGroup className="px-2 py-0">
					<SidebarGroupLabel className="justify-between">
						{t('common.agent')}
						<AgentDialog onCreated={refetchAgents}>
							<Button variant="ghost" size="icon-xs" title={t('dialog-agent-create.title')}>
								<Plus id="tour-create-agent" className="size-3.5" />
							</Button>
						</AgentDialog>
					</SidebarGroupLabel>
					<SidebarGroupContent className="flex items-center">
						<AgentSelect
							className="flex-1 min-w-0"
							agents={agents}
							value={urlAgentId ?? null}
							onChange={(id) => navigate(`/chat/${id}`)}
							variant="ghost"
							size="default"
						/>
						<DropdownMenu>
							<DropdownMenuTrigger asChild>
								<Button
									className="shrink-0 text-muted-foreground"
									variant="ghost"
									size="icon"
									disabled={!urlAgentId || !selectedAgent?.editable}
								>
									<Ellipsis />
								</Button>
							</DropdownMenuTrigger>
							{/* w-auto: the default pins the menu to the
								    trigger's width, which is a 32px icon button. */}
							<DropdownMenuContent className="w-auto">
								<DropdownMenuItem onClick={() => setEditOpen(true)}>
									<Settings2 />
									{t('agent-menu.settings')}
								</DropdownMenuItem>
								<DropdownMenuItem onClick={() => setDeleteOpen(true)} variant="destructive">
									<Trash2 />
									{t('agent-menu.delete')}
								</DropdownMenuItem>
							</DropdownMenuContent>
						</DropdownMenu>
					</SidebarGroupContent>
				</SidebarGroup>
				<SidebarGroup className="mt-5 min-h-0 flex-1 px-2 py-0">
					<SidebarGroupLabel className="justify-between">
						{t('chat.session.label')}
						<span className="text-[10px] text-text-data font-mono">{sessions.length}</span>
					</SidebarGroupLabel>
					<SidebarGroupContent className="flex min-h-0 flex-1 flex-col">
						<SidebarGroup>
							<SidebarMenu className="mb-2">
								<Button id="tour-create-session" onClick={handleCreateSession}>
									<Plus />
									{t('chat.newSession')}
								</Button>
							</SidebarMenu>
						</SidebarGroup>

						<div className="no-scrollbar min-h-0 flex-1 overflow-y-auto">
							{sessions.length === 0 ? (
								<Empty className="border-none py-4 min-h-50">
									<EmptyHeader>
										<EmptyMedia variant="icon">
											<MessageSquareDashed />
										</EmptyMedia>
										<EmptyTitle>{t('chat.session.emptyTitle')}</EmptyTitle>
										<EmptyDescription>
											{urlAgentId
												? t('chat.session.emptyHasAgent')
												: t('chat.session.emptyNoAgent')}
										</EmptyDescription>
									</EmptyHeader>
								</Empty>
							) : (
								<>
									<SidebarGroup>
										<SidebarGroupLabel>{t('chat.session.today')}</SidebarGroupLabel>
										<SidebarGroupContent>
											<SidebarMenu>
												{todaySessions.map((view) => {
													const session = view.session;
													const SourceIcon = SOURCE_ICON[session.origin.type] ?? BotMessageSquare;
													return (
														<SidebarMenuItem key={session.id}>
															{/* Wider right gutter than the stock
															    pr-8: the badge holds a mono timestamp. */}
															<SidebarMenuButton
																className="text-muted-foreground hover:text-foreground group-has-data-[sidebar=menu-action]/menu-item:pr-16"
																isActive={urlSessionId === session.id}
																onClick={() => {
																	navigate(`/chat/${urlAgentId}/${session.id}`);
																	setOpenMobile(false);
																}}
															>
																{showSourceIcons && <SourceIcon />}
																<span className="truncate">
																	{session.config.name || session.id}
																</span>
															</SidebarMenuButton>
															{/* Badge and action are mutually exclusive.
															    Keyboard focus reveals the action, plain
															    focus-within does not — otherwise clicking
															    the row would pin it open. */}
															<SidebarMenuBadge className="max-md:hidden group-hover/menu-item:hidden group-has-focus-visible/menu-item:hidden group-has-data-[state=open]/menu-item:hidden text-text-tertiary! font-mono">
																{format(new Date(view.session.created_at), 'HH:mm')}
															</SidebarMenuBadge>
															<DropdownMenu>
																<DropdownMenuTrigger asChild>
																	<SidebarMenuAction className="md:opacity-0 group-hover/menu-item:opacity-100 group-has-focus-visible/menu-item:opacity-100 aria-expanded:opacity-100 peer-data-active/menu-button:text-sidebar-accent-foreground">
																		<Ellipsis />
																	</SidebarMenuAction>
																</DropdownMenuTrigger>
																<DropdownMenuContent className="w-auto" side="right" align="start">
																	<DropdownMenuItem
																		onClick={() => {
																			setRenameSession(session);
																			setRenameOpen(true);
																		}}
																	>
																		<Pencil />
																		{t('session-menu.rename')}
																	</DropdownMenuItem>
																	<DropdownMenuItem
																		variant="destructive"
																		onClick={() => requestDeleteSession(session)}
																	>
																		<Trash2 />
																		{t('session-menu.delete')}
																	</DropdownMenuItem>
																</DropdownMenuContent>
															</DropdownMenu>
														</SidebarMenuItem>
													);
												})}
											</SidebarMenu>
										</SidebarGroupContent>
									</SidebarGroup>
									<SidebarGroup>
										<SidebarGroupLabel>{t('chat.session.earlier')}</SidebarGroupLabel>
										<SidebarGroupContent>
											<SidebarMenu>
												{earlierSessions.map((view) => {
													const session = view.session;
													const SourceIcon = SOURCE_ICON[session.origin.type] ?? BotMessageSquare;
													return (
														<SidebarMenuItem key={session.id}>
															<SidebarMenuButton
																className="text-muted-foreground hover:text-foreground group-has-data-[sidebar=menu-action]/menu-item:pr-16"
																isActive={urlSessionId === session.id}
																onClick={() => {
																	navigate(`/chat/${urlAgentId}/${session.id}`);
																	setOpenMobile(false);
																}}
															>
																{showSourceIcons && <SourceIcon />}
																<span className="truncate">
																	{session.config.name || session.id}
																</span>
															</SidebarMenuButton>
															<SidebarMenuBadge className="max-md:hidden group-hover/menu-item:hidden group-has-focus-visible/menu-item:hidden group-has-data-[state=open]/menu-item:hidden text-text-tertiary! font-mono">
																{format(new Date(view.session.created_at), 'MMM dd')}
															</SidebarMenuBadge>
															<DropdownMenu>
																<DropdownMenuTrigger asChild>
																	<SidebarMenuAction className="md:opacity-0 group-hover/menu-item:opacity-100 group-has-focus-visible/menu-item:opacity-100 aria-expanded:opacity-100 peer-data-active/menu-button:text-sidebar-accent-foreground">
																		<Ellipsis />
																	</SidebarMenuAction>
																</DropdownMenuTrigger>
																<DropdownMenuContent className="w-auto" side="right" align="start">
																	<DropdownMenuItem
																		onClick={() => {
																			setRenameSession(session);
																			setRenameOpen(true);
																		}}
																	>
																		<Pencil />
																		{t('session-menu.rename')}
																	</DropdownMenuItem>
																	<DropdownMenuItem
																		variant="destructive"
																		onClick={() => requestDeleteSession(session)}
																	>
																		<Trash2 />
																		{t('session-menu.delete')}
																	</DropdownMenuItem>
																</DropdownMenuContent>
															</DropdownMenu>
														</SidebarMenuItem>
													);
												})}
											</SidebarMenu>
										</SidebarGroupContent>
									</SidebarGroup>
								</>
							)}
						</div>
					</SidebarGroupContent>
				</SidebarGroup>
			</SidebarContent>
		</Sidebar>
	);
}
