#!/usr/bin/env python3
"""
간단한 프로젝트 키 생성 테스트
"""

import asyncio
import os
from app.database.async_database import get_db
from app.services.project_key_service import ProjectKeyService
from app.utils.security_key_manager import get_master_key

async def test_project_key_creation():
    """프로젝트 키 생성 테스트"""
    print("마스터 키:", get_master_key())
    
    # 데이터베이스 세션 생성
    async for db in get_db():
        try:
            service = ProjectKeyService(db)
            print("서비스 생성됨")
            
            project_key_obj = await service.create_project_key(
                project_name="test_project",
                request_date="20250807",
                request_ip="127.0.0.1"
            )
            
            print("프로젝트 키 생성 성공!")
            print(f"Project ID: {project_key_obj.id}")
            print(f"Project Key: {project_key_obj.project_key[:30]}...")
            
            return project_key_obj
            
        except Exception as e:
            print(f"에러 발생: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            break

if __name__ == "__main__":
    os.environ['MASTER_KEY'] = "dysnt2025FileWallersBallKAuEZzTAsBjXiQ=="
    asyncio.run(test_project_key_creation())