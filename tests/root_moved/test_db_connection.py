#!/usr/bin/env python3
"""
데이터베이스 연결 테스트 스크립트
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_database_connection():
    """데이터베이스 연결 테스트"""
    print("🔍 데이터베이스 연결 테스트...")
    
    try:
        # 데이터베이스 모듈 import 테스트
        from app.dependencies.database import get_async_session
        from app.models.orm_models import FileInfo
        from sqlalchemy import select
        
        print("✅ 모듈 import 성공")
        
        # 세션 생성 테스트
        async for session in get_async_session():
            print("✅ 데이터베이스 세션 생성 성공")
            
            # 간단한 쿼리 테스트
            try:
                stmt = select(FileInfo).limit(1)
                result = await session.execute(stmt)
                files = result.scalars().all()
                print(f"✅ 데이터베이스 쿼리 성공: {len(files)}개 파일 발견")
                
                # 테이블 구조 확인
                if files:
                    file = files[0]
                    print(f"📋 파일 정보 예시:")
                    print(f"  - ID: {file.id}")
                    print(f"  - UUID: {file.file_uuid}")
                    print(f"  - 파일명: {file.original_filename}")
                    print(f"  - 크기: {file.file_size}")
                    print(f"  - MIME 타입: {file.mime_type}")
                
            except Exception as e:
                print(f"❌ 데이터베이스 쿼리 실패: {e}")
            
            break
            
    except ImportError as e:
        print(f"❌ 모듈 import 실패: {e}")
    except Exception as e:
        print(f"❌ 데이터베이스 연결 실패: {e}")

def test_config():
    """설정 테스트"""
    print("\n⚙️ 설정 테스트...")
    
    try:
        from app.config import get_settings
        
        settings = get_settings()
        print("✅ 설정 로드 성공")
        print(f"  - 환경: {settings.environment}")
        print(f"  - 데이터베이스 호스트: {settings.db_host}")
        print(f"  - 데이터베이스 포트: {settings.db_port}")
        print(f"  - 데이터베이스 이름: {settings.db_name}")
        print(f"  - 업로드 디렉토리: {settings.upload_dir}")
        print(f"  - 효과적 업로드 디렉토리: {settings.effective_upload_dir}")
        
    except Exception as e:
        print(f"❌ 설정 로드 실패: {e}")

def test_upload_directory():
    """업로드 디렉토리 테스트"""
    print("\n📁 업로드 디렉토리 테스트...")
    
    try:
        from app.config import get_settings
        
        settings = get_settings()
        upload_dir = Path(settings.effective_upload_dir)
        
        print(f"업로드 디렉토리 경로: {upload_dir}")
        print(f"디렉토리 존재: {upload_dir.exists()}")
        print(f"디렉토리 권한: {oct(upload_dir.stat().st_mode)[-3:] if upload_dir.exists() else 'N/A'}")
        
        if upload_dir.exists():
            files = list(upload_dir.glob("*"))
            print(f"디렉토리 내 파일 수: {len(files)}")
            for file in files[:5]:  # 처음 5개 파일만 표시
                print(f"  - {file.name} ({file.stat().st_size} bytes)")
        
    except Exception as e:
        print(f"❌ 업로드 디렉토리 테스트 실패: {e}")

async def main():
    """메인 테스트 실행"""
    print("🚀 데이터베이스 및 설정 테스트 시작")
    print("=" * 60)
    
    # 1. 설정 테스트
    test_config()
    
    # 2. 업로드 디렉토리 테스트
    test_upload_directory()
    
    # 3. 데이터베이스 연결 테스트
    await test_database_connection()
    
    print("\n" + "=" * 60)
    print("🏁 테스트 완료")

if __name__ == "__main__":
    asyncio.run(main())