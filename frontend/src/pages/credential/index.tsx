import { Plus } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

import { DetailPanel } from './detail-panel';
import type { CredentialSchema, CredentialView } from '@/api';
import { credentialApi } from '@/api';
import { CreateCredentialDialog } from '@/components/dialog/CreateCredentialDialog';
import { DeleteDialog } from '@/components/dialog/DeleteDialog';
import { EditCredentialDialog } from '@/components/dialog/EditCredentialDialog';
import { Badge } from '@/components/ui/badge';
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from '@/components/ui/empty';
import {
	Sidebar,
	SidebarContent,
	SidebarGroup,
	SidebarGroupContent,
	SidebarGroupLabel,
	SidebarHeader,
	SidebarMenu,
	SidebarMenuButton,
	SidebarMenuItem,
} from '@/components/ui/sidebar';
import { Skeleton } from '@/components/ui/skeleton';
import { useCredentials } from '@/hooks/useCredentials';
import { useTranslation } from '@/i18n/useI18n';

// ─── Page ─────────────────────────────────────────────────────────────────────

export const CredentialPage = () => {
	const { t } = useTranslation();
	const { credentials, loading, remove, refetch } = useCredentials();
	const [schemas, setSchemas] = useState<CredentialSchema[]>([]);
	const [selectedId, setSelectedId] = useState<string | null>(null);
	const [createOpen, setCreateOpen] = useState(false);
	const [createDefaultType, setCreateDefaultType] = useState<string | undefined>();
	const [editOpen, setEditOpen] = useState(false);
	const [deleteOpen, setDeleteOpen] = useState(false);

	useEffect(() => {
		credentialApi.schemas().then((res) => setSchemas(res.schemas));
	}, []);

	// Auto-select first credential
	useEffect(() => {
		if (!selectedId && credentials.length > 0) {
			setSelectedId(credentials[0].id);
		}
	}, [credentials, selectedId]);

	const selectedCredential = credentials.find((c) => c.id === selectedId) ?? null;
	const selectedSchema = selectedCredential
		? (schemas.find(
				(s) => (s.properties.type?.const as string) === (selectedCredential.data.type as string),
			) ?? null)
		: null;

	// Group credentials by type, then list all schema types (even empty ones)
	const groupedByType: Array<{ type: string; title: string; records: CredentialView[] }> =
		schemas.map((s) => {
			const type = s.properties.type?.const as string;
			return {
				type,
				title: s.title,
				records: credentials.filter((c) => c.data.type === type),
			};
		});

	// Split providers so the user's actual configuration leads, and the
	// (mostly empty) "add a provider" entries don't drown it out.
	const configuredGroups = groupedByType.filter((g) => g.records.length > 0);
	const totalConfigured = configuredGroups.reduce((n, g) => n + g.records.length, 0);

	const handleOpenCreate = useCallback((type?: string) => {
		setCreateDefaultType(type);
		setCreateOpen(true);
	}, []);

	const handleDelete = useCallback(async () => {
		if (!selectedCredential) return;
		await remove(selectedCredential.id);
		setSelectedId(null);
	}, [selectedCredential, remove]);

	return (
		<div className="flex h-full w-full p-2 gap-2">
			{/* Left sidebar */}
			<Sidebar collapsible="none" className="rounded-[22px]">
				<SidebarHeader className={'flex flex-col p-[20px_18px_14px] gap-y-1'}>
					<div className="text-xl font-medium tracking-[-0.02em] text-foreground">
						{t('common.credential')}
					</div>
					<div className="text-text-tertiary text-xs">{t('credential.subtitle')}</div>
				</SidebarHeader>
				{/*<Separator />*/}
				<SidebarContent>
					{loading ? (
						<div className="flex flex-col gap-y-2 p-4">
							{Array.from({ length: 3 }).map((_, i) => (
								<Skeleton key={i} className="h-8 rounded" />
							))}
						</div>
					) : groupedByType.length === 0 ? (
						<Empty className="border-none py-8">
							<EmptyHeader>
								<EmptyTitle>{t('credential.noProviders')}</EmptyTitle>
							</EmptyHeader>
						</Empty>
					) : (
						<>
							{/* Configured credentials lead — this is what the user actually set up. */}
							{configuredGroups.length > 0 && (
								<SidebarGroup className="mt-6 px-2 py-0">
									<SidebarGroupLabel className="justify-between">
										{t('credential.configured')}
										<span className="text-[10px] text-text-data font-mono">{totalConfigured}</span>
									</SidebarGroupLabel>
									<SidebarGroupContent>
										{configuredGroups.map(({ type, title, records }) => (
											<SidebarGroup key={type} className="mt-3 px-0 py-0">
												<SidebarGroupLabel>{title}</SidebarGroupLabel>
												<SidebarGroupContent>
													<SidebarMenu>
														{records.map((rec) => {
															const name = (rec.data.name as string | undefined) ?? rec.id;
															return (
																<SidebarMenuItem key={rec.id}>
																	<SidebarMenuButton
																		isActive={selectedId === rec.id}
																		onClick={() => setSelectedId(rec.id)}
																	>
																		<span className="min-w-0 flex-1 truncate">{name}</span>
																		{!rec.editable && (
																			<Badge
																				variant="secondary"
																				className="text-[10px] px-1 py-0"
																				title={t('common.readOnlyTooltip')}
																			>
																				{t('common.readOnly')}
																			</Badge>
																		)}
																	</SidebarMenuButton>
																</SidebarMenuItem>
															);
														})}
													</SidebarMenu>
												</SidebarGroupContent>
											</SidebarGroup>
										))}
									</SidebarGroupContent>
								</SidebarGroup>
							)}

							{/* Add credential — every provider is an entry point (including
							    configured ones, to add more under the same provider). */}
							<SidebarGroup className="mt-5 px-2 py-0">
								<SidebarGroupLabel>{t('credential.addProvider')}</SidebarGroupLabel>
								<SidebarGroupContent>
									<SidebarMenu>
										{groupedByType.map(({ type, title }) => (
											<SidebarMenuItem key={type}>
												<SidebarMenuButton onClick={() => handleOpenCreate(type)}>
													<Plus />
													<span className="min-w-0 flex-1 truncate">{title}</span>
												</SidebarMenuButton>
											</SidebarMenuItem>
										))}
									</SidebarMenu>
								</SidebarGroupContent>
							</SidebarGroup>
						</>
					)}
				</SidebarContent>
			</Sidebar>

			{/* Right detail */}
			<main className="flex-1 min-h-0 overflow-hidden rounded-[22px] bg-card shadow-panel">
				{selectedCredential ? (
					<DetailPanel
						credential={selectedCredential}
						schema={selectedSchema}
						onEdit={() => setEditOpen(true)}
						onDelete={() => setDeleteOpen(true)}
					/>
				) : (
					<div className="flex h-full items-center justify-center">
						<Empty className="border-none">
							<EmptyHeader>
								<EmptyTitle>{t('credential.selectHint')}</EmptyTitle>
								<EmptyDescription>{t('credential.selectHintDescription')}</EmptyDescription>
							</EmptyHeader>
						</Empty>
					</div>
				)}
			</main>

			{/* Dialogs */}
			<CreateCredentialDialog
				open={createOpen}
				onOpenChange={setCreateOpen}
				defaultType={createDefaultType}
				onCreated={() => refetch()}
			/>
			{selectedCredential && (
				<>
					<EditCredentialDialog
						open={editOpen}
						onOpenChange={setEditOpen}
						credential={selectedCredential}
						onUpdated={() => refetch()}
					/>
					<DeleteDialog
						open={deleteOpen}
						onOpenChange={setDeleteOpen}
						title={t('common.deleteTitle', {
							entity: t('credential.deleteEntity'),
							name: (selectedCredential.data.name as string | undefined) ?? selectedCredential.id,
						})}
						description={t('common.deleteDescription')}
						onConfirm={handleDelete}
					/>
				</>
			)}
		</div>
	);
};
