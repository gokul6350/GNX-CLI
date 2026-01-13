import requests
import base64
import json
import os
import time
from PIL import Image
import io
import datetime
import sys

# Add parent directory to path to import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

# Configuration
# Ensure URL ends with /chat/completions for direct requests usage if it's just the base
base_url = "https://qwen3vl-2b-it-nexa.90xdev.dev"#config.VL_BASE_URL
if not base_url.endswith("/chat/completions"):
    if base_url.endswith("/v1"):
        API_BASE_URL = f"{base_url}/chat/completions"
    else:
        API_BASE_URL = f"{base_url}/v1/chat/completions"
else:
    API_BASE_URL = base_url

IMAGE_PATH = r"C:\Users\BARATH\Documents\CODING\GNX CLI\mobile_screenshot.png"
API_KEY = config.VL_API_KEY

def log_step(step_name, start_time=None):
    current_time = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    if start_time:
        duration = time.time() - start_time
        print(f"[{current_time}] [COMPLETED] {step_name} (Took: {duration:.4f}s)")
    else:
        print(f"[{current_time}] [STARTED] {step_name}")
    return time.time()

def encode_image(image_path):
    step_start = log_step("Image Processing & Encoding")
    
    # Resize image to ensure faster processing
    with Image.open(image_path) as img:
        log_step(f"Opened image (Size: {img.size})")
        
        # Resize if larger than 512 on longest side
        max_size = 512
        if max(img.size) > max_size:
            resize_start = time.time()
            ratio = max_size / max(img.size)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            log_step(f"Resized image to {new_size}", resize_start)
        
        save_start = time.time()
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        encoded = base64.b64encode(buffered.getvalue()).decode('utf-8')
        log_step("Image encoding to Base64", save_start)
        
        log_step("Image Processing & Encoding", step_start)
        return encoded

def describe_image():
    total_start = log_step("Full Process")
    
    if not os.path.exists(IMAGE_PATH):
        print(f"Error: Image not found at {IMAGE_PATH}")
        return

    # Encode image
    base64_image = encode_image(IMAGE_PATH)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    payload = {
        "model": config.VL_MODEL, # Or whatever model name the server expects
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "describe this img"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 300
    }

    # DEBUG: Save request payload to file
    try:
        with open("last_rough_request.json", "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"DEBUG: Request payload saved to last_rough_request.json")
    except Exception as e:
        print(f"DEBUG: Failed to save request payload: {e}")

    try:
        log_step(f"Sending request to {API_BASE_URL}")
        req_start = time.time()
        response = requests.post(API_BASE_URL, headers=headers, json=payload)
        log_step("API Request", req_start)
        
        response.raise_for_status()
        
        parse_start = time.time()
        result = response.json()
        log_step("Response Parsing", parse_start)
        
        print("\nResponse:")
        print(json.dumps(result, indent=2))
        
        if 'choices' in result and len(result['choices']) > 0:
            print("\nDescription:")
            print(result['choices'][0]['message']['content'])
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Status Code: {e.response.status_code}")
            # Check if response is HTML (Cloudflare error)
            if "text/html" in e.response.headers.get('Content-Type', ''):
                print("Response is HTML (likely a server/proxy error page).")
                if "<title>" in e.response.text:
                    start = e.response.text.find("<title>") + 7
                    end = e.response.text.find("</title>")
                    print(f"Page Title: {e.response.text[start:end]}")
            else:
                print(f"Response Text: {e.response.text}")
    
    log_step("Full Process", total_start)

if __name__ == "__main__":
    describe_image()
