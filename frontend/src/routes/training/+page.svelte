<script lang="ts">
	import { Pause, Play, SlidersHorizontal, Square } from 'lucide-svelte';
	import DatasetConfigurationForm from '$lib/components/DatasetConfigurationForm.svelte';
	import DragDropFileInput from '$lib/components/DragDropFileInput.svelte';
	import MetricCard from '$lib/components/MetricCard.svelte';
	import SeriesChart from '$lib/components/SeriesChart.svelte';
	import WorkflowStepTabs from '$lib/components/WorkflowStepTabs.svelte';
	import { toSeries, useLahsoWorkflow } from '$lib/state/lahso-workflow.svelte';

	const app = useLahsoWorkflow();

	let trainingSteps = $derived([
		{ id: 'dataset', label: 'Dataset Input' },
		{ id: 'settings', label: 'Simulation Settings', disabled: !app.readiness.datasetReady },
		{ id: 'run', label: 'Training', disabled: !app.readiness.trainingReady }
	]);
	let trainingCostSeries = $derived(toSeries(app.metrics.training, 'Total Cost'));
	let trainingRewardSeries = $derived(toSeries(app.metrics.training, 'Total Reward'));
	let trainingProgress = $derived(
		app.run.totalEpisodes > 0
			? Math.min(100, Math.round((app.run.trainingEpisode / app.run.totalEpisodes) * 100))
			: 0
	);
	let canControlTraining = $derived(app.readiness.trainingReady || app.run.trainingRunning);
	let trainingArtifacts = $derived(
		app.artifacts.files.filter(
			(artifact) => artifact.kind === 'model' || artifact.kind === 'training_metric'
		)
	);
</script>

<svelte:head>
	<title>LAHSO | Training Agent</title>
	<meta
		name="description"
		content="Validate datasets, configure simulations, and monitor live LAHSO training progress."
	/>
</svelte:head>

<WorkflowStepTabs label="Training steps" steps={trainingSteps} bind:currentStep={app.steps.training} />

{#if app.steps.training === 'dataset'}
	<DatasetConfigurationForm
		bind:form={app.forms.dataset}
		defaultFiles={app.status.defaultFiles}
		prefix="dataset"
		submitLabel="Validate Dataset"
		loading={app.status.loadingConfig}
		onsubmit={app.submitDataset}
		onreload={app.loadDefaults}
	/>
{:else if app.steps.training === 'settings'}
	<form class="panel-grid" onsubmit={app.submitTrainingSettings}>
		<div class="field-panel">
			<h2>Disruption Inputs</h2>
			<DragDropFileInput
				id="training-service-disruptions"
				label="Service Disruptions"
				helper={app.status.defaultFiles ? `Default: ${app.status.defaultFiles.service_disruptions}` : 'CSV input'}
				bind:file={app.forms.training.service_disruptions}
			/>
			<DragDropFileInput
				id="training-demand-disruptions"
				label="Demand Disruptions"
				helper={app.status.defaultFiles ? `Default: ${app.status.defaultFiles.demand_disruptions}` : 'CSV input'}
				bind:file={app.forms.training.demand_disruptions}
			/>
			{#if app.forms.training.continue_training}
				<DragDropFileInput
					id="training-last-q-table"
					label="Last Q-Table"
					accept=".pkl"
					helper={app.status.defaultFiles ? `Default: ${app.status.defaultFiles.q_table}` : 'PKL input'}
					bind:file={app.forms.training.last_q_table}
				/>
				<DragDropFileInput
					id="training-last-total-cost"
					label="Last Total Cost"
					accept=".pkl"
					helper="Previous total-cost metric pickle"
					bind:file={app.forms.training.last_total_cost}
				/>
				<DragDropFileInput
					id="training-last-reward"
					label="Last Reward"
					accept=".pkl"
					helper="Previous reward metric pickle"
					bind:file={app.forms.training.last_reward}
				/>
			{/if}
		</div>

		<div class="field-panel">
			<h2>Learning and Simulation</h2>
			<label class="form-field">
				<span>Learning Rate</span>
				<input type="number" min="0" max="1" step="0.01" bind:value={app.forms.training.learning_rate} />
			</label>
			<label class="form-field">
				<span>Exploratory Rate</span>
				<input
					type="number"
					min="0"
					max="1"
					step="0.01"
					bind:value={app.forms.training.exploratory_rate}
				/>
			</label>
			<label class="form-field">
				<span>Number of Simulations</span>
				<input type="number" min="1" bind:value={app.forms.training.num_simulations} />
			</label>
			<label class="form-field">
				<span>Simulation Duration</span>
				<input type="number" min="1" bind:value={app.forms.training.simulation_duration} />
				<span class="hint">Days per simulation</span>
			</label>
			<label class="check-row">
				<input type="checkbox" bind:checked={app.forms.training.continue_training} />
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
			<MetricCard
				label="Episode"
				value={`${app.run.trainingEpisode} / ${app.run.totalEpisodes}`}
				tone="green"
			/>
			<MetricCard label="Progress" value={`${trainingProgress}%`} tone="blue" />
			<MetricCard
				label="State"
				value={app.run.trainingPaused ? 'Paused' : app.run.trainingRunning ? 'Running' : 'Ready'}
				tone="amber"
			/>
		</div>

		<div class="control-row">
			<button
				class="primary-button"
				type="button"
				disabled={!app.readiness.trainingReady || app.run.trainingRunning}
				onclick={app.startTraining}
			>
				<Play size={18} />
				Start
			</button>
			<button
				class="icon-button"
				type="button"
				aria-label="Pause training"
				disabled={!canControlTraining || app.run.trainingPaused}
				onclick={app.pauseTraining}
			>
				<Pause size={18} />
			</button>
			<button
				class="icon-button"
				type="button"
				aria-label="Resume training"
				disabled={!canControlTraining}
				onclick={app.resumeTraining}
			>
				<Play size={18} />
			</button>
			<button
				class="icon-button"
				type="button"
				aria-label="Stop training"
				disabled={!canControlTraining}
				onclick={app.stopTraining}
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
				emptyLabel={app.run.trainingRunning ? 'Training is running' : 'Waiting for data'}
			/>
			<SeriesChart
				title="Average Reward"
				points={trainingRewardSeries}
				tone="green"
				xAxisLabel="Episode"
				yAxisLabel="Total Reward"
				emptyLabel={app.run.trainingRunning ? 'Training is running' : 'Waiting for data'}
			/>
		</div>

		{#if trainingArtifacts.length}
			<div class="artifact-list">
				<h2>Downloads</h2>
				{#each trainingArtifacts as artifact (artifact.id)}
					<div class="artifact-row">
						<span>{artifact.label}</span>
						<a href={artifact.url}>Download</a>
					</div>
				{/each}
			</div>
		{/if}
	</div>
{/if}
