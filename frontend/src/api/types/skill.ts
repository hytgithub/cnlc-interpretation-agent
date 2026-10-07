// skill API contracts.

export interface Skill {
	name: string;
	description: string;
	dir: string;
	markdown: string;
	updated_at: number;
}

/**
 * @deprecated The path is resolved on the server, which only means
 * anything for a single-host deployment. Upload a folder or install
 * from the library instead.
 */
export interface AddSkillRequest {
	skill_path: string;
}

/**
 * One skill in the user's own library. Unlike an MCP, the skill's files are
 * not stored — the record says where they came from, and the archive is
 * re-fetched from the hub when the skill reaches a workspace.
 */
export interface SkillView {
	id: string;
	/** Unique per user — the handle a workspace refers to it by. */
	name: string;
	enabled: boolean;
	display_name: string | null;
	description: string;
	tags: string[];
	/** Snapshotted from the card at install time, so the library keeps the
	 *  identity of the listing it came from. */
	author: string | null;
	icon_url: string | null;
	url: string | null;
	hub_id: string | null;
	card_id: string | null;
	version: string | null;
}

/** A library skill with its `SKILL.md` body, from the detail endpoint. */
export interface SkillRecord extends SkillView {
	markdown: string;
}
