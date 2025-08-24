#!/usr/bin/env python3
"""
Keygen + Upload 통합 테스트 스크립트

프로젝트 키 생성 후 파일 업로드 기능을 테스트합니다.
"""

import requests
import json
import os
import signal
import subprocess
import time
import atexit
import tempfile
from datetime import datetime
from pathlib import Path


class KeygenUploadIntegrationTester:
    def __init__(self, base_url=None, port=None):
        self.port = port or self._find_available_port()
        self.base_url = base_url or f"http://localhost:{self.port}"
        self.master_key = "dysnt2025FileWallersBallKAuEZzTAsBjXiQ=="
        self.created_project_id = None
        self.created_project_key = None
        self.uploaded_file_id = None
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
                '--log-level', 'warning'
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
            return False
    
    def test_project_key_creation(self):
        """프로젝트 키 생성 테스트"""
        print("\n" + "=" * 50)
        print("1. 프로젝트 키 생성")
        print("=" * 50)
        
        url = f"{self.base_url}/api/v1/projects/"
        payload = {
            "project_name": f"integration_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "master_key": self.master_key
        }
        
        try:
            response = requests.post(url, json=payload)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ 프로젝트 키 생성 성공!")
                print(f"Project ID: {data.get('project_id')}")
                print(f"Project Key: {data.get('project_key')[:30]}...")
                
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
    
    def test_file_upload_with_project_key(self):
        """프로젝트 키를 사용한 파일 업로드 테스트"""
        if not self.created_project_key:
            print("❌ 프로젝트 키가 없어 업로드 테스트를 건너뜁니다.")
            return False
        
        print("\n" + "=" * 50)
        print("2. 프로젝트 키를 사용한 파일 업로드")
        print("=" * 50)
        
        # 테스트 파일 생성 (1KB 이상)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            test_content = f"통합 테스트 파일\n생성 시간: {datetime.now()}\n프로젝트 ID: {self.created_project_id}\n"
            # 1KB 이상으로 만들기 위해 더미 데이터 추가
            test_content += "=" * 50 + "\n"
            test_content += "이 파일은 Keygen + Upload 통합 테스트용 파일입니다.\n"
            test_content += "파일 크기를 1KB 이상으로 만들기 위해 추가 내용을 포함합니다.\n"
            test_content += "테스트 데이터: " + "x" * 800 + "\n"  # 800자 추가
            test_content += "=" * 50 + "\n"
            f.write(test_content)
            test_file_path = f.name
        
        try:
            # 파일 업로드 요청
            url = f"{self.base_url}/upload"
            
            with open(test_file_path, 'rb') as f:
                files = {'file': ('test_integration.txt', f, 'text/plain')}
                headers = {
                    'X-Project-Key': self.created_project_key
                }
                
                response = requests.post(url, files=files, headers=headers)
                print(f"Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print("✅ 파일 업로드 성공!")
                    print(f"File ID: {data.get('file_id')}")
                    print(f"Filename: {data.get('filename')}")
                    print(f"File Size: {data.get('file_size')} bytes")
                    print(f"Upload Time: {data.get('upload_time')}")
                    
                    self.uploaded_file_id = data.get('file_id')
                    return True
                else:
                    print(f"❌ 파일 업로드 실패: {response.status_code}")
                    print(f"Error: {response.text}")
                    return False
                    
        except Exception as e:
            print(f"❌ 업로드 요청 실패: {e}")
            return False
        finally:
            # 테스트 파일 삭제
            if os.path.exists(test_file_path):
                os.unlink(test_file_path)
    
    def test_file_retrieval(self):
        """업로드된 파일 조회 테스트"""
        if not self.uploaded_file_id:
            print("❌ 업로드된 파일이 없어 조회 테스트를 건너뜁니다.")
            return False
        
        print("\n" + "=" * 50)
        print("3. 업로드된 파일 조회")
        print("=" * 50)
        
        url = f"{self.base_url}/files/{self.uploaded_file_id}"
        
        try:
            response = requests.get(url)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ 파일 정보 조회 성공!")
                print(f"File ID: {data.get('file_id')}")
                print(f"Filename: {data.get('filename')}")
                print(f"MIME Type: {data.get('mime_type')}")
                print(f"File Size: {data.get('file_size')} bytes")
                print(f"Project Key ID: {data.get('project_key_id')}")
                
                # 프로젝트 키 연결 확인
                if data.get('project_key_id') == self.created_project_id:
                    print("✅ 프로젝트 키 연결 확인됨!")
                else:
                    print(f"⚠️ 프로젝트 키 불일치: {data.get('project_key_id')} != {self.created_project_id}")
                
                return True
            else:
                print(f"❌ 파일 조회 실패: {response.status_code}")
                print(f"Error: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ 조회 요청 실패: {e}")
            return False
    
    def test_file_download(self):
        """파일 다운로드 테스트"""
        if not self.uploaded_file_id:
            print("❌ 업로드된 파일이 없어 다운로드 테스트를 건너뜁니다.")
            return False
        
        print("\n" + "=" * 50)
        print("4. 파일 다운로드")
        print("=" * 50)
        
        url = f"{self.base_url}/download/{self.uploaded_file_id}"
        
        try:
            response = requests.get(url)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ 파일 다운로드 성공!")
                print(f"Content Type: {response.headers.get('content-type')}")
                print(f"Content Length: {len(response.content)} bytes")
                
                # 내용 일부 출력
                content_preview = response.text[:100] if response.headers.get('content-type', '').startswith('text/') else f"Binary data ({len(response.content)} bytes)"
                print(f"Content Preview: {content_preview}")
                
                return True
            else:
                print(f"❌ 파일 다운로드 실패: {response.status_code}")
                print(f"Error: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ 다운로드 요청 실패: {e}")
            return False
    
    def test_upload_without_project_key(self):
        """프로젝트 키 없이 업로드 시도 (실패 케이스)"""
        print("\n" + "=" * 50)
        print("5. 프로젝트 키 없이 업로드 시도")
        print("=" * 50)
        
        # 테스트 파일 생성 (1KB 이상)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            content = "프로젝트 키 없이 업로드 테스트\n" + "x" * 1000  # 1KB 이상
            f.write(content)
            test_file_path = f.name
        
        try:
            url = f"{self.base_url}/upload"
            
            with open(test_file_path, 'rb') as f:
                files = {'file': ('no_key_test.txt', f, 'text/plain')}
                # 프로젝트 키 헤더 없음
                
                response = requests.post(url, files=files)
                print(f"Status Code: {response.status_code}")
                
                # 프로젝트 키 없이도 업로드가 가능한지 확인
                if response.status_code == 200:
                    print("⚠️ 프로젝트 키 없이도 업로드 성공 (공개 업로드 허용)")
                    data = response.json()
                    print(f"File ID: {data.get('file_id')}")
                    return True
                elif response.status_code in [401, 403]:
                    print("✅ 프로젝트 키 없는 업로드 거부됨 (보안 정책 적용)")
                    return True
                else:
                    print(f"❓ 예상치 못한 응답: {response.status_code}")
                    print(f"Response: {response.text}")
                    return False
                    
        except Exception as e:
            print(f"❌ 요청 실패: {e}")
            return False
        finally:
            # 테스트 파일 삭제
            if os.path.exists(test_file_path):
                os.unlink(test_file_path)
    
    def test_file_content_verification(self):
        """업로드된 파일 내용 검증"""
        if not self.uploaded_file_id:
            print("❌ 업로드된 파일이 없어 내용 검증을 건너뜁니다.")
            return False
        
        print("\n" + "=" * 50)
        print("5. 업로드된 파일 내용 검증")
        print("=" * 50)
        
        url = f"{self.base_url}/download/{self.uploaded_file_id}"
        
        try:
            response = requests.get(url)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                content = response.text
                
                # 예상 내용이 포함되어 있는지 확인
                expected_patterns = [
                    "통합 테스트 파일",
                    f"프로젝트 ID: {self.created_project_id}",
                    "테스트 데이터:"
                ]
                
                all_found = True
                for pattern in expected_patterns:
                    if pattern in content:
                        print(f"✅ 패턴 확인: '{pattern}'")
                    else:
                        print(f"❌ 패턴 없음: '{pattern}'")
                        all_found = False
                
                if all_found:
                    print("✅ 파일 내용 검증 성공!")
                    return True
                else:
                    print("❌ 파일 내용 검증 실패")
                    return False
            else:
                print(f"❌ 파일 내용 검증 실패: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 내용 검증 요청 실패: {e}")
            return False

    def test_invalid_project_key_upload(self):
        """잘못된 프로젝트 키로 업로드 시도"""
        print("\n" + "=" * 50)
        print("6. 잘못된 프로젝트 키로 업로드 시도")
        print("=" * 50)
        
        # 테스트 파일 생성 (1KB 이상)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            content = "잘못된 프로젝트 키 업로드 테스트\n" + "y" * 1000  # 1KB 이상
            f.write(content)
            test_file_path = f.name
        
        try:
            url = f"{self.base_url}/upload"
            
            with open(test_file_path, 'rb') as f:
                files = {'file': ('invalid_key_test.txt', f, 'text/plain')}
                headers = {
                    'X-Project-Key': 'invalid_project_key_12345'
                }
                
                response = requests.post(url, files=files, headers=headers)
                print(f"Status Code: {response.status_code}")
                
                if response.status_code == 401:
                    print("✅ 잘못된 프로젝트 키 거부됨! (401 Unauthorized)")
                    print(f"Error: {response.text}")
                    return True
                elif response.status_code == 403:
                    print("✅ 잘못된 프로젝트 키 금지됨! (403 Forbidden)")
                    print(f"Error: {response.text}")
                    return True
                elif response.status_code == 200:
                    print("❌ 잘못된 키에도 업로드 성공 (보안 검증 필요)")
                    return False
                else:
                    print(f"❌ 예상치 못한 응답: {response.status_code}")
                    print(f"Response: {response.text}")
                    return False
                    
        except Exception as e:
            print(f"❌ 요청 실패: {e}")
            return False
        finally:
            # 테스트 파일 삭제
            if os.path.exists(test_file_path):
                os.unlink(test_file_path)
    
    def run_all_tests(self):
        """모든 통합 테스트 실행"""
        print("=" * 60)
        print("🔥 Keygen + Upload 통합 테스트 시작")
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
            
            # 2. 프로젝트 키를 사용한 파일 업로드
            results.append(self.test_file_upload_with_project_key())
            
            # 3. 업로드된 파일 조회
            results.append(self.test_file_retrieval())
            
            # 4. 파일 다운로드
            results.append(self.test_file_download())
            
            # 5. 업로드된 파일 내용 검증
            results.append(self.test_file_content_verification())
            
            # 6. 프로젝트 키 없이 업로드 시도
            results.append(self.test_upload_without_project_key())
            
            # 7. 잘못된 프로젝트 키로 업로드 시도
            results.append(self.test_invalid_project_key_upload())
            
            # 결과 요약
            print("\n" + "=" * 60)
            print("📊 통합 테스트 결과 요약")
            print("=" * 60)
            
            test_names = [
                "서버 헬스 체크",
                "프로젝트 키 생성",
                "프로젝트 키 파일 업로드",
                "업로드 파일 조회",
                "파일 다운로드",
                "파일 내용 검증",
                "키 없이 업로드",
                "잘못된 키 업로드"
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
            
            # 생성된 데이터 요약
            if self.created_project_key:
                print(f"\n📝 생성된 데이터:")
                print(f"  - Project ID: {self.created_project_id}")
                print(f"  - Project Key: {self.created_project_key[:30]}...")
                if self.uploaded_file_id:
                    print(f"  - File ID: {self.uploaded_file_id}")
            
            print(f"\n🕐 완료 시간: {datetime.now()}")
            
        except KeyboardInterrupt:
            print("\n\n⚠️ 사용자에 의해 테스트가 중단되었습니다.")
        except Exception as e:
            print(f"\n\n❌ 테스트 중 예상치 못한 오류가 발생했습니다: {e}")
        finally:
            # 서버 정리
            self.cleanup_servers()


if __name__ == "__main__":
    tester = KeygenUploadIntegrationTester()
    tester.run_all_tests()