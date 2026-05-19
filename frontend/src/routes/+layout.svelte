<script lang="ts">
	import type { Snippet } from 'svelte';
	import { onMount } from 'svelte';
	import { dev } from '$app/environment';
	import { page } from '$app/state';
	import { BarChart3, BrainCircuit, Server } from 'lucide-svelte';
	import favicon from '$lib/assets/favicon.svg';
	import MetricCard from '$lib/components/MetricCard.svelte';
	import { apiBase } from '$lib/api';
	import {
		createLahsoWorkflowState,
		navItems,
		setLahsoWorkflow
	} from '$lib/state/lahso-workflow.svelte';
	import '../app.css';

	let { children }: { children: Snippet } = $props();

	const workflow = createLahsoWorkflowState();
	setLahsoWorkflow(workflow);

	let pathname = $derived(page.url.pathname);
	let activeNav = $derived(
		navItems.find((item) => pathname === item.href || pathname.startsWith(`${item.href}/`)) ??
			navItems[0]
	);

	onMount(() => workflow.mount());
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<div class="app-shell">
	<aside class="sidebar">
		<a class="brand brand-link" href="/training" data-sveltekit-preload-data="hover">
			<div class="brand-mark">L</div>
			<div>
				<strong>LAHSO</strong>
				<span>Hybrid simulation optimization</span>
			</div>
		</a>

		<nav class="nav-stack" aria-label="Workflow">
			{#each navItems as item (item.id)}
				<a
					href={item.href}
					data-sveltekit-preload-data="hover"
					class={`nav-button ${activeNav.id === item.id ? 'active' : ''}`}
					aria-current={activeNav.id === item.id ? 'page' : undefined}
				>
					{#if item.id === 'training'}
						<BrainCircuit size={18} />
					{:else if item.id === 'implementation'}
						<Server size={18} />
					{:else}
						<BarChart3 size={18} />
					{/if}
					<span>{item.label}</span>
				</a>
			{/each}
		</nav>

		{#if dev}
			<div class="sidebar-note">
				Gradio remains available for the full research/operator workflow while this frontend moves the
				Flask UI toward a product API client.
			</div>
		{/if}
	</aside>

	<main class="main-panel">
		<header class="topbar">
			<div>
				<h1>{activeNav.label}</h1>
				<p>{activeNav.description}</p>
			</div>

			{#if dev}
				<div class="status-pill">
					<span class={`status-dot ${workflow.status.socketConnected ? 'connected' : ''}`}></span>
					<span>{workflow.status.socketConnected ? 'Live session' : 'Connecting'}</span>
				</div>
			{/if}
		</header>

		<div class={`workspace-grid ${dev ? '' : 'full-width'}`}>
			<section class="work-surface">
				{#if workflow.status.connectionInterrupted}
					<div class="disconnect-panel">
						<h2>Connection interrupted</h2>
						<p>
							The backend job may still be running. Reconnect to recover the current session state and
							continue monitoring progress.
						</p>
						<button class="primary-button" type="button" onclick={workflow.refreshSessionStatus}>
							Reconnect Session
						</button>
					</div>
				{:else}
					{@render children()}
				{/if}
			</section>

			{#if dev}
				<aside class="side-surface">
					<h2>Session Status</h2>
					<div
						class={`feedback ${workflow.status.feedbackTone === 'neutral' ? '' : workflow.status.feedbackTone}`}
					>
						{workflow.status.feedbackMessage}
					</div>
					<MetricCard
						label="Session"
						value={workflow.status.sessionId ? workflow.status.sessionId.slice(0, 8) : 'Pending'}
						tone="slate"
					/>
					<MetricCard label="Backend" value={apiBase || 'Same origin'} tone="blue" />
					<MetricCard
						label="Socket"
						value={workflow.status.socketConnected ? 'Connected' : 'Waiting'}
						tone="green"
					/>
				</aside>
			{/if}
		</div>
	</main>
</div>
