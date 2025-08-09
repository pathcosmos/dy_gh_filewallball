#!/usr/bin/env python3
"""
데이터베이스 프로젝트 키 확인 스크립트
"""

import asyncio
from sqlalchemy import select
from app.database.async_database import get_db
from app.models.orm_models import ProjectKey

async def check_projects():
    """데이터베이스의 프로젝트 키 확인"""
    async for db in get_db():
        try:
            # 모든 프로젝트 키 조회
            stmt = select(ProjectKey).order_by(ProjectKey.id.desc()).limit(10)
            result = await db.execute(stmt)
            projects = result.scalars().all()
            
            print("=" * 60)
            print("데이터베이스 프로젝트 키 목록 (최근 10개)")
            print("=" * 60)
            
            if not projects:
                print("프로젝트 키가 없습니다.")
            else:
                for project in projects:
                    print(f"\nID: {project.id}")
                    print(f"프로젝트명: {project.project_name}")
                    print(f"프로젝트 키: {project.project_key[:30]}...")
                    print(f"요청 날짜: {project.request_date}")
                    print(f"요청 IP: {project.request_ip}")
                    print(f"활성화: {project.is_active}")
                    print(f"생성일: {project.created_at}")
                    # print(f"파일 수: {len(project.files) if project.files else 0}")  # 비동기 관계 접근 제외
                    print("-" * 40)
            
            print(f"\n총 {len(projects)}개의 프로젝트 키가 있습니다.")
            
            # 특정 ID로 조회 테스트
            test_id = 2
            stmt = select(ProjectKey).where(ProjectKey.id == test_id)
            result = await db.execute(stmt)
            project = result.scalar_one_or_none()
            
            if project:
                print(f"\nID {test_id} 조회 성공!")
                print(f"프로젝트명: {project.project_name}")
            else:
                print(f"\nID {test_id}를 찾을 수 없습니다.")
                
        except Exception as e:
            print(f"에러 발생: {e}")
            import traceback
            traceback.print_exc()
        finally:
            break

if __name__ == "__main__":
    asyncio.run(check_projects())