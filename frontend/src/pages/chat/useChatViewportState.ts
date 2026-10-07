import type { PermissionContext } from '@agentscope-ai/agentscope/permission';
import type { TaskContext } from '@agentscope-ai/agentscope/state';
import { useCallback, useEffect, useRef, useState } from 'react';

import type { ChatViewportProps } from './chat-viewport-types';
import { openPanelInLayout } from './panel-layout';
import { useChatPanels } from './useChatPanels';
import { useChatSessionConfig } from './useChatSessionConfig';
import { usePanelLayout } from './usePanelLayout';
import { useAvailableModels } from '@/hooks/useAvailableModels';
import { useKnowledgeBaseMiddlewareSchema } from '@/hooks/useKnowledgeBaseMiddlewareSchema';
import { useKnowledgeBases } from '@/hooks/useKnowledgeBases';
import { useMessages } from '@/hooks/useMessages';
import { useSessions } from '@/hooks/useSessions';
import { useWorkspace } from '@/hooks/useWorkspace.ts';
import { useWorkspaceStatus } from '@/hooks/useWorkspaceStatus';
import { useTranslation } from '@/i18n/useI18n';

export function useChatViewportState({ agentId, sessionId, onSessionsChanged }: ChatViewportProps) {
	const { t } = useTranslation();

	const { sessions, refetch: refetchSessions } = useSessions(agentId);

	const { groups } = useAvailableModels();

	// Declared above `panels` — the memo factory reads `view.team`
	// eagerly on first render, so a later `const` would still be in
	// the temporal dead zone.
	const view = sessions.find((v) => v.session.id === sessionId) ?? null;

	const {
		selectedModel,
		selectedFallbackModel,
		selectedTTSModel,
		selectedKnowledgeConfig,
		selectedPermissionMode,
		configPending,
		handleKnowledgeConfigChange,
		selectedModelCard,
		handleLlmChange,
		handleParametersChange,
		handleFallbackChange,
		handleTTSChange,
		handleCwdChange,
		handlePermissionModeChange,
	} = useChatSessionConfig({ agentId, sessionId, view, groups, refetchSessions });

	const [credentialOpen, setCredentialOpen] = useState(false);

	const [credentialRefetchTrigger, setCredentialRefetchTrigger] = useState(0);

	const [tasksContext, setTasksContext] = useState<TaskContext | null>(null);

	const [permissionContext, setPermissionContext] = useState<PermissionContext | null>(null);

	const { panelLayout, setPanelLayout, togglePanel, closePanel, isPanelOpen } = usePanelLayout();

	// When the viewport agent differs from the outer page's selected
	// agent (i.e. user drilled into a team member), `refetchSessions`
	// only refreshes the member's session list, so we also fire the
	// parent's refetch to keep its copy in sync.
	//
	// Surfacing the team panel here is what makes a team visible at all
	// — `TeamCreate` / `AgentCreate` / `AgentInvite` are agent tools, so
	// the user never opened a dialog that could have opened the panel.
	// `team_updated` also fires on `TeamDelete` and carries no payload,
	// hence checking the refetched list rather than opening blindly.
	const handleTeamUpdated = useCallback(async () => {
		const next = await refetchSessions();
		if (next.some((v) => v.session.id === sessionId && v.team)) {
			// `openPanelInLayout`, not `togglePanel` — the latter would
			// close a panel the user already has open.
			setPanelLayout((layout) => openPanelInLayout(layout, 'team'));
		}
		onSessionsChanged?.();
	}, [refetchSessions, sessionId, onSessionsChanged, setPanelLayout]);

	// Auto-naming replaced the session's placeholder name. The outer
	// page shares this cached list whenever both are looking at the same
	// agent; when they are not — drilled into a team member — it needs
	// its own nudge.
	const handleSessionUpdated = useCallback(async () => {
		await refetchSessions();
		onSessionsChanged?.();
	}, [refetchSessions, onSessionsChanged]);

	// Surface the plan panel the first time a session's tasks arrive over
	// the stream, and only then — reopening it on every update would undo
	// the user closing it. `state_updated` also fires for permission-only
	// changes and always carries `tasks_context`, hence gating on a
	// non-empty task list rather than the field being present.
	const taskPanelOpenedForRef = useRef<string | null>(null);

	const handleStateUpdated = useCallback(
		(value: Record<string, unknown>) => {
			if (value.tasks_context) {
				const incoming = value.tasks_context as TaskContext;
				setTasksContext(incoming);
				if (incoming.tasks.length > 0 && taskPanelOpenedForRef.current !== sessionId) {
					taskPanelOpenedForRef.current = sessionId;
					setPanelLayout((layout) => openPanelInLayout(layout, 'plan'));
				}
			}
			if (value.permission_context) {
				setPermissionContext(value.permission_context as PermissionContext);
			}
		},
		[sessionId, setPanelLayout],
	);

	const {
		msgs,
		loading: messagesLoading,
		phase,
		send,
		onUserConfirm,
		onSubagentConfirm,
		subagentHitl,
		interrupt,
	} = useMessages(agentId, sessionId, {
		onTeamUpdated: handleTeamUpdated,
		onStateUpdated: handleStateUpdated,
		onSessionUpdated: handleSessionUpdated,
	});

	const workspace = useWorkspace(agentId, sessionId);

	const knowledge = useKnowledgeBases();

	const { schema: kbMiddlewareSchema } = useKnowledgeBaseMiddlewareSchema();

	const { status: workspaceStatus, refetch: refetchWorkspaceStatus } = useWorkspaceStatus(
		agentId,
		sessionId,
		view?.session.config.cwd ?? null,
	);

	// A finished reply is the one moment the agent may have changed the
	// working tree, and it is why nothing polls for git status. Watching
	// `phase` rather than the REPLY_END event also covers the interrupt
	// timeout, which reaches idle without one.
	const prevPhaseRef = useRef(phase);

	useEffect(() => {
		const wasRunning = prevPhaseRef.current !== 'idle';
		prevPhaseRef.current = phase;
		if (wasRunning && phase === 'idle') void refetchWorkspaceStatus();
	}, [phase, refetchWorkspaceStatus]);

	const panels = useChatPanels({
		t,
		tasksContext,
		permissionContext,
		workspace,
		knowledge,
		selectedKnowledgeConfig,
		kbMiddlewareSchema,
		handleKnowledgeConfigChange,
		sessionId,
		view,
	});

	// Safety net for a `view` that never arrives. A session created from
	// the outer page reaches this list on its own, since both mount the
	// same cached query — but not when the two are looking at different
	// agents (drilled into a team member), and not for a write that
	// happened outside either. Without a `view` every effect below
	// early-returns on `!view`, leaving the model select and friends
	// pinned to whatever the previously-viewed session had configured.
	useEffect(() => {
		if (!sessionId) return;
		if (view) return;
		refetchSessions();
	}, [sessionId, view, refetchSessions]);

	// Seed tasks + permission from the session snapshot ONCE per
	// session, then leave them to the CustomEvent(name="state_updated")
	// stream via `handleStateUpdated`.
	//
	// Seeding on every `view` change would be wrong: storage is only
	// written when a run ends, so mid-run the snapshot still holds the
	// run-start values. `view` gets a new identity on every
	// `refetchSessions()` — which `team_updated` triggers — and
	// re-seeding then would silently roll both panels back to where the
	// reply started. Clearing on `!view` still matters so switching
	// sessions cannot leak the previous session's tasks or rules.
	const seededSessionRef = useRef<string | null>(null);

	useEffect(() => {
		if (!view) {
			seededSessionRef.current = null;
			setTasksContext(null);
			setPermissionContext(null);
			return;
		}
		if (seededSessionRef.current === view.session.id) return;
		seededSessionRef.current = view.session.id;
		const state = view.session.state as Record<string, unknown> | undefined;
		setTasksContext((state?.tasks_context as TaskContext) ?? null);
		setPermissionContext((state?.permission_context as PermissionContext) ?? null);
	}, [view]);

	return {
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
	};
}
