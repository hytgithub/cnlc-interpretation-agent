// knowledge API contracts.
import type { CredentialView } from './credential';
import type { EmbeddingModelCard, EmbeddingModelConfig } from './model';
import type { JSONSchema } from './schema';

export interface ChunkerConfig {
	type: string;
	parameters: Record<string, unknown>;
}

export interface ChunkerInfo {
	type: string;
	parameter_schema: JSONSchema;
}

export interface ListChunkersResponse {
	chunkers: ChunkerInfo[];
}

/**
 * Knowledge base view as exposed by the API. Mirrors
 * :class:`agentscope.app._service.KnowledgeBaseView`.
 */
export interface KnowledgeBaseView {
	id: string;
	name: string;
	description: string;
	embedding_model_config: EmbeddingModelConfig;
	chunker_config?: ChunkerConfig;
	created_at: string;
	updated_at: string;
	/**
	 * Whether the current viewer may modify this knowledge base (edit
	 * metadata, add/delete documents). `false` for knowledge bases
	 * shared with read-only permission.
	 */
	editable: boolean;
	/** Number of documents registered in the knowledge base. */
	document_count: number;
	/** Total indexed chunks across all documents. */
	chunk_count: number;
	/**
	 * Display name of the credential behind
	 * `embedding_model_config.credential_id`, resolved server-side so
	 * shared viewers see it too. `null` when the credential was deleted.
	 */
	credential_name: string | null;
	/** Per-indexing-status document counts; always served. */
	status_counts: KnowledgeBaseStatusCounts;
}

/** Documents of one knowledge base, counted by indexing status. */
export interface KnowledgeBaseStatusCounts {
	pending: number;
	parsing: number;
	chunking: number;
	indexing: number;
	ready: number;
	error: number;
}

/** Query parameters accepted by `GET /knowledge_bases/`. */
export interface ListKnowledgeBasesParams {
	/** Filter down to one knowledge base — list doubles as get-single. */
	id?: string;
	/** Case-insensitive substring filter on the name. */
	name?: string;
	/** 1-based page number (default 1). */
	page?: number;
	/** Page size (default 30, max 128). */
	page_size?: number;
	orderby?: 'create_time' | 'update_time';
	desc?: boolean;
}

export interface ListKnowledgeBasesResponse {
	knowledge_bases: KnowledgeBaseView[];
	/** Total across all pages (after filters), for page counts. */
	total: number;
	page: number;
	page_size: number;
}

export interface CreateKnowledgeBaseRequest {
	name: string;
	description?: string;
	embedding_model_config: EmbeddingModelConfig;
	chunker_config: ChunkerConfig;
}

export interface CreateKnowledgeBaseResponse {
	knowledge_base_id: string;
}

/**
 * Body for `PATCH /knowledge_bases/{id}`. Only mutable fields can be
 * sent; the embedding model is pinned at creation time and cannot
 * change because the underlying collection is sized to its dimension.
 */
export interface UpdateKnowledgeBaseRequest {
	name?: string;
	description?: string;
}

/**
 * Lifecycle states a document can be in. Mirrors
 * :class:`agentscope.app.storage.KnowledgeDocumentStatus`.
 *
 * - `pending` — accepted, blob stored, indexing not yet started.
 * - `parsing` / `chunking` / `indexing` — worker phases.
 * - `ready` — chunks committed to the vector store.
 * - `error` — terminal failure; `error` field carries the reason.
 */
export type KnowledgeDocumentStatus =
	'pending' | 'parsing' | 'chunking' | 'indexing' | 'ready' | 'error';

/**
 * Document view returned by `/knowledge_bases/{id}/documents` and
 * `/knowledge_bases/{id}/documents/status`. Mirrors
 * :class:`agentscope.app._router._schema.KnowledgeDocumentView`.
 */
export interface KnowledgeDocumentView {
	id: string;
	filename: string;
	size: number;
	content_type: string | null;
	status: KnowledgeDocumentStatus;
	error: string | null;
	chunk_count: number;
	created_at: string;
	updated_at: string;
}

/** Query parameters accepted by `GET /knowledge_bases/{id}/documents`. */
export interface ListKnowledgeDocumentsParams {
	/** Filter down to one document by id. */
	id?: string;
	/** Case-insensitive substring filter on the filename. */
	keywords?: string;
	/** Filter by indexing status. */
	status?: KnowledgeDocumentStatus;
	/** 1-based page number (default 1). */
	page?: number;
	/** Page size (default 30, max 128). */
	page_size?: number;
	orderby?: 'create_time' | 'update_time';
	desc?: boolean;
}

export interface ListKnowledgeDocumentsResponse {
	documents: KnowledgeDocumentView[];
	/** Total across all pages (after filters), for page counts. */
	total: number;
	page: number;
	page_size: number;
}

export interface ListKnowledgeDocumentStatusResponse {
	items: KnowledgeDocumentView[];
}

export interface UploadKnowledgeDocumentResponse {
	document_id: string;
	filename: string;
	status: KnowledgeDocumentStatus;
}

export interface SearchKnowledgeBaseRequest {
	query: string;
	top_k?: number;
}

/**
 * Lightweight chunk shape returned inside `VectorSearchResult`. Mirrors
 * :class:`agentscope.rag.Chunk` — content is the raw `TextBlock` /
 * `DataBlock` discriminated union the backend ships.
 */
export interface KnowledgeChunk {
	content: { type: 'text'; text: string; id?: string } | { type: string; [key: string]: unknown };
	source: string;
	chunk_index: number;
	total_chunks: number;
	metadata: Record<string, unknown>;
}

/**
 * Response of `GET /knowledge_bases/{id}/documents/{doc}/chunks` —
 * one page of a document's chunks in `chunk_index` order.
 */
export interface ListDocumentChunksResponse {
	chunks: KnowledgeChunk[];
	/** Total chunks in the document; `0` while it is still indexing. */
	total: number;
	page: number;
	page_size: number;
}

/**
 * Response of `POST /knowledge_bases/{id}/documents/{doc}/download_token`
 * — a short-lived capability for browser-native fetches (`<iframe>`,
 * `<img>`, download links) that cannot carry the `X-User-ID` header.
 */
export interface DocumentDownloadTokenResponse {
	token: string;
	/** Unix timestamp after which the token is refused. */
	expires_at: number;
}

/**
 * One vector search hit returned by the knowledge base search endpoint.
 * Mirrors :class:`agentscope.rag.VectorSearchResult` on the backend.
 */
export interface VectorSearchResult {
	score: number;
	document_id: string;
	chunk: KnowledgeChunk;
}

export interface SearchKnowledgeBaseResponse {
	results: VectorSearchResult[];
	total: number;
}

/**
 * Mirrors :class:`agentscope.app.rag.knowledge_base_manager.DimensionPolicyKind`.
 */
export type DimensionPolicyKind = 'any' | 'fixed' | 'locked_by_existing';

/**
 * Mirrors :class:`agentscope.app.rag.knowledge_base_manager.DimensionPolicy`.
 */
export interface DimensionPolicy {
	kind: DimensionPolicyKind;
	dimension: number | null;
}

/** One credential and the embedding models it can serve, post-policy. */
export interface KbEmbeddingProvider {
	credential: CredentialView;
	models: EmbeddingModelCard[];
}

/**
 * Response of `GET /knowledge_bases/embedding_models`.
 *
 * Server-side already filtered models by the manager's
 * :class:`DimensionPolicy` and narrowed matryoshka cards to the
 * locked dimension when applicable. The policy is included so the
 * UI can render an explanatory banner.
 */
export interface ListKbEmbeddingModelsResponse {
	providers: KbEmbeddingProvider[];
	policy: DimensionPolicy;
}

/**
 * Session-level knowledge base attachment. Persisted on
 * :class:`SessionConfig.knowledge_config` and translated into a
 * `KnowledgeBaseMiddleware` at chat-run time.
 *
 * `parameters` holds the user-tunable middleware fields verbatim — its
 * accepted keys/values are described by the JSON Schema returned from
 * `GET /knowledge_bases/middleware/parameters_schema`.
 */
export interface SessionKnowledgeConfig {
	knowledge_base_ids: string[];
	parameters: Record<string, unknown>;
}

/** Response of `GET /knowledge_bases/middleware/parameters_schema`. */
export interface KbMiddlewareParametersSchemaResponse {
	parameter_schema: Record<string, unknown>;
}

/** Response of `GET /knowledge_bases/supported_content_types`. */
export interface ListSupportedContentTypesResponse {
	/** Union of IANA media types every registered parser handles. */
	media_types: string[];
	/** Union of filename extensions (each starting with `.`). */
	extensions: string[];
}
