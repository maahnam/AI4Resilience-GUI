<script lang="ts">
	import { CheckCircle2, FileText } from 'lucide-svelte';

	type Props = {
		label: string;
		path?: string;
		status?: 'ready' | 'manual' | 'missing';
	};

	let { label, path = '', status = 'ready' }: Props = $props();

	const fileName = $derived(path ? path.split('/').at(-1) : 'Not selected');
</script>

<div class={`file-badge ${status}`}>
	<div class="file-icon">
		{#if status === 'ready'}
			<CheckCircle2 size={18} />
		{:else}
			<FileText size={18} />
		{/if}
	</div>
	<div>
		<span>{label}</span>
		<strong>{fileName}</strong>
	</div>
</div>
