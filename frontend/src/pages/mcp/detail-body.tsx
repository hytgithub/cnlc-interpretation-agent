import type { MCPCard } from '@/api';
import { Markdown } from '@/components/markdown';
import { useTranslation } from '@/i18n/useI18n';

/**
 * The drawer body: the server's README where a skill shows its `SKILL.md`,
 * plus what it will actually be installed as.
 *
 * The `${...}` placeholders are left in — they are resolved server-side
 * from the install form, so this is the template, never the filled-in
 * config with its secrets.
 */
export function MCPDetailBody({ card }: { card: MCPCard | null }) {
	const { t } = useTranslation();

	if (!card) return null;

	return (
		<div className="flex flex-col gap-y-6">
			<div className="flex flex-col gap-y-2">
				<span className="text-xs text-muted-foreground">{t('mcp.configLabel')}</span>
				<pre className="overflow-x-auto rounded-md bg-muted p-3 text-xs">
					{JSON.stringify(card.config_template, null, 2)}
				</pre>
			</div>
			{card.readme && <Markdown>{card.readme}</Markdown>}
		</div>
	);
}
