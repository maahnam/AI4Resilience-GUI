<script lang="ts">
	type StepItem = {
		id: string;
		label: string;
		disabled?: boolean;
	};

	type Props = {
		label: string;
		steps: StepItem[];
		currentStep: string;
	};

	let { label, steps, currentStep = $bindable() }: Props = $props();
</script>

<div class="step-tabs" aria-label={label}>
	{#each steps as step (step.id)}
		<button
			type="button"
			class={`step-tab ${currentStep === step.id ? 'active' : ''}`}
			disabled={step.disabled}
			onclick={() => (currentStep = step.id)}
		>
			{step.label}
		</button>
	{/each}
</div>
