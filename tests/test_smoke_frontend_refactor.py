from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = PROJECT_ROOT / "frontend"


def test_sveltekit_frontend_uses_svelte_5_and_flask_api_contract() -> None:
    package_json = json.loads((FRONTEND_ROOT / "package.json").read_text())
    dependencies = package_json.get("dependencies", {})
    dev_dependencies = package_json.get("devDependencies", {})

    assert dependencies["socket.io-client"].startswith("^4.")
    assert dependencies["lucide-svelte"]
    assert dev_dependencies["svelte"].startswith("^5.")
    assert dev_dependencies["svelte-adapter-bun"]

    layout_source = (FRONTEND_ROOT / "src" / "routes" / "+layout.svelte").read_text()
    root_page_load = (FRONTEND_ROOT / "src" / "routes" / "+page.ts").read_text()
    training_page_source = (
        FRONTEND_ROOT / "src" / "routes" / "training" / "+page.svelte"
    ).read_text()
    implementation_page_source = (
        FRONTEND_ROOT / "src" / "routes" / "implementation" / "+page.svelte"
    ).read_text()
    comparison_page_source = (
        FRONTEND_ROOT / "src" / "routes" / "comparison" / "+page.svelte"
    ).read_text()
    api_source = (FRONTEND_ROOT / "src" / "lib" / "api.ts").read_text()
    workflow_state_source = (
        FRONTEND_ROOT / "src" / "lib" / "state" / "lahso-workflow.svelte.ts"
    ).read_text()
    dataset_form_source = (
        FRONTEND_ROOT / "src" / "lib" / "components" / "DatasetConfigurationForm.svelte"
    ).read_text()
    workflow_tabs_source = (
        FRONTEND_ROOT / "src" / "lib" / "components" / "WorkflowStepTabs.svelte"
    ).read_text()
    series_chart_source = (
        FRONTEND_ROOT / "src" / "lib" / "components" / "SeriesChart.svelte"
    ).read_text()
    app_css = (FRONTEND_ROOT / "src" / "app.css").read_text()
    svelte_config = (FRONTEND_ROOT / "svelte.config.js").read_text()
    vite_config = (FRONTEND_ROOT / "vite.config.ts").read_text()

    page_sources = "\n".join(
        [
            layout_source,
            training_page_source,
            implementation_page_source,
            comparison_page_source,
            dataset_form_source,
            workflow_tabs_source,
        ]
    )

    assert "createContext" in workflow_state_source
    assert "$state(" in workflow_state_source
    assert "$derived(" in training_page_source
    assert "$derived(" in implementation_page_source
    assert 'href="/training"' in layout_source
    assert "href: '/training'" in workflow_state_source
    assert "href: '/implementation'" in workflow_state_source
    assert "href: '/comparison'" in workflow_state_source
    assert "throw redirect(307, '/training')" in root_page_load
    assert "WorkflowStepTabs" in training_page_source
    assert "WorkflowStepTabs" in implementation_page_source
    assert "WorkflowStepTabs" in comparison_page_source
    assert "DatasetConfigurationForm" in training_page_source
    assert "DatasetConfigurationForm" in implementation_page_source
    assert "bind:file={form.network}" in dataset_form_source
    assert "bind:file={form.mode_costs}" in dataset_form_source
    assert "bind:file={app.forms.training.service_disruptions}" in training_page_source
    assert "bind:file={app.forms.implementation.q_table}" in implementation_page_source
    assert "bind:file={app.forms.comparison.file1}" in comparison_page_source
    assert "bind:file={app.forms.comparison.file2}" in comparison_page_source
    assert (
        training_page_source.count('xAxisLabel="Episode"')
        + implementation_page_source.count('xAxisLabel="Episode"')
        == 3
    )
    assert 'yAxisLabel="Total Cost"' in training_page_source
    assert 'yAxisLabel="Total Reward"' in training_page_source
    assert 'yAxisLabel="Total Cost"' in implementation_page_source
    assert "axisXTicks" in series_chart_source
    assert "axisYTicks" in series_chart_source
    assert 'class="x-axis-scale"' in series_chart_source
    assert 'class="y-axis-scale"' in series_chart_source
    assert ".x-axis-scale" in app_css
    assert ".y-axis-scale" in app_css
    assert 'tone="blue"\n\t\t\temptyLabel' not in page_sources
    assert 'tone="amber"\n\t\t\temptyLabel' not in page_sources
    assert "let canControlTraining = $derived(app.readiness.trainingReady || app.run.trainingRunning)" in training_page_source
    assert "payload.error === 'Training already active'" in workflow_state_source
    assert "Controls are reconnected" in workflow_state_source
    assert "io(apiBase || undefined" in workflow_state_source
    assert "disabled={!canControlTraining || app.run.trainingPaused}" in training_page_source
    assert training_page_source.count("disabled={!canControlTraining}") == 2
    assert "on:click" not in page_sources
    assert "on:submit" not in page_sources
    assert "syncSession(payload.session_id)" in workflow_state_source
    assert "join_session" in workflow_state_source
    assert "CSV Path" not in page_sources
    assert "FormData" in api_source
    assert "$env/dynamic/public" not in api_source
    assert "import.meta" in api_source
    assert "appendOptionalFile(formData, 'network'" in api_source
    assert "appendOptionalFile(formData, 'service_disruptions'" in api_source
    assert "appendOptionalFile(formData, 'q_table'" in api_source
    assert "/api/config/default" in api_source
    assert "/api/training/start" in api_source
    assert "svelte-adapter-bun" in svelte_config
    assert "runes:" in svelte_config
    assert "'/api': 'http://127.0.0.1:5001'" in vite_config
    assert "'/socket.io'" in vite_config


def test_gradio_frontend_files_are_still_present() -> None:
    gradio_modules = {
        "dataset_input_tab.py",
        "training_agent_tabs.py",
        "model_implementation_tabs.py",
        "result_comparison_tabs.py",
    }
    ui_root = PROJECT_ROOT / "src" / "lahso" / "ui"

    assert gradio_modules.issubset({path.name for path in ui_root.glob("*.py")})


def test_frontend_and_flask_runner_share_development_port_contract() -> None:
    root_app = (PROJECT_ROOT / "app.py").read_text()
    frontend_readme = (FRONTEND_ROOT / "README.md").read_text()

    assert "port=5001" in root_app
    assert "http://127.0.0.1:5001" in frontend_readme
    assert "bun --bun run dev" in frontend_readme
