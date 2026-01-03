#!/usr/bin/env python3
"""
Simple vision tool to describe desktop screenshot using Gemini.
Uses Google GenAI SDK for accurate token counting.
"""

import base64
import io
import os
from pathlib import Path
from dotenv import load_dotenv
from mss import mss
from PIL import Image
from google import genai

# Load environment
load_dotenv()


def capture_screenshot_512() -> str:
    """Capture desktop screenshot, downscale to 512x512, return as base64 data URL."""
    with mss() as sct:
        # Capture primary monitor
        mon = sct.monitors[0]
        shot = sct.grab(mon)
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        
        # Downscale to 512x512
        img.thumbnail((512, 512), Image.LANCZOS)
        
        # Save to file for reference
        path = Path(os.getcwd()) / "desktop_screenshot_vision.png"
        img.save(path)
        print(f"✓ Screenshot saved: {path}")
        
        # Encode to base64
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        data_url = f"data:image/png;base64,{b64}"
        
        return data_url


def describe_screen():
    """Send screenshot to Gemini and get description with accurate token counting."""
    print("\n📸 Capturing screenshot...")
    # Capture and save screenshot
    with mss() as sct:
        mon = sct.monitors[0]
        shot = sct.grab(mon)
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        
        # Downscale to 512x512
        img.thumbnail((512, 512), Image.LANCZOS)
        
        # Save to file
        path = Path(os.getcwd()) / "desktop_screenshot_vision.png"
        img.save(path)
        print(f"✓ Screenshot saved: {path}")
    
    print("🧠 Sending to Gemini for analysis...")
    
    # Initialize Google GenAI client
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    
    # Upload image file to Google's servers
    print("📤 Uploading image to Google...")
    uploaded_file = client.files.upload(file=path)
    print(f"✓ Image uploaded: {uploaded_file.uri}")
    
    # Prepare prompt and image for token counting
    prompt = "Describe what you see on this screen in 2-3 sentences. Be factual and direct."
    contents = [prompt, uploaded_file]
    
    # Count tokens BEFORE generation
    print("\n📊 Counting tokens...")
    print(f"  Method: Files API (image uploaded separately)")
    token_count = client.models.count_tokens(
        model="gemma-3-27b-it",
        contents=contents
    )
    print(f"  Estimated tokens: {token_count.total_tokens:,}")
    print(f"  ⚠️  Note: Files API counts file reference (~178 tokens)")
    print(f"      Actual image processing tokens may be separate/hidden")
    
    # Generate response
    print("\n🤖 Generating response...")
    response = client.models.generate_content(
        model="gemma-3-27b-it",
        contents=contents
    )
    
    # Show actual token usage
    usage = response.usage_metadata
    print(f"\n📊 Actual Token Usage:")
    print(f"  Prompt tokens:     {usage.prompt_token_count if usage.prompt_token_count else '(not available)':,}")
    if usage.candidates_token_count:
        print(f"  Response tokens:   {usage.candidates_token_count:,}")
    if usage.total_token_count:
        print(f"  Total tokens:      {usage.total_token_count:,}")
    
    print("\n📝 Gemini's Description:")
    print("─" * 60)
    print(response.text)
    print("─" * 60)
    
    # Clean up
    print("\n🧹 Cleaning up...")
    client.files.delete(name=uploaded_file.name)
    print("✓ Image deleted from Google")

if __name__ == "__main__":
    try:
        describe_screen()
    except Exception as e:
        print(f"❌ Error: {e}")
