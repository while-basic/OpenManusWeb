# app/flow/agent_integration.py

from typing import Dict, Optional, Type, Union

from app.agent.base import BaseAgent
from app.agent.manus import Manus
from app.agent.planning import PlanningAgent
from app.agent.swe import SWEAgent
from app.flow.base import BaseFlow
from app.logger import logger
from app.schema import Message


class AgentIntegration:
    """
    Helper class for managing agent integration and context sharing between agents.
    Facilitates smooth handoffs between different agent types.
    """

    @staticmethod
    async def handoff_to_planning(
        source_agent: BaseAgent, 
        planning_agent: Optional[PlanningAgent] = None,
        request: str = ""
    ) -> PlanningAgent:
        """
        Prepare for handoff from a source agent to a Planning Agent.
        
        Args:
            source_agent: The agent initiating the handoff
            planning_agent: Optional existing planning agent to use
            request: The specific request to hand off
            
        Returns:
            An initialized PlanningAgent ready to continue the task
        """
        # Create planning agent if not provided
        if not planning_agent:
            planning_agent = PlanningAgent()
            
        # Create context for planning agent
        context = f"""
        I'm taking over this task from {source_agent.name}.
        
        Task context:
        {request}
        
        Previous actions:
        {AgentIntegration._get_recent_agent_history(source_agent, max_messages=5)}
        
        Please create an appropriate plan for this task.
        """
        
        # Initialize with context
        planning_agent.memory.add_message(Message.user_message(context))
        
        logger.info(f"Handoff from {source_agent.name} to Planning Agent initiated")
        return planning_agent
    
    @staticmethod
    async def handoff_to_swe(
        source_agent: BaseAgent, 
        swe_agent: Optional[SWEAgent] = None,
        code_task: str = ""
    ) -> SWEAgent:
        """
        Prepare for handoff from a source agent to an SWE Agent.
        
        Args:
            source_agent: The agent initiating the handoff
            swe_agent: Optional existing SWE agent to use
            code_task: The specific coding task to hand off
            
        Returns:
            An initialized SWEAgent ready to continue the task
        """
        # Create SWE agent if not provided
        if not swe_agent:
            swe_agent = SWEAgent()
            
        # Create context for SWE agent
        context = f"""
        I'm taking over this coding task from {source_agent.name}.
        
        Coding task:
        {code_task}
        
        Previous context:
        {AgentIntegration._get_recent_agent_history(source_agent, max_messages=5)}
        
        Please explore the codebase and implement the appropriate solution.
        """
        
        # Initialize with context
        swe_agent.memory.add_message(Message.user_message(context))
        
        logger.info(f"Handoff from {source_agent.name} to SWE Agent initiated")
        return swe_agent
    
    @staticmethod
    async def handoff_to_manus(
        source_agent: BaseAgent, 
        manus_agent: Optional[Manus] = None,
        info_request: str = ""
    ) -> Manus:
        """
        Prepare for handoff from a source agent to a Manus Agent.
        
        Args:
            source_agent: The agent initiating the handoff
            manus_agent: Optional existing Manus agent to use
            info_request: The specific information request to hand off
            
        Returns:
            An initialized Manus agent ready to continue the task
        """
        # Create Manus agent if not provided
        if not manus_agent:
            manus_agent = Manus()
            
        # Create context for Manus agent
        context = f"""
        I'm taking over this information-gathering task from {source_agent.name}.
        
        Information needed:
        {info_request}
        
        Previous context:
        {AgentIntegration._get_recent_agent_history(source_agent, max_messages=5)}
        
        Please find the requested information using your capabilities.
        """
        
        # Initialize with context
        manus_agent.memory.add_message(Message.user_message(context))
        
        logger.info(f"Handoff from {source_agent.name} to Manus Agent initiated")
        return manus_agent
    
    @staticmethod
    def _get_recent_agent_history(agent: BaseAgent, max_messages: int = 5) -> str:
        """
        Extract recent message history from an agent in a readable format.
        
        Args:
            agent: The agent to extract history from
            max_messages: Maximum number of messages to include
            
        Returns:
            Formatted string of recent agent messages
        """
        history = []
        messages = agent.memory.get_recent_messages(max_messages)
        
        for msg in messages:
            role = msg.role.capitalize()
            content = msg.content if msg.content else "[Tool execution]"
            history.append(f"{role}: {content[:200]}{'...' if len(content) > 200 else ''}")
            
        return "\n".join(history)
    
    @staticmethod
    async def return_results_to_source(
        source_agent: BaseAgent,
        results_agent: BaseAgent,
        results: str
    ) -> None:
        """
        Return results from a specialized agent back to the source agent.
        
        Args:
            source_agent: The original agent that initiated the handoff
            results_agent: The specialized agent that generated results
            results: The results to pass back
        """
        context = f"""
        Results from {results_agent.name}:
        
        {results}
        
        Please continue with your task using this information.
        """
        
        source_agent.memory.add_message(Message.user_message(context))
        logger.info(f"Results from {results_agent.name} returned to {source_agent.name}")