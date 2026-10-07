// workspace API contracts.

/** One entry in a workspace directory listing. */
export interface DirectoryEntry {
	name: string;
	is_dir: boolean;
	/** Always null for a directory, and for a file the backend could not stat. */
	size_bytes: number | null;
	/** Last modification time as a Unix timestamp. */
	updated_at: number | null;
}

/** One directory level, plus the path it actually resolved to. */
export interface DirectoryListing {
	/**
	 * Absolute path of the directory that was listed. The only way to
	 * learn where a relative request landed — the workspace root is
	 * backend-dependent and unknowable client-side.
	 */
	path: string;
	entries: DirectoryEntry[];
}

/** Git state of one directory. */
export interface GitStatus {
	/** `null` on a detached HEAD. */
	branch: string | null;
	/** Full commit SHA, or `null` when the repository has no commits. */
	head: string | null;
	/**
	 * Commits ahead of the upstream. `null` means no upstream is
	 * configured, which is a different state from being level with one.
	 */
	ahead: number | null;
	behind: number | null;
	/**
	 * Lines changed relative to HEAD. Untracked files contribute
	 * nothing — `git diff` does not see them — so a session that only
	 * created files reports zero here and a non-zero `untracked`.
	 */
	insertions: number;
	deletions: number;
	/** File counts. */
	staged: number;
	unstaged: number;
	untracked: number;
	conflicted: number;
}

/** Where a session is pointed, and the git state of that place. */
export interface WorkspaceStatus {
	/** Absolute path of the workspace root; not derivable client-side. */
	workdir: string;
	/** Absolute path the session is focused on. Equals `workdir` when unset. */
	cwd: string;
	/**
	 * `null` when there is nothing to report — not a repository, git
	 * unavailable, timed out. The badge is hidden either way.
	 */
	git: GitStatus | null;
}
