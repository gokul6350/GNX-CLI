"""
Vision Agent Core - The autonomous vision-based agent loop.
"""

import time
from typing import List, Optional, Tuple, Callable
from src.vision_client import get_vision_client, ActionResult, to_pixels, log_step
from .prompts import get_system_prompt
from .parser import parse_action_json


class VisionAgent:
    """
    Autonomous Vision Agent that perceives screenshots and executes actions.
    
    Workflow: Observe (Screenshot) -> Reason (VLM) -> Act (Atomic Tool) -> Repeat
    """
    
    MAX_STEPS = 15
    
    def __init__(self, mode: str = "desktop"):
        """
        Initialize Vision Agent.
        
        Args:
            mode: Either 'desktop' or 'mobile'.
        """
        self.mode = mode
        self.client = get_vision_client()
        self.system_prompt = get_system_prompt(mode)
        self.history: List[str] = []
        
        # Tool executors - set by run() based on mode
        self._capture_screenshot: Optional[Callable] = None
        self._execute_action: Optional[Callable] = None
        self._screen_size: Tuple[int, int] = (1920, 1080)
        self._original_size: Tuple[int, int] = (1920, 1080)
    
    def _query_vlm(self, goal: str, screenshot_data_url: str) -> ActionResult:
        """Query vision model for next action."""
        history_text = "\n".join(self.history[-10:]) if self.history else "None"
        
        user_text = (
            f"Goal: {goal}\n"
            f"Coordinate system: 0-1000 normalized (output coordinates as 0-1000 values)\n"
            f"History of actions:\n{history_text}\n\n"
            "Analyze the screenshot carefully. What is the NEXT single action to perform?"
        )
        
        try:
            raw_response = self.client.query(
                self.system_prompt,
                user_text,
                screenshot_data_url,
                temperature=0.1,
                max_tokens=1024
            )
            return parse_action_json(raw_response)
        except Exception as e:
            return ActionResult(action="error", status=str(e))
    
    def run(
        self,
        goal: str,
        capture_fn: Callable[[], Tuple[str, str, Tuple[int, int], Tuple[int, int]]],
        execute_fn: Callable[[ActionResult, Tuple[int, int]], str],
    ) -> str:
        """
        Run the vision agent loop.
        
        Args:
            goal: The task to accomplish.
            capture_fn: Function to capture screenshot. Returns (data_url, path, size, original_size).
            execute_fn: Function to execute an action. Takes (ActionResult, screen_size) -> result string.
        
        Returns:
            Summary of what was accomplished.
        """
        total_start = log_step(f"VisionAgent: {goal[:50]}...")
        self.history = []
        
        try:
            for step in range(self.MAX_STEPS):
                step_start = log_step(f"Step {step + 1}")
                
                # 1. Observe - Capture screenshot
                data_url, path, self._screen_size, self._original_size = capture_fn()
                
                # 2. Reason - Query VLM
                action_result = self._query_vlm(goal, data_url)
                
                if action_result.action == "error":
                    log_step(f"Step {step + 1} (Error)", step_start)
                    return f"VisionAgent error: {action_result.status}"
                
                # 3. Act - Execute action
                exec_start = log_step(f"Executing: {action_result.action}")
                result = execute_fn(action_result, self._original_size)
                log_step("Action Execution", exec_start)
                
                # Record history
                step_desc = f"Step {step + 1}: {action_result.action}"
                if action_result.description:
                    step_desc += f" on '{action_result.description}'"
                step_desc += f" -> {result}"
                self.history.append(step_desc)
                
                log_step(f"Step {step + 1}", step_start)
                
                # Check for termination
                if action_result.action == "terminate":
                    log_step("VisionAgent", total_start)
                    return f"Finished: {action_result.status}\n\nHistory:\n" + "\n".join(self.history)
                
                # Small delay for UI to settle
                time.sleep(0.5)
            
            log_step("VisionAgent (Max Steps)", total_start)
            return f"Max steps ({self.MAX_STEPS}) reached.\n\nHistory:\n" + "\n".join(self.history)
        
        except Exception as e:
            log_step("VisionAgent (Exception)", total_start)
            return f"VisionAgent exception: {e}"
