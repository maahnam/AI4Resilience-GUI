<script lang="ts">
	import { onMount } from 'svelte';
	import type { Socket } from 'socket.io-client';
	import {
		Activity,
		BarChart3,
		BrainCircuit,
		CheckCircle2,
		Database,
		Pause,
		Play,
		RefreshCw,
		Server,
		SlidersHorizontal,
		Square
	} from 'lucide-svelte';
	import { api, apiBase } from '$lib/api';
	import FileBadge from '$lib/components/FileBadge.svelte';
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
		storage_cost: 1,
		delay_penalty: 1,
		undelivered_penalty: 100,
		compute_kbest: true
	});

	let trainingForm: TrainingForm = $state({
		learning_rate: 0.5,
		exploratory_rate: 0.95,
		num_simulations: 50000,
		simulation_duration: 42,
		continue_training: false
	});

	let implementationForm: ImplementationForm = $state({
		policy: 'gp',
		num_simulations: 20,
		simulation_duration: 35
	});

	let comparisonForm: ComparisonForm = $state({
		file1_path: '',
		file2_path: '',
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
	const datasetFiles = $derived(datasetFileList(defaultFiles));
	const disruptionFiles = $derived(disruptionFileList(defaultFiles));

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
				sessionId = payload.session_id;
				socketConnected = true;
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
				setFeedback(payload.error ?? 'Training did not start.', 'error');
				return;
			}
			trainingRunning = true;
			trainingPaused = false;
			setFeedback(payload.message ?? 'Training started.', 'good');
		} catch (error) {
			setFeedback(errorMessage(error, 'Training did not start.'), 'error');
		}
	}

	async function pauseTraining() {
		if (!trainingRunning || trainingPaused) return;

		const payload = await api.pauseTraining();
		if (payload.success) {
			trainingPaused = true;
			setFeedback(payload.message ?? 'Training paused.', 'warn');
		}
	}

	async function resumeTraining() {
		if (!trainingRunning || !trainingPaused) return;

		const payload = await api.resumeTraining();
		if (payload.success) {
			trainingPaused = false;
			setFeedback(payload.message ?? 'Training resumed.', 'good');
		} else {
			setFeedback(payload.error ?? 'Training could not resume.', 'error');
		}
	}

	async function stopTraining() {
		const payload = await api.stopTraining();
		if (payload.success) {
			trainingRunning = false;
			trainingPaused = false;
			setFeedback(payload.message ?? 'Training stopped.', 'warn');
		}
	}

	function acceptImplementationDataset() {
		implementationDatasetReady = true;
		implementationStep = 'settings';
		setFeedback('Implementation will reuse the current dataset configuration.', 'good');
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
			simulationRunning = true;
			setFeedback(payload.message ?? 'Simulation started.', 'good');
		} catch (error) {
			setFeedback(errorMessage(error, 'Simulation did not start.'), 'error');
		}
	}

	async function submitComparison(event: SubmitEvent) {
		event.preventDefault();
		setFeedback('Comparing output files...', 'neutral');
		try {
			const payload = await api.compareResults({
				...comparisonForm,
				file1_path: comparisonForm.file1_path.trim(),
				file2_path: comparisonForm.file2_path.trim(),
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

	function normalizeDatasetForm(): DatasetForm {
		return {
			storage_cost: Number(datasetForm.storage_cost),
			delay_penalty: Number(datasetForm.delay_penalty),
			undelivered_penalty: Number(datasetForm.undelivered_penalty),
			compute_kbest: datasetForm.compute_kbest
		};
	}

	function normalizeTrainingForm(): TrainingForm {
		return {
			learning_rate: Number(trainingForm.learning_rate),
			exploratory_rate: Number(trainingForm.exploratory_rate),
			num_simulations: Number(trainingForm.num_simulations),
			simulation_duration: Number(trainingForm.simulation_duration),
			continue_training: trainingForm.continue_training
		};
	}

	function normalizeImplementationForm(): ImplementationForm {
		return {
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

	function datasetFileList(files: DefaultFiles | null): Array<[string, string]> {
		if (!files) return [];

		return [
			['Intermodal network', files.network],
			['Barge network', files.network_barge],
			['Train network', files.network_train],
			['Truck network', files.network_truck],
			['Fixed schedule', files.fixed_schedule],
			['Truck schedule', files.truck_schedule],
			['Demand', files.demand],
			['Mode costs', files.mode_costs]
		];
	}

	function disruptionFileList(files: DefaultFiles | null): Array<[string, string]> {
		if (!files) return [];

		return [
			['Service disruptions', files.service_disruptions],
			['Demand disruptions', files.demand_disruptions],
			['Q-table', files.q_table]
		];
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
								<div class="field-grid">
									{#each datasetFiles as file (file[0])}
										<FileBadge label={file[0]} path={file[1]} />
									{/each}
								</div>
							</div>

							<div class="field-panel">
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
								<div class="field-grid">
									{#each disruptionFiles.slice(0, 2) as file (file[0])}
										<FileBadge label={file[0]} path={file[1]} />
									{/each}
								</div>
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
									disabled={!trainingRunning || trainingPaused}
									onclick={pauseTraining}
								>
									<Pause size={18} />
								</button>
								<button
									class="icon-button"
									type="button"
									aria-label="Resume training"
									disabled={!trainingRunning || !trainingPaused}
									onclick={resumeTraining}
								>
									<Play size={18} />
								</button>
								<button
									class="icon-button"
									type="button"
									aria-label="Stop training"
									disabled={!trainingRunning}
									onclick={stopTraining}
								>
									<Square size={17} />
								</button>
							</div>

							<div class="chart-grid">
								<SeriesChart title="Average Total Cost" points={trainingCostSeries} tone="amber" />
								<SeriesChart title="Average Reward" points={trainingRewardSeries} tone="green" />
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
						<div class="run-panel">
							<h2>Reuse Dataset Configuration</h2>
							<p>
								The implementation run uses the dataset selected in the training workflow and the
								default q-table artifact unless a backend upload path is added later.
							</p>
							<div class="panel-grid">
								{#each disruptionFiles as file (file[0])}
									<FileBadge label={file[0]} path={file[1]} />
								{/each}
							</div>
							<div class="action-row">
								<button class="primary-button" type="button" onclick={acceptImplementationDataset}>
									<Database size={18} />
									Use Current Dataset
								</button>
							</div>
						</div>
					{:else if implementationStep === 'settings'}
						<form class="panel-grid" onsubmit={submitImplementationSettings}>
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
							</div>
							<div class="field-panel">
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
								tone="blue"
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
								<label class="form-field">
									<span>CSV Path</span>
									<input
										type="text"
										placeholder="artifacts/runs/simulation_outputs/always_wait.csv"
										bind:value={comparisonForm.file1_path}
									/>
								</label>
								<label class="form-field">
									<span>Plot Label</span>
									<input type="text" bind:value={comparisonForm.label1} />
								</label>
							</div>
							<div class="field-panel">
								<h2>Second Policy Output</h2>
								<label class="form-field">
									<span>CSV Path</span>
									<input
										type="text"
										placeholder="artifacts/runs/simulation_outputs/greedy_policy.csv"
										bind:value={comparisonForm.file2_path}
									/>
								</label>
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
