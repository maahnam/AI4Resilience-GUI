import type {
	ApiResponse,
	ComparisonForm,
	ComparisonRow,
	DatasetForm,
	DefaultConfigPayload,
	ImplementationForm,
	SessionStatusPayload,
	TrainingForm
} from '$lib/types';

type PublicImportMetaEnv = ImportMeta & {
	env: Record<string, string | boolean | undefined>;
};

const publicEnv = (import.meta as PublicImportMetaEnv).env;

function envString(value: string | boolean | undefined): string {
	return typeof value === 'string' ? value : '';
}

function trimTrailingSlash(value: string): string {
	return value.replace(/\/$/, '');
}

export const apiBase = trimTrailingSlash(envString(publicEnv.PUBLIC_LAHSO_API_BASE));
export const socketBase = trimTrailingSlash(
	envString(publicEnv.PUBLIC_LAHSO_SOCKET_BASE) || apiBase
);

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
		if (typeof FormData !== 'undefined' && options.body instanceof FormData) {
			init.body = options.body;
		} else {
			headers.set('content-type', 'application/json');
			init.body = JSON.stringify(options.body);
		}
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
	getSessionStatus: () => request<SessionStatusPayload>('/api/session/status'),
	validateDataset: (payload: DatasetForm) =>
		request<ApiResponse<{ kbest_generated: boolean }>>('/api/dataset/validate', {
			method: 'POST',
			body: datasetFormData(payload)
		}),
	configureTraining: (payload: TrainingForm) =>
		request<ApiResponse<{ total_episodes: number }>>('/api/training/configure', {
			method: 'POST',
			body: trainingFormData(payload)
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
			body: implementationFormData(payload)
		}),
	executeImplementation: () =>
		request<ApiResponse<{ session_id: string }>>('/api/implementation/execute', {
			method: 'POST'
		}),
	compareResults: (payload: ComparisonForm) => {
		const formData = new FormData();
		if (payload.file1) formData.append('file1', payload.file1);
		if (payload.file2) formData.append('file2', payload.file2);
		formData.append('label1', payload.label1);
		formData.append('label2', payload.label2);

		return request<ApiResponse<{ comparison_data: ComparisonRow[] }>>(
			'/api/comparison/compare',
			{
				method: 'POST',
				body: formData
			}
		);
	}
};

function datasetFormData(payload: DatasetForm) {
	const formData = new FormData();
	appendOptionalFile(formData, 'network', payload.network);
	appendOptionalFile(formData, 'network_barge', payload.network_barge);
	appendOptionalFile(formData, 'network_train', payload.network_train);
	appendOptionalFile(formData, 'network_truck', payload.network_truck);
	appendOptionalFile(formData, 'fixed_schedule', payload.fixed_schedule);
	appendOptionalFile(formData, 'truck_schedule', payload.truck_schedule);
	appendOptionalFile(formData, 'demand', payload.demand);
	appendOptionalFile(formData, 'mode_costs', payload.mode_costs);
	formData.append('storage_cost', String(payload.storage_cost));
	formData.append('delay_penalty', String(payload.delay_penalty));
	formData.append('undelivered_penalty', String(payload.undelivered_penalty));
	formData.append('compute_kbest', String(payload.compute_kbest));
	return formData;
}

function trainingFormData(payload: TrainingForm) {
	const formData = new FormData();
	appendOptionalFile(formData, 'service_disruptions', payload.service_disruptions);
	appendOptionalFile(formData, 'demand_disruptions', payload.demand_disruptions);
	if (payload.continue_training) {
		appendOptionalFile(formData, 'last_q_table', payload.last_q_table);
		appendOptionalFile(formData, 'last_total_cost', payload.last_total_cost);
		appendOptionalFile(formData, 'last_reward', payload.last_reward);
	}
	formData.append('learning_rate', String(payload.learning_rate));
	formData.append('exploratory_rate', String(payload.exploratory_rate));
	formData.append('num_simulations', String(payload.num_simulations));
	formData.append('simulation_duration', String(payload.simulation_duration));
	formData.append('continue_training', String(payload.continue_training));
	return formData;
}

function implementationFormData(payload: ImplementationForm) {
	const formData = new FormData();
	appendOptionalFile(formData, 'service_disruptions', payload.service_disruptions);
	appendOptionalFile(formData, 'demand_disruptions', payload.demand_disruptions);
	appendOptionalFile(formData, 'q_table', payload.q_table);
	formData.append('policy', payload.policy);
	formData.append('num_simulations', String(payload.num_simulations));
	formData.append('simulation_duration', String(payload.simulation_duration));
	return formData;
}

function appendOptionalFile(formData: FormData, fieldName: string, file: File | null) {
	if (file) {
		formData.append(fieldName, file);
	}
}
