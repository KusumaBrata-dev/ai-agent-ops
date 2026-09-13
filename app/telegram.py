"""Telegram bot — PIC terima task + tombol jawaban (Fase 2.3, PLAN.md).

Arsitektur lazy (lihat DECISIONS D014):
- SEND  : Bot API sendMessage + inline keyboard (fixed / cannot) — httpx saja.
- ANSWER: dua jalur —
   a) lokal/tanpa host publik : keyboard berisi URL ke web UI /t/<task_id>
   b) deploy (TELEGRAM_WEBHOOK_URL diset) : tombol callback → Telegram POST
      ke /telegram/callback → update task di DB (logika sama dengan web form).

Setup: @BotFather → token → .env TELEGRAM_BOT_TOKEN. Map nama PIC → chat_id
via /telegram/register (PIC kirim /start ke bot lalu isi form).
"""
from __future__ import annotations

import json

import httpx
from fastapi import APIRouter, Form, HTTPException

from . import models
from .audit import audit
from .config import TELEGRAM_BOT_TOKEN, TELEGRAM_ENABLED, TELEGRAM_WEBHOOK_URL

router = APIRouter(prefix="/telegram", tags=["telegram"])

_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}" if TELEGRAM_ENABLED else None


def _send(chat_id: str, text: str, buttons: list[dict] | None = None) -> bool:
    if not _API:
        return False  # dev tanpa token: silent, task tetap di web UI
    payload: dict = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if buttons:
        payload["reply_markup"] = {"inline_keyboard": [buttons]}
    try:
        r = httpx.post(f"{_API}/sendMessage", json=payload, timeout=15.0)
        return r.status_code == 200
    except httpx.HTTPError:
        return False


def notify_task(task_id: int, pic_name: str, station: str, description: str, due) -> bool:
    """Dipanggil tools.create_task (via audit hook) — kirim ke PIC kalau ada chat_id."""
    with models.SessionLocal() as s:
        user = s.query(models.User).filter_by(name=pic_name).first()
    if not user or not user.telegram:
        return False

    if TELEGRAM_WEBHOOK_URL:  # tombol callback Telegram (deploy)
        buttons = [dict(text="✅ Selesai", callback_data=f"fixed:{task_id}"),
                   dict(text="❌ Tidak bisa", callback_data=f"cannot:{task_id}")]
    else:  # dev lokal: link ke web UI
        url = TELEGRAM_WEBHOOK_URL or ""
        buttons = [dict(text=f"Jawab di web (task {task_id})", url=f"{url}/")]
    return _send(user.telegram,
                 f"🔔 <b>Task {station}</b>\n{description}\nDue: {due}", buttons)


@router.post("/register")
def register(pic: str = Form(...), chat_id: str = Form(...)):
    """Admin mapping PIC → chat_id (PIC dapat chat_id dari @userinfobot)."""
    with models.SessionLocal() as s:
        user = s.query(models.User).filter_by(name=pic).one_or_none()
        if not user:
            raise HTTPException(404, f"user {pic} tidak ada")
        user.telegram = chat_id
        s.commit()
    audit("approver:system", "telegram_register", pic=pic)
    return {"ok": True, "pic": pic, "chat_id": chat_id}


@router.post("/callback")
async def telegram_callback(update: dict):
    """Webhook Telegram (deploy). Tombol fixed/cannot → update task."""
    cb = update.get("callback_query")
    if not cb:
        return {"ok": True}  # ignore non-callback
    data = cb.get("data", "")          # "fixed:12" | "cannot:12"
    chat_id = cb["message"]["chat"]["id"]
    action, _, task_id = data.partition(":")
    with models.SessionLocal() as s:
        user = s.query(models.User).filter_by(telegram=str(chat_id)).one_or_none()
        task = s.get(models.Task, int(task_id))
    if not user or not task:
        return {"ok": False}
    if user.name != task.pic:  # hanya PIC yang ditugaskan (RULES R2 spirit)
        audit("pic:" + user.name, "telegram_denied", task_id=task_id)
        return {"ok": False, "error": "bukan pemilik task"}
    with models.SessionLocal() as s:
        t = s.get(models.Task, int(task_id))
        t.status = "fixed" if action == "fixed" else "open"
        s.commit()
    audit(f"pic:{user.name}", "task_reply", task_id=int(task_id), reply=action,
          via="telegram")
    return {"ok": True}


@router.get("/setup-webhook")
def setup_webhook():
    """Set Telegram webhook → TELEGRAM_WEBHOOK_URL/telegram/callback. Deploy only."""
    if not (TELEGRAM_ENABLED and TELEGRAM_WEBHOOK_URL):
        raise HTTPException(400, "TELEGRAM_BOT_TOKEN / TELEGRAM_WEBHOOK_URL kosong")
    r = httpx.get(f"{_API}/setWebhook", params={
        "url": f"{TELEGRAM_WEBHOOK_URL}/telegram/callback",
        "allowed_updates": json.dumps(["callback_query"]),
    }, timeout=15.0)
    return r.json()
