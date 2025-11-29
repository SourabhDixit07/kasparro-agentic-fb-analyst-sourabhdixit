"""
Agent Orchestrator - Coordinates all agents and manages workflow.
FIXED: Correct key names, better logging, query routing
"""

import json
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from src.agents import (
    PlannerAgent,
    DataAgent,
    InsightAgent,
    EvaluatorAgent,
    CreativeAgent
)


class AgentOrchestrator:
    """Orchestrates multi-agent workflow."""
    
    def __init__(self, config: Dict[str, Any], llm_client, logger):
        self.config = config
        self.llm_client = llm_client
        self.logger = logger
        
        # Initialize all agents
        self.planner = PlannerAgent(config, llm_client, logger)
        self.data_agent = DataAgent(config, llm_client, logger)
        self.insight_agent = InsightAgent(config, llm_client, logger)
        self.evaluator_agent = EvaluatorAgent(config, llm_client, logger)
        self.creative_agent = CreativeAgent(config, llm_client, logger)
        
        # Storage for intermediate results
        self.user_query = None
        self.plan = None
        self.data_summary = None
        self.insights = None
        self.evaluations = None
        self.creatives = None
    
    def run(self, user_query: str) -> Dict[str, Any]:
        """
        Execute full multi-agent workflow.
        
        Args:
            user_query: User's question or request
            
        Returns:
            Complete analysis results
        """
        self.user_query = user_query  # Store query
        
        self.logger.log_agent_action(
            "Orchestrator",
            "workflow_started",
            {"query": user_query}
        )
        
        try:
            # Step 1: Planning
            print("\n🧠 STEP 1: Planning...")
            self.plan = self.planner.plan(user_query)
            print(f"   ✓ Created plan with {len(self.plan.get('subtasks', []))} subtasks")
            
            # Step 2: Data Loading
            print("\n📊 STEP 2: Loading & Analyzing Data...")
            data_result = self.data_agent.execute("load_and_summarize")
            self.data_summary = data_result['summary']
            print(f"   ✓ Loaded {self.data_summary['total_records']} records")
            print(f"   ✓ Date range: {self.data_summary['date_range']['start']} to {self.data_summary['date_range']['end']}")
            
            # Step 3: Insight Generation (NOW QUERY-AWARE)
            print("\n💡 STEP 3: Generating Hypotheses...")
            self.insights = self.insight_agent.generate_hypotheses(data_result, user_query)  # Pass query
            hypothesis_count = len(self.insights.get('hypotheses', []))
            print(f"   ✓ Generated {hypothesis_count} hypotheses")
            for i, h in enumerate(self.insights.get('hypotheses', [])[:3], 1):
                print(f"   {i}. {h.get('hypothesis', 'N/A')} (confidence: {h.get('confidence', 0):.2f})")
            
            # Step 4: Validation
            print("\n✅ STEP 4: Validating Hypotheses...")
            dataframe = self.data_agent.get_dataframe()
            self.evaluations = self.evaluator_agent.validate_hypotheses(
                self.insights,
                dataframe
            )
            validated_count = self.evaluations.get('validated_count', 0)
            print(f"   ✓ Validated {validated_count}/{hypothesis_count} hypotheses")
            
            # Step 5: Creative Recommendations
            print("\n✨ STEP 5: Generating Creative Recommendations...")
            self.creatives = self.creative_agent.generate_recommendations(dataframe)
            
            # ✅ FIX: Use correct key name
            creative_count = len(self.creatives.get('recommendations', []))
            print(f"   ✓ Generated recommendations for {creative_count} campaigns")
            
            # Step 6: Save Results
            print("\n💾 STEP 6: Saving Results...")
            self._save_outputs()
            print("   ✓ Saved insights.json")
            print("   ✓ Saved creatives.json")
            print("   ✓ Saved report.md")
            
            # Compile final results
            results = {
                "query": user_query,
                "plan": self.plan,
                "data_summary": self.data_summary,
                "insights": self.insights,
                "evaluations": self.evaluations,
                "creatives": self.creatives,
                "status": "success"
            }
            
            self.logger.log_agent_action(
                "Orchestrator",
                "workflow_completed",
                {"status": "success"},
                status="success"
            )
            
            print("\n✅ Analysis complete! Check the reports/ folder for outputs.")
            
            return results
            
        except Exception as e:
            self.logger.log_error("Orchestrator", str(e))
            print(f"\n❌ Error: {str(e)}")
            raise
    
    def _save_outputs(self):
        """Save all outputs to files."""
        reports_dir = Path(self.config['output']['reports_dir'])
        reports_dir.mkdir(exist_ok=True)
        
        # ✅ NEW: Create archives directory
        archives_dir = reports_dir / "archives"
        archives_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save insights.json
        if self.config['output']['save_insights'] and self.insights:
            insights_data = {
                "hypotheses": self.insights.get('hypotheses', []),
                "evaluations": self.evaluations.get('evaluations', []),
                "overall_assessment": self.evaluations.get('overall_assessment', '')
            }
            
            insights_path = reports_dir / "insights.json"
            with open(insights_path, 'w') as f:
                json.dump(insights_data, f, indent=2)
            
            # Archive copy
            archive_path = archives_dir / f"{timestamp}_insights.json"
            with open(archive_path, 'w') as f:
                json.dump(insights_data, f, indent=2)
        
        # Save creatives.json
        if self.config['output']['save_creatives'] and self.creatives:
            creatives_path = reports_dir / "creatives.json"
            with open(creatives_path, 'w') as f:
                json.dump(self.creatives, f, indent=2)
            
            # Archive copy
            archive_path = archives_dir / f"{timestamp}_creatives.json"
            with open(archive_path, 'w') as f:
                json.dump(self.creatives, f, indent=2)
        
        # Save report.md
        if self.config['output']['save_report']:
            report_content = self._generate_markdown_report()
            
            report_path = reports_dir / "report.md"
            with open(report_path, 'w') as f:
                f.write(report_content)
            
            # Archive copy
            archive_path = archives_dir / f"{timestamp}_report.md"
            with open(archive_path, 'w') as f:
                f.write(report_content)
    
    def _generate_markdown_report(self) -> str:
        """Generate human-readable markdown report."""
        timestamp = datetime.now().isoformat()
        
        report = f"# Facebook Ads Performance Analysis Report\n\n"
        report += f"**Query:** {self.user_query}\n\n"
        report += f"**Generated:** {timestamp}\n\n"
        report += "## Executive Summary\n\n"
        report += "### Key Findings\n\n"
        
        # Add validated hypotheses
        if self.evaluations:
            validated = [e for e in self.evaluations.get('evaluations', []) if e['verdict'] == 'VALIDATED']
            report += f"**Validated Insights:** {len(validated)} out of {len(self.evaluations.get('evaluations', []))}\n\n"
            
            for i, eval_data in enumerate(validated, 1):
                hyp = next((h for h in self.insights.get('hypotheses', []) if h['id'] == eval_data['hypothesis_id']), {})
                report += f"{i}. **{hyp.get('hypothesis', 'N/A')}**\n"
                report += f"   - Confidence: {eval_data['confidence']:.0%}\n"
                report += f"   - Evidence: {eval_data['validation_notes']}\n\n"
        
        # Add data summary
        report += "\n## Data Overview\n\n"
        if self.data_summary:
            report += f"- **Records Analyzed:** {self.data_summary['total_records']:,}\n"
            report += f"- **Date Range:** {self.data_summary['date_range']['start']} to {self.data_summary['date_range']['end']}\n"
            report += f"- **Average ROAS:** {self.data_summary['metrics']['avg_roas']:.2f}\n"
            report += f"- **Average CTR:** {self.data_summary['metrics']['avg_ctr']:.2%}\n"
        
        # ✅ FIX: Use correct key name and show actual recommendations
        report += "\n## Creative Recommendations\n\n"
        if self.creatives and 'recommendations' in self.creatives:
            recommendations = self.creatives['recommendations']
            
            if len(recommendations) > 0:
                for rec in recommendations[:5]:  # Show top 5
                    report += f"### Campaign: {rec.get('campaign', 'N/A')}\n\n"
                    report += f"**Current Performance:** {rec.get('current_ctr', 0):.2%} CTR\n"
                    report += f"**Issue:** {rec.get('issue', 'N/A')}\n\n"
                    report += "**Recommended New Messages:**\n\n"
                    
                    for i, msg in enumerate(rec.get('new_messages', []), 1):
                        report += f"{i}. \"{msg.get('message', 'N/A')}\"\n"
                        report += f"   - Strategy: {msg.get('strategy', 'N/A')}\n"
                        report += f"   - Expected CTR: {msg.get('expected_ctr', 'N/A')}\n\n"
            else:
                report += "*No recommendations generated (all campaigns performing well)*\n\n"
        else:
            report += "*Creative recommendations not available*\n\n"
        
        report += "\n## Next Steps\n\n"
        report += "1. Review validated hypotheses and prioritize actions\n"
        report += "2. Test recommended creative messages in A/B tests\n"
        report += "3. Monitor performance changes over next 2-4 weeks\n"
        report += "4. Re-run analysis to measure improvement\n"
        
        return report
