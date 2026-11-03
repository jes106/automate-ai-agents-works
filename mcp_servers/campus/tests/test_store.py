import json
from datetime import datetime

import pytest

import store as st
from store import STORE, parse_dt


@pytest.fixture(autouse=True)
def fresh(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTBOX_PATH", str(tmp_path / "outbox.jsonl"))
    STORE.reset()


def overlaps(a, b):
    return a[0] < b[1] and b[0] < a[1]


def test_free_slots_never_overlap_events_and_respect_window():
    s, e = parse_dt("2026-11-03"), parse_dt("2026-11-20", end_of_day=True)
    slots = STORE.free_slots(s, e, 50, limit=500)
    assert slots
    events = [(x["start"], x["end"]) for x in STORE.events(s, e)]
    prev_end = None
    for sl in slots:
        a, b = datetime.fromisoformat(sl["start"]), datetime.fromisoformat(sl["end"])
        assert (b - a).seconds == 50 * 60
        assert "09:00" <= a.strftime("%H:%M") and b.strftime("%H:%M") <= "21:30"
        assert not any(overlaps((a, b), ev) for ev in events), sl
        if prev_end and prev_end.date() == a.date():
            assert a >= prev_end  # slots do not overlap each other
        prev_end = b


def test_free_slots_skip_gym_and_exam():
    slots = STORE.free_slots(parse_dt("2026-11-03"), parse_dt("2026-11-03", True), 50)
    starts = [s["start"][11:] for s in slots]
    assert "19:00" not in starts and all(not ("19:00" < t < "20:30") for t in starts)
    exam_day = STORE.free_slots(parse_dt("2026-11-12"), parse_dt("2026-11-12", True), 50)
    assert all(not (s["start"][11:] < "12:00" and s["end"][11:] > "10:00") for s in exam_day)


def test_check_clashes():
    assert [c["id"] for c in STORE.clashes(parse_dt("2026-11-12T09:30"), parse_dt("2026-11-12T10:30"))] \
        == ["cls-redes-jue@2026-11-12", "exam-ia"]
    assert STORE.clashes(parse_dt("2026-11-03T16:00"), parse_dt("2026-11-03T16:50")) == []
    # touching boundaries are not clashes
    assert STORE.clashes(parse_dt("2026-11-03T13:30"), parse_dt("2026-11-03T14:00")) == []


def test_create_block_clash_rejected():
    r = STORE.create_study_block("BD", "2026-11-03T09:00", "2026-11-03T09:50", "SQL", "k0")
    assert not r["ok"] and r["error"] == "clash"


def test_create_block_idempotent_and_outbox():
    args = ("BD", "2026-11-04T16:00", "2026-11-04T16:50", "Tema 4", "k1")
    r1 = STORE.create_study_block(*args)
    r2 = STORE.create_study_block(*args)
    assert r1["ok"] and r2["event"] == r1["event"] and r2["idempotent_replay"]
    assert len([e for e in STORE.one_off if e["kind"] == "study"]) == 1
    lines = st.outbox_path().read_text().splitlines()
    assert len(lines) == 1 and json.loads(lines[0])["action"] == "create_study_block"
    # the block now clashes
    assert STORE.clashes(parse_dt("2026-11-04T16:00"), parse_dt("2026-11-04T16:50"))


def test_move_and_delete_idempotent():
    ev = STORE.create_study_block("BD", "2026-11-04T16:00", "2026-11-04T16:50", "T4", "a")["event"]
    m = STORE.move_event(ev["id"], "2026-11-04T17:00", "2026-11-04T17:50", "b")
    assert m["ok"] and m["event"]["start"] == "2026-11-04T17:00"
    assert STORE.move_event(ev["id"], "2026-11-05T17:00", "2026-11-05T17:50", "b")["idempotent_replay"]
    d1 = STORE.delete_event(ev["id"], "c")
    d2 = STORE.delete_event(ev["id"], "c")
    assert d1["ok"] and d2["idempotent_replay"]
    assert len(st.outbox_path().read_text().splitlines()) == 3


def test_cannot_delete_recurring_and_reset():
    assert not STORE.delete_event("cls-bd-lun@2026-11-09", "z")["ok"]
    STORE.create_study_block("BD", "2026-11-04T16:00", "2026-11-04T16:50", "T4", "a")
    STORE.reset()
    assert st.outbox_path().read_text() == "" and [e["id"] for e in STORE.one_off] == ["exam-ia"]
    assert STORE.create_study_block("BD", "2026-11-04T16:00", "2026-11-04T16:50", "T4", "a")["ok"]


def test_tool_descriptions_flag_writes():
    import asyncio
    from server import mcp
    tools = asyncio.run(mcp.list_tools())
    d = {t.name: t.description for t in tools}
    for n in ("create_study_block", "move_event", "delete_event"):
        assert d[n].startswith("WRITE TOOL - REQUIRES HUMAN APPROVAL.")
    assert not d["list_events"].startswith("WRITE")
