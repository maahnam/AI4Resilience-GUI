<script lang="ts">
	import type { ComparisonRow } from '$lib/types';

	type Props = {
		title: string;
		rows: ComparisonRow[];
		metricKey: string;
		label1: string;
		label2: string;
		emptyLabel?: string;
	};

	type DeltaPoint = {
		label: string;
		value: number;
	};

	let {
		title,
		rows,
		metricKey,
		label1,
		label2,
		emptyLabel = 'Waiting for comparison data'
	}: Props = $props();

	const points = $derived(
		rows
			.map((row, index) => {
				const value = Number(row[metricKey]);
				if (!Number.isFinite(value)) return null;

				return {
					label: String(row.Episode ?? row.index ?? index + 1),
					value
				};
			})
			.filter((point): point is DeltaPoint => point !== null)
	);
	const maxMagnitude = $derived(
		Math.max(1, ...points.map((point) => Math.abs(normalizeZero(point.value))))
	);
	const yTicks = $derived([maxMagnitude, 0, -maxMagnitude].map(formatNumber));
	const xTicks = $derived(axisXTicks(points));
	const barWidth = $derived(points.length ? Math.max(0.16, Math.min(6, 72 / points.length)) : 0);
	const zeroY = 50;

	function barHeight(value: number) {
		return Math.max(Math.abs(normalizeZero(value)) / maxMagnitude * 44, value === 0 ? 0.5 : 0);
	}

	function barY(value: number) {
		const height = barHeight(value);
		if (value > 0) return zeroY - height;
		if (value < 0) return zeroY;
		return zeroY - height / 2;
	}

	function barX(index: number) {
		const slotWidth = 100 / points.length;
		return index * slotWidth + (slotWidth - barWidth) / 2;
	}

	function barClass(value: number) {
		if (value > 0) return 'policy-one';
		if (value < 0) return 'policy-two';
		return 'policy-even';
	}

	function axisXTicks(nextPoints: DeltaPoint[]) {
		if (!nextPoints.length) return [];
		if (nextPoints.length === 1) return [{ label: nextPoints[0].label, position: 'center' }];

		const middleIndex = Math.floor((nextPoints.length - 1) / 2);
		return [
			{ label: nextPoints[0].label, position: 'start' },
			{ label: nextPoints[middleIndex].label, position: 'center' },
			{ label: nextPoints[nextPoints.length - 1].label, position: 'end' }
		].filter((tick, index, ticks) => ticks.findIndex((item) => item.label === tick.label) === index);
	}

	function normalizeZero(value: number) {
		return Math.abs(value) < 0.000001 ? 0 : value;
	}

	function formatNumber(value: number) {
		const normalizedValue = normalizeZero(value);
		return normalizedValue.toLocaleString(undefined, {
			maximumFractionDigits: Math.abs(normalizedValue) >= 100 ? 0 : 2
		});
	}
</script>

<section class="delta-bar-chart">
	<header>
		<h3>{title}</h3>
		{#if points.length}
			<span>{points.length.toLocaleString()} episodes</span>
		{/if}
	</header>

	<div class="delta-legend" aria-hidden="true">
		<span><i class="policy-one"></i>{label1} performs better</span>
		<span><i class="policy-two"></i>{label2} performs better</span>
	</div>

	<div class="chart-frame delta-frame">
		<div class="y-axis-label">{metricKey}</div>
		<div class="y-axis-scale" aria-hidden="true">
			{#each yTicks as tick (tick)}
				<span>{tick}</span>
			{/each}
		</div>
		<div class="chart-plot">
			{#if points.length}
				<svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-label={`${title} by episode`}>
					<line class="delta-zero-line" x1="0" x2="100" y1={zeroY} y2={zeroY} />
					{#each points as point, index (`${point.label}-${index}`)}
						<rect
							class={barClass(point.value)}
							x={barX(index)}
							y={barY(point.value)}
							width={barWidth}
							height={barHeight(point.value)}
						/>
					{/each}
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
		<div class="x-axis-label">Episode</div>
	</div>
</section>
