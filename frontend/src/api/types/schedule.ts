// schedule API contracts.
import type { ChatModelConfig } from './model';
import type { PermissionMode, RecordBase } from './shared';

export type ScheduleSource = 'USER' | 'AGENT';

export interface ScheduleData {
	name: string;
	description: string;
	enabled: boolean;
	timezone: string;
	cron_expression: string;
	started_at: string;
	ended_at: string | null;
	chat_model_config: ChatModelConfig;
	stateful: boolean;
	permission_mode: PermissionMode;
	source: ScheduleSource;
	source_session_id: string;
}

export interface ScheduleRecord extends RecordBase {
	user_id: string;
	agent_id: string;
	data: ScheduleData;
}

export interface CreateScheduleRequest {
	name: string;
	description?: string;
	cron_expression: string;
	timezone?: string;
	agent_id: string;
	chat_model_config: ChatModelConfig;
	enabled?: boolean;
	stateful?: boolean;
	permission_mode?: PermissionMode;
}

export interface CreateScheduleResponse {
	schedule_id: string;
}

export interface UpdateScheduleRequest {
	name?: string;
	description?: string;
	cron_expression?: string;
	timezone?: string;
	enabled?: boolean;
	stateful?: boolean;
	permission_mode?: PermissionMode;
}

export interface ScheduleListResponse {
	schedules: ScheduleRecord[];
	total: number;
}
