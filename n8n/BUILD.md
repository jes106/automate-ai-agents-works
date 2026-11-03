# Build the workflow by hand in n8n (≈15 min)

Goal: `Chat Trigger → AI Agent (+ Gemini model, memory, MCP tools) ` where **every calendar write needs the student's approval in the n8n chat**.

> n8n's UI changes between versions. Labels below are the ones I expect in a recent n8n (`n8nio/n8n:latest`). Anything marked **(verify)** could not be checked against the current docs when this file was written (see `NOTES.md`) - rehearse it once before the talk.

## 0. Before you start (1 min)
```bash
make up                                  # n8n on :5678, campus-mcp on :8000
curl -s localhost:8000/health    # expect {"ok":true}
```
Open http://localhost:5678 and create the owner account (first run only). Have a Gemini API key ready (https://aistudio.google.com/apikey). Never commit it.

## 1. Credential "Gemini" (2 min)
1. Left sidebar → **Credentials** → **Create credential** (or from the model node later).
2. Search **Google Gemini(PaLM) API** → Continue.
3. Paste the API key. Host: leave default. **Name it exactly `Gemini`**. Save → the green "Connection tested successfully" message should appear.

## 2. New workflow + Chat Trigger (1 min)
1. **Workflows → Create workflow**. Rename it `Study planner`.
2. Click **+ Add first step** → search **Chat Trigger** (`When chat message received`) → add it.
3. Leave defaults (Public off). The **Open chat** button appears at the bottom of the canvas.

## 3. AI Agent (2 min)
1. Click the **+** on the trigger's output → **AI Agent**. 
2. Parameters: **Source for Prompt** = *Connected Chat Trigger Node* (default).
3. **Options → Add option → System Message**. Open `prompts/planner-v1.md`, copy the whole file, paste it into System Message.
4. (Optional but recommended) Options → **Max Iterations** = 15.

## 4. Gemini Chat Model (1 min)
1. On the agent, click the **+** under **Chat Model\***.
2. Choose **Google Gemini Chat Model**.
3. Credential: `Gemini`. Model: pick `gemini-3.8-flash` if present, otherwise the **newest Flash model in the list**. Do not choose a "Pro" model for the live demo (latency).
4. Options → Temperature `0.2`.

## 5. Memory (30 s)
1. On the agent, **+** under **Memory** → **Simple Memory** (Window Buffer Memory).
2. Defaults are fine (Session ID from the chat trigger, context window 5 - raise to `10` so the "denied" turn is remembered).

## 6. MCP Client Tool (2 min)
1. On the agent, **+** under **Tool\*** → search **MCP Client Tool**.
2. **Endpoint**: `http://campus-mcp:8000/mcp`  (container name, not `localhost`).
3. **Server Transport**: *HTTP Streamable*. **Authentication**: *None*.
4. **Tools to Include**: *All* (we split read/write by approval in the next step).
5. Click **Execute step** / open the node: the tool list should show 8 tools: `list_courses, get_syllabus, list_events, find_free_slots, check_clashes, create_study_block, move_event, delete_event`.

## 7. Human approval on the write tools (3 min) **(verify)**
n8n has a "human review for tool calls" feature: the agent pauses before running a tool and asks a human in a channel; *Approve* runs it, *Deny* returns a "denied" result to the agent.

The MCP Client Tool exposes all 8 tools through one node, so the approval must be scoped to the 3 write tools only. Preferred layout - **two MCP Client Tool nodes**:

1. Rename the node from step 6 to `Campus READ`. Set **Tools to Include** = *Selected* → pick `list_courses, get_syllabus, list_events, find_free_slots, check_clashes`.
2. Add a second **MCP Client Tool**, rename `Campus WRITE`, same endpoint/transport, **Tools to Include** = *Selected* → `create_study_block, move_event, delete_event`.
3. Hover over the connection line between `Campus WRITE` and the AI Agent. A **+** (or *"Add human review step"*) should appear on the connector. Click it.
4. Choose the channel **Chat** (the n8n Chat, so the approval appears in the same window as the conversation). If Chat is not offered for your version, see *Troubleshooting → approval not shown*.
5. Configure the approval message so it shows the tool and its parameters. Use an expression such as:
   ```
   The agent wants to run: {{ $tool.name }}
   Parameters:
   {{ JSON.stringify($tool.parameters, null, 2) }}
   ```
   If the node already prints the tool name and parameters by default, keep the default. If the variables above are not accepted, open the expression editor on the message field and pick the tool name / parameters from the left-hand variable list **(verify)**.
6. Leave *Approve* / *Deny* buttons labels as default (`Approve`, `Decline`).

Do the same human-review step on **nothing else**: reads must stay fast.

## 8. Save and test (2 min)
1. **Save** (Ctrl+S). Do NOT activate; the editor's *Open chat* is enough.
2. Click **Open chat** and paste:
   `El parcial de Bases de Datos será el 20 de noviembre a las 10:00. Entran los temas 4 y 5.`
3. Expect: the agent reads the calendar, lists blocks, then an approval card appears in the chat for `create_study_block`. Approve → `make outbox` shows a new line in `outbox.jsonl`.
4. `make reset` between runs. Then follow `demo/messages.md`.

---

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| **MCP "connection refused" / `ECONNREFUSED`** | You used `localhost` (that is the n8n container itself) or the server is down. Use `http://campus-mcp:8000/mcp`. Check `docker compose ps` and `docker compose logs campus-mcp`. From the host: `curl -i localhost:8000/health` should return 200. |
| **404 / "Not found" / session error** | Wrong path. FastMCP streamable HTTP serves **`/mcp`** (no trailing slash needed, never `/sse`, never `/`). Verify: `curl -i -X POST localhost:8000/mcp -H 'Accept: application/json, text/event-stream' -H 'Content-Type: application/json' -d '{}'` gives a JSON-RPC error (path exists); `404` means wrong path. |
| **Transport mismatch** (hangs, 405/406) | Set *Server Transport* = **HTTP Streamable**. *SSE* is the legacy transport and this server does not expose it. |
| **MCP node connects but tools are not listed** | Re-open the node and refresh the tool list. Check *Tools to Include* is not set to *Selected* with nothing selected / *Except* with everything. Confirm with `docker compose logs campus-mcp` that a `tools/list` request arrived. If the server was restarted after you created the node, click out and back in (new MCP session). |
| **Agent answers but never calls tools** | The chat model has no tool-calling (wrong model) or tools are not connected to the Agent's *Tool* input. Use a Gemini Flash chat model; check the connector lines. |
| **Approval not shown** | (1) Your n8n is too old for human review on tool calls: `docker compose pull n8n && make up`. (2) The review step must sit on the *tool → agent* connector, not on the trigger. (3) Chat channel not offered: use the *Open chat* panel of this workflow (not an activated public chat URL) and keep it open; if still absent, use another channel (e.g. Slack/Telegram) only as backup, or the fallback below. (4) The write goes through the READ node: move the tool into `Campus WRITE` and exclude it from READ. |
| **Writes happen without approval** | A write tool is still included in the READ node. Fix the *Tools to Include* lists, then test with message B2 (it must never delete). |
| **Agent retries after Deny** | Re-check that the full `planner-v1.md` was pasted into System Message (rule 4), and memory window ≥ 10. |
| **Gemini 429 / quota** | Free-tier rate limit: wait a minute or use another Flash model; keep a recorded run as backup. |

### Last-resort fallback (weaker - say so on stage)
If human review cannot be made to work before the talk, keep only `Campus READ` connected and present the proposals as text; the agent's writes are then impossible by construction. Do not rely on the prompt alone to gate writes.
