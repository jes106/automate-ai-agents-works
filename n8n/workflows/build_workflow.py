"""Generate study-planner-telegram.json from prompts/planner-telegram-v1.md.

    python3 n8n/workflows/build_workflow.py

Node types/parameters were checked against the n8n packages' source (see n8n/NOTES.md).
Credentials are referenced by name only; pick them again after import.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
prompt = (ROOT / "prompts" / "planner-telegram-v1.md").read_text(encoding="utf-8")

MCP_URL = "http://campus-mcp:8000/mcp"
CHAT_ID = "={{ $('Telegram Trigger').item.json.message.chat.id }}"
READ = ["list_courses", "get_syllabus", "list_events", "find_free_slots", "check_clashes"]
WRITE = ["create_study_block", "move_event", "delete_event"]


def mcp(name, tools, pos):
    return {"parameters": {"endpointUrl": MCP_URL, "serverTransport": "httpStreamable",
                           "authentication": "none", "include": "selected", "includeTools": tools},
            "type": "@n8n/n8n-nodes-langchain.mcpClientTool", "typeVersion": 1.4,
            "position": pos, "name": name}


nodes = [
    {"parameters": {"updates": ["message"], "additionalFields": {}},
     "type": "n8n-nodes-base.telegramTrigger", "typeVersion": 1.2, "position": [0, 0],
     "name": "Telegram Trigger", "webhookId": "7b1c2f0e-5c3a-4a53-9a43-5f6c1d0a0001",
     "credentials": {"telegramApi": {"name": "Telegram Bot"}}},
    {"parameters": {"promptType": "define", "text": "={{ $json.message.text }}",
                    "options": {"systemMessage": prompt, "maxIterations": 15}},
     "type": "@n8n/n8n-nodes-langchain.agent", "typeVersion": 3.1, "position": [320, 0],
     "name": "AI Agent"},
    {"parameters": {"modelName": "models/gemini-3-flash-preview", "options": {"temperature": 0.2}},
     "type": "@n8n/n8n-nodes-langchain.lmChatGoogleGemini", "typeVersion": 1.2,
     "position": [120, 260], "name": "Google Gemini Chat Model",
     "credentials": {"googlePalmApi": {"name": "Gemini"}}},
    {"parameters": {"sessionIdType": "customKey", "sessionKey": CHAT_ID, "contextWindowLength": 12},
     "type": "@n8n/n8n-nodes-langchain.memoryBufferWindow", "typeVersion": 1.2,
     "position": [320, 260], "name": "Simple Memory"},
    mcp("Campus READ", READ, [520, 260]),
    mcp("Campus WRITE", WRITE, [520, 480]),
    {"parameters": {
        "chatId": CHAT_ID,
        "message": "=✋ El agente quiere ejecutar: {{ $tool.name }}\n\nParámetros:\n{{ $tool.parameters }}",
        "approvalOptions": {"values": {"approvalType": "double",
                                       "approveLabel": "✅ Aprobar", "disapproveLabel": "❌ Rechazar"}}},
     "type": "n8n-nodes-base.telegramHitlTool", "typeVersion": 1.2, "position": [720, 380],
     "name": "Human review (Telegram)", "credentials": {"telegramApi": {"name": "Telegram Bot"}}},
    {"parameters": {"resource": "message", "operation": "sendMessage", "chatId": CHAT_ID,
                    "text": "={{ $json.output }}", "additionalFields": {"appendAttribution": False}},
     "type": "n8n-nodes-base.telegram", "typeVersion": 1.2, "position": [680, 0],
     "name": "Send reply", "credentials": {"telegramApi": {"name": "Telegram Bot"}}},
]


def link(kind, target):
    return {kind: [[{"node": target, "type": kind, "index": 0}]]}


connections = {
    "Telegram Trigger": link("main", "AI Agent"),
    "AI Agent": link("main", "Send reply"),
    "Google Gemini Chat Model": link("ai_languageModel", "AI Agent"),
    "Simple Memory": link("ai_memory", "AI Agent"),
    "Campus READ": link("ai_tool", "AI Agent"),
    # gated tools feed the HITL node, and the HITL node feeds the agent
    "Campus WRITE": link("ai_tool", "Human review (Telegram)"),
    "Human review (Telegram)": link("ai_tool", "AI Agent"),
}

wf = {"name": "Study planner (Telegram)", "nodes": nodes, "connections": connections,
      "active": False, "settings": {"executionOrder": "v1"}}
out = ROOT / "n8n" / "workflows" / "study-planner-telegram.json"
out.write_text(json.dumps(wf, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print("wrote", out)
