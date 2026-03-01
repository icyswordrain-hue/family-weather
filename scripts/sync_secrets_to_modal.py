import subprocess
import base64

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
    "GCP_SA_JSON",
    "NARRATION_PROVIDER",
]

# Secrets that contain multiline content (e.g. JSON) must be base64-encoded
# before being passed to Modal CLI's key=value format.
BASE64_ENCODE = {"GCP_SA_JSON"}

def pull_from_gcp(name: str):
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

    if not secrets:
        print("No secrets pulled. Check GCP project and secret names.")
        return

    # Base64-encode multiline secrets so they survive Modal CLI key=value format
    for name in BASE64_ENCODE:
        if name in secrets:
            secrets[name] = base64.b64encode(secrets[name].encode()).decode()
            print(f"  ENC  {name} (base64)")

    args = [MODAL_EXE, "secret", "create", MODAL_SECRET]
    for key, value in secrets.items():
        args.append(f"{key}={value}")
    args.append("--force")

    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"\nPushed {len(secrets)} secrets to Modal secret '{MODAL_SECRET}'")
    else:
        print(f"\nFailed to push to Modal:\n{result.stderr}")

if __name__ == "__main__":
    main()
