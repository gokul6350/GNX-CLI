import httpx
import os
from dotenv import load_dotenv

def list_vl_models():
    # Since config.py uses custom provider
    url = "https://qwen3vl-2b-it-nexa.90xdev.dev/v1/models"
    
    print(f"Requesting models from {url}...")
    try:
        response = httpx.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Accessible Models:")
            models = response.json()
            print(models)
        else:
            print(f"Failed to get models: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_vl_models()
