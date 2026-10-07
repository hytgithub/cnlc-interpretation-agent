// model API contracts.

export interface ChatModelConfig {
	type: string;
	credential_id: string;
	model: string;
	parameters: Record<string, unknown>;
}

export interface TTSModelConfig {
	type: string;
	credential_id: string;
	model: string;
	parameters: Record<string, unknown>;
}

export interface ModelCard {
	type: 'chat_model';
	name: string;
	label: string;
	status: 'active' | 'deprecated' | 'sunset';
	deprecated_at: string | null;
	input_types: string[];
	output_types: string[];
	context_size: number;
	output_size: number;
	parameter_schema: Record<string, unknown>;
	parameters_overrides: Record<string, Record<string, unknown>>;
}

export interface ListModelRequest {
	provider: string;
}

export interface ListModelResponse {
	models: ModelCard[];
	total: number;
}

export interface EmbeddingModelConfig {
	type: string;
	credential_id: string;
	model: string;
	/**
	 * Output vector dimensions, pinned at config time. Required because
	 * the backend uses it to size the vector store collection and to
	 * validate against the manager's `DimensionPolicy`.
	 */
	dimensions: number;
	parameters: Record<string, unknown>;
}

export interface EmbeddingModelCard {
	type: 'embedding_model';
	name: string;
	label: string;
	status: 'active' | 'deprecated' | 'sunset';
	input_types: string[];
	output_types: string[];
	context_size: number | null;
	/** Default output dimensions for this model. */
	dimensions: number;
	/**
	 * If set, the only dimensions this model can produce (Matryoshka).
	 * `null` means the model is fixed-dim at `dimensions`.
	 */
	supported_dimensions: number[] | null;
	parameter_schema: Record<string, unknown>;
	parameter_overrides: Record<string, Record<string, unknown>>;
}

/** Response of `GET /embedding-model/` — the provider's full catalogue. */
export interface ListEmbeddingModelResponse {
	models: EmbeddingModelCard[];
	total: number;
}

export interface TTSModelCard {
	type: 'tts_model';
	name: string;
	label: string;
	status: 'active' | 'deprecated' | 'sunset';
	deprecated_at: string | null;
	input_types: string[];
	output_types: string[];
	realtime: boolean;
	parameter_schema: Record<string, unknown>;
	parameters_overrides: Record<string, Record<string, unknown>>;
}

export interface ListTTSModelResponse {
	models: TTSModelCard[];
	total: number;
}
