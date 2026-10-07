from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.pdf_dir.mkdir(parents=True, exist_ok=True)
settings.signature_dir.mkdir(parents=True, exist_ok=True)
settings.branding_dir.mkdir(parents=True, exist_ok=True)

_engine_kwargs: dict = {"pool_pre_ping": True}
if settings.sqlalchemy_url.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
engine = create_engine(settings.sqlalchemy_url, **_engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
