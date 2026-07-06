from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from sqlalchemy.pool import NullPool

from app.core.config import settings

# Supabase note:
#   - Session pooler (port 5432, *.pooler.supabase.com)  -> default QueuePool is fine.
#   - Transaction pooler (port 6543)                     -> set DB_USE_NULL_POOL=true,
#     since pgBouncer in transaction mode is incompatible with client-side connection pooling.
_engine_kwargs: dict = {"pool_pre_ping": True, "future": True}
if settings.DB_USE_NULL_POOL:
    _engine_kwargs["poolclass"] = NullPool

engine = create_engine(settings.DATABASE_URL, **_engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
