import path from 'node:path';
import { fileURLToPath } from 'node:url';

import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';
import svgr from 'vite-plugin-svgr';

const frontendDir = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
	plugins: [react(), tailwindcss(), svgr()],
	server: {
		host: '127.0.0.1',
		port: 5173,
		proxy: Object.fromEntries(
			[
				'/business',
				'/health',
				'/agent',
				'/credential',
				'/sessions',
				'/chat',
				'/model',
				'/embedding-model',
				'/tts-model',
				'/skill',
				'/workspace',
				'/mcp',
				'/hub',
				'/channels',
				'/schedule',
				'/knowledge_bases',
			].map((route) => [route, 'http://127.0.0.1:8000']),
		),
	},
	build: {
		outDir: '../backend/src/cnlc_agent/static/agentscope',
		emptyOutDir: true,
	},
	resolve: {
		alias: {
			'@': path.resolve(frontendDir, './src'),
			'next/navigation': path.resolve(frontendDir, './src/lib/next-navigation-shim.ts'),
		},
	},
	optimizeDeps: {
		include: ['mime-types'],
	},
});
