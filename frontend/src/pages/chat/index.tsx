import { ChatViewport } from './ChatViewport';
import { ChatSessionDialogs } from './session-dialogs';
import { ChatSessionSidebar } from './session-sidebar';
import { useChatPageState } from './useChatPageState';
import { ChatTourController } from '@/components/tour/ChatTourController';
import { SidebarProvider } from '@/components/ui/sidebar';
import { AudioProvider } from '@/context/AudioContext';

const ChatPageInner = () => {
	const state = useChatPageState();
	const {
		agents,
		sessions,
		refetchSessions,
		setOpen,
		setOpenMobile,
		effectiveAgentId,
		effectiveSessionId,
	} = state;
	return (
		<div className="flex h-full w-full p-2 gap-2">
			{/*
			 * Desktop stays `collapsible="none"` so the session list sits in
			 * normal flow beside the app rail (AppSidebar). Mobile switches to
			 * `offcanvas`, which makes shadcn's Sidebar render its Sheet overlay
			 * (the drawer we want) — instead of the desktop `fixed left-0`
			 * container, which would otherwise cover the app rail.
			 */}
			<ChatSessionSidebar state={state} />
			<div className="flex flex-1 min-w-0">
				<ChatViewport
					agentId={effectiveAgentId}
					sessionId={effectiveSessionId}
					onSessionsChanged={refetchSessions}
				/>
			</div>
			<ChatSessionDialogs state={state} />
			<ChatTourController
				agentsCount={agents.length}
				sessionsCount={sessions.length}
				onEnsureSidebarOpen={() => {
					setOpen(true);
					setOpenMobile(true);
				}}
			/>
		</div>
	);
};

export const ChatPage = () => (
	<AudioProvider>
		<SidebarProvider defaultOpen>
			<ChatPageInner />
		</SidebarProvider>
	</AudioProvider>
);
