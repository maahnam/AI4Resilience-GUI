
## Smoke Tests

Run the repository smoke suite with:

```bash
pytest tests/test_smoke_repo_layout.py tests/test_smoke_web_backend.py tests/test_smoke_frontend_refactor.py -q
```

The smoke tests verify:

- default path resolution for the reorganized repository
- generation of processed path data
- loading `ModelInput` end-to-end from the new layout
- Flask app creation, the SvelteKit handoff page, default config JSON, and Socket.IO
  session creation
- SvelteKit 5 frontend contract, Bun adapter configuration, Flask API client
  endpoints, and retention of the Gradio UI modules

## Notes For Further Cleanup

- The Gradio and SvelteKit frontends are intentionally left structurally separate for now.
- `templates/` remains at the root because Flask still serves a small fallback page.
- `policy_function_improved.py` and `simulation_module_improved.py` are still duplication candidates for a later consolidation pass.
