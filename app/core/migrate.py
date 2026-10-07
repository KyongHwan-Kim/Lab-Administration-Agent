import time
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError

from app.core.database import engine

ROOT = Path(__file__).resolve().parents[2]


def upgrade_database() -> None:
    _wait_for_database()
    config = _alembic_config()
    with engine.connect() as connection:
        tables = set(inspect(connection).get_table_names())
        revision = _current_revision(connection, tables)
    if revision is None and "users" in tables:
        command.stamp(config, "head")
    else:
        command.upgrade(config, "head")
    engine.dispose()


def _wait_for_database() -> None:
    for attempt in range(30):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return
        except OperationalError:
            if attempt == 29:
                raise
            time.sleep(1)
            engine.dispose()


def _alembic_config() -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", str(engine.url).replace("%", "%%"))
    return config


def _current_revision(connection, tables: set[str]) -> str | None:
    if "alembic_version" not in tables:
        return None
    row = connection.execute(text("SELECT version_num FROM alembic_version")).first()
    if row is None:
        return None
    return str(row[0])
