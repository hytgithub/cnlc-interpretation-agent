import type { useChatPageState } from './useChatPageState';
import { DeleteDialog } from '@/components/dialog/DeleteDialog';
import { EditAgentDialog } from '@/components/dialog/EditAgentDialog';
import { RenameSessionDialog } from '@/components/dialog/RenameSessionDialog';

export function ChatSessionDialogs({ state }: { state: ReturnType<typeof useChatPageState> }) {
	const {
		t,
		refetchAgents,
		removeAgent,
		editOpen,
		setEditOpen,
		deleteOpen,
		setDeleteOpen,
		renameOpen,
		setRenameOpen,
		renameSession,
		deleteSessionOpen,
		setDeleteSessionOpen,
		sessionToDelete,
		selectedAgent,
		handleAgentDeleted,
		handleDeleteSession,
		handleRenameConfirm,
	} = state;
	return (
		<>
			{selectedAgent && (
				<>
					<EditAgentDialog
						open={editOpen}
						onOpenChange={setEditOpen}
						agent={selectedAgent}
						onUpdated={refetchAgents}
					/>
					<DeleteDialog
						open={deleteOpen}
						onOpenChange={setDeleteOpen}
						title={t('common.deleteTitle', {
							entity: t('dialog-agent-delete.entity'),
							name: selectedAgent.data.name,
						})}
						description={t('common.deleteDescription')}
						confirmLabel={t('dialog-agent-delete.confirm')}
						onConfirm={async () => {
							await removeAgent(selectedAgent.id);
							await handleAgentDeleted();
						}}
					/>
				</>
			)}
			<RenameSessionDialog
				open={renameOpen}
				onOpenChange={setRenameOpen}
				currentName={renameSession?.config.name ?? renameSession?.id ?? ''}
				onConfirm={handleRenameConfirm}
			/>
			<DeleteDialog
				open={deleteSessionOpen}
				onOpenChange={setDeleteSessionOpen}
				title={t('common.deleteTitle', {
					entity: t('dialog-session-delete.entity'),
					name: (() => {
						const raw = sessionToDelete?.config.name || sessionToDelete?.id || '';
						return raw.length > 30 ? `${raw.slice(0, 30)}…` : raw;
					})(),
				})}
				description={t('common.deleteDescription')}
				confirmLabel={t('dialog-session-delete.confirm')}
				onConfirm={async () => {
					if (sessionToDelete) {
						await handleDeleteSession(sessionToDelete.id);
					}
				}}
			/>
		</>
	);
}
