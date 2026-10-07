// hub API contracts.
import type { HttpMCPConfig, StdioMCPConfig } from './mcp';
import type { JSONSchema } from './schema';

/** One registered hub, as shown in the hub picker. */
export interface HubInfo {
	hub_id: string;
	display_name: string;
	description: string;
	/** `null` when the hub has no icon; fall back rather than leave a gap. */
	icon_url: string | null;
}

/**
 * Query for browsing one hub. Pagination is cursor-based — pass the previous
 * page's `next_cursor` to load more; a `null` cursor means the end.
 */
export interface HubBrowseParams {
	/** Keyword search. Some hubs answer this from a separate, unpaginated endpoint. */
	q?: string;
	cursor?: string;
	/** 1-200, defaults to 20 server-side. */
	limit?: number;
}

interface HubCardBase {
	/** The hub this card came from. Together with `id` it addresses the card globally. */
	hub_id: string;
	/**
	 * The card's id on its hub — opaque, and not necessarily URL-safe (some
	 * registries use ids containing `:`). Always encode it into a path.
	 */
	id: string;
	name: string;
	display_name?: string | null;
	description: string;
	tags: string[];
	version?: string | null;
}

/**
 * An MCP listing: a *template*, not something connectable. `config_template`
 * holds `${...}` placeholders that the server fills from the values submitted
 * at install time — never substitute them client-side.
 */
export interface MCPCard extends HubCardBase {
	is_stateful: boolean;
	updated_at?: number | null;
	/** Who published it. `null` when the hub does not say. */
	author?: string | null;
	/** An image representing it. `null` when the hub offers none. */
	icon_url?: string | null;
	/** Its page on the hub's website. `null` if it has none. */
	url?: string | null;
	/** `null` means uncounted, which is not the same as zero. */
	installs?: number | null;
	downloads?: number | null;
	/** `none` — install directly, no form. `inputs` — render `inputs_schema`. */
	auth: 'none' | 'inputs';
	/**
	 * JSON Schema for the install form. Empty (no `properties`) when the card
	 * needs no configuration, so branch on `auth` before rendering.
	 * Secret fields carry `writeOnly: true` / `format: 'password'`.
	 */
	inputs_schema: Partial<JSONSchema>;
	/**
	 * The server's long-form docs. Only populated by the detail endpoint —
	 * READMEs run to tens of kilobytes, so listings leave them out.
	 */
	readme?: string | null;
	/** Shown read-only; the placeholders are resolved server-side. */
	config_template: StdioMCPConfig | HttpMCPConfig;
}

/** A skill listing. Unlike an MCP there is nothing to configure. */
export interface SkillCard extends HubCardBase {
	updated_at?: number | null;
	/** Who published it. `null` when the hub does not say. */
	author?: string | null;
	/**
	 * An image representing the skill. `null` when the hub offers none —
	 * fall back rather than rendering a broken image.
	 */
	icon_url?: string | null;
	/**
	 * How many times the skill has been installed. `null` means the hub does
	 * not count installs — which is not the same as zero, so don't render it.
	 */
	installs?: number | null;
	/** How many times it has been downloaded. `null` when uncounted. */
	downloads?: number | null;
	/** The skill's page on the hub's website. `null` if it has none. */
	url?: string | null;
	/** The `SKILL.md` body — only populated by the detail endpoint. */
	markdown?: string | null;
	metadata: Record<string, unknown>;
}

export interface MCPHubPage {
	cards: MCPCard[];
	/** `null` when this is the last page. */
	next_cursor: string | null;
}

export interface SkillHubPage {
	cards: SkillCard[];
	next_cursor: string | null;
}

/**
 * The outcome of putting library MCPs into a workspace, reported per MCP:
 * connecting happens one at a time, so a bad API key on the third pick must
 * not throw away the two that worked.
 */
export interface AddFromLibraryResponse {
	/** Now in the workspace. Excludes ones already present. */
	added: string[];
	/** Whatever could not be added, mapped to why. */
	failed: Record<string, string>;
}
