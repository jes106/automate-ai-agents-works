.PHONY: up down reset test outbox

up:       ## build and start n8n (:5678) and campus-mcp (:8000/mcp)
	docker compose up -d --build

down:     ## stop everything (n8n data volume is kept)
	docker compose down

reset:    ## restore calendar data + empty outbox (between rehearsals)
	curl -fsS -X POST http://localhost:8000/reset && echo

test:     ## run the MCP server tests (pip install -r mcp_servers/campus/requirements-dev.txt)
	cd mcp_servers/campus && python -m pytest -q

outbox:   ## watch the calendar writes live (second terminal)
	tail -f mcp_servers/campus/data/outbox.jsonl
