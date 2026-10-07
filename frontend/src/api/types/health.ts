// health API contracts.

/** `disabled` means the deployment turned an optional feature off, not that it is down. */
export type ComponentStatus = 'ok' | 'not_ready' | 'disabled';

export interface HealthResponse {
	status: 'ok' | 'not_ready';
	version: string;
	components: Record<string, ComponentStatus>;
}
