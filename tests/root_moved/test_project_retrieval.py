#!/usr/bin/env python3
"""
프로젝트 조회 테스트
"""

import asyncio
from sqlalchemy import select
from app.database.async_database import get_db
from app.models.orm_models import ProjectKey

async def test_project_retrieval():
    """프로젝트 조회 테스트"""
    async for db in get_db():
        try:
            # 최신 프로젝트 ID 조회
            stmt = select(ProjectKey).order_by(ProjectKey.id.desc()).limit(1)
            result = await db.execute(stmt)
            latest_project = result.scalar_one_or_none()
            
            if not latest_project:
                print("프로젝트가 없습니다.")
                return
                
            project_id = latest_project.id
            print(f"테스트 대상 프로젝트 ID: {project_id}")
            
            # ID로 조회
            stmt = select(ProjectKey).where(ProjectKey.id == project_id)
            result = await db.execute(stmt)
            project = result.scalar_one_or_none()
            
            if project:
                print("✅ 프로젝트 조회 성공!")
                print(f"ID: {project.id}")
                print(f"프로젝트명: {project.project_name}")
                print(f"프로젝트 키: {project.project_key[:30]}...")
                print(f"요청 날짜: {project.request_date}")
                print(f"요청 IP: {project.request_ip}")
                print(f"활성화: {project.is_active}")
                
                # 날짜 처리
                created_at = project.created_at.isoformat() if project.created_at else "None"
                updated_at = project.updated_at.isoformat() if project.updated_at else "None"
                
                print(f"생성일: {created_at}")
                print(f"수정일: {updated_at}")
                
                # JSON 응답 형태로 출력
                response = {
                    "project_id": project.id,
                    "project_name": project.project_name,
                    "request_date": project.request_date,
                    "request_ip": project.request_ip,
                    "is_active": project.is_active,
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "file_count": 0
                }
                
                print(f"\nAPI 응답: {response}")
                
            else:
                print(f"❌ ID {project_id}를 찾을 수 없습니다.")
                
        except Exception as e:
            print(f"에러 발생: {e}")
            import traceback
            traceback.print_exc()
        finally:
            break

if __name__ == "__main__":
    asyncio.run(test_project_retrieval())