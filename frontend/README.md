# AgentScope Web UI

This directory contains the AgentScope official Web UI source adapted for the CNLC local prototype. Upstream origin, commit, license, and local integration notes are in [UPSTREAM.md](./UPSTREAM.md).

For the complete setup, run instructions, and model credential notes, see the [project README](../README.md).

From the repository root:

```sh
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend build
```

The production build is written to `backend/src/cnlc_agent/static/agentscope` and served by FastAPI at `/`. For frontend development, start the backend and run `pnpm --dir frontend dev`; Vite proxies AgentScope API requests to `127.0.0.1:8000`.
