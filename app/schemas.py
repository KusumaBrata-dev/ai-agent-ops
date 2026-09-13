"""Structured output LLM — schema analysis. Anti-hallucination: evidence wajib."""
from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field, ValidationError


class AnalysisResult(BaseModel):
    """Kontrak structured output agent. Schema ketat, tipe aman."""
    station: str
    is_anomaly: bool
    analysis: str = Field(..., description="temuan, bahasa Indonesia, singkat")
    recommendation: str = Field(..., description="tindakan konkret utk PIC")
    suggested_pic: str = Field(..., description="nama PIC dari allowlist")
    evidence: str = Field(..., description="angka/bukti dari data, bukan opini")
    confidence: float = Field(0.0, ge=0.0, le=1.0)


# JSON schema dikirim sebagai tool/function ke LLM → paksa output terstruktur.
ANALYSIS_TOOL_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "record_analysis",
        "description": "Catat hasil analisis anomaly stasiun produksi.",
        "parameters": {
            "type": "object",
            "properties": {
                "station": {"type": "string"},
                "is_anomaly": {"type": "boolean"},
                "analysis": {"type": "string"},
                "recommendation": {"type": "string"},
                "suggested_pic": {"type": "string"},
                "evidence": {"type": "string"},
                "confidence": {"type": "number"},
            },
            "required": [
                "station", "is_anomaly", "analysis", "recommendation",
                "suggested_pic", "evidence", "confidence",
            ],
        },
    },
}

PROMPT_TEMPLATE = """Kamu AI Agent QC di pabrik elektronik. Analisis data produksi stasiun {station}.

DATA 7 HARI (tanggal | output | NG | yield%):
{data_rows}

AMBANG: yield minimum {yield_threshold}%.
MEMORY riwayat stasiun ini:
{history}

ATURAN KETAT:
- evidence WAJIB berisi angka dari data di atas. Tanpa angka = analisis tidak valid.
- suggested_pic WAJIB salah satu dari: {pic_list}. Jangan menebak nama lain.
- Jika tidak ada anomaly, isi is_anomaly=false dan recommendation singkat.
Panggil function record_analysis dengan hasil."""

REJECT_NO_EVIDENCE = "REJECT_NO_EVIDENCE"
