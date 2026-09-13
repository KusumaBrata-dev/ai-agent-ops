"""Audit helper — semua aksi agent & manusia tercatat, append-only."""
from __future__ import annotations

import json

from . import models


def audit(actor: str, action: str, **detail) -> None:
    """Catat aksi. Panggil dari tools + approval + task reply.

    actor: 'agent' | 'approver:<nama>' | 'pic:<nama>'
    """
    with models.SessionLocal() as session:
        session.add(
            models.AuditLog(actor=actor, action=action, detail=json.dumps(detail, default=str))
        )
        session.commit()
