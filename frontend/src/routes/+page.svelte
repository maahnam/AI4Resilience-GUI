<script lang="ts">
	import { onMount } from 'svelte';
	import type { Socket } from 'socket.io-client';
	import {
		Activity,
		BarChart3,
		BrainCircuit,
		CheckCircle2,
		Pause,
		Play,
		RefreshCw,
		Server,
		SlidersHorizontal,
		Square
	} from 'lucide-svelte';
	import { api, apiBase } from '$lib/api';
	import DragDropFileInput from '$lib/components/DragDropFileInput.svelte';
	import MetricCard from '$lib/components/MetricCard.svelte';
	import SeriesChart from '$lib/components/SeriesChart.svelte';
	import type {
		ComparisonForm,
		ComparisonStep,
		DefaultFiles,
		DatasetForm,
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

	type FeedbackTone = 'good' | 'warn' | 'error' | 'neutral';
	type NavItem = {
		id: MainWorkflow;
		label: string;
		description: string;
	};

	const navItems: NavItem[] = [
		{
			id: 'training',
			label: 'Training Agent',
			description: 'Validate data, configure learning, and monitor training progress.'
		},
		{
			id: 'implementation',
			label: 'Model Implementation',
			description: 'Run trained policies against implementation simulations.'
		},
		{
			id: 'comparison',
			label: 'Results Comparison',
			description: 'Compare policy output files produced by simulation runs.'
		}
	];

	let mainTab: MainWorkflow = $state('training');
	let trainingStep: TrainingStep = $state('dataset');
	let implementationStep: ImplementationStep = $state('dataset');
	let comparisonStep: ComparisonStep = $state('files');

	let defaultFiles: DefaultFiles | null = $state(null);
	let sessionId = $state('');
	let socketConnected = $state(false);
	let socket: Socket | null = $state(null);

	let datasetReady = $state(false);
	let trainingReady = $state(false);
	let implementationDatasetReady = $state(false);
	let implementationReady = $state(false);
	let comparisonReady = $state(false);

	let trainingRunning = $state(false);
	let trainingPaused = $state(false);
	let trainingEpisode = $state(0);
	let totalEpisodes = $state(50000);
	let simulationRunning = $state(false);

	let trainingMetrics: TrainingMetric[] = $state([]);
	let simulationMetrics: SimulationMetric[] = $state([]);
	let comparisonRows: Record<string, unknown>[] = $state([]);

	let loadingConfig = $state(true);
	let feedbackMessage = $state('Loading backend defaults...');
	let feedbackTone: FeedbackTone = $state('neutral');

	let datasetForm: DatasetForm = $state({
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

	let trainingForm: TrainingForm = $state({
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

	let implementationForm: ImplementationForm = $state({
		service_disruptions: null,
		demand_disruptions: null,
		q_table: null,
		policy: 'gp',
		num_simulations: 20,
		simulation_duration: 35
	});

	let comparisonForm: ComparisonForm = $state({
		file1: null,
		file2: null,
		label1: 'Always Wait',
		label2: 'Greedy Policy'
	});

	const activeNav = $derived(navItems.find((item) => item.id === mainTab) ?? navItems[0]);
	const trainingCostSeries = $derived(toSeries(trainingMetrics, 'Total Cost'));
	const trainingRewardSeries = $derived(toSeries(trainingMetrics, 'Total Reward'));
	const simulationCostSeries = $derived(toSeries(simulationMetrics, 'Total Cost'));
	const trainingProgress = $derived(
		totalEpisodes > 0 ? Math.min(100, Math.round((trainingEpisode / totalEpisodes) * 100)) : 0
	);
	const comparisonPreviewRows = $derived(comparisonRows.slice(0, 10));
	const canControlTraining = $derived(trainingReady || trainingRunning);

	onMount(() => {
		let disposed = false;

		void loadDefaults();

		void import('socket.io-client').then(({ io }) => {
			if (disposed) return;

			const client = io(apiBase || undefined, {
				withCredentials: true,
				transports: ['websocket', 'polling']
			});

			socket = client;

			client.on('connected', (payload: { session_id: string }) => {
				socketConnected = true;
				syncSession(sessionId || payload.session_id);
			});
			client.on('disconnect', () => {
				socketConnected = false;
			});
			client.on('training_progress', handleTrainingProgress);
			client.on('training_complete', (payload: { message?: string }) => {
				trainingRunning = false;
				trainingPaused = false;
				setFeedback(payload.message ?? 'Training completed successfully.', 'good');
			});
			client.on('training_error', (payload: { error?: string }) => {
				trainingRunning = false;
				trainingPaused = false;
				setFeedback(payload.error ?? 'Training failed.', 'error');
			});
			client.on('simulation_progress', handleSimulationProgress);
			client.on('simulation_complete', (payload: { message?: string }) => {
				simulationRunning = false;
				setFeedback(payload.message ?? 'Simulation completed successfully.', 'good');
			});
			client.on('simulation_error', (payload: { error?: string }) => {
				simulationRunning = false;
				setFeedback(payload.error ?? 'Simulation failed.', 'error');
			});
		});

		return () => {
			disposed = true;
			socket?.disconnect();
		};
	});

	async function loadDefaults() {
		loadingConfig = true;
		try {
			const payload = await api.getDefaultConfig();
			defaultFiles = payload.default_files;
			datasetForm.storage_cost = payload.config.storage_cost;
			datasetForm.delay_penalty = payload.config.delay_penalty;
			datasetForm.undelivered_penalty = payload.config.undelivered_penalty;
			trainingForm.learning_rate = payload.config.learning_rate;
			trainingForm.exploratory_rate = payload.config.exploratory_rate;
			trainingForm.num_simulations = payload.config.num_simulations;
			trainingForm.simulation_duration = payload.config.simulation_duration;
			implementationForm.num_simulations = payload.config.impl_num_simulations;
			implementationForm.simulation_duration = payload.config.impl_duration;
			totalEpisodes = payload.config.num_simulations;
			setFeedback('Backend defaults loaded.', 'good');
		} catch (error) {
			setFeedback(errorMessage(error, 'Unable to load backend defaults.'), 'error');
		} finally {
			loadingConfig = false;
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
			datasetReady = true;
			trainingStep = 'settings';
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
			datasetReady = true;
			implementationDatasetReady = true;
			implementationStep = 'settings';
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
			trainingReady = true;
			trainingStep = 'run';
			totalEpisodes = payload.total_episodes;
			trainingEpisode = 0;
			trainingMetrics = [];
			setFeedback(payload.message ?? 'Training configuration saved.', 'good');
			await startTraining();
		} catch (error) {
			setFeedback(errorMessage(error, 'Training configuration failed.'), 'error');
		}
	}

	async function startTraining() {
		if (!trainingReady || trainingRunning) return;

		setFeedback('Starting training job...', 'neutral');
		try {
			const payload = await api.startTraining();
			if (!payload.success) {
				if (payload.error === 'Training already active') {
					syncSession(payload.session_id);
					trainingReady = true;
					trainingRunning = true;
					trainingPaused = false;
					setFeedback('Training is already active. Controls are reconnected.', 'warn');
					return;
				}
				setFeedback(payload.error ?? 'Training did not start.', 'error');
				return;
			}
			syncSession(payload.session_id);
			trainingRunning = true;
			trainingPaused = false;
			setFeedback(payload.message ?? 'Training started.', 'good');
		} catch (error) {
			setFeedback(errorMessage(error, 'Training did not start.'), 'error');
		}
	}

	async function pauseTraining() {
		if (!canControlTraining || trainingPaused) return;

		const payload = await api.pauseTraining();
		if (payload.success) {
			trainingRunning = true;
			trainingPaused = true;
			setFeedback(payload.message ?? 'Training paused.', 'warn');
		} else {
			setFeedback(payload.error ?? 'Training could not pause.', 'error');
		}
	}

	async function resumeTraining() {
		if (!canControlTraining) return;

		const payload = await api.resumeTraining();
		if (payload.success) {
			trainingRunning = true;
			trainingPaused = false;
			setFeedback(payload.message ?? 'Training resumed.', 'good');
		} else {
			setFeedback(payload.error ?? 'Training could not resume.', 'error');
		}
	}

	async function stopTraining() {
		if (!canControlTraining) return;

		const payload = await api.stopTraining();
		if (payload.success) {
			trainingRunning = false;
			trainingPaused = false;
			setFeedback(payload.message ?? 'Training stopped.', 'warn');
		} else {
			setFeedback(payload.error ?? 'Training could not stop.', 'error');
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
			implementationReady = true;
			implementationStep = 'execute';
			simulationMetrics = [];
			setFeedback(payload.message ?? 'Implementation configuration saved.', 'good');
		} catch (error) {
			setFeedback(errorMessage(error, 'Implementation configuration failed.'), 'error');
		}
	}

	async function executeSimulation() {
		if (!implementationReady || simulationRunning) return;

		setFeedback('Starting simulation job...', 'neutral');
		try {
			const payload = await api.executeImplementation();
			if (!payload.success) {
				setFeedback(payload.error ?? 'Simulation did not start.', 'error');
				return;
			}
			syncSession(payload.session_id);
			simulationRunning = true;
			setFeedback(payload.message ?? 'Simulation started.', 'good');
		} catch (error) {
			setFeedback(errorMessage(error, 'Simulation did not start.'), 'error');
		}
	}

	async function submitComparison(event: SubmitEvent) {
		event.preventDefault();

		if (!comparisonForm.file1 || !comparisonForm.file2) {
			setFeedback('Choose two policy output CSV files before comparing.', 'warn');
			return;
		}

		setFeedback('Comparing output files...', 'neutral');
		try {
			const payload = await api.compareResults({
				...comparisonForm,
				file1: comparisonForm.file1,
				file2: comparisonForm.file2,
				label1: comparisonForm.label1.trim() || 'Policy 1',
				label2: comparisonForm.label2.trim() || 'Policy 2'
			});
			if (!payload.success) {
				setFeedback(payload.error ?? 'Comparison failed.', 'error');
				return;
			}
			comparisonRows = payload.comparison_data;
			comparisonReady = true;
			comparisonStep = 'compare';
			setFeedback(payload.message ?? 'Comparison completed.', 'good');
		} catch (error) {
			setFeedback(errorMessage(error, 'Comparison failed.'), 'error');
		}
	}

	function handleTrainingProgress(payload: TrainingProgress) {
		if (sessionId && payload.session_id !== sessionId) return;

		trainingEpisode = payload.episode;
		totalEpisodes = payload.total_episodes;
		trainingMetrics = payload.data;
	}

	function handleSimulationProgress(payload: SimulationProgress) {
		if (sessionId && payload.session_id !== sessionId) return;

		simulationMetrics = payload.data;
	}

	function syncSession(nextSessionId?: string) {
		if (!nextSessionId) return;

		sessionId = nextSessionId;
		socket?.emit('join_session', { session_id: nextSessionId });
	}

	function normalizeDatasetForm(): DatasetForm {
		return {
			network: datasetForm.network,
			network_barge: datasetForm.network_barge,
			network_train: datasetForm.network_train,
			network_truck: datasetForm.network_truck,
			fixed_schedule: datasetForm.fixed_schedule,
			truck_schedule: datasetForm.truck_schedule,
			demand: datasetForm.demand,
			mode_costs: datasetForm.mode_costs,
			storage_cost: Number(datasetForm.storage_cost),
			delay_penalty: Number(datasetForm.delay_penalty),
			undelivered_penalty: Number(datasetForm.undelivered_penalty),
			compute_kbest: datasetForm.compute_kbest
		};
	}

	function normalizeTrainingForm(): TrainingForm {
		return {
			service_disruptions: trainingForm.service_disruptions,
			demand_disruptions: trainingForm.demand_disruptions,
			last_q_table: trainingForm.last_q_table,
			last_total_cost: trainingForm.last_total_cost,
			last_reward: trainingForm.last_reward,
			learning_rate: Number(trainingForm.learning_rate),
			exploratory_rate: Number(trainingForm.exploratory_rate),
			num_simulations: Number(trainingForm.num_simulations),
			simulation_duration: Number(trainingForm.simulation_duration),
			continue_training: trainingForm.continue_training
		};
	}

	function normalizeImplementationForm(): ImplementationForm {
		return {
			service_disruptions: implementationForm.service_disruptions,
			demand_disruptions: implementationForm.demand_disruptions,
			q_table: implementationForm.q_table,
			policy: implementationForm.policy,
			num_simulations: Number(implementationForm.num_simulations),
			simulation_duration: Number(implementationForm.simulation_duration)
		};
	}

	function toSeries(rows: Array<Record<string, unknown>>, field: 'Total Cost' | 'Total Reward'): SeriesPoint[] {
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

	function setFeedback(message: string, tone: FeedbackTone = 'neutral') {
		feedbackMessage = message;
		feedbackTone = tone;
	}

	function errorMessage(error: unknown, fallback: string) {
		return error instanceof Error ? error.message : fallback;
	}

</script>

<svelte:head>
	<title>LAHSO - Learning Assisted Hybrid Simulation-Optimization</title>
	<meta
		name="description"
		content="LAHSO web frontend for dataset validation, training, implementation, and comparison workflows"
	/>
</svelte:head>

<div class="app-shell">
	<aside class="sidebar">
		<div class="brand">
			<div class="brand-mark">L</div>
			<div>
				<strong>LAHSO</strong>
				<span>Hybrid simulation optimization</span>
			</div>
		</div>

		<nav class="nav-stack" aria-label="Workflow">
			{#each navItems as item (item.id)}
				<button
					type="button"
					class={`nav-button ${mainTab === item.id ? 'active' : ''}`}
					aria-current={mainTab === item.id ? 'page' : undefined}
					onclick={() => (mainTab = item.id)}
				>
					{#if item.id === 'training'}
						<BrainCircuit size={18} />
					{:else if item.id === 'implementation'}
						<Server size={18} />
					{:else}
						<BarChart3 size={18} />
					{/if}
					<span>{item.label}</span>
				</button>
			{/each}
		</nav>

		<div class="sidebar-note">
			Gradio remains available for the full research/operator workflow while this frontend moves the
			Flask UI toward a product API client.
		</div>
	</aside>

	<main class="main-panel">
		<header class="topbar">
			<div>
				<h1>{activeNav.label}</h1>
				<p>{activeNav.description}</p>
			</div>

			<div class="status-pill">
				<span class={`status-dot ${socketConnected ? 'connected' : ''}`}></span>
				<span>{socketConnected ? 'Live session' : 'Connecting'}</span>
			</div>
		</header>

		<div class="workspace-grid">
			<section class="work-surface">
				{#if mainTab === 'training'}
					<div class="step-tabs" aria-label="Training steps">
						<button
							type="button"
							class={`step-tab ${trainingStep === 'dataset' ? 'active' : ''}`}
							onclick={() => (trainingStep = 'dataset')}
						>
							Dataset Input
						</button>
						<button
							type="button"
							class={`step-tab ${trainingStep === 'settings' ? 'active' : ''}`}
							disabled={!datasetReady}
							onclick={() => (trainingStep = 'settings')}
						>
							Simulation Settings
						</button>
						<button
							type="button"
							class={`step-tab ${trainingStep === 'run' ? 'active' : ''}`}
							disabled={!trainingReady}
							onclick={() => (trainingStep = 'run')}
						>
							Training
						</button>
					</div>

					{#if trainingStep === 'dataset'}
						<form class="panel-grid" onsubmit={submitDataset}>
							<div class="field-panel">
								<h2>Network and Demand Files</h2>
								<DragDropFileInput
									id="dataset-network"
									label="Intermodal Network"
									helper={defaultFiles ? `Default: ${defaultFiles.network}` : 'CSV input'}
									bind:file={datasetForm.network}
								/>
								<DragDropFileInput
									id="dataset-network-barge"
									label="Barge Network"
									helper={defaultFiles ? `Default: ${defaultFiles.network_barge}` : 'CSV input'}
									bind:file={datasetForm.network_barge}
								/>
								<DragDropFileInput
									id="dataset-network-train"
									label="Train Network"
									helper={defaultFiles ? `Default: ${defaultFiles.network_train}` : 'CSV input'}
									bind:file={datasetForm.network_train}
								/>
								<DragDropFileInput
									id="dataset-network-truck"
									label="Truck Network"
									helper={defaultFiles ? `Default: ${defaultFiles.network_truck}` : 'CSV input'}
									bind:file={datasetForm.network_truck}
								/>
							</div>

							<div class="field-panel">
								<h2>Schedules, Demand, and Costs</h2>
								<DragDropFileInput
									id="dataset-fixed-schedule"
									label="Fixed Schedule"
									helper={defaultFiles ? `Default: ${defaultFiles.fixed_schedule}` : 'CSV input'}
									bind:file={datasetForm.fixed_schedule}
								/>
								<DragDropFileInput
									id="dataset-truck-schedule"
									label="Truck Schedule"
									helper={defaultFiles ? `Default: ${defaultFiles.truck_schedule}` : 'CSV input'}
									bind:file={datasetForm.truck_schedule}
								/>
								<DragDropFileInput
									id="dataset-demand"
									label="Demand"
									helper={defaultFiles ? `Default: ${defaultFiles.demand}` : 'CSV input'}
									bind:file={datasetForm.demand}
								/>
								<DragDropFileInput
									id="dataset-mode-costs"
									label="Mode Costs"
									helper={defaultFiles ? `Default: ${defaultFiles.mode_costs}` : 'CSV input'}
									bind:file={datasetForm.mode_costs}
								/>
								<h2>Cost Parameters</h2>
								<label class="form-field">
									<span>Storage Cost</span>
									<input type="number" min="0" bind:value={datasetForm.storage_cost} />
									<span class="hint">Euro per container hour</span>
								</label>
								<label class="form-field">
									<span>Delay Penalty</span>
									<input type="number" min="0" bind:value={datasetForm.delay_penalty} />
									<span class="hint">Euro per container hour</span>
								</label>
								<label class="form-field">
									<span>Undelivered Penalty</span>
									<input type="number" min="0" bind:value={datasetForm.undelivered_penalty} />
									<span class="hint">Euro per container</span>
								</label>
								<label class="check-row">
									<input type="checkbox" bind:checked={datasetForm.compute_kbest} />
									<span>Compute K-best solution set</span>
								</label>
								<div class="action-row">
									<button class="primary-button" type="submit" disabled={loadingConfig}>
										<CheckCircle2 size={18} />
										Validate Dataset
									</button>
									<button class="ghost-button" type="button" onclick={loadDefaults}>
										<RefreshCw size={17} />
										Reload Defaults
									</button>
								</div>
							</div>
						</form>
					{:else if trainingStep === 'settings'}
						<form class="panel-grid" onsubmit={submitTrainingSettings}>
							<div class="field-panel">
								<h2>Disruption Inputs</h2>
								<DragDropFileInput
									id="training-service-disruptions"
									label="Service Disruptions"
									helper={defaultFiles ? `Default: ${defaultFiles.service_disruptions}` : 'CSV input'}
									bind:file={trainingForm.service_disruptions}
								/>
								<DragDropFileInput
									id="training-demand-disruptions"
									label="Demand Disruptions"
									helper={defaultFiles ? `Default: ${defaultFiles.demand_disruptions}` : 'CSV input'}
									bind:file={trainingForm.demand_disruptions}
								/>
								{#if trainingForm.continue_training}
									<DragDropFileInput
										id="training-last-q-table"
										label="Last Q-Table"
										accept=".pkl"
										helper={defaultFiles ? `Default: ${defaultFiles.q_table}` : 'PKL input'}
										bind:file={trainingForm.last_q_table}
									/>
									<DragDropFileInput
										id="training-last-total-cost"
										label="Last Total Cost"
										accept=".pkl"
										helper="Previous total-cost metric pickle"
										bind:file={trainingForm.last_total_cost}
									/>
									<DragDropFileInput
										id="training-last-reward"
										label="Last Reward"
										accept=".pkl"
										helper="Previous reward metric pickle"
										bind:file={trainingForm.last_reward}
									/>
								{/if}
							</div>

							<div class="field-panel">
								<h2>Learning and Simulation</h2>
								<label class="form-field">
									<span>Learning Rate</span>
									<input
										type="number"
										min="0"
										max="1"
										step="0.01"
										bind:value={trainingForm.learning_rate}
									/>
								</label>
								<label class="form-field">
									<span>Exploratory Rate</span>
									<input
										type="number"
										min="0"
										max="1"
										step="0.01"
										bind:value={trainingForm.exploratory_rate}
									/>
								</label>
								<label class="form-field">
									<span>Number of Simulations</span>
									<input type="number" min="1" bind:value={trainingForm.num_simulations} />
								</label>
								<label class="form-field">
									<span>Simulation Duration</span>
									<input type="number" min="1" bind:value={trainingForm.simulation_duration} />
									<span class="hint">Days per simulation</span>
								</label>
								<label class="check-row">
									<input type="checkbox" bind:checked={trainingForm.continue_training} />
									<span>Continue previous training</span>
								</label>
								<div class="action-row">
									<button class="primary-button" type="submit">
										<SlidersHorizontal size={18} />
										Save Configuration
									</button>
								</div>
							</div>
						</form>
					{:else}
						<div class="run-panel">
							<div class="metric-grid">
								<MetricCard label="Episode" value={`${trainingEpisode} / ${totalEpisodes}`} tone="green" />
								<MetricCard label="Progress" value={`${trainingProgress}%`} tone="blue" />
								<MetricCard
									label="State"
									value={trainingPaused ? 'Paused' : trainingRunning ? 'Running' : 'Ready'}
									tone="amber"
								/>
							</div>

							<div class="control-row">
								<button
									class="primary-button"
									type="button"
									disabled={!trainingReady || trainingRunning}
									onclick={startTraining}
								>
									<Play size={18} />
									Start
								</button>
								<button
									class="icon-button"
									type="button"
									aria-label="Pause training"
									disabled={!canControlTraining || trainingPaused}
									onclick={pauseTraining}
								>
									<Pause size={18} />
								</button>
								<button
									class="icon-button"
									type="button"
									aria-label="Resume training"
									disabled={!canControlTraining}
									onclick={resumeTraining}
								>
									<Play size={18} />
								</button>
								<button
									class="icon-button"
									type="button"
									aria-label="Stop training"
									disabled={!canControlTraining}
									onclick={stopTraining}
								>
									<Square size={17} />
								</button>
							</div>

							<div class="chart-grid">
								<SeriesChart
									title="Average Total Cost"
									points={trainingCostSeries}
									tone="green"
									xAxisLabel="Episode"
									yAxisLabel="Total Cost"
									emptyLabel={trainingRunning ? 'Training is running' : 'Waiting for data'}
								/>
								<SeriesChart
									title="Average Reward"
									points={trainingRewardSeries}
									tone="green"
									xAxisLabel="Episode"
									yAxisLabel="Total Reward"
									emptyLabel={trainingRunning ? 'Training is running' : 'Waiting for data'}
								/>
							</div>
						</div>
					{/if}
				{:else if mainTab === 'implementation'}
					<div class="step-tabs" aria-label="Implementation steps">
						<button
							type="button"
							class={`step-tab ${implementationStep === 'dataset' ? 'active' : ''}`}
							onclick={() => (implementationStep = 'dataset')}
						>
							Dataset Input
						</button>
						<button
							type="button"
							class={`step-tab ${implementationStep === 'settings' ? 'active' : ''}`}
							disabled={!implementationDatasetReady}
							onclick={() => (implementationStep = 'settings')}
						>
							Simulation Settings
						</button>
						<button
							type="button"
							class={`step-tab ${implementationStep === 'execute' ? 'active' : ''}`}
							disabled={!implementationReady}
							onclick={() => (implementationStep = 'execute')}
						>
							Execute Simulation
						</button>
					</div>

					{#if implementationStep === 'dataset'}
						<form class="panel-grid" onsubmit={submitImplementationDataset}>
							<div class="field-panel">
								<h2>Network and Demand Files</h2>
								<DragDropFileInput
									id="implementation-dataset-network"
									label="Intermodal Network"
									helper={defaultFiles ? `Default: ${defaultFiles.network}` : 'CSV input'}
									bind:file={datasetForm.network}
								/>
								<DragDropFileInput
									id="implementation-dataset-network-barge"
									label="Barge Network"
									helper={defaultFiles ? `Default: ${defaultFiles.network_barge}` : 'CSV input'}
									bind:file={datasetForm.network_barge}
								/>
								<DragDropFileInput
									id="implementation-dataset-network-train"
									label="Train Network"
									helper={defaultFiles ? `Default: ${defaultFiles.network_train}` : 'CSV input'}
									bind:file={datasetForm.network_train}
								/>
								<DragDropFileInput
									id="implementation-dataset-network-truck"
									label="Truck Network"
									helper={defaultFiles ? `Default: ${defaultFiles.network_truck}` : 'CSV input'}
									bind:file={datasetForm.network_truck}
								/>
							</div>

							<div class="field-panel">
								<h2>Schedules, Demand, and Costs</h2>
								<DragDropFileInput
									id="implementation-dataset-fixed-schedule"
									label="Fixed Schedule"
									helper={defaultFiles ? `Default: ${defaultFiles.fixed_schedule}` : 'CSV input'}
									bind:file={datasetForm.fixed_schedule}
								/>
								<DragDropFileInput
									id="implementation-dataset-truck-schedule"
									label="Truck Schedule"
									helper={defaultFiles ? `Default: ${defaultFiles.truck_schedule}` : 'CSV input'}
									bind:file={datasetForm.truck_schedule}
								/>
								<DragDropFileInput
									id="implementation-dataset-demand"
									label="Demand"
									helper={defaultFiles ? `Default: ${defaultFiles.demand}` : 'CSV input'}
									bind:file={datasetForm.demand}
								/>
								<DragDropFileInput
									id="implementation-dataset-mode-costs"
									label="Mode Costs"
									helper={defaultFiles ? `Default: ${defaultFiles.mode_costs}` : 'CSV input'}
									bind:file={datasetForm.mode_costs}
								/>
								<h2>Cost Parameters</h2>
								<label class="form-field">
									<span>Storage Cost</span>
									<input type="number" min="0" bind:value={datasetForm.storage_cost} />
									<span class="hint">Euro per container hour</span>
								</label>
								<label class="form-field">
									<span>Delay Penalty</span>
									<input type="number" min="0" bind:value={datasetForm.delay_penalty} />
									<span class="hint">Euro per container hour</span>
								</label>
								<label class="form-field">
									<span>Undelivered Penalty</span>
									<input type="number" min="0" bind:value={datasetForm.undelivered_penalty} />
									<span class="hint">Euro per container</span>
								</label>
								<label class="check-row">
									<input type="checkbox" bind:checked={datasetForm.compute_kbest} />
									<span>Compute K-best solution set</span>
								</label>
								<div class="action-row">
									<button class="primary-button" type="submit" disabled={loadingConfig}>
										<CheckCircle2 size={18} />
										Validate Dataset
									</button>
									<button class="ghost-button" type="button" onclick={loadDefaults}>
										<RefreshCw size={17} />
										Reload Defaults
									</button>
								</div>
							</div>
						</form>
					{:else if implementationStep === 'settings'}
						<form class="panel-grid" onsubmit={submitImplementationSettings}>
							<div class="field-panel">
								<h2>Disruption and Model Inputs</h2>
								<DragDropFileInput
									id="implementation-service-disruptions"
									label="Service Disruptions"
									helper="Default: data/raw/disruptions/No_Service_Disruption_Profile.csv"
									bind:file={implementationForm.service_disruptions}
								/>
								<DragDropFileInput
									id="implementation-demand-disruptions"
									label="Demand Disruptions"
									helper="Default: data/raw/disruptions/No_Request_Disruption_Profile.csv"
									bind:file={implementationForm.demand_disruptions}
								/>
								<DragDropFileInput
									id="implementation-q-table"
									label="Q-Table"
									accept=".pkl"
									helper={defaultFiles ? `Default: ${defaultFiles.q_table}` : 'PKL input'}
									bind:file={implementationForm.q_table}
								/>
							</div>
							<div class="field-panel">
								<h2>Policy</h2>
								<div class="segment-control" aria-label="Policy">
									<button
										type="button"
										class={`segment-button ${implementationForm.policy === 'gp' ? 'active' : ''}`}
										onclick={() => (implementationForm.policy = 'gp')}
									>
										Greedy
									</button>
									<button
										type="button"
										class={`segment-button ${implementationForm.policy === 'aw' ? 'active' : ''}`}
										onclick={() => (implementationForm.policy = 'aw')}
									>
										Always Wait
									</button>
									<button
										type="button"
										class={`segment-button ${implementationForm.policy === 'ar' ? 'active' : ''}`}
										onclick={() => (implementationForm.policy = 'ar')}
									>
										Always Reassign
									</button>
								</div>
								<h2>Simulation</h2>
								<label class="form-field">
									<span>Number of Simulations</span>
									<input type="number" min="1" bind:value={implementationForm.num_simulations} />
								</label>
								<label class="form-field">
									<span>Duration per Episode</span>
									<input type="number" min="1" bind:value={implementationForm.simulation_duration} />
									<span class="hint">Days per episode</span>
								</label>
								<div class="action-row">
									<button class="primary-button" type="submit">
										<SlidersHorizontal size={18} />
										Save Configuration
									</button>
								</div>
							</div>
						</form>
					{:else}
						<div class="run-panel">
							<div class="metric-grid">
								<MetricCard label="Policy" value={implementationForm.policy.toUpperCase()} tone="blue" />
								<MetricCard
									label="Episodes"
									value={implementationForm.num_simulations}
									tone="green"
								/>
								<MetricCard
									label="State"
									value={simulationRunning ? 'Running' : 'Ready'}
									tone="amber"
								/>
							</div>
							<div class="action-row">
								<button
									class="primary-button"
									type="button"
									disabled={!implementationReady || simulationRunning}
									onclick={executeSimulation}
								>
									<Activity size={18} />
									Execute Simulation
								</button>
							</div>
							<SeriesChart
								title="Total Cost per Simulation Episode"
								points={simulationCostSeries}
								tone="green"
								xAxisLabel="Episode"
								yAxisLabel="Total Cost"
								emptyLabel={simulationRunning ? 'Simulation is running' : 'Waiting for data'}
							/>
						</div>
					{/if}
				{:else}
					<div class="step-tabs" aria-label="Comparison steps">
						<button
							type="button"
							class={`step-tab ${comparisonStep === 'files' ? 'active' : ''}`}
							onclick={() => (comparisonStep = 'files')}
						>
							Dataset Input
						</button>
						<button
							type="button"
							class={`step-tab ${comparisonStep === 'compare' ? 'active' : ''}`}
							disabled={!comparisonReady}
							onclick={() => (comparisonStep = 'compare')}
						>
							Policy Comparison
						</button>
					</div>

					{#if comparisonStep === 'files'}
						<form class="panel-grid" onsubmit={submitComparison}>
							<div class="field-panel">
								<h2>First Policy Output</h2>
								<DragDropFileInput
									id="comparison-file-1"
									label="Policy CSV"
									helper="Upload the first simulation output file"
									bind:file={comparisonForm.file1}
								/>
								<label class="form-field">
									<span>Plot Label</span>
									<input type="text" bind:value={comparisonForm.label1} />
								</label>
							</div>
							<div class="field-panel">
								<h2>Second Policy Output</h2>
								<DragDropFileInput
									id="comparison-file-2"
									label="Policy CSV"
									helper="Upload the second simulation output file"
									bind:file={comparisonForm.file2}
								/>
								<label class="form-field">
									<span>Plot Label</span>
									<input type="text" bind:value={comparisonForm.label2} />
								</label>
								<div class="action-row">
									<button class="primary-button" type="submit">
										<BarChart3 size={18} />
										Compare Results
									</button>
								</div>
							</div>
						</form>
					{:else}
						{#if comparisonPreviewRows.length}
							<table class="comparison-table">
								<thead>
									<tr>
										{#each Object.keys(comparisonPreviewRows[0]) as key (key)}
											<th>{key}</th>
										{/each}
									</tr>
								</thead>
								<tbody>
									{#each comparisonPreviewRows as row, index (index)}
										<tr>
											{#each Object.values(row) as value, cellIndex (cellIndex)}
												<td>{String(value)}</td>
											{/each}
										</tr>
									{/each}
								</tbody>
							</table>
						{:else}
							<div class="empty-state">Run a comparison to preview the result rows.</div>
						{/if}
					{/if}
				{/if}
			</section>

			<aside class="side-surface">
				<h2>Session Status</h2>
				<div class={`feedback ${feedbackTone === 'neutral' ? '' : feedbackTone}`}>
					{feedbackMessage}
				</div>
				<MetricCard label="Session" value={sessionId ? sessionId.slice(0, 8) : 'Pending'} tone="slate" />
				<MetricCard label="Backend" value={apiBase || 'Same origin'} tone="blue" />
				<MetricCard label="Socket" value={socketConnected ? 'Connected' : 'Waiting'} tone="green" />
			</aside>
		</div>
	</main>
</div>
