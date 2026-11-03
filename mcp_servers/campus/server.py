"""Campus MCP server (FastMCP, streamable HTTP). Endpoint: http://<host>:8000/mcp"""
from __future__ import annotations

import os

from fastmcp import FastMCP
from starlette.responses import JSONResponse

from store import STORE, parse_dt

mcp = FastMCP("campus")
W = "WRITE TOOL - REQUIRES HUMAN APPROVAL. "


@mcp.tool
def list_courses() -> list[dict]:
    """List the student's courses (id, name, professor, number of syllabus topics)."""
    return STORE.courses()


@mcp.tool
def get_syllabus(course_id: str) -> dict:
    """Get the numbered syllabus topics of a course. course_id is one of BD, REDES, IA, IS, EST."""
    c = STORE.course(course_id)
    if not c:
        return {"ok": False, "error": f"unknown course_id {course_id!r}"}
    return {"ok": True, "course_id": c["id"], "name": c["name"], "syllabus": c["syllabus"]}


@mcp.tool
def list_events(start: str, end: str) -> list[dict]:
    """List calendar events (classes, personal, exams, study blocks) between start and end.
    Dates are YYYY-MM-DD (end inclusive) or ISO datetimes, Europe/Madrid."""
    return [STORE.public(e) for e in STORE.events(parse_dt(start), parse_dt(end, end_of_day=True))]


@mcp.tool
def find_free_slots(start: str, end: str, duration_min: int = 50,
                    earliest: str = "09:00", latest: str = "21:30") -> list[dict]:
    """Find free, non-overlapping slots of duration_min minutes between start and end
    (YYYY-MM-DD, end inclusive), only within earliest-latest each day. Returns at most 40."""
    return STORE.free_slots(parse_dt(start), parse_dt(end, end_of_day=True), duration_min, earliest, latest)


@mcp.tool
def check_clashes(start: str, end: str) -> list[dict]:
    """Return the events overlapping the interval start-end (ISO datetimes). Empty list = no clash."""
    return STORE.clashes(parse_dt(start), parse_dt(end))


@mcp.tool(description=W + "Create a study block in the calendar. idempotency_key must be unique per intended action.")
def create_study_block(course_id: str, start: str, end: str, topic: str, idempotency_key: str) -> dict:
    return STORE.create_study_block(course_id, start, end, topic, idempotency_key)


@mcp.tool(description=W + "Move a one-off event (e.g. a study block) to a new time.")
def move_event(event_id: str, new_start: str, new_end: str, idempotency_key: str) -> dict:
    return STORE.move_event(event_id, new_start, new_end, idempotency_key)


@mcp.tool(description=W + "Delete a one-off event from the calendar.")
def delete_event(event_id: str, idempotency_key: str) -> dict:
    return STORE.delete_event(event_id, idempotency_key)


# Not an MCP tool on purpose: the agent must not be able to reset the data.
@mcp.custom_route("/reset", methods=["POST"])
async def reset(request):
    STORE.reset()
    return JSONResponse({"ok": True, "message": "data restored, outbox cleared"})


@mcp.custom_route("/health", methods=["GET"])
async def health(request):
    return JSONResponse({"ok": True})


if __name__ == "__main__":
    # FastMCP's default streamable-HTTP path is /mcp
    mcp.run(transport="streamable-http", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
