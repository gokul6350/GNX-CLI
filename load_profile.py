"""
Script to inject personalized user data into Memory OS.
Run this once to pre-seed your memory with your profile.
"""

import sys
import os
from dotenv import load_dotenv

# Load .env BEFORE any src imports
load_dotenv()

sys.path.append(os.getcwd())

from src.memory import AdvancedMemoryOS

# Your personalized profile data - split into distinct chunks
PROFILE_CHUNKS = [
    (
        "personal_info",
        """User: S.K. GOKULBARATH
Date of Birth: September 17, 2005 (10:20 AM, Chennai)
Height: 170 cm
Location: Chennai, India
Routine: Wake 10:00 AM IST, Sleep 02:00 AM IST
Nutrition: OMAD protocol with Intermittent Fasting
Training: 2 hours daily calisthenics and acrobatics
Note: Has Deviated Nasal Septum"""
    ),
    (
        "professional",
        """User profession: 2nd-year Mechatronics Engineering student.
Founder of a SaaS tech ecosystem (established 2021).
Specializes in Embedded Systems (Robotics) and Advanced AI (LLMs/Computer Vision).
Expert in fine-tuning LLMs for robotic control and developing autonomous systems."""
    ),
    (
        "tech_stack",
        """User technical arsenal:
Primary OS: Kubuntu KDE (daily driver), Kali Linux (security), Windows (dual-boot)
Languages: Python (primary), C, C++, JavaScript (React/Next.js)
AI/CV: YOLOv8, OpenCV, TensorFlow, PyTorch, Gemini API
Robotics: ROS, Gazebo, Arduino, Raspberry Pi Pico W
Web/Backend: FastAPI, Flask, Streamlit, React, Socket.IO"""
    ),
    (
        "projects",
        """User active projects:
1. AutonomX - Autonomous delivery rover (Python, ROS, React, Socket.IO, GPS)
2. Women Safety Analytics - YOLOv8 on street lights with face/wake-word detection
3. Ghost Blocker App - Hidden Android app for web blocking and location tracking
4. Inventory & Invoice System - Web app converting to .exe"""
    ),
    (
        "fitness",
        """User physical training goals:
- L-Sit and L-Sit to Handstand (static strength)
- Gainer Flip, Backflip (dynamic power)
- Fly Push-ups no-foot-touching variant (explosive strength)"""
    ),
]

def main():
    print("Initializing Memory OS...")
    memory = AdvancedMemoryOS(enable_analytics=False)
    
    print(f"Embedding provider: {memory.warm.embeddings.provider_name}")
    print(f"Storage path: {memory.warm.storage_path}")
    
    # Add each chunk
    for name, content in PROFILE_CHUNKS:
        memory.add_memory(content.strip(), tags=[name])
        print(f"  Added: {name}")
    
    print(f"\nTotal memories in Warm Tier: {memory.warm.size()}")
    
    # Test retrieval
    print("\n--- TESTING RETRIEVAL ---")
    test_queries = [
        "What is the user's name?",
        "What programming languages does the user know?",
        "What is the AutonomX project?",
        "What calisthenics skills is user training?",
    ]
    
    for query in test_queries:
        results = memory.retrieve_context(query, top_k=1)
        found = results["warm_context"][0][:80] if results["warm_context"] else "Not found"
        print(f"\nQ: {query}")
        print(f"A: {found}...")
    
    print("\n--- PROFILE LOADED AND PERSISTED ---")
    print(f"Saved to: {memory.warm.storage_path}")

if __name__ == "__main__":
    main()
