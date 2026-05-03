import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		proxy: {
			'/api': 'http://127.0.0.1:5001',
			'/socket.io': {
				target: 'http://127.0.0.1:5001',
				ws: true
			}
		}
	}
});
