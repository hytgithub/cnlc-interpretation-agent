import { Eye, EyeOff } from 'lucide-react';
import { useState } from 'react';

import { Button } from '@/components/ui/button';

// ─── Masked value ─────────────────────────────────────────────────────────────
export function MaskedValue({ value }: { value: string }) {
	const [visible, setVisible] = useState(false);
	const masked = value.length > 8 ? value.slice(0, 4) + '••••••••' + value.slice(-4) : '••••••••';
	return (
		<span className="flex items-center gap-x-1.5 font-mono text-sm">
			{visible ? value : masked}
			<Button
				size={'icon-sm'}
				className="text-text-tertiary hover:text-foreground"
				variant={'ghost'}
				onClick={() => setVisible((v) => !v)}
			>
				{visible ? <EyeOff /> : <Eye />}
			</Button>
		</span>
	);
}
