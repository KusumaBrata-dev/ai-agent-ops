"""Generator data produksi â€” menggantikan Google Sheets/MES di fase portfolio.

Dua mode:
- sehat : yield stabil 96-99%
- anomali: beberapa hari yield jatuh (stok kasus utk demo agent)
"""
from __future__ import annotations

import datetime as dt
import random

from . import models

STATIONS = ["SMT-01", "SMT-02", "ASY-01", "TEST-01", "PACK-01"]


def seed(days: int = 10, anomaly_station: str = "SMT-01") -> None:
    models.init_db()
    rng = random.Random(42)
    today = dt.date.today()
    with models.SessionLocal() as s:
        if s.query(models.DailyProduction).count():
            print("DB sudah ada data â€” skip seed.")
            return
        for st in STATIONS:
            for d in range(days):
                date = today - dt.timedelta(days=days - d)
                output = rng.randint(900, 1100)
                if st == anomaly_station and d >= 5:  # 5 hari TERAKHIR yield jatuh
                    ng = rng.randint(90, 150)       # yield ~87-85%
                else:
                    ng = rng.randint(5, 30)          # yield ~97-99%
                y = (output - ng) / output * 100
                s.add(models.DailyProduction(
                    date=date, station=st, output=output, ng_qty=ng, yield_pct=round(y, 1),
                ))
        # User demo (PIC dari allowlist agent_config.yaml)
        for name, role in [("Budi", "pic"), ("Sari", "pic"), ("Andi", "pic"),
                           ("Dewi", "pic"), ("Rian", "pic"), ("LeadQC", "lead_qc"),
                           ("HeadProd", "head_production")]:
            s.add(models.User(name=name, role=role))
        s.commit()
    print(f"Seed OK: {len(STATIONS)} stasiun Ã— {days} hari. Anomali di {anomaly_station}.")

