"""
Planner Agent - Decomposes user queries into subtasks.
"""

import json
from typing import Dict, Any, List
from pathlib import Path


class PlannerAgent:
    """Plans and orchestrates the analysis workflow."""
    
    def __init__(self, config: Dict[str, Any], llm_client, logger):
        self.config = config
        self.llm_client = llm_client
        self.logger = logger
        self.prompt_template = self._load_prompt()
    
    def _load_prompt(self) -> str:
        """Load prompt template."""
        prompt_path = Path("prompts/planner_prompt.md")
        if prompt_path.exists():
            return prompt_path.read_text()
        return "You are a Planner Agent. Decompose user queries into subtasks."
    
    def plan(self, user_query: str) -> Dict[str, Any]:
        """
        Create an execution plan from user query.
        
        Args:
            user_query: The user's question or request
            
        Returns:
            Structured plan with subtasks
        """
        self.logger.log_agent_action(
            "PlannerAgent",
            "planning",
            {"query": user_query}
        )
        
        try:
            # Construct prompt
            messages = [
                {"role": "system", "content": self.prompt_template},
                {"role": "user", "content": f"User Query: {user_query}\n\nCreate a detailed execution plan."}
            ]
            
            # Call LLM
            response = self.llm_client.chat.completions.create(
                model=self.config['llm']['model'],
                messages=messages,
                temperature=0.3,  # Lower temperature for structured planning
                response_format={"type": "json_object"}
            )
            
            # Parse response
            plan = json.loads(response.choices[0].message.content)
            
            self.logger.log_agent_action(
                "PlannerAgent",
                "plan_created",
                {
                    "subtasks_count": len(plan.get('subtasks', [])),
                    "objective": plan.get('objective', '')
                },
                status="success"
            )
            
            return plan
            
        except Exception as e:
            self.logger.log_error("PlannerAgent", str(e), {"query": user_query})
            # Return fallback plan
            return self._create_fallback_plan(user_query)
    
    def _create_fallback_plan(self, query: str) -> Dict[str, Any]:
        """Create a basic fallback plan if LLM fails."""
        return {
            "query_understanding": query,
            "objective": "Analyze Facebook Ads performance",
            "subtasks": [
                {
                    "step": 1,
                    "agent": "DataAgent",
                    "action": "load_and_summarize",
                    "parameters": {}
                },
                {
                    "step": 2,
                    "agent": "InsightAgent",
                    "action": "generate_hypotheses",
                    "parameters": {}
                },
                {
                    "step": 3,
                    "agent": "EvaluatorAgent",
                    "action": "validate_hypotheses",
                    "parameters": {}
                }
            ]
        }
