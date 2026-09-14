# DEPLOYMENT — Local, Docker, Recovery

## 1. Dev lokal (Windows/Linux)

```powershell
python -m venv .venv
.\.venv\Scripts\activate        # Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env          # isi OPENAI_API_KEY atau MOCK_LLM=1
python seed.py                  # DB + data demo
uvicorn app.main:app --reload   # http://localhost:8000
```

Smoke: `python tests/smoke.py` (set `MOCK_LLM=1`, `AGENT_ENABLED=0` di .env
untuk kontrol manual via POST /agent/run).

## 2. Variabel environment

| Var | Wajib | Default | Catatan |
|---|---|---|---|
| OPENAI_BASE_URL | tidak | openrouter | ganti provider = ganti ini |
| OPENAI_API_KEY | ya* | — | *wajib kalau MOCK_LLM≠1 |
| MODEL_NAME | tidak | gemini flash free | |
| MOCK_LLM | tidak | 0 | 1 = offline dev/CI |
| DATABASE_URL | tidak | sqlite ./agent.db | prod: postgresql://... |
| AGENT_INTERVAL_SEC | tidak | 30 | demo; prod: 3600 |
| AGENT_ENABLED | tidak | 1 | 0 = agent idle, API tetap hidup |

Aturan: **tidak ada nilai lain hardcode**. Tambah env var baru → update
tabel ini (dokumen = kontrak config).

## 3. Docker / Production (Fase 4 — file siap)

```bash
# .env minimal: OPENAI_API_KEY (atau MOCK_LLM=1 utk demo)
docker compose up -d --build     # app + PostgreSQL 16
# cek: http://localhost:8000/health
```

- `db/init/01_audit_triggers.sql` jalan otomatis saat volume DB pertama
- App startup memasang ulang trigger secara idempotent (D018) — invarian
  append-only dijamin bahkan pada volume lama
- Healthcheck: `/health` tiap 60s, restart `unless-stopped`
- Password DB di compose = demo lokal; prod: ganti via env/secret manager

## 4. Operasional harian

- Log: stdout (uvicorn) + tabel audit_log (sumber kebenaran aksi agent)
- Cek sehat: `GET /health` → `{"ok":true}`; `/api/stations` → yield terakhir
- Interval jalan? Cek audit_log `cycle_done` / `cycle_error` terakhir.
  `cycle_error` beruntun → cek env (key, network) — loop tidak mati tapi idle.

## 5. Backup & Recovery

| Objek | Metode | Rhythm |
|---|---|---|
| agent.db / PostgreSQL | copy file (sqlite) / pg_dump | harian sebelum demo |
| .env | TIDAK di backup ke repo — simpan aman manual | sekali |
| eval_report.md | commit ke git (bukti portfolio) | per run eval |

Recovery: restore DB + `pip install` + `uvicorn app.main:app` — state machine
ada di DB, tidak ada state di memori yang hilang. Case aktif melanjutkan
dari status terakhir.

## 6. Runbook insiden

| Gejala | Cek | Aksi |
|---|---|---|
| Tidak ada case padahal yield turun | audit cycle_error | cek key/jaringan; POST /agent/run manual |
| Spam task | audit guardrail_blocked rate_limit | normal; kalau salah tingkatkan limit via yaml |
| PIC bilang tak menerima tugas | web UI + tasks | PIC lihat / panel; Fase 2: cek map telegram |
| Audit penuh | row count | arsip ke tabel audit_archive (Fase 4, jangan delete asli) |
