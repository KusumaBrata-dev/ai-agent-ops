# PRD — AI Agent Ops (NG/Yield Watchdog)

Versi: 1.0 · Status: Fase 1 selesai · Owner: (kamu) · Repo: `ai-agent-ops`

## 1. Problem

Pabrik elektronik memantau KPI produksi (Output/day, NG/day, Yield%) manual:
manusia harus membuka dashboard, membandingkan angka, menemukan penyimpangan,
ingat siapa PIC-nya, lalu menagih. Proses lambat, terlambat, dan tidak
konsisten. Penyimpangan yield sering ketahuan berhari-hari kemudian.

## 2. Solusi

AI Agent operasional yang menjalankan loop otonom:

**Observe → Analyze → Recommend → Assign → Follow-up → Escalate → Verify → Close**

Agent membaca data produksi harian tiap interval, mendeteksi anomali yield,
menganalisis dengan LLM (structured output, wajib bukti), menugaskan PIC yang
sah, menagih yang lewat deadline, mengeskalasi ke Lead QC untuk kasus sensitif
(dengan human approval), memverifikasi perbaikan, lalu menyimpan hasil ke
memory untuk konteks analisis berikutnya.

## 3. User & Persona

| User | Peran | Kebutuhan |
|---|---|---|
| PIC stasiun | Penerima tugas | Tahu apa yang harus dikerjakan + cara menjawab (fixed/cannot) |
| Lead QC | Approver | Menyetujui/menolak eskalasi; tidak ingin kejutan dari agent |
| Head Production | Pengawas | Melihat semua case, audit trail, tren anomali |
| Recruiter/Hiring manager | **Pembaca portfolio** | Melihat bukti nyata skill AI Engineer sesuai job desc |

## 4. Goals & Success Criteria

| # | Goal | Ukuran |
|---|---|---|
| G1 | Deteksi anomali yield akurat | Golden set ≥ 85% aksi benar (Fase 3) |
| G2 | Tugas sampai ke PIC yang benar | 0 kirim ke PIC di luar allowlist (guardrail, hard) |
| G3 | Aksi sensitif selalu lewat manusia | 0 aksi tier-approval tanpa approval (audit cek) |
| G4 | Semua aksi terlacak | 100% aksi agent ada di audit_log |
| G5 | Portfolio siap demo | Video 5 menit + README + laporan eval |

**Non-goals (JANGAN dibangun):** lihat §6.

## 5. Scope

### In-scope (commit ini repo)

1. Agent loop 8 tahap dengan state machine DB (SELESAI)
2. 7 tools function-calling dengan tier + guardrail + audit (SELESAI)
3. Structured output LLM OpenAI-compatible + mode MOCK offline (SELESAI)
4. Human approval queue + web UI (approve/reject/reply PIC) (SELESAI)
5. Memory case_history + injection ke prompt (SELESAI)
6. Audit append-only via DB trigger (SELESAI)
7. Golden set evaluation harness (`run_eval.py`) — Fase 3
8. Telegram bot untuk PIC + tombol jawaban — Fase 2
9. Google Sheets reader sebagai sumber data alternatif — Fase 2
10. Docker deployment (compose: app + PostgreSQL) — Fase 4
11. Dokumentasi lengkap (repo `docs/`) — Fase 4

### Out-of-scope / Non-goals (kunci disiplin scope)

1. **TIDAK** membangun frontend dashboard grafis (grafik, chart library).
   API `/api/stations` cukup; visualisasi = tanggung jawab sistem lain.
2. **TIDAK** RAG / pgvector / embedding search. Memory = SQL terstruktur.
   (Upgrade path tercatat di docs/SCHEMA.md, jangan build sebelum dibutuhkan.)
3. **TIDAK** multi-tenant / multi-factory. Satu pabrik, satu DB.
4. **TIDAK** fine-tuning model atau training ML. Cloud API + prompt saja.
5. **TIDAK** agent multi-LLM / model routing / self-reflection loop.
6. **TIDAK** autopilot penuh: aksi keuangan/sanksi/penilaian karyawan TIDAK
   ADA tool-nya sama sekali (guardrail by absence).
7. **TIDAK** SSO / OAuth login. Web UI = internal demo, tanpa auth (Fase 4:
   API key sederhana kalau diminta).
8. **TIDAK** mobile app / kiosk. Web HTML responsif cukup.
9. **TIDAK** real-time streaming data / WebSocket. Poll per interval cukup.
10. **TIDAK** migrasi dari legacy MES / integrasi sistem vendor lain.
    Sumber data = seed/simulasi → Google Sheets (Fase 2) → selesai.

## 6. Acceptance Criteria (per fitur, verifiable)

| ID | Fitur | Kriteria LULUS |
|---|---|---|
| AC-1 | Agent cycle | `run_agent_cycle()` pada data anomali → case+task dibuat; data sehat → no-op |
| AC-2 | Guardrail PIC | `create_task` PIC asing → PermissionError, tercatat di audit |
| AC-3 | Rate limit | >1 task/stasiun/hari → ditolak |
| AC-4 | Audit immutable | UPDATE/DELETE audit_log → ditolak DB |
| AC-5 | Approval queue | Eskalasi menunggu `approvals.status=pending` sampai manusia putuskan |
| AC-6 | PIC reply | Task fixed → case masuk verify → yield pulih → close + memory |
| AC-7 | Structured output | Output LLM lolos Pydantic schema ATAU ditolak (tidak pernah crash) |
| AC-8 | Anti-hallucination | Analysis tanpa digit di evidence → REJECT |
| AC-9 | Eval harness | `python run_eval.py` → skor + `eval_report.md` |
| AC-10 | Telegram | PIC menerima task + tombol fixed/cannot (Fase 2) |
| AC-11 | Sheets | Data dari Google Sheet dibaca agent (Fase 2) |
| AC-12 | Docker | `docker compose up` → sistem jalan penuh (Fase 4) |

## 7. Metrik operasional (saat live)

- Precision deteksi anomali (dari golden set + review manual)
- False alarm per minggu
- Median waktu anomali → task terkirim
- % case closed dengan outcome "fixed"

## 8. Risiko & Mitigasi

| Risiko | Mitigasi |
|---|---|
| LLM halusinasi analisis | Wajib evidence berdigit; reject jika tidak |
| PIC salah disebut nama | Allowlist di config; PIC di luar list = eskalasi |
| Spam task ke stasiun | Rate limit 1/stasiun/hari |
| Biaya API | Mock mode utk dev/CI; interval kontrol via env |
| Scope creep (fitur "keren") | Non-goals §5.2 dikunci; perubahan lewat docs/DECISIONS.md |

## 9. Link dokumen pendukung

- `docs/PLAN.md` — roadmap fase + definition of done
- `docs/SCHEMA.md` — ERD, tabel, state machine, upgrade path
- `docs/RULES.md` — aturan pengembangan + guardrail behavior
- `docs/WORKFLOW.md` — detail alur 8 tahap + contoh jejak audit
- `docs/EVALUATION.md` — desain golden set & metrik
- `docs/DEPLOYMENT.md` — lokal, Docker, env vars, recovery
- `docs/SECURITY.md` — secrets, access, audit, backup
- `docs/DECISIONS.md` — log keputusan (ADR ringkas, append-only)
