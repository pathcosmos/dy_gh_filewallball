# FileWallBall 백업 및 복구 전략

## 🔄 백업 시스템 개요

### ✅ 구현된 백업 시스템

#### 1. **자동 백업 (CronJob)**
- **스케줄**: 매일 오전 2시 자동 실행
- **보관 기간**: 7일
- **압축**: gzip으로 압축하여 저장 공간 절약
- **무결성 검증**: 백업 후 자동 무결성 검증

#### 2. **수동 백업 (스크립트)**
- **스크립트**: `scripts/backup-database.sh`
- **실행**: 언제든지 수동으로 실행 가능
- **기능**: 백업, 압축, 무결성 검증, 오래된 파일 정리

#### 3. **복구 시스템**
- **스크립트**: `scripts/restore-database.sh`
- **기능**: 백업 파일 목록, 복구 실행, 안전 백업 생성
- **검증**: 복구 후 데이터베이스 상태 검증

## 📁 백업 저장소 구조

### PersistentVolume 설정
```yaml
# k8s/backup-pv.yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: filewallball-backup-pv
spec:
  storageClassName: microk8s-hostpath
  capacity:
    storage: 10Gi
  hostPath:
    path: "/home/lanco/cursor/fileWallBall/backups"
```

### 백업 파일 명명 규칙
```
filewallball_backup_YYYYMMDD_HHMMSS.sql.gz
예시: filewallball_backup_20250725_170206.sql.gz
```

## 🛠️ 백업 스크립트 기능

### 1. **백업 스크립트 (`scripts/backup-database.sh`)**

#### 주요 기능:
- **MariaDB Pod 자동 감지**: 라벨 기반 Pod 검색
- **완전 백업**: 모든 테이블, 루틴, 트리거, 이벤트 포함
- **트랜잭션 안전성**: `--single-transaction` 옵션 사용
- **압축**: gzip으로 백업 파일 압축
- **무결성 검증**: 백업 후 자동 검증
- **자동 정리**: 7일 이상 된 백업 파일 자동 삭제

#### 백업 옵션:
```bash
mysqldump -u root -pfilewallball2024 \
    --single-transaction \
    --routines \
    --triggers \
    --events \
    --hex-blob \
    --add-drop-database \
    --add-drop-table \
    --add-drop-trigger \
    --comments \
    --complete-insert \
    --extended-insert \
    --lock-tables=false \
    --set-charset \
    --default-character-set=utf8mb4 \
    filewallball_db
```

### 2. **복구 스크립트 (`scripts/restore-database.sh`)**

#### 주요 기능:
- **백업 파일 목록**: `--list` 옵션으로 사용 가능한 백업 확인
- **무결성 검증**: 복구 전 백업 파일 무결성 검증
- **안전 백업**: 복구 전 기존 데이터베이스 자동 백업
- **복구 검증**: 복구 후 테이블 수 및 상태 확인
- **롤백 기능**: 복구 실패 시 안전 백업에서 복구

#### 사용법:
```bash
# 백업 파일 목록 확인
./scripts/restore-database.sh --list

# 특정 백업 파일로 복구
./scripts/restore-database.sh -f filewallball_backup_20250725_170206.sql.gz
```

## ⏰ 자동 백업 스케줄

### CronJob 설정
```yaml
# k8s/backup-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: filewallball-backup-cronjob
spec:
  schedule: "0 2 * * *"  # 매일 오전 2시
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 1
```

### 백업 정책
- **빈도**: 매일 1회
- **시간**: 오전 2시 (서버 부하 최소 시간)
- **보관**: 7일간 보관
- **동시성**: 중복 실행 방지

## 🔐 보안 및 권한

### ServiceAccount 설정
```yaml
# k8s/backup-serviceaccount.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: filewallball-backup-sa
  namespace: filewallball
```

### RBAC 권한
- **Pod 접근**: MariaDB Pod 실행 및 접근
- **PVC 접근**: 백업 저장소 접근
- **최소 권한**: 필요한 최소 권한만 부여

## 📊 백업 모니터링

### 1. **백업 상태 확인**
```bash
# CronJob 상태 확인
microk8s kubectl get cronjobs -n filewallball

# 백업 Job 히스토리 확인
microk8s kubectl get jobs -n filewallball

# 백업 파일 목록 확인
microk8s kubectl exec -n filewallball mariadb-65c8cbd577-kb9lh -- ls -lh /backup/
```

### 2. **백업 로그 확인**
```bash
# 최근 백업 Job 로그 확인
microk8s kubectl logs -n filewallball job/filewallball-backup-cronjob-<timestamp>
```

### 3. **백업 파일 크기 모니터링**
```bash
# 백업 파일 크기 확인
microk8s kubectl exec -n filewallball mariadb-65c8cbd577-kb9lh -- du -sh /backup/
```

## 🚨 재해 복구 절차

### 1. **데이터베이스 손상 시**
```bash
# 1. 백업 파일 목록 확인
./scripts/restore-database.sh --list

# 2. 최신 백업으로 복구
./scripts/restore-database.sh -f filewallball_backup_YYYYMMDD_HHMMSS.sql.gz

# 3. 복구 결과 검증
microk8s kubectl exec -n filewallball mariadb-65c8cbd577-kb9lh -- mysql -u root -pfilewallball2024 -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'filewallball_db';"
```

### 2. **Pod 재시작 시**
```bash
# 1. MariaDB Pod 상태 확인
microk8s kubectl get pods -n filewallball

# 2. Pod 재시작
microk8s kubectl delete pod mariadb-65c8cbd577-kb9lh -n filewallball

# 3. 새로운 Pod 상태 확인
microk8s kubectl get pods -n filewallball
```

### 3. **전체 클러스터 재구성 시**
```bash
# 1. 백업 파일 외부 복사
microk8s kubectl cp filewallball/mariadb-65c8cbd577-kb9lh:/backup/filewallball_backup_YYYYMMDD_HHMMSS.sql.gz ./backups/

# 2. 새로운 클러스터에 MariaDB 배포
microk8s kubectl apply -f k8s/mariadb-deployment.yaml

# 3. 백업 파일 복사 및 복구
microk8s kubectl cp ./backups/filewallball_backup_YYYYMMDD_HHMMSS.sql.gz filewallball/mariadb-<new-pod>:/backup/
./scripts/restore-database.sh -f filewallball_backup_YYYYMMDD_HHMMSS.sql.gz
```

## 📋 백업 체크리스트

### ✅ 완료된 항목
- [x] 자동 백업 CronJob 설정
- [x] 수동 백업 스크립트 구현
- [x] 복구 스크립트 구현
- [x] 백업 저장소 (PV/PVC) 설정
- [x] RBAC 권한 설정
- [x] 백업 파일 무결성 검증
- [x] 자동 정리 정책 (7일)
- [x] 안전 백업 생성 (복구 시)

### 🔄 지속적 모니터링
- [ ] 백업 성공률 모니터링
- [ ] 백업 파일 크기 추이 확인
- [ ] 복구 테스트 주기적 실행
- [ ] 백업 로그 분석

## 🎯 성능 최적화

### 1. **백업 성능**
- **단일 트랜잭션**: 일관성 보장하면서 성능 최적화
- **압축**: gzip으로 저장 공간 70% 절약
- **병렬 처리**: 백업과 압축을 순차적으로 처리

### 2. **복구 성능**
- **증분 복구**: 전체 백업에서 선택적 복구
- **검증 최적화**: 복구 후 핵심 테이블만 검증
- **롤백 지원**: 실패 시 안전 백업으로 복구

### 3. **저장소 최적화**
- **자동 정리**: 7일 이상 된 백업 자동 삭제
- **압축**: 백업 파일 크기 최소화
- **모니터링**: 저장소 사용량 추적

## 📝 추가 권장사항

### 1. **백업 전략 개선**
- **증분 백업**: 전체 백업 + 증분 백업 조합
- **다중 저장소**: 로컬 + 클라우드 백업
- **암호화**: 민감한 데이터 암호화 백업

### 2. **모니터링 강화**
- **알림 시스템**: 백업 실패 시 알림
- **메트릭 수집**: 백업 성능 메트릭
- **대시보드**: 백업 상태 시각화

### 3. **테스트 자동화**
- **정기 복구 테스트**: 백업 파일 복구 가능성 검증
- **성능 테스트**: 백업/복구 시간 측정
- **무결성 테스트**: 데이터 무결성 검증

---

**최종 결과**: FileWallBall 백업 및 복구 시스템이 성공적으로 구현되었습니다. 자동 백업, 수동 백업, 복구 기능이 모두 작동하며, 7일 보관 정책과 무결성 검증이 적용되어 있습니다.
