# Cloud Deployment Guide
_Family Weather Dashboard — Edward Canada Lee_

**Account references used throughout this guide:**
- GCP project ID: `gen-lang-client-0266464307`
- GCP project number: `707581314081`
- GCP region: `asia-east1`
- Docker Hub: `icyswordrain`
- Modal workspace: `icyswordrain`
- GitHub repo: `icyswordrain-hue/family-weather` (branch: `master`)
- Default compute service account: `707581314081-compute@developer.gserviceaccount.com`

---

## Overview

```
GitHub (master) → GitHub Actions → Docker Hub (icyswordrain/family-weather:latest)
                                 → Cloud Run redeploy

Cloud Scheduler (06:15 / 11:15 / 17:15 CST)
    → POST /api/refresh on Cloud Run (Flask proxy)
    → Modal pipeline worker (fetch + LLM + TTS cache)
    → GCS bucket (broadcasts, audio, regen)
    → Dashboard reads from GCS
```

Complete steps in order. Each step ends with a confirmation check.

---

## Step 1 — Point GCP CLI at the Right Project

```powershell
gcloud config set project gen-lang-client-0266464307
gcloud config get project
```

Expected: `gen-lang-client-0266464307`

Enable required APIs:

```powershell
gcloud services enable `
  run.googleapis.com `
  cloudscheduler.googleapis.com `
  storage.googleapis.com `
  secretmanager.googleapis.com `
  artifactregistry.googleapis.com
```

**Check:** Completes without errors.

---

## Step 2 — GCS Bucket

```powershell
gcloud storage buckets create gs://family-weather-dashboard `
  --location=asia-east1 `
  --uniform-bucket-level-access
```

Make bucket public (audio served directly to browser):

```powershell
gcloud storage buckets add-iam-policy-binding gs://family-weather-dashboard `
  --member=allUsers `
  --role=roles/storage.objectViewer
```

Create `lifecycle.json` in your project root:

```json
{
  "rule": [
    {
      "action": {"type": "Delete"},
      "condition": {
        "age": 30,
        "matchesPrefix": ["audio/"]
      }
    }
  ]
}
```

Apply it:

```powershell
gcloud storage buckets update gs://family-weather-dashboard `
  --lifecycle-file=lifecycle.json
```

**Check:**
```powershell
gcloud storage buckets describe gs://family-weather-dashboard
```
Confirm public access and lifecycle rule are present.

---

## Step 3 — IAM: Grant Compute Service Account GCS Access

The default compute service account already has Secret Manager access (confirmed in your setup). Add GCS write access so Cloud Run and Modal can write broadcasts and audio:

```powershell
gcloud projects add-iam-policy-binding gen-lang-client-0266464307 `
  --member="serviceAccount:707581314081-compute@developer.gserviceaccount.com" `
  --role="roles/storage.objectAdmin"
```

**Check:**
```powershell
gcloud projects get-iam-policy gen-lang-client-0266464307 `
  --flatten="bindings[].members" `
  --filter="bindings.members:707581314081-compute@developer.gserviceaccount.com" `
  --format="table(bindings.role)"
```
Should list both `roles/secretmanager.secretAccessor` and `roles/storage.objectAdmin`.

---

## Step 4 — Modal Setup

### 4a. Install and authenticate

```powershell
pip install modal
modal token new
```

Browser opens — log in with your Modal account (`icyswordrain`).

### 4b. Sync secrets from GCP Secret Manager to Modal

Create `scripts/sync_secrets_to_modal.py` in your project root:

```python
"""
Pulls secrets from GCP Secret Manager and pushes to Modal.
Run once now. Re-run whenever a key rotates or a new key is added.
Skips secrets not found in GCP without failing.
"""
import subprocess
import modal

GCP_PROJECT  = "gen-lang-client-0266464307"
MODAL_SECRET = "family-weather-secrets"

# Add GEMINI_API_KEY to this list when the key is ready
SECRET_NAMES = [
    "CWA_API_KEY",
    "MOENV_API_KEY",
    "ANTHROPIC_API_KEY",
    "GCS_BUCKET_NAME",
    "GCP_PROJECT_ID",
]

def pull_from_gcp(name: str) -> str | None:
    result = subprocess.run(
        ["gcloud", "secrets", "versions", "access", "latest",
         f"--secret={name}", f"--project={GCP_PROJECT}"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"  SKIP {name}: not found in GCP Secret Manager")
        return None
    return result.stdout.strip()

def main():
    secrets = {}
    for name in SECRET_NAMES:
        value = pull_from_gcp(name)
        if value:
            secrets[name] = value
            print(f"  OK   {name}")

    if not secrets:
        print("No secrets pulled. Check GCP project and secret names.")
        return

    modal.Secret.create(MODAL_SECRET, env_dict=secrets, overwrite=True)
    print(f"\nPushed {len(secrets)} secrets to Modal secret '{MODAL_SECRET}'")

if __name__ == "__main__":
    main()
```

Run it:

```powershell
python scripts/sync_secrets_to_modal.py
```

Expected output:
```
  OK   CWA_API_KEY
  OK   MOENV_API_KEY
  OK   ANTHROPIC_API_KEY
  OK   GCS_BUCKET_NAME
  OK   GCP_PROJECT_ID

Pushed 5 secrets to Modal secret 'family-weather-secrets'
```

**Check:** [modal.com](https://modal.com) → Secrets → `family-weather-secrets` exists with 5 keys.

### 4c. Deploy Modal pipeline

```powershell
modal deploy backend/modal_app.py
```

Modal prints endpoint URLs on completion:
```
https://icyswordrain--family-weather-refresh.modal.run
https://icyswordrain--family-weather-broadcast.modal.run
```

Save both URLs — needed in Steps 5 and 6.

**Check:**
```powershell
modal run backend/modal_app.py::health_check
```
Returns `{"status": "ok"}`.

---

## Step 5 — GitHub Actions

### 5a. Create a GCP service account for GitHub Actions

```powershell
gcloud iam service-accounts create github-actions-sa `
  --display-name="GitHub Actions Deployer"

gcloud projects add-iam-policy-binding gen-lang-client-0266464307 `
  --member="serviceAccount:github-actions-sa@gen-lang-client-0266464307.iam.gserviceaccount.com" `
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding gen-lang-client-0266464307 `
  --member="serviceAccount:github-actions-sa@gen-lang-client-0266464307.iam.gserviceaccount.com" `
  --role="roles/iam.serviceAccountUser"

gcloud iam service-accounts keys create github-actions-key.json `
  --iam-account=github-actions-sa@gen-lang-client-0266464307.iam.gserviceaccount.com
```

Open `github-actions-key.json`, copy the entire file contents.

### 5b. Add secrets to GitHub

Go to: `https://github.com/icyswordrain-hue/family-weather/settings/secrets/actions`

Add these repository secrets:

| Secret name | Value |
|---|---|
| `DOCKERHUB_USERNAME` | `icyswordrain` |
| `DOCKERHUB_TOKEN` | Create at hub.docker.com → Account Settings → Security → New Access Token |
| `GCP_SA_KEY` | Full contents of `github-actions-key.json` (the entire JSON) |
| `MODAL_REFRESH_URL` | URL from Step 4c |
| `MODAL_BROADCAST_URL` | URL from Step 4c |

Delete the key file after adding it to GitHub:

```powershell
Remove-Item github-actions-key.json
```

### 5c. Create the workflow file

Create `.github/workflows/deploy.yml` in your repo:

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

      - name: Log in to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}

      - name: Build and push image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: icyswordrain/family-weather:latest

      - name: Authenticate to GCP
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Deploy to Cloud Run
        uses: google-github-actions/deploy-cloudrun@v2
        with:
          service: family-weather
          region: asia-east1
          image: icyswordrain/family-weather:latest
          env_vars: |
            RUN_MODE=CLOUD
            MODAL_REFRESH_URL=${{ secrets.MODAL_REFRESH_URL }}
            MODAL_BROADCAST_URL=${{ secrets.MODAL_BROADCAST_URL }}
```

Commit and push this file to master. Do not push yet if Cloud Run doesn't exist — complete Step 6 first, then push.

---

## Step 6 — Initial Cloud Run Deploy (Manual, One-Time)

Replace the two Modal URLs with your actual URLs from Step 4c:

```powershell
gcloud run deploy family-weather `
  --image=icyswordrain/family-weather:latest `
  --region=asia-east1 `
  --platform=managed `
  --service-account=707581314081-compute@developer.gserviceaccount.com `
  --allow-unauthenticated `
  --min-instances=0 `
  --max-instances=2 `
  --memory=512Mi `
  --timeout=300 `
  --set-env-vars="RUN_MODE=CLOUD" `
  --set-env-vars="GCS_BUCKET_NAME=family-weather-dashboard" `
  --set-env-vars="GCP_PROJECT_ID=gen-lang-client-0266464307" `
  --set-env-vars="NARRATION_PROVIDER=CLAUDE" `
  --set-env-vars="MODAL_REFRESH_URL=https://icyswordrain--family-weather-refresh.modal.run" `
  --set-env-vars="MODAL_BROADCAST_URL=https://icyswordrain--family-weather-broadcast.modal.run" `
  --update-secrets="CWA_API_KEY=CWA_API_KEY:latest" `
  --update-secrets="MOENV_API_KEY=MOENV_API_KEY:latest" `
  --update-secrets="ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:latest"
```

Cloud Run prints your service URL:
```
Service URL: https://family-weather-xxxxxxxx-de.a.run.app
```

Save this — it's your dashboard address.

**Check:** Open `<SERVICE_URL>/api/health` in browser. Returns `{"status": "ok"}`.

Now push `.github/workflows/deploy.yml` to master. Go to `https://github.com/icyswordrain-hue/family-weather/actions` and confirm the workflow runs green end-to-end.

---

## Step 7 — Cloud Scheduler

Replace `<SERVICE_URL>` with your URL from Step 6:

```powershell
gcloud scheduler jobs create http weather-morning `
  --location=asia-east1 `
  --schedule="15 6 * * *" `
  --time-zone="Asia/Taipei" `
  --uri="<SERVICE_URL>/api/refresh" `
  --message-body='{"slot":"morning"}' `
  --headers="Content-Type=application/json"

gcloud scheduler jobs create http weather-midday `
  --location=asia-east1 `
  --schedule="15 11 * * *" `
  --time-zone="Asia/Taipei" `
  --uri="<SERVICE_URL>/api/refresh" `
  --message-body='{"slot":"midday"}' `
  --headers="Content-Type=application/json"

gcloud scheduler jobs create http weather-evening `
  --location=asia-east1 `
  --schedule="15 17 * * *" `
  --time-zone="Asia/Taipei" `
  --uri="<SERVICE_URL>/api/refresh" `
  --message-body='{"slot":"evening"}' `
  --headers="Content-Type=application/json"
```

Trigger the morning job immediately to test the full pipeline:

```powershell
gcloud scheduler jobs run weather-morning --location=asia-east1
```

Wait 60 seconds, open the dashboard URL. Today's morning broadcast should appear.

**Check:**
```powershell
gcloud logging read "resource.type=cloud_run_revision" --limit=20 `
  --format="table(timestamp,textPayload)"
```
No errors in the log output.

---

## Step 8 — Add Gemini Key When Ready

1. Add to GCP Secret Manager:
```powershell
echo "your-gemini-key" | gcloud secrets create GEMINI_API_KEY --data-file=-
```

2. Add `GEMINI_API_KEY` to the `SECRET_NAMES` list in `scripts/sync_secrets_to_modal.py`, then sync to Modal:
```powershell
python scripts/sync_secrets_to_modal.py
```

3. Add to Cloud Run:
```powershell
gcloud run services update family-weather `
  --region=asia-east1 `
  --update-secrets="GEMINI_API_KEY=GEMINI_API_KEY:latest"
```

---

## Final Checklist

- [ ] `<SERVICE_URL>/api/health` returns `{"status": "ok"}`
- [ ] Manual scheduler trigger produces a broadcast on the dashboard
- [ ] `gcloud storage ls gs://family-weather-dashboard/broadcasts/` shows today's date folder
- [ ] Clicking Play returns audio within 3 seconds
- [ ] Pushing a commit to master triggers GitHub Actions and redeploys Cloud Run automatically

---

## Troubleshooting

**Permission errors on gcloud commands**
```powershell
gcloud config get project
```
Must return `gen-lang-client-0266464307`. If not, run `gcloud config set project gen-lang-client-0266464307` and retry.

**Dashboard shows no broadcast data**
```powershell
gcloud storage ls gs://family-weather-dashboard/broadcasts/
```
If empty, check Modal logs: `modal logs family-weather-refresh`. Most common cause: a secret is missing from the Modal secret store — re-run `sync_secrets_to_modal.py`.

**Audio spinner never resolves**
Open browser devtools → Network → click Play → find the `/api/tts` request. If 500, check Cloud Run logs. Most common cause: GCS bucket public access not applied — re-run the `add-iam-policy-binding` command from Step 2.

**GitHub Actions fails on GCP auth step**
Confirm `GCP_SA_KEY` in GitHub secrets contains the full JSON including outer `{ }` braces. Recreate the key and re-paste if unsure.

**Modal deploy fails**
```powershell
modal logs family-weather-refresh
```
Most common cause: `family-weather-secrets` is missing a key the pipeline expects. Re-run `sync_secrets_to_modal.py`.

**Redeploying Modal after pipeline code changes**
```powershell
modal deploy backend/modal_app.py
```
Only needed when files under `backend/`, `data/`, or `narration/` change. Flask-only changes deploy automatically via GitHub Actions.
