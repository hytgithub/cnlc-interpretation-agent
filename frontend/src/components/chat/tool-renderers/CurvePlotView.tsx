import { useEffect, useState } from 'react';

import type { CurvePlotMetadata } from './curve-plot-data';
import { client } from '@/api/client';

export function CurvePlotView({ plot, summary }: { plot: CurvePlotMetadata; summary: string }) {
	const [image, setImage] = useState<{ url: string; source: string } | null>(null);
	const [error, setError] = useState<{ url: string; message: string } | null>(null);
	useEffect(() => {
		const controller = new AbortController();
		let disposed = false;
		let objectUrl: string | null = null;
		void client.stream(plot.url, { signal: controller.signal, silent: true }).then(async response => {
			if (response.headers.get('content-type')?.split(';')[0] !== 'image/svg+xml') {
				throw new Error('返回内容不是测井图表。');
			}
			const blob = await response.blob();
			if (disposed) return;
			objectUrl = URL.createObjectURL(blob);
			setImage({ url: plot.url, source: objectUrl });
		}).catch(reason => {
			if (!disposed) setError({ url: plot.url, message: reason instanceof Error ? reason.message : '图表读取失败。' });
		});
		return () => {
			disposed = true;
			controller.abort();
			if (objectUrl) URL.revokeObjectURL(objectUrl);
		};
	}, [plot.url]);
	const activeImage = image?.url === plot.url ? image.source : null;
	let warnings: string[] = [];
	try {
		const payload = JSON.parse(summary) as { warnings?: unknown };
		if (Array.isArray(payload.warnings)) warnings = payload.warnings.filter((w): w is string => typeof w === 'string');
	} catch { /* An incomplete summary does not prevent reading a valid chart artifact. */ }
	return (
		<figure className="my-2 rounded-md border bg-background p-3 space-y-2">
			<figcaption className="flex items-center justify-between gap-3 text-sm">
				<span>测井曲线图 · 深度 MD / m</span>
				{activeImage && <a className="underline" href={activeImage} download="well-log-curves.svg">下载 SVG</a>}
			</figcaption>
			{warnings.map((warning, i) => <p className="text-xs text-amber-700 dark:text-amber-300" key={i}>{warning}</p>)}
			{error?.url === plot.url ? <p role="alert" className="text-sm text-destructive">{error.message}</p> : activeImage ? (
				<div className="overflow-auto max-h-[800px]">
					<img src={activeImage} alt="多道测井曲线图，深度向下增加" width={plot.width} height={plot.height} style={{ maxWidth: 'none' }} />
				</div>
			) : <p className="text-sm text-muted-foreground">正在读取图表…</p>}
		</figure>
	);
}

