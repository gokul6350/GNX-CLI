import httpx
import os
from dotenv import load_dotenv
import time
import jwt

def generate_token(apikey: str, exp_seconds: int):
    try:
        id, secret = apikey.split(".")
    except Exception as e:
        raise Exception("invalid apikey", e)

    payload = {
        "api_key": id,
        "exp": int(time.time()) + exp_seconds,
        "timestamp": int(time.time()),
    }

    return jwt.encode(
        payload,
        secret,
        algorithm="HS256",
        headers={"alg": "HS256", "sign_type": "SIGN"},
    )

def test_api_raw():
    load_dotenv()
    api_key = os.getenv("ZHIPUAI_API_KEY")
    if not api_key:
        print("No API Key")
        return

    url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    token = generate_token(api_key, 3600)
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messages": [{"role": "user", "content": "hi"}]
    }
    
    # Try several models
    models_to_try = ["glm-4.5", "glm-4.5-flash", "glm-4-flash", "glm-4-air", "glm-4"]
    
    for model in models_to_try:
        print(f"--- Trying {model} ---")
        payload["model"] = model
        try:
            response = httpx.post(url, headers=headers, json=payload, timeout=30)
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
        except Exception as e:
            print(f"Request failed: {e}")

if __name__ == "__main__":
    test_api_raw()
