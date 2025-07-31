#!/usr/bin/env python3
"""
Migration management script for FileWallBall application.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class MigrationManager:
    """마이그레이션 관리 클래스"""

    def __init__(self):
        self.project_root = project_root
        self.alembic_dir = project_root / "alembic"
        self.versions_dir = self.alembic_dir / "versions"

    def run_alembic_command(self, command: List[str]) -> subprocess.CompletedProcess:
        """Alembic 명령어 실행"""
        try:
            result = subprocess.run(
                ["alembic"] + command,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
            )
            return result
        except subprocess.CalledProcessError as e:
            print(f"Alembic command failed: {e}")
            print(f"STDOUT: {e.stdout}")
            print(f"STDERR: {e.stderr}")
            raise

    def check_current_revision(self) -> Optional[str]:
        """현재 리비전 확인"""
        try:
            result = self.run_alembic_command(["current"])
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None

    def list_migrations(self) -> List[str]:
        """마이그레이션 목록 조회"""
        try:
            result = self.run_alembic_command(["history", "--verbose"])
            return result.stdout.strip().split("\n")
        except subprocess.CalledProcessError:
            return []

    def create_migration(self, message: str) -> bool:
        """새 마이그레이션 생성"""
        try:
            result = self.run_alembic_command(
                ["revision", "--autogenerate", "-m", message]
            )
            print(f"Migration created: {result.stdout}")
            return True
        except subprocess.CalledProcessError:
            print("Failed to create migration")
            return False

    def upgrade_database(self, revision: str = "head") -> bool:
        """데이터베이스 업그레이드"""
        try:
            result = self.run_alembic_command(["upgrade", revision])
            print(f"Database upgraded: {result.stdout}")
            return True
        except subprocess.CalledProcessError:
            print("Failed to upgrade database")
            return False

    def downgrade_database(self, revision: str) -> bool:
        """데이터베이스 다운그레이드"""
        try:
            result = self.run_alembic_command(["downgrade", revision])
            print(f"Database downgraded: {result.stdout}")
            return True
        except subprocess.CalledProcessError:
            print("Failed to downgrade database")
            return False

    def show_migration_sql(self, revision: str) -> Optional[str]:
        """마이그레이션 SQL 확인"""
        try:
            result = self.run_alembic_command(["upgrade", revision, "--sql"])
            return result.stdout
        except subprocess.CalledProcessError:
            return None

    def check_migration_status(self) -> dict:
        """마이그레이션 상태 확인"""
        current_revision = self.check_current_revision()
        migrations = self.list_migrations()

        return {
            "current_revision": current_revision,
            "total_migrations": len(migrations),
            "migrations": migrations,
        }

    def validate_migrations(self) -> bool:
        """마이그레이션 유효성 검사"""
        try:
            result = self.run_alembic_command(["check"])
            print(f"Migration validation: {result.stdout}")
            return True
        except subprocess.CalledProcessError:
            print("Migration validation failed")
            return False


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="Migration Manager for FileWallBall")
    parser.add_argument(
        "command",
        choices=[
            "status",
            "current",
            "history",
            "create",
            "upgrade",
            "downgrade",
            "sql",
            "validate",
        ],
    )
    parser.add_argument("--message", "-m", help="Migration message")
    parser.add_argument("--revision", "-r", help="Revision ID")

    args = parser.parse_args()

    manager = MigrationManager()

    if args.command == "status":
        status = manager.check_migration_status()
        print(f"Current revision: {status['current_revision']}")
        print(f"Total migrations: {status['total_migrations']}")

    elif args.command == "current":
        current = manager.check_current_revision()
        print(f"Current revision: {current}")

    elif args.command == "history":
        migrations = manager.list_migrations()
        for migration in migrations:
            print(migration)

    elif args.command == "create":
        if not args.message:
            print("Error: --message is required for create command")
            return 1
        success = manager.create_migration(args.message)
        return 0 if success else 1

    elif args.command == "upgrade":
        revision = args.revision or "head"
        success = manager.upgrade_database(revision)
        return 0 if success else 1

    elif args.command == "downgrade":
        if not args.revision:
            print("Error: --revision is required for downgrade command")
            return 1
        success = manager.downgrade_database(args.revision)
        return 0 if success else 1

    elif args.command == "sql":
        revision = args.revision or "head"
        sql = manager.show_migration_sql(revision)
        if sql:
            print(sql)
        else:
            print("Failed to generate SQL")
            return 1

    elif args.command == "validate":
        success = manager.validate_migrations()
        return 0 if success else 1

    return 0


if __name__ == "__main__":
    exit(main())
