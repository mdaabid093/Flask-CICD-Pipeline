# Flask CI/CD & GitOps Pipeline

A production-style DevOps pipeline built from scratch: a Flask app that goes
from `git push` to a running, monitored deployment with zero manual steps —
tested, containerized, deployed via GitOps, and observable.

**Pipeline:** GitHub Actions (CI) → Docker Hub → ArgoCD (GitOps) → Kubernetes → Prometheus & Grafana

---

## What this project shows

- A complete CI/CD pipeline, not just isolated tool usage
- GitOps delivery: Git is the single source of truth, and the cluster
  self-heals if it ever drifts from what Git declares
- Kubernetes fundamentals: Deployments, Services, rolling updates
- Application observability: custom Prometheus metrics and Grafana dashboards
- Real engineering trade-offs made along the way (see [Design Decisions](#design-decisions))

<!-- Add a screenshot here, e.g.: -->
<!-- ![Dashboard](docs/dashboard.png) -->
<!-- ![ArgoCD sync view](docs/argocd.png) -->

---

## Architecture

```
 git push
    │
    ▼
GitHub Actions ──► runs tests ──► builds image ──► pushes to Docker Hub
    │                                                     │
    │◄──── commits new image tag back to the repo ────────┘
    ▼
ArgoCD  (watches the repo, auto-syncs, self-heals drift)
    ▼
Kubernetes  (Deployment + Service, 2 replicas, rolling updates)
    ▼
Prometheus  (scrapes /metrics every 15s)  ──►  Grafana  (dashboards)
```

A single `git push` is the only manual step. Everything after that —
testing, building, tagging, deploying, and keeping the cluster in sync — is
automated.

---

## Tech Stack

Flask · Gunicorn · pytest · Docker · GitHub Actions · Kubernetes · Helm ·
ArgoCD · Prometheus · Grafana

---

## Getting Started

**Prerequisites:** Docker, `kubectl`, a local Kubernetes cluster, Helm,
Python 3.11+

```bash
# 1. Clone the repo
git clone https://github.com/mdaabid093/Flask-CICD-Pipeline.git
cd Flask-CICD-Pipeline

# 2. Run the app locally
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
# visit http://localhost:5000

# 3. Run the tests
pytest tests/

# 4. Build and run the container
docker build -t flask-devops-demo .
docker run -p 5000:5000 flask-devops-demo
```

**Deploying to Kubernetes:**

```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

**Setting up the full GitOps loop** requires installing ArgoCD and pointing
an Application at the `k8s/` folder in this repo (Application → Repository:
this repo, Path: `k8s`, Sync Policy: Automated).

**Setting up monitoring** requires installing the `kube-prometheus-stack`
Helm chart and applying `k8s/servicemonitor.yaml`, which tells Prometheus
to scrape this app's `/metrics` endpoint every 15 seconds.

---

## CI/CD Pipeline

Every push to `main` triggers `.github/workflows/ci.yml`:

1. Checkout code
2. Run the `pytest` suite — acts as a quality gate; nothing downstream runs
   if tests fail
3. Build a Docker image, tagged with the Git commit SHA (not `latest`) so
   every deployed version is traceable to an exact commit
4. Push the image to Docker Hub
5. Update `k8s/deployment.yaml` with the new image tag and commit that
   change back to the repo

ArgoCD picks up that manifest change automatically and rolls it out —
closing the loop from source code to a live, updated deployment.

---

## Observability

The app exposes a `/metrics` endpoint (via `prometheus_client`) tracking:

- **Request count**, labeled by method, endpoint, and status code
- **Request latency**, as a histogram, enabling percentile queries

Example Grafana queries used in the dashboard:

```promql
# Requests per second
rate(flask_request_count_total[1m])

# p95 latency
histogram_quantile(0.95, rate(flask_request_latency_seconds_bucket[5m]))
```

---

## Design Decisions

- **Commit-SHA image tags instead of `latest`** — guarantees every
  deployment is traceable to an exact commit and gives ArgoCD a real diff
  to detect, rather than a tag name that never changes.
- **GitOps (ArgoCD) over manual `kubectl apply`** — makes the cluster's
  state auditable, reversible (`git revert`), and self-healing if it ever
  drifts from what's declared in Git.
- **Manual Prometheus instrumentation (`prometheus_client`) over an
  auto-instrumentation library** — chosen after hitting a version
  incompatibility between Flask 3.x and a popular auto-instrumentation
  package; explicit instrumentation traded a little convenience for
  reliability and full visibility into what's actually being tracked.
- **Rolling updates with 2 replicas** — ensures zero-downtime deploys;
  Kubernetes brings up new pods and confirms health before terminating old
  ones.

---

## Project Structure

```
├── app.py                     # Flask app + Prometheus instrumentation
├── requirements.txt
├── Dockerfile
├── templates/index.html
├── tests/test_app.py
├── k8s/
│   ├── deployment.yaml
│   ├── service.yaml
│   └── servicemonitor.yaml
└── .github/workflows/ci.yml
```

---

## Author

Built by Md Aabid Hussain — [GitHub](https://github.com/mdaabid093)

*Feedback welcome — feel free to open an issue or reach out.*
