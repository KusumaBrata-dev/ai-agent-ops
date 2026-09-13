# WORKFLOW — Alur 8 Tahap & Jejak Contoh

## 1. Siklus hidup agent

```
[SCHEDULER / POST /agent/run]
   │
   ▼ untuk tiap stasiun TANPA case aktif:
1. OBSERVE    tools.get_production_data(station, 7 hari)
2. ANALYZE    llm.call_llm(prompt) → AnalysisResult (Pydantic)
              guardrail: evidence harus berdigit, PIC dari allowlist
3. RECOMMEND  disimpan ke cases(analysis, recommendation, evidence)
4. ASSIGN     tools.create_task → guardrail allowlist + rate limit
              gagal guardrail → request_escalation (ANTRE, tidak paksa)
5. FOLLOW-UP  tiap cycle: tools.get_overdue_tasks → send_reminder
6. ESCALATE   task overdue → request_escalation → approval manusia
7. VERIFY     PIC reply fixed → cek yield terbaru ≥ threshold
8. CLOSE      record_case_outcome → case_history (memory) + status closed
```

## 2. Contoh jejak nyata (dari smoke test)

Data: SMT-01 5 hari terakhir yield ±87% (threshold 95%).

```
audit_log:
  agent analysis_recorded {case 1, station SMT-01, confidence 0.8,
                           evidence "2026-09-08 | 1073 | 137 | 87.2"}
  agent create_task      {task 1, case 1, pic "Budi", station SMT-01}

cases:    id=1 SMT-01 status=assigned evidence=...87.2
tasks:    id=1 Budi @ SMT-01 open due=H+1

guardrail test: create_task(pic="Hacker", SMT-01)
  → PermissionError pic_not_in_allowlist
  → audit agent guardrail_blocked {reason: pic_not_in_allowlist}
```

## 3. Percakapan LLM (apa yang dikirim & diterima)

**Prompt** (template `app/schemas.py`):
```
Kamu AI Agent QC di pabrik elektronik. Analisis data produksi stasiun SMT-01.
DATA 7 HARI (tanggal | output | NG | yield%): ...
AMBANG: yield minimum 95.0%.
MEMORY riwayat stasiun ini: ...
ATURAN KETAT:
- evidence WAJIB berisi angka dari data di atas...
- suggested_pic WAJIB salah satu dari: Budi, Sari...
Panggil function record_analysis dengan hasil.
```

**Dikirim ke API** dengan `tools=[record_analysis schema]` +
`tool_choice` dipaksa → LLM menjawab lewat function call, bukan teks bebas.

**Diterima** → `AnalysisResult.model_validate(...)` → lolos/ditolak.
Ditolak = TIDAK ada case (bukan retry sampai lolos — RULES §5).

Mode `MOCK_LLM=1`: analyzer statistik lokal menghasilkan JSON bentuk sama —
semua downstream (guardrail, audit, task) tidak tahu bedanya. Itu bukti
arsitektur provider-agnostic.

## 4. Alur approval (eskalasi)

1. Trigger: task overdue, PIC tidak di allowlist, atau LLM tanpa evidence
2. Agent: `request_escalation` → cases.status=escalated, approvals baru (pending)
3. Manusia buka web UI `/` → kolom "Approval Pending"
4. Approve → system buat task utk lead_qc dengan `approved_by` terisi
5. Reject → case tetap escalated tanpa task; keputusan tercatat di audit

## 5. Alur reply PIC

1. Task muncul di web UI (Fase 2: Telegram juga)
2. PIC isi nama + pilih `in_progress | fixed | cannot_fix`
3. `fixed` → case masuk VERIFY; cycle berikut cek yield
   - yield ≥ threshold → close (tier approval) atau auto-close via data
   - yield belum pulih → tetap verify, PIC/lead yang putuskan lanjutan
4. `cannot_fix` → task kembali open + eskalasi otomatis ke lead
