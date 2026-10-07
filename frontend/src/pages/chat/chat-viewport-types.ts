export interface ChatViewportProps {
	/**
	 * The agent that owns the session being viewed. May be the
	 * user-facing leader agent or — when drilled into a team member
	 * via the URL's `:memberId` slot — a worker agent.
	 */
	agentId: string | null;
	/**
	 * The session whose messages, model config, permission mode, and
	 * workspace drive every control rendered here.
	 */
	sessionId: string | null;
	/**
	 * Optional hook invoked when a server-side change to this session
	 * or its team arrives on the SSE stream. The outer page owns the
	 * session list that backs the sidebar, so it must be told to
	 * refetch too; passing this callback wires that signal up.
	 */
	onSessionsChanged?: () => void;
}
