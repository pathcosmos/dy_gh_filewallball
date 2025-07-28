#!/usr/bin/env python3
"""
IP 기반 인증 시스템 테스트 스크립트
"""

import os
import sys
import time
import requests
from datetime import datetime, timedelta

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, SessionLocal
from app.models.orm_models import Base, AllowedIP, IPAuthLog, IPRateLimit
from app.services.ip_auth_service import IPAuthService
from app.utils.security_utils import generate_encryption_key, hash_key


def setup_database():
    """데이터베이스 테이블 생성"""
    print("데이터베이스 테이블 생성 중...")
    Base.metadata.create_all(bind=engine)
    print("✅ 데이터베이스 테이블 생성 완료")


def test_ip_auth_service():
    """IP 인증 서비스 테스트"""
    print("\n=== IP 인증 서비스 테스트 ===")
    
    db = SessionLocal()
    ip_auth_service = IPAuthService(db)
    
    try:
        # 1. 허용 IP 추가 테스트
        print("1. 허용 IP 추가 테스트")
        test_ip = "192.168.1.100"
        test_key = generate_encryption_key()
        
        allowed_ip = ip_auth_service.add_allowed_ip(
            ip_address=test_ip,
            encryption_key=test_key,
            max_uploads_per_hour=50,
            max_file_size=52428800  # 50MB
        )
        
        print(f"   ✅ 허용 IP 추가됨: {allowed_ip.ip_address}")
        print(f"   🔑 생성된 키: {test_key[:20]}...")
        
        # 2. IP 및 키 검증 테스트
        print("\n2. IP 및 키 검증 테스트")
        verified_ip = ip_auth_service.verify_ip_and_key(test_ip, test_key)
        
        if verified_ip:
            print(f"   ✅ 검증 성공: {verified_ip.ip_address}")
        else:
            print("   ❌ 검증 실패")
            return False
        
        # 3. 잘못된 키로 검증 테스트
        print("\n3. 잘못된 키로 검증 테스트")
        wrong_key = generate_encryption_key()
        verified_ip = ip_auth_service.verify_ip_and_key(test_ip, wrong_key)
        
        if not verified_ip:
            print("   ✅ 올바르게 거부됨 (잘못된 키)")
        else:
            print("   ❌ 잘못된 키가 허용됨")
            return False
        
        # 4. Rate limiting 테스트
        print("\n4. Rate limiting 테스트")
        for i in range(5):
            is_allowed = ip_auth_service.check_rate_limit(test_ip, test_key)
            print(f"   요청 {i+1}: {'✅ 허용' if is_allowed else '❌ 차단'}")
        
        # 5. 통계 조회 테스트
        print("\n5. 통계 조회 테스트")
        stats = ip_auth_service.get_ip_statistics(test_ip, days=1)
        print(f"   총 요청 수: {stats['total_requests']}")
        print(f"   성공률: {stats['success_rate']:.1f}%")
        
        # 6. 키 재생성 테스트
        print("\n6. 키 재생성 테스트")
        new_key = ip_auth_service.regenerate_encryption_key(test_ip, test_key)
        print(f"   🔑 새 키: {new_key[:20]}...")
        
        # 새 키로 검증
        verified_ip = ip_auth_service.verify_ip_and_key(test_ip, new_key)
        if verified_ip:
            print("   ✅ 새 키로 검증 성공")
        else:
            print("   ❌ 새 키로 검증 실패")
            return False
        
        # 7. 허용 IP 제거 테스트
        print("\n7. 허용 IP 제거 테스트")
        success = ip_auth_service.remove_allowed_ip(test_ip, new_key)
        if success:
            print("   ✅ 허용 IP 제거 성공")
        else:
            print("   ❌ 허용 IP 제거 실패")
            return False
        
        print("\n🎉 모든 테스트 통과!")
        return True
        
    except Exception as e:
        print(f"❌ 테스트 실패: {str(e)}")
        return False
    finally:
        db.close()


def test_api_endpoints():
    """API 엔드포인트 테스트"""
    print("\n=== API 엔드포인트 테스트 ===")
    
    base_url = "http://localhost:8000"
    
    try:
        # 1. 헬스체크 테스트
        print("1. 헬스체크 테스트")
        response = requests.get(f"{base_url}/api/v1/ip-auth/health")
        if response.status_code == 200:
            print("   ✅ 헬스체크 성공")
        else:
            print(f"   ❌ 헬스체크 실패: {response.status_code}")
            return False
        
        # 2. 허용 IP 추가 API 테스트
        print("\n2. 허용 IP 추가 API 테스트")
        test_ip = "127.0.0.1"  # localhost IP 사용
        
        response = requests.post(
            f"{base_url}/api/v1/ip-auth/allowed-ips",
            params={
                "ip_address": test_ip,
                "max_uploads_per_hour": 30,
                "max_file_size": 26214400  # 25MB
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ 허용 IP 추가 성공: {data['ip_address']}")
            encryption_key = data['encryption_key']
            print(f"   🔑 생성된 키: {encryption_key[:20]}...")
        else:
            print(f"   ❌ 허용 IP 추가 실패: {response.status_code}")
            return False
        
        # 3. 파일 업로드 API 테스트 (성공 케이스)
        print("\n3. 파일 업로드 API 테스트 (성공)")
        
        # 테스트 파일 생성
        test_file_content = "This is a test file for IP authentication upload."
        with open("test_upload.txt", "w") as f:
            f.write(test_file_content)
        
        with open("test_upload.txt", "rb") as f:
            files = {"file": ("test_upload.txt", f, "text/plain")}
            headers = {"X-API-Key": encryption_key}
            
            response = requests.post(
                f"{base_url}/api/v1/ip-auth/upload",
                files=files,
                headers=headers
            )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ 파일 업로드 성공: {data['file_uuid']}")
        else:
            print(f"   ❌ 파일 업로드 실패: {response.status_code}")
            print(f"   응답: {response.text}")
            return False
        
        # 4. 잘못된 키로 업로드 테스트
        print("\n4. 잘못된 키로 업로드 테스트")
        wrong_key = generate_encryption_key()
        
        with open("test_upload.txt", "rb") as f:
            files = {"file": ("test_upload.txt", f, "text/plain")}
            headers = {"X-API-Key": wrong_key}
            
            response = requests.post(
                f"{base_url}/api/v1/ip-auth/upload",
                files=files,
                headers=headers
            )
        
        if response.status_code == 401:
            print("   ✅ 올바르게 거부됨 (잘못된 키)")
        else:
            print(f"   ❌ 잘못된 키가 허용됨: {response.status_code}")
            return False
        
        # 5. 통계 조회 API 테스트
        print("\n5. 통계 조회 API 테스트")
        response = requests.get(
            f"{base_url}/api/v1/ip-auth/statistics",
            params={"ip_address": test_ip, "days": 1}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ 통계 조회 성공")
            print(f"   총 요청 수: {data['statistics']['total_requests']}")
        else:
            print(f"   ❌ 통계 조회 실패: {response.status_code}")
            return False
        
        # 6. 허용 IP 제거 API 테스트
        print("\n6. 허용 IP 제거 API 테스트")
        response = requests.delete(
            f"{base_url}/api/v1/ip-auth/allowed-ips",
            params={
                "ip_address": test_ip,
                "encryption_key": encryption_key
            }
        )
        
        if response.status_code == 200:
            print("   ✅ 허용 IP 제거 성공")
        else:
            print(f"   ❌ 허용 IP 제거 실패: {response.status_code}")
            return False
        
        # 정리
        if os.path.exists("test_upload.txt"):
            os.remove("test_upload.txt")
        
        print("\n🎉 모든 API 테스트 통과!")
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.")
        return False
    except Exception as e:
        print(f"❌ API 테스트 실패: {str(e)}")
        return False


def main():
    """메인 테스트 함수"""
    print("🚀 IP 기반 인증 시스템 테스트 시작")
    print("=" * 50)
    
    # 데이터베이스 설정
    setup_database()
    
    # 서비스 테스트
    service_success = test_ip_auth_service()
    
    if service_success:
        print("\n" + "=" * 50)
        print("서비스 테스트 완료. API 테스트를 시작합니다.")
        print("서버를 실행한 후 다음 명령어로 테스트를 계속하세요:")
        print("python test_ip_auth.py --api-test")
    else:
        print("\n❌ 서비스 테스트 실패")
        return False
    
    return True


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--api-test":
        # API 테스트만 실행
        api_success = test_api_endpoints()
        if not api_success:
            sys.exit(1)
    else:
        # 전체 테스트 실행
        success = main()
        if not success:
            sys.exit(1) 