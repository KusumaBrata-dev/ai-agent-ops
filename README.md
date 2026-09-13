# AI Agent Ops — NG/Yield Watchdog

AI Agent operasional untuk pabrik elektronik: memantau data produksi harian
(Output, NG, Yield), menganalisis penyimpangan, membuat rekomendasi, menugaskan
PIC, dan mem-follow-up — dengan human approval sebelum aksi sensitif.

Dibangun sesuai pola job role AI Engineer:
Observe → Analyze → Recommend → Assign → Follow-up → Escalate → Verify → Close.

## Arsitektur

```
[seed_data: stasiun produksi harian]      (simulasi Google Sheets / MES)
        ↓  scheduler tiap 5 detik (prod: tiap jam)
[AGENT loop — FastAPI background task]
   1. Observe   : baca data 7 hari terakhir (tool: get_production_data)
   2. Analyze   : LLM + structured output (tool: analyze_anomaly)
   3. Recommend : rekomendasi + PIC + bukti (JSON schema ketat, wajib evidence)
   4. Assign    : task PIC (tool: create_task) — tier "auto"
   5. Follow-up : cek deadline task (tool: get_overdue_tasks)
   6. Escalate  : task lewat deadline → eskalasi ke Lead (tier "approval")
   7. Verify    : PIC jawab fixed → agent cek data membaik
   8. Close     : data membaik / PIC konfirmasi
```

- **Human-in-the-loop**: aksi sensitif (eskalasi, tandai selesai) butuh
  approval manusia via antarmuka web sederhana (`/pending`).
- **Guardrail**:
  - PIC allowlist per stasiun (config `agent_config.yaml`) — PIC di luar
    allowlist → agent DILARANG menugaskan, otomatis eskalasi.
  - Output LLM wajib `evidence` (angka dari data). Tanpa bukti → REJECT.
  - Rate limit: max 1 task per stasiun per hari (anti-spam).
- **Audit trail**: tabel `audit_log` append-only (DB trigger blok UPDATE/DELETE).
- **Memory**: tabel `case_history` — riwayat masalah per stasiun diinjeksi ke
  prompt analisis berikutnya.
- **Memory** di sini berarti penyimpanan structured (SQL), bukan RAG — cukup
  untuk fase portfolio; upgrade path: pgvector.

## Stack

- Python 3.11+ / FastAPI / SQLAlchemy / PostgreSQL (dev: SQLite fallback)
- LLM via API OpenAI-compatible (base URL + key via env vars; default Gemini
  free tier via OpenRouter)
- Template rendering untuk prompt analisis (Jinja2-like, tanpa dependency)

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env        # isi OPENAI_API_KEY (atau pakai MOCK_LLM=1 tanpa LLM)
alembic ...                 # (opsional) atau: python seed.py
python seed.py              # buat DB + data contoh + user demo
uvicorn app.main:app --reload
```

Buka http://localhost:8000/docs untuk API interaktif.

### Mode tanpa LLM (offline demo / CI)

```bash
set MOCK_LLM=1
python seed.py
uvicorn app.main:app
```

Agent jalan penuh dengan analyzer aturan statistik sederhana
(z-score), structured output tetap lolos schema yang sama — bukti bahwa
arsitektur tidak tergantung satu provider.

## Struktur

```
app/
  main.py            # FastAPI + agent loop (scheduler)
  config.py          # env + config (PIC allowlist, tier aksi)
  db.py              # engine/session, init schema
  models.py          # ORM: DailyProduction, Case, Task, AuditLog, CaseHistory, User
  schemas.py         # Pydantic: AnalysisResult (structured output LLM)
  llm.py             # klien OpenAI-compatible + mock + parsing terstruktur
  agent.py           # state machine 8 tahap
  tools.py           # function calling: 7 tool + tier + guardrail
  seed_data.py       # generator data produksi (mode "sehat" & "anomali")
  web.py             # UI approval (HTML sederhana) + endpointPIC
  audit.py           # audit trail helper
tests/
  test_agent.py      # golden set: skenario → expected aksi agent
```

## Evaluasi

```bash
python run_eval.py
```

Golden set: skenario data → aksi agent yang diharapkan (assign benar PIC /
eskalasi / no-action). Skor = kecocokan aksi. Laporan ke `eval_report.md`.

## Dokumentasi job-role mapping

| Job requirement | Di mana di repo ini |
|---|---|
| Integrasi Sheets/dashboard → analisis/alert/tugas | `seed_data.py` + agent Observe/Analyze |
| Workflow 8 tahap | `agent.py` state machine |
| Tool/function calling | `tools.py` (7 tools, tiap tool cek scope) |
| Human approval aksi sensitif | tier system + `web.py` approval UI |
| Memory & context | `case_history` + injection ke prompt |
| Guardrail + escalation matrix | `agent_config.yaml` + tools.py guardrail |
| Audit trail | `audit.py` + DB trigger append-only |
| Testing & evaluation | `tests/` + `run_eval.py` golden set |
| Anti-hallucination | wajib `evidence`; tanpa bukti → REJECT |
| Secrets via env vars | `.env.example`, no hardcoded key |
```
