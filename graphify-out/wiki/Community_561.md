# Community 561

> 27 nodes · cohesion 0.12

## Key Concepts

- **Onyx Env ConfigMap** (10 connections) — `deployment/helm/charts/onyx/templates/configmap.yaml`
- **Celery K8s Health Probe (celery_k8s_probe.py)** (7 connections) — `deployment/helm/charts/onyx/templates/celery-worker-docfetching.yaml`
- **Celery Docfetching Worker Deployment** (5 connections) — `deployment/helm/charts/onyx/templates/celery-worker-docfetching.yaml`
- **Celery Docprocessing Worker Deployment** (5 connections) — `deployment/helm/charts/onyx/templates/celery-worker-docprocessing.yaml`
- **Celery Heavy Worker Deployment** (4 connections) — `deployment/helm/charts/onyx/templates/celery-worker-heavy.yaml`
- **Celery Light Worker Deployment** (4 connections) — `deployment/helm/charts/onyx/templates/celery-worker-light.yaml`
- **Celery Monitoring Worker Deployment** (4 connections) — `deployment/helm/charts/onyx/templates/celery-worker-monitoring.yaml`
- **Celery Primary Worker Deployment** (4 connections) — `deployment/helm/charts/onyx/templates/celery-worker-primary.yaml`
- **Celery User File Processing Worker Deployment** (4 connections) — `deployment/helm/charts/onyx/templates/celery-worker-user-file-processing.yaml`
- **Docfetching Worker HorizontalPodAutoscaler** (3 connections) — `deployment/helm/charts/onyx/templates/celery-worker-docfetching-hpa.yaml`
- **Docfetching Worker KEDA ScaledObject** (3 connections) — `deployment/helm/charts/onyx/templates/celery-worker-docfetching-scaledobject.yaml`
- **Dual Autoscaling Engine Selection (HPA vs KEDA)** (2 connections) — `deployment/helm/charts/onyx/templates/celery-worker-docfetching-scaledobject.yaml`
- **Docprocessing Worker HorizontalPodAutoscaler** (2 connections) — `deployment/helm/charts/onyx/templates/celery-worker-docprocessing-hpa.yaml`
- **Docprocessing Worker KEDA ScaledObject** (2 connections) — `deployment/helm/charts/onyx/templates/celery-worker-docprocessing-scaledobject.yaml`
- **Heavy Worker HorizontalPodAutoscaler** (2 connections) — `deployment/helm/charts/onyx/templates/celery-worker-heavy-hpa.yaml`
- **Heavy Worker KEDA ScaledObject** (2 connections) — `deployment/helm/charts/onyx/templates/celery-worker-heavy-scaledobject.yaml`
- **Light Worker HorizontalPodAutoscaler** (2 connections) — `deployment/helm/charts/onyx/templates/celery-worker-light-hpa.yaml`
- **Light Worker KEDA ScaledObject** (2 connections) — `deployment/helm/charts/onyx/templates/celery-worker-light-scaledobject.yaml`
- **Monitoring Worker HorizontalPodAutoscaler** (2 connections) — `deployment/helm/charts/onyx/templates/celery-worker-monitoring-hpa.yaml`
- **Monitoring Worker KEDA ScaledObject** (2 connections) — `deployment/helm/charts/onyx/templates/celery-worker-monitoring-scaledobject.yaml`
- **Primary Worker HorizontalPodAutoscaler** (2 connections) — `deployment/helm/charts/onyx/templates/celery-worker-primary-hpa.yaml`
- **Primary Worker KEDA ScaledObject** (2 connections) — `deployment/helm/charts/onyx/templates/celery-worker-primary-scaledobject.yaml`
- **User File Processing Worker HorizontalPodAutoscaler** (2 connections) — `deployment/helm/charts/onyx/templates/celery-worker-user-file-processing-hpa.yaml`
- **User File Processing Worker KEDA ScaledObject** (2 connections) — `deployment/helm/charts/onyx/templates/celery-worker-user-file-processing-scaledobject.yaml`
- **Indexing Model Server Deployment** (2 connections) — `deployment/helm/charts/onyx/templates/indexing-model-deployment.yaml`
- *... and 2 more nodes in this community*

## Relationships

- No strong cross-community connections detected

## Source Files

- `deployment/helm/charts/onyx/templates/celery-worker-docfetching-hpa.yaml`
- `deployment/helm/charts/onyx/templates/celery-worker-docfetching-scaledobject.yaml`
- `deployment/helm/charts/onyx/templates/celery-worker-docfetching.yaml`
- `deployment/helm/charts/onyx/templates/celery-worker-docprocessing-hpa.yaml`
- `deployment/helm/charts/onyx/templates/celery-worker-docprocessing-scaledobject.yaml`
- `deployment/helm/charts/onyx/templates/celery-worker-docprocessing.yaml`
- `deployment/helm/charts/onyx/templates/celery-worker-heavy-hpa.yaml`
- `deployment/helm/charts/onyx/templates/celery-worker-heavy-scaledobject.yaml`
- `deployment/helm/charts/onyx/templates/celery-worker-heavy.yaml`
- `deployment/helm/charts/onyx/templates/celery-worker-light-hpa.yaml`
- `deployment/helm/charts/onyx/templates/celery-worker-light-scaledobject.yaml`
- `deployment/helm/charts/onyx/templates/celery-worker-light.yaml`
- `deployment/helm/charts/onyx/templates/celery-worker-monitoring-hpa.yaml`
- `deployment/helm/charts/onyx/templates/celery-worker-monitoring-scaledobject.yaml`
- `deployment/helm/charts/onyx/templates/celery-worker-monitoring.yaml`
- `deployment/helm/charts/onyx/templates/celery-worker-primary-hpa.yaml`
- `deployment/helm/charts/onyx/templates/celery-worker-primary-scaledobject.yaml`
- `deployment/helm/charts/onyx/templates/celery-worker-primary.yaml`
- `deployment/helm/charts/onyx/templates/celery-worker-user-file-processing-hpa.yaml`
- `deployment/helm/charts/onyx/templates/celery-worker-user-file-processing-scaledobject.yaml`

## Audit Trail

- EXTRACTED: 60 (71%)
- INFERRED: 24 (29%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*