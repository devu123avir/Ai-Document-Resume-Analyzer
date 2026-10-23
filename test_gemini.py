
import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai

# Load API key from this project's .env file
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("ERROR: GEMINI_API_KEY .env file mein nahi mili.")
else:
    try:
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents="Explain Python in two simple sentences."
        )

        print("\nSUCCESS: Gemini AI is working!")
        print("\nAI Response:")
        print(response.text)

    except Exception as e:
        print("\nGemini API test failed.")
        print("Error:", e)

