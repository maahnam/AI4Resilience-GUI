<script lang="ts">
	import type { Snippet } from 'svelte';

	type Props = {
		label: string;
		value: string | number;
		tone?: 'green' | 'blue' | 'amber' | 'slate';
		children?: Snippet;
	};

	let { label, value, tone = 'slate', children }: Props = $props();
</script>

<section class={`metric-card ${tone}`}>
	<span>{label}</span>
	<strong>{value}</strong>
	{#if children}
		<div class="metric-extra">
			{@render children()}
		</div>
	{/if}
</section>
