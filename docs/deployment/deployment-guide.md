# Family Weather Dashboard — Deployment Guide
_Last updated: 2026-03-01_

---

## Account Reference

| Item | Value |
|---|---|
| GCP project ID | `gen-lang-client-0266464307` |
| GCP project number | `707581314081` |
| GCP region | `asia-east1` |
| GCS bucket | `family-weather-dashboard` |
| Artifact Registry repo | `family-weather` |
| Docker image path | `asia-east1-docker.pkg.dev/gen-lang-client-0266464307/family-weather/app:latest` |
| Cloud Run service | `family-weather` |
| Cloud Run URL | `https://family-weather-707581314081.asia-east1.run.app` |
| Modal workspace | `icyswordrain` |
| Modal app | `family-weather-engine` |
| Modal health | `https://icyswordrain--family-weather-engine-health.modal.run` |
| Modal refresh | `https://icyswordrain--family-weather-engine-refresh.modal.run` |
| Modal broadcast | `https://icyswordrain--family-weather-engine-broadcast.modal.run` |
| GitHub repo | `icyswordrain-hue/family-weather` (branch: `master`) |
| Compute service account | `707581314081-compute@developer.gserviceaccount.com` |
| GitHub Actions service account | `github-actions-sa@gen-lang-client-0266464307.iam.gserviceaccount.com` |
| Local working directory | `C:\Users\User\.gemini\antigravity\scratch\family-weather` |
| Python version | 3.13.0 |
| OS | Windows |

---

## How Deployment Works

Every push to `master` triggers GitHub Actions, which does five things in order:

1. Checks out your code
2. Builds a Docker image from your code
3. Pushes the image to Artifact Registry (`asia-east1`)
4. Deploys the new image to Cloud Run (the Flask web server)
5. Deploys the Modal pipeline (`backend/modal_app.py`)

**You never need to run deployment commands manually.** Push to master and everything updates automatically.

The only exception is rotating API keys — that requires running `scripts/sync_secrets_to_modal.py` manually.

---

## What to Deploy When

| What changed | Action |
|---|---|
| `app.py`, `web/`, templates, static files | Push to master |
| `backend/`, `data/`, `narration/` | Push to master |
| `config.py` | Push to master |
| API key rotated | Run `sync_secrets_to_modal.py`, then update secret version in GCP console |
| Modal endpoint URLs changed | Update `MODAL_REFRESH_URL` and `MODAL_BROADCAST_URL` in GitHub secrets |

---

## Step 1 — GCP Project Setup

Set the active project. Run this first in every new terminal session:

```
gcloud config set project gen-lang-client-0266464307
```

Enable required APIs (one-time):

```
gcloud services enable run.googleapis.com cloudscheduler.googleapis.com storage.googleapis.com secretmanager.googleapis.com artifactregistry.googleapis.com
```

---

## Step 2 — GCS Bucket

Create the bucket (one-time):

```
gcloud storage buckets create gs://family-weather-dashboard --location=asia-east1
```

Set 30-day lifecycle on audio files (one-time):

```
gcloud storage buckets update gs://family-weather-dashboard --lifecycle-file=lifecycle.json
```

Make bucket publicly readable:

```
gcloud storage buckets add-iam-policy-binding gs://family-weather-dashboard --member=allUsers --role=roles/storage.objectViewer
```

---

## Step 3 — GCP Secrets

Add each secret to Secret Manager. Replace `VALUE` with the actual key:

```
echo VALUE | gcloud secrets create CWA_API_KEY --data-file=-
echo VALUE | gcloud secrets create MOENV_API_KEY --data-file=-
echo VALUE | gcloud secrets create ANTHROPIC_API_KEY --data-file=-
echo VALUE | gcloud secrets create GEMINI_API_KEY --data-file=-
echo family-weather-dashboard | gcloud secrets create GCS_BUCKET_NAME --data-file=-
echo gen-lang-client-0266464307 | gcloud secrets create GCP_PROJECT_ID --data-file=-
```

To update an existing secret:

```
echo NEWVALUE | gcloud secrets versions add SECRET_NAME --data-file=-
```

---

## Step 4 — Artifact Registry

Create the Docker repository (one-time):

```
gcloud artifacts repositories create family-weather --repository-format=docker --location=asia-east1 --project=gen-lang-client-0266464307
```

Authenticate Docker to it:

```
gcloud auth configure-docker asia-east1-docker.pkg.dev
```

---

## Step 5 — GitHub Actions Service Account

Create the service account (one-time):

```
gcloud iam service-accounts create github-actions-sa --display-name="GitHub Actions Deployer" --project=gen-lang-client-0266464307
```

Grant required roles:

```
gcloud projects add-iam-policy-binding gen-lang-client-0266464307 --member="serviceAccount:github-actions-sa@gen-lang-client-0266464307.iam.gserviceaccount.com" --role="roles/run.admin"

gcloud projects add-iam-policy-binding gen-lang-client-0266464307 --member="serviceAccount:github-actions-sa@gen-lang-client-0266464307.iam.gserviceaccount.com" --role="roles/iam.serviceAccountUser"

gcloud artifacts repositories add-iam-policy-binding family-weather --location=asia-east1 --member="serviceAccount:github-actions-sa@gen-lang-client-0266464307.iam.gserviceaccount.com" --role="roles/artifactregistry.writer"
```

Create the key — **do not commit this file to git**:

```
gcloud iam service-accounts keys create github-actions-key.json --iam-account=github-actions-sa@gen-lang-client-0266464307.iam.gserviceaccount.com
```

Open `github-actions-key.json`, copy all contents. Delete the file immediately after:

```
Remove-Item github-actions-key.json
```

---

## Step 6 — GitHub Secrets

Go to `https://github.com/icyswordrain-hue/family-weather/settings/secrets/actions` and add these repository secrets:

| Secret name | Value |
|---|---|
| `DOCKERHUB_USERNAME` | `icyswordrain` |
| `DOCKERHUB_TOKEN` | hub.docker.com → Account Settings → Security → New Access Token |
| `GCP_SA_KEY` | Full JSON contents of `github-actions-key.json` (copied in Step 5) |
| `MODAL_REFRESH_URL` | `https://icyswordrain--family-weather-engine-refresh.modal.run` |
| `MODAL_BROADCAST_URL` | `https://icyswordrain--family-weather-engine-broadcast.modal.run` |
| `MODAL_TOKEN_ID` | `ak-qM3Gt8v5UWVFSdyUnXofuz` |
| `MODAL_TOKEN_SECRET` | `as-QiuUw1fHxdcqzewYqgsmNE` |

---

## Step 7 — Modal Setup

Install Modal:

```
pip install modal
```

Authenticate (opens browser):

```
modal token new
```

Create a dedicated CI token for GitHub Actions:

```
modal token new --profile github-actions
```

View the token values:

```
type C:\Users\User\.modal.toml
```

Copy the `token_id` and `token_secret` from the `[github-actions]` profile into the `MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET` GitHub secrets.

Deploy the Modal pipeline (first time, and whenever GitHub Actions is not yet set up):

```
cd C:\Users\User\.gemini\antigravity\scratch\family-weather
modal deploy backend/modal_app.py
```

Confirm it deployed:

```
modal app list
```

Expected: `family-weather-engine` with state `deployed`.

Sync secrets from GCP to Modal:

```
python scripts/sync_secrets_to_modal.py
```

---

## Step 8 — GitHub Actions Workflow

Create `.github/workflows/deploy.yml` with this content:

```yaml
name: Deploy

on:
  push:
    branches: [master]

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Authenticate to GCP
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Configure Docker for Artifact Registry
        run: gcloud auth configure-docker asia-east1-docker.pkg.dev --quiet

      - name: Build and push image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: asia-east1-docker.pkg.dev/gen-lang-client-0266464307/family-weather/app:latest

      - name: Deploy to Cloud Run
        uses: google-github-actions/deploy-cloudrun@v2
        with:
          service: family-weather
          region: asia-east1
          image: asia-east1-docker.pkg.dev/gen-lang-client-0266464307/family-weather/app:latest
          env_vars: |
            RUN_MODE=CLOUD
            MODAL_REFRESH_URL=${{ secrets.MODAL_REFRESH_URL }}
            MODAL_BROADCAST_URL=${{ secrets.MODAL_BROADCAST_URL }}

      - name: Deploy Modal pipeline
        env:
          MODAL_TOKEN_ID: ${{ secrets.MODAL_TOKEN_ID }}
          MODAL_TOKEN_SECRET: ${{ secrets.MODAL_TOKEN_SECRET }}
        run: |
          pip install modal
          modal deploy backend/modal_app.py
```

Commit and push to master to trigger the first automated deploy:

```
git add .github/workflows/deploy.yml
git commit -m "add github actions workflow"
git push origin master
```

Watch the run at `https://github.com/icyswordrain-hue/family-weather/actions`.

---

## Step 9 — First Cloud Run Deploy

This step is only needed the first time, before GitHub Actions has run. After that, GitHub Actions handles all deploys.

Build and push the image manually:

```
gcloud auth configure-docker asia-east1-docker.pkg.dev
docker build -t asia-east1-docker.pkg.dev/gen-lang-client-0266464307/family-weather/app:latest .
docker push asia-east1-docker.pkg.dev/gen-lang-client-0266464307/family-weather/app:latest
```

Deploy to Cloud Run:

```
gcloud run deploy family-weather --image=asia-east1-docker.pkg.dev/gen-lang-client-0266464307/family-weather/app:latest --region=asia-east1 --platform=managed --service-account=707581314081-compute@developer.gserviceaccount.com --allow-unauthenticated --min-instances=0 --max-instances=2 --memory=512Mi --timeout=300 --set-env-vars=RUN_MODE=CLOUD,GCS_BUCKET_NAME=family-weather-dashboard,GCP_PROJECT_ID=gen-lang-client-0266464307,NARRATION_PROVIDER=CLAUDE,MODAL_REFRESH_URL=https://icyswordrain--family-weather-engine-refresh.modal.run,MODAL_BROADCAST_URL=https://icyswordrain--family-weather-engine-broadcast.modal.run --update-secrets=CWA_API_KEY=CWA_API_KEY:latest,MOENV_API_KEY=MOENV_API_KEY:latest,ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:latest
```

Verify:

```
curl https://family-weather-707581314081.asia-east1.run.app/api/health
```

---

## Step 10 — Cloud Scheduler

Create the three cron jobs (one-time). Run each separately in cmd:

```
gcloud scheduler jobs create http weather-morning --location=asia-east1 --schedule="15 6 * * *" --time-zone="Asia/Taipei" --uri=https://family-weather-707581314081.asia-east1.run.app/api/refresh --message-body={\"slot\":\"morning\"} --headers=Content-Type=application/json
```

```
gcloud scheduler jobs create http weather-midday --location=asia-east1 --schedule="15 11 * * *" --time-zone="Asia/Taipei" --uri=https://family-weather-707581314081.asia-east1.run.app/api/refresh --message-body={\"slot\":\"midday\"} --headers=Content-Type=application/json
```

```
gcloud scheduler jobs create http weather-evening --location=asia-east1 --schedule="15 17 * * *" --time-zone="Asia/Taipei" --uri=https://family-weather-707581314081.asia-east1.run.app/api/refresh --message-body={\"slot\":\"evening\"} --headers=Content-Type=application/json
```

Verify:

```
gcloud scheduler jobs list --location=asia-east1
```

Expected: three jobs, all `ENABLED`, timezone `Asia/Taipei`.

---

## Verification Checklist

Run these after any deployment to confirm everything is healthy.

```
curl https://family-weather-707581314081.asia-east1.run.app/api/health
```
Expected: `{"status": "ok"}`

```
modal app list
```
Expected: `family-weather-engine` state `deployed`

```
gcloud scheduler jobs list --location=asia-east1
```
Expected: `weather-morning`, `weather-midday`, `weather-evening` all `ENABLED`

```
curl https://family-weather-707581314081.asia-east1.run.app/api/broadcast
```
Expected: JSON with `narration_text`, `processed_data`, `paragraphs`

Manually trigger a pipeline run to confirm end-to-end:

```
gcloud scheduler jobs run weather-morning --location=asia-east1
```

---

## Rotating API Keys

1. Update the secret in GCP Secret Manager:
```
echo NEWVALUE | gcloud secrets versions add SECRET_NAME --data-file=-
```

2. Sync to Modal:
```
python scripts/sync_secrets_to_modal.py
```

3. If the key is used by Cloud Run directly (not just Modal), update the secret version in GCP console → Cloud Run → Edit & Deploy New Revision → Variables & Secrets.
