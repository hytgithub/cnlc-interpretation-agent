import type { PermissionContext } from '@agentscope-ai/agentscope/permission';
import type { TaskContext } from '@agentscope-ai/agentscope/state';
import { BookText, Database, ListTodo, ShieldCheck, UsersRound } from 'lucide-react';
import { useMemo } from 'react';

import type { SessionKnowledgeConfig, SessionView } from '@/api';
import MCPSvg from '@/assets/images/mcp.svg?react';
import { KnowledgeBasePanel } from '@/components/panel/KnowledgeBasePanel';
import { McpPanel } from '@/components/panel/McpPanel';
import { type PanelDescriptor, type PanelKey } from '@/components/panel/PanelDock.tsx';
import { PermissionPanel } from '@/components/panel/PermissionPanel';
import { SkillPanel } from '@/components/panel/SkillPanel';
import { TaskPanel } from '@/components/panel/TaskPanel';
import { TeamPanel } from '@/components/panel/TeamPanel';
import { KnowledgeBaseParametersPopover } from '@/components/popover/KnowledgeBaseParametersPopover';
import { Badge } from '@/components/ui/badge';
import { useKnowledgeBaseMiddlewareSchema } from '@/hooks/useKnowledgeBaseMiddlewareSchema';
import { useKnowledgeBases } from '@/hooks/useKnowledgeBases';
import { useWorkspace } from '@/hooks/useWorkspace.ts';
import { useTranslation } from '@/i18n/useI18n';
interface ChatPanelsOptions {
	t: ReturnType<typeof useTranslation>['t'];
	tasksContext: TaskContext | null;
	permissionContext: PermissionContext | null;
	workspace: ReturnType<typeof useWorkspace>;
	knowledge: ReturnType<typeof useKnowledgeBases>;
	selectedKnowledgeConfig: SessionKnowledgeConfig | null;
	kbMiddlewareSchema: ReturnType<typeof useKnowledgeBaseMiddlewareSchema>['schema'];
	handleKnowledgeConfigChange: (config: SessionKnowledgeConfig | null) => Promise<void>;
	sessionId: string | null;
	view: SessionView | null;
}
export function useChatPanels(options: ChatPanelsOptions) {
	const {
		t,
		tasksContext,
		permissionContext,
		workspace,
		knowledge,
		selectedKnowledgeConfig,
		kbMiddlewareSchema,
		handleKnowledgeConfigChange,
		sessionId,
		view,
	} = options;
	const {
		mcps,
		loading: mcpsLoading,
		addMcps,
		addMcpsFromLibrary,
		removeMcp,
		skills,
		skillsLoading,
		uploadSkill,
		addSkillsFromLibrary,
		removeSkill,
	} = workspace;
	const { knowledgeBases, loading: knowledgeBasesLoading } = knowledge;
	// Build the panel descriptors with live data. Rebuilt on every
	// data change so the dock always renders the latest state — the
	// dock itself stays free of any data dependency.
	const panels = useMemo<Record<PanelKey, PanelDescriptor>>(
		() => ({
			plan: {
				title: t('panel.plan.title'),
				icon: <ListTodo className="size-4" />,
				content: <TaskPanel tasksContext={tasksContext} />,
			},
			mcp: {
				title: 'MCP',
				icon: <MCPSvg className="size-4" />,
				content: (
					<McpPanel
						mcps={mcps}
						loading={mcpsLoading}
						onAdd={addMcps}
						onAddFromLibrary={addMcpsFromLibrary}
						onRemove={removeMcp}
					/>
				),
			},
			skill: {
				title: t('panel.skill.title'),
				icon: <BookText className="size-4" />,
				content: (
					<SkillPanel
						skills={skills}
						loading={skillsLoading}
						onUpload={uploadSkill}
						onAddFromLibrary={addSkillsFromLibrary}
						onRemove={removeSkill}
					/>
				),
			},
			permission: {
				title: (
					<span className="flex items-center gap-x-2">
						{t('panel.permission.title')}
						{permissionContext?.mode ? (
							<Badge variant="outline" className="capitalize">
								{t('panel.permission.mode', { mode: permissionContext.mode })}
							</Badge>
						) : null}
					</span>
				),
				icon: <ShieldCheck className="size-4" />,
				content: <PermissionPanel permissionContext={permissionContext} />,
			},
			knowledge: {
				title: (
					<span className="flex items-center gap-x-2">
						{t('panel.knowledge.title')}
						{selectedKnowledgeConfig?.knowledge_base_ids.length ? (
							<Badge variant="outline">{selectedKnowledgeConfig.knowledge_base_ids.length}</Badge>
						) : null}
					</span>
				),
				icon: <Database className="size-4" />,
				actions: (
					<KnowledgeBaseParametersPopover
						value={selectedKnowledgeConfig}
						schema={kbMiddlewareSchema}
						onChange={handleKnowledgeConfigChange}
						disabled={!sessionId}
					/>
				),
				content: (
					<KnowledgeBasePanel
						knowledgeBases={knowledgeBases}
						loading={knowledgeBasesLoading}
						value={selectedKnowledgeConfig}
						onChange={handleKnowledgeConfigChange}
						disabled={!sessionId}
					/>
				),
			},
			team: {
				title: (
					<span className="flex items-center gap-x-2">
						{t('common.team')}
						{view?.team ? <Badge variant="outline">{view.team.members.length}</Badge> : null}
					</span>
				),
				icon: <UsersRound className="size-4" />,
				content: <TeamPanel team={view?.team ?? null} currentSessionId={sessionId} />,
			},
		}),
		[
			t,
			tasksContext,
			mcps,
			mcpsLoading,
			addMcps,
			addMcpsFromLibrary,
			removeMcp,
			skills,
			skillsLoading,
			uploadSkill,
			addSkillsFromLibrary,
			removeSkill,
			permissionContext,
			knowledgeBases,
			knowledgeBasesLoading,
			selectedKnowledgeConfig,
			kbMiddlewareSchema,
			handleKnowledgeConfigChange,
			sessionId,
			view,
		],
	);
	return panels;
}
