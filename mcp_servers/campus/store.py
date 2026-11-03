"""Calendar state + logic for the campus demo. No MCP imports: easy to test.

All datetimes are naive and mean Europe/Madrid local time ("2026-11-04T16:00").
Weekly items (classes, gym, job) are expanded on the fly; one-off events
(exam, study blocks) live in memory and can be moved/deleted.
"""
from __future__ import annotations

import copy
import json
import os
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = Path(__file__).parent
DATA_FILE = BASE / "data" / "campus.json"
TZ = ZoneInfo("Europe/Madrid")


def outbox_path() -> Path:
    return Path(os.environ.get("OUTBOX_PATH", BASE / "data" / "outbox.jsonl"))


def today() -> date:
    return date.fromisoformat(os.environ.get("DEMO_TODAY", "2026-11-03"))


def parse_dt(value: str, end_of_day: bool = False) -> datetime:
    """Accept 'YYYY-MM-DD' or ISO datetime; tz-aware input is converted to Madrid."""
    value = value.strip()
    if len(value) == 10:
        d = date.fromisoformat(value)
        return datetime.combine(d, time.max.replace(microsecond=0) if end_of_day else time.min)
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is not None:
        dt = dt.astimezone(TZ).replace(tzinfo=None)
    return dt


def fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M")


def _hm(day: date, hm: str) -> datetime:
    h, m = hm.split(":")
    return datetime.combine(day, time(int(h), int(m)))


class Store:
    def __init__(self) -> None:
        self.reset(clear_outbox=False)

    # ---- lifecycle -------------------------------------------------
    def reset(self, clear_outbox: bool = True) -> None:
        self.data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        self.one_off = copy.deepcopy(self.data["one_off"])
        self.keys: dict[str, dict] = {}
        self.counter = 0
        if clear_outbox:
            p = outbox_path()
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("", encoding="utf-8")

    # ---- reads -----------------------------------------------------
    def courses(self) -> list[dict]:
        return [{k: c[k] for k in ("id", "name", "professor")} | {"topics": len(c["syllabus"])}
                for c in self.data["courses"]]

    def course(self, course_id: str) -> dict | None:
        cid = course_id.strip().upper()
        return next((c for c in self.data["courses"] if c["id"].upper() == cid), None)

    def events(self, start: datetime, end: datetime) -> list[dict]:
        """All events overlapping [start, end), sorted."""
        out: list[dict] = []
        day = start.date()
        while day <= end.date():
            for w in self.data["weekly"]:
                if w["weekday"] == day.weekday():
                    s, e = _hm(day, w["start"]), _hm(day, w["end"])
                    out.append({"id": f'{w["id"]}@{day.isoformat()}', "title": w["title"],
                                "kind": w["kind"], "start": s, "end": e, "recurring": True,
                                "course_id": w.get("course_id")})
            day += timedelta(days=1)
        for ev in self.one_off:
            out.append({**ev, "start": datetime.fromisoformat(ev["start"]),
                        "end": datetime.fromisoformat(ev["end"]), "recurring": False})
        out = [e for e in out if e["start"] < end and e["end"] > start]
        out.sort(key=lambda e: (e["start"], e["id"]))
        return out

    @staticmethod
    def public(ev: dict) -> dict:
        return {**ev, "start": fmt(ev["start"]), "end": fmt(ev["end"])}

    def free_slots(self, start: datetime, end: datetime, duration_min: int,
                   earliest: str = "09:00", latest: str = "21:30",
                   break_min: int = 10, limit: int = 40) -> list[dict]:
        """Non-overlapping slots of duration_min inside [earliest, latest] each day."""
        if duration_min <= 0:
            raise ValueError("duration_min must be > 0")
        dur = timedelta(minutes=duration_min)
        slots: list[dict] = []
        day = start.date()
        while day <= end.date() and len(slots) < limit:
            lo = max(_hm(day, earliest), start)
            hi = min(_hm(day, latest), end)
            busy = [(e["start"], e["end"]) for e in self.events(lo, hi)] if lo < hi else []
            cursor = lo
            for bs, be in sorted(busy) + [(hi, hi)]:
                while cursor + dur <= min(bs, hi):
                    slots.append({"start": fmt(cursor), "end": fmt(cursor + dur)})
                    cursor += dur + timedelta(minutes=break_min)
                    if len(slots) >= limit:
                        return slots
                cursor = max(cursor, be)
            day += timedelta(days=1)
        return slots

    def clashes(self, start: datetime, end: datetime) -> list[dict]:
        return [self.public(e) for e in self.events(start, end)]

    # ---- writes (idempotent) ---------------------------------------
    def _commit(self, key: str, action: str, payload: dict, result: dict) -> dict:
        self.keys[key] = result
        line = {"ts": datetime.now(TZ).isoformat(timespec="seconds"), "action": action,
                "idempotency_key": key, "payload": payload, "result": result}
        p = outbox_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
        return result

    def create_study_block(self, course_id: str, start: str, end: str, topic: str, key: str) -> dict:
        if key in self.keys:
            return {**self.keys[key], "idempotent_replay": True}
        c = self.course(course_id)
        if not c:
            return {"ok": False, "error": f"unknown course_id {course_id!r}"}
        s, e = parse_dt(start), parse_dt(end)
        if e <= s:
            return {"ok": False, "error": "end must be after start"}
        clash = self.clashes(s, e)
        if clash:
            return {"ok": False, "error": "clash", "clashes": clash}
        self.counter += 1
        ev = {"id": f"blk-{self.counter:04d}", "title": f'Estudio {c["name"]}: {topic}',
              "kind": "study", "course_id": c["id"], "start": fmt(s), "end": fmt(e)}
        self.one_off.append(ev)
        return self._commit(key, "create_study_block", {"course_id": c["id"], "start": fmt(s),
                           "end": fmt(e), "topic": topic}, {"ok": True, "event": ev})

    def _find_one_off(self, event_id: str) -> dict | None:
        return next((e for e in self.one_off if e["id"] == event_id), None)

    def move_event(self, event_id: str, new_start: str, new_end: str, key: str) -> dict:
        if key in self.keys:
            return {**self.keys[key], "idempotent_replay": True}
        ev = self._find_one_off(event_id)
        if not ev:
            return {"ok": False, "error": f"event {event_id!r} not found or recurring (only one-off events can be moved)"}
        s, e = parse_dt(new_start), parse_dt(new_end)
        if e <= s:
            return {"ok": False, "error": "end must be after start"}
        clash = [c for c in self.clashes(s, e) if c["id"] != event_id]
        if clash:
            return {"ok": False, "error": "clash", "clashes": clash}
        ev["start"], ev["end"] = fmt(s), fmt(e)
        return self._commit(key, "move_event", {"event_id": event_id, "new_start": fmt(s),
                           "new_end": fmt(e)}, {"ok": True, "event": dict(ev)})

    def delete_event(self, event_id: str, key: str) -> dict:
        if key in self.keys:
            return {**self.keys[key], "idempotent_replay": True}
        ev = self._find_one_off(event_id)
        if not ev:
            return {"ok": False, "error": f"event {event_id!r} not found or recurring (only one-off events can be deleted)"}
        self.one_off.remove(ev)
        return self._commit(key, "delete_event", {"event_id": event_id}, {"ok": True, "deleted": event_id})


STORE = Store()
