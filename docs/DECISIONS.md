# DECISIONS — Log Keputusan (append-only, format ADR ringkas)

Format: nomor · tanggal · keputusan · alasan · dampak. Tambah entri baru di
bawah; JANGAN edit/hapus entri lama.

---

D001 · 2026-09-13 · Stack: Python/FastAPI/SQLAlchemy/SQLite-dev
Alasan: job desc minta Python; FastAPI standar de-facto; SQLite = zero-setup
untuk dev/CI. Dampak: prod naik ke PostgreSQL via DATABASE_URL (sudah
disiapkan di config).

D002 · 2026-09-13 · LLM via API OpenAI-compatible, default OpenRouter free tier
Alasan: tidak perlu spek lokal; ganti provider = ganti env. Dampak: tidak
ada ketergantungan SDK vendor — cukup httpx + JSON.

D003 · 2026-09-13 · Mode MOCK_LLM untuk dev/CI/eval
Alasan: eval harus deterministik & gratis; guardrail/audit/workflow diuji
tanpa LLM. Dampak: semua downstream tidak tahu beda mock vs live.

D004 · 2026-09-13 · Guardrail di KODE, prompt hanya instruksi analisis
Alasan: prompt bisa bocor/ditipu; kode tidak. Allowlist+tier+rate = tools.py.
Dampak: LLM "nakal" maksimal menghasilkan output yang ditolak, tidak aksi.

D005 · 2026-09-13 · Memory = SQL (case_history), BUKAN RAG/pgvector
Alasan: kebutuhan aktual = riwayat kasus per stasiun; SQL cukup dan auditable.
Dampak: upgrade path tercatat di SCHEMA.md §5 — bangun hanya saat benar-benar
perlu (ribuan kasus).

D006 · 2026-09-13 · Aksi sensitif (eskalasi, close) = tier approval
Alasan: job desc eksplisit minta human-in-the-loop untuk keputusan penting;
juga aman untuk demo. Dampak: agent tidak bisa close case sendiri tanpa
approval (kecuali verify via data yield — didiskusikan di D008).

D007 · 2026-09-13 · Satu case aktif per stasiun
Alasan: sederhana, cegah spam, cukup untuk domain. Dampak: anomali baru saat
case aktif di-skip; setelah close, cycle berikut bisa buka case baru.

D008 · 2026-09-13 · Verify close pakai data yield (bukan opini LLM)
Alasan: penutupan kasus harus berbasis bukti data (yield pulih), bukan klaim.
Dampak: LLM tidak terlibat tahap verify — murni rule data + approval.

D009 · 2026-09-13 · Telegram & Google Sheets = Fase 2 (setelah eval harness)
Alasan: PLAN.md urutan terkunci — integrasi tanpa alat ukur = berbahaya.
Dampak: PRD AC-10/11 menunggu Fase 2.

D010 · 2026-09-13 · Web UI tanpa auth di fase portfolio
Alasan: internal demo. Dampak: SECURITY.md mencatat penambahan API key
sederhana sebagai syarat bila di-host di server bersama.

D011 · 2026-09-13 · Write-limit agent session: sisa file (run_eval.py dsb.)
dilanjutkan sesi berikut
Alasan: batas tooling 15 file/sesi. Dampak: Fase 2.1 memulai dari draft eval.

D012 · 2026-09-13 · Docs-first: PRD/PLAN/SCHEMA/RULES dikunci sebelum Fase 2
Alasan: permintaan eksplisit user — agar project tidak keluar dari plan.
Dampak: semua fitur baru HARUS lewat entri DECISIONS + update PRD dulu
(lihat RULES §1).
