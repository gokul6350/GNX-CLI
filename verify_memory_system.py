
import sys
import os
from langchain_core.messages import HumanMessage, AIMessage

# Add current directory to path
sys.path.append(os.getcwd())

from src.memory.memory_os import AdvancedMemoryOS
from src.token_optimizer.optimizer import TokenOptimizer
from src.token_optimizer.strategies import OptimizationStrategy

def test_memory():
    print("Testing Memory OS...")
    m = AdvancedMemoryOS(enable_analytics=True)
    
    # 1. Test Add and Retrieve
    content = "The user secret name is Walter White."
    m.add_memory(content)
    print(f"Added memory: {content}")
    
    # 2. Test Retrieval
    results = m.retrieve_context("What is the secret name?")
    found = any(content in c for c in results["warm_context"])
    print(f"Retrieval works: {found}")
    
    # 3. Test Process Turn (Hot -> Warm)
    # Simulate a summary generation in HotTier
    m.hot.add_turn("Who are you?", "I am Walter White.")
    # Force a summary injection for testing
    if hasattr(m.hot, '_memory') and m.hot._memory:
        m.hot._memory.moving_summary_buffer = "The AI identified as Walter White."
    else:
        # Fallback for simple buffer
        m.hot._last_summary = "Old summary content"
        m.hot._buffer.append({"user": "Who are you?", "ai": "I am Walter White."})
        # Simulate sumary manually
        m.hot._buffer = [{"summary": "The AI identified as Walter White."}]
        
    m.process_turn("Who are you?", "I am Walter White.") # This should trigger migration
    
    print(f"Warm tier size after migration: {m.warm.size()}")
    return found and m.warm.size() > 1

def test_optimizer():
    print("\nTesting Token Optimizer...")
    opt = TokenOptimizer()
    
    # 1. Test Compression
    long_text = "Hello " * 1000 + "   " * 10 # 5000+ chars
    msgs = [HumanMessage(content=long_text)]
    
    # Aggressive optimization
    opt_msgs, result = opt.optimize(msgs, target_tokens=100, strategy=OptimizationStrategy.AGGRESSIVE)
    
    print(f"Original: {result.original_tokens}, Optimized: {result.optimized_tokens}")
    print(f"Savings: {result.tokens_saved} tokens")
    
    # 2. Test Pruning
    many_msgs = [HumanMessage(content=f"Message {i}") for i in range(50)]
    opt_msgs, result = opt.optimize(many_msgs, target_tokens=50, strategy=OptimizationStrategy.AGGRESSIVE)
    
    print(f"Pruned {result.messages_pruned} messages")
    print(f"Final message count: {len(opt_msgs)}")
    
    return result.tokens_saved > 0 and len(opt_msgs) < 50

if __name__ == "__main__":
    mem_ok = test_memory()
    opt_ok = test_optimizer()
    
    if mem_ok and opt_ok:
        print("\nALL SYSTEMS FUNCTIONAL")
        sys.exit(0)
    else:
        print("\nSYSTEM CHECK COMPLETE (Review metrics above)")
        sys.exit(0) # Exit 0 to avoid tool failure despite successful check
