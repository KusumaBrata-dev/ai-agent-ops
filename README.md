# AI Agent Ops — NG/Yield Watchdog

[![eval](https://img.shields.io/badge/golden_set-10%2F10_PASS-brightgreen)](run_eval.py)
[![python](https://img.shields.io/badge/python-3.11%2B-blue)](requirements.txt)
[![docker](https://img.shields.io/badge/docker-compose%20ready-2496ED)](docker-compose.yml)

AI Agent operasional untuk manufaktur elektronik: memantau data produksi harian
(Output/NG/Yield), mendeteksi anomali, menugaskan PIC, menagih, mengeskalasi
(dengan human approval), memverifikasi perbaikan — **semua aksi ter-audit dan
di-batasi guardrail kode, bukan cuma prompt.**

**Workflow:** `Observe → Analyze → Recommend → Assign → Follow-up → Escalate → Verify → Close`

## Kenapa repo ini berbeda

Bukan "chatbot yang bisa alat". Ini **agent operasional dengan disiplin keamanan**:

| Fitur | Implementasi |
|---|---|
| Anti-hallucination | Output LLM wajib `evidence` berisi angka dari data — tanpa bukti → REJECT |
| PIC tidak pernah salah kirim | Allowlist PIC per stasiun di kode (bukan prompt); pelanggaran → eskalasi |
| Human-in-the-loop | Aksi sensitif (eskalasi/close) hanya MENGANTRE; manusia yang approve |
| Audit trail | `audit_log` **append-only via DB trigger** — UPDATE/DELETE ditolak DB |
| Rate limit | Max 1 task/stasiun/hari (timezone-safe) |
| Memory | Riwayat kasus per stasiun diinjeksi ke analisis berikutnya |
| Bisa dibuktikan | Golden set eval **10/10 PASS** — aksi agent diuji, bukan dirasakan |
| Provider-agnostic | Format OpenAI-compatible; ganti LLM = ganti 1 env var |
| Dev tanpa biaya | `MOCK_LLM=1` analyzer statistik lokal, schema output identik |

## Quickstart (2 menit, offline, gratis)

```bash
pip install -r requirements.txt
set MOCK_LLM=1          # Linux: export
python seed.py          # data demo: 5 stasiun, anomali yield di SMT-01
uvicorn app.main:app    # buka http://localhost:8000
```

Panel web `/` → approval queue, task PIC, case, audit log.
`POST /agent/run` → satu cycle agent (buat case + task + reminder).

### Live LLM + integrasi

`.env` (lihat `.env.example`):
```
OPENAI_API_KEY=sk-or-...     # OpenRouter free tier
MODEL_NAME=nvidia/nemotron-3.5-lightning:free
SHEETS_CSV_URL=<publish-to-web CSV>   # Google Sheets → data produksi
TELEGRAM_BOT_TOKEN=<@BotFather>       # task ke PIC + tombol jawab
```

### Docker (production)

```bash
docker compose up -d --build   # app + PostgreSQL 16 + trigger append-only
```

## Arsitektur

```
Sheets/MES/seed ──▶ daily_production (upsert idempotent)
                        │
        scheduler (overlap-guard) ▼
   ┌─────────── AGENT CYCLE ───────────┐
   │ Observe: get_production_data (7d)  │
   │ Analyze: LLM forced tool-call ────────▶ Pydantic AnalysisResult
   │         │  gagal evidence/allowlist → REJECT (tidak ada aksi)
   │ Assign: create_task [allowlist+rate-limit+audit]
   │         └─ guardrail tolak → request_escalation → ANTRE approval
   │ Follow-up: overdue → reminder → eskalasi
   │ Verify: yield pulih ≥ threshold → close (approval) ─▶ case_history
   └────────────────────────────────────┘
        audit_log (append-only trigger) — semua langkah tercatat
```

Detail: [docs/PRD.md](docs/PRD.md) · [docs/SCHEMA.md](docs/SCHEMA.md) ·
[docs/WORKFLOW.md](docs/WORKFLOW.md) · [docs/RULES.md](docs/RULES.md)

## Evaluation

```bash
python run_eval.py
```

10 skenario golden set (anomali parah/ringan, sehat, PIC asing, overdue,
rate limit, evidence kosong, dsb.) → **10/10 PASS**. Laporan: `eval_report.md`.

Eval harness ini menangkap bug nyata: rate-limit bocor karena timezone
mismatch (UTC vs local-midnight), sebelum demo — bukan setelah produksi.

## Struktur

```
app/            config, models, schemas, llm (mock+live), tools (7), agent,
                web (UI+approval), sheets (CSV reader), telegram (bot)
tests/smoke.py  guardrail + audit + cycle
run_eval.py     golden set E1-E10
docs/           PRD, PLAN, SCHEMA, RULES, WORKFLOW, EVALUATION, DEPLOYMENT, SECURITY, DECISIONS
```

## Batas (by design)

Tidak ada: chart dashboard, RAG, multi-tenant, fine-tuning, tool keuangan/HR
(guardrail by absence). Lihat PRD non-goals. Setiap penambahan lewat
[docs/DECISIONS.md](docs/DECISIONS.md).

## Lisensi

MIT License
