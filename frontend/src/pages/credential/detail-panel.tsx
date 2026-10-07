import { Pen, Trash2 } from 'lucide-react';
import { useEffect, useState } from 'react';

import { MaskedValue } from './masked-value';
import type { ModelTab } from './model-table';
import { ModelTable } from './model-table';
import type {
	CredentialSchema,
	CredentialView,
	EmbeddingModelCard,
	ModelCard,
	TTSModelCard,
} from '@/api';
import { embeddingModelApi, modelApi, ttsModelApi } from '@/api';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from '@/components/ui/empty';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useTranslation } from '@/i18n/useI18n';

// ─── Detail panel ─────────────────────────────────────────────────────────────
export interface DetailPanelProps {
	credential: CredentialView;
	schema: CredentialSchema | null;
	onEdit: () => void;
	onDelete: () => void;
}

export function DetailPanel({ credential, schema, onEdit, onDelete }: DetailPanelProps) {
	const { t } = useTranslation();
	const [models, setModels] = useState<ModelCard[]>([]);
	const [ttsModels, setTtsModels] = useState<TTSModelCard[]>([]);
	const [embeddingModels, setEmbeddingModels] = useState<EmbeddingModelCard[]>([]);
	const [modelsLoading, setModelsLoading] = useState(false);
	const [tab, setTab] = useState<ModelTab>('llm');

	const type = credential.data.type as string | undefined;
	const shown = tab === 'llm' ? models : tab === 'tts' ? ttsModels : embeddingModels;
	const total = models.length + ttsModels.length + embeddingModels.length;

	// A credential switch can land on a provider with no TTS models at
	// all, which would leave the tab pointing at an empty list.
	useEffect(() => setTab('llm'), [credential.id]);

	useEffect(() => {
		if (!type) return;
		setModelsLoading(true);
		Promise.all([
			modelApi
				.list(type)
				.then((res) => res.models)
				.catch(() => [] as ModelCard[]),
			ttsModelApi
				.list(type)
				.then((res) => res.models)
				.catch(() => [] as TTSModelCard[]),
			embeddingModelApi
				.list(type)
				.then((res) => res.models)
				.catch(() => [] as EmbeddingModelCard[]),
		])
			.then(([chatModels, tts, embeddings]) => {
				setModels(chatModels);
				setTtsModels(tts);
				setEmbeddingModels(embeddings);
			})
			.finally(() => setModelsLoading(false));
	}, [credential.id, type]);

	// Fields to display: use schema properties order, skip id/type/const fields
	const displayFields = schema
		? Object.entries(schema.properties).filter(
				([key, prop]) => key !== 'id' && key !== 'type' && prop.const === undefined,
			)
		: Object.entries(credential.data)
				.filter(([key]) => key !== 'id' && key !== 'type')
				.map(
					([key]) =>
						[key, { title: key, writeOnly: false }] as [
							string,
							{ title: string; writeOnly: boolean },
						],
				);

	const name = (credential.data.name as string | undefined) ?? credential.id;

	return (
		<div className="flex h-full flex-col">
			{/* Header */}
			<div className="shrink-0 flex items-start justify-between gap-x-4 p-[18px_18px_16px]">
				<div className="flex flex-col gap-y-1">
					<span className="text-foreground text-lg font-medium tracking-[-0.015em]">{name}</span>
					<span className="font-mono text-text-data text-sm">{type}</span>
					{!credential.editable && (
						<Badge variant="secondary" title={t('common.readOnlyTooltip')}>
							{t('common.readOnly')}
						</Badge>
					)}
				</div>
				<div className="flex items-center gap-x-2 shrink-0">
					<Button
						size="icon-sm"
						variant="ghost"
						className="text-text-tertiary hover:text-foreground"
						onClick={onEdit}
						disabled={!credential.editable}
						tooltip={credential.editable ? undefined : t('common.readOnlyTooltip')}
					>
						<Pen />
					</Button>
					<Button
						size="icon-sm"
						variant="ghost"
						className="text-text-tertiary hover:bg-destructive/8 hover:text-destructive"
						onClick={onDelete}
						disabled={!credential.editable}
						tooltip={credential.editable ? undefined : t('common.readOnlyTooltip')}
					>
						<Trash2 />
					</Button>
				</div>
			</div>

			<Separator className="shrink-0" />

			<div className="min-h-0 flex-1 overflow-y-auto">
				{/* Fields */}
				<div className="flex flex-col gap-y-3 p-[20px_18px_0]">
					{displayFields.map(([key, prop]) => {
						const schemaProp = prop as {
							title?: string;
							writeOnly?: boolean;
							format?: string;
						};
						const label = schemaProp.title ?? key.replace(/_/g, ' ');
						const isSecret = schemaProp.writeOnly || schemaProp.format === 'password';
						const val = credential.data[key];
						if (val === undefined || val === null) return null;
						const strVal = String(val);
						return (
							<div
								key={key}
								className="grid grid-cols-[104px_1fr] gap-x-4.5 gap-y-3 items-baseline font-mono"
							>
								<span className="text-[10px] text-text-tertiary tracking-[0.12em] uppercase">
									{label}
								</span>
								{isSecret ? (
									<MaskedValue value={strVal} />
								) : (
									<span className="text-sm text-foreground break-all">{strVal}</span>
								)}
							</div>
						);
					})}
				</div>

				{/* Available Models */}
				<Tabs
					value={tab}
					onValueChange={(v) => setTab(v as ModelTab)}
					className="gap-0 px-[18px] pb-6"
				>
					<div className="mt-[30px] mb-3 flex items-center justify-between">
						<span className="flex items-center gap-x-2 text-[13.5px] font-medium text-foreground">
							{t('credential.availableModels')}
							<span className="font-mono text-[11px] text-text-data">{total}</span>
						</span>
						{/* Only worth a switch when there is a second list to switch to. */}
						{(ttsModels.length > 0 || embeddingModels.length > 0) && (
							<TabsList className="bg-surface-muted">
								{/* Only the shadow is overridden here; the stock one
							    is shadow-sm. */}
								<TabsTrigger
									value="llm"
									className="px-2.5 text-[11.5px] text-muted-foreground group-data-[variant=default]/tabs-list:data-active:shadow-tab!"
								>
									{t('common.llm')}
									<span className="font-mono text-[10px] text-text-data">{models.length}</span>
								</TabsTrigger>
								{ttsModels.length > 0 && (
									<TabsTrigger
										value="tts"
										className="px-2.5 text-[11.5px] text-muted-foreground group-data-[variant=default]/tabs-list:data-active:shadow-tab!"
									>
										{t('common.tts')}
										<span className="font-mono text-[10px] text-text-data">{ttsModels.length}</span>
									</TabsTrigger>
								)}
								{embeddingModels.length > 0 && (
									<TabsTrigger
										value="embedding"
										className="px-2.5 text-[11.5px] text-muted-foreground group-data-[variant=default]/tabs-list:data-active:shadow-tab!"
									>
										{t('common.embedding')}
										<span className="font-mono text-[10px] text-text-data">
											{embeddingModels.length}
										</span>
									</TabsTrigger>
								)}
							</TabsList>
						)}
					</div>

					{modelsLoading ? (
						<Skeleton className="h-40 rounded-[16px]" />
					) : shown.length === 0 ? (
						<Empty className="border-none py-6">
							<EmptyHeader>
								<EmptyTitle>{t('credential.noModels')}</EmptyTitle>
								<EmptyDescription>{t('credential.noModelsDescription')}</EmptyDescription>
							</EmptyHeader>
						</Empty>
					) : (
						<>
							<TabsContent value="llm">
								<ModelTable models={models} variant="llm" />
							</TabsContent>
							<TabsContent value="tts">
								<ModelTable models={ttsModels} variant="tts" />
							</TabsContent>
							<TabsContent value="embedding">
								<ModelTable models={embeddingModels} variant="embedding" />
							</TabsContent>
						</>
					)}
				</Tabs>
			</div>
		</div>
	);
}
