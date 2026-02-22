import os
from google import genai
from config import GEMINI_API_KEY, GEMINI_PRO_MODEL, GEMINI_FLASH_MODEL

def test_gemini():
    print(f"Testing Gemini API Key: {GEMINI_API_KEY[:5]}...{GEMINI_API_KEY[-5:] if len(GEMINI_API_KEY) > 10 else ''}")
    print(f"Primary Model: {GEMINI_PRO_MODEL}")
    print(f"Flash Model: {GEMINI_FLASH_MODEL}")
    
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        # Test with the flash model first as it's faster
        response = client.models.generate_content(
            model=GEMINI_FLASH_MODEL,
            contents="Hello, say 'API connection successful' if you can read this."
        )
        print(f"Success! Response: {response.text}")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    test_gemini()
