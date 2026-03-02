# IntegrityBot — Kubernetes Deploy Qo'llanmasi

## Fayl tuzilmasi

```
k8s/
├── namespace.yaml          # integritybot namespace
├── configmap.yaml          # Maxfiy bo'lmagan sozlamalar
├── secrets.yaml            # Maxfiy qiymatlar (git ga qo'SHILMASIN!)
├── deployments/
│   ├── backend.yaml        # FastAPI backend (2 replica, HPA bilan 10 gacha)
│   ├── frontend.yaml       # Vue.js + nginx (2 replica)
│   └── redis.yaml          # Redis 7 + PVC
├── services/
│   └── services.yaml       # Backend, Frontend, Redis ClusterIP services
├── ingress/
│   └── ingress.yaml        # NGINX Ingress + cert-manager (Let's Encrypt TLS)
├── hpa/
│   └── hpa.yaml            # Horizontal Pod Autoscaler
└── jobs/
    └── db-migration.yaml   # DB migration Job (deploy oldidan)
```

## Talablar

- Kubernetes 1.25+
- `kubectl` sozlangan
- NGINX Ingress Controller
- cert-manager (TLS uchun, ixtiyoriy)

## O'rnatish

### 1. NGINX Ingress Controller

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/cloud/deploy.yaml
```

### 2. cert-manager (TLS uchun)

```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/latest/download/cert-manager.yaml
```

### 3. Secrets sozlash

`k8s/secrets.yaml` faylida barcha `CHANGE_ME` qiymatlarini o'zgartiring, yoki `.env` dan avtomatik:

```bash
kubectl create secret generic integritybot-secrets \
  --namespace=integritybot \
  --from-env-file=.env \
  --dry-run=client -o yaml > k8s/secrets.yaml
```

### 4. Docker image larni build qilish

```bash
docker build -t integritybot/backend:latest ./backend
docker build -t integritybot/frontend:latest ./frontend
docker push integritybot/backend:latest
docker push integritybot/frontend:latest
```

### 5. To'liq deploy (tartib bilan)

```bash
# 1. Namespace
kubectl apply -f k8s/namespace.yaml

# 2. Konfiguratsiya
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml

# 3. DB migration (deploy oldidan)
kubectl apply -f k8s/jobs/db-migration.yaml
kubectl wait --for=condition=complete job/integritybot-db-migrate \
  -n integritybot --timeout=120s

# 4. Deployments
kubectl apply -f k8s/deployments/

# 5. Services
kubectl apply -f k8s/services/

# 6. Ingress
kubectl apply -f k8s/ingress/

# 7. HPA
kubectl apply -f k8s/hpa/
```

### 6. Barcha bir buyruqda

```bash
kubectl apply -f k8s/namespace.yaml && \
kubectl apply -f k8s/configmap.yaml && \
kubectl apply -f k8s/secrets.yaml && \
kubectl apply -f k8s/deployments/ && \
kubectl apply -f k8s/services/ && \
kubectl apply -f k8s/ingress/ && \
kubectl apply -f k8s/hpa/
```

## Holat tekshirish

```bash
# Podlar
kubectl get pods -n integritybot

# Deployment holati
kubectl get deployments -n integritybot

# HPA holati
kubectl get hpa -n integritybot

# Loglar
kubectl logs -n integritybot deployment/integritybot-backend -f
```

## Yangilash (Rolling Update — zero downtime)

```bash
kubectl set image deployment/integritybot-backend \
  backend=integritybot/backend:v1.1.0 -n integritybot
```

## Xavfsizlik eslatmalari

- `k8s/secrets.yaml` faylini `.gitignore` da saqlang
- Production da **External Secrets Operator** yoki **Sealed Secrets** ishlating
- Image larni `latest` o'rniga aniq version tag bilan belgilang (`v1.0.0`)
