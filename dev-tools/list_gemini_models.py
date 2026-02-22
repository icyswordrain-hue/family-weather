from google import genai
from config import GEMINI_API_KEY

def list_models():
    client = genai.Client(api_key=GEMINI_API_KEY)
    print("Available Gemini Models:")
    try:
        for m in client.models.list():
            print(f"- {m.name}")
    except Exception as e:
        print(f"Failed to list models: {e}")

if __name__ == "__main__":
    list_models()
