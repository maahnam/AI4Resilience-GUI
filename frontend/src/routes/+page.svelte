<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	onMount(() => {
		void goto('/training', { replaceState: true });
	});
</script>

<svelte:head>
	<title>LAHSO</title>
</svelte:head>

<div class="empty-state">Opening Training Agent...</div>
