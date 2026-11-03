# What is verified and what is not

## `workflows/study-planner-telegram.json` (Telegram bot) - checked against n8n package source
Node types, versions and parameter names were read from the published npm packages (`@n8n/n8n-nodes-langchain` 2.46.4, `n8n-nodes-base` 2.15.1, `n8n-core`) and the n8n repo (`packages/cli/src/tool-generation/hitl-tools.ts`), not guessed:
- `telegramTrigger` 1.2 (`updates`, `additionalFields.chatIds/userIds`), `telegram` 1.2 (`resource`, `operation`, `chatId`, `text`, `additionalFields.appendAttribution`).
- `agent` 3.1 (`promptType: define`, `text`, `options.systemMessage`, `options.maxIterations`), `lmChatGoogleGemini` 1.2 (`modelName`, default `models/gemini-3-flash-preview`), `memoryBufferWindow` 1.2 (`sessionIdType: customKey`, `sessionKey`, `contextWindowLength`).
- `mcpClientTool` 1.4 (`endpointUrl`, `serverTransport: httpStreamable`, `authentication`, `include: selected`, `includeTools`).
- Human review = the auto-generated `n8n-nodes-base.telegramHitlTool` (from Telegram's *Send and Wait*): **gated tools → HITL node → Agent** (`ai_tool` connections); the default message uses `{{ $tool.name }}` / `{{ $tool.parameters }}`; denial returns "User rejected the tool call ... STOP" to the agent.

**Not verified (no n8n instance could run in the sandbox: no Docker daemon):**
- The JSON was never imported into a running n8n. Expect to re-select credentials; if a node shows as unknown, rebuild it by hand (the structure above is the recipe).
- The `includeTools` names are valid only if the MCP server lists them (it does; tested over HTTP).
- The Gemini model is `models/gemini-3-flash-preview` (newest Flash default in the package); `gemini-3.8-flash` from the brief is not something I could confirm. Change it in the node if your list has a newer Flash.
- The `HitlTool` variants are generated when n8n loads nodes; if your n8n is older than that feature the node will not exist (use `n8nio/n8n:latest`).
- The credential ids in the JSON are placeholders (names only).

## `BUILD.md` (n8n Chat version, built by hand)
Still hand-built; the Chat HITL step and `$tool.*` message variables are consistent with the sources above. It needs Chat Trigger *Response Mode = Using Response Nodes*. No importable JSON for this variant.

## Server
FastMCP 4.1.6: `http://localhost:8000/mcp`, tested with `Host: campus-mcp:8000`; pytest passes. Compose files not run (no Docker daemon).
