lask CI/CD & GitOps Pipeline — Project Overview

A hands-on DevOps project demonstrating a complete path from source code to a running, self-healing deployment: CI with GitHub Actions → containerization with Docker → orchestration with Kubernetes → GitOps delivery with ArgoCD → observability with Prometheus & Grafana.

This document is written as an interview-ready summary: what was built, why each piece exists, how they connect, and the real issues hit (and fixed) along the way.

1. Architecture at a Glance
Developer
   │  git push
   ▼
GitHub Repository ───────────────► GitHub Actions (CI)
   ▲                                   │
   │ bot commit (new image tag)        │ 1. run tests (pytest)
   │                                   │ 2. build Docker image
   │                                   │ 3. push image → Docker Hub
   │                                   │ 4. update k8s/deployment.yaml
   │                                   │ 5. commit + push back to repo
   └───────────────────────────────────┘
                    │
                    ▼
              ArgoCD (GitOps)
     watches the Git repo continuously
     auto-syncs cluster state to match Git
     self-heals if cluster drifts from Git
                    │
                    ▼
        Kubernetes Cluster (local)
     ┌─────────────────────────────┐
     │ Deployment (2 replicas)     │
     │ Service (NodePort)          │
     │ ServiceMonitor              │
     └─────────────────────────────┘
                    │
                    ▼
      Prometheus (scrapes /metrics every 15s)
                    │
                    ▼
      Grafana (dashboards & visualization)

Core idea (GitOps): Git is the single source of truth. Nobody runs kubectl apply by hand for normal changes — a git push alone is enough to take code from a laptop to a running, monitored deployment.

2. Tech Stack
Layer	Tool	Purpose
Application	Flask (Python)	Simple web app with health/info endpoints
WSGI server	Gunicorn	Production-grade server (not Flask's dev server)
Testing	pytest	Runs automatically in CI, gates bad code from deploying
Containerization	Docker	Packages app + dependencies into a portable image
Image registry	Docker Hub	Stores built images, tagged by Git commit SHA
CI	GitHub Actions	Tests, builds, pushes images, updates manifests
Orchestration	Kubernetes	Runs and manages containers (Deployment + Service)
GitOps / CD	ArgoCD	Watches Git, auto-syncs cluster, self-heals drift
Metrics collection	Prometheus	Scrapes /metrics on an interval, stores time-series data
Visualization	Grafana	Dashboards built on top of Prometheus data
Package management (K8s)	Helm	Installed the Prometheus/Grafana stack as one chart
3. Repository Structure
flask-devops-demo/
├── app.py                     # Flask app: routes, metrics instrumentation
├── requirements.txt           # Pinned dependencies (Flask, gunicorn, prometheus-client)
├── Dockerfile                 # Multi-step image build, layer-cached deps
├── .dockerignore / .gitignore # Keep venv/tests out of image & repo bloat
├── templates/
│   └── index.html             # Styled status page (version badge, pod hostname)
├── tests/
│   └── test_app.py            # pytest suite — CI's quality gate
├── k8s/
│   ├── deployment.yaml        # 2 replicas, image tag updated automatically by CI
│   ├── service.yaml           # NodePort service, labeled for Prometheus discovery
│   └── servicemonitor.yaml    # Tells Prometheus Operator to scrape this service
└── .github/workflows/
    └── ci.yml                 # The full CI pipeline definition
4. How the CI Pipeline Works (.github/workflows/ci.yml)

Triggered on every push to main:

Checkout code — fresh runner VM, pulls the repo
Set up Python — matches the version used in the Docker image
Install dependencies — from requirements.txt
Run tests (pytest) — the quality gate; if this fails, everything downstream is skipped and nothing broken ever gets deployed
Log in to Docker Hub — using GitHub Secrets (DOCKERHUB_USERNAME, DOCKERHUB_TOKEN), never hardcoded credentials
Build & push the image — tagged with the commit SHA (not latest), so every deployed version is traceable to an exact commit
Update k8s/deployment.yaml — a sed command rewrites the image tag in place to the new SHA
Commit and push that manifest change back to the repo, authored by a bot identity, with [skip ci] in the message to avoid an infinite trigger loop

This last step is what closes the loop — it's the difference between "CI builds an image" and "a single git push results in a live redeploy with no human running any kubectl command."

5. How GitOps / ArgoCD Works
An ArgoCD Application object points at this repo's k8s/ folder and a target cluster/namespace
Auto-Sync is enabled: any new commit ArgoCD detects in k8s/ is applied automatically — no manual "Sync" click needed
Self Heal is enabled: if someone manually changes or deletes a resource directly in the cluster (bypassing Git), ArgoCD detects the drift and reverts it back to match Git within moments — proven by manually deleting the Service and watching ArgoCD recreate it unprompted
Prune is enabled: if a resource is removed from Git, ArgoCD removes it from the cluster too, so nothing lingers that Git no longer describes

Rollback approach: ArgoCD's own "History and Rollback" UI can re-apply an older synced state instantly, but since Auto-Sync + Self Heal are on, ArgoCD will re-apply the latest Git commit again unless Git itself is also rolled back. The durable fix is git revert <bad-commit> — this keeps Git and the live cluster in agreement permanently, rather than fighting the self-healing behavior.

6. Kubernetes Objects Explained
Deployment — declares how many replicas (2) of the Flask container should run, and Kubernetes keeps that many alive automatically, replacing any that crash. Rolling updates happen automatically on image change: new pods come up and pass health checks before old ones are terminated — zero-downtime deploys.
Service (NodePort) — gives the Pods a stable network identity even as individual Pods are replaced; routes traffic to whichever Pods currently match its label selector.
ServiceMonitor — a custom resource (added by the Prometheus Operator) that tells Prometheus which Service to scrape, on which port, at which path, and how often — without hand-editing Prometheus's own config file.
7. Monitoring: Prometheus + Grafana

Why: deployment automation (CI/CD) proves code reaches production; monitoring proves it's actually healthy once there. Both are expected DevOps skills.

The Flask app exposes a /metrics endpoint using the prometheus_client Python library — a Counter tracks total requests (labeled by method, endpoint, status code) and a Histogram tracks request latency.
Prometheus (installed via the kube-prometheus-stack Helm chart) scrapes that endpoint every 15 seconds via the ServiceMonitor and stores the values as time-series data.
Grafana connects to Prometheus as a data source and visualizes it — e.g. rate(flask_request_count_total[1m]) for requests-per-second, or histogram_quantile(0.95, rate(flask_request_latency_seconds_bucket[5m])) for p95 latency, a standard real-world SLO metric.

Core mental model: the app generates raw numbers → Prometheus pulls (scrapes) and stores them with timestamps → Grafana queries Prometheus and draws the results as panels grouped into dashboards.

8. Real Issues Hit & Fixed (good interview material)

Debugging real problems is often more convincing in an interview than a clean run-through. Genuine issues resolved during this build:

venv/ accidentally committed to Git, causing ArgoCD to reject the repo outright with an "out-of-bounds symlinks" error (a Python venv's symlinked interpreter pointed outside the repo). Fixed with git rm -r --cached venv/ plus a correct .gitignore.
GitHub Actions secret misconfiguration (Username and password required on Docker Hub login) — resolved by correctly naming repo secrets and using a Docker Hub access token, never the account password.
Divergent Git branches after CI pushed a bot commit that wasn't pulled locally first — resolved by understanding merge vs rebase strategies (git config pull.rebase false) instead of blindly retrying.
A stray YAML character (-name: http instead of name: http) silently broke Service port naming, which in turn broke Prometheus's ability to discover the scrape target — a good example of why small YAML syntax errors can cause confusing downstream failures.
Missing gunicorn in requirements.txt caused CrashLoopBackOff in production pods — even though CI showed fully green — because passing tests never guaranteed the container itself could actually start. This is a concrete example of why testing alone isn't a complete safety net; the built artifact still needs to be verified.
Flask/prometheus-flask-exporter version incompatibility — a third-party auto-instrumentation library silently failed to register its /metrics route on a newer Flask version. Resolved by switching to direct, explicit instrumentation with prometheus_client, trading a little convenience for reliability and a clearer understanding of what was actually happening under the hood.
9. What This Project Demonstrates
End-to-end CI/CD pipeline design, not just individual tool usage
GitOps principles: Git as source of truth, declarative infrastructure, drift detection and self-healing
Kubernetes fundamentals: Deployments, Services, label-based linking, rolling updates
Observability basics: metrics instrumentation, scraping, PromQL, dashboarding
Real debugging methodology: isolating a failure to a specific stage of the pipeline rather than guessing, checking logs/events at each layer
