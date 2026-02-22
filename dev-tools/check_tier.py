import os
import anthropic
import time
from dotenv import load_dotenv

load_dotenv()

key = os.environ.get("ANTHROPIC_API_KEY")
client = anthropic.Anthropic(api_key=key)

print(f"Checking access for key: {key[:15]}...")
print("If you just added credits, it might take a few minutes.\n")

models = [
    "claude-3-5-sonnet-latest",
    "claude-3-5-sonnet-20241022",
    "claude-3-opus-latest"
]

for model in models:
    print(f"Testing {model}...", end=" ")
    try:
        client.messages.create(
            model=model,
            max_tokens=10,
            messages=[{"role": "user", "content": "hi"}]
        )
        print("[OK] SUCCESS! Tier 1 Unlocked.")
        # If successful, we can stop
        break
    except anthropic.NotFoundError:
        print("[FAIL] 404 Not Found (Still Tier 0 / Restricted)")
    except Exception as e:
        print(f"[ERR] Error: {e}")

print("\n--- Troubleshooting Tips ---")
print("1. Did you verify your phone number? (Required for Tier 1)")
print("2. Did you generate a NEW key after depositing? (Try that)")
print("3. Are you in the right 'Project' on the console?")
