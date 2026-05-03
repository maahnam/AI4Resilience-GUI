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
    svelte_config = (FRONTEND_ROOT / "svelte.config.js").read_text()
    vite_config = (FRONTEND_ROOT / "vite.config.ts").read_text()

    assert "$state(" in page_source
    assert "$derived(" in page_source
    assert "on:click" not in page_source
    assert "on:submit" not in page_source
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
