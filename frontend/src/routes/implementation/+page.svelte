<script lang="ts">
	import { Activity, SlidersHorizontal } from 'lucide-svelte';
	import DatasetConfigurationForm from '$lib/components/DatasetConfigurationForm.svelte';
	import DragDropFileInput from '$lib/components/DragDropFileInput.svelte';
	import MetricCard from '$lib/components/MetricCard.svelte';
	import SeriesChart from '$lib/components/SeriesChart.svelte';
	import WorkflowStepTabs from '$lib/components/WorkflowStepTabs.svelte';
	import { toSeries, useLahsoWorkflow } from '$lib/state/lahso-workflow.svelte';

	const app = useLahsoWorkflow();

	let implementationSteps = $derived([
		{ id: 'dataset', label: 'Dataset Input' },
		{
			id: 'settings',
			label: 'Simulation Settings',
			disabled: !app.readiness.implementationDatasetReady
		},
		{
			id: 'execute',
			label: 'Execute Simulation',
			disabled: !app.readiness.implementationReady
		}
	]);
	let simulationCostSeries = $derived(toSeries(app.metrics.simulation, 'Total Cost'));
	let simulationArtifacts = $derived(
		app.artifacts.files.filter((artifact) => artifact.kind === 'simulation_output')
	);
</script>

<svelte:head>
	<title>LAHSO | Model Implementation</title>
	<meta
		name="description"
		content="Configure LAHSO implementation runs and watch cost output as simulations complete."
	/>
</svelte:head>

<WorkflowStepTabs
	label="Implementation steps"
	steps={implementationSteps}
	bind:currentStep={app.steps.implementation}
/>

{#if app.steps.implementation === 'dataset'}
	<DatasetConfigurationForm
		bind:form={app.forms.dataset}
		defaultFiles={app.status.defaultFiles}
		prefix="implementation-dataset"
		submitLabel="Validate Dataset"
		loading={app.status.loadingConfig}
		onsubmit={app.submitImplementationDataset}
		onreload={app.loadDefaults}
	/>
{:else if app.steps.implementation === 'settings'}
	<form class="panel-grid" onsubmit={app.submitImplementationSettings}>
		<div class="field-panel">
			<h2>Disruption and Model Inputs</h2>
			<DragDropFileInput
				id="implementation-service-disruptions"
				label="Service Disruptions"
				helper="Default: data/raw/disruptions/No_Service_Disruption_Profile.csv"
				bind:file={app.forms.implementation.service_disruptions}
			/>
			<DragDropFileInput
				id="implementation-demand-disruptions"
				label="Demand Disruptions"
				helper="Default: data/raw/disruptions/No_Request_Disruption_Profile.csv"
				bind:file={app.forms.implementation.demand_disruptions}
			/>
			<DragDropFileInput
				id="implementation-q-table"
				label="Q-Table"
				accept=".pkl"
				helper={app.status.defaultFiles ? `Default: ${app.status.defaultFiles.q_table}` : 'PKL input'}
				bind:file={app.forms.implementation.q_table}
			/>
		</div>

		<div class="field-panel">
			<h2>Policy</h2>
			<div class="segment-control" aria-label="Policy">
				<button
					type="button"
					class={`segment-button ${app.forms.implementation.policy === 'gp' ? 'active' : ''}`}
					onclick={() => (app.forms.implementation.policy = 'gp')}
				>
					Greedy
				</button>
				<button
					type="button"
					class={`segment-button ${app.forms.implementation.policy === 'aw' ? 'active' : ''}`}
					onclick={() => (app.forms.implementation.policy = 'aw')}
				>
					Always Wait
				</button>
				<button
					type="button"
					class={`segment-button ${app.forms.implementation.policy === 'ar' ? 'active' : ''}`}
					onclick={() => (app.forms.implementation.policy = 'ar')}
				>
					Always Reassign
				</button>
			</div>

			<h2>Simulation</h2>
			<label class="form-field">
				<span>Number of Simulations</span>
				<input type="number" min="1" bind:value={app.forms.implementation.num_simulations} />
			</label>
			<label class="form-field">
				<span>Duration per Episode</span>
				<input type="number" min="1" bind:value={app.forms.implementation.simulation_duration} />
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
			<MetricCard label="Policy" value={app.forms.implementation.policy.toUpperCase()} tone="blue" />
			<MetricCard label="Episodes" value={app.forms.implementation.num_simulations} tone="green" />
			<MetricCard label="State" value={app.run.simulationRunning ? 'Running' : 'Ready'} tone="amber" />
		</div>

		<div class="action-row">
			<button
				class="primary-button"
				type="button"
				disabled={!app.readiness.implementationReady || app.run.simulationRunning}
				onclick={app.executeSimulation}
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
			emptyLabel={app.run.simulationRunning ? 'Simulation is running' : 'Waiting for data'}
		/>

		{#if simulationArtifacts.length}
			<div class="artifact-list">
				<h2>Downloads</h2>
				{#each simulationArtifacts as artifact (artifact.id)}
					<div class="artifact-row">
						<span>{artifact.label}</span>
						<a href={artifact.url}>Download</a>
					</div>
				{/each}
			</div>
		{/if}
	</div>
{/if}
