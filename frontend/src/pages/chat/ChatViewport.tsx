import {
	BookText,
	ChevronDown,
	Database,
	ListTodo,
	PanelRight,
	ShieldCheck,
	UsersRound,
} from 'lucide-react';

import type { ChatViewportProps } from './chat-viewport-types';
import { getAllowedInputTypes, processChatFile } from './input-media';
import { useChatViewportState } from './useChatViewportState';
import MCPSvg from '@/assets/images/mcp.svg?react';
import { ChatContent } from '@/components/chat/ChatContent.tsx';
import { SubagentHitlCard } from '@/components/chat/SubagentHitlCard';
import { CreateCredentialDialog } from '@/components/dialog/CreateCredentialDialog';
import { PanelDock } from '@/components/panel/PanelDock.tsx';
import { ModelParametersPopover } from '@/components/popover/ModelParametersPopover';
import { LlmSelect } from '@/components/select/LlmSelect';
import { PermissionModeSelect } from '@/components/select/PermissionModeSelect.tsx';
import { Button } from '@/components/ui/button';
import {
	DropdownMenu,
	DropdownMenuCheckboxItem,
	DropdownMenuContent,
	DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
	ResizableHandle,
	ResizablePanel,
	ResizablePanelGroup,
} from '@/components/ui/resizable.tsx';
import { SidebarTrigger } from '@/components/ui/sidebar';

export function ChatViewport(props: ChatViewportProps) {
	const { agentId, sessionId } = props;
	const {
		t,
		selectedModel,
		selectedFallbackModel,
		selectedTTSModel,
		selectedPermissionMode,
		credentialOpen,
		setCredentialOpen,
		credentialRefetchTrigger,
		setCredentialRefetchTrigger,
		configPending,
		panelLayout,
		msgs,
		messagesLoading,
		phase,
		send,
		onUserConfirm,
		onSubagentConfirm,
		subagentHitl,
		interrupt,
		togglePanel,
		closePanel,
		isPanelOpen,
		view,
		workspaceStatus,
		refetchWorkspaceStatus,
		panels,
		selectedModelCard,
		handleLlmChange,
		handleParametersChange,
		handleFallbackChange,
		handleTTSChange,
		handleCwdChange,
		handlePermissionModeChange,
	} = useChatViewportState(props);
	return (
		<>
			<main className="flex size-full">
				<ResizablePanelGroup orientation="horizontal">
					<ResizablePanel
						className="flex flex-1 rounded-[22px] bg-card shadow-panel"
						minSize="24rem"
					>
						<div className="flex flex-col flex-1 min-h-0 min-w-0 overflow-x-hidden p-2">
							<div className="flex flex-row gap-x-2 justify-between">
								<div className="flex min-w-0 flex-row items-center gap-x-1">
									<SidebarTrigger className="md:hidden" />
									{/* The open session, named opposite its own
									    settings. The sidebar is the only other
									    place the name appears, and it collapses
									    on mobile — so on a narrow screen this is
									    the only thing saying which conversation
									    is on screen.

									    Withheld until the session has something
									    in it: an untouched one is still named
									    after the timestamp it was created at,
									    and a date is worse than no title at all.
									    The first reply replaces that with a real
									    one. */}
									{msgs.length > 0 && (
										<span
											className="truncate px-2 text-sm text-muted-foreground"
											title={view?.session.config.name}
										>
											{view?.session.config.name}
										</span>
									)}
								</div>
								{/* Never squeezed by a long session name: the
								    name truncates instead. */}
								<div className="flex shrink-0 flex-row gap-x-1">
									<LlmSelect
										id="tour-llm-select"
										variant="ghost"
										className="font-mono text-muted-foreground hover:text-foreground"
										value={selectedModel}
										onChange={handleLlmChange}
										onAddCredential={() => setCredentialOpen(true)}
										refetchTrigger={credentialRefetchTrigger}
										disabled={configPending}
									/>
									<ModelParametersPopover
										selectedModel={selectedModel}
										modelCard={selectedModelCard}
										onChange={handleParametersChange}
										selectedFallbackModel={selectedFallbackModel}
										onFallbackChange={handleFallbackChange}
										selectedTTSModel={selectedTTSModel}
										onTTSChange={handleTTSChange}
										disabled={configPending}
									/>
									<PermissionModeSelect
										id="tour-permission-mode"
										variant={'ghost'}
										className="font-mono text-muted-foreground hover:text-foreground"
										value={selectedPermissionMode}
										disabled={!sessionId || configPending}
										onChange={handlePermissionModeChange}
									/>
									<DropdownMenu>
										<DropdownMenuTrigger asChild>
											<Button variant="ghost" size="sm" className="gap-1 px-2">
												<PanelRight />
												<ChevronDown className="size-3 text-muted-foreground" />
											</Button>
										</DropdownMenuTrigger>
										<DropdownMenuContent align="end" className="w-auto">
											<DropdownMenuCheckboxItem
												checked={isPanelOpen('plan')}
												onCheckedChange={() => togglePanel('plan')}
												onSelect={(e) => e.preventDefault()}
											>
												<ListTodo />
												{t('panel.plan.title')}
											</DropdownMenuCheckboxItem>
											<DropdownMenuCheckboxItem
												checked={isPanelOpen('mcp')}
												onCheckedChange={() => togglePanel('mcp')}
												onSelect={(e) => e.preventDefault()}
											>
												<MCPSvg className="size-4" />
												MCP
											</DropdownMenuCheckboxItem>
											<DropdownMenuCheckboxItem
												checked={isPanelOpen('skill')}
												onCheckedChange={() => togglePanel('skill')}
												onSelect={(e) => e.preventDefault()}
											>
												<BookText />
												{t('panel.skill.title')}
											</DropdownMenuCheckboxItem>
											<DropdownMenuCheckboxItem
												checked={isPanelOpen('permission')}
												onCheckedChange={() => togglePanel('permission')}
												onSelect={(e) => e.preventDefault()}
											>
												<ShieldCheck />
												{t('panel.permission.title')}
											</DropdownMenuCheckboxItem>
											<DropdownMenuCheckboxItem
												checked={isPanelOpen('knowledge')}
												onCheckedChange={() => togglePanel('knowledge')}
												onSelect={(e) => e.preventDefault()}
											>
												<Database />
												{t('panel.knowledge.title')}
											</DropdownMenuCheckboxItem>
											<DropdownMenuCheckboxItem
												checked={isPanelOpen('team')}
												onCheckedChange={() => togglePanel('team')}
												onSelect={(e) => e.preventDefault()}
											>
												<UsersRound />
												{t('common.team')}
											</DropdownMenuCheckboxItem>
										</DropdownMenuContent>
									</DropdownMenu>
								</div>
							</div>
							<div className="flex flex-1 justify-center min-h-0 overflow-hidden relative [--chat-content-w:48rem]">
								<ChatContent
									className={'max-w-[var(--chat-content-w)] w-full'}
									msgs={msgs}
									loading={messagesLoading}
									agentId={agentId}
									sessionId={sessionId}
									cwd={view?.session.config.cwd ?? null}
									onCwdChange={handleCwdChange}
									git={workspaceStatus?.git ?? null}
									onRefreshGit={refetchWorkspaceStatus}
									phase={phase}
									disabled={selectedModel === null}
									onSend={send}
									onUserConfirm={onUserConfirm}
									onInterrupt={interrupt}
									// cwd={
									// 	{cwd: view?.session.config.cwd, git: {
									// 		branch: 'main',
									// 		deletion: 0,
									// 		addition: 0,
									// 	}}
									// }
									footerSlot={
										subagentHitl.length > 0 ? (
											<SubagentHitlCard
												key={`${subagentHitl[0].worker_session_id}:${subagentHitl[0].reply_id}`}
												entry={subagentHitl[0]}
												onConfirm={(toolCall, confirm, rules) =>
													onSubagentConfirm(subagentHitl[0], toolCall, confirm, rules)
												}
											/>
										) : null
									}
									allowedInputTypes={getAllowedInputTypes(selectedModelCard?.input_types ?? [])}
									fileProcessor={processChatFile}
								/>
							</div>
						</div>
					</ResizablePanel>
					{panelLayout.length > 0 && (
						<ResizableHandle withHandle className="bg-transparent w-1.5" />
					)}
					<PanelDock layout={panelLayout} panels={panels} onClosePanel={closePanel} />
				</ResizablePanelGroup>
			</main>
			<CreateCredentialDialog
				open={credentialOpen}
				onOpenChange={setCredentialOpen}
				onCreated={() => setCredentialRefetchTrigger((n) => n + 1)}
			/>
		</>
	);
}
