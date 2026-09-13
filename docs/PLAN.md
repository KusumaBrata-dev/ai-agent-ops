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

## Fase 2 — Integrasi Nyata (2–3 minggu)

- [ ] 2.1 `run_eval.py` golden set (bawa dari draft; 4 skenario awal, target 10+)
- [ ] 2.2 LLM live: isi `OPENAI_API_KEY` (Gemini/OpenRouter free), verifikasi
      structured output nyata lolos schema
- [ ] 2.3 Telegram bot: PIC terima task, tombol inline `fixed`/`cannot_fix`;
      webhook atau polling `python-telegram-bot`; map `users.telegram`
- [ ] 2.4 Google Sheets reader: service account, baca sheet "Produksi Harian"
      (kolom: date, station, output, ng) → upsert `daily_production`;
      mode fallback seed jika sheet kosong
- [ ] 2.5 Scheduler tuning: interval via env, overlap guard (skip jika cycle jalan)

**DoD Fase 2:** bot kirim task nyata; data dari sheet; LLM live menganalisis;
eval tetap hijau (guardrail tidak berubah perilaku).

## Fase 3 — Evaluation & Hardening (1–2 minggu)

- [ ] 3.1 Golden set 10+ skenario: anomali parah, anomali ringan, sehat,
      stasiun tanpa riwayat, PIC tidak di allowlist, task overdue, dll.
- [ ] 3.2 Metrik: precision, false-alarm rate, PIC-correct rate → `eval_report.md`
- [ ] 3.3 Error handling LLM: retry + backoff, log token usage
- [ ] 3.4 Cleanup edge: DB locked (timeout), timezone, data duplikat sheet

**DoD Fase 3:** `python run_eval.py` ≥ 85% PASS; laporan eval masuk README.

## Fase 4 — Production & Portfolio Packaging (1–2 minggu)

- [ ] 4.1 Docker: `Dockerfile` + `docker-compose.yml` (app + PostgreSQL + migrasi)
- [ ] 4.2 PostgreSQL: trigger append-only versi PG (migration SQL)
- [ ] 4.3 Dokumentasi final: README (badge, diagram, quickstart), API docs,
      runbook recovery, video demo 5 menit
- [ ] 4.4 CV: narasi mapping job desc (lihat docs/PORTFOLIO-CV.md bila dibuat)
- [ ] 4.5 Publikasi: repo GitHub public, hapus data sensitif, tag `v1.0.0`

**DoD Fase 4:** `docker compose up` jalan penuh; video demo; tag rilis.

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
