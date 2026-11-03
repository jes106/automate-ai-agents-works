# Notes on what is (not) verified

- **`n8n/workflows/study-planner.json` is intentionally NOT included.** While preparing this repo the sandbox could not reach `docs.n8n.io`, so node type names, parameter names and the human-review wiring could not be confirmed against the current docs. A guessed export would likely fail on import or silently drop the approval gate - the worst failure for this talk. `BUILD.md` is the supported path.
- **Verify before the talk (marked "(verify)" in BUILD.md):**
  - Exact label/location of the *human review* step on the tool connector, and that the **Chat** channel is offered for it.
  - Whether it works with the **MCP Client Tool** node in your n8n version (this repo uses two MCP nodes, READ and WRITE, so approval only covers writes).
  - Expression variables for tool name/parameters in the approval message (`$tool.name`, `$tool.parameters` are a guess; the default message may already show them).
  - MCP Client Tool option names (*Server Transport = HTTP Streamable*, *Tools to Include*).
  - Model name: `gemini-3.8-flash` was requested; pick the newest Flash in the dropdown.
- **Tip once it works:** export it (workflow menu → Download) and commit the JSON as `n8n/workflows/study-planner.json`; it is then a verified import for next time. Credentials are not included in exports.
- **Verified here:** the MCP server (FastMCP 4.1.6) answers on `http://localhost:8000/mcp` with streamable HTTP, also with `Host: campus-mcp:8000`; `/sse` is 404; 8 tools listed; pytest passes. Docker/compose files were not run in the sandbox.
