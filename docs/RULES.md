# RULES — Aturan Pengembangan & Guardrail ai-agent-ops

Dokumen ini yang mencegah project keluar dari plan. Dibaca SEBELUM koding
dan SETIAP kali tergoda menambah fitur.

## 1. Scope Lock (prioritas tertinggi)

1. **PRD.md adalah kontrak.** Fitur di luar PRD §5.1 = TIDAK dibangun.
2. Mau tambah/ubah fitur? Urutan WAJIB:
   a. Tulis entri di `DECISIONS.md` (apa, kenapa, dampak)
   b. Update PRD (in-scope / non-goals)
   c. Baru tulis kode
   Tidak boleh langsung koding karena "sebentar doang".
3. Non-goals PRD = larangan keras, bukan "nanti dulu". Contoh: tidak ada
   chart frontend, tidak ada RAG, tidak ada multi-tenant.
4. Setiap PR review (termasuk self-review via AI assistant): pertanyaan
   pertama — "ini masih dalam PRD?" Bukan "ini kode bagus?"

## 2. Aturan Agent Behavior (tidak bisa dinegosiasi)

| # | Aturan | Enforcement |
|---|---|---|
| R1 | Aksi tanpa bukti = REJECT | validasi evidence berdigit, kode |
| R2 | PIC di luar allowlist = eskalasi, bukan paksa | PermissionError di create_task |
| R3 | Max 1 task/stasiun/hari | rate limit di create_task |
| R4 | Eskalasi & close = keputusan manusia | tier approval + tabel approvals |
| R5 | Semua aksi tercatat | audit() dipanggil di SEMUA tool |
| R6 | Agent tidak punya tool keuangan/sanksi/HR | tidak ada fungsinya — jangan tambah |
| R7 | Satu case aktif per stasiun | filter di run_agent_cycle |
| R8 | Prompt tidak berisi secret | key hanya via env |

R1–R8 diuji otomatis: skenario di `run_eval.py` + `tests/smoke.py`.
Mengubah perilaku R1-R8 = perubahan PRD + DECISIONS + eval diperbarui.

## 3. Aturan Koding

1. **Python 3.11+**, tanpa fitur eksotis. Boring > clever.
2. **Dependency**: hanya dari requirements.txt. Dependency baru = alasan di
   DECISIONS. Target tetap minimal (jika bisa stdlib → stdlib).
3. **DB access**: selalu via `models.SessionLocal()` context manager —
   tidak ada session global/long-lived (pernah kena DB locked).
4. **Error**: tool raise exception spesifik (PermissionError/ValueError);
   agent loop menangkap, audit `cycle_error`, lanjut — loop tidak boleh mati.
5. **No business logic di prompt.** Prompt hanya instruksi format/analisis.
   Keputusan hard (allowlist, tier, rate) selalu di KODE. Prompt bisa bocor;
   kode tidak.
6. **Config di agent_config.yaml / .env** — tidak ada magic number di kode.
7. **File baru**: satu tanggung jawab, <300 baris. Melebihi → pecah.
8. **Test**: tiap perilaku baru minimal 1 skenario eval/smoke. Non-trivial
   logic tanpa test = belum selesai.

## 4. Aturan Git

1. Commit message konvensional: `feat(tools): ...`, `fix(agent): ...`,
   `docs(prd): ...`, `test(eval): ...`
2. Branch: `main` stabil (eval hijau), kerja di `feat/<nama>`, squash merge.
3. JANGAN commit: `.env`, `agent.db`, `*.log`, `__pycache__`, hasil eval lama.
4. Secret di commit (walau cuma "sebentar") = ganti key, tulis post-mortem
   di SECURITY.md.

## 5. Aturan LLM Usage (saat live)

1. Dev & CI pakai `MOCK_LLM=1`. LLM live hanya untuk: eksperimen analisis,
   demo, sesi eval tertentu.
2. Jangan kirim data > yang dibutuhkan prompt (7 hari data cukup).
3. Output LLM TIDAK PERNAH dipercaya mentah — selalu lewat Pydantic
   AnalysisResult + guardrail evidence. LLM gagal validasi = case tidak dibuat
   (bukan diretry sampai lolos).
4. Jangan loop panggil LLM tanpa batas — 1 call per stasiun per cycle.

## 6. Definition of "Selesai"

Fitur baru dianggap selesai HANYA jika:
1. Kode jalan + smoke test pass
2. Ada skenario eval (jika mengubah perilaku agent)
3. Dokumen terkait di-update (PRD/SCHEMA/RULES/WORKFLOW)
4. Audit trail merekam aksi barunya
5. Tidak melanggar R1–R8 dan non-goals PRD

## 7. Anti-Pattern yang Pernah Terjadi (belajaran repo ini)

- Session DB lupa ditutup di test → `database is locked` (sudah: db.close()
  + context manager).
- Edit file via PowerShell Set-Content dengan string complex → syntax error
  mojibake (sudah: pakai edit tool).
- Write-limit 15 file per agent session → sisa file lanjut sesi baru
  (sudah: catat di DECISIONS).
