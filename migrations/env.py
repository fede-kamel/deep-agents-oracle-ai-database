"""Alembic environment: migrations run as DA_OWNER, online only."""

from __future__ import annotations

from alembic import context
from sqlalchemy import create_engine

from common.config import OWNER, load_config, password


def run_migrations_online() -> None:
    engine = create_engine(
        "oracle+oracledb://",
        connect_args={"user": OWNER, "password": password(OWNER), "dsn": load_config()["dsn"]},
    )
    with engine.connect() as connection:
        context.configure(connection=connection, transaction_per_migration=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    raise SystemExit("Offline mode is not supported; run `alembic upgrade head`.")
run_migrations_online()
