# SECURITY — Secrets, Access, Audit, Boundary

## 1. Secrets

- API key HANYA via `OPENAI_API_KEY` env / .env. Nol hardcode. Nol di log.
- `.env` ada di .gitignore; commit `.env.example` (nilai kosong) sebagai kontrak.
- Kebocoran key (walau sempat) = ROTASI key + entri post-mortem di file ini.
- agent_config.yaml boleh di-commit: isinya kebijakan (allowlist, tier),
  bukan kredensial. Jangan pernah taruh token di situ.

## 2. Access control & boundary

| Permukaan | Siapa | Kontrol |
|---|---|---|
| Web UI `/` (panel+approval) | internal demo | Fase 4: API key sederhana bila di-deploy di server |
| `/agent/run` | operator | idem |
| `/api/stations` | dashboard lain | read-only, tidak ada data rahasia |
| Tool create_task | AGENT | allowlist PIC + rate limit — di kode, bukan prompt |
| Aksi tier approval | AGENT | hanya bisa MENGANTRE; eksekusi butuh manusia |
| Keuangan/sanksi/HR | — | TIDAK ADA TOOL (guardrail by absence, PRD non-goal) |

Prinsip: **prompt = saran, kode = hukum.** Instruksi ke LLM dianggap input
tidak tepercaya; semua batas keputusan ada di tools.py (lihat RULES R1–R8).

## 3. Audit trail

- Semua aksi (agent, approver, pic) → `audit_log` append-only.
- SQLite: trigger RAISE(ABORT). PostgreSQL (Fase 4): trigger + REVOKE.
- Audit = sumber kebenaran saat rekonsiliasi "kenapa agent kirim X ke Y".
- Isi detail JSON — JANGAN pernah menulis token/password ke field detail.

## 4. Data

- Data produksi (seed/Sheets) = data operasional internal, bukan PII.
- History & evidence = snapshot angka, boleh dibawa ke portfolio.
- Sebelum repo public: pastikan tidak ada nama perusahaan asli/nama karyawan
  asli — ganti dengan data dummy (aturan portfolio privacy).

## 5. Dev/Prod separation

- Dev: SQLite + MOCK_LLM=1 + AGENT_INTERVAL_SEC=30.
- Prod: PostgreSQL + LLM live + interval 3600 + .env terpisah.
- Jangan pernah arahkan dev ke DB prod. Migrasi schema lewat file SQL
  ter-review (Fase 4), bukan edit langsung.
