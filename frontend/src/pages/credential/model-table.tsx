import type { EmbeddingModelCard, ModelCard, TTSModelCard } from '@/api';
import {
	Table,
	TableBody,
	TableCell,
	TableHead,
	TableHeader,
	TableRow,
} from '@/components/ui/table';
import { useTranslation } from '@/i18n/useI18n';
import { cn } from '@/lib/utils';
import { formatNumber } from '@/utils/common.ts';

/** Which model list the detail panel is showing. */
export type ModelTab = 'llm' | 'tts' | 'embedding';

/** A row in the model table — one of the three card shapes. */
export type ModelRow = ModelCard | TTSModelCard | EmbeddingModelCard;

// ─── Model table ──────────────────────────────────────────────────────────────

/** MIME main-types that stand on their own in the ACCEPTS / OUTPUTS cells. */
const MODALITIES = new Set(['text', 'image', 'video', 'audio']);

/** Marks a model as reasoning-capable; not a real input modality. */
const THINKING_TYPE = 'application/x-thinking';

/** Dense-vector output of an embedding model. */
const EMBEDDING_TYPE = 'application/x-embedding';

/**
 * Collapse a model's MIME list into short modality labels. Anything
 * outside the four media types (PDFs, office documents, …) folds into a
 * single `file` entry so the cell stays one line.
 *
 * @param types - MIME types straight off the model card.
 * @returns De-duplicated labels in encounter order.
 */
function modalities(types: string[]): string[] {
	const out = new Set<string>();
	for (const type of types) {
		if (type === THINKING_TYPE) continue;
		if (type === EMBEDDING_TYPE) {
			out.add('vector');
			continue;
		}
		const main = type.split('/')[0];
		out.add(MODALITIES.has(main) ? main : 'file');
	}
	return [...out];
}

/** Inline pill sitting next to a model name (reasoning, realtime, status). */
export function ModelTag({ children }: { children: React.ReactNode }) {
	return (
		<span className="rounded bg-surface-muted px-1.75 py-0.5 font-mono text-[9px] tracking-[0.06em] uppercase text-text-secondary">
			{children}
		</span>
	);
}

export function HeadCell({ children }: { children: React.ReactNode }) {
	return (
		<TableHead className="h-auto bg-muted px-4 py-2.25 font-mono text-[9.5px] font-normal tracking-widest uppercase text-text-tertiary">
			{children}
		</TableHead>
	);
}

/** Numeric / modality cell — mono, one step darker than the head row. */
export function DataCell({ children, size }: { children: React.ReactNode; size: '11' | '11.5' }) {
	return (
		<TableCell
			className={cn(
				'px-4 py-2.5 font-mono text-text-secondary',
				size === '11' ? 'text-[11px]' : 'text-[11.5px]',
			)}
		>
			{children}
		</TableCell>
	);
}

export interface ModelTableProps {
	/** Rows to render; the shape must match `variant`. */
	models: ModelRow[];
	/** Drives which numeric columns sit between MODEL and ACCEPTS. */
	variant: ModelTab;
}

/**
 * The model list as a table: one row per model, sizes and modalities in
 * their own columns rather than repeated label/value pairs per card.
 *
 * @param models - Rows to render.
 * @param variant - Which column set applies.
 * @returns The bordered table plus its legend.
 */
export function ModelTable({ models, variant }: ModelTableProps) {
	const { t } = useTranslation();
	const isChat = variant === 'llm';
	const isEmbedding = variant === 'embedding';

	return (
		<div>
			<div className="overflow-x-auto rounded-[16px] border border-border">
				<Table className="min-w-[500px]">
					<TableHeader>
						<TableRow className="border-border hover:bg-transparent">
							<HeadCell>{t('credential.table.model')}</HeadCell>
							{(isChat || isEmbedding) && <HeadCell>{t('credential.table.context')}</HeadCell>}
							{isChat && <HeadCell>{t('credential.table.maxOutput')}</HeadCell>}
							{isEmbedding && <HeadCell>{t('credential.table.dimensions')}</HeadCell>}
							<HeadCell>{t('credential.table.accepts')}</HeadCell>
							<HeadCell>{t('credential.table.outputs')}</HeadCell>
						</TableRow>
					</TableHeader>
					<TableBody>
						{models.map((model) => {
							const chat = isChat ? (model as ModelCard) : null;
							const embed = isEmbedding ? (model as EmbeddingModelCard) : null;
							const tts = variant === 'tts' ? (model as TTSModelCard) : null;
							const context = chat?.context_size ?? embed?.context_size;
							return (
								<TableRow key={model.name} className="border-border hover:bg-row-hover">
									<TableCell className="px-4 py-2.5 text-[12.5px] text-foreground">
										<span className="flex items-center gap-x-2">
											<span className="min-w-0 flex-1 truncate" title={model.name}>
												{model.label || model.name}
											</span>
											{model.input_types.includes(THINKING_TYPE) && (
												<ModelTag>{t('credential.reasoning')}</ModelTag>
											)}
											{tts?.realtime && <ModelTag>{t('credential.realtime')}</ModelTag>}
											{model.status !== 'active' && <ModelTag>{model.status}</ModelTag>}
										</span>
									</TableCell>
									{(isChat || isEmbedding) && (
										<DataCell size="11.5">{context ? formatNumber(context) : '—'}</DataCell>
									)}
									{isChat && (
										<DataCell size="11.5">
											{chat?.output_size ? formatNumber(chat.output_size) : '—'}
										</DataCell>
									)}
									{isEmbedding && <DataCell size="11.5">{embed?.dimensions ?? '—'}</DataCell>}
									<DataCell size="11">{modalities(model.input_types).join(' · ') || '—'}</DataCell>
									<DataCell size="11">{modalities(model.output_types).join(' · ') || '—'}</DataCell>
								</TableRow>
							);
						})}
					</TableBody>
				</Table>
			</div>
			<p className="mt-2.5 text-[11px] text-muted-foreground">{t('credential.table.legend')}</p>
		</div>
	);
}
