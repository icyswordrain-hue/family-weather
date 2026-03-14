# GCP Service Account Key Rotation & IAM Fix
_2026-03-14_

---

## Problem

Deployments #206–#212 all failed within 7–12 seconds. The GitHub Actions workflow (`deploy.yml`) could not get past the "Authenticate to GCP" step.

---

## Root Causes

### 1. Invalid Service Account Key

The `GCP_SA_KEY` GitHub secret contained a service account JSON whose RSA private key was invalid. The `google-github-actions/auth@v2` action parsed the JSON successfully but the underlying key material was corrupt, causing:

```
ValueError('Invalid private key')
```

This surfaced as `error getting credentials` during `docker push` to Artifact Registry.

**Fix:** Generated a fresh key for `family-weather-sa@gen-lang-client-0266464307.iam.gserviceaccount.com` via the GCP Console (IAM → Service Accounts → Keys → Create new key → JSON) and updated the `GCP_SA_KEY` GitHub secret using `gh secret set`.

### 2. Missing IAM Roles

The new service account key belonged to `family-weather-sa`, but this SA only had limited roles (`speech.client`, `pubsub.publisher`, `iam.serviceAccountTokenCreator`, `artifactregistry.attachmentWriter`). It was missing the roles needed for the CI/CD pipeline.

**Roles granted:**

| Role | Purpose |
|------|---------|
| `roles/artifactregistry.writer` | Push Docker images to Artifact Registry |
| `roles/run.admin` | Deploy revisions to Cloud Run |
| `roles/iam.serviceAccountUser` | Act as the Cloud Run service account during deployment |

Commands used:
```bash
gcloud projects add-iam-policy-binding gen-lang-client-0266464307 \
  --member="serviceAccount:family-weather-sa@gen-lang-client-0266464307.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding gen-lang-client-0266464307 \
  --member="serviceAccount:family-weather-sa@gen-lang-client-0266464307.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding gen-lang-client-0266464307 \
  --member="serviceAccount:family-weather-sa@gen-lang-client-0266464307.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"
```

### 3. Docker Buildx Credential Isolation

`docker/build-push-action@v5` uses a buildx `docker-container` driver by default, which runs in an isolated container that cannot see the gcloud credential helper configured by `gcloud auth configure-docker`.

**Fix:** Added `docker/setup-buildx-action@v3` with `driver: docker` to force buildx to use the default Docker daemon, which inherits the gcloud credential helper configuration.

```yaml
- name: Set up Docker Buildx
  uses: docker/setup-buildx-action@v3
  with:
    driver: docker
```

---

## Timeline

| Deploy # | Commit | Failure Point | Error |
|----------|--------|---------------|-------|
| #204 | 2ac95d0 | — | Last successful deploy (used old `github-actions-sa` key) |
| #206–#212 | b545d86–a002689 | Authenticate to GCP | Invalid/missing `GCP_SA_KEY` secret |
| #213 (rerun) | ae40571 | Build and push image | `ValueError('Invalid private key')` |
| #214 (rerun) | ae40571 | Build and push image | `Permission 'artifactregistry.repositories.uploadArtifacts' denied` |
| #215 (rerun) | ae40571 | — | All steps passed |

---

## IAM Hardening (same day, later session)

Audited all project IAM bindings against actual GCP service usage and revoked everything unnecessary.

**Services confirmed in use:** Artifact Registry, Cloud Run, GCS, Cloud TTS, Secret Manager.
**Services NOT in use:** Pub/Sub, Vertex AI.

### Changes made

**Default Compute SA** (`707581314081-compute@developer.gserviceaccount.com`):

| Action | Role | Reason |
|---|---|---|
| Revoked | `roles/editor` | 11,073 excess permissions — replaced with targeted roles |
| Revoked | `roles/artifactregistry.writer` | Runtime only pulls images, never pushes |
| Revoked | `roles/run.admin` | Service doesn't manage itself |
| Added | `roles/storage.objectAdmin` | GCS access for audio, history, regen data |

**Family Weather SA** (`family-weather-sa@...`):

| Action | Role | Reason |
|---|---|---|
| Revoked | `roles/artifactregistry.attachmentWriter` | Not needed |
| Revoked | `roles/artifactregistry.writer` | CI/CD moved back to `github-actions-sa` |
| Revoked | `roles/run.admin` | CI/CD moved back to `github-actions-sa` |
| Revoked | `roles/pubsub.publisher` | No Pub/Sub usage in codebase |
| Revoked | `roles/iam.serviceAccountTokenCreator` | No signed URLs or token delegation |
| Added | `roles/storage.objectAdmin` | GCS access for audio, history, regen data |

**GitHub Actions SA** (`github-actions-sa@...`):

| Action | Role | Reason |
|---|---|---|
| Added | `roles/artifactregistry.writer` | Needed to push Docker images |

**Vertex AI Express SA** (`vertex-express@...`): Deleted entirely — project uses Gemini via API key, not Vertex AI.

### GCP_SA_KEY rotated back to github-actions-sa

The March 14 morning session had rotated `GCP_SA_KEY` to `family-weather-sa`. After revoking CI/CD roles from that SA, we generated a fresh key for `github-actions-sa` and updated the GitHub secret. This restores the intended separation: `github-actions-sa` for CI/CD, `family-weather-sa` for runtime.

### Final IAM state

| Service Account | Roles |
|---|---|
| `707581314081-compute` (default) | AR Reader, Logs Writer, Secret Manager Secret Accessor, Storage Object Admin, SA User |
| `family-weather-sa` | Cloud Speech Client, Storage Object Admin, SA User |
| `github-actions-sa` | AR Writer, Cloud Run Admin, SA User |

---

## Lessons Learned

- The previous working setup used a different SA (`github-actions-sa`). When secrets were rotated to `family-weather-sa`, the IAM roles did not carry over.
- `artifactregistry.attachmentWriter` is not `artifactregistry.writer` — the former only handles OCI attachments, not image uploads.
- Always verify both the key validity AND the SA's IAM roles when rotating service account keys.
- The `Editor` primitive role grants ~11,000 permissions. Replace it with the 3–5 specific roles you actually need.
- Keep CI/CD and runtime service accounts separate — mixing them leads to overprivileged SAs.
