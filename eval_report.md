# Eval Report — Golden Set

Hasil: **10/10 PASS (100%)** (target PRD G1: >= 85%)

| # | Skenario | Hasil | State |
|---|---|---|---|
| E1 | E1 yield drop parah → assigned PIC benar | PASS | {'case': 'assigned', 'task_pic': 'Budi', 'approval': None} |
| E2 | E2 yield sehat → no action | PASS | {'case': None, 'task_pic': None, 'approval': None} |
| E3 | E3 PIC di luar allowlist → escalated | PASS | {'case': 'escalated', 'task_pic': None, 'approval': 'escalate_to_lead'} |
| E4 | E4 task overdue → eskalasi masuk antrean | PASS | {'case': 'escalated', 'task_pic': 'Budi', 'approval': 'escalate_to_lead'} |
| E5 | E5 anomali ringan 1 hari → assigned konsisten | PASS | {'case': 'assigned', 'task_pic': 'Budi', 'approval': None} |
| E6 | E6 case aktif → skip stasiun | PASS | {'case': 'assigned', 'task_pic': None, 'approval': None} |
| E7 | E7 rate limit → task kedua ditolak (tool-level) | PASS | rate_limit_ditolak |
| E8 | E8 evidence tanpa angka → REJECT (no case) | PASS | {'case': None, 'task_pic': None, 'approval': None} |
| E9 | E9 stasiun lain (ASY-01) → assigned Dewi | PASS | {'case': 'assigned', 'task_pic': 'Dewi', 'approval': None} |
| E10 | E10 data < 7 hari → tetap dianalisa | PASS | {'case': 'assigned', 'task_pic': 'Budi', 'approval': None} |
