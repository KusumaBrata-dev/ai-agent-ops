"""FastAPI entrypoint: /docs, UI, agent scheduler."""
from __future__ import annotations

import asyncio
import contextlib
import threading

from fastapi import FastAPI

from . import models
from .agent import run_agent_cycle
from .audit import audit
from .config import AGENT_ENABLED, AGENT_INTERVAL_SEC

app = FastAPI(title="AI Agent Ops", version="0.2.0")

# Overlap guard: cycle berjalan -> cycle berikut skip (PLAN 2.5).
_cycle_lock = threading.Lock()


def _run_cycle_guarded() -> dict | None:
    if not _cycle_lock.acquire(blocking=False):
        audit("agent", "cycle_skipped", reason="cycle_masih_berjalan")
        return None
    try:
        return run_agent_cycle()
    finally:
        _cycle_lock.release()


async def _agent_loop():
    while True:
        try:
            report = await asyncio.to_thread(_run_cycle_guarded)
            if report and any(report.values()):
                audit("agent", "cycle_done", **report)
        except Exception as e:  # noqa: BLE001 — agent loop tidak boleh mati
            audit("agent", "cycle_error", error=str(e))
        await asyncio.sleep(AGENT_INTERVAL_SEC)


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI):
    models.init_db()
    task = asyncio.create_task(_agent_loop()) if AGENT_ENABLED else None
    yield
    if task:
        task.cancel()


app.router.lifespan_context = lifespan

from .web import router as web_router  # noqa: E402
from .sheets import router as sheets_router  # noqa: E402
from .telegram import router as telegram_router  # noqa: E402

app.include_router(web_router)
app.include_router(sheets_router)
app.include_router(telegram_router)


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/agent/run")
def run_once():
    """Jalankan satu cycle manual (utk demo / testing)."""
    return _run_cycle_guarded() or {"skipped": "cycle_masih_berjalan"}
