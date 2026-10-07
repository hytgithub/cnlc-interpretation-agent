// session API contracts.
import type { SessionKnowledgeConfig } from './knowledge';
import type { ChatModelConfig, TTSModelConfig } from './model';
import type { PermissionMode, RecordBase } from './shared';
import type { TeamDetailResponse } from './team';

/** How a session came to exist — fixed when it is created. */
export type SessionOrigin =
	| { type: 'user' }
	| { type: 'schedule'; schedule_id: string }
	| {
			type: 'channel';
			channel_id: string;
			chat_id: string;
			chat_name: string | null;
	  }
	| { type: 'team' };

/** The tag of a {@link SessionOrigin}. */
export type SessionSourceKind = SessionOrigin['type'];

export interface SessionConfig {
	name: string;
	/** Who owns `name` — see the backend's `SessionNaming`. */
	naming: { auto: boolean };
	chat_model_config: ChatModelConfig;
	/** Fallback model used when the primary model fails. */
	fallback_chat_model_config: ChatModelConfig | null;
	/** TTS model configuration. null means TTS is not enabled. */
	tts_model_config: TTSModelConfig | null;
	/** Knowledge bases attached to this session + KB middleware parameters. */
	knowledge_config: SessionKnowledgeConfig | null;
	workspace_id: string;
	/**
	 * Directory the session is focused on — absolute, or relative to the
	 * workspace root, and not confined to it. `null` means the root.
	 * Purely a viewing anchor; it does not move where tools execute.
	 */
	cwd: string | null;
}

// TODO: update when Python side is finalised
export type AgentState = Record<string, unknown>;

export interface SessionRecord extends RecordBase {
	user_id: string;
	agent_id: string;
	origin: SessionOrigin;
	/**
	 * The team this session participates in, if any. Set when the
	 * session is the leader of a team (the session that called
	 * `TeamCreate`) or a worker spawned by `AgentCreate`. `null` for
	 * regular standalone sessions.
	 */
	team_id: string | null;
	config: SessionConfig;
	state: AgentState;
}

export interface CreateSessionRequest {
	agent_id: string;
	workspace_id?: string;
	chat_model_config?: ChatModelConfig | null;
	/** Optional fallback model. Omit (or pass null) for no fallback. */
	fallback_chat_model_config?: ChatModelConfig | null;
	/** Optional TTS model. Omit (or pass null) for no TTS. */
	tts_model_config?: TTSModelConfig | null;
	/** Optional knowledge base attachment. Omit (or null) for none. */
	knowledge_config?: SessionKnowledgeConfig | null;
}

export interface CreateSessionResponse {
	session_id: string;
}

export interface InterruptSessionResponse {
	session_id: string;
}

export interface UpdateSessionRequest {
	name?: string;
	chat_model_config?: ChatModelConfig;
	/**
	 * New fallback model. PATCH semantics:
	 *   - omit the field → leave unchanged
	 *   - set to `null`  → clear the existing fallback
	 *   - set to a value → replace the existing fallback
	 */
	fallback_chat_model_config?: ChatModelConfig | null;
	/**
	 * New TTS model. PATCH semantics:
	 *   - omit the field → leave unchanged
	 *   - set to `null`  → disable TTS
	 *   - set to a value → replace the existing TTS config
	 */
	tts_model_config?: TTSModelConfig | null;
	/**
	 * New knowledge base attachment. PATCH semantics:
	 *   - omit the field → leave unchanged
	 *   - set to `null`  → detach every knowledge base
	 *   - set to a value → replace the existing attachment
	 */
	knowledge_config?: SessionKnowledgeConfig | null;
	permission_mode?: PermissionMode;
	/**
	 * New working directory — absolute or relative to the workspace
	 * root, and not confined to it. PATCH semantics:
	 *   - omit the field → leave unchanged
	 *   - set to `null`  → reset to the workspace root
	 *   - set to a value → focus that directory
	 */
	cwd?: string | null;
}

export interface SessionListResponse {
	sessions: SessionView[];
	total: number;
}

/**
 * Response body for `GET /schedule/{id}/sessions`. Returns plain
 * `SessionRecord[]` (no team / is_running enrichment) because
 * scheduled-execution sessions are listed for audit purposes only,
 * not for opening in the chat UI.
 */
export interface ScheduleSessionsResponse {
	sessions: SessionRecord[];
	total: number;
}

/**
 * A session's unified status. `running` means a worker somewhere holds
 * its run lease; the `awaiting_*` values mean nobody is running it but
 * its stored context is parked on a pending tool call.
 */
export type SessionStatus = 'running' | 'idle' | 'awaiting_permission' | 'awaiting_external_result';

/**
 * Per-session bundle returned by `GET /sessions/?agent_id=...`.
 *
 * Bundles what the chat UI needs to render a session without follow-up
 * requests: the persisted record, its status, and — when the session
 * participates in a team — the resolved team detail.
 */
export interface SessionView {
	/**
	 * The record with the bulk of `state` stripped: `context`, `summary`
	 * and `tool_context` arrive cleared, since they hold the model's
	 * conversation and every file it has read. `permission_context` and
	 * `tasks_context` survive — the panels seed from them. Messages come
	 * from `GET /sessions/{id}/messages`.
	 */
	session: SessionRecord;
	/**
	 * @deprecated Use {@link status}. True only while a worker holds the
	 * run lease, which a session parked on a confirmation prompt does
	 * not — so this reads `false` for a session visibly waiting on you.
	 */
	is_running: boolean;
	/** Exactly one applies at a time, so one indicator renders it. */
	status: SessionStatus;
	team: TeamDetailResponse | null;
}
