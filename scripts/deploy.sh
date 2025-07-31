#!/bin/bash

set -e

echo "🚀 FileWallBall API System 배포 시작..."

# MicroK8s 애드온 활성화
echo "📦 MicroK8s 애드온 활성화 중..."
microk8s enable dns
microk8s enable storage
microk8s enable ingress
microk8s enable metrics-server

# Docker 이미지 빌드
echo "🐳 Docker 이미지 빌드 중..."
docker build -t filewallball:latest .

# MicroK8s에 이미지 로드
echo "📤 MicroK8s에 이미지 로드 중..."
microk8s ctr image import filewallball:latest

# 네임스페이스 생성
echo "🏗️ Kubernetes 리소스 배포 중..."
kubectl apply -f k8s/namespace.yaml

# ConfigMap 배포
kubectl apply -f k8s/configmap.yaml

# MariaDB 배포
kubectl apply -f k8s/mariadb-deployment.yaml

# Redis 배포
kubectl apply -f k8s/redis-deployment.yaml

# PVC 생성
kubectl apply -f k8s/pvc.yaml

# 애플리케이션 배포
kubectl apply -f k8s/app-deployment.yaml

# 서비스 배포
kubectl apply -f k8s/service.yaml

# HPA 배포
kubectl apply -f k8s/hpa.yaml

# Ingress 배포
kubectl apply -f k8s/ingress.yaml

echo "⏳ 배포 완료 대기 중..."
kubectl wait --for=condition=available --timeout=300s deployment/mariadb-deployment -n filewallball
kubectl wait --for=condition=available --timeout=300s deployment/filewallball-deployment -n filewallball
kubectl wait --for=condition=available --timeout=300s deployment/redis-deployment -n filewallball

echo "✅ 배포 완료!"
echo ""
echo "📊 배포 상태 확인:"
kubectl get pods -n filewallball
echo ""
echo "🌐 서비스 정보:"
kubectl get svc -n filewallball
echo ""
echo "📈 HPA 상태:"
kubectl get hpa -n filewallball
echo ""
echo "🔗 접속 정보:"
echo "API Base URL: http://filewallball-service.filewallball.svc.cluster.local:8000"
echo "LoadBalancer IP: $(kubectl get svc filewallball-ingress -n filewallball -o jsonpath='{.status.loadBalancer.ingress[0].ip}')"
