#!/usr/bin/env python3
"""
Async Alembic migration script for FileWallBall application.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from alembic import command
from alembic.config import Config


def create_alembic_config() -> Config:
    """Create Alembic configuration."""
    alembic_cfg = Config("alembic.ini")

    # Set environment variable to use async env
    os.environ["ALEMBIC_ASYNC"] = "1"

    return alembic_cfg


async def run_async_migration(action: str, **kwargs):
    """Run async Alembic migration."""
    config = create_alembic_config()

    if action == "upgrade":
        command.upgrade(config, kwargs.get("revision", "head"))
    elif action == "downgrade":
        command.downgrade(config, kwargs.get("revision", "-1"))
    elif action == "revision":
        command.revision(
            config,
            message=kwargs.get("message", "Auto-generated migration"),
            autogenerate=kwargs.get("autogenerate", True),
        )
    elif action == "current":
        command.current(config)
    elif action == "history":
        command.history(config)
    elif action == "show":
        command.show(config, kwargs.get("revision"))
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/async_alembic.py <action> [options]")
        print("Actions: upgrade, downgrade, revision, current, history, show")
        sys.exit(1)

    action = sys.argv[1]
    kwargs = {}

    # Parse additional arguments
    if len(sys.argv) > 2:
        if action in ["upgrade", "downgrade"]:
            kwargs["revision"] = sys.argv[2]
        elif action == "revision":
            kwargs["message"] = sys.argv[2]
        elif action == "show":
            kwargs["revision"] = sys.argv[2]

    # Run migration
    asyncio.run(run_async_migration(action, **kwargs))


if __name__ == "__main__":
    main()
