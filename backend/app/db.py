"""
Database engine/session setup. Dialect-agnostic by design — every model
and query in this app goes through SQLAlchemy's ORM/Core, never raw
string-interpolated SQL, so the same code runs unmodified against SQLite
(dev), Postgres, or MySQL (prod), controlled entirely by DATABASE_URL.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

_connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=_connect_args,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def sync_schema() -> None:
    """Idempotent, additive-only schema sync: creates any missing tables
    (create_all) and adds any columns present on a model but missing from
    its existing table (create_all never alters an existing table).

    Existing-install upgrades used to depend on someone remembering to run
    a one-off migrate_*.py script after pulling model changes — miss that
    step and every query touching the new column 500s in production. This
    runs automatically on every startup instead, so a model change can
    never again outrun the live schema. Never drops or alters existing
    columns, only adds ones that don't exist yet.
    """
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue  # just created above, already has every column
            existing_columns = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing_columns:
                    continue
                # Always added nullable, even if the model marks it NOT NULL:
                # existing rows have no value to backfill, and a NOT NULL
                # ADD COLUMN without a default fails outright on MySQL/
                # Postgres once the table has any rows. App code already
                # has to tolerate None on a freshly-added column anyway.
                ddl_type = column.type.compile(dialect=engine.dialect)
                conn.execute(text(
                    f"ALTER TABLE {table.name} ADD COLUMN {column.name} {ddl_type}"
                ))


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    """For use outside request handlers (scripts, background jobs)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
