import os
import litellm
from litellm import completion
from dotenv import load_dotenv

# Load env variables
print(f"Current Working Directory: {os.getcwd()}")
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
print(f"Loading .env from: {os.path.abspath(dotenv_path)}")
load_dotenv(dotenv_path=dotenv_path, override=True)

api_key = os.getenv("OPENROUTER_API_KEY")
model_name = os.getenv("MODEL_NAME", "openrouter/mistralai/devstral-2512:free")

print(f"API Key found: {'Yes' if api_key else 'No'}")
if api_key:
    print(f"API Key length: {len(api_key)}")
    print(f"API Key prefix: {api_key[:10]}...")

print(f"Model: {model_name}")

try:
    print("Attempting simple completion...")
    response = completion(
        model=model_name,
        messages=[{"role": "user", "content": "Hello"}],
        api_key=api_key
    )
    print("Success!")
    print(response.choices[0].message.content)
except Exception as e:
    print(f"Error: {e}")