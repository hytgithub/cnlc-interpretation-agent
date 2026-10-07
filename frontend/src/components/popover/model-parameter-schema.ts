export interface ParameterProperty {
	type?: string;
	title?: string;
	description?: string;
	default?: unknown;
	minimum?: number;
	maximum?: number;
	exclusiveMinimum?: number;
	exclusiveMaximum?: number;
	enum?: unknown[];
	anyOf?: ParameterProperty[];
}

export interface ParameterSchema {
	title?: string;
	description?: string;
	type?: string;
	properties?: Record<string, ParameterProperty>;
	required?: string[];
}

export interface ResolvedType {
	type: string;
	enumValues: unknown[] | null;
}

/** Resolve a property's effective scalar type and enum values, looking
 *  through ``anyOf`` and ignoring ``null`` variants. */
export function resolveType(prop: ParameterProperty): ResolvedType {
	if (prop.type) {
		return { type: prop.type, enumValues: prop.enum ?? null };
	}
	for (const variant of prop.anyOf ?? []) {
		if (variant.type && variant.type !== 'null') {
			return {
				type: variant.type,
				enumValues: variant.enum ?? prop.enum ?? null,
			};
		}
	}
	return { type: 'string', enumValues: null };
}

/** Extract default values from a TTS model card's parameter schema. */
export function extractDefaults(schema: ParameterSchema | undefined): Record<string, unknown> {
	const defaults: Record<string, unknown> = {};
	if (schema?.properties) {
		for (const [k, p] of Object.entries(schema.properties)) {
			if (p.default !== undefined) defaults[k] = p.default;
		}
	}
	return defaults;
}
