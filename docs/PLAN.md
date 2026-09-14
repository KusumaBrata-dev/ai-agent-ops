# PLAN — Roadmap ai-agent-ops

Status per 2026-09-13. Fase & prioritas dikunci; perubahan lewat `DECISIONS.md`.

## Fase 1 — Core Agent (SELESAI ✅)

- [x] Schema DB + ORM + audit trigger append-only (SQLite)
- [x] 7 tools function calling (tier + guardrail + audit)
- [x] Agent state machine 8 tahap
- [x] LLM klien OpenAI-compatible + structured output + MOCK mode
- [x] Approval queue + web UI sederhana
- [x] Memory case_history + prompt injection
- [x] Seed data + smoke test (guardrail/audit/cycle) — PASS
- [x] Dokumen: PRD, PLAN, SCHEMA, RULES, WORKFLOW, EVALUATION, DEPLOYMENT, SECURITY, DECISIONS

**Definition of Done Fase 1 (tercapai):** seed → cycle → case+task benar;
guardrail menolak PIC asing; audit immutable; API `/health` + `/api/stations` hidup.

## Fase 2 — Integrasi Nyata (SELESAI ✅ per 2026-09-13, kecuali LLM live)

- [x] 2.1 `run_eval.py` golden set — 10/10 PASS (100%), exit-code CI-friendly
- [x] 2.5 Scheduler overlap guard (`_cycle_lock`) + interval env (sudah ada)
- [x] 2.4 Google Sheets reader: CSV publish URL → upsert idempotent
      (D013) + auto-sync di awal cycle, error → audit (D016)
- [x] 2.3 Telegram bot (D014): notify_task di create_task, callback
      fixed/cannot + guard pemilik task, /telegram/register chat_id,
      /telegram/setup-webhook (deploy); tanpa token = silent, web UI tetap jalan
- [ ] 2.2 LLM live — menunggu OPENAI_API_KEY user (lihat catatan bawah)
- [x] Bugfix produksi dari eval: rate-limit UTC (D015), agent overdue key,
      mock PIC regex greedy — semua tertutup skenario eval otomatis

**Catatan 2.2:** semua jalur LLM sudah siap (OpenAI-compatible, forced tool
choice). Yang belum = eksekusi verifikasi live: isi `OPENAI_API_KEY` di
`.env` (OpenRouter free / Gemini), `MOCK_LLM=0`, `POST /agent/run`, lihat
audit `analysis_recorded` dari model nyata. Juga catat di DECISIONS model
mana yang dipilih.

## Fase 3 — Evaluation & Hardening (SELESAI ✅ per 2026-09-13)

- [x] 3.1 Golden set 10 skenario — **10/10 PASS (100%)**, target PRD ≥85% terlampaui
- [x] 3.2 Metrik terukur: action accuracy, PIC-correct, false-alarm,
      hallucination, approval-bypass — semua invariant 0/100% hijau di eval
- [x] 3.3 LLM hardening: retry+backoff (429/5xx, 1s→2s), 4xx langsung gagal,
      token usage tercatat di audit `analysis_recorded.token_usage`,
      provider down → skip cycle (loop tak mati)
- [x] 3.4 Edge review: date-lokal (bisnis) vs datetime-UTC (audit) = konsisten
      per-kolom; guard pemilik task 403 terverifikasi (web + jalur Telegram);
      sheet idempotent + invalid-row skip teruji
- [x] Ekstra: E-guard "PIC jawab task orang lain" → 403 via API test

**DoD Fase 3:** `python run_eval.py` ≥ 85% (aktual 100%), hardening masuk
main, semua docs sinkron. TERCAPAI.

## Fase 4 — Production & Portfolio Packaging (berjalan — file siap, build menunggu Docker di PC)

- [x] 4.1 Dockerfile (slim, non-root, healthcheck /health) + docker-compose
      (app + PostgreSQL 16, env inject, restart policy) — D019
- [x] 4.2 PG trigger append-only: `db/init/01_audit_triggers.sql` (volume baru)
      + pemasangan idempotent oleh app startup (D018) — invarian selalu aktif
- [x] 4.3 README final (badge, arsitektur, quickstart offline 2 menit,
      tabel fitur keamanan, struktur, batas by-design)
- [ ] 4.4 `docker compose up --build` verifikasi fisik — **menunggu Docker
      Desktop terinstall** (file siap, tak ada perubahan kode yang tersisa)
- [ ] 4.5 Video demo 5 menit + tag `v1.0.0` + push GitHub public
      (cek SECURITY.md §4: data dummy saja — sudah dummy dari awal)

**DoD Fase 4 (tersisa):** compose jalan fisik; demo video; repo public.

## Urutan eksekusi yang DILARANG diubah

1. Tidak integrasi (Fase 2) sebelum eval harness jalan (2.1) — kalau tidak,
   tidak ada cara mengukur bahwa integrasi tidak merusak guardrail.
2. Tidak Docker (4.1) sebelum PG trigger (4.2) disiapkan — urutan teknis
   dependensi.
3. Tidak ada fitur di luar PRD §5.1. Mau fitur baru? Buka entri DECISIONS
   dengan alasan, update PRD, baru eksekusi — TIDAK langsung koding.

## Estimasi total

Fase 2+3+4 ≈ 4–7 minggu sambil kerja penuh waktu. Jangan dipercepat dengan
memotong evaluation — itu nilai jual utama portfolio ("bikin AI" biasa,
"bisa BUKTIKAN AI-nya aman" langka).
