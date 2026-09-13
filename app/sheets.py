"""Google Sheets reader — sumber data alternatif (Fase 2.4, PLAN.md).

Cara pakai (paling sederhana, tanpa service account):
1. Google Sheet berisi kolom: date | station | output | ng
2. File → Share → Publish to web → pilih CSV → dapat URL
3. .env: SHEETS_CSV_URL=<url tadi>
4. POST /sheets/sync  (atau tunggu agent cycle — auto-sync tiap cycle)

Mengapa CSV publik, bukan API resmi? Portfolio: nol auth, nol dependency
baru, idempotent. Service account (write-back, private sheet) = upgrade
path tercatat di DECISIONS D013.

Rule ingest (SCHEMA.md): upsert by (date, station) — sumber boleh dikirim ulang.
"""
from __future__ import annotations

import csv
import datetime as dt
import io

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from . import models
from .audit import audit
from .config import SHEETS_CSV_URL

router = APIRouter(prefix="/sheets", tags=["sheets"])


class SyncResult(BaseModel):
    rows_read: int
    rows_upserted: int
    rows_invalid: int


def fetch_rows(url: str) -> list[dict]:
    resp = httpx.get(url, timeout=30.0, follow_redirects=True)
    resp.raise_for_status()
    return list(csv.DictReader(io.StringIO(resp.text)))


def _parse_date(v: str) -> dt.date | None:
    v = (v or "").strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return dt.datetime.strptime(v, fmt).date()
        except ValueError:
            continue
    return None


def sync_from_csv(url: str | None = None) -> SyncResult:
    url = url or SHEETS_CSV_URL
    if not url:
        raise HTTPException(400, "SHEETS_CSV_URL kosong — set di .env")
    rows = fetch_rows(url)

    n_up, n_bad = 0, 0
    with models.SessionLocal() as s:
        for r in rows:
            date = _parse_date(r.get("date"))
            station = (r.get("station") or "").strip()
            try:
                output = int(float(r.get("output") or 0))
                ng = int(float(r.get("ng") or 0))
            except (TypeError, ValueError):
                n_bad += 1
                continue
            if not date or not station or output <= 0:
                n_bad += 1
                continue
            y = round((output - ng) / output * 100, 1)
            existing = (
                s.query(models.DailyProduction)
                .filter_by(date=date, station=station)
                .one_or_none()
            )
            if existing:  # upsert idempotent
                existing.output, existing.ng_qty, existing.yield_pct = output, ng, y
            else:
                s.add(models.DailyProduction(
                    date=date, station=station, output=output, ng_qty=ng, yield_pct=y,
                ))
            n_up += 1
        s.commit()
    audit("agent", "sheets_sync", rows=len(rows), upserted=n_up, invalid=n_bad)
    return SyncResult(rows_read=len(rows), rows_upserted=n_up, rows_invalid=n_bad)


@router.post("/sync", response_model=SyncResult)
def sync(url: str | None = None):
    """Tarik data dari Google Sheet (CSV publish) → daily_production."""
    return sync_from_csv(url)
