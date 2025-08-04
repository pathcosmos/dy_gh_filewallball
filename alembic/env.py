"""
Alembic environment configuration for FileWallBall application.
"""

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from app.models.database_enhanced import enhanced_db_manager

# add your model's MetaData object here
# for 'autogenerate' support
from app.models.orm_models import Base

# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_database_url():
    """환경 변수에서 데이터베이스 URL 가져오기"""
    # Docker 환경에서는 MariaDB 사용
    if os.getenv("DB_HOST") and os.getenv("DB_HOST") != "localhost":
        db_host = os.getenv("DB_HOST", "mariadb")
        db_port = os.getenv("DB_PORT", "3306")
        db_name = os.getenv("DB_NAME", "filewallball_db")
        db_user = os.getenv("DB_USER", "filewallball_user")
        db_password = os.getenv("DB_PASSWORD", "filewallball_user_password")
        return f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    # 로컬 개발 환경에서는 SQLite 사용
    db_name = os.getenv("DB_NAME", "filewallball.db")
    return f"sqlite:///./{db_name}"


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


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # 환경 변수에서 데이터베이스 URL 가져오기
    url = get_database_url()

    # 설정에 URL 추가
    config.set_main_option("sqlalchemy.url", url)

    # SQLite와 MariaDB에 따른 설정 분기
    if url.startswith("sqlite"):
        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
    else:
        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
            # MariaDB 특화 설정
            connect_args={
                "charset": "utf8mb4",
                "autocommit": False,
                "sql_mode": "STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO",
            },
        )

    with connectable.connect() as connection:
        # SQLite와 MariaDB에 따른 설정 분기
        if url.startswith("sqlite"):
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
            )
        else:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                # MariaDB 특화 설정
                compare_type=True,
                compare_server_default=True,
                include_schemas=False,
            )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
