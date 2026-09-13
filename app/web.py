"""UI approval + endpoint PIC + status. HTML sederhana, tanpa JS framework."""
from __future__ import annotations

import datetime as dt
import json

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse

from . import models, tools
from .audit import audit
from .config import PIC_ALLOWLIST

router = APIRouter()

_PAGE = """<!doctype html><html lang="id"><head><meta charset="utf-8">
<title>Agent Ops</title><style>
body{font-family:system-ui;margin:2rem;max-width:60rem}
table{border-collapse:collapse;width:100%;margin-bottom:2rem}
td,th{border:1px solid #ccc;padding:.4rem .6rem;text-align:left;font-size:.9rem}
.app{background:#fff8e7} .rej{background:#fde7e7}
form{display:inline}
button{padding:.2rem .8rem;cursor:pointer}
h2{margin-top:2rem}
</style></head><body>
<h1>AI Agent Ops — Panel</h1>
<h2>Approval Pending (aksi sensitif menunggu manusia)</h2>
{approval_rows}
<h2>Task PIC</h2>
{task_rows}
<h2>Case</h2>
{case_rows}
<h2>Audit Log (20 terakhir)</h2>
{audit_rows}
</body></html>"""


def _rows(items: list[str]) -> str:
    return "<table>" + "".join(items) + "</table>" if items else "<p>(kosong)</p>"


@router.get("/", response_class=HTMLResponse)
def dashboard():
    with models.SessionLocal() as s:
        approvals = s.query(models.Approval).filter_by(status="pending").all()
        tasks = s.query(models.Task).order_by(models.Task.id.desc()).limit(20).all()
        cases = s.query(models.Case).order_by(models.Case.id.desc()).limit(20).all()
        logs = s.query(models.AuditLog).order_by(models.AuditLog.id.desc()).limit(20).all()

    a_rows = ["<tr><th>ID</th><th>Aksi</th><th>Payload</th><th>Keputusan</th></tr>"]
    for a in approvals:
        a_rows.append(
            f"<tr><td>{a.id}</td><td>{a.action}</td><td>{a.payload}</td>"
            f"<td><form method='post' action='/approval/{a.id}'><input name='decision' value='approve'>"
            f"<input name='by' placeholder='nama approver' required>"
            f"<button>approve</button></form> "
            f"<form method='post' action='/approval/{a.id}'><input type='hidden' name='decision' value='reject'>"
            f"<input type='hidden' name='by' value='-'><button>reject</button></form></td></tr>"
        )

    t_rows = ["<tr><th>ID</th><th>PIC</th><th>Stasiun</th><th>Status</th><th>Tugas</th><th>Due</th><th>Aksi PIC</th></tr>"]
    for t in tasks:
        t_rows.append(
            f"<tr><td>{t.id}</td><td>{t.pic}</td><td>{t.station}</td><td>{t.status}</td>"
            f"<td>{t.description}</td><td>{t.due_date}</td>"
            f"<td><form method='post' action='/task/{t.id}/reply'>"
            f"<input name='pic' placeholder='nama kamu' required>"
            f"<select name='reply'><option>in_progress</option><option>fixed</option>"
            f"<option>cannot_fix</option></select>"
            f"<button>kirim</button></form></td></tr>"
        )

    c_rows = ["<tr><th>ID</th><th>Stasiun</th><th>Status</th><th>Analisis</th><th>Evidence</th></tr>"]
    for c in cases:
        c_rows.append(
            f"<tr><td>{c.id}</td><td>{c.station}</td><td>{c.status}</td>"
            f"<td>{c.analysis[:120]}</td><td>{c.evidence[:120]}</td></tr>"
        )

    l_rows = ["<tr><th>TS</th><th>Actor</th><th>Aksi</th><th>Detail</th></tr>"]
    for lg in logs:
        l_rows.append(f"<tr><td>{lg.ts}</td><td>{lg.actor}</td><td>{lg.action}</td>"
                      f"<td>{lg.detail[:160]}</td></tr>")

    return HTMLResponse(_PAGE.format(
        approval_rows=_rows(a_rows), task_rows=_rows(t_rows),
        case_rows=_rows(c_rows), audit_rows=_rows(l_rows),
    ))


@router.post("/approval/{approval_id}")
def decide(approval_id: int, decision: str = Form(...), by: str = Form(...)):
    with models.SessionLocal() as s:
        ap = s.get(models.Approval, approval_id)
        if ap is None or ap.status != "pending":
            raise HTTPException(404, "approval tidak ditemukan / sudah diputus")
        ap.status = "approved" if decision == "approve" else "rejected"
        ap.decided_by = by
        ap.decided_at = dt.datetime.utcnow()
        payload = json.loads(ap.payload)
        if ap.status == "approved" and ap.action == "escalate_to_lead":
            # Realisasi eskalasi: buat task utk lead QC stasiun tsb.
            lead = _lead_for(payload["station"])
            if lead:
                s.add(models.Task(
                    case_id=payload["case_id"], pic=lead, station=payload["station"],
                    description=f"ESKALASI: {payload.get('reason','')} — review case {payload['case_id']}",
                    due_date=dt.date.today() + dt.timedelta(days=1), approved_by=by,
                ))
        s.commit()
    audit(f"approver:{by}", f"approval_{ap.status}", approval_id=approval_id,
          action=ap.action, payload=ap.payload)
    return {"ok": True, "approval": approval_id, "status": ap.status}


def _lead_for(station: str) -> str | None:
    with models.SessionLocal() as s:
        lead = s.query(models.User).filter_by(role="lead_qc").first()
    return lead.name if lead else None


@router.post("/task/{task_id}/reply")
def task_reply(task_id: int, pic: str = Form(...), reply: str = Form(...)):
    """PIC menjawab task. Validasi: hanya PIC yang ditugaskan yang boleh."""
    with models.SessionLocal() as s:
        t = s.get(models.Task, task_id)
        if t is None:
            raise HTTPException(404, "task tidak ada")
        if t.pic != pic:
            raise HTTPException(403, f"task ini milik {t.pic}, bukan {pic}")
        t.status = {"in_progress": "in_progress", "fixed": "fixed",
                    "cannot_fix": "open"}[reply]
        s.commit()
    audit(f"pic:{pic}", "task_reply", task_id=task_id, reply=reply)
    return {"ok": True, "task": task_id, "status": reply}


@router.get("/api/stations")
def stations():
    """Ringkasan yield per stasiun (dashboard integration point)."""
    with models.SessionLocal() as s:
        rows = s.query(models.DailyProduction).order_by(
            models.DailyProduction.station, models.DailyProduction.date.desc()).all()
    out = {}
    for r in rows:
        out.setdefault(r.station, {"last_yield": r.yield_pct, "last_date": str(r.date)})
    return out
