// agent API contracts.
import type { JSONSchema } from './schema';
import type { ContextConfig, InviteConfig, ReActConfig, RecordBase } from './shared';

export interface AgentData {
	id: string;
	name: string;
	system_prompt: string;
	context_config: ContextConfig;
	react_config: ReActConfig;
	invite_config: InviteConfig;
}

export interface AgentView extends RecordBase {
	user_id: string;
	data: AgentData;
	/**
	 * Whether the current viewer may PATCH/DELETE this agent. `false`
	 * for agents shared to the viewer with read-only permission.
	 */
	editable: boolean;
}

export interface CreateAgentRequest {
	name: string;
	system_prompt?: string;
	context_config?: ContextConfig;
	react_config?: ReActConfig;
	invite_config?: InviteConfig;
}

export interface CreateAgentResponse {
	agent_id: string;
}

export interface UpdateAgentRequest {
	name?: string;
	system_prompt?: string;
	context_config?: ContextConfig;
	react_config?: ReActConfig;
	invite_config?: InviteConfig;
}

export interface AgentListResponse {
	agents: AgentView[];
	total: number;
}

/**
 * @deprecated Superseded by {@link AgentSchemaV2Response}. Kept only for
 * legacy consumers still calling `GET /agent/schema`. The new form flow
 * uses `GET /agent/schema/v2`, which returns the full `AgentData` JSON
 * Schema in a single `schema` field.
 */
export interface AgentSchemaResponse {
	identity: JSONSchema;
	context_config: JSONSchema;
	react_config: JSONSchema;
}

/**
 * Response of `GET /agent/schema/v2`. `schema` is the full `AgentData`
 * JSON Schema (with `$ref`s inlined, `id` filtered out, and
 * `context_config.summary_schema` filtered out). The frontend derives
 * its section grouping directly from `schema.properties`:
 *   - top-level scalar/textarea/boolean properties → "identity" section
 *   - top-level `object`-typed properties (currently `context_config`,
 *     `react_config`, and `invite_config`) → one section each
 */
export interface AgentSchemaV2Response {
	schema: JSONSchema;
}
