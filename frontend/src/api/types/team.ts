// team API contracts.
import type { AgentView } from './agent';
import type { RecordBase } from './shared';

export interface TeamData {
	name: string;
	description: string;
	/** Worker agent ids belonging to the team. */
	member_ids: string[];
}

export interface TeamRecord extends RecordBase {
	user_id: string;
	/** The leader session id — the session that called `TeamCreate`. */
	session_id: string;
	data: TeamData;
}

/**
 * One member entry inside `TeamDetailResponse.members`. Pairs the
 * worker's `AgentView` with its single `session_id` so the UI can
 * navigate straight to the worker's chat.
 */
export interface TeamMemberInfo {
	agent: AgentView;
	/** `null` if the agent is in an inconsistent state (no session). */
	session_id: string | null;
}

/**
 * Resolved team detail returned inline inside `SessionView.team`.
 *
 * The leader's `AgentView` is looked up from the team's
 * `session_id` → `session.agent_id` chain on the server side.
 */
export interface TeamDetailResponse {
	team: TeamRecord;
	leader_agent: AgentView | null;
	members: TeamMemberInfo[];
}
