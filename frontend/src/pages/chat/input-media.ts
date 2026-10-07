import type { ContentBlock } from '@agentscope-ai/agentscope/message';

export const processChatFile: (file: File) => Promise<ContentBlock> = async (file) => {
	const filePath = (file as File & { path?: string }).path;
	if (filePath) {
		return {
			id: crypto.randomUUID(),
			type: 'data' as const,
			source: {
				type: 'url' as const,
				url: `file://${filePath}`,
				media_type: file.type || 'application/octet-stream',
			},
			name: file.name,
			created_at: new Date().toISOString(),
		};
	}
	if (file.type === 'text/plain') {
		const text = await file.text();
		return {
			id: crypto.randomUUID(),
			type: 'text' as const,
			text: `[File: ${file.name}]\n${text}`,
			created_at: new Date().toISOString(),
		};
	}
	const buffer = await file.arrayBuffer();
	const bytes = new Uint8Array(buffer);
	let binary = '';
	for (let i = 0; i < bytes.byteLength; i++) {
		binary += String.fromCharCode(bytes[i]);
	}
	const base64 = btoa(binary);
	return {
		id: crypto.randomUUID(),
		type: 'data' as const,
		source: {
			type: 'base64' as const,
			media_type: file.type || 'application/octet-stream',
			data: base64,
		},
		name: file.name,
		created_at: new Date().toISOString(),
	};
};

export function getAllowedInputTypes(types: string[]) {
	return types.filter(
		(t) =>
			/^(image|video|audio|text)\/.+/.test(t) ||
			t === 'application/pdf' ||
			t.startsWith('application/vnd.') ||
			t.startsWith('application/msword') ||
			t.startsWith('application/vnd.openxmlformats'),
	);
}
