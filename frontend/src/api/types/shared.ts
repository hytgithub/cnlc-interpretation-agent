// shared API contracts.

export interface RecordBase {
	id: string;
	created_at: string;
	updated_at: string;
}

export interface ContextConfig {
	trigger_ratio?: number;
	reserve_ratio?: number;
	tool_result_limit?: number;
	compression_prompt?: string;
	summary_template?: string;
}

export interface ReActConfig {
	max_iters?: number;
	stop_on_reject?: boolean;
}

export interface InviteConfig {
	invitable?: boolean;
	invite_description?: string | null;
}

export type PermissionMode =
	'default' | 'accept_edits' | 'explore' | 'bypass' | 'dont_ask' | (string & {});
