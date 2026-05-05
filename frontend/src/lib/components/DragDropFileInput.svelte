<script lang="ts">
	import { CheckCircle2, FileText, Upload, X } from 'lucide-svelte';

	type Props = {
		id: string;
		label: string;
		accept?: string;
		helper?: string;
		file: File | null;
	};

	let { id, label, accept = '.csv', helper = '', file = $bindable<File | null>(null) }: Props =
		$props();

	let inputElement: HTMLInputElement | null = $state(null);
	let isDragging = $state(false);

	const fileKind = $derived(fileKindFromAccept(accept));
	const emptyLabel = $derived(
		fileKind === 'file' ? 'Choose or drop a file' : `Choose or drop a ${fileKind} file`
	);
	const fileDetail = $derived(
		file ? `${formatFileSize(file.size)} ${fileKind.toUpperCase()}` : helper
	);

	function handleInputChange(event: Event) {
		const target = event.currentTarget as HTMLInputElement;
		file = target.files?.[0] ?? null;
	}

	function handleDragOver(event: DragEvent) {
		event.preventDefault();
		isDragging = true;
	}

	function handleDragLeave(event: DragEvent) {
		if (event.currentTarget === event.target) {
			isDragging = false;
		}
	}

	function handleDrop(event: DragEvent) {
		event.preventDefault();
		isDragging = false;

		file = event.dataTransfer?.files?.[0] ?? null;
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter' || event.key === ' ') {
			event.preventDefault();
			inputElement?.click();
		}
	}

	function clearFile(event: MouseEvent) {
		event.stopPropagation();
		file = null;
		if (inputElement) {
			inputElement.value = '';
		}
	}

	function formatFileSize(size: number) {
		if (size < 1024) return `${size} B`;
		if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
		return `${(size / (1024 * 1024)).toFixed(1)} MB`;
	}

	function fileKindFromAccept(acceptedTypes: string) {
		if (acceptedTypes.includes('.pkl')) return 'PKL';
		if (acceptedTypes.includes('.csv')) return 'CSV';
		return 'file';
	}
</script>

<input
	bind:this={inputElement}
	class="sr-only"
	type="file"
	{id}
	{accept}
	onchange={handleInputChange}
/>

<div
	class={`drop-file ${isDragging ? 'dragging' : ''} ${file ? 'ready' : ''}`}
	role="button"
	tabindex="0"
	aria-controls={id}
	aria-label={`${label}: ${file ? file.name : 'choose file'}`}
	onclick={() => inputElement?.click()}
	onkeydown={handleKeydown}
	ondragover={handleDragOver}
	ondragleave={handleDragLeave}
	ondrop={handleDrop}
>
	<div class="file-icon">
		{#if file}
			<CheckCircle2 size={18} />
		{:else if isDragging}
			<Upload size={18} />
		{:else}
			<FileText size={18} />
		{/if}
	</div>
	<div class="drop-copy">
		<span>{label}</span>
		<strong>{file?.name ?? emptyLabel}</strong>
		{#if fileDetail}
			<small>{fileDetail}</small>
		{/if}
	</div>
	{#if file}
		<button class="drop-clear" type="button" aria-label={`Clear ${label}`} onclick={clearFile}>
			<X size={15} />
		</button>
	{/if}
</div>
