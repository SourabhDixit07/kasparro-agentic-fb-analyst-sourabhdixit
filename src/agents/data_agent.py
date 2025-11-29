"""
Data Agent - Loads, cleans, and summarizes dataset.
ENHANCED: Now provides campaign rankings and query-specific analysis
"""

import json
import pandas as pd
from typing import Dict, Any, List
from pathlib import Path
from src.utils.data_loader import DataLoader


class DataAgent:
    """Handles all data operations."""
    
    def __init__(self, config: Dict[str, Any], llm_client, logger):
        self.config = config
        self.llm_client = llm_client
        self.logger = logger
        self.data_loader = DataLoader(config)
        self.prompt_template = self._load_prompt()
        self.df = None
        self.name = "DataAgent"
    
    def _load_prompt(self) -> str:
        """Load prompt template."""
        prompt_path = Path("prompts/data_agent_prompt.md")
        if prompt_path.exists():
            return prompt_path.read_text()
        return "You are a Data Agent. Summarize and analyze data."
    
    def execute(self, action: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute a data operation.
        
        Args:
            action: Action to perform (load_and_summarize, filter_by_criteria, etc.)
            parameters: Action parameters
            
        Returns:
            Data summary and insights
        """
        parameters = parameters or {}
        
        self.logger.log_agent_action(
            self.name,
            action,
            {"parameters": parameters}
        )
        
        try:
            if action == "load_and_summarize":
                return self._load_and_summarize()
            elif action == "filter_by_criteria":
                return self._filter_data(parameters)
            elif action == "get_creative_patterns":
                return self._get_creative_patterns()
            elif action == "rank_campaigns":
                return self._rank_campaigns(parameters)
            elif action == "get_metric_trends":
                return self._get_metric_trends(parameters)
            else:
                raise ValueError(f"Unknown action: {action}")
                
        except Exception as e:
            self.logger.log_error(self.name, str(e), {"action": action})
            raise
    
    def _load_and_summarize(self) -> Dict[str, Any]:
        """Load data and generate comprehensive summary."""
        # Load and clean data
        self.df = self.data_loader.load_data()
        self.df = self.data_loader.clean_data()
        
        # Generate summary
        summary = self.data_loader.generate_summary()
        
        # Ensure summary is not None
        if summary is None:
            summary = {
                "total_records": len(self.df),
                "columns": list(self.df.columns),
                "date_range": {"start": "N/A", "end": "N/A"},
                "metrics": {
                    "avg_roas": 0.0,
                    "avg_ctr": 0.0,
                    "total_spend": 0.0,
                    "total_revenue": 0.0
                }
            }
        
        # ✅ NEW: Add campaign rankings to summary
        summary['top_campaigns_by_roas'] = self._get_top_campaigns('roas', 10)
        summary['bottom_campaigns_by_roas'] = self._get_bottom_campaigns('roas', 10)
        summary['top_campaigns_by_ctr'] = self._get_top_campaigns('ctr', 10)
        summary['bottom_campaigns_by_ctr'] = self._get_bottom_campaigns('ctr', 10)
        
        # Use LLM to generate insights from summary
        insights = self._generate_insights(summary)
        
        result = {
            "status": "success",
            "summary": summary,
            "insights": insights,
            "dataframe_loaded": True
        }
        
        self.logger.log_agent_action(
            self.name,
            "data_loaded",
            {"records": len(self.df)},
            status="success"
        )
        
        return result
    
    def _get_top_campaigns(self, metric: str, n: int = 10) -> List[Dict]:
        """Get top N campaigns by metric."""
        if self.df is None or len(self.df) == 0:
            return []
        
        # Group by campaign and get mean
        campaign_metrics = self.df.groupby('campaign_name')[metric].mean().reset_index()
        top_campaigns = campaign_metrics.nlargest(n, metric)
        
        return [
            {
                "campaign": row['campaign_name'],
                metric: float(row[metric])
            }
            for _, row in top_campaigns.iterrows()
        ]
    
    def _get_bottom_campaigns(self, metric: str, n: int = 10) -> List[Dict]:
        """Get bottom N campaigns by metric."""
        if self.df is None or len(self.df) == 0:
            return []
        
        # Group by campaign and get mean
        campaign_metrics = self.df.groupby('campaign_name')[metric].mean().reset_index()
        bottom_campaigns = campaign_metrics.nsmallest(n, metric)
        
        return [
            {
                "campaign": row['campaign_name'],
                metric: float(row[metric])
            }
            for _, row in bottom_campaigns.iterrows()
        ]
    
    def _rank_campaigns(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Rank all campaigns by specified metric."""
        metric = parameters.get('metric', 'roas')
        ascending = parameters.get('ascending', False)
        
        if self.df is None:
            raise ValueError("Data not loaded")
        
        # Group by campaign and calculate metrics
        campaign_stats = self.df.groupby('campaign_name').agg({
            'roas': 'mean',
            'ctr': 'mean',
            'cpc': 'mean',
            'spend': 'sum',
            'revenue': 'sum',
            'conversions': 'sum'
        }).reset_index()
        
        # Sort by metric
        ranked = campaign_stats.sort_values(metric, ascending=ascending)
        
        return {
            "status": "success",
            "rankings": ranked.to_dict('records')
        }
    
    def _get_metric_trends(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Get metric trends over time."""
        metric = parameters.get('metric', 'cpc')
        
        if self.df is None:
            raise ValueError("Data not loaded")
        
        if 'date' not in self.df.columns:
            return {"status": "error", "message": "No date column available"}
        
        # Convert date to datetime if needed
        if not pd.api.types.is_datetime64_any_dtype(self.df['date']):
            self.df['date'] = pd.to_datetime(self.df['date'])
        
        # Group by date and calculate metric
        trends = self.df.groupby(self.df['date'].dt.to_period('M'))[metric].mean().reset_index()
        trends['date'] = trends['date'].astype(str)
        
        return {
            "status": "success",
            "metric": metric,
            "trends": trends.to_dict('records')
        }
    
    def _generate_insights(self, summary: Dict[str, Any]) -> List[str]:
        """Use LLM to extract key insights from data summary."""
        try:
            messages = [
                {"role": "system", "content": self.prompt_template},
                {"role": "user", "content": f"""
Analyze this data summary and extract 5-7 key insights that would be valuable for a marketer:

{json.dumps(summary, indent=2)}

Provide insights as a JSON array of strings. Focus on:
- Performance trends
- Concerning patterns
- Opportunities
- Top and bottom performers
"""}
            ]
            
            response = self.llm_client.chat.completions.create(
                model=self.config['llm']['model'],
                messages=messages,
                temperature=0.5,
                response_format={"type": "json_object"}
            )
            
            insights_data = json.loads(response.choices[0].message.content)
            return insights_data.get('insights', [])
            
        except Exception as e:
            self.logger.log_error(self.name, f"Insight generation failed: {str(e)}")
            # Return basic insights from summary
            insights = [
                f"Dataset contains {summary.get('total_records', 0)} records",
                f"Average ROAS: {summary.get('metrics', {}).get('avg_roas', 0):.2f}",
                f"Average CTR: {summary.get('metrics', {}).get('avg_ctr', 0):.4f}"
            ]
            
            # Add top campaigns
            top_roas = summary.get('top_campaigns_by_roas', [])
            if top_roas:
                best = top_roas[0]
                insights.append(f"Best campaign by ROAS: {best['campaign']} ({best['roas']:.2f})")
            
            return insights
    
    def _filter_data(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Filter data based on criteria."""
        if self.df is None:
            raise ValueError("Data not loaded. Run load_and_summarize first.")
        
        metric = parameters.get('metric', 'ctr')
        threshold = parameters.get('threshold', 0.009)
        
        filtered_df = self.data_loader.filter_low_performers(metric, threshold)
        
        return {
            "status": "success",
            "filtered_count": len(filtered_df),
            "records": filtered_df.to_dict('records')[:100]  # Limit to 100 records
        }
    
    def _get_creative_patterns(self) -> Dict[str, Any]:
        """Extract creative message patterns."""
        if self.df is None:
            raise ValueError("Data not loaded.")
        
        patterns = self.data_loader.get_creative_patterns(top_n=20)
        
        return {
            "status": "success",
            "patterns": patterns
        }
    
    def get_dataframe(self):
        """Return the loaded dataframe."""
        return self.df
