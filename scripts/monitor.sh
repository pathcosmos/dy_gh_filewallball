#!/bin/bash

echo "📊 FileWallBall 시스템 모니터링..."

# Pod 상태 확인
echo "1. Pod 상태:"
kubectl get pods -n filewallball -o wide

echo ""
echo "2. 서비스 상태:"
kubectl get svc -n filewallball

echo ""
echo "3. HPA 상태:"
kubectl get hpa -n filewallball

echo ""
echo "4. 리소스 사용량:"
kubectl top pods -n filewallball

echo ""
echo "5. 로그 확인 (최근 10줄):"
kubectl logs -n filewallball deployment/filewallball-deployment --tail=10

echo ""
echo "6. Redis 상태:"
kubectl logs -n filewallball deployment/redis-deployment --tail=5

echo ""
echo "7. 메트릭 확인:"
API_POD=$(kubectl get pods -n filewallball -l app=filewallball -o jsonpath='{.items[0].metadata.name}')
if [ ! -z "$API_POD" ]; then
    kubectl exec -n filewallball $API_POD -- curl -s localhost:8000/metrics | grep -E "(file_uploads_total|file_downloads_total)"
fi

echo ""
echo "8. PVC 상태:"
kubectl get pvc -n filewallball

echo ""
echo "9. 이벤트 확인:"
kubectl get events -n filewallball --sort-by='.lastTimestamp' | tail -10 