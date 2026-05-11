import { createContext } from 'svelte';
import type { Socket } from 'socket.io-client';
import { api, socketBase } from '$lib/api';
import type {
	ComparisonForm,
	ComparisonStep,
	DatasetForm,
	DefaultFiles,
	ImplementationForm,
	ImplementationStep,
	MainWorkflow,
	SeriesPoint,
	SimulationMetric,
	SimulationProgress,
	TrainingForm,
	TrainingMetric,
	TrainingProgress,
	TrainingStep
} from '$lib/types';

export type FeedbackTone = 'good' | 'warn' | 'error' | 'neutral';

export type NavItem = {
	id: MainWorkflow;
	href: '/training' | '/implementation' | '/comparison';
	label: string;
	description: string;
};

export const navItems: NavItem[] = [
	{
		id: 'training',
		href: '/training',
		label: 'Training Agent',
		description: 'Validate data, configure learning, and monitor training progress.'
	},
	{
		id: 'implementation',
		href: '/implementation',
		label: 'Model Implementation',
		description: 'Run trained policies against implementation simulations.'
	},
	{
		id: 'comparison',
		href: '/comparison',
		label: 'Results Comparison',
		description: 'Compare policy output files produced by simulation runs.'
	}
];

type ComparisonRow = Record<string, unknown>;

export type LahsoWorkflowState = ReturnType<typeof createLahsoWorkflowState>;

export const [useLahsoWorkflow, setLahsoWorkflow] = createContext<LahsoWorkflowState>();

export function createLahsoWorkflowState() {
	const status = $state({
		defaultFiles: null as DefaultFiles | null,
		sessionId: '',
		socketConnected: false,
		loadingConfig: true,
		feedbackMessage: 'Loading backend defaults...',
		feedbackTone: 'neutral' as FeedbackTone
	});

	const readiness = $state({
		datasetReady: false,
		trainingReady: false,
		implementationDatasetReady: false,
		implementationReady: false,
		comparisonReady: false
	});

	const run = $state({
		trainingRunning: false,
		trainingPaused: false,
		trainingEpisode: 0,
		totalEpisodes: 50000,
		simulationRunning: false
	});

	const steps = $state({
		training: 'dataset' as TrainingStep,
		implementation: 'dataset' as ImplementationStep,
		comparison: 'files' as ComparisonStep
	});

	const datasetForm = $state<DatasetForm>({
		network: null,
		network_barge: null,
		network_train: null,
		network_truck: null,
		fixed_schedule: null,
		truck_schedule: null,
		demand: null,
		mode_costs: null,
		storage_cost: 1,
		delay_penalty: 1,
		undelivered_penalty: 100,
		compute_kbest: true
	});

	const trainingForm = $state<TrainingForm>({
		service_disruptions: null,
		demand_disruptions: null,
		last_q_table: null,
		last_total_cost: null,
		last_reward: null,
		learning_rate: 0.5,
		exploratory_rate: 0.95,
		num_simulations: 50000,
		simulation_duration: 42,
		continue_training: false
	});

	const implementationForm = $state<ImplementationForm>({
		service_disruptions: null,
		demand_disruptions: null,
		q_table: null,
		policy: 'gp',
		num_simulations: 20,
		simulation_duration: 35
	});

	const comparisonForm = $state<ComparisonForm>({
		file1: null,
		file2: null,
		label1: 'Always Wait',
		label2: 'Greedy Policy'
	});

	const forms = $state({
		dataset: datasetForm,
		training: trainingForm,
		implementation: implementationForm,
		comparison: comparisonForm
	});

	const metrics = $state({
		training: [] as TrainingMetric[],
		simulation: [] as SimulationMetric[],
		comparison: [] as ComparisonRow[]
	});

	let socket: Socket | null = null;

	function mount() {
		let disposed = false;

		void loadDefaults();

		void import('socket.io-client').then(({ io }) => {
			if (disposed) return;

			const client = io(socketBase || undefined, {
				withCredentials: true,
				transports: ['websocket', 'polling']
			});

			socket = client;

			client.on('connected', (payload: { session_id: string }) => {
				status.socketConnected = true;
				syncSession(status.sessionId || payload.session_id);
			});
			client.on('disconnect', () => {
				status.socketConnected = false;
			});
			client.on('training_progress', handleTrainingProgress);
			client.on('training_complete', (payload: { message?: string }) => {
				run.trainingRunning = false;
				run.trainingPaused = false;
				setFeedback(payload.message ?? 'Training completed successfully.', 'good');
			});
			client.on('training_error', (payload: { error?: string }) => {
				run.trainingRunning = false;
				run.trainingPaused = false;
				setFeedback(payload.error ?? 'Training failed.', 'error');
			});
			client.on('simulation_progress', handleSimulationProgress);
			client.on('simulation_complete', (payload: { message?: string }) => {
				run.simulationRunning = false;
				setFeedback(payload.message ?? 'Simulation completed successfully.', 'good');
			});
			client.on('simulation_error', (payload: { error?: string }) => {
				run.simulationRunning = false;
				setFeedback(payload.error ?? 'Simulation failed.', 'error');
			});
		});

		return () => {
			disposed = true;
			socket?.disconnect();
			socket = null;
			status.socketConnected = false;
		};
	}

	async function loadDefaults() {
		status.loadingConfig = true;

		try {
			const payload = await api.getDefaultConfig();
			status.defaultFiles = payload.default_files;
			forms.dataset.storage_cost = payload.config.storage_cost;
			forms.dataset.delay_penalty = payload.config.delay_penalty;
			forms.dataset.undelivered_penalty = payload.config.undelivered_penalty;
			forms.training.learning_rate = payload.config.learning_rate;
			forms.training.exploratory_rate = payload.config.exploratory_rate;
			forms.training.num_simulations = payload.config.num_simulations;
			forms.training.simulation_duration = payload.config.simulation_duration;
			forms.implementation.num_simulations = payload.config.impl_num_simulations;
			forms.implementation.simulation_duration = payload.config.impl_duration;
			run.totalEpisodes = payload.config.num_simulations;
			setFeedback('Backend defaults loaded.', 'good');
		} catch (error) {
			setFeedback(errorMessage(error, 'Unable to load backend defaults.'), 'error');
		} finally {
			status.loadingConfig = false;
		}
	}

	async function submitDataset(event: SubmitEvent) {
		event.preventDefault();
		setFeedback('Validating dataset and path inputs...', 'neutral');

		try {
			const payload = await api.validateDataset(normalizeDatasetForm());
			if (!payload.success) {
				setFeedback(payload.error ?? 'Dataset validation failed.', 'error');
				return;
			}

			readiness.datasetReady = true;
			steps.training = 'settings';
			setFeedback(payload.message ?? 'Dataset validated.', 'good');
		} catch (error) {
			setFeedback(errorMessage(error, 'Dataset validation failed.'), 'error');
		}
	}

	async function submitImplementationDataset(event: SubmitEvent) {
		event.preventDefault();
		setFeedback('Validating implementation dataset and path inputs...', 'neutral');

		try {
			const payload = await api.validateDataset(normalizeDatasetForm());
			if (!payload.success) {
				setFeedback(payload.error ?? 'Implementation dataset validation failed.', 'error');
				return;
			}

			readiness.datasetReady = true;
			readiness.implementationDatasetReady = true;
			steps.implementation = 'settings';
			setFeedback(payload.message ?? 'Implementation dataset validated.', 'good');
		} catch (error) {
			setFeedback(errorMessage(error, 'Implementation dataset validation failed.'), 'error');
		}
	}

	async function submitTrainingSettings(event: SubmitEvent) {
		event.preventDefault();
		setFeedback('Saving training configuration...', 'neutral');

		try {
			const payload = await api.configureTraining(normalizeTrainingForm());
			if (!payload.success) {
				setFeedback(payload.error ?? 'Training configuration failed.', 'error');
				return;
			}

			readiness.trainingReady = true;
			steps.training = 'run';
			run.totalEpisodes = payload.total_episodes;
			run.trainingEpisode = 0;
			metrics.training = [];
			setFeedback(payload.message ?? 'Training configuration saved.', 'good');
			await startTraining();
		} catch (error) {
			setFeedback(errorMessage(error, 'Training configuration failed.'), 'error');
		}
	}

	async function startTraining() {
		if (!readiness.trainingReady || run.trainingRunning) return;

		setFeedback('Starting training job...', 'neutral');

		try {
			const payload = await api.startTraining();
			if (!payload.success) {
				if (payload.error === 'Training already active') {
					syncSession(payload.session_id);
					readiness.trainingReady = true;
					run.trainingRunning = true;
					run.trainingPaused = false;
					setFeedback('Training is already active. Controls are reconnected.', 'warn');
					return;
				}

				setFeedback(payload.error ?? 'Training did not start.', 'error');
				return;
			}

			syncSession(payload.session_id);
			run.trainingRunning = true;
			run.trainingPaused = false;
			setFeedback(payload.message ?? 'Training started.', 'good');
		} catch (error) {
			setFeedback(errorMessage(error, 'Training did not start.'), 'error');
		}
	}

	async function pauseTraining() {
		if (!canControlTraining() || run.trainingPaused) return;

		try {
			const payload = await api.pauseTraining();
			if (payload.success) {
				run.trainingRunning = true;
				run.trainingPaused = true;
				setFeedback(payload.message ?? 'Training paused.', 'warn');
			} else {
				setFeedback(payload.error ?? 'Training could not pause.', 'error');
			}
		} catch (error) {
			setFeedback(errorMessage(error, 'Training could not pause.'), 'error');
		}
	}

	async function resumeTraining() {
		if (!canControlTraining()) return;

		try {
			const payload = await api.resumeTraining();
			if (payload.success) {
				run.trainingRunning = true;
				run.trainingPaused = false;
				setFeedback(payload.message ?? 'Training resumed.', 'good');
			} else {
				setFeedback(payload.error ?? 'Training could not resume.', 'error');
			}
		} catch (error) {
			setFeedback(errorMessage(error, 'Training could not resume.'), 'error');
		}
	}

	async function stopTraining() {
		if (!canControlTraining()) return;

		try {
			const payload = await api.stopTraining();
			if (payload.success) {
				run.trainingRunning = false;
				run.trainingPaused = false;
				setFeedback(payload.message ?? 'Training stopped.', 'warn');
			} else {
				setFeedback(payload.error ?? 'Training could not stop.', 'error');
			}
		} catch (error) {
			setFeedback(errorMessage(error, 'Training could not stop.'), 'error');
		}
	}

	async function submitImplementationSettings(event: SubmitEvent) {
		event.preventDefault();
		setFeedback('Saving implementation configuration...', 'neutral');

		try {
			const payload = await api.configureImplementation(normalizeImplementationForm());
			if (!payload.success) {
				setFeedback(payload.error ?? 'Implementation configuration failed.', 'error');
				return;
			}

			readiness.implementationReady = true;
			steps.implementation = 'execute';
			metrics.simulation = [];
			setFeedback(payload.message ?? 'Implementation configuration saved.', 'good');
		} catch (error) {
			setFeedback(errorMessage(error, 'Implementation configuration failed.'), 'error');
		}
	}

	async function executeSimulation() {
		if (!readiness.implementationReady || run.simulationRunning) return;

		setFeedback('Starting simulation job...', 'neutral');

		try {
			const payload = await api.executeImplementation();
			if (!payload.success) {
				setFeedback(payload.error ?? 'Simulation did not start.', 'error');
				return;
			}

			syncSession(payload.session_id);
			run.simulationRunning = true;
			setFeedback(payload.message ?? 'Simulation started.', 'good');
		} catch (error) {
			setFeedback(errorMessage(error, 'Simulation did not start.'), 'error');
		}
	}

	async function submitComparison(event: SubmitEvent) {
		event.preventDefault();

		if (!forms.comparison.file1 || !forms.comparison.file2) {
			setFeedback('Choose two policy output CSV files before comparing.', 'warn');
			return;
		}

		setFeedback('Comparing output files...', 'neutral');

		try {
			const payload = await api.compareResults({
				...forms.comparison,
				file1: forms.comparison.file1,
				file2: forms.comparison.file2,
				label1: forms.comparison.label1.trim() || 'Policy 1',
				label2: forms.comparison.label2.trim() || 'Policy 2'
			});
			if (!payload.success) {
				setFeedback(payload.error ?? 'Comparison failed.', 'error');
				return;
			}

			metrics.comparison = payload.comparison_data;
			readiness.comparisonReady = true;
			steps.comparison = 'compare';
			setFeedback(payload.message ?? 'Comparison completed.', 'good');
		} catch (error) {
			setFeedback(errorMessage(error, 'Comparison failed.'), 'error');
		}
	}

	function handleTrainingProgress(payload: TrainingProgress) {
		if (status.sessionId && payload.session_id !== status.sessionId) return;

		run.trainingEpisode = payload.episode;
		run.totalEpisodes = payload.total_episodes;
		metrics.training = payload.data;
	}

	function handleSimulationProgress(payload: SimulationProgress) {
		if (status.sessionId && payload.session_id !== status.sessionId) return;

		metrics.simulation = payload.data;
	}

	function syncSession(nextSessionId?: string) {
		if (!nextSessionId) return;

		status.sessionId = nextSessionId;
		socket?.emit('join_session', { session_id: nextSessionId });
	}

	function normalizeDatasetForm(): DatasetForm {
		return {
			network: forms.dataset.network,
			network_barge: forms.dataset.network_barge,
			network_train: forms.dataset.network_train,
			network_truck: forms.dataset.network_truck,
			fixed_schedule: forms.dataset.fixed_schedule,
			truck_schedule: forms.dataset.truck_schedule,
			demand: forms.dataset.demand,
			mode_costs: forms.dataset.mode_costs,
			storage_cost: Number(forms.dataset.storage_cost),
			delay_penalty: Number(forms.dataset.delay_penalty),
			undelivered_penalty: Number(forms.dataset.undelivered_penalty),
			compute_kbest: forms.dataset.compute_kbest
		};
	}

	function normalizeTrainingForm(): TrainingForm {
		return {
			service_disruptions: forms.training.service_disruptions,
			demand_disruptions: forms.training.demand_disruptions,
			last_q_table: forms.training.last_q_table,
			last_total_cost: forms.training.last_total_cost,
			last_reward: forms.training.last_reward,
			learning_rate: Number(forms.training.learning_rate),
			exploratory_rate: Number(forms.training.exploratory_rate),
			num_simulations: Number(forms.training.num_simulations),
			simulation_duration: Number(forms.training.simulation_duration),
			continue_training: forms.training.continue_training
		};
	}

	function normalizeImplementationForm(): ImplementationForm {
		return {
			service_disruptions: forms.implementation.service_disruptions,
			demand_disruptions: forms.implementation.demand_disruptions,
			q_table: forms.implementation.q_table,
			policy: forms.implementation.policy,
			num_simulations: Number(forms.implementation.num_simulations),
			simulation_duration: Number(forms.implementation.simulation_duration)
		};
	}

	function canControlTraining() {
		return readiness.trainingReady || run.trainingRunning;
	}

	function setFeedback(message: string, tone: FeedbackTone = 'neutral') {
		status.feedbackMessage = message;
		status.feedbackTone = tone;
	}

	function errorMessage(error: unknown, fallback: string) {
		return error instanceof Error ? error.message : fallback;
	}

	return {
		status,
		readiness,
		run,
		steps,
		forms,
		metrics,
		mount,
		loadDefaults,
		submitDataset,
		submitImplementationDataset,
		submitTrainingSettings,
		startTraining,
		pauseTraining,
		resumeTraining,
		stopTraining,
		submitImplementationSettings,
		executeSimulation,
		submitComparison
	};
}

export function toSeries(
	rows: Array<Record<string, unknown>>,
	field: 'Total Cost' | 'Total Reward'
): SeriesPoint[] {
	return rows
		.map((row, index) => {
			const value = Number(row[field]);
			return {
				label: String(row.Episode ?? index + 1),
				value
			};
		})
		.filter((point) => Number.isFinite(point.value));
}
