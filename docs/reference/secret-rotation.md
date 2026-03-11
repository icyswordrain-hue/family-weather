# Secret Rotation Runbook

How to rotate any API key or credential in the cloud pipeline.

## Where secrets live

| Store | What it's for |
|-------|--------------|
| GCP Secret Manager | Source of truth for all secrets |
| Modal `family-weather-secrets` | Runtime secrets injected into Modal functions |
| `.env` (local) | Local development only — never committed |

Cloud Run itself only receives `RUN_MODE`, `MODAL_REFRESH_URL`, `MODAL_BROADCAST_URL`, and `MODAL_AUDIO_URL` (see `.github/workflows/deploy.yml`). It does not hold API keys.

## Rotation procedure

### 1. Update GCP Secret Manager

```bash
# Pipe the new value directly to avoid it landing in shell history
printf '%s' 'NEW_KEY_VALUE' | gcloud secrets versions add SECRET_NAME --data-file=-
```

Secrets managed here (see `scripts/sync_secrets_to_modal.py`):

| Secret name | Used by |
|-------------|---------|
| `CWA_API_KEY` | CWA weather API |
| `MOENV_API_KEY` | MOENV AQI API |
| `ANTHROPIC_API_KEY` | Claude narration |
| `GEMINI_API_KEY` | Gemini narration |
| `GCS_BUCKET_NAME` | GCS audio/history storage |
| `GCP_PROJECT_ID` | GCP project identifier |
| `GCP_SA_JSON` | GCS service account (base64-encoded) |
| `NARRATION_PROVIDER` | `CLAUDE` or `GEMINI` |

### 2. Sync to Modal

```bash
python scripts/sync_secrets_to_modal.py
```

This pulls the latest version of every secret from GCP and re-creates `family-weather-secrets` in Modal. No Modal redeploy needed — secrets are injected at invocation time.

### 3. Update local `.env`

Edit `.env` manually. The file is `.gitignore`d.

## Verification

After syncing, trigger a pipeline run and check for auth errors:

```bash
# Quick smoke test — calls the Modal refresh endpoint
curl -X POST "$MODAL_REFRESH_URL"
```

Or via the dashboard: open the app → System Log → confirm all fetch sources show `ok`.

For Gemini/Claude specifically, request a narration broadcast and confirm it generates without `401`/`403` errors in the Modal function logs.

## GitHub Actions secrets

`MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET` are stored as GitHub repository secrets and are used only during CI/CD deployment (not at runtime). Rotate via **Settings → Secrets and variables → Actions** in the GitHub repo.
