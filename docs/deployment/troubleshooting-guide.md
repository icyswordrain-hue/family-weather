# Family Weather Dashboard — Troubleshooting, Glossary & FAQ
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

## Glossary

**Cloud Run** — Google's managed container platform. Hosts the Flask web server that serves the dashboard and proxies pipeline requests to Modal. Scales to zero when idle — a cold start takes 1–3 seconds. Receives HTTP from the browser and Cloud Scheduler.

**Modal** — Serverless Python compute platform. Runs the heavy pipeline work: CWA/MOENV data fetch, Claude narration, TTS caching. Triggered by Cloud Run via HTTP POST. Billed only while executing — idle time is free. Deployed separately from Cloud Run.

**Docker** — Packages the Flask app and all its Python dependencies into a portable container image. Cloud Run pulls this image to run the web server. GitHub Actions builds and pushes a new image on every push to master.

**Artifact Registry** — Google's private Docker image registry, hosted in `asia-east1`. Cloud Run pulls the Docker image from here. Must be in the same region as Cloud Run. Cloud Run cannot pull from Docker Hub in this region.

**GCS (Google Cloud Storage)** — Object storage. Stores broadcast JSON files, TTS audio cache, and meal/location regen data. The bucket `family-weather-dashboard` is public — the browser fetches audio directly without going through Flask.

**Cloud Scheduler** — GCP's cron service. Fires HTTP POST requests to Cloud Run at 06:15, 11:15, and 17:15 CST daily. Each request body contains `{"slot": "morning|midday|evening"}`.

**GitHub Actions** — CI/CD pipeline defined in `.github/workflows/deploy.yml`. Triggered on every push to `master`. Builds the Docker image, pushes to Artifact Registry, deploys Cloud Run, deploys Modal. The workflow run name comes from the git commit message — cosmetic only.

**Secret Manager** — GCP service storing API keys as versioned named secrets. Cloud Run reads secrets at runtime via `--update-secrets`. Modal has its own separate secret store synced via `scripts/sync_secrets_to_modal.py`.

**Gunicorn** — Python WSGI server that runs Flask inside the Docker container on port 8080. Two worker processes. Logs show `Booting worker with pid` on each container start.

**`RUN_MODE`** — Environment variable controlling pipeline behaviour. `CLOUD` = Flask proxies all pipeline work to Modal. `LOCAL` = Flask runs the pipeline in-process (development only).

**`slot`** — The time-of-day parameter passed by Cloud Scheduler: `morning`, `midday`, or `evening`. Controls which CWA observation window the pipeline targets and whether midday skip logic applies.

**`family-weather-engine`** — The name of the Modal app. Contains three web endpoints: `health`, `refresh`, and `broadcast`.

**`cloud-run-source-deploy`** — An Artifact Registry repository auto-created by GCP for source-based deployments. Not used by this project — ignore it.

---

## Pipeline Flow (for debugging)

When something breaks, identify which stage failed:

```
Cloud Scheduler fires
    └─ [1] Did Cloud Run receive the request?
           Check: gcloud logging read ... --limit=50

    └─ [2] Did Cloud Run forward to Modal?
           Check: Cloud Run logs for "Forwarding to Modal" or HTTP 5xx

    └─ [3] Did Modal fetch CWA/MOENV data?
           Check: modal logs family-weather-engine

    └─ [4] Did Claude narrate successfully?
           Check: modal logs — look for "narration_source: claude"

    └─ [5] Did broadcast write to GCS?
           Check: gcloud storage ls gs://family-weather-dashboard/broadcasts/

    └─ [6] Did the browser receive the broadcast?
           Check: curl https://family-weather-707581314081.asia-east1.run.app/api/broadcast
```

---

## Checking Logs

**Cloud Run logs:**
```
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=family-weather" --limit=50 --format="table(timestamp,textPayload)"
```

**Modal logs:**
```
modal logs family-weather-engine
```

**Cloud Scheduler last run status:**
```
gcloud scheduler jobs describe weather-morning --location=asia-east1
```
Check `lastAttemptTime` and `status`. An empty `status: {}` means the job fired and Cloud Run returned 200.

**GCS broadcast files:**
```
gcloud storage ls gs://family-weather-dashboard/broadcasts/
```

**Manually trigger a run:**
```
gcloud scheduler jobs run weather-morning --location=asia-east1
```

---

## FAQ — Errors Encountered

---

### GCP / gcloud

**`ERROR: NOT_FOUND: Unknown service account` or unexpected permission errors**

The active gcloud project is wrong. This is common because Google AI Studio auto-creates projects with the `gen-lang-client-` prefix and the CLI may default to a different one.

Fix:
```
gcloud config set project gen-lang-client-0266464307
```

---

**`The requested bucket name is not available`**

GCS bucket names are globally unique across all GCP accounts. If `family-weather-dashboard` is taken, verify you own it:
```
gcloud storage buckets describe gs://family-weather-dashboard
```
If it returns details, you own it and can use it. If it returns 403, the name is taken by another account — choose a new name and update `GCS_BUCKET_NAME` in Secret Manager, Modal secrets, and Cloud Run env vars.

---

**`denied: Permission 'artifactregistry.repositories.uploadArtifacts' denied`**

The GitHub Actions service account lacks Artifact Registry write permission. Fix:
```
gcloud artifacts repositories add-iam-policy-binding family-weather --location=asia-east1 --member="serviceAccount:github-actions-sa@gen-lang-client-0266464307.iam.gserviceaccount.com" --role="roles/artifactregistry.writer"
```
Then re-run the failed GitHub Actions workflow.

---

**`Image 'mirror.gcr.io/icyswordrain/family-weather:latest' not found`**

Cloud Run in `asia-east1` cannot pull from Docker Hub. Images must be in Artifact Registry. Always use:
```
asia-east1-docker.pkg.dev/gen-lang-client-0266464307/family-weather/app:latest
```
Update this path in `deploy.yml` and in any manual `gcloud run deploy` command.

---

**Duplicate Cloud Scheduler jobs**

Running the create commands twice creates duplicate jobs. The old job names from a previous session were `morning-refresh`, `midday-refresh`, `evening-refresh`. Delete them:
```
gcloud scheduler jobs delete morning-refresh --location=asia-east1
gcloud scheduler jobs delete midday-refresh --location=asia-east1
gcloud scheduler jobs delete evening-refresh --location=asia-east1
```
Keep only the three `weather-*` named jobs.

---

### Docker / Artifact Registry

**Why not Docker Hub?**

Cloud Run in `asia-east1` cannot reliably pull from Docker Hub (`mirror.gcr.io`). The region matters — Artifact Registry must be in the same region as Cloud Run. If you ever change the Cloud Run region, you must create a new Artifact Registry repo in the new region and update all image paths.

**If you change region, update these:**
- `asia-east1` in `.github/workflows/deploy.yml` (two places)
- `--location=asia-east1` in `gcloud artifacts` commands
- `--region=asia-east1` in `gcloud run deploy`

---

### Modal

**`AttributeError: module 'modal' has no attribute 'Mount'`**

Modal v1.x removed `modal.Mount`. Replace:
```python
# Old (broken)
mounts=[modal.Mount.from_local_dir(".", remote_path="/app")]

# New (correct)
image = modal.Image.debian_slim().add_local_dir(".", remote_path="/app")
```

---

**`Web endpoint Functions require FastAPI to be installed`**

Modal v1.x requires FastAPI explicitly in the image definition. Add before other pip installs:
```python
image = (
    modal.Image.debian_slim()
    .pip_install("fastapi[standard]")
    .pip_install_from_requirements("requirements.txt")
    .add_local_dir(".", remote_path="/app")
)
```

---

**`AttributeError: type object 'Secret' has no attribute 'create'`**

Modal SDK removed programmatic `Secret.create()`. Use the CLI via subprocess instead. See `scripts/sync_secrets_to_modal.py`.

---

**`FileNotFoundError: modal` in Python subprocess on Windows**

Modal installs as `modal.exe` on Windows and subprocess cannot find it without the full path. Find it:
```
where.exe modal
```
Hardcode the full path in scripts:
```python
MODAL_EXE = r"C:\Users\User\AppData\Local\Programs\Python\Python313\Scripts\modal.exe"
```

---

### GitHub Actions

**`GH013: Repository rule violations — Push cannot contain secrets`**

A service account JSON key file was accidentally committed to git. GitHub's secret scanning blocked the push. Fix in order:

1. Delete the compromised key in GCP:
```
gcloud iam service-accounts keys delete <KEY_ID> --iam-account=github-actions-sa@gen-lang-client-0266464307.iam.gserviceaccount.com
```
The `KEY_ID` appears in the error output from GitHub.

2. Create a new key:
```
gcloud iam service-accounts keys create github-actions-key.json --iam-account=github-actions-sa@gen-lang-client-0266464307.iam.gserviceaccount.com
```

3. Copy contents, update `GCP_SA_KEY` in GitHub secrets, delete the file immediately:
```
Remove-Item github-actions-key.json
```

4. Remove the file from git history:
```
git filter-branch --force --index-filter "git rm --cached --ignore-unmatch github-actions-key.json" --prune-empty --tag-name-filter cat -- --all
```

5. Force push the cleaned history:
```
git push origin <branch> --force
```

6. Add to `.gitignore` permanently — never commit key files.

---

**`remote rejected — push declined due to repository rule violations`**

Branch protection rule on master blocks direct pushes. Two options:

Option A — disable the rule at `https://github.com/icyswordrain-hue/family-weather/settings/rules`

Option B — push to a feature branch and merge:
```
git checkout -b my-branch
git push origin my-branch
```
Then open a pull request on GitHub and merge to master.

---

**Push went to wrong branch — master not updating**

Check with:
```
git log --oneline -3
```
If commits are on a feature branch instead of master:
```
git checkout master
git merge <branch-name>
git push origin master
```

---

**Workflow run name is confusing ("test github actions")**

GitHub Actions names workflow runs after the git commit message that triggered them. The name is purely cosmetic — a run named "test github actions" is a full production deployment. Write descriptive commit messages so you can audit deploys at a glance.

---

**Workflow shows only one run after updating the workflow file**

Each push to master creates one run. If you pushed the workflow update to a feature branch instead of master, it won't appear. Merge to master to trigger a new run.

---

### gcloud on Windows

**`FileNotFoundError: gcloud` in Python subprocess**

`gcloud` on Windows is a `.cmd` file and subprocess cannot find it without the extension. Use `gcloud.cmd` in all subprocess calls:

```python
subprocess.run(["gcloud.cmd", "secrets", "versions", "access", ...])
```

---

### Narration / Pipeline

**`ClientError: 404 NOT_FOUND — models/gemini-1.5-pro-latest`**

Gemini model names are stale. Update `config.py`:
```python
GEMINI_PRO_MODEL   = os.getenv("GEMINI_PRO_MODEL",   "gemini-2.0-pro-exp")
GEMINI_FLASH_MODEL = os.getenv("GEMINI_FLASH_MODEL",  "gemini-2.0-flash")
```

---

**`httpx.ReadTimeout` on Gemini calls**

Gemini API timed out. The pipeline falls back to Claude automatically if `NARRATION_PROVIDER=CLAUDE` is set. If Claude is the primary provider, Gemini is only reached if Claude itself fails — Gemini timeouts in that context are logged but non-fatal as long as the template fallback works.

---

**`AttributeError: 'NoneType' object has no attribute 'get'` in fallback_narrator.py line 265**

A forecast segment is `None` where the code expects a dict. Add a None guard in `narration/fallback_narrator.py`:
```python
# Before
"likely" in (seg.get("precip_text") or "").lower()

# After
"likely" in (seg.get("precip_text") or "").lower() if seg else False
```

---

## Syncing Secrets (reference)

File: `scripts/sync_secrets_to_modal.py`

Run after rotating any API key. Pulls from GCP Secret Manager, pushes to Modal.

```python
import subprocess

GCP_PROJECT  = "gen-lang-client-0266464307"
MODAL_SECRET = "family-weather-secrets"
MODAL_EXE    = r"C:\Users\User\AppData\Local\Programs\Python\Python313\Scripts\modal.exe"

SECRET_NAMES = [
    "CWA_API_KEY",
    "MOENV_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "GCS_BUCKET_NAME",
    "GCP_PROJECT_ID",
]

def pull_from_gcp(name):
    result = subprocess.run(
        ["gcloud.cmd", "secrets", "versions", "access", "latest",
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

    args = [MODAL_EXE, "secret", "create", MODAL_SECRET]
    for key, value in secrets.items():
        args.append(f"{key}={value}")
    args.append("--force")

    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"\nPushed {len(secrets)} secrets to Modal secret '{MODAL_SECRET}'")
    else:
        print(f"\nFailed:\n{result.stderr}")

if __name__ == "__main__":
    main()
```

Run:
```
python scripts/sync_secrets_to_modal.py
```

---

## Incident Log — 2026-03-01: Cloud deployment loop + empty dashboard tiles

### Symptoms observed
- Cloud Run Gunicorn workers dying with `CRITICAL WORKER TIMEOUT` on every scheduled refresh
- Dashboard gauge tiles showing `--` (empty) despite system log reporting "Data received successfully"
- Claude narration falling back to template output
- Cloud Scheduler retrying, triggering multiple concurrent Modal pipeline runs

### Root causes found and fixed (commits `4db410f`, `d256547`)

#### 1. No timeout on `requests.post()` to Modal — `app.py`
`requests.post(modal_url, ..., stream=True)` had no `timeout=` kwarg. If Modal was slow
to cold-start or the pipeline was long, Cloud Run held the connection open indefinitely.
Gunicorn killed the worker at 300s → Cloud Run returned 503 to Cloud Scheduler →
Cloud Scheduler retried → new Modal run started while old one was still running → loop.

**Fix:** Added `timeout=290` (just under Gunicorn's 300s limit).

#### 2. NDJSON newline stripping in the Cloud Run → Modal stream proxy — `app.py`
`resp.iter_lines()` strips `\n` delimiters before yielding each line to Flask's `Response`.
The browser's JS stream reader splits on `\n` (`buffer.split('\n')`), so without newlines
it never found a split. Every NDJSON line — including the final `{"type":"result",...}`
payload — accumulated in `buffer` unparsed. `gotResult` was always `false`, so the
fallback `GET /api/broadcast` always fired instead of using the stream result. If Modal
had no broadcast cached yet, that fallback returned 404 and tiles stayed empty.

**Fix:** Replaced `resp.iter_lines()` with `resp.iter_content(chunk_size=None)`, which
passes raw bytes through unchanged, preserving newlines.

#### 3. `slot` and `lang` not forwarded to Modal — `app.py` + `modal_app.py`
Cloud Run's proxy sent `{"date", "provider", "lang"}` but omitted `slot`. Modal's
`refresh` endpoint defaulted to `slot="midday"` and `lang="en"` for every run,
regardless of whether it was a morning or evening scheduled job.

**Fix:** Added `"slot": slot` to the proxy JSON body; Modal now reads and forwards both
`slot` and `lang` to `_pipeline_steps`.

#### 4. `RUN_MODE` defaults to `"CLOUD"` inside Modal containers — `config.py` + `modal_app.py`
`config.py` defaults `RUN_MODE` to `"CLOUD"` when the env var is absent. Modal's secret
`family-weather-secrets` only contains API keys, not `RUN_MODE`. So Modal ran with
`RUN_MODE="CLOUD"`, causing `LOCAL_DATA_DIR` to resolve to `local_data` (ephemeral
container path) instead of `/data` (the persistent Modal Volume).

**Fix:** `os.environ.setdefault("RUN_MODE", "MODAL")` added to `modal_app.py:refresh`
before importing `app`, ensuring the first `config.py` import sees the correct value.

#### 5. `modal deploy` step had no timeout in GitHub Actions — `.github/workflows/deploy.yml`
If Modal's platform was slow or auth failed silently, the workflow step would hang for
up to GitHub Actions' 6-hour default, making the deployment appear "stuck".

**Fix:** Added `timeout-minutes: 10` to the "Deploy Modal pipeline" step.

#### 6. Claude narration timeout too short — `config.py`
`NARRATION_TIMEOUT_PRO` was **60s** and `NARRATION_TIMEOUT_FLASH` was **30s**. Claude
Sonnet routinely needs more than 60s to write a full multi-paragraph weather narration,
so it was timing out on every run and falling back to template output.

**Fix:** Raised `NARRATION_TIMEOUT_PRO` to **240s** and `NARRATION_TIMEOUT_FLASH` to
**90s** — both well within Modal's 300s function timeout.

### Files changed
| File | Change |
|---|---|
| `app.py` | `timeout=290` + `iter_content(chunk_size=None)` + `"slot": slot` in proxy |
| `backend/modal_app.py` | `os.environ.setdefault("RUN_MODE","MODAL")`; read + forward `lang`, `slot` |
| `config.py` | `NARRATION_TIMEOUT_PRO` 60→240, `NARRATION_TIMEOUT_FLASH` 30→90 |
| `.github/workflows/deploy.yml` | `timeout-minutes: 10` on Modal deploy step |

---

## Code Cleanup — 2026-03-01: Removed dead `load_broadcast()` function

### Background

`history/conversation.py` contained two functions for reading broadcast data:

- `get_today_broadcast(date_str)` — reads from `history/conversation.json` (the file `save_day()` actually writes)
- `load_broadcast(date, slot)` — reads from `broadcasts/{date}/{slot}.json` (a path that was **never written** by the pipeline)

Both `app.py` and `backend/modal_app.py` already called `get_today_broadcast()` correctly, so `load_broadcast()` was unreachable dead code. It was misleading because it implied a second GCS storage layout that doesn't exist.

### Fix

Removed `load_broadcast()` and the unused `TIMEZONE` config import from `history/conversation.py`.

### Files changed
| File | Change |
|---|---|
| `history/conversation.py` | Removed `load_broadcast()` (16 lines) and unused `TIMEZONE` import |
