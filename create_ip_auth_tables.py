#!/usr/bin/env python3
"""
IP 인증 관련 테이블들을 직접 생성하는 스크립트
"""

import os
import sys
from sqlalchemy import create_engine, text
from app.config import get_settings

def create_ip_auth_tables():
    """IP 인증 관련 테이블들을 생성합니다."""
    
    # 설정 로드
    settings = get_settings()
    database_url = settings.database_url
    
    print(f"데이터베이스 URL: {database_url}")
    
    # 엔진 생성
    engine = create_engine(database_url)
    
    # 테이블 생성 SQL
    tables_sql = [
        """
        CREATE TABLE IF NOT EXISTS allowed_ips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address VARCHAR(45) NOT NULL,
            ip_range VARCHAR(18),
            encryption_key VARCHAR(255) NOT NULL,
            key_hash VARCHAR(255) NOT NULL,
            permissions TEXT,
            max_uploads_per_hour INTEGER DEFAULT 100,
            max_file_size BIGINT DEFAULT 104857600,
            is_active BOOLEAN DEFAULT 1,
            expires_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_allowed_ips_ip_address ON allowed_ips (ip_address)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_allowed_ips_is_active ON allowed_ips (is_active)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_allowed_ips_key_hash ON allowed_ips (key_hash)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_allowed_ips_expires_at ON allowed_ips (expires_at)
        """,
        """
        CREATE UNIQUE INDEX IF NOT EXISTS unique_ip_key ON allowed_ips (ip_address, encryption_key)
        """,
        """
        CREATE TABLE IF NOT EXISTS ip_auth_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address VARCHAR(45) NOT NULL,
            allowed_ip_id INTEGER,
            api_key_hash VARCHAR(255),
            action VARCHAR(50) NOT NULL,
            file_uuid VARCHAR(36),
            user_agent TEXT,
            request_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            response_code INTEGER,
            error_message TEXT,
            request_size BIGINT,
            processing_time_ms INTEGER,
            FOREIGN KEY (allowed_ip_id) REFERENCES allowed_ips (id)
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_ip_auth_logs_ip_address ON ip_auth_logs (ip_address)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_ip_auth_logs_action ON ip_auth_logs (action)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_ip_auth_logs_api_key_hash ON ip_auth_logs (api_key_hash)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_ip_auth_logs_file_uuid ON ip_auth_logs (file_uuid)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_ip_auth_logs_request_time ON ip_auth_logs (request_time)
        """,
        """
        CREATE TABLE IF NOT EXISTS ip_rate_limits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address VARCHAR(45) NOT NULL,
            api_key_hash VARCHAR(255),
            window_start DATETIME NOT NULL,
            request_count INTEGER DEFAULT 0,
            last_request_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_ip_rate_limits_ip_address ON ip_rate_limits (ip_address)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_ip_rate_limits_api_key_hash ON ip_rate_limits (api_key_hash)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_ip_rate_limits_window_start ON ip_rate_limits (window_start)
        """,
        """
        CREATE UNIQUE INDEX IF NOT EXISTS unique_rate_limit ON ip_rate_limits (ip_address, api_key_hash, window_start)
        """
    ]
    
    try:
        with engine.connect() as connection:
            for i, sql in enumerate(tables_sql, 1):
                print(f"실행 중: {i}/{len(tables_sql)}")
                connection.execute(text(sql))
                connection.commit()
            
            print("✅ IP 인증 관련 테이블들이 성공적으로 생성되었습니다!")
            
            # 생성된 테이블 확인
            result = connection.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%ip%'"))
            tables = [row[0] for row in result]
            print(f"생성된 IP 관련 테이블들: {tables}")
            
    except Exception as e:
        print(f"❌ 테이블 생성 중 오류 발생: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = create_ip_auth_tables()
    sys.exit(0 if success else 1) 