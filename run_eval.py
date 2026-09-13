"""Golden set evaluation — jalankan: python run_eval.py

Tiap skenario dari docs/EVALUATION.md: DB in-memory baru → seed data →
jalankan agent cycle (MOCK_LLM=1, deterministik) → bandingkan AKSI hasil.
"""
from __future__ import annotations

import datetime as dt
import os
import sys

os.environ["MOCK_LLM"] = "1"
os.environ["AGENT_ENABLED"] = "0"

from sqlalchemy import create_engine  # noqa: E402

from app import config, models  # noqa: E402
from app.agent import run_agent_cycle  # noqa: E402


def _fresh_db() -> None:
    """Ganti engine ke SQLite in-memory + reset mutasi global skenario lalu."""
    _reset_globals()
    models.engine.dispose()
    models.engine = create_engine("sqlite://", echo=False)
    models.SessionLocal.configure(bind=models.engine)
    models.Base.metadata.create_all(models.engine)


def _seed_users() -> None:
    with models.SessionLocal() as s:
        for name, role in [("Budi", "pic"), ("Sari", "pic"), ("Andi", "pic"),
                           ("Dewi", "pic"), ("LeadQC", "lead_qc")]:
            s.add(models.User(name=name, role=role))
        s.commit()


def _seed_prod(station: str, yields: list[float], start_offset: int | None = None) -> None:
    """yields: list 7 nilai yield%, index akhir = hari ini.
    start_offset: geser tanggal mulai (utk skenario overdue/history)."""
    today = dt.date.today()
    n = len(yields)
    with models.SessionLocal() as s:
        for i, y in enumerate(yields):
            out = 1000
            ng = round(out * (100 - y) / 100)
            date = today - dt.timedelta(days=n - 1 - i + (start_offset or 0))
            s.add(models.DailyProduction(
                date=date, station=station, output=out, ng_qty=ng, yield_pct=y,
            ))
        s.commit()


def _state(station: str) -> dict:
    """Snapshot aksi yang diambil utk stasiun: case, task, approval."""
    with models.SessionLocal() as s:
        case = s.query(models.Case).filter_by(station=station).first()
        task = s.query(models.Task).filter_by(station=station).first()
        approval = s.query(models.Approval).first()
    return {
        "case": case.status if case else None,
        "task_pic": task.pic if task else None,
        "approval": approval.action if approval else None,
    }


def check(sc: dict) -> bool:
    """Bandingkan state aktual vs aturan skenario."""
    st = _state(sc["station"])
    mode = sc["expect"]

    if mode == "assigned":
        return st["case"] == "assigned" and st["task_pic"] == sc["expect_pic"]
    if mode == "escalated":
        return st["approval"] == "escalate_to_lead"
    if mode == "no_action":
        # E7 pakai expect=no_action + flag rate_limit_hit utk cek guardrail tercatat
        if sc.get("rate_limit_hit"):
            with models.SessionLocal() as s:
                hit = s.query(models.AuditLog).filter_by(
                    action="guardrail_blocked").filter(
                    models.AuditLog.detail.like('%rate_limit%')).count()
            return st["case"] is None and hit >= 1
        return st["case"] is None and st["approval"] is None
    if mode == "skip_active":
        return sc["n_cases_before"] == _count_cases()
    return False


def _count_cases() -> int:
    with models.SessionLocal() as s:
        return s.query(models.Case).count()


def scenario(name: str, station: str, yields: list[float], expect: str,
             expect_pic: str | None = None, setup=None) -> dict:
    _fresh_db()
    _seed_users()
    if setup:
        setup()
    _seed_prod(station, yields)
    before = _count_cases()
    report = run_agent_cycle()
    sc = {"name": name, "station": station, "expect": expect,
          "expect_pic": expect_pic, "n_cases_before": before,
          "rate_limit_hit": name.startswith("E7")}
    passed = check(sc)
    return {"name": name, "pass": passed, "state": _state(station), "report": report}


# ---------- Setup khusus ----------
# CATATAN ISOLASI: setup boleh memutasi global (config/llm) — _fresh_db()
# mereset semuanya sebelum tiap skenario (lihat _reset_globals).

_ORIG_MOCK = None


def _reset_globals() -> None:
    """Reset mutasi dari setup skenario sebelumnya."""
    config.PIC_ALLOWLIST.clear()
    config.PIC_ALLOWLIST.update(config._load_yaml().get("pic_allowlist", {}))
    if _ORIG_MOCK is not None:
        import app.llm as llm
        llm._mock_analyze = _ORIG_MOCK


def _setup_pic_not_in_allowlist():
    """Kosongkan allowlist SMT-01 → PIC usulan apapun pasti ditolak."""
    config.PIC_ALLOWLIST["SMT-01"] = []


def _setup_active_case():
    """Bikin case aktif di SMT-01 manual (guardrail anti-duplikat)."""
    with models.SessionLocal() as s:
        s.add(models.Case(station="SMT-01", status="assigned"))
        s.commit()


def _setup_overdue_task():
    """Task overdue 3 hari di SMT-01 + due date kemarin → expect reminder+eskalasi."""
    with models.SessionLocal() as s:
        case = models.Case(station="SMT-01", status="assigned")
        s.add(case)
        s.flush()
        s.add(models.Task(
            case_id=case.id, pic="Budi", station="SMT-01",
            description="tugas lama", due_date=dt.date.today() - dt.timedelta(days=3),
        ))
        s.commit()


def _setup_rate_limit():
    """Task SMT-01 sudah dibuat hari ini → task kedua harus ditolak tool."""
    with models.SessionLocal() as s:
        case = models.Case(station="SMT-01", status="assigned")
        s.add(case)
        s.flush()
        s.add(models.Task(
            case_id=case.id, pic="Budi", station="SMT-01", description="x",
            due_date=dt.date.today(),
        ))
        s.commit()


def scenario_rate_limit() -> dict:
    """E7: rate limit = guardrail TOOL-level, diuji langsung (bukan via cycle
    — cycle skip stasiun ber-case-aktif, tool tak terpanggil)."""
    _fresh_db()
    _seed_users()
    _setup_rate_limit()
    from app import tools
    try:
        tools.create_task(1, "Budi", "SMT-01", "task kedua hari yang sama")
        passed, state = False, "task_kedua_DITERIMA (bug!)"
    except PermissionError:
        passed, state = True, "rate_limit_ditolak"
    return {"name": "E7 rate limit → task kedua ditolak (tool-level)",
            "pass": passed, "state": state}


def _setup_evidence_reject():
    """Hancurkan regex mock analyzer agar evidence tanpa digit → harus REJECT."""
    global _ORIG_MOCK
    import app.llm as llm
    if _ORIG_MOCK is None:
        _ORIG_MOCK = llm._mock_analyze
    llm._mock_analyze = lambda prompt: {
        "station": "SMT-01", "is_anomaly": True, "analysis": "turun",
        "recommendation": "cek", "suggested_pic": "Budi",
        "evidence": "yield jelek sekali",  # tanpa angka
        "confidence": 0.9,
    }


# ---------- Golden set (dari docs/EVALUATION.md E1-E10) ----------

def run_all() -> None:
    results = [
        scenario("E1 yield drop parah → assigned PIC benar", "SMT-01",
                 [98.5, 98.1, 97.8, 90.2, 86.5, 85.1, 87.0], "assigned", "Budi"),
        scenario("E2 yield sehat → no action", "SMT-01",
                 [98.9, 97.8, 98.2, 97.5, 98.8, 99.0, 98.1], "no_action"),
        scenario("E3 PIC di luar allowlist → escalated", "SMT-01",
                 [98.0, 97.5, 91.0, 88.0, 86.5, 85.9, 84.2], "escalated",
                 setup=_setup_pic_not_in_allowlist),
        scenario("E4 task overdue → eskalasi masuk antrean", "SMT-01",
                 [98.0, 98.0, 98.0, 98.0, 98.0, 98.0, 98.0], "escalated",
                 setup=_setup_overdue_task),
        scenario("E5 anomali ringan 1 hari → assigned konsisten", "SMT-01",
                 [98.0, 98.2, 98.1, 98.4, 98.0, 97.9, 93.0], "assigned", "Budi"),
        scenario("E6 case aktif → skip stasiun", "SMT-01",
                 [99.0, 98.0, 90.0, 88.0, 86.0, 85.0, 84.0], "skip_active",
                 setup=_setup_active_case),
        scenario_rate_limit(),
        scenario("E8 evidence tanpa angka → REJECT (no case)", "SMT-01",
                 [98.0, 97.0, 90.0, 88.0, 86.0, 85.0, 84.0], "no_action",
                 setup=_setup_evidence_reject),
        scenario("E9 stasiun lain (ASY-01) → assigned Dewi", "ASY-01",
                 [98.0, 97.5, 98.1, 91.0, 88.0, 86.5, 85.9], "assigned", "Dewi"),
        scenario("E10 data < 7 hari → tetap dianalisa", "SMT-01",
                 [99.0, 98.0, 85.0], "assigned", "Budi"),
    ]

    passed = sum(1 for r in results if r["pass"])
    total = len(results)
    print(f"\n=== GOLDEN SET: {passed}/{total} PASS ({passed / total * 100:.0f}%) ===")
    for r in results:
        mark = "PASS" if r["pass"] else "FAIL"
        print(f"[{mark}] {r['name']} → state={r['state']}")

    with open("eval_report.md", "w", encoding="utf-8") as f:
        f.write("# Eval Report — Golden Set\n\n")
        f.write(f"Hasil: **{passed}/{total} PASS ({passed / total * 100:.0f}%)** "
                f"(target PRD G1: >= 85%)\n\n")
        f.write("| # | Skenario | Hasil | State |\n|---|---|---|---|\n")
        for i, r in enumerate(results, 1):
            f.write(f"| E{i} | {r['name']} | {'PASS' if r['pass'] else 'FAIL'} "
                    f"| {r['state']} |\n")

    ok = passed / total >= 0.85
    print(f"\nLaporan: eval_report.md | Target >=85%: {'TERCAPAI' if ok else 'BELUM'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    run_all()
