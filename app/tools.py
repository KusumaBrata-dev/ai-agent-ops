"""Function-calling tools agent. Tiap tool = guardrail + audit + return value utk LLM."""
from __future__ import annotations

import datetime as dt
import json

from . import models
from .audit import audit
from .config import (
    ACTION_TIERS,
    PIC_ALLOWLIST,
    RATE_LIMIT,
)


def _tier(action: str) -> str:
    return ACTION_TIERS.get(action, "forbidden")


def _today() -> dt.date:
    return dt.date.today()


# ---------- TOOLS: baca data ----------

def get_production_data(station: str, days: int = 7) -> str:
    """Observe: data produksi N hari terakhir, format pipe utk prompt."""
    cutoff = _today() - dt.timedelta(days=days)
    with models.SessionLocal() as s:
        rows = (
            s.query(models.DailyProduction)
            .filter(models.DailyProduction.station == station,
                    models.DailyProduction.date >= cutoff)
            .order_by(models.DailyProduction.date)
            .all()
        )
    return "\n".join(f"{r.date} | {r.output} | {r.ng_qty} | {r.yield_pct:.1f}" for r in rows)


def get_case_history(station: str, limit: int = 5) -> str:
    """Memory: ringkasan kasus lama stasiun ini."""
    with models.SessionLocal() as s:
        rows = (
            s.query(models.CaseHistory)
            .filter(models.CaseHistory.station == station)
            .order_by(models.CaseHistory.id.desc())
            .limit(limit)
            .all()
        )
    return "\n".join(f"- {r.summary} [hasil: {r.outcome}]" for r in rows)


def get_overdue_tasks() -> list[dict]:
    """Follow-up: task lewat due date dan belum fixed."""
    with models.SessionLocal() as s:
        rows = (
            s.query(models.Task)
            .filter(models.Task.status.in_(("open", "in_progress")),
                    models.Task.due_date < _today())
            .all()
        )
    return [
        {"id": t.id, "case_id": t.case_id, "pic": t.pic, "station": t.station,
         "due_date": str(t.due_date), "description": t.description}
        for t in rows
    ]


# ---------- TOOLS: tulis data ----------

def create_task(case_id: int, pic: str, station: str, description: str, due_days: int = 1) -> dict:
    """Assign. Guardrail: PIC wajib dalam allowlist stasiun + rate limit."""
    if _tier("create_task") == "forbidden":
        raise PermissionError("create_task forbidden by tier")
    if pic not in PIC_ALLOWLIST.get(station, []):
        audit("agent", "guardrail_blocked", tool="create_task", reason="pic_not_in_allowlist",
              pic=pic, station=station)
        raise PermissionError(f"pic_not_in_allowlist: {pic} @ {station}")

    max_per_day = int(RATE_LIMIT.get("max_tasks_per_station_per_day", 1))
    utc_today = dt.datetime.utcnow().date()  # satukan dgn created_at (UTC)
    with models.SessionLocal() as s:
        today_count = (
            s.query(models.Task)
            .filter(models.Task.station == station,
                    models.Task.created_at >= dt.datetime.combine(
                        utc_today, dt.time.min))
            .count()
        )
        if today_count >= max_per_day:
            audit("agent", "guardrail_blocked", tool="create_task", reason="rate_limit",
                  station=station)
            raise PermissionError(f"rate_limit: max {max_per_day} task/hari utk {station}")

        case = s.get(models.Case, case_id)
        if case is None:
            raise ValueError(f"case_id {case_id} tidak ada")
        task = models.Task(
            case_id=case_id, pic=pic, station=station, description=description,
            due_date=_today() + dt.timedelta(days=due_days),
        )
        s.add(task)
        case.status = "assigned"
        s.commit()
        task_id = task.id
        due = task.due_date

    # Notifikasi PIC (best-effort; tanpa token/gagal kirim → task tetap di web UI)
    from .telegram import notify_task
    notify_task(task_id, pic, station, description, due)

    audit("agent", "create_task", task_id=task_id, case_id=case_id, pic=pic,
          station=station, description=description)
    return {"task_id": task_id, "pic": pic, "station": station}


def send_reminder(task_id: int) -> dict:
    """Follow-up reminder (tier auto)."""
    with models.SessionLocal() as s:
        t = s.get(models.Task, task_id)
        if t is None:
            raise ValueError(f"task {task_id} tidak ada")
        if t.status not in ("open", "in_progress"):
            raise ValueError(f"task {task_id} status {t.status}, tidak perlu reminder")
    audit("agent", "send_reminder", task_id=task_id, pic=t.pic)
    return {"task_id": task_id, "reminded_pic": t.pic}


def request_escalation(case_id: int, reason: str) -> dict:
    """Escalate — tier approval: masuk antrean, manusia yang putuskan."""
    if _tier("escalate_to_lead") != "approval":
        raise PermissionError("escalate_to_lead tidak tier approval")
    with models.SessionLocal() as s:
        case = s.get(models.Case, case_id)
        if case is None:
            raise ValueError(f"case {case_id} tidak ada")
        case.status = "escalated"
        s.add(models.Approval(
            action="escalate_to_lead",
            payload=json.dumps({"case_id": case_id, "station": case.station, "reason": reason}),
        ))
        s.commit()
    audit("agent", "request_escalation", case_id=case_id, reason=reason)
    return {"case_id": case_id, "queued": True}


def record_case_outcome(case_id: int, summary: str, outcome: str) -> dict:
    """Verify→Close: tulis memory utk analisis berikutnya."""
    with models.SessionLocal() as s:
        case = s.get(models.Case, case_id)
        if case is None:
            raise ValueError(f"case {case_id} tidak ada")
        s.add(models.CaseHistory(station=case.station, summary=summary, outcome=outcome))
        case.status = "closed"
        s.commit()
    audit("agent", "record_case_outcome", case_id=case_id, outcome=outcome)
    return {"case_id": case_id, "memory_saved": True}


# Registry — tampilkan juga di /docs sebagai daftar capability agent.
TOOLS = {
    "get_production_data": get_production_data,
    "get_case_history": get_case_history,
    "get_overdue_tasks": get_overdue_tasks,
    "create_task": create_task,
    "send_reminder": send_reminder,
    "request_escalation": request_escalation,
    "record_case_outcome": record_case_outcome,
}
