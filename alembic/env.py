from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

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
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
from app.models.base import Base
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

import os


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
    return f"mysql+pymysql://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"


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

    # MariaDB 설정
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
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

    # MariaDB 연결 설정
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
        # MariaDB 설정
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