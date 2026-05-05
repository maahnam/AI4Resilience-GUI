<script lang="ts">
	import { CheckCircle2, RefreshCw } from 'lucide-svelte';
	import DragDropFileInput from '$lib/components/DragDropFileInput.svelte';
	import type { DatasetForm, DefaultFiles } from '$lib/types';

	type Props = {
		form: DatasetForm;
		defaultFiles: DefaultFiles | null;
		prefix: string;
		submitLabel?: string;
		loading?: boolean;
		onsubmit: (event: SubmitEvent) => void | Promise<void>;
		onreload: () => void | Promise<void>;
	};

	let {
		form = $bindable(),
		defaultFiles,
		prefix,
		submitLabel = 'Validate Dataset',
		loading = false,
		onsubmit,
		onreload
	}: Props = $props();
</script>

<form class="panel-grid" onsubmit={onsubmit}>
	<div class="field-panel">
		<h2>Network and Demand Files</h2>
		<DragDropFileInput
			id={`${prefix}-network`}
			label="Intermodal Network"
			helper={defaultFiles ? `Default: ${defaultFiles.network}` : 'CSV input'}
			bind:file={form.network}
		/>
		<DragDropFileInput
			id={`${prefix}-network-barge`}
			label="Barge Network"
			helper={defaultFiles ? `Default: ${defaultFiles.network_barge}` : 'CSV input'}
			bind:file={form.network_barge}
		/>
		<DragDropFileInput
			id={`${prefix}-network-train`}
			label="Train Network"
			helper={defaultFiles ? `Default: ${defaultFiles.network_train}` : 'CSV input'}
			bind:file={form.network_train}
		/>
		<DragDropFileInput
			id={`${prefix}-network-truck`}
			label="Truck Network"
			helper={defaultFiles ? `Default: ${defaultFiles.network_truck}` : 'CSV input'}
			bind:file={form.network_truck}
		/>
	</div>

	<div class="field-panel">
		<h2>Schedules, Demand, and Costs</h2>
		<DragDropFileInput
			id={`${prefix}-fixed-schedule`}
			label="Fixed Schedule"
			helper={defaultFiles ? `Default: ${defaultFiles.fixed_schedule}` : 'CSV input'}
			bind:file={form.fixed_schedule}
		/>
		<DragDropFileInput
			id={`${prefix}-truck-schedule`}
			label="Truck Schedule"
			helper={defaultFiles ? `Default: ${defaultFiles.truck_schedule}` : 'CSV input'}
			bind:file={form.truck_schedule}
		/>
		<DragDropFileInput
			id={`${prefix}-demand`}
			label="Demand"
			helper={defaultFiles ? `Default: ${defaultFiles.demand}` : 'CSV input'}
			bind:file={form.demand}
		/>
		<DragDropFileInput
			id={`${prefix}-mode-costs`}
			label="Mode Costs"
			helper={defaultFiles ? `Default: ${defaultFiles.mode_costs}` : 'CSV input'}
			bind:file={form.mode_costs}
		/>

		<h2>Cost Parameters</h2>
		<label class="form-field">
			<span>Storage Cost</span>
			<input type="number" min="0" bind:value={form.storage_cost} />
			<span class="hint">Euro per container hour</span>
		</label>
		<label class="form-field">
			<span>Delay Penalty</span>
			<input type="number" min="0" bind:value={form.delay_penalty} />
			<span class="hint">Euro per container hour</span>
		</label>
		<label class="form-field">
			<span>Undelivered Penalty</span>
			<input type="number" min="0" bind:value={form.undelivered_penalty} />
			<span class="hint">Euro per container</span>
		</label>
		<label class="check-row">
			<input type="checkbox" bind:checked={form.compute_kbest} />
			<span>Compute K-best solution set</span>
		</label>

		<div class="action-row">
			<button class="primary-button" type="submit" disabled={loading}>
				<CheckCircle2 size={18} />
				{submitLabel}
			</button>
			<button class="ghost-button" type="button" onclick={onreload}>
				<RefreshCw size={17} />
				Reload Defaults
			</button>
		</div>
	</div>
</form>
