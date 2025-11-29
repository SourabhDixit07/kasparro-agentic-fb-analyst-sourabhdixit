"""
Query Router - Detects query type and extracts relevant information.
This is the KEY component that makes the system query-aware!
"""

import re
from typing import Dict, List, Any


class QueryRouter:
    """Routes queries and extracts intent."""
    
    def __init__(self):
        self.metrics = ['cpc', 'roas', 'ctr', 'spend', 'revenue', 'conversions']
        self.entities = ['campaign', 'audience', 'creative', 'message', 'platform']
    
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze user query and extract key information.
        
        Returns:
            {
                'query_type': str,
                'metrics': List[str],
                'entities': List[str],
                'intent': str,
                'needs_ranking': bool,
                'needs_trends': bool
            }
        """
        query_lower = query.lower()
        
        return {
            'query_type': self._classify_query_type(query_lower),
            'metrics': self._extract_metrics(query_lower),
            'entities': self._extract_entities(query_lower),
            'intent': self._detect_intent(query_lower),
            'needs_ranking': self._needs_ranking(query_lower),
            'needs_trends': self._needs_trend_analysis(query_lower),
            'action_required': self._detect_action(query_lower)
        }
    
    def _classify_query_type(self, query: str) -> str:
        """Classify the type of query."""
        
        # Ranking/List queries
        if any(word in query for word in ['which', 'what', 'list', 'show', 'top', 'bottom', 'best', 'worst']):
            if 'campaign' in query:
                return 'campaign_ranking'
            if 'message' in query or 'creative' in query or 'ad' in query:
                return 'creative_ranking'
            if 'audience' in query:
                return 'audience_comparison'
        
        # Why/Root cause queries
        if any(word in query for word in ['why', 'reason', 'cause', 'explain', 'happened']):
            return 'root_cause_analysis'
        
        # How to improve queries
        if any(word in query for word in ['how', 'improve', 'optimize', 'increase', 'boost', 'fix']):
            return 'optimization_recommendation'
        
        # Action queries
        if any(word in query for word in ['pause', 'stop', 'kill', 'turn off', 'disable']):
            return 'pause_recommendation'
        
        if any(word in query for word in ['scale', 'increase budget', 'spend more']):
            return 'scale_recommendation'
        
        # Comparison queries
        if any(word in query for word in ['compare', 'versus', 'vs', 'difference between']):
            return 'comparison'
        
        # Trend queries
        if any(word in query for word in ['trend', 'over time', 'increasing', 'decreasing', 'changing']):
            return 'trend_analysis'
        
        return 'general_analysis'
    
    def _extract_metrics(self, query: str) -> List[str]:
        """Extract metrics mentioned in query."""
        found_metrics = []
        
        if 'cpc' in query or 'cost per click' in query:
            found_metrics.append('cpc')
        if 'roas' in query or 'return on ad spend' in query:
            found_metrics.append('roas')
        if 'ctr' in query or 'click-through' in query or 'click through' in query:
            found_metrics.append('ctr')
        if 'spend' in query or 'budget' in query or 'cost' in query:
            found_metrics.append('spend')
        if 'revenue' in query or 'sales' in query:
            found_metrics.append('revenue')
        if 'conversion' in query:
            found_metrics.append('conversions')
        
        # Default to ROAS if no metric specified
        if not found_metrics:
            found_metrics = ['roas', 'ctr']
        
        return found_metrics
    
    def _extract_entities(self, query: str) -> List[str]:
        """Extract entities mentioned in query."""
        found_entities = []
        
        if 'campaign' in query:
            found_entities.append('campaign')
        if 'audience' in query or 'targeting' in query:
            found_entities.append('audience')
        if 'creative' in query or 'message' in query or 'ad copy' in query:
            found_entities.append('creative')
        if 'platform' in query or 'facebook' in query or 'instagram' in query:
            found_entities.append('platform')
        
        return found_entities
    
    def _detect_intent(self, query: str) -> str:
        """Detect user's intent."""
        
        if any(word in query for word in ['find', 'identify', 'show', 'list']):
            return 'discover'
        
        if any(word in query for word in ['why', 'explain', 'understand']):
            return 'understand'
        
        if any(word in query for word in ['improve', 'optimize', 'fix', 'increase']):
            return 'optimize'
        
        if any(word in query for word in ['should i', 'recommend', 'suggest']):
            return 'recommend'
        
        return 'analyze'
    
    def _needs_ranking(self, query: str) -> bool:
        """Check if query needs campaign ranking."""
        ranking_keywords = [
            'which', 'what', 'top', 'bottom', 'best', 'worst',
            'highest', 'lowest', 'rank', 'list', 'show'
        ]
        return any(word in query for word in ranking_keywords)
    
    def _needs_trend_analysis(self, query: str) -> bool:
        """Check if query needs trend over time."""
        trend_keywords = [
            'trend', 'over time', 'increasing', 'decreasing',
            'growing', 'declining', 'change', 'changing', 'month'
        ]
        return any(word in query for word in trend_keywords)
    
    def _detect_action(self, query: str) -> str:
        """Detect what action user wants."""
        
        if any(word in query for word in ['pause', 'stop', 'turn off']):
            return 'pause'
        
        if any(word in query for word in ['scale', 'increase budget', 'spend more']):
            return 'scale'
        
        if any(word in query for word in ['test', 'a/b', 'experiment']):
            return 'test'
        
        if any(word in query for word in ['change', 'update', 'modify']):
            return 'modify'
        
        return 'analyze'
    
    def generate_analysis_plan(self, query_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a plan based on query analysis."""
        
        plan = {
            'steps': [],
            'focus_areas': [],
            'output_format': 'standard'
        }
        
        query_type = query_analysis['query_type']
        
        if query_type == 'campaign_ranking':
            plan['steps'] = [
                'rank_campaigns_by_metric',
                'analyze_top_performers',
                'analyze_bottom_performers'
            ]
            plan['output_format'] = 'ranked_list'
            
        elif query_type == 'root_cause_analysis':
            plan['steps'] = [
                'analyze_metric_trends',
                'segment_analysis',
                'identify_root_causes'
            ]
            plan['output_format'] = 'hypothesis_based'
            
        elif query_type == 'pause_recommendation':
            plan['steps'] = [
                'identify_underperformers',
                'calculate_waste',
                'recommend_actions'
            ]
            plan['output_format'] = 'action_list'
        
        # Add focus areas based on entities
        plan['focus_areas'] = query_analysis['entities']
        
        return plan
