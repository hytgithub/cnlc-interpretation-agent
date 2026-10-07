// mcp API contracts.

export interface StdioMCPConfig {
	type: 'stdio_mcp';
	command: string;
	args?: string[] | null;
	env?: Record<string, string> | null;
	cwd?: string | null;
	encoding_error_handler?: 'strict' | 'ignore' | 'replace';
}

export interface HttpMCPConfig {
	type: 'http_mcp';
	url: string;
	headers?: Record<string, string> | null;
	timeout?: number | null;
}

export interface MCPClient {
	name: string;
	is_stateful: boolean;
	mcp_config: StdioMCPConfig | HttpMCPConfig;
}

export interface ToolInfo {
	name: string;
	description?: string | null;
}

export interface MCPClientStatus extends MCPClient {
	is_healthy: boolean;
	tools: ToolInfo[];
	/**
	 * Why listing this MCP's tools failed. `null` when healthy — a red dot
	 * alone leaves nothing to act on, since a wrong API key, an unreachable
	 * host and a missing command all look the same.
	 */
	error: string | null;
}

/** A library edit. Omitted fields are left alone. */
export interface UpdateMCPRequest {
	name?: string;
	/**
	 * New answers, merged over the stored ones — send only what changed, so
	 * a write-only field the form never echoed back survives.
	 */
	values?: Record<string, unknown>;
	enabled?: boolean;
}

export interface InstallMCPRequest {
	/**
	 * Name to install under, defaulting to the card's. Must match
	 * `[a-zA-Z0-9_-]+`; use it to resolve a 409 name clash.
	 */
	name?: string | null;
	/** Answers to `inputs_schema`, e.g. API keys. */
	values: Record<string, unknown>;
}

/**
 * One MCP in the user's own library, which is where an install lands —
 * distinct from `WorkspaceMCP`, which is what one session's workspace holds.
 *
 * The rendered config is not exposed: it carries the values submitted at
 * install time, API keys included.
 */
export interface MCPView {
	id: string;
	/** Unique per user — the handle a workspace refers to it by. */
	name: string;
	is_stateful: boolean;
	enabled: boolean;
	/**
	 * Snapshotted from the card at install time, so they survive the hub
	 * going away — and may lag behind it.
	 */
	display_name: string | null;
	description: string;
	tags: string[];
	author: string | null;
	icon_url: string | null;
	url: string | null;
	/** `null` when the MCP was added by hand rather than from a hub. */
	hub_id: string | null;
	card_id: string | null;
	version: string | null;
}
