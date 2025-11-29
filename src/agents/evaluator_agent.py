"""
Evaluator Agent - Validates hypotheses with statistical analysis.
"""

import json
import numpy as np
import pandas as pd
from typing import Dict, Any, List
from pathlib import Path
from scipy import stats


class EvaluatorAgent:
    """Validates hypotheses using statistical tests."""
    
    def __init__(self, config: Dict[str, Any], llm_client, logger):
        self.config = config
        self.llm_client = llm_client
        self.logger = logger
        self.prompt_template = self._load_prompt()
    
    def _load_prompt(self) -> str:
        """Load prompt template."""
        prompt_path = Path("prompts/evaluator_agent_prompt.md")
        if prompt_path.exists():
            return prompt_path.read_text()
        return "You are an Evaluator Agent. Validate hypotheses statistically."
    
    def validate_hypotheses(
        self,
        hypotheses: Dict[str, Any],
        dataframe: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Validate hypotheses with statistical analysis.
        
        Args:
            hypotheses: Hypotheses from Insight Agent
            dataframe: Full dataset for analysis
            
        Returns:
            Validation results with statistical evidence
        """
        self.logger.log_agent_action(
            "EvaluatorAgent",
            "validating_hypotheses",
            {"hypothesis_count": len(hypotheses.get('hypotheses', []))}
        )
        
        evaluations = []
        
        try:
            for hypothesis in hypotheses.get('hypotheses', []):
                evaluation = self._validate_single_hypothesis(hypothesis, dataframe)
                evaluations.append(evaluation)
            
            # Use LLM for final assessment
            final_assessment = self._generate_assessment(evaluations)
            
            result = {
                "evaluations": evaluations,
                "overall_assessment": final_assessment,
                "validated_count": sum(1 for e in evaluations if e['verdict'] == 'VALIDATED'),
                "total_count": len(evaluations)
            }
            
            self.logger.log_agent_action(
                "EvaluatorAgent",
                "validation_complete",
                {"validated": result['validated_count']},
                status="success"
            )
            
            return result
            
        except Exception as e:
            self.logger.log_error("EvaluatorAgent", str(e))
            raise
    
    def _validate_single_hypothesis(
        self,
        hypothesis: Dict[str, Any],
        df: pd.DataFrame
    ) -> Dict[str, Any]:
        """Validate a single hypothesis with statistical tests."""
        
        hypothesis_text = hypothesis.get('hypothesis', '')
        hypothesis_id = hypothesis.get('id', 'unknown')
        
        # Perform statistical tests based on hypothesis content
        tests_performed = []
        quantitative_evidence = {}
        
        # Example: Test if Video has lower CTR
        if 'video' in hypothesis_text.lower() and 'ctr' in hypothesis_text.lower():
            video_ctr = df[df['creative_type'] == 'Video']['ctr'].dropna()
            other_ctr = df[df['creative_type'] != 'Video']['ctr'].dropna()
            
            if len(video_ctr) > 0 and len(other_ctr) > 0:
                t_stat, p_value = stats.ttest_ind(video_ctr, other_ctr)
                
                tests_performed.append({
                    "test": "Two-sample t-test",
                    "comparison": "Video CTR vs Other formats CTR",
                    "result": f"p-value = {p_value:.4f}",
                    "interpretation": "Statistically significant" if p_value < 0.05 else "Not significant"
                })
                
                quantitative_evidence = {
                    "video_avg_ctr": float(video_ctr.mean()),
                    "other_avg_ctr": float(other_ctr.mean()),
                    "difference_pct": float((video_ctr.mean() - other_ctr.mean()) / other_ctr.mean() * 100),
                    "p_value": float(p_value)
                }
        
        # Example: Test if ROAS declined over time
        if 'roas' in hypothesis_text.lower() and ('decline' in hypothesis_text.lower() or 'drop' in hypothesis_text.lower()):
            df_sorted = df.sort_values('date')
            first_half = df_sorted.head(len(df_sorted)//2)['roas'].dropna()
            second_half = df_sorted.tail(len(df_sorted)//2)['roas'].dropna()
            
            if len(first_half) > 0 and len(second_half) > 0:
                t_stat, p_value = stats.ttest_ind(first_half, second_half)
                
                tests_performed.append({
                    "test": "Two-sample t-test (time periods)",
                    "comparison": "First half ROAS vs Second half ROAS",
                    "result": f"p-value = {p_value:.4f}",
                    "interpretation": "Statistically significant" if p_value < 0.05 else "Not significant"
                })
                
                quantitative_evidence['first_half_roas'] = float(first_half.mean())
                quantitative_evidence['second_half_roas'] = float(second_half.mean())
                quantitative_evidence['change_pct'] = float((second_half.mean() - first_half.mean()) / first_half.mean() * 100)
        
        # Determine verdict
        if tests_performed and any(t.get('interpretation') == 'Statistically significant' for t in tests_performed):
            verdict = "VALIDATED"
            confidence = min(0.95, hypothesis.get('confidence', 0.7) * 1.1)
        elif tests_performed:
            verdict = "PARTIALLY VALIDATED"
            confidence = hypothesis.get('confidence', 0.5) * 0.8
        else:
            verdict = "INSUFFICIENT DATA"
            confidence = 0.4
        
        return {
            "hypothesis_id": hypothesis_id,
            "verdict": verdict,
            "confidence": confidence,
            "statistical_tests": tests_performed,
            "quantitative_evidence": quantitative_evidence,
            "validation_notes": self._generate_validation_notes(verdict, tests_performed),
            "recommendation": self._get_recommendation(verdict)
        }
    
    def _generate_validation_notes(self, verdict: str, tests: List[Dict]) -> str:
        """Generate human-readable validation notes."""
        if verdict == "VALIDATED":
            return "Strong statistical evidence supports this hypothesis."
        elif verdict == "PARTIALLY VALIDATED":
            return "Some evidence supports this hypothesis, but confidence is moderate."
        else:
            return "Insufficient data to validate this hypothesis conclusively."
    
    def _get_recommendation(self, verdict: str) -> str:
        """Get action recommendation based on verdict."""
        recommendations = {
            "VALIDATED": "ACCEPT - Act on this insight",
            "PARTIALLY VALIDATED": "MONITOR - Consider additional validation",
            "NOT VALIDATED": "REJECT - Look for alternative explanations",
            "INSUFFICIENT DATA": "COLLECT MORE DATA"
        }
        return recommendations.get(verdict, "REVIEW")
    
    def _generate_assessment(self, evaluations: List[Dict]) -> str:
        """Generate overall assessment using LLM."""
        try:
            messages = [
                {"role": "system", "content": self.prompt_template},
                {"role": "user", "content": f"""
Based on these hypothesis validations, provide a 2-3 sentence overall assessment:

{json.dumps(evaluations, indent=2)}

Focus on: what was validated, what needs more investigation, and overall confidence in findings.
"""}
            ]
            
            response = self.llm_client.chat.completions.create(
                model=self.config['llm']['model'],
                messages=messages,
                temperature=0.5,
                max_tokens=200
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            validated_count = sum(1 for e in evaluations if e['verdict'] == 'VALIDATED')
            return f"{validated_count} out of {len(evaluations)} hypotheses validated with statistical evidence."
