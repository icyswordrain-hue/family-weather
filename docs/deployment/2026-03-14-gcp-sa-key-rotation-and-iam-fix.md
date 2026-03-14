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

## Lessons Learned

- The previous working setup used a different SA (`github-actions-sa`). When secrets were rotated to `family-weather-sa`, the IAM roles did not carry over.
- `artifactregistry.attachmentWriter` is not `artifactregistry.writer` — the former only handles OCI attachments, not image uploads.
- Always verify both the key validity AND the SA's IAM roles when rotating service account keys.
