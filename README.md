# LAHSO

Learning Assisted Hybrid Simulation-Optimization for synchromodal transport under disruptions.

## Repository Layout

```text
AI4Resilience-GUI/
  src/lahso/           Python package
  data/
    raw/               source datasets used for local runs
    processed/         generated possible-path and k-best datasets
  artifacts/
    models/            q-tables and checkpoints
    metrics/           training metrics and summaries
    runs/              simulation outputs and detailed logs
  docs/                architecture notes and supporting documents
  notebooks/           exploratory notebooks
  scripts/             operational helper scripts
  templates/           current Flask HTML assets
  tests/               smoke tests
```

## Current Conventions

- Treat `src/lahso/` as the only source-of-truth for Python code.
- Treat `data/raw/` as input data copied into the workspace.
- Treat `data/processed/` as reproducible derived data.
- Treat `artifacts/` as disposable generated output.
- Keep the repository root limited to project config, docs, and a few entry files.

## Running

1. Install dependencies with `uv sync`.
2. Place local datasets in `data/raw/`.
3. If you use Gurobi credentials, create `.env` from `.env.example`.
4. Launch the Gradio UI with `uv run ui`.
5. Launch the Flask web app with `python scripts/run_web.py`.

## Smoke Tests

Run the repository smoke suite with:

```bash
pytest tests/test_smoke_repo_layout.py tests/test_smoke_web_backend.py -q
```

The smoke tests verify:

- default path resolution for the reorganized repository
- generation of processed path data
- loading `ModelInput` end-to-end from the new layout
- Flask app creation, the current HTML shell, default config JSON, and Socket.IO
  session creation

## Notes For Further Cleanup

- The two frontend implementations were intentionally left structurally separate for now.
- `templates/` remains at the root because the current Flask app still serves from there.
- `policy_function_improved.py` and `simulation_module_improved.py` are still duplication candidates for a later consolidation pass.
