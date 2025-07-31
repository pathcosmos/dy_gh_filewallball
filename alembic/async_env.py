"""
Async Alembic environment configuration for FileWallBall application.
"""

import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

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

# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata


def get_database_url():
    """환경 변수에서 데이터베이스 URL 가져오기"""
    # 로컬 개발 환경에서는 SQLite 사용
    if os.getenv("ENVIRONMENT", "development") == "development":
        db_name = os.getenv("DB_NAME", "filewallball.db")
        return f"sqlite+aiosqlite:///./{db_name}"

    # 프로덕션 환경에서는 MariaDB 사용
    db_host = os.getenv("DB_HOST", "mariadb-service")
    db_port = os.getenv("DB_PORT", "3306")
    db_name = os.getenv("DB_NAME", "filewallball_db")
    db_user = os.getenv("DB_USER", "filewallball_user")
    db_password = os.getenv("DB_PASSWORD", "filewallball_user_password")

    return f"mysql+aiomysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_database_url()

    # SQLite와 MariaDB에 따른 설정 분기
    if url.startswith("sqlite"):
        context.configure(
            url=url,
            target_metadata=target_metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
        )
    else:
        context.configure(
            url=url,
            target_metadata=target_metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
            # MariaDB 특화 설정
            compare_type=True,
            compare_server_default=True,
            include_schemas=False,
        )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # 환경 변수에서 데이터베이스 URL 가져오기
    url = get_database_url()

    # 설정에 URL 추가
    config.set_main_option("sqlalchemy.url", url)

    # 비동기 엔진 생성
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        # SQLite와 MariaDB에 따른 설정 분기
        if url.startswith("sqlite"):
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
                compare_server_default=True,
            )
        else:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
                compare_server_default=True,
                include_schemas=False,
            )

        async with context.begin_transaction():
            await context.run_migrations()

    await connectable.dispose()


def run_async_migrations():
    """Run async migrations."""
    asyncio.run(run_migrations_online())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_async_migrations()
