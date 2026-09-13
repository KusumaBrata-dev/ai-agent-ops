import os
os.environ.setdefault("MOCK_LLM", "1")
from app import models, tools
from app.agent import run_agent_cycle

try:
    tools.create_task(9999, "Hacker", "SMT-01", "inject")
    raise SystemExit("FAIL guardrail")
except PermissionError as e:
    assert "pic_not_in_allowlist" in str(e)
print("guardrail PIC: OK")

import sqlite3
db = sqlite3.connect("agent.db")
try:
    db.execute("UPDATE audit_log SET actor = 'x' WHERE id = 1"); db.commit()
    raise SystemExit("FAIL audit mutable")
except sqlite3.OperationalError:
    pass
except sqlite3.IntegrityError:
    pass
db.close()
print("audit immutable: OK")

report = run_agent_cycle()
with models.SessionLocal() as s:
    print("agent cycle: OK, tasks=", s.query(models.Task).count())


