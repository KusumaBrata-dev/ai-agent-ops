"""FastAPI entrypoint: /docs, UI, agent scheduler."""
from __future__ import annotations

import asyncio
import contextlib

from fastapi import FastAPI

from . import models
from .agent import run_agent_cycle
from .audit import audit
from .config import AGENT_ENABLED, AGENT_INTERVAL_SEC

app = FastAPI(title="AI Agent Ops", version="0.1.0")


@app.on_event("startup")
def startup():
    models.init_db()
    if AGENT_ENABLED:
        asyncio.get_event_loop().create_task(_agent_loop()) if False else None
        # (di bawah: pakai lifespan — lebih bersih)


async def _agent_loop():
    while True:
        try:
            report = await asyncio.to_thread(run_agent_cycle)
            if any(report.values()):
                audit("agent", "cycle_done", **report)
        except Exception as e:  # noqa: BLE001 — agent loop tidak boleh mati
            audit("agent", "cycle_error", error=str(e))
        await asyncio.sleep(AGENT_INTERVAL_SEC)


# Lifespan (FastAPI modern) — agent loop di sini.
@contextlib.asynccontextmanager
async def lifespan(_: FastAPI):
    models.init_db()
    task = asyncio.create_task(_agent_loop()) if AGENT_ENABLED else None
    yield
    if task:
        task.cancel()


app.router.lifespan_context = lifespan

from .web import router as web_router  # noqa: E402

app.include_router(web_router)


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/agent/run")
def run_once():
    """Jalankan satu cycle manual (utk demo / testing)."""
    return run_agent_cycle()
