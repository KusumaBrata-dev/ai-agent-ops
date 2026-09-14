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

D013 · 2026-09-13 · Sheets via CSV publish URL, BUKAN Sheets API resmi
Alasan: portfolio butuh baca data — CSV publish nol auth, nol dependency,
idempotent upsert (date,station). Dampak: private sheet / write-back →
upgrade ke service account (catat entri baru saat itu).

D014 · 2026-09-13 · Telegram: httpx Bot API send-only + callback webhook,
BUKAN framework python-telegram-bot
Alasan: butuh 3 hal saja (kirim task, tombol fixed/cannot, map chat_id) —
framework = dependency + proses polling terpisah. Dampak: fitur chat
interaktif penuh (command /tasks, dsb.) → baru pertimbangkan framework.

D015 · 2026-09-13 · Rate limit pakai UTC (utcnow), bukan tanggal lokal
Alasan: bug nyata — created_at UTC vs filter local midnight (UTC+7) bikin
rate limit bocor saat lewat tengah malam WIB. Dampak: satu sumber waktu
(UTC) untuk created_at + rate-limit. PRD AC-3 tetap hijau (eval E7).

D016 · 2026-09-13 · Sheets auto-sync di awal cycle, error → audit bukan crash
Alasan: sumber eksternal (internet/Google) tidak boleh matikan agent loop.
Dampak: cycle jalan dengan data terakhir yang ada bila sync gagal.

D017 · 2026-09-13 · LLM live = OpenRouter `nvidia/nemotron-3.5-lightning:free`
Alasan: model :free valid pertama yang lolos forced tool-call + structured
output pada verifikasi 2026-09-13 (gemma-4-31b upstream 429; gemini-2.0-flash-exp
sudah dihapus provider). Hasil: evidence angka nyata, PIC dari allowlist,
confidence 0.95. Dampak: MODEL_NAME di .env default baru; ganti model =
ganti env saja (arsitektur tetap provider-agnostic). Analisis LLM keluar
bahasa Inggris — acceptable utk portfolio (prompt bisa ditulis "jawab dalam
Bahasa Indonesia" saat operasional).

D018 · 2026-09-14 · PG trigger dipasang idempotent oleh app saat startup
Alasan: ORM create_all membuat tabel; trigger hanya bisa dipasang SETELAH
tabel ada. Init-SQL docker ternyata chicken-and-egg (jalan sebelum tabel
dibuat → kontainer DB gagal start — terbukti saat build fisik 2026-09-14,
init SQL dihapus). App startup memasang (CREATE OR REPLACE + DROP IF
EXISTS) menjamin invarian append-only selalu aktif, termasuk volume lama.
Dampak: startup butuh hak CREATE TRIGGER; invarian tetap teruji via
eval/smoke.

D019 · 2026-09-14 · Image Docker: python:3.12-slim, non-root user, healthcheck
/health
Alasan: baseline keamanan container tanpa perlu distroless (portfolio).
Dampak: upgrade distroless tercatat sebagai opsi saat operasional.

D020 · 2026-09-14 · Docker: build fisik terverifikasi via Docker Engine di WSL
Alasan: PC tanpa Docker Desktop — Engine + compose v5 di WSL Ubuntu cukup.
Pelajaran build: (1) init-SQL db/init = chicken-and-egg (tabel belum ada saat
init jalan) → dihapus, trigger dipasang app-startup saja (lihat D018);
(2) psycopg2-binary + python-multipart harus masuk requirements (dev SQLite
tidak menangkap); (3) exec/exec-idle VM WSL (vmIdleTimeout) bikin DNS compose
race — jalankan build+seed+verify dalam SATU sesi wsl sh -c.
Dampak: DoD Fase 4.4 tercapai — compose up → health OK, seed, agent cycle
assigned, PG trigger menolak UPDATE audit_log.
