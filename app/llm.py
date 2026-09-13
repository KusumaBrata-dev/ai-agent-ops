"""Klien LLM OpenAI-compatible + mode mock. Ganti provider = ganti env saja."""
from __future__ import annotations

import json
import re
from typing import Any

import httpx

from .config import MODEL_NAME, MOCK_LLM, OPENAI_API_KEY, OPENAI_BASE_URL
from .schemas import ANALYSIS_TOOL_SCHEMA, AnalysisResult, PROMPT_TEMPLATE, REJECT_NO_EVIDENCE

_TIMEOUT = httpx.Timeout(60.0)


def build_prompt(station: str, data_rows: str, history: str, pic_list: str, yield_threshold: float) -> str:
    return PROMPT_TEMPLATE.format(
        station=station,
        data_rows=data_rows,
        history=history or "(belum ada riwayat)",
        pic_list=pic_list,
        yield_threshold=yield_threshold,
    )


def _extract_json(text: str) -> dict[str, Any] | None:
    """Fence ```json ...``` atau objek { pertama-terakhir. """
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    return None


def call_llm(prompt: str) -> AnalysisResult | None:
    """Return AnalysisResult valid, atau None (gagal/invalid). Anti-hallucination di sini."""
    raw_args = _call_raw(prompt)
    if raw_args is None:
        return None
    try:
        result = AnalysisResult.model_validate(raw_args)
    except Exception:
        return None
    # Guardrail evidence: wajib mengandung digit (angka dari data).
    if not re.search(r"\d", result.evidence or ""):
        return None
    if result.is_anomaly and not result.evidence:
        return None
    return result


def _call_raw(prompt: str) -> dict[str, Any] | None:
    if MOCK_LLM:
        return _mock_analyze(prompt)

    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY kosong. Isi .env atau set MOCK_LLM=1.")

    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "tools": [ANALYSIS_TOOL_SCHEMA],
        "tool_choice": {"type": "function", "function": {"name": "record_analysis"}},
    }
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.post(f"{OPENAI_BASE_URL}/chat/completions", json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    try:
        msg = data["choices"][0]["message"]
        if msg.get("tool_calls"):
            return json.loads(msg["tool_calls"][0]["function"]["arguments"])
        args = _extract_json(msg.get("content") or "")
        return args
    except (KeyError, IndexError):
        return None


def _mock_analyze(prompt: str) -> dict[str, Any] | None:
    """Analyzer statistik sederhana utk mode offline — ambil station & evidence dari prompt."""
    m_station = re.search(r"stasiun (\S+)", prompt)
    if not m_station:
        return None
    station = m_station.group(1)
    # Cari baris yield terendah di blok data.
    worst_yield, worst_line = None, ""
    for line in prompt.splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) == 4 and parts[0].count("-") == 2:
            try:
                y = float(parts[3])
            except ValueError:
                continue
            if worst_yield is None or y < worst_yield:
                worst_yield, worst_line = y, line
    if worst_yield is None:
        return None
    m_pic = re.search(r"salah satu dari: ([^\n]+)\.", prompt)
    pic = (m_pic.group(1).split(",")[0].strip() if m_pic else "Budi")
    is_anomaly = worst_yield < 95.0
    return {
        "station": station,
        "is_anomaly": is_anomaly,
        "analysis": (
            f"Yield {station} jatuh: baris terburuk {worst_line.strip()} di bawah ambang 95%."
            if is_anomaly else f"Yield {station} stabil di atas ambang ({worst_yield:.1f}% terburuk)."
        ),
        "recommendation": (
            f"Periksa proses {station}: cek feeding, nozzle, dan parameter terakhir; "
            "lapor jika perlu ganti feeder."
            if is_anomaly else "Tidak perlu tindakan."
        ),
        "suggested_pic": pic,
        "evidence": worst_line.strip(),
        "confidence": 0.8 if is_anomaly else 0.5,
    }
