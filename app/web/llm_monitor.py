"""
LLM Communication Monitoring Module, for capturing and simulating communication with LLMs
"""
import asyncio
import random
import time
from functools import wraps
from typing import Any, Callable, Dict, List, Optional


class LLMMonitor:
    """LLM Communication Monitor, supports various ways to track LLM communications"""

    def __init__(self):
        self.interceptors = []
        self.communications = []
        
    @classmethod
    def create_for_session(cls, session_id, agent):
        """Factory method to create a monitor for a specific session and agent"""
        monitor = cls()
        monitor.session_id = session_id
        monitor.agent = agent
        
        # If agent is provided, set up communication interception
        if agent is not None and hasattr(agent, "llm") and hasattr(agent.llm, "completion"):
            monitor.intercept_method(agent.llm, "completion")
            print(f"LLM communication monitoring set up for session {session_id}")
        
        return monitor

    def register_interceptor(self, func: Callable):
        """Register an interceptor function that will be called on each communication"""
        self.interceptors.append(func)
        return func  # Convenient for use as a decorator

    def record_communication(self, direction: str, content: Any):
        """Record communication content"""
        comm_record = {
            "direction": direction,  # "in" or "out"
            "content": str(content)[:1000],  # Limit length
            "timestamp": time.time(),
        }
        self.communications.append(comm_record)

        # Notify all interceptors
        for interceptor in self.interceptors:
            try:
                interceptor(comm_record)
            except Exception as e:
                print(f"Interceptor error: {str(e)}")

    def get_communications(self, start_idx: int = 0) -> List[Dict[str, Any]]:
        """Get communication records"""
        return self.communications[start_idx:]

    def clear(self):
        """Clear all communication records"""
        self.communications = []

    def intercept_method(self, obj, method_name):
        """Intercept method calls on an object"""
        if not hasattr(obj, method_name):
            return False

        original_method = getattr(obj, method_name)

        @wraps(original_method)
        async def wrapped_method(*args, **kwargs):
            # Record input
            input_data = str(args[0]) if args else str(kwargs)
            self.record_communication("in", input_data)

            # Call the original method
            result = await original_method(*args, **kwargs)

            # Record output
            self.record_communication("out", result)
            return result

        # Replace the original method
        setattr(obj, method_name, wrapped_method)
        return True


# Create a global monitor instance
monitor = LLMMonitor()


# Provide some simulated LLM functions, can be used for demonstration or testing
async def simulate_llm_thinking(
    prompt: str, callback: Optional[Callable] = None, steps: int = 5, delay: float = 1.0
):
    """Simulate LLM thinking process, generating a series of thinking steps"""

    # Record input
    monitor.record_communication("in", prompt)

    thinking_steps = ["Analyzing problem requirements", "Retrieving relevant knowledge", "Organizing information", "Drafting initial answer", "Checking and optimizing answer", "Generating final response"]

    # Adjust thinking steps based on the prompt
    if "code" in prompt or "programming" in prompt:
        thinking_steps = ["Understanding code requirements", "Designing code structure", "Writing core functions", "Implementing error handling", "Testing code functionality", "Optimizing code efficiency"]

    # Ensure reasonable number of steps
    actual_steps = min(steps, len(thinking_steps))

    # Simulate thinking process
    for i in range(actual_steps):
        step_msg = thinking_steps[i]
        if callback:
            callback(step_msg)
        await asyncio.sleep(delay * (0.5 + random.random()))

    # Generate answer
    result = f"This is an answer to the question \"{prompt[:30]}...\"\n\n"
    result += "Based on my analysis, here are several suggestions:\n"
    result += "1. First, confirm the core of the problem\n"
    result += "2. Next, analyze possible solutions\n"
    result += "3. Finally, choose the most appropriate method to implement"

    # Record output
    monitor.record_communication("out", result)
    return result
