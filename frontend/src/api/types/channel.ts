// channel API contracts.
import type { ChatModelConfig } from './model';
import type { SessionRecord } from './session';
import type { PermissionMode } from './shared';

// How inbound messages are grouped into agent sessions.
export type SessionScope = 'per_chat' | 'per_chat_user';

// One routing rule: match an inbound event, then pick the agent and how
// its session is grouped. Rules are ordered; the first match wins and the
// last must be a catch-all (match_value === '*').
export interface ChannelBinding {
	match_key: string;
	match_value: string;
	agent_id: string;
	session_scope: SessionScope;
}

export interface RoutingConfig {
	bindings: ChannelBinding[];
}

export interface SessionSettings {
	chat_model_config: ChatModelConfig;
	fallback_chat_model_config?: ChatModelConfig | null;
	permission_mode: PermissionMode;
}

export interface ChannelRecord {
	id: string;
	channel_type: string;
	name: string | null;
	user_id: string;
	platform_bot_id: string;
	enabled: boolean;
	platform_config: Record<string, unknown>;
	routing: RoutingConfig;
	session: SessionSettings;
	created_at: string;
	updated_at: string;
}

export interface CreateChannelRequest {
	channel_type: string;
	name?: string | null;
	credentials?: Record<string, unknown>;
	/** Completed binding to take the credentials from, instead of sending them. */
	credential_binding_id?: string | null;
	platform_config?: Record<string, unknown>;
	routing: RoutingConfig;
	session: SessionSettings;
	enabled?: boolean;
}

export interface UpdateChannelRequest {
	name?: string | null;
	platform_config?: Record<string, unknown>;
	routing?: RoutingConfig;
	session?: SessionSettings;
	enabled?: boolean;
}

export interface ChannelTypeSchema {
	channel_type: string;
	display_name: string;
	description?: string;
	icon_url?: string;
	credentials_schema: Record<string, unknown>;
	config_schema: Record<string, unknown>;
	platform_bot_id_field?: string;
	/** Whether the platform can hand its credentials over interactively. */
	supports_credential_binding?: boolean;
}

export type BindingState = 'pending' | 'authorized' | 'failed' | 'cancelled';

export interface BindingView {
	binding_id: string;
	state: BindingState;
	/** Where the operator must approve; rendered as a QR code. */
	verification_url: string;
	error: string;
	retry_after_secs: number;
}

export type ChannelState = 'stopped' | 'connecting' | 'retrying' | 'connected' | 'failed';

export interface ChannelStatus {
	state: ChannelState;
	last_error: string;
}

export interface ChannelSessionsResponse {
	sessions: SessionRecord[];
	total: number;
}

export interface ChannelChatIdsResponse {
	chats: { chat_id: string; name: string; source: string }[];
}
