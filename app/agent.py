"""Agent loop — state machine 8 tahap, dijalankan scheduler FastAPI."""
from __future__ import annotations

import datetime as dt
import json

from . import models, tools
from .audit import audit
from .config import ACTION_TIERS, PIC_ALLOWLIST, YIELD_THRESHOLD
from .llm import build_prompt, call_llm


def run_agent_cycle() -> dict:
    """Satu putaran: Observe → Analyze → Assign + Follow-up → Escalate."""
    report = {"analyzed": 0, "assigned": 0, "escalated": 0, "rejected": 0, "reminded": 0}

    with models.SessionLocal() as s:
        stations = [r[0] for r in s.query(models.DailyProduction.station).distinct().all()]
        open_cases = {
            c.station: c for c in s.query(models.Case)
            .filter(models.Case.status.notin_(("closed", "rejected")))
            .all()
        }

    for station in stations:
        if station in open_cases:
            continue  # satu kasus aktif per stasiun — sederhana & aman

        # 1-2. OBSERVE + ANALYZE
        data = tools.get_production_data(station)
        if not data:
            continue
        history = tools.get_case_history(station)
        pic_list = ", ".join(PIC_ALLOWLIST.get(station, []))
        prompt = build_prompt(station, data, history, pic_list, YIELD_THRESHOLD)

        result = call_llm(prompt)  # None = gagal/guardrail evidence
        if result is None or not result.is_anomaly:
            report["rejected"] += 0 if result else 1
            continue

        # Buat case (status analyzed)
        with models.SessionLocal() as s:
            case = models.Case(
                station=station, status="analyzed",
                analysis=result.analysis, recommendation=result.recommendation,
                evidence=result.evidence, confidence=result.confidence,
            )
            s.add(case)
            s.commit()
            case_id = case.id
        audit("agent", "analysis_recorded", case_id=case_id, station=station,
              confidence=result.confidence, evidence=result.evidence)
        report["analyzed"] += 1

        # 3-4. RECOMMEND→ASSIGN
        try:
            tools.create_task(
                case_id=case_id, pic=result.suggested_pic, station=station,
                description=result.recommendation,
            )
            report["assigned"] += 1
        except PermissionError as e:
            # Guardrail menolak → eskalasi ke manusia, bukan paksa.
            tools.request_escalation(case_id=case_id, reason=str(e))
            report["escalated"] += 1

    # 5-6. FOLLOW-UP → ESCALATE
    for t in tools.get_overdue_tasks():
        try:
            tools.send_reminder(t["id"])
            report["reminded"] += 1
        except ValueError:
            pass
        with models.SessionLocal() as s:
            case = s.get(models.Case, t["case_id"])
            if case and case.status not in ("escalated",):
                tools.request_escalation(case_id=t["case_id"],
                                         reason=f"task overdue sejak {t['due_date']}")
                report["escalated"] += 1

    # 7. VERIFY: task fixed → cek data hari setelahnya membaik (diproses cycle berikut)
    _verify_fixed_cases()
    return report


def _verify_fixed_cases() -> None:
    """Task fixed → kalau yield terakhir >= threshold, tutup case + simpan memory."""
    with models.SessionLocal() as s:
        fixed_tasks = s.query(models.Task).filter(models.Task.status == "fixed").all()
        for t in fixed_tasks:
            case = s.get(models.Case, t.case_id)
            if case is None or case.status in ("closed", "rejected"):
                continue
    # ambil yield terbaru stasiun
            latest = (
                s.query(models.DailyProduction)
                .filter(models.DailyProduction.station == t.station)
                .order_by(models.DailyProduction.date.desc())
                .first()
            )
            if latest and latest.yield_pct >= YIELD_THRESHOLD:
                if ACTION_TIERS.get("close_case") == "approval":
                    s.add(models.Approval(
                        action="close_case",
                        payload=json.dumps({"case_id": t.case_id, "station": t.station,
                                            "verified_yield": latest.yield_pct}),
                    ))
                    case.status = "verify"
                else:
                    tools.record_case_outcome(
                        case_id=t.case_id,
                        summary=f"Yield pulih ke {latest.yield_pct:.1f}% setelah tugas {t.id}",
                        outcome="fixed",
                    )
        s.commit()
