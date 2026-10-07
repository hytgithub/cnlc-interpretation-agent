import { useCallback, useEffect, useMemo, useState } from 'react';

import type {
	ChatModelConfig,
	PermissionMode,
	SessionKnowledgeConfig,
	SessionView,
	TTSModelConfig,
	UpdateSessionRequest,
} from '@/api';
import { sessionApi } from '@/api';
import { useAvailableModels } from '@/hooks/useAvailableModels';
import { useSessions } from '@/hooks/useSessions';
interface SessionConfigOptions {
	agentId: string | null;
	sessionId: string | null;
	view: SessionView | null;
	groups: ReturnType<typeof useAvailableModels>['groups'];
	refetchSessions: ReturnType<typeof useSessions>['refetch'];
}
export function useChatSessionConfig({
	agentId,
	sessionId,
	view,
	groups,
	refetchSessions,
}: SessionConfigOptions) {
	const [selectedModel, setSelectedModel] = useState<ChatModelConfig | null>(null);

	const [selectedFallbackModel, setSelectedFallbackModel] = useState<ChatModelConfig | null>(null);

	const [selectedTTSModel, setSelectedTTSModel] = useState<TTSModelConfig | null>(null);

	const [selectedKnowledgeConfig, setSelectedKnowledgeConfig] =
		useState<SessionKnowledgeConfig | null>(null);

	const [selectedPermissionMode, setSelectedPermissionMode] = useState<string>('default');

	const [configPending, setConfigPending] = useState(false);

	/**
	 * Persist a knowledge-base attachment change. `null` detaches every
	 * knowledge base from this session, removing the `RAGMiddleware`.
	 *
	 * Declared above `panels` (rather than alongside the other model
	 * handlers below) because `panels` is built inside `useMemo` and
	 * references this handler eagerly — a later `const` would still be
	 * in the temporal dead zone when the memo factory runs on first
	 * render.
	 *
	 * @param config - New attachment, or `null` to detach all.
	 */
	/**
	 * Persist a session config change, applying it locally only once
	 * the server accepts it.
	 *
	 * The backend rejects config writes with 409 while a chat run holds
	 * the session, so an optimistic update would leave the control
	 * showing a value the session does not have. Waiting for the
	 * response keeps the control on its previous value with no rollback
	 * bookkeeping; `client.ts` has already surfaced the error toast by
	 * the time we land in `catch`.
	 *
	 * Declared above `panels` for the same temporal-dead-zone reason as
	 * `handleKnowledgeConfigChange` below.
	 *
	 * @param body - The PATCH body.
	 * @param apply - Mirrors the change into local state on success.
	 */
	const patchConfig = useCallback(
		async (body: UpdateSessionRequest, apply: () => void) => {
			if (!sessionId || !agentId) return;
			setConfigPending(true);
			try {
				await sessionApi.update(sessionId, agentId, body);
				apply();
				await refetchSessions();
			} catch {
				// Toast already shown; local state deliberately untouched.
			} finally {
				setConfigPending(false);
			}
		},
		[sessionId, agentId, refetchSessions],
	);

	const handleKnowledgeConfigChange = useCallback(
		async (config: SessionKnowledgeConfig | null) => {
			await patchConfig({ knowledge_config: config }, () => setSelectedKnowledgeConfig(config));
		},
		[patchConfig],
	);

	// Reset local UI state when the target session changes. Otherwise
	// the model select (and disabled-state guards on `send`) would
	// show the previous session's model during the in-flight window
	// before `view` repopulates — and an immediate send would post to
	// a session whose backend config doesn't actually have that model.
	useEffect(() => {
		setSelectedModel(null);
		setSelectedFallbackModel(null);
		setSelectedTTSModel(null);
		setSelectedKnowledgeConfig(null);
	}, [sessionId]);

	const selectedModelCard = useMemo(() => {
		if (!selectedModel) return null;
		const items = groups[selectedModel.type];
		if (!items) return null;
		for (const { models } of items) {
			const card = models.find((m) => m.name === selectedModel.model);
			if (card) return card;
		}
		return null;
	}, [groups, selectedModel?.type, selectedModel?.model]);

	/**
	 * Pick the first model the available-models endpoint surfaces, used
	 * as a sensible default when the current session has no model
	 * configured yet.
	 *
	 * @returns The first available `ChatModelConfig`, or `null` when
	 *   no credentials / models are configured.
	 */
	const getFirstAvailableModel = (): ChatModelConfig | null => {
		const firstType = Object.keys(groups)[0];
		if (!firstType) return null;
		const items = groups[firstType];
		if (!items || items.length === 0) return null;
		const firstItem = items[0];
		const firstModel = (firstItem.models as { name?: string; id?: string }[])[0];
		if (!firstModel) return null;
		const modelName = firstModel.name ?? firstModel.id ?? null;
		if (!modelName) return null;
		return {
			type: firstType,
			credential_id: firstItem.credential.id,
			model: modelName,
			parameters: {},
		};
	};

	// Sync selectedModel + selectedFallbackModel from the session
	// record. If the session has no model configured yet, auto-pick
	// the first available one and persist it back so subsequent
	// reasoning has a model to call.
	//
	// Important: skip while `view` is still loading. Otherwise the
	// in-flight window between "agentId changed" and "useSessions
	// returned the new list" looks like "session has no model" and
	// we would racily auto-select + persist the first available
	// model, clobbering whatever the user had configured.
	useEffect(() => {
		if (!view) return;
		const sessionModel = view.session.config.chat_model_config;

		if (sessionModel) {
			setSelectedModel(sessionModel);
		} else {
			const firstModel = getFirstAvailableModel();
			if (firstModel) {
				setSelectedModel(firstModel);
				if (sessionId && agentId) {
					// `silent` because the user did not ask for this write —
					// surfacing a toast for a revoked credential or a network
					// blip they never triggered is pure noise.
					sessionApi
						.update(sessionId, agentId, { chat_model_config: firstModel }, { silent: true })
						.then(() => refetchSessions())
						.catch(() => {});
				}
			} else {
				setSelectedModel(null);
			}
		}

		setSelectedFallbackModel(view.session.config.fallback_chat_model_config ?? null);
		setSelectedTTSModel(view.session.config.tts_model_config ?? null);
		setSelectedKnowledgeConfig(view.session.config.knowledge_config ?? null);
	}, [view, groups, sessionId, agentId]);

	// Sync selectedPermissionMode when the session changes. Same
	// loading-window guard as above — don't reset the displayed mode
	// to "default" while the new session view is still on the wire.
	useEffect(() => {
		if (!view) return;
		const mode = (view.session.state?.permission_context as Record<string, unknown>)
			?.mode as string;
		setSelectedPermissionMode(mode ?? 'default');
	}, [sessionId, view]);

	/**
	 * Persist a model change to the session and refetch so the local
	 * view picks up the new value.
	 *
	 * @param config - New chat model config; `null` is ignored
	 *   because the primary selector does not allow clearing.
	 */
	const handleLlmChange = async (config: ChatModelConfig | null) => {
		if (!config) return;
		await patchConfig({ chat_model_config: config }, () => setSelectedModel(config));
	};

	/**
	 * Persist a parameter change on the currently selected model.
	 *
	 * @param parameters - New parameter map (model-provider specific).
	 */
	const handleParametersChange = async (parameters: Record<string, unknown>) => {
		if (!selectedModel) return;
		const updated = { ...selectedModel, parameters };
		await patchConfig({ chat_model_config: updated }, () => setSelectedModel(updated));
	};

	/**
	 * Persist a fallback-model change. `null` clears the fallback.
	 *
	 * @param config - New fallback config or `null` to clear.
	 */
	const handleFallbackChange = async (config: ChatModelConfig | null) => {
		await patchConfig({ fallback_chat_model_config: config }, () =>
			setSelectedFallbackModel(config),
		);
	};

	/**
	 * Persist a TTS model change. `null` disables TTS.
	 *
	 * @param config - New TTS config or `null` to disable.
	 */
	const handleTTSChange = async (config: TTSModelConfig | null) => {
		await patchConfig({ tts_model_config: config }, () => setSelectedTTSModel(config));
	};

	/**
	 * Persist a permission-mode change.
	 *
	 * @param mode - New permission mode (e.g. `default`, `explore`).
	 */
	/**
	 * Persist a new working directory.
	 *
	 * Nothing local mirrors it — the value is read straight off the
	 * session view, which `patchConfig` refetches on success.
	 *
	 * @param next - Directory relative to the workspace root, or `null`
	 *   for the root itself.
	 */
	const handleCwdChange = async (next: string | null) => {
		// Bypasses `patchConfig`: the dialog shows the failure inline and
		// stays open on it, so the toast would be a duplicate and the
		// swallowed rejection would let the dialog close as if it worked.
		if (!sessionId || !agentId) return;
		setConfigPending(true);
		try {
			await sessionApi.update(sessionId, agentId, { cwd: next }, { silent: true });
			await refetchSessions();
		} finally {
			setConfigPending(false);
		}
	};

	const handlePermissionModeChange = async (mode: string) => {
		await patchConfig({ permission_mode: mode as PermissionMode }, () =>
			setSelectedPermissionMode(mode),
		);
	};
	return {
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
	};
}
