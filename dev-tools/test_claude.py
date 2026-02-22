import logging
import sys
import os
from dotenv import load_dotenv
import anthropic

# Setup logging to see what's happening
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()
api_key = os.environ.get("ANTHROPIC_API_KEY")

if not api_key:
    print("ERROR: ANTHROPIC_API_KEY not found in environment.")
    sys.exit(1)

print(f"Using API Key: {api_key[:10]}...")

client = anthropic.Anthropic(api_key=api_key)

# Test with a valid model first
model = "claude-3-haiku-20240307"
print(f"Testing connectivity with {model}...")

try:
    message = client.messages.create(
        model=model,
        max_tokens=10,
        messages=[{"role": "user", "content": "Hello"}]
    )
    print("SUCCESS: Haiku connection works.")
    print(f"Response: {message.content[0].text}")
except Exception as e:
    print(f"FAILURE with Haiku: {e}")

# Test with the configured SONNET model
sonnet_model = os.environ.get("CLAUDE_MODEL", "claude-4-6-sonnet-latest")
print(f"Testing connectivity with configured model: {sonnet_model}...")

try:
    message = client.messages.create(
        model=sonnet_model,
        max_tokens=10,
        messages=[{"role": "user", "content": "Hello"}]
    )
    print("SUCCESS: Configured model works.")
except Exception as e:
    print(f"FAILURE with configured model: {e}")
