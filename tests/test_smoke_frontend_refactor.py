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

    page_source = (FRONTEND_ROOT / "src" / "routes" / "+page.svelte").read_text()
    api_source = (FRONTEND_ROOT / "src" / "lib" / "api.ts").read_text()
    series_chart_source = (
        FRONTEND_ROOT / "src" / "lib" / "components" / "SeriesChart.svelte"
    ).read_text()
    app_css = (FRONTEND_ROOT / "src" / "app.css").read_text()
    svelte_config = (FRONTEND_ROOT / "svelte.config.js").read_text()
    vite_config = (FRONTEND_ROOT / "vite.config.ts").read_text()

    assert "$state(" in page_source
    assert "$derived(" in page_source
    assert "DragDropFileInput" in page_source
    assert "bind:file={datasetForm.network}" in page_source
    assert "id=\"implementation-dataset-network\"" in page_source
    assert "onsubmit={submitImplementationDataset}" in page_source
    assert "bind:file={trainingForm.service_disruptions}" in page_source
    assert "bind:file={implementationForm.q_table}" in page_source
    assert "bind:file={comparisonForm.file1}" in page_source
    assert "bind:file={comparisonForm.file2}" in page_source
    assert page_source.count('xAxisLabel="Episode"') == 3
    assert 'yAxisLabel="Total Cost"' in page_source
    assert 'yAxisLabel="Total Reward"' in page_source
    assert "axisXTicks" in series_chart_source
    assert "axisYTicks" in series_chart_source
    assert 'class="x-axis-scale"' in series_chart_source
    assert 'class="y-axis-scale"' in series_chart_source
    assert ".x-axis-scale" in app_css
    assert ".y-axis-scale" in app_css
    assert 'tone="blue"\n\t\t\t\t\t\t\t\temptyLabel' not in page_source
    assert 'tone="amber"\n\t\t\t\t\t\t\t\temptyLabel' not in page_source
    assert "const canControlTraining = $derived(trainingReady || trainingRunning)" in page_source
    assert "payload.error === 'Training already active'" in page_source
    assert "Controls are reconnected" in page_source
    assert "disabled={!canControlTraining || trainingPaused}" in page_source
    assert page_source.count("disabled={!canControlTraining}") == 2
    assert "on:click" not in page_source
    assert "on:submit" not in page_source
    assert "syncSession(payload.session_id)" in page_source
    assert "join_session" in page_source
    assert "CSV Path" not in page_source
    assert "FormData" in api_source
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
