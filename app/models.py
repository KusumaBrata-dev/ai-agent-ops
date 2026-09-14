"""ORM models — agent.db (SQLite dev / PostgreSQL prod)."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    event,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from .config import DATABASE_URL

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    role: Mapped[str] = mapped_column(String(20))  # pic | lead_qc | head_production
    telegram: Mapped[str] = mapped_column(String(50), default="")

    @property
    def is_lead(self) -> bool:
        return self.role in ("lead_qc", "head_production")


class DailyProduction(Base):
    """Sumber data operasional — prod: diganti dari Google Sheets/MES."""
    __tablename__ = "daily_production"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[dt.date] = mapped_column(Date, index=True)
    station: Mapped[str] = mapped_column(String(20), index=True)
    output: Mapped[int] = mapped_column(Integer)
    ng_qty: Mapped[int] = mapped_column(Integer)
    yield_pct: Mapped[float] = mapped_column(Float)  # (output-ng)/output*100


class Case(Base):
    __tablename__ = "cases"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    station: Mapped[str] = mapped_column(String(20), index=True)
    status: Mapped[str] = mapped_column(String(20), default="observe")
    # status: observe|analyzed|assigned|followup|escalated|verify|closed|rejected
    analysis: Mapped[str] = mapped_column(Text, default="")
    recommendation: Mapped[str] = mapped_column(Text, default="")
    evidence: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    tasks: Mapped[list["Task"]] = relationship(back_populates="case")


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    pic: Mapped[str] = mapped_column(String(50))
    station: Mapped[str] = mapped_column(String(20))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="open")
    # status: open|in_progress|fixed|rejected|overdue
    due_date: Mapped[dt.date] = mapped_column(Date)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    approved_by: Mapped[str] = mapped_column(String(50), default="")  # kosong = auto-tier

    case: Mapped[Case] = relationship(back_populates="tasks")


class Approval(Base):
    """Antrean human approval untuk aksi tier=approval."""
    __tablename__ = "approvals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    action: Mapped[str] = mapped_column(String(30))       # escalate_to_lead | close_case
    payload: Mapped[str] = mapped_column(Text)           # JSON detail
    status: Mapped[str] = mapped_column(String(10), default="pending")  # pending|approved|rejected
    requested_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    decided_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    decided_by: Mapped[str] = mapped_column(String(50), default="")


class CaseHistory(Base):
    """Memory: ringkasan kasus lama, diinjeksi ke prompt analisis berikutnya."""
    __tablename__ = "case_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    station: Mapped[str] = mapped_column(String(20), index=True)
    summary: Mapped[str] = mapped_column(Text)
    outcome: Mapped[str] = mapped_column(String(20))  # fixed | not_fixed
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)


class AuditLog(Base):
    """Append-only. Di SQLite: trigger blok UPDATE/DELETE; di PG: sama + policy."""
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    actor: Mapped[str] = mapped_column(String(20))   # agent | approver | pic
    action: Mapped[str] = mapped_column(String(40))
    detail: Mapped[str] = mapped_column(Text)        # JSON: tool, args, result


def init_db() -> None:
    Base.metadata.create_all(engine)
    _install_audit_triggers()


def _install_audit_triggers() -> None:
    if DATABASE_URL.startswith("sqlite"):
        with engine.begin() as conn:
            conn.exec_driver_sql(
                "CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit_log "
                "BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END;"
            )
            conn.exec_driver_sql(
                "CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit_log "
                "BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END;"
            )
        return
    # PostgreSQL: idempotent — aman dipanggil tiap startup (F4.2)
    pg_sql = """
    CREATE OR REPLACE FUNCTION forbid_audit_mutation() RETURNS trigger AS $$
    BEGIN RAISE EXCEPTION 'audit_log is append-only'; END;
    $$ LANGUAGE plpgsql;
    DROP TRIGGER IF EXISTS audit_no_update ON audit_log;
    CREATE TRIGGER audit_no_update BEFORE UPDATE ON audit_log
        FOR EACH ROW EXECUTE FUNCTION forbid_audit_mutation();
    DROP TRIGGER IF EXISTS audit_no_delete ON audit_log;
    CREATE TRIGGER audit_no_delete BEFORE DELETE ON audit_log
        FOR EACH ROW EXECUTE FUNCTION forbid_audit_mutation();
    """
    with engine.begin() as conn:
        conn.exec_driver_sql(pg_sql)
