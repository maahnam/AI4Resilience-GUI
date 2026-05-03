import { env } from '$env/dynamic/public';
import type {
	ApiResponse,
	ComparisonForm,
	DatasetForm,
	DefaultConfigPayload,
	ImplementationForm,
	TrainingForm
} from '$lib/types';

export const apiBase = (env.PUBLIC_LAHSO_API_BASE ?? '').replace(/\/$/, '');

type RequestOptions = {
	method?: 'GET' | 'POST';
	body?: unknown;
};

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
	const headers = new Headers();
	const init: RequestInit = {
		method: options.method ?? 'GET',
		credentials: 'include',
		headers
	};

	if (options.body !== undefined) {
		headers.set('content-type', 'application/json');
		init.body = JSON.stringify(options.body);
	}

	const response = await fetch(`${apiBase}${path}`, init);
	const payload = (await response.json()) as T;

	if (!response.ok) {
		const message =
			typeof payload === 'object' && payload !== null && 'error' in payload
				? String(payload.error)
				: `Request failed with status ${response.status}`;
		throw new Error(message);
	}

	return payload;
}

export const api = {
	getDefaultConfig: () => request<DefaultConfigPayload>('/api/config/default'),
	validateDataset: (payload: DatasetForm) =>
		request<ApiResponse<{ kbest_generated: boolean }>>('/api/dataset/validate', {
			method: 'POST',
			body: payload
		}),
	configureTraining: (payload: TrainingForm) =>
		request<ApiResponse<{ total_episodes: number }>>('/api/training/configure', {
			method: 'POST',
			body: payload
		}),
	startTraining: () =>
		request<ApiResponse<{ session_id: string }>>('/api/training/start', {
			method: 'POST'
		}),
	pauseTraining: () =>
		request<ApiResponse>('/api/training/pause', {
			method: 'POST'
		}),
	resumeTraining: () =>
		request<ApiResponse>('/api/training/resume', {
			method: 'POST'
		}),
	stopTraining: () =>
		request<ApiResponse>('/api/training/stop', {
			method: 'POST'
		}),
	configureImplementation: (payload: ImplementationForm) =>
		request<ApiResponse>('/api/implementation/configure', {
			method: 'POST',
			body: payload
		}),
	executeImplementation: () =>
		request<ApiResponse<{ session_id: string }>>('/api/implementation/execute', {
			method: 'POST'
		}),
	compareResults: (payload: ComparisonForm) =>
		request<ApiResponse<{ comparison_data: Record<string, unknown>[] }>>(
			'/api/comparison/compare',
			{
				method: 'POST',
				body: payload
			}
		)
};
