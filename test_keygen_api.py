#!/usr/bin/env python3
"""
Keygen API 테스트 스크립트

프로젝트 키 생성 및 검증 API를 테스트합니다.
"""

import requests
import json
import os
import signal
import subprocess
import time
import atexit
from datetime import datetime


class KeygenAPITester:
    def __init__(self, base_url=None, port=None):
        self.port = port or self._find_available_port()
        self.base_url = base_url or f"http://localhost:{self.port}"
        self.master_key = "dysnt2025FileWallersBallKAuEZzTAsBjXiQ=="
        self.created_project_id = None
        self.created_project_key = None
        self.server_process = None
        self.server_pids = set()
        
        # 프로그램 종료 시 서버 정리하도록 등록
        atexit.register(self.cleanup_servers)
    
    def _find_available_port(self):
        """사용 가능한 포트 찾기 (8000-8010 범위)"""
        import socket
        for port in range(8000, 8011):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('127.0.0.1', port))
                    return port
            except OSError:
                continue
        raise RuntimeError("사용 가능한 포트를 찾을 수 없습니다.")
    
    def cleanup_servers(self):
        """실행 중인 모든 테스트 서버 정리"""
        print("\n🧹 테스트 서버 정리 중...")
        
        # 현재 프로세스 종료
        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
                print(f"✅ 메인 서버 프로세스 종료")
            except subprocess.TimeoutExpired:
                self.server_process.kill()
                print(f"⚠️ 메인 서버 프로세스 강제 종료")
            except:
                pass
        
        # PID로 추적된 프로세스들 종료
        for pid in self.server_pids:
            try:
                os.kill(pid, signal.SIGTERM)
                print(f"✅ PID {pid} 서버 종료")
            except ProcessLookupError:
                pass  # 이미 종료됨
            except:
                try:
                    os.kill(pid, signal.SIGKILL)
                    print(f"⚠️ PID {pid} 서버 강제 종료")
                except:
                    pass
        
        # uvicorn 프로세스 패턴으로 검색하여 종료
        try:
            # 테스트 포트 범위의 uvicorn 프로세스 찾기
            result = subprocess.run(
                ['pgrep', '-f', 'uvicorn.*app\\.main.*800[0-9]'],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid:
                        try:
                            os.kill(int(pid), signal.SIGTERM)
                            print(f"✅ 패턴 매칭으로 PID {pid} 서버 종료")
                        except:
                            pass
        except:
            pass
        
        print("🏁 서버 정리 완료")
    
    def start_test_server(self):
        """테스트 서버 시작"""
        print(f"🚀 테스트 서버 시작 중 (포트: {self.port})...")
        
        # 환경변수 설정
        env = os.environ.copy()
        env['MASTER_KEY'] = self.master_key
        
        # 서버 시작
        try:
            self.server_process = subprocess.Popen([
                'python', '-m', 'uvicorn', 'app.main:app',
                '--host', '127.0.0.1',
                '--port', str(self.port),
                '--log-level', 'warning'  # 로그 레벨을 warning으로 설정하여 출력 줄이기
            ], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            self.server_pids.add(self.server_process.pid)
            
            # 서버 시작 대기
            for attempt in range(30):  # 최대 15초 대기
                try:
                    response = requests.get(f"{self.base_url}/health", timeout=1)
                    if response.status_code == 200:
                        print(f"✅ 테스트 서버 시작 완료: {self.base_url}")
                        return True
                except:
                    time.sleep(0.5)
            
            print("❌ 서버 시작 실패")
            return False
            
        except Exception as e:
            print(f"❌ 서버 시작 중 오류: {e}")
            return False
    
    def test_project_key_creation(self):
        """프로젝트 키 생성 테스트"""
        print("=" * 50)
        print("1. 프로젝트 키 생성 테스트")
        print("=" * 50)
        
        url = f"{self.base_url}/api/v1/projects/"
        payload = {
            "project_name": f"test_project_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "master_key": self.master_key
        }
        
        try:
            response = requests.post(url, json=payload)
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ 프로젝트 키 생성 성공!")
                print(f"Project ID: {data.get('project_id')}")
                print(f"Project Key: {data.get('project_key')[:20]}...")
                print(f"JWT Token: {data.get('jwt_token')[:30] if data.get('jwt_token') else 'None'}...")
                print(f"Message: {data.get('message')}")
                
                # 생성된 데이터 저장
                self.created_project_id = data.get('project_id')
                self.created_project_key = data.get('project_key')
                
                return True
            else:
                print(f"❌ 프로젝트 키 생성 실패: {response.status_code}")
                print(f"Error: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ 요청 실패: {e}")
            return False
    
    def test_project_info_retrieval(self):
        """프로젝트 정보 조회 테스트"""
        if not self.created_project_id:
            print("❌ 생성된 프로젝트 ID가 없어 정보 조회를 건너뜁니다.")
            return False
            
        print("\n" + "=" * 50)
        print("2. 프로젝트 정보 조회 테스트")
        print("=" * 50)
        
        url = f"{self.base_url}/api/v1/projects/{self.created_project_id}"
        
        try:
            response = requests.get(url)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ 프로젝트 정보 조회 성공!")
                print(f"Project ID: {data.get('project_id')}")
                print(f"Project Name: {data.get('project_name')}")
                print(f"Request Date: {data.get('request_date')}")
                print(f"Request IP: {data.get('request_ip')}")
                print(f"Is Active: {data.get('is_active')}")
                print(f"Created At: {data.get('created_at')}")
                print(f"File Count: {data.get('file_count')}")
                
                return True
            else:
                print(f"❌ 프로젝트 정보 조회 실패: {response.status_code}")
                print(f"Error: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ 요청 실패: {e}")
            return False
    
    def test_invalid_master_key(self):
        """잘못된 마스터 키 테스트"""
        print("\n" + "=" * 50)
        print("3. 잘못된 마스터 키 테스트")
        print("=" * 50)
        
        url = f"{self.base_url}/api/v1/projects/"
        payload = {
            "project_name": "invalid_test_project",
            "master_key": "invalid_key_123"
        }
        
        try:
            response = requests.post(url, json=payload)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 401:
                print("✅ 잘못된 마스터 키 거부 성공!")
                print(f"Error: {response.text}")
                return True
            else:
                print(f"❌ 예상과 다른 응답: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ 요청 실패: {e}")
            return False
    
    def test_nonexistent_project(self):
        """존재하지 않는 프로젝트 조회 테스트"""
        print("\n" + "=" * 50)
        print("4. 존재하지 않는 프로젝트 조회 테스트")
        print("=" * 50)
        
        url = f"{self.base_url}/api/v1/projects/99999"
        
        try:
            response = requests.get(url)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 404:
                print("✅ 존재하지 않는 프로젝트 404 응답 성공!")
                print(f"Error: {response.text}")
                return True
            else:
                print(f"❌ 예상과 다른 응답: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ 요청 실패: {e}")
            return False
    
    def test_health_check(self):
        """헬스 체크 테스트"""
        print("\n" + "=" * 50)
        print("0. 서버 헬스 체크")
        print("=" * 50)
        
        url = f"{self.base_url}/health"
        
        try:
            response = requests.get(url)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ 서버 정상 동작 중!")
                print(f"Service: {data.get('service')}")
                print(f"Version: {data.get('version')}")
                print(f"Status: {data.get('status')}")
                return True
            else:
                print(f"❌ 서버 헬스 체크 실패: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 서버 연결 실패: {e}")
            print("서버가 실행되고 있는지 확인하세요: uvicorn app.main:app --reload")
            return False
    
    def run_all_tests(self):
        """모든 테스트 실행"""
        print("=" * 60)
        print("🔥 Keygen API 테스트 시작")
        print("=" * 60)
        print(f"📍 Base URL: {self.base_url}")
        print(f"🕐 시작 시간: {datetime.now()}")
        
        # 서버 시작
        if not self.start_test_server():
            print("❌ 테스트 서버 시작 실패로 테스트를 중단합니다.")
            return
        
        try:
            results = []
            
            # 0. 헬스 체크
            results.append(self.test_health_check())
            
            if not results[0]:
                print("\n❌ 서버 헬스 체크 실패로 테스트를 중단합니다.")
                return
        
            # 1. 프로젝트 키 생성
            results.append(self.test_project_key_creation())
            
            # 2. 프로젝트 정보 조회
            results.append(self.test_project_info_retrieval())
            
            # 3. 잘못된 마스터 키
            results.append(self.test_invalid_master_key())
            
            # 4. 존재하지 않는 프로젝트
            results.append(self.test_nonexistent_project())
            
            # 결과 요약
            print("\n" + "=" * 60)
            print("📊 테스트 결과 요약")
            print("=" * 60)
            
            test_names = [
                "서버 헬스 체크",
                "프로젝트 키 생성", 
                "프로젝트 정보 조회",
                "잘못된 마스터 키 거부",
                "존재하지 않는 프로젝트 404"
            ]
            
            passed = sum(results)
            total = len(results)
            
            for i, (name, result) in enumerate(zip(test_names, results)):
                status = "✅ PASS" if result else "❌ FAIL"
                print(f"{i}: {name} - {status}")
            
            print(f"\n📈 총 테스트: {total}개")
            print(f"✅ 성공: {passed}개")
            print(f"❌ 실패: {total - passed}개")
            success_rate = passed/total*100
            if success_rate == 100.0:
                print(f"🎉 성공률: {success_rate:.1f}% (완벽!)")
            else:
                print(f"📊 성공률: {success_rate:.1f}%")
            
            if self.created_project_key:
                print(f"\n🔑 생성된 프로젝트 키: {self.created_project_key[:30]}...")
            
            print(f"🕐 완료 시간: {datetime.now()}")
            
        except KeyboardInterrupt:
            print("\n\n⚠️ 사용자에 의해 테스트가 중단되었습니다.")
        except Exception as e:
            print(f"\n\n❌ 테스트 중 예상치 못한 오류가 발생했습니다: {e}")
        finally:
            # 서버 정리
            self.cleanup_servers()


if __name__ == "__main__":
    tester = KeygenAPITester()
    tester.run_all_tests()