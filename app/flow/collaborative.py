# app/flow/collaborative.py

import asyncio
import time
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

from pydantic import Field

from app.agent.base import BaseAgent
from app.agent.manus import Manus
from app.agent.planning import PlanningAgent
from app.agent.swe import SWEAgent
from app.flow.agent_integration import AgentIntegration
from app.flow.base import BaseFlow, FlowType
from app.logger import logger
from app.schema import Message


class AgentRole(str, Enum):
    """Define roles for agents in collaborative workflows"""
    COORDINATOR = "coordinator"  # Manages the overall workflow
    PLANNER = "planner"          # Creates and manages plans
    PROGRAMMER = "programmer"    # Handles code-related tasks
    RESEARCHER = "researcher"    # Gathers information


class CollaborativeFlow(BaseFlow):
    """
    A flow that enables collaboration between different agent types
    to solve complex tasks by leveraging their specialized capabilities.
    """

    # Key agents for different roles
    coordinator: Optional[Manus] = Field(default=None)
    planner: Optional[PlanningAgent] = Field(default=None)
    programmer: Optional[SWEAgent] = Field(default=None)
    
    # Tracking
    active_agent_key: str = Field(default="coordinator")
    collaboration_history: List[Dict] = Field(default_factory=list)
    flow_start_time: float = Field(default_factory=time.time)
    
    def __init__(
        self, agents: Union[BaseAgent, List[BaseAgent], Dict[str, BaseAgent]], **data
    ):
        super().__init__(agents, **data)
        
        # Initialize role-specific agents
        self._initialize_role_agents()
        
        # Set coordinator as primary if not specified
        if not self.primary_agent_key and self.coordinator:
            self.primary_agent_key = "coordinator"
            
        # Log the initialization    
        logger.info(f"Collaborative flow initialized with agents: {', '.join(self.agents.keys())}")
    
    def _initialize_role_agents(self):
        """Initialize specialized agents for each role from the agents dictionary"""
        
        # Find agents by type
        for key, agent in self.agents.items():
            if isinstance(agent, Manus) and not self.coordinator:
                self.coordinator = agent
                self.agents["coordinator"] = agent
                
            elif isinstance(agent, PlanningAgent) and not self.planner:
                self.planner = agent
                self.agents["planner"] = agent
                
            elif isinstance(agent, SWEAgent) and not self.programmer:
                self.programmer = agent
                self.agents["programmer"] = agent
        
        # Create any missing essential agents
        if not self.coordinator:
            self.coordinator = Manus()
            self.agents["coordinator"] = self.coordinator
            
        if not self.primary_agent:
            self.primary_agent_key = "coordinator"
            
        logger.info(f"Initialized collaborative flow with {len(self.agents)} agents")
    
    async def execute(
        self, input_text: str, job_id: str = None, cancel_event: asyncio.Event = None
    ) -> str:
        """
        Execute the collaborative flow with agents.
        
        Args:
            input_text: The user's input request
            job_id: Optional job identifier for logging
            cancel_event: Optional event to signal cancellation
            
        Returns:
            String containing the execution results
        """
        try:
            # Reset tracking
            self.flow_start_time = time.time()
            self.collaboration_history = []
            
            # Initialize with the coordinator agent
            self.active_agent_key = "coordinator"
            
            # Start with the coordinator to understand the task
            coordinator_result = await self.coordinator.run(input_text)
            self._log_agent_action("coordinator", "task_analysis", input_text, coordinator_result)
            
            # Determine if planning is needed
            needs_planning = "structured plan" in coordinator_result.lower() or \
                            "break down" in coordinator_result.lower() or \
                            "complex task" in coordinator_result.lower()
            
            if needs_planning and self.planner:
                # Handoff to planner
                self.active_agent_key = "planner"
                planning_request = f"Create a plan for this task: {input_text}"
                
                # Use integration helper for handoff
                await AgentIntegration.handoff_to_planning(
                    self.coordinator, 
                    self.planner, 
                    planning_request
                )
                
                # Execute planning
                plan_result = await self.planner.run()
                self._log_agent_action("planner", "planning", planning_request, plan_result)
                
                # Execute plan steps, potentially involving other agents
                plan_execution_result = await self._execute_plan(cancel_event)
                
                # Return results back to coordinator
                await AgentIntegration.return_results_to_source(
                    self.coordinator,
                    self.planner,
                    plan_execution_result
                )
                
                # Final summary from coordinator
                self.active_agent_key = "coordinator"
                final_result = await self.coordinator.run("Provide a final summary of the completed task.")
                
                return final_result
            else:
                # Coordinator handles the task directly
                direct_result = await self._handle_direct_execution(input_text, cancel_event)
                return direct_result
                
        except Exception as e:
            logger.error(f"Error in CollaborativeFlow: {str(e)}")
            return f"Execution failed: {str(e)}"
    
    async def _execute_plan(self, cancel_event: Optional[asyncio.Event] = None) -> str:
        """Execute the plan created by the planning agent, potentially involving other agents"""
        if not self.planner:
            return "Cannot execute plan: No planning agent available"
        
        execution_results = []
        
        # Continue executing steps until plan complete or canceled
        while True:
            # Check for cancellation
            if cancel_event and cancel_event.is_set():
                return "Plan execution cancelled"
            
            # Get current step from planner
            current_step_index, step_info = await self._get_current_step()
            
            # Exit if no more steps
            if current_step_index is None:
                break
                
            step_text = step_info.get("text", "")
            step_type = step_info.get("type")
            
            # Determine which agent should handle this step
            if step_type == "code" and self.programmer:
                # Programming step - delegate to SWE agent
                self.active_agent_key = "programmer"
                
                # Handoff to programmer
                await AgentIntegration.handoff_to_swe(
                    self.planner,
                    self.programmer,
                    step_text
                )
                
                # Execute programming task
                programming_result = await self.programmer.run()
                self._log_agent_action("programmer", "coding", step_text, programming_result)
                
                # Return results to planner
                await AgentIntegration.return_results_to_source(
                    self.planner,
                    self.programmer,
                    programming_result
                )
                
                execution_results.append(f"Step {current_step_index} (Programming): {programming_result}")
                
            elif step_type == "research" and self.coordinator:
                # Research step - delegate to Manus agent
                self.active_agent_key = "coordinator"
                
                # Handoff to research
                await AgentIntegration.handoff_to_manus(
                    self.planner,
                    self.coordinator,
                    step_text
                )
                
                # Execute research task
                research_result = await self.coordinator.run()
                self._log_agent_action("coordinator", "research", step_text, research_result)
                
                # Return results to planner
                await AgentIntegration.return_results_to_source(
                    self.planner,
                    self.coordinator,
                    research_result
                )
                
                execution_results.append(f"Step {current_step_index} (Research): {research_result}")
                
            else:
                # Default to planner executing its own steps
                self.active_agent_key = "planner"
                step_result = await self.planner.run(f"Execute step {current_step_index}: {step_text}")
                self._log_agent_action("planner", "execution", step_text, step_result)
                
                execution_results.append(f"Step {current_step_index}: {step_result}")
            
            # Mark step as completed
            await self._mark_step_completed(current_step_index)
            
        return "\n\n".join(execution_results)
    
    async def _handle_direct_execution(
        self, task: str, cancel_event: Optional[asyncio.Event] = None
    ) -> str:
        """Handle direct task execution by the coordinator without formal planning"""
        if not self.coordinator:
            return "Cannot execute task: No coordinator agent available"
            
        # Check if task involves code
        needs_coding = "code" in task.lower() or \
                      "programming" in task.lower() or \
                      "script" in task.lower() or \
                      "function" in task.lower() or \
                      "develop" in task.lower()
                      
        if needs_coding and self.programmer:
            # For coding tasks, use the SWE agent
            self.active_agent_key = "programmer"
            
            # Handoff to programmer
            await AgentIntegration.handoff_to_swe(
                self.coordinator,
                self.programmer,
                task
            )
            
            # Execute programming task
            programming_result = await self.programmer.run()
            self._log_agent_action("programmer", "coding", task, programming_result)
            
            # Return results to coordinator for final delivery
            await AgentIntegration.return_results_to_source(
                self.coordinator,
                self.programmer,
                programming_result
            )
            
            # Get final summary from coordinator
            self.active_agent_key = "coordinator"
            final_result = await self.coordinator.run("Provide a final summary incorporating the programming results.")
            
            return final_result
        else:
            # For other tasks, let coordinator handle directly
            direct_result = await self.coordinator.run(task)
            self._log_agent_action("coordinator", "direct_execution", task, direct_result)
            
            return direct_result
            
    async def _get_current_step(self) -> Tuple[Optional[int], Optional[Dict]]:
        """Get the current step from the planner that needs execution"""
        if not self.planner:
            return None, None
            
        # Use the planner's internal method to get the current step
        try:
            current_step_index, step_info = await self.planner._get_current_step_info()
            return current_step_index, step_info
        except Exception as e:
            logger.error(f"Error getting current step: {str(e)}")
            return None, None
            
    async def _mark_step_completed(self, step_index: int) -> bool:
        """Mark a step as completed in the planner"""
        if not self.planner:
            return False
            
        try:
            # Use the planner's method to mark step as completed
            await self.planner.update_plan_status(f"step_{step_index}")
            return True
        except Exception as e:
            logger.error(f"Error marking step {step_index} as completed: {str(e)}")
            return False
            
    def _log_agent_action(self, agent_key: str, action_type: str, input_text: str, result: str) -> None:
        """Log an agent action for tracking and debugging"""
        entry = {
            "timestamp": time.time(),
            "elapsed": time.time() - self.flow_start_time,
            "agent": agent_key,
            "action": action_type,
            "input": input_text[:200] + ("..." if len(input_text) > 200 else ""),
            "result": result[:200] + ("..." if len(result) > 200 else "")
        }
        
        self.collaboration_history.append(entry)
        logger.info(f"Agent action: {agent_key} performed {action_type}")
        
    def get_collaboration_summary(self) -> str:
        """Generate a summary of the collaboration process"""
        if not self.collaboration_history:
            return "No collaboration has occurred yet."
            
        steps = []
        for i, entry in enumerate(self.collaboration_history, 1):
            agent = entry["agent"]
            action = entry["action"]
            elapsed = entry["elapsed"]
            steps.append(f"{i}. [{elapsed:.2f}s] {agent.capitalize()} performed {action}")
            
        total_time = time.time() - self.flow_start_time
        return f"Collaboration summary ({len(steps)} steps, {total_time:.2f}s total):\n" + "\n".join(steps)