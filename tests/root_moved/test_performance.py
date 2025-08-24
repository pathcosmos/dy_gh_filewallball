#!/usr/bin/env python3
"""
FileWallBall API - 성능 및 안정성 테스트 스크립트

이 스크립트는 API의 성능, 동시 접속 처리 능력, 메모리 사용량 등을
테스트하여 시스템의 안정성을 검증합니다.
"""

import os
import time
import requests
import json
import threading
import concurrent.futures
import statistics
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import psutil
import subprocess
import tempfile

class PerformanceTester:
    def __init__(self, api_base_url: str = "http://127.0.0.1:8000"):
        self.api_base_url = api_base_url
        self.test_results = {}
        self.start_time = time.time()
        self.process = psutil.Process()
        
    def log(self, message: str, level: str = "INFO"):
        """로그 메시지 출력"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    def get_system_stats(self) -> Dict:
        """시스템 리소스 사용량 조회"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_gb": memory.available / (1024**3),
            "disk_percent": disk.percent,
            "disk_free_gb": disk.free / (1024**3)
        }
    
    def test_health_endpoint_performance(self, num_requests: int = 100) -> Dict:
        """헬스체크 엔드포인트 성능 테스트"""
        self.log(f"\n--- 헬스체크 엔드포인트 성능 테스트 ({num_requests}회) ---")
        
        response_times = []
        success_count = 0
        error_count = 0
        
        start_time = time.time()
        
        for i in range(num_requests):
            try:
                request_start = time.time()
                response = requests.get(f"{self.api_base_url}/health", timeout=5)
                request_time = time.time() - request_start
                
                if response.status_code == 200:
                    success_count += 1
                    response_times.append(request_time * 1000)  # Convert to milliseconds
                else:
                    error_count += 1
                    
            except Exception as e:
                error_count += 1
                self.log(f"요청 {i+1} 실패: {e}", "ERROR")
        
        total_time = time.time() - start_time
        
        if response_times:
            avg_response_time = statistics.mean(response_times)
            p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
            min_response_time = min(response_times)
            max_response_time = max(response_times)
        else:
            avg_response_time = p95_response_time = min_response_time = max_response_time = 0
        
        tps = success_count / total_time if total_time > 0 else 0
        
        result = {
            "test_name": "헬스체크 엔드포인트 성능 테스트",
            "total_requests": num_requests,
            "success_count": success_count,
            "error_count": error_count,
            "success_rate": (success_count / num_requests) * 100,
            "total_time_seconds": total_time,
            "tps": tps,
            "response_times_ms": {
                "average": round(avg_response_time, 2),
                "p95": round(p95_response_time, 2),
                "min": round(min_response_time, 2),
                "max": round(max_response_time, 2)
            }
        }
        
        self.log(f"✅ 성공: {success_count}/{num_requests} ({result['success_rate']:.1f}%)")
        self.log(f"📊 TPS: {tps:.2f}")
        self.log(f"⏱️ 평균 응답시간: {avg_response_time:.2f}ms")
        self.log(f"📈 95퍼센타일: {p95_response_time:.2f}ms")
        
        return result
    
    def test_concurrent_uploads(self, num_concurrent: int = 10, files_per_batch: int = 5) -> Dict:
        """동시 업로드 성능 테스트"""
        self.log(f"\n--- 동시 업로드 성능 테스트 (동시 {num_concurrent}개, 배치당 {files_per_batch}개) ---")
        
        # 테스트 파일들 생성
        test_files = []
        for i in range(num_concurrent * files_per_batch):
            file_path = Path(f"perf_test_{i}.txt")
            content = f"Performance test file {i}\n" * 100  # ~2KB 파일
            file_path.write_text(content)
            test_files.append(file_path)
        
        upload_results = []
        start_time = time.time()
        
        def upload_batch(file_batch: List[Path]) -> List[Dict]:
            batch_results = []
            for file_path in file_batch:
                try:
                    upload_start = time.time()
                    with open(file_path, 'rb') as f:
                        files = {'file': (file_path.name, f, 'text/plain')}
                        response = requests.post(f"{self.api_base_url}/upload", files=files, timeout=30)
                    
                    upload_time = time.time() - upload_start
                    
                    if response.status_code == 200:
                        data = response.json()
                        batch_results.append({
                            "filename": file_path.name,
                            "success": True,
                            "file_id": data.get('file_id'),
                            "upload_time_seconds": upload_time,
                            "file_size_bytes": os.path.getsize(file_path)
                        })
                    else:
                        batch_results.append({
                            "filename": file_path.name,
                            "success": False,
                            "status_code": response.status_code,
                            "error": response.text[:100]
                        })
                        
                except Exception as e:
                    batch_results.append({
                        "filename": file_path.name,
                        "success": False,
                        "error": str(e)
                    })
            
            return batch_results
        
        try:
            # 파일들을 배치로 나누기
            batches = [test_files[i:i + files_per_batch] for i in range(0, len(test_files), files_per_batch)]
            
            # 동시 업로드 실행
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent) as executor:
                future_to_batch = {executor.submit(upload_batch, batch): batch for batch in batches}
                
                for future in concurrent.futures.as_completed(future_to_batch):
                    batch_results = future.result()
                    upload_results.extend(batch_results)
            
            total_time = time.time() - start_time
            
            # 결과 분석
            successful_uploads = [r for r in upload_results if r.get('success', False)]
            failed_uploads = [r for r in upload_results if not r.get('success', False)]
            
            if successful_uploads:
                upload_times = [r['upload_time_seconds'] for r in successful_uploads]
                avg_upload_time = statistics.mean(upload_times)
                p95_upload_time = statistics.quantiles(upload_times, n=20)[18] if len(upload_times) >= 20 else max(upload_times)
                total_file_size = sum(r['file_size_bytes'] for r in successful_uploads)
                throughput_mbps = (total_file_size / total_time) / (1024 * 1024) if total_time > 0 else 0
            else:
                avg_upload_time = p95_upload_time = throughput_mbps = 0
            
            result = {
                "test_name": "동시 업로드 성능 테스트",
                "concurrent_workers": num_concurrent,
                "files_per_batch": files_per_batch,
                "total_files": len(test_files),
                "successful_uploads": len(successful_uploads),
                "failed_uploads": len(failed_uploads),
                "success_rate": (len(successful_uploads) / len(test_files)) * 100,
                "total_time_seconds": total_time,
                "avg_upload_time_seconds": round(avg_upload_time, 3),
                "p95_upload_time_seconds": round(p95_upload_time, 3),
                "throughput_mbps": round(throughput_mbps, 2),
                "upload_results": upload_results[:10]  # 처음 10개만 저장 (전체는 너무 큼)
            }
            
            self.log(f"✅ 성공: {len(successful_uploads)}/{len(test_files)} ({result['success_rate']:.1f}%)")
            self.log(f"⏱️ 평균 업로드 시간: {avg_upload_time:.3f}s")
            self.log(f"📈 95퍼센타일: {p95_upload_time:.3f}s")
            self.log(f"🚀 처리량: {throughput_mbps:.2f} MB/s")
            
        except Exception as e:
            self.log(f"❌ 동시 업로드 테스트 실패: {e}", "ERROR")
            result = {
                "test_name": "동시 업로드 성능 테스트",
                "error": str(e),
                "success": False
            }
        
        finally:
            # 테스트 파일들 정리
            for file_path in test_files:
                if file_path.exists():
                    file_path.unlink()
        
        return result
    
    def test_memory_usage_during_load(self, duration_seconds: int = 60) -> Dict:
        """부하 상태에서의 메모리 사용량 모니터링"""
        self.log(f"\n--- 부하 상태에서의 메모리 사용량 모니터링 ({duration_seconds}초) ---")
        
        memory_samples = []
        start_time = time.time()
        
        # 백그라운드에서 지속적인 요청 생성
        def background_requests():
            while time.time() - start_time < duration_seconds:
                try:
                    requests.get(f"{self.api_base_url}/health", timeout=2)
                    time.sleep(0.1)  # 100ms 간격
                except:
                    pass
        
        # 메모리 모니터링 시작
        monitor_thread = threading.Thread(target=background_requests)
        monitor_thread.start()
        
        try:
            while time.time() - start_time < duration_seconds:
                # 현재 프로세스 메모리 사용량
                process_memory = self.process.memory_info()
                system_memory = psutil.virtual_memory()
                
                memory_samples.append({
                    "timestamp": time.time() - start_time,
                    "process_rss_mb": process_memory.rss / (1024 * 1024),
                    "process_vms_mb": process_memory.vms / (1024 * 1024),
                    "system_memory_percent": system_memory.percent,
                    "system_memory_available_gb": system_memory.available / (1024**3)
                })
                
                time.sleep(1)  # 1초마다 샘플링
                
        except KeyboardInterrupt:
            self.log("메모리 모니터링 중단됨")
        
        monitor_thread.join()
        
        if memory_samples:
            rss_values = [s['process_rss_mb'] for s in memory_samples]
            vms_values = [s['process_vms_mb'] for s in memory_samples]
            system_memory_percent = [s['system_memory_percent'] for s in memory_samples]
            
            result = {
                "test_name": "부하 상태에서의 메모리 사용량 모니터링",
                "duration_seconds": duration_seconds,
                "sample_count": len(memory_samples),
                "process_memory_mb": {
                    "rss": {
                        "min": round(min(rss_values), 2),
                        "max": round(max(rss_values), 2),
                        "average": round(statistics.mean(rss_values), 2),
                        "p95": round(statistics.quantiles(rss_values, n=20)[18] if len(rss_values) >= 20 else max(rss_values), 2)
                    },
                    "vms": {
                        "min": round(min(vms_values), 2),
                        "max": round(max(vms_values), 2),
                        "average": round(statistics.mean(vms_values), 2),
                        "p95": round(statistics.quantiles(vms_values, n=20)[18] if len(vms_values) >= 20 else max(vms_values), 2)
                    }
                },
                "system_memory_percent": {
                    "min": round(min(system_memory_percent), 2),
                    "max": round(max(system_memory_percent), 2),
                    "average": round(statistics.mean(system_memory_percent), 2)
                },
                "memory_samples": memory_samples[::5]  # 5초마다 샘플링하여 저장
            }
            
            self.log(f"📊 프로세스 RSS: {result['process_memory_mb']['rss']['min']:.1f}MB ~ {result['process_memory_mb']['rss']['max']:.1f}MB")
            self.log(f"📊 프로세스 VMS: {result['process_memory_mb']['vms']['min']:.1f}MB ~ {result['process_memory_mb']['vms']['max']:.1f}MB")
            self.log(f"📊 시스템 메모리: {result['system_memory_percent']['min']:.1f}% ~ {result['system_memory_percent']['max']:.1f}%")
            
        else:
            result = {
                "test_name": "부하 상태에서의 메모리 사용량 모니터링",
                "error": "메모리 샘플 수집 실패",
                "success": False
            }
        
        return result
    
    def test_apache_bench(self, num_requests: int = 1000, concurrency: int = 10) -> Dict:
        """Apache Bench를 사용한 부하 테스트"""
        self.log(f"\n--- Apache Bench 부하 테스트 ({num_requests} 요청, 동시 {concurrency}) ---")
        
        # ab 명령어 확인
        try:
            subprocess.run(["ab", "-V"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.log("❌ Apache Bench (ab)가 설치되어 있지 않습니다.", "WARNING")
            return {
                "test_name": "Apache Bench 부하 테스트",
                "error": "Apache Bench (ab) not installed",
                "success": False
            }
        
        try:
            # 헬스체크 엔드포인트로 부하 테스트
            cmd = [
                "ab", "-n", str(num_requests), "-c", str(concurrency),
                "-g", "ab_results.tsv",  # 결과를 TSV 파일로 저장
                f"{self.api_base_url}/health"
            ]
            
            self.log(f"실행 명령어: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                # 결과 파싱
                output_lines = result.stdout.split('\n')
                ab_results = {}
                
                for line in output_lines:
                    if 'Requests per second:' in line:
                        ab_results['rps'] = float(line.split(':')[1].strip().split()[0])
                    elif 'Time per request:' in line:
                        ab_results['time_per_request_ms'] = float(line.split(':')[1].strip().split()[0])
                    elif 'Transfer rate:' in line:
                        ab_results['transfer_rate_kbps'] = float(line.split(':')[1].strip().split()[0])
                    elif 'Percentage of the requests served within a certain time' in line:
                        # 95퍼센타일 시간 찾기
                        for i, l in enumerate(output_lines):
                            if '95%' in l:
                                ab_results['p95_time_ms'] = float(l.split()[1])
                                break
                
                # TSV 파일에서 상세 결과 읽기
                if os.path.exists("ab_results.tsv"):
                    with open("ab_results.tsv", 'r') as f:
                        lines = f.readlines()
                        if len(lines) > 1:  # 헤더 + 데이터
                            response_times = []
                            for line in lines[1:]:  # 헤더 제외
                                parts = line.strip().split('\t')
                                if len(parts) >= 2:
                                    try:
                                        response_times.append(float(parts[1]))
                                    except ValueError:
                                        continue
                            
                            if response_times:
                                ab_results['response_times_ms'] = {
                                    'min': min(response_times),
                                    'max': max(response_times),
                                    'mean': statistics.mean(response_times),
                                    'median': statistics.median(response_times)
                                }
                
                result_data = {
                    "test_name": "Apache Bench 부하 테스트",
                    "num_requests": num_requests,
                    "concurrency": concurrency,
                    "success": True,
                    "ab_results": ab_results,
                    "raw_output": result.stdout[:1000]  # 처음 1000자만 저장
                }
                
                self.log(f"✅ RPS: {ab_results.get('rps', 'N/A')}")
                self.log(f"⏱️ 평균 응답시간: {ab_results.get('time_per_request_ms', 'N/A')}ms")
                if 'p95_time_ms' in ab_results:
                    self.log(f"📈 95퍼센타일: {ab_results['p95_time_ms']:.2f}ms")
                
                return result_data
                
            else:
                self.log(f"❌ Apache Bench 실행 실패: {result.stderr}", "ERROR")
                return {
                    "test_name": "Apache Bench 부하 테스트",
                    "error": result.stderr,
                    "success": False
                }
                
        except subprocess.TimeoutExpired:
            self.log("❌ Apache Bench 테스트 시간 초과", "ERROR")
            return {
                "test_name": "Apache Bench 부하 테스트",
                "error": "Timeout expired",
                "success": False
            }
        except Exception as e:
            self.log(f"❌ Apache Bench 테스트 실패: {e}", "ERROR")
            return {
                "test_name": "Apache Bench 부하 테스트",
                "error": str(e),
                "success": False
            }
        finally:
            # 임시 파일 정리
            if os.path.exists("ab_results.tsv"):
                os.remove("ab_results.tsv")
    
    def run_all_tests(self):
        """모든 성능 테스트를 실행합니다."""
        self.log("🚀 FileWallBall API 성능 및 안정성 테스트 시작")
        
        # 초기 시스템 상태
        initial_stats = self.get_system_stats()
        self.log(f"초기 시스템 상태: CPU {initial_stats['cpu_percent']:.1f}%, 메모리 {initial_stats['memory_percent']:.1f}%")
        
        # API 헬스체크
        try:
            response = requests.get(f"{self.api_base_url}/health", timeout=5)
            if response.status_code != 200:
                self.log("❌ API가 실행 중이지 않습니다. 테스트를 중단합니다.", "ERROR")
                return
        except Exception as e:
            self.log(f"❌ API 연결 실패: {e}. 테스트를 중단합니다.", "ERROR")
            return
        
        # 각 테스트 실행
        tests = [
            self.test_health_endpoint_performance,
            self.test_concurrent_uploads,
            self.test_memory_usage_during_load,
            self.test_apache_bench
        ]
        
        for test_func in tests:
            try:
                self.log(f"\n{'='*60}")
                test_result = test_func()
                self.test_results[test_result["test_name"]] = test_result
                
                # 테스트 간 잠시 대기
                time.sleep(2)
                
            except Exception as e:
                self.log(f"❌ 테스트 실행 중 오류 발생: {test_func.__name__} - {e}", "ERROR")
                self.test_results[test_func.__name__] = {
                    "test_name": test_func.__name__,
                    "status": "ERROR",
                    "error": str(e)
                }
        
        # 최종 시스템 상태
        final_stats = self.get_system_stats()
        
        # 결과 요약
        self.log("\n" + "="*60)
        self.log("🏁 성능 및 안정성 테스트 완료 요약")
        self.log("="*60)
        
        total_tests = len(self.test_results)
        successful_tests = sum(1 for r in self.test_results.values() if r.get("success", True))
        failed_tests = total_tests - successful_tests
        
        self.log(f"총 테스트: {total_tests}")
        self.log(f"성공: {successful_tests}")
        self.log(f"실패: {failed_tests}")
        
        # 상세 결과
        for test_name, result in self.test_results.items():
            status_icon = "✅" if result.get("success", True) else "❌"
            self.log(f"{status_icon} {test_name}: {'성공' if result.get('success', True) else '실패'}")
        
        # 시스템 상태 변화
        self.log(f"\n📊 시스템 상태 변화:")
        self.log(f"CPU: {initial_stats['cpu_percent']:.1f}% → {final_stats['cpu_percent']:.1f}%")
        self.log(f"메모리: {initial_stats['memory_percent']:.1f}% → {final_stats['memory_percent']:.1f}%")
        self.log(f"사용 가능한 메모리: {initial_stats['memory_available_gb']:.2f}GB → {final_stats['memory_available_gb']:.2f}GB")
        
        # 결과 저장
        with open("performance_test_results.json", "w", encoding="utf-8") as f:
            json.dump(self.test_results, f, indent=4, ensure_ascii=False)
        self.log("\n테스트 결과가 performance_test_results.json에 저장되었습니다.")
        
        end_time = time.time()
        total_duration = end_time - self.start_time
        self.log(f"총 소요 시간: {total_duration:.2f}초")

if __name__ == "__main__":
    tester = PerformanceTester()
    tester.run_all_tests()
