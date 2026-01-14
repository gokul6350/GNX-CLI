import os
from dotenv import load_dotenv
from langchain_community.chat_models import ChatZhipuAI
from langchain_core.messages import HumanMessage

def test_glm():
    # Load environment variables
    load_dotenv()
    
    api_key = os.getenv("ZHIPUAI_API_KEY")
    if not api_key:
        print("Error: ZHIPUAI_API_KEY not found in .env file.")
        return

    print(f"Testing ZhipuAI connection with key starting with: {api_key[:10]}...")
    
    try:
        # Initialize the model
        # Trying glm-4-flash (standard model)
        model_name = "glm-4-flash"
        print(f"Initializing {model_name}...")
        
        llm = ChatZhipuAI(
            model=model_name,
            temperature=0.6,
            zhipuai_api_key=api_key
        )
        
        # Simple prompt
        message = HumanMessage(content="Describe the GNX engine in one short sentence.")
        print("Sending request...")
        
        response = llm.invoke([message])
        
        print("\n--- Response ---")
        print(response.content)
        print("----------------\n")
        
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        if "429" in str(e):
            print("\nAdvice: You are hitting rate limits (429). Check your ZhipuAI quota or try the 'glm-4-flash' model instead.")

if __name__ == "__main__":
    test_glm()
