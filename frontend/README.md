# LAHSO SvelteKit Frontend

This is the SvelteKit 5 frontend for the LAHSO Flask API.

## Developing

Run the Flask API from the repository root:

```sh
python scripts/run_web.py
```

Then start the frontend from this directory:

```sh
bun --bun run dev
```

Vite proxies `/api` and `/socket.io` to `http://127.0.0.1:5001`, which is the
port used by the Flask runner. The `dev` script intentionally launches Vite
with Node, even when invoked through Bun, because Vite's WebSocket proxy depends
on Node socket APIs that are not fully compatible with Bun's dev-server runtime.

## Checking And Building

```sh
bun --bun run check
bun --bun run build
```

If Bun is not available on your shell path, the existing Node installation can
still run the same package scripts with `npm run check`, `npm run build`, and
`npm run dev`.
