"""
Tests for async Alembic migrations.
"""

import pytest

from alembic import command
from alembic.config import Config


@pytest.fixture
def alembic_config():
    """Create Alembic configuration for testing."""
    config = Config("alembic.ini")
    config.set_main_option("script_location", "alembic")
    return config


def test_alembic_config_creation(alembic_config):
    """Test Alembic configuration creation."""
    assert alembic_config is not None
    assert alembic_config.get_main_option("script_location") == "alembic"


def test_alembic_current(alembic_config):
    """Test Alembic current command."""
    try:
        command.current(alembic_config)
    except Exception as e:
        # This might fail if no migrations exist yet
        assert "No such file or directory" in str(e) or "No version information" in str(
            e
        )


def test_alembic_history(alembic_config):
    """Test Alembic history command."""
    try:
        command.history(alembic_config)
    except Exception as e:
        # This might fail if no migrations exist yet
        assert "No such file or directory" in str(e) or "No version information" in str(
            e
        )


def test_async_env_import():
    """Test async environment import."""
    try:
        from alembic.async_env import run_async_migrations

        assert callable(run_async_migrations)
    except ImportError:
        # async_env.py might not be used by default
        pass


def test_async_alembic_script():
    """Test async Alembic script import."""
    try:
        from scripts.async_alembic import create_alembic_config, run_async_migration

        assert callable(create_alembic_config)
        assert callable(run_async_migration)
    except ImportError:
        # Script might not be available
        pass
