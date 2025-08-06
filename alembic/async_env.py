"""
Async environment for Alembic migrations with MariaDB support.
"""

import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
from app.models.base import Base
target_metadata = Base.metadata


def get_database_url():
    """환경 변수에서 MariaDB 데이터베이스 URL 가져오기"""
    # MariaDB 전용 설정
    db_host = os.getenv("DB_HOST", "pathcosmos.iptime.org")
    db_port = os.getenv("DB_PORT", "33377")
    db_name = os.getenv("DB_NAME", "filewallball_dev")
    db_user = os.getenv("DB_USER", "filewallball")
    db_password = os.getenv("DB_PASSWORD", "jK9#zQ$p&2@f!L7^xY*")
    
    from urllib.parse import quote_plus
    encoded_password = quote_plus(db_password)
    return f"mysql+aiomysql://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_database_url()

    # MariaDB 설정
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        render_as_batch=False,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode with async support."""
    url = get_database_url()
    
    # MariaDB 비동기 엔진 생성
    connectable = create_async_engine(
        url,
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        # MariaDB 설정
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            render_as_batch=False,
        )

        async with connection.begin() as trans:
            await connection.run_sync(do_run_migrations)
            
    await connectable.dispose()


def do_run_migrations(connection):
    """Helper function to run migrations synchronously."""
    context.configure(connection=connection, target_metadata=target_metadata)
    
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())