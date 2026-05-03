<script lang="ts">
	import type { SeriesPoint } from '$lib/types';

	type Props = {
		title: string;
		points: SeriesPoint[];
		tone?: 'green' | 'blue' | 'amber';
		emptyLabel?: string;
	};

	let { title, points, tone = 'green', emptyLabel = 'Waiting for data' }: Props = $props();

	const boundedPoints = $derived(points.slice(-80));
	const values = $derived(boundedPoints.map((point) => point.value).filter(Number.isFinite));
	const min = $derived(values.length ? Math.min(...values) : 0);
	const max = $derived(values.length ? Math.max(...values) : 0);
	const range = $derived(max - min || 1);
	const chartPath = $derived(
		boundedPoints
			.map((point, index) => {
				const x = boundedPoints.length === 1 ? 0 : (index / (boundedPoints.length - 1)) * 100;
				const y = 100 - ((point.value - min) / range) * 88 - 6;
				return `${index === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`;
			})
			.join(' ')
	);
	const latest = $derived(boundedPoints.at(-1));
</script>

<section class={`series-chart ${tone}`}>
	<header>
		<h3>{title}</h3>
		{#if latest}
			<span>{latest.value.toLocaleString()}</span>
		{/if}
	</header>

	<div class="chart-frame">
		{#if boundedPoints.length > 1}
			<svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-label={title}>
				<path class="chart-fill" d={`${chartPath} L 100 100 L 0 100 Z`} />
				<path class="chart-line" d={chartPath} />
			</svg>
		{:else}
			<p>{emptyLabel}</p>
		{/if}
	</div>
</section>
