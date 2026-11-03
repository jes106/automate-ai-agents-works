# Runbook: zero to demo

1. Prerequisites: Docker + Docker Compose, `make`, a Gemini API key (do not paste it anywhere but the n8n credential form).
2. `cp .env.example .env` (optional; only sets `DEMO_TODAY`, default `2026-11-03`).
3. `make up` - builds `campus-mcp`, starts n8n. Check `curl -s localhost:8000/health` → `{"ok":true}`.
4. Open http://localhost:5678, create the owner account (first run only).
5. Create the credential **Gemini** (Credentials → Create → *Google Gemini(PaLM) API* → paste key → name `Gemini`).
6. Build the workflow following `n8n/BUILD.md` (≈15 min). There is no import JSON (see `n8n/NOTES.md`).
7. `make reset` - restores the calendar and empties the outbox.
8. Second terminal on the projector: `make outbox`.
9. Run **B1**, **B2**, **B3** from `demo/messages.md` (`make reset` between them if you want clean state).
10. After the talk: `make down` (n8n workflow/credential persist in the `n8n_data` volume).

**Reset between rehearsals (1 line):** `make reset` (or `curl -X POST localhost:8000/reset`). Also start a new chat session in n8n (clear memory) - e.g. refresh the chat panel.

Pre-talk checklist: font size up (Ctrl +), run B1–B3 once, rehearse the Deny click, have a screen recording as backup, tests green (`make test`).
