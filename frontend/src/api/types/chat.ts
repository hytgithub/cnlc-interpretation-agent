// chat API contracts.

export type { Msg, ContentBlock } from '@agentscope-ai/agentscope/message';

export type { AgentEvent } from '@agentscope-ai/agentscope/event';

import type {
	UserConfirmResultEvent,
	ExternalExecutionResultEvent,
} from '@agentscope-ai/agentscope/event';
import type { Msg } from '@agentscope-ai/agentscope/message';

export interface ChatRequest {
	agent_id: string;
	session_id: string;
	input: Msg | Msg[] | UserConfirmResultEvent | ExternalExecutionResultEvent | null;
}
