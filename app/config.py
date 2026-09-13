from __future__ import annotations

import os

import yaml
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "agent_config.yaml")

OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "gemini/gemini-2.0-flash-exp:free")
MOCK_LLM = os.getenv("MOCK_LLM", "0") == "1"

DATABASE_URL = os.getenv("DATABASE_URL") or f"sqlite:///{os.path.join(BASE_DIR, 'agent.db')}"
AGENT_INTERVAL_SEC = int(os.getenv("AGENT_INTERVAL_SEC", "30"))
AGENT_ENABLED = os.getenv("AGENT_ENABLED", "1") == "1"
SHEETS_CSV_URL = os.getenv("SHEETS_CSV_URL", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_ENABLED = bool(TELEGRAM_BOT_TOKEN)
TELEGRAM_WEBHOOK_URL = os.getenv("TELEGRAM_WEBHOOK_URL", "")  # host publik, deploy


def _load_yaml() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


CFG = _load_yaml()
PIC_ALLOWLIST: dict[str, list[str]] = CFG.get("pic_allowlist", {})
ACTION_TIERS: dict[str, str] = CFG.get("action_tiers", {})
ESCALATION_MATRIX: dict[str, str] = CFG.get("escalation_matrix", {})
RATE_LIMIT: dict = CFG.get("rate_limit", {})
YIELD_THRESHOLD: float = float(CFG.get("yield_threshold", 95.0))
