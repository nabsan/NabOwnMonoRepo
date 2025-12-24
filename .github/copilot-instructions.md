# Copilot instructions for NabOwnMonoRepo

This repository contains several small Python web utilities and an MCP/Gradio-based toolset. Keep guidance focused and concrete so an AI coding agent can be productive immediately.

**Architecture (big picture)**
- Multiple small Flask/Gradio apps live under `apps/` (each app has `app.py`, `templates/`, `static/`). Example: [apps/markdSlide/app.py](apps/markdSlide/app.py#L1-L40).
- `nabmcp` is an MCP/Gradio client and orchestrator. It connects to local MCP servers in `apps/nabmcp/server/` and exposes tools via `mcp.tool()` (see [apps/nabmcp/server/mcp_rag_qdrant.py](apps/nabmcp/server/mcp_rag_qdrant.py#L1-L40)).
- Data flows:
  - `web2markd` fetches webpages → extracts main content → converts to Markdown → writes to `apps/web2markd/downloads/` ([apps/web2markd/app.py](apps/web2markd/app.py#L1-L40)).
  - `markdSlide` reads Markdown (uploads/) → splits into slides using `---` and `<!-- timing: N -->` comments (see `parse_markdown_slides` in [apps/markdSlide/app.py](apps/markdSlide/app.py#L1-L80)).
  - `nabmcp` RAG server uses Ollama for embeddings and Qdrant for vector storage; see env vars in [apps/nabmcp/server/mcp_rag_qdrant.py](apps/nabmcp/server/mcp_rag_qdrant.py#L1-L40).

**Critical developer workflows & commands**
- Run Flask apps (examples):
  - `export FLASK_APP=apps/markdSlide/app.py && flask run --port 5001` (or use the same pattern for other apps).
  - If using the CLI, run loader scripts directly with `python`: see `apps/nabmcp/scripts` usage below.
- Load documents into Qdrant (document loaders): read [apps/nabmcp/README.md](apps/nabmcp/README.md#L1) for examples. Primary commands look like:
  - `python apps/nabmcp/scripts/load_ducuments_to_qdrant.py /path/to/doc.pdf --chunk-size 800 --tags "manual"`
  - `python apps/nabmcp/scripts/batch_load_documents.py /path/to/docs/ --recursive`
  - Note: there is a filename typo: `load_ducuments_to_qdrant.py` (script lives at `apps/nabmcp/scripts/load_ducuments_to_qdrant.py`).

**Project-specific conventions & patterns**
- Small, self-contained apps: each app keeps static templates under `templates/` and `static/` (CSS/JS). Follow existing folder layout when adding new apps.
- Optional dependency pattern: many modules attempt imports and set a flag (e.g., `REPORTLAB_AVAILABLE`, `REQUESTS_AVAILABLE`, `BS4_AVAILABLE`) and fall back; prefer following that pattern for optional features.
- Explicit debug logging: functions contain `print('DEBUG: ...')` statements used across apps for quick troubleshooting. Use the same style when adding debug messages.
- Markdown slide timing: timing is embedded as HTML comments `<!-- timing: 120 -->` — parsing logic is in `parse_markdown_slides` ([apps/markdSlide/app.py](apps/markdSlide/app.py#L1-L80)).

**Integration points & external services**
- Ollama (chat/embeddings) and Qdrant are primary external services:
  - Env vars: `OLLAMA_HOST`, `QDRANT_HOST`, `QDRANT_COLLECTION`, `EMBEDDING_MODEL` (see [apps/nabmcp/server/mcp_rag_qdrant.py](apps/nabmcp/server/mcp_rag_qdrant.py#L1-L40) and [apps/nabmcp/README.md](apps/nabmcp/README.md#L1)).
  - Defaults in code are often set to internal network addresses (e.g. `http://172.21.32.1:11434`) — update these when deploying to different environments.
- File storage conventions:
  - Uploads: `apps/markdSlide/uploads/`
  - Downloads/exports: `apps/web2markd/downloads/`
  - Scripts write to the `uploads`/`downloads` folders relative to each app.

**Errors, gotchas & quick checks**
- Confirm optional dependencies before running features (e.g., `pip install reportlab` for PDF export in `markdSlide`). See checks near the top of each `app.py`.
- MCP servers: `nabmcp/app.py` spawns stdio MCP client sessions to each Python file in `apps/nabmcp/server/` — start those server scripts directly to expose their tools. Example server: [apps/nabmcp/server/mcp_rag_qdrant.py](apps/nabmcp/server/mcp_rag_qdrant.py#L1-L40).
- Watch for filename mismatch: `load_ducuments_to_qdrant.py` vs README references to `load_documents_to_qdrant.py`.

**When editing code**
- Keep changes minimal and local to the app you modify; patterns favor self-contained services.
- New long-running services should follow the MCP server pattern (expose `mcp.tool()` functions and accept simple JSON-friendly inputs/outputs).

If anything here is unclear or you want more examples (e.g., run scripts, env setup, or more code snippets), tell me which area to expand and I will iterate.
