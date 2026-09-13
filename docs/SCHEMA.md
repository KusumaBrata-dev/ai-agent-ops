# SCHEMA — Data Model & State Machine

## 1. ERD (teks)

```
users 1───n tasks n───1 cases 1───n case_history
                     │
                     ├── n approvals (via case_id di payload JSON)
daily_production ────┘ (station adalah join key, bukan FK — data sumber)
audit_log (mandiri, append-only)
```

Relasi kunci:
- `cases 1—n tasks`: satu kasus bisa punya task PIC + task eskalasi.
- `cases 1—n case_history`: saat close, ringkasan kasus disalin ke history
  (memory). History tidak pernah diubah setelah ditulis.
- `daily_production` TIDAK ber-FK ke cases: data produksi datang dari sumber
  eksternal (Sheets/MES); analisis membuat snapshot evidence di `cases.evidence`.

## 2. Tabel

### users
| Kolom | Tipe | Catatan |
|---|---|---|
| id | PK | |
| name | str unique | harus cocok `pic_allowlist` di agent_config.yaml |
| role | str | pic \| lead_qc \| head_production |
| telegram | str | chat id / username — diisi Fase 2 |

### daily_production (sumber data — "Sheets" di fase portfolio)
| Kolom | Tipe | Catatan |
|---|---|---|
| id | PK | |
| date | date, index | |
| station | str, index | SMT-01, ASY-01, ... |
| output | int | unit/hari |
| ng_qty | int | |
| yield_pct | float | (output-ng)/output*100 — dihitung saat ingest |

Ingest rule: upsert by (date, station) — idempotent, sumber boleh dikirim ulang.

### cases (state machine utama)
| Kolom | Tipe | Catatan |
|---|---|---|
| id | PK | |
| station | str index | satu case AKTIF per stasiun (agent skip jika ada) |
| status | str | lihat §3 |
| analysis | text | hasil LLM |
| recommendation | text | |
| evidence | text | WAJIB mengandung digit (guardrail) |
| confidence | float 0-1 | |
| created_at / updated_at | datetime | |

### tasks
| Kolom | Tipe | Catatan |
|---|---|---|
| id | PK | |
| case_id | FK cases | |
| pic / station | str | |
| description | text | instruksi konkret utk PIC |
| status | open \| in_progress \| fixed \| overdue | cannot_fix → tetap open + eskalasi |
| due_date | date | default H+1 |
| approved_by | str | kosong = tier auto; isi nama approver = hasil approval |

### approvals (human-in-the-loop queue)
| Kolom | Tipe | Catatan |
|---|---|---|
| id | PK | |
| action | str | escalate_to_lead \| close_case |
| payload | text JSON | {case_id, station, reason} |
| status | pending \| approved \| rejected | |
| decided_by / decided_at | | diisi manusia |

Invarian: aksi tier=approval TIDAK PERNAH dieksekusi tanpa baris approval
`status=approved`. Eksekusi eskalasi = buat task lead dengan `approved_by` terisi.

### case_history (memory)
| station | summary | outcome=fixed\|not_fixed | created_at |
Dipakai `get_case_history()` → string riwayat → injeksi ke prompt analisis.
Satu-satunya "context engine" fase ini. Tidak ada embedding.

### audit_log (append-only)
| ts | actor (agent\|approver:x\|pic:x) | action | detail JSON |
SQLite: trigger BEFORE UPDATE/DELETE → RAISE(ABORT).
PostgreSQL: trigger func + REVOKE UPDATE, DELETE (Fase 4).

## 3. State Machine — Case.status

```
            ┌─────────(tidak ada anomali)──────────────┐
            ▼                                          │(case baru saat cycle berikut)
[observe]──anomali──▶[analyzed]──guardrail ok──▶[assigned]
                        │                              │      │
                        │guardrail tolak              │      │due lewat
                        ▼                              ▼      ▼
                   [escalated]◀──request_escalation──[followup]
                        │                              │
                  approval manusia                PIC fixed
                        ▼                              ▼
                   task lead                   [verify]──yield pulih──▶[closed]
                                                        │              │
                                              yield belum pulih  record_case_outcome
                                                        ▼         → case_history
                                                  tetap verify
                                                        (cycle berikut cek lagi)
```

Transisi ILLEGAL (ditolak oleh kode, bukan hanya prompt):
- assigned → closed (harus lewat verify)
- escalated → closed tanpa approval
- case baru untuk stasiun yang masih punya case aktif
- task dibuat tanpa case
- analisis masuk tanpa evidence berdigit

## 4. Tier aksi (guardrail execute-level)

| Tool | Tier | Siapa bisa eksekusi |
|---|---|---|
| get_production_data, get_case_history, get_overdue_tasks | auto (read) | agent |
| create_task, send_reminder | auto | agent (dengan allowlist + rate limit) |
| request_escalation | approval | agent mengANTRE, manusia eksekusi |
| close_case (record_case_outcome) | approval | sama — kecuali verify otomatis via yield data |
| (tidak ada tool keuangan/sanksi/HR) | forbidden | TIDAK ADA TOOL-NYA — guardrail by absence |

## 5. Upgrade path (jangan dibangun sebelum dibutuhkan — lihat PRD non-goals)

| Kebutuhan nyata baru | Upgrade |
|---|---|
| Ribuan kasus, pencarian semantik riwayat | case_history → pgvector embedding |
| Banyak stasiun + banyak agent paralel | queue (Redis/RQ) pengganti loop |
| Data realtime < 1 menit | polling → event push (webhook MES) |
| Multi-factory | tenant_id di semua tabel + auth |
