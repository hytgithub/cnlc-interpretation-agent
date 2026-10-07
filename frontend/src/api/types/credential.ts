// credential API contracts.
import type { JSONSchema, JSONSchemaProperty } from './schema';
import type { RecordBase } from './shared';

export type CredentialSchemaProperty = JSONSchemaProperty;

// Credential schemas always include title + type (Pydantic always emits them
// for credential data classes); we narrow the generic JSONSchema here so call
// sites that read `schema.title` don't have to do null-checks.
export interface CredentialSchema extends JSONSchema {
	title: string;
	type: string;
}

export interface CredentialSchemasResponse {
	schemas: CredentialSchema[];
}

export interface CredentialView extends RecordBase {
	user_id: string;
	/**
	 * Credential payload. When the current viewer is not the owner
	 * (shared credential), only `type` and `name` are populated —
	 * secret fields are stripped server-side.
	 */
	data: Record<string, unknown>;
	/**
	 * Whether the current viewer may PATCH/DELETE this credential.
	 * `false` for credentials shared with read-only permission.
	 */
	editable: boolean;
}

export interface CreateCredentialRequest {
	data: Record<string, unknown>;
}

export interface CreateCredentialResponse {
	credential_id: string;
}

export interface UpdateCredentialRequest {
	data: Record<string, unknown>;
}

export interface CredentialListResponse {
	credentials: CredentialView[];
	total: number;
}
