<script lang="ts">
	import type { SeriesPoint } from '$lib/types';

	type Props = {
		title: string;
		points: SeriesPoint[];
		tone?: 'green' | 'blue' | 'amber';
		emptyLabel?: string;
		xAxisLabel?: string;
		yAxisLabel?: string;
	};

	let {
		title,
		points,
		tone = 'green',
		emptyLabel = 'Waiting for data',
		xAxisLabel = '',
		yAxisLabel = ''
	}: Props = $props();

	const boundedPoints = $derived(points.slice(-80));
	const values = $derived(boundedPoints.map((point) => point.value).filter(Number.isFinite));
	const min = $derived(values.length ? Math.min(...values) : 0);
	const max = $derived(values.length ? Math.max(...values) : 0);
	const range = $derived(max - min || 1);
	const xTicks = $derived(axisXTicks(boundedPoints));
	const yTicks = $derived(axisYTicks(min, max));
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

	function axisXTicks(points: SeriesPoint[]) {
		if (!points.length) return [];
		if (points.length === 1) return [{ label: points[0].label, position: 'center' }];

		const middleIndex = Math.floor((points.length - 1) / 2);
		return [
			{ label: points[0].label, position: 'start' },
			{ label: points[middleIndex].label, position: 'center' },
			{ label: points[points.length - 1].label, position: 'end' }
		].filter((tick, index, ticks) => ticks.findIndex((item) => item.label === tick.label) === index);
	}

	function axisYTicks(minValue: number, maxValue: number) {
		if (!values.length) return [];
		if (minValue === maxValue) return [formatTick(maxValue)];

		return [maxValue, minValue + (maxValue - minValue) / 2, minValue].map(formatTick);
	}

	function formatTick(value: number | string) {
		const numericValue = Number(value);
		if (!Number.isFinite(numericValue)) return String(value);

		return numericValue.toLocaleString(undefined, {
			maximumFractionDigits: Math.abs(numericValue) >= 100 ? 0 : 2
		});
	}
</script>

<section class={`series-chart ${tone}`}>
	<header>
		<h3>{title}</h3>
		{#if latest}
			<span>{latest.value.toLocaleString()}</span>
		{/if}
	</header>

	<div class="chart-frame">
		<div class="y-axis-label">{yAxisLabel}</div>
		<div class="y-axis-scale" aria-hidden="true">
			{#each yTicks as tick (tick)}
				<span>{tick}</span>
			{/each}
		</div>
		<div class="chart-plot">
			{#if boundedPoints.length}
				<svg
					viewBox="0 0 100 100"
					preserveAspectRatio="none"
					aria-label={`${title}${xAxisLabel ? `, x axis ${xAxisLabel}` : ''}${yAxisLabel ? `, y axis ${yAxisLabel}` : ''}`}
				>
					{#if boundedPoints.length > 1}
						<path class="chart-fill" d={`${chartPath} L 100 100 L 0 100 Z`} />
						<path class="chart-line" d={chartPath} />
					{:else}
						<circle class="chart-point" cx="50" cy="50" r="3.5" />
					{/if}
				</svg>
			{:else}
				<p>{emptyLabel}</p>
			{/if}
		</div>
		<div class="x-axis-scale" aria-hidden="true">
			{#each xTicks as tick (tick.label)}
				<span class={`x-tick ${tick.position}`}>{tick.label}</span>
			{/each}
		</div>
		<div class="x-axis-label">{xAxisLabel}</div>
	</div>
</section>
