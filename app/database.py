"""Database configuration and session management for the Tour Planner app."""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, declarative_base, sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tour_planner.db")


def _build_engine(url: str):
    """Create the SQLAlchemy engine with backend-specific tuning."""

    engine_kwargs = {"future": True, "echo": False}
    dialect = make_url(url).get_backend_name()

    if dialect == "sqlite":
        # SQLite needs a special flag for usage with FastAPI's threaded test client.
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    else:
        # Enable pool pre-ping so long-lived connections recover gracefully.
        engine_kwargs["pool_pre_ping"] = True

    return create_engine(url, **engine_kwargs)


engine = _build_engine(DATABASE_URL)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

Base = declarative_base()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
