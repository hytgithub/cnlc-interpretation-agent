import { Check, Copy } from 'lucide-react';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { useTranslation } from '@/i18n/useI18n';
import { copyToClipboard } from '@/utils/common';

/**
 * Copies the message's text to the clipboard, flipping to a check mark
 * for a moment so the click has visible feedback. Hidden until the
 * message is hovered on pointer devices; always visible on touch.
 */
export function CopyButton({ text }: { text: string }) {
	const { t } = useTranslation();
	const [copied, setCopied] = useState(false);

	const handleCopy = async () => {
		if (!(await copyToClipboard(text))) return;
		setCopied(true);
		setTimeout(() => setCopied(false), 2000);
	};

	return (
		<Button
			variant="ghost"
			size="icon-xs"
			className="text-muted-foreground md:opacity-0 group-hover/message:opacity-100 focus-visible:opacity-100"
			tooltip={t('messageBubble.copy')}
			aria-label={t('messageBubble.copy')}
			onClick={handleCopy}
		>
			{copied ? <Check /> : <Copy />}
		</Button>
	);
}
