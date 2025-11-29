"""
Insight Agent - Generates hypotheses about performance patterns.
FIXED: Now query-aware - focuses on what user actually asks
"""

import json
import re
from typing import Dict, Any, List
from pathlib import Path


class InsightAgent:
    """Generates insights and hypotheses based on user query."""
    
    def __init__(self, config: Dict[str, Any], llm_client, logger):
        self.config = config
        self.llm_client = llm_client
        self.logger = logger
        self.prompt_template = self._load_prompt()
    
    def _load_prompt(self) -> str:
        """Load prompt template."""
        prompt_path = Path("prompts/insight_agent_prompt.md")
        if prompt_path.exists():
            return prompt_path.read_text()
        return "You are an Insight Agent. Generate hypotheses about data patterns."
    
    def generate_hypotheses(self, data_summary: Dict[str, Any], user_query: str = None) -> Dict[str, Any]:
        """
        Generate hypotheses explaining performance patterns.
        
        Args:
            data_summary: Summary from Data Agent
            user_query: User's original question (NEW - for query awareness)
            
        Returns:
            List of hypotheses with evidence
        """
        self.logger.log_agent_action(
            "InsightAgent",
            "generating_hypotheses",
            {"data_summary_keys": list(data_summary.keys()), "user_query": user_query}
        )
        
        try:
            # Extract summary data
            summary_data = data_summary.get('summary', {})
            
            # ✅ NEW: Detect metrics mentioned in query
            query_metrics = self._extract_metrics_from_query(user_query or "")
            query_focus = self._classify_query(user_query or "")
            
            # ✅ NEW: Build query-aware prompt
            focus_instruction = self._build_focus_instruction(user_query, query_metrics, query_focus)
            
            # Construct prompt with data summary AND user query
            messages = [
                {"role": "system", "content": self.prompt_template},
                {"role": "user", "content": f"""
USER'S QUESTION: "{user_query or 'Analyze overall performance'}"

{focus_instruction}

Data Summary:
{json.dumps(summary_data, indent=2)}

Generate 3-5 hypotheses that DIRECTLY ANSWER the user's question above.

Return JSON with this structure:
{{
  "hypotheses": [
    {{
      "id": "H1",
      "hypothesis": "Clear statement addressing the user's question",
      "confidence": 0.8,
      "evidence": ["Evidence point 1 with numbers", "Evidence point 2 with numbers"],
      "impact": "high/medium/low",
      "recommendation": "What should be done"
    }}
  ]
}}

IMPORTANT:
- Focus on metrics mentioned in the question ({', '.join(query_metrics) if query_metrics else 'ROAS, CTR'})
- Include specific campaign names when relevant
- Use actual numbers from the data
- Make hypotheses specific, not generic
"""}
            ]
            
            response = self.llm_client.chat.completions.create(
                model=self.config['llm']['model'],
                messages=messages,
                temperature=self.config['llm']['temperature'],
                max_tokens=self.config['llm']['max_tokens']
            )
            
            # Parse response
            content = response.choices[0].message.content
            
            # Try to extract JSON from response
            try:
                hypotheses = json.loads(content)
            except json.JSONDecodeError:
                # If response is not pure JSON, try to find JSON block
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    hypotheses = json.loads(json_match.group())
                else:
                    raise ValueError("Could not parse LLM response as JSON")
            
            # Ensure hypotheses key exists
            if 'hypotheses' not in hypotheses:
                hypotheses = {'hypotheses': []}
            
            # Add IDs if missing
            for i, h in enumerate(hypotheses['hypotheses']):
                if 'id' not in h:
                    h['id'] = f"H{i+1}"
            
            # Filter by confidence threshold
            min_confidence = self.config['agents']['insight']['min_confidence']
            filtered_hypotheses = [
                h for h in hypotheses.get('hypotheses', [])
                if h.get('confidence', 0) >= min_confidence
            ]
            
            hypotheses['hypotheses'] = filtered_hypotheses
            
            self.logger.log_agent_action(
                "InsightAgent",
                "hypotheses_generated",
                {"count": len(filtered_hypotheses)},
                status="success"
            )
            
            return hypotheses
            
        except Exception as e:
            self.logger.log_error("InsightAgent", str(e))
            # Return fallback hypotheses based on data
            return self._generate_fallback_hypotheses(data_summary, user_query)
    
    def _extract_metrics_from_query(self, query: str) -> List[str]:
        """Extract metrics mentioned in user query."""
        query_lower = query.lower()
        metrics = []
        
        if 'cpc' in query_lower or 'cost per click' in query_lower:
            metrics.append('CPC')
        if 'roas' in query_lower or 'return on ad spend' in query_lower:
            metrics.append('ROAS')
        if 'ctr' in query_lower or 'click-through' in query_lower or 'click through' in query_lower:
            metrics.append('CTR')
        if 'spend' in query_lower or 'budget' in query_lower or 'cost' in query_lower:
            metrics.append('Spend')
        if 'revenue' in query_lower or 'sales' in query_lower:
            metrics.append('Revenue')
        if 'conversion' in query_lower:
            metrics.append('Conversions')
            
        return metrics
    
    def _classify_query(self, query: str) -> str:
        """Classify the type of question user is asking."""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['which', 'what', 'list', 'show me']):
            if 'campaign' in query_lower:
                return 'campaign_ranking'
            if 'message' in query_lower or 'creative' in query_lower or 'ad' in query_lower:
                return 'creative_analysis'
            if 'audience' in query_lower:
                return 'audience_analysis'
        
        if any(word in query_lower for word in ['why', 'reason', 'cause', 'explain']):
            return 'root_cause_analysis'
        
        if any(word in query_lower for word in ['pause', 'stop', 'kill', 'turn off']):
            return 'pause_recommendation'
        
        if any(word in query_lower for word in ['improve', 'optimize', 'fix', 'better']):
            return 'optimization'
        
        return 'general_analysis'
    
    def _build_focus_instruction(self, query: str, metrics: List[str], query_type: str) -> str:
        """Build specific instructions based on query."""
        
        if query_type == 'campaign_ranking':
            return """
FOCUS: The user wants a RANKED LIST of campaigns.
- Identify specific campaign names with their metrics
- Order them from best to worst (or worst to best based on context)
- Include actual performance numbers
"""
        
        elif query_type == 'root_cause_analysis':
            metric_focus = metrics[0] if metrics else 'ROAS'
            return f"""
FOCUS: The user wants to know WHY {metric_focus} changed.
- Analyze {metric_focus} trends over time
- Compare {metric_focus} across segments (audience, creative, platform)
- Identify root causes with evidence
- Include specific data points and comparisons
"""
        
        elif query_type == 'creative_analysis':
            return """
FOCUS: The user wants creative/messaging insights.
- Analyze actual ad message text
- Identify patterns in high vs low performing messages
- Reference specific campaigns and their messages
"""
        
        elif query_type == 'audience_analysis':
            return """
FOCUS: The user wants audience performance comparison.
- Compare Broad vs Lookalike vs Retargeting
- Include specific metrics for each audience type
- Recommend which audiences to use
"""
        
        else:
            metric_text = ', '.join(metrics) if metrics else 'ROAS and CTR'
            return f"""
FOCUS: Answer the user's question directly.
- Prioritize analysis of: {metric_text}
- Include specific examples and numbers
- Make hypotheses actionable
"""
    
    def _generate_fallback_hypotheses(self, data_summary: Dict[str, Any], user_query: str = None) -> Dict[str, Any]:
        """Generate rule-based hypotheses if LLM fails."""
        summary = data_summary.get('summary', {})
        metrics = summary.get('metrics', {})
        
        # Extract metrics from query
        query_metrics = self._extract_metrics_from_query(user_query or "")
        
        hypotheses = []
        
        # Query-aware fallback
        if 'CPC' in query_metrics:
            avg_cpc = metrics.get('avg_cpc', 0)
            hypotheses.append({
                "id": "H1",
                "hypothesis": f"Average CPC is ${avg_cpc:.2f}. Analyze if this has increased over time or varies by audience type.",
                "confidence": 0.75,
                "evidence": [f"Average CPC: ${avg_cpc:.2f}"],
                "impact": "high",
                "recommendation": "Review CPC trends by month and audience segment"
            })
        
        # Default ROAS hypothesis
        avg_roas = metrics.get('avg_roas', 0)
        if avg_roas < self.config['thresholds']['low_roas']:
            hypotheses.append({
                "id": "H2",
                "hypothesis": f"Overall ROAS of {avg_roas:.2f} is below healthy threshold of {self.config['thresholds']['low_roas']}",
                "confidence": 0.9,
                "evidence": [f"Average ROAS: {avg_roas:.2f}", "Below industry benchmark"],
                "impact": "high",
                "recommendation": "Investigate ad creative quality and audience targeting"
            })
        
        # CTR hypothesis
        avg_ctr = metrics.get('avg_ctr', 0)
        hypotheses.append({
            "id": "H3",
            "hypothesis": f"Average CTR of {avg_ctr:.2%} indicates ad engagement level",
            "confidence": 0.85,
            "evidence": [f"Average CTR: {avg_ctr:.2%}"],
            "impact": "medium",
            "recommendation": "Compare CTR across creative types and audiences"
        })
        
        return {"hypotheses": hypotheses[:3]}  # Return top 3
