<script lang="ts">
	import { BarChart3 } from 'lucide-svelte';
	import DragDropFileInput from '$lib/components/DragDropFileInput.svelte';
	import WorkflowStepTabs from '$lib/components/WorkflowStepTabs.svelte';
	import { useLahsoWorkflow } from '$lib/state/lahso-workflow.svelte';

	const app = useLahsoWorkflow();

	let comparisonSteps = $derived([
		{ id: 'files', label: 'Policy Files' },
		{ id: 'compare', label: 'Comparison Preview', disabled: !app.readiness.comparisonReady }
	]);
	let comparisonPreviewRows = $derived(app.metrics.comparison.slice(0, 10));
</script>

<svelte:head>
	<title>LAHSO | Results Comparison</title>
	<meta
		name="description"
		content="Upload two LAHSO policy outputs and preview the comparison table without leaving the app."
	/>
</svelte:head>

<WorkflowStepTabs
	label="Comparison steps"
	steps={comparisonSteps}
	bind:currentStep={app.steps.comparison}
/>

{#if app.steps.comparison === 'files'}
	<form class="panel-grid" onsubmit={app.submitComparison}>
		<div class="field-panel">
			<h2>First Policy Output</h2>
			<DragDropFileInput
				id="comparison-file-1"
				label="Policy CSV"
				helper="Upload the first simulation output file"
				bind:file={app.forms.comparison.file1}
			/>
			<label class="form-field">
				<span>Plot Label</span>
				<input type="text" bind:value={app.forms.comparison.label1} />
			</label>
		</div>

		<div class="field-panel">
			<h2>Second Policy Output</h2>
			<DragDropFileInput
				id="comparison-file-2"
				label="Policy CSV"
				helper="Upload the second simulation output file"
				bind:file={app.forms.comparison.file2}
			/>
			<label class="form-field">
				<span>Plot Label</span>
				<input type="text" bind:value={app.forms.comparison.label2} />
			</label>
			<div class="action-row">
				<button class="primary-button" type="submit">
					<BarChart3 size={18} />
					Compare Results
				</button>
			</div>
		</div>
	</form>
{:else if comparisonPreviewRows.length}
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
