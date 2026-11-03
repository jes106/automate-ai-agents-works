# From Demo to Production: AI agents that don't break

Live demo for a university talk: a **study-planner agent**. A student pastes a professor's message into the n8n chat; a Gemini agent extracts the deadline, reads her calendar through an MCP server, proposes study blocks, and **every calendar write needs her approval** in the chat.

## Architecture
1. **n8n Chat** → message in.
2. **AI Agent** (system prompt `prompts/planner-v1.md`, simple memory) with a **Gemini Flash** chat model.
3. **MCP Client Tool** nodes → `http://campus-mcp:8000/mcp` (READ and WRITE tools split).
4. **Human review** on the write tools: approve/deny in the n8n chat.
5. **`campus-mcp`** (Python 3.12 + FastMCP, streamable HTTP, mock data): writes are idempotent and logged to `mcp_servers/campus/data/outbox.jsonl`.

## Quickstart
```bash
make up        # n8n :5678, MCP server :8000/mcp
make test      # pytest (pip install -r mcp_servers/campus/requirements-dev.txt)
make reset     # restore mock data between rehearsals
```
Then follow [`n8n/BUILD.md`](n8n/BUILD.md) to build the workflow, and [`docs/RUNBOOK.md`](docs/RUNBOOK.md) / [`demo/messages.md`](demo/messages.md) to run the demo.
**Telegram bot variant** (conversational agenda in a Telegram chat, approvals via buttons): see [`n8n/TELEGRAM.md`](n8n/TELEGRAM.md) and the importable `n8n/workflows/study-planner-telegram.json`.

No secrets in this repo: the Gemini key lives only in the n8n credential. "Today" is `DEMO_TODAY` (default 2026-11-03). Caveats on what is unverified: [`n8n/NOTES.md`](n8n/NOTES.md).
