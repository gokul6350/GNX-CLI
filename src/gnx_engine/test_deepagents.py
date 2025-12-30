
import sys
import os

# Add src to path
sys.path.append(os.getcwd())

if "GOOGLE_API_KEY" not in os.environ:
    os.environ["GOOGLE_API_KEY"] = "AIzaSyAZc84jW2KbLE2qFCas80BtaMftNA_18q8"

from src.gnx_engine.engine import GNXEngine

if __name__ == "__main__":
    with open("test_output.txt", "w", encoding="utf-8") as f:
        sys.stdout = f
        sys.stderr = f
        
        try:
            print("Testing direct model invocation...")
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(model="gemma-3-27b-it")
            res = llm.invoke("Hello")
            print(f"Direct model response: {res.content}")
            print("Direct model test PASSED.")
            
            print("Initializing GNXEngine...")
            engine = GNXEngine()
            print("GNXEngine initialized successfully.")
            
            print("Running simple query...")
            # Using a query that doesn't strictly need a tool but tests the agent loop
            response = engine.run("Hello, are you online?")
            print(f"Response: {response}")
            print("Test Passed!")
        except Exception as e:
            print(f"Test Failed with error: {e}")
            import traceback
            traceback.print_exc()
