<script lang="ts">
	import type { Snippet } from 'svelte';
	import favicon from '$lib/assets/favicon.svg';
	import '../app.css';

	let { children }: { children: Snippet } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>LAHSO</title>
</svelte:head>

{@render children()}
