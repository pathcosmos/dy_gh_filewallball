#!/usr/bin/env python3
"""
Redis 연결 테스트 스크립트
"""

import redis
import json
from datetime import datetime

def test_redis_connection():
    """Redis 연결 및 기본 기능 테스트"""
    try:
        # Redis 클라이언트 생성
        r = redis.Redis(
            host='localhost',
            port=6379,
            password='filewallball2024',
            decode_responses=True
        )
        
        # 연결 테스트
        print("🔍 Redis 연결 테스트 중...")
        response = r.ping()
        print(f"✅ Redis 연결 성공: {response}")
        
        # 기본 데이터 저장/조회 테스트
        print("\n📝 기본 데이터 저장/조회 테스트...")
        test_key = "test:connection"
        test_data = {
            "message": "Hello Redis!",
            "timestamp": datetime.now().isoformat(),
            "test_id": "connection_test_001"
        }
        
        # 데이터 저장
        r.setex(test_key, 300, json.dumps(test_data))  # 5분 만료
        print(f"✅ 데이터 저장 완료: {test_key}")
        
        # 데이터 조회
        retrieved_data = r.get(test_key)
        if retrieved_data:
            data = json.loads(retrieved_data)
            print(f"✅ 데이터 조회 성공: {data['message']}")
        else:
            print("❌ 데이터 조회 실패")
            
        # 키 목록 조회
        print("\n🔍 키 목록 조회...")
        keys = r.keys("test:*")
        print(f"✅ 테스트 키 개수: {len(keys)}")
        
        # 테스트 데이터 정리
        r.delete(test_key)
        print(f"✅ 테스트 데이터 정리 완료")
        
        return True
        
    except redis.ConnectionError as e:
        print(f"❌ Redis 연결 실패: {e}")
        return False
    except Exception as e:
        print(f"❌ Redis 테스트 중 오류 발생: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Redis 연결 테스트 시작\n")
    success = test_redis_connection()
    
    if success:
        print("\n🎉 모든 Redis 테스트가 성공했습니다!")
    else:
        print("\n💥 Redis 테스트에 실패했습니다.") 