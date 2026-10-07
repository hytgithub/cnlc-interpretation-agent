# AgentScope Frontend

This directory vendors the official AgentScope example Web UI frontend.

- Upstream repository: https://github.com/agentscope-ai/agentscope
- Upstream path: `examples/web_ui/frontend`
- Source revision: `8a97dcb7`
- License: Apache-2.0 (see `LICENSE.agentscope`)

The frontend talks to the AgentScope Service REST and SSE APIs. The Vite development server proxies those API paths to the local FastAPI service on port 8000. A production build writes its assets into the Python package so FastAPI can serve the SPA on the same origin.

The AgentScope UI does not create or choose a paid model automatically. Configure a provider credential and model through its own interface before using natural-language chat. Credentials entered there are sent to this local service and stored by AgentScope; no environment key is copied into the application.
