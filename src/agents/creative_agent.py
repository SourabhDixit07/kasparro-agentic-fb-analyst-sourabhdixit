"""
Creative Agent - Uses LLM trained knowledge + YOUR historical data.
FIXED: Now uses percentile-based filtering instead of fixed thresholds
"""

import json
import re
import pandas as pd
from typing import Dict, Any, List
from pathlib import Path


class CreativeAgent:
    """Generates creative message recommendations using LLM + historical data."""
    
    def __init__(self, config: Dict[str, Any], llm_client, logger):
        self.config = config
        self.llm_client = llm_client
        self.logger = logger
        self.prompt_template = self._load_prompt()
    
    def _load_prompt(self) -> str:
        """Load prompt template."""
        prompt_path = Path("prompts/creative_agent_prompt.md")
        if prompt_path.exists():
            return prompt_path.read_text()
        return "You are a Creative Agent. Generate new creative recommendations."
    
    def generate_recommendations(self, dataframe: pd.DataFrame) -> Dict[str, Any]:
        """Generate recommendations using LLM + historical data."""
        
        self.logger.log_agent_action("CreativeAgent", "generating_recommendations", {})
        
        try:
            # ✅ FIX: Use percentile instead of fixed threshold
            # Get bottom 20% of campaigns by CTR
            low_ctr_threshold = dataframe['ctr'].quantile(0.20)
            low_performers_df = dataframe[dataframe['ctr'] <= low_ctr_threshold].copy()
            
            # ✅ FIX: Ensure we have at least 10 campaigns
            if len(low_performers_df) < 10:
                # Take bottom 10 campaigns by absolute ranking
                low_performers_df = dataframe.nsmallest(10, 'ctr').copy()
            
            if len(low_performers_df) == 0:
                # This should never happen now, but keep as safety
                return {"low_performers": [], "recommendations": [], "message": "No campaigns in dataset"}
            
            # Analyze what works in YOUR data
            performance_insights = self._analyze_historical_patterns(dataframe)
            
            # Get unique campaigns (one row per campaign)
            low_sample = low_performers_df.groupby('campaign_name').first().reset_index().head(10)
            
            low_performers_data = []
            for idx, row in low_sample.iterrows():
                low_performers_data.append({
                    "campaign": row['campaign_name'],
                    "current_message": row['creative_message'],
                    "current_ctr": float(row['ctr']),
                    "creative_type": row.get('creative_type', 'Unknown'),
                    "audience_type": row.get('audience_type', 'Unknown')
                })
            
            # Try LLM first
            recommendations = self._generate_with_llm(
                low_performers_data,
                performance_insights
            )
            
            # If LLM fails, use data-driven fallback
            if not recommendations or 'recommendations' not in recommendations:
                print("⚠️  LLM failed, using data-driven fallback")
                recommendations = self._generate_from_data_only(
                    low_performers_data,
                    performance_insights
                )
            
            self.logger.log_agent_action(
                "CreativeAgent",
                "recommendations_generated",
                {"campaigns_analyzed": len(low_performers_data)},
                status="success"
            )
            
            return recommendations
            
        except Exception as e:
            self.logger.log_error("CreativeAgent", str(e))
            return {"recommendations": [], "error": str(e)}
    
    def _analyze_historical_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze YOUR data to find what works."""
        
        # Get top 25% performing ads
        high_ctr_threshold = df['ctr'].quantile(0.75)
        top_performers = df[df['ctr'] >= high_ctr_threshold].copy()
        
        insights = {
            "best_performing_messages": [],
            "successful_patterns": {},
            "avg_ctr": float(df['ctr'].mean()),
            "median_ctr": float(df['ctr'].median())
        }
        
        if len(top_performers) > 0:
            # Get top 10 messages
            top_msgs = top_performers.nlargest(10, 'ctr')[['creative_message', 'ctr']]
            insights["best_performing_messages"] = top_msgs.to_dict('records')
            
            # Extract patterns from successful messages
            insights["successful_patterns"] = self._extract_text_patterns(
                top_performers['creative_message'].tolist()
            )
        
        return insights
    
    def _extract_text_patterns(self, messages: List[str]) -> Dict[str, int]:
        """Find patterns in successful messages."""
        
        patterns = {
            "urgency": 0,
            "discount": 0,
            "social_proof": 0,
            "comfort": 0,
            "quality": 0
        }
        
        for msg in messages:
            msg_lower = msg.lower()
            
            # Urgency indicators
            if any(w in msg_lower for w in ['tonight', 'now', 'limited', 'ends', '24', 'last chance']):
                patterns["urgency"] += 1
            
            # Discount indicators
            if any(w in msg_lower for w in ['%', 'off', 'deal', 'sale', 'discount']):
                patterns["discount"] += 1
            
            # Social proof
            if any(w in msg_lower for w in ['best', 'rated', 'love', 'customers', 'doctors', 'recommend']):
                patterns["social_proof"] += 1
            
            # Comfort/quality
            if any(w in msg_lower for w in ['comfort', 'soft', 'breathable', 'cotton', 'seamless']):
                patterns["comfort"] += 1
                
            if any(w in msg_lower for w in ['premium', 'quality', 'signature', 'bold']):
                patterns["quality"] += 1
        
        return patterns
    
    def _generate_with_llm(self, low_performers: List[Dict], insights: Dict[str, Any]) -> Dict[str, Any]:
        """Use LLM with YOUR data as context."""
        
        best_ads = insights.get("best_performing_messages", [])
        
        if best_ads:
            best_ads_text = "\n".join([
                f"- \"{ad['creative_message']}\" (CTR: {ad['ctr']:.2%})"
                for ad in best_ads[:5]
            ])
        else:
            best_ads_text = "No high-performing ads available"
        
        patterns = insights.get("successful_patterns", {})
        pattern_text = f"""
Your successful ads have these patterns:
- {patterns.get('urgency', 0)} use urgency words (tonight, limited, ends)
- {patterns.get('discount', 0)} mention discounts (%, off, sale)
- {patterns.get('social_proof', 0)} use social proof (doctors, best-rated)
- {patterns.get('comfort', 0)} emphasize comfort (soft, breathable)
- {patterns.get('quality', 0)} highlight quality (premium, signature)
"""
        
        avg_ctr = insights.get("avg_ctr", 0.013)
        
        user_prompt = f"""You are an expert Facebook ads copywriter.

CLIENT'S TOP PERFORMING ADS (Learn from these):
{best_ads_text}

{pattern_text}

Average CTR in dataset: {avg_ctr:.2%}

CAMPAIGNS TO FIX (need new ad copy):
{json.dumps(low_performers[:3], indent=2)}

Generate 3 new ad messages for EACH campaign above. Return ONLY valid JSON (no markdown):
{{
  "recommendations": [
    {{
      "campaign": "Campaign Name",
      "current_ctr": 0.0076,
      "issue": "Why current ad fails",
      "new_messages": [
        {{
          "message": "New ad copy here",
          "strategy": "Why this will work based on top ads",
          "expected_ctr": "1.2-1.5%"
        }},
        {{
          "message": "Second option",
          "strategy": "Alternative approach",
          "expected_ctr": "1.0-1.3%"
        }},
        {{
          "message": "Third option",
          "strategy": "Another variant",
          "expected_ctr": "1.1-1.4%"
        }}
      ]
    }}
  ]
}}
"""
        
        try:
            response = self.llm_client.chat.completions.create(
                model=self.config['llm']['model'],
                messages=[
                    {"role": "system", "content": self.prompt_template},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content.strip()
            
            # Clean markdown formatting
            content = self._clean_markdown(content)
            
            # Extract JSON
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                content = json_match.group()
            
            recommendations = json.loads(content)
            
            if 'recommendations' in recommendations and len(recommendations['recommendations']) > 0:
                return recommendations
            else:
                return None
            
        except Exception as e:
            print(f"⚠️  LLM generation failed: {e}")
            return None
    
    def _clean_markdown(self, text: str) -> str:
        """Remove markdown formatting from LLM response."""
        # Remove json code blocks
        if "json" in text and text.count('"') > 10:
            lines = text.split('\n')
            clean_lines = []
            skip = False
            for line in lines:
                if 'json' in line.lower() and len(line) < 10:
                    skip = True
                    continue
                if skip and line.strip() and line.strip()[0] == '{':
                    skip = False
                if not skip:
                    clean_lines.append(line)
            text = '\n'.join(clean_lines)
        return text.strip()
    
    def _generate_from_data_only(self, low_performers: List[Dict], insights: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback: Use only YOUR data if LLM fails."""
        
        recommendations = []
        best_ads = insights.get("best_performing_messages", [])
        
        if not best_ads or len(best_ads) == 0:
            # No historical data - return generic recommendations
            return {
                "recommendations": [{
                    "campaign": "General Recommendation",
                    "issue": "No historical data available for comparison",
                    "new_messages": [{
                        "message": "Test discount + urgency: 'Limited time: 20% off - Shop now!'",
                        "strategy": "Industry standard approach combining urgency and discount",
                        "expected_ctr": "1.0-1.5%"
                    }]
                }]
            }
        
        # Generate recommendations based on YOUR best ads
        for campaign_data in low_performers[:5]:
            product = self._extract_product(campaign_data['current_message'])
            
            new_messages = []
            for i, top_ad in enumerate(best_ads[:3]):
                adapted = self._adapt_message(top_ad['creative_message'], product)
                expected_improvement = top_ad['ctr'] * 0.7  # Expect 70% of top performer's CTR
                
                new_messages.append({
                    "message": adapted,
                    "strategy": f"Adapted from your top ad (CTR: {top_ad['ctr']:.2%})",
                    "expected_ctr": f"{expected_improvement:.2%}"
                })
            
            recommendations.append({
                "campaign": campaign_data['campaign'],
                "current_ctr": campaign_data['current_ctr'],
                "issue": f"Current CTR {campaign_data['current_ctr']:.2%} is below average",
                "new_messages": new_messages
            })
        
        return {"recommendations": recommendations}
    
    def _extract_product(self, message: str) -> str:
        """Extract product type from message."""
        msg_lower = message.lower()
        
        if 'bra' in msg_lower:
            return 'bras'
        elif 'boxer' in msg_lower:
            return 'boxers'
        elif 'brief' in msg_lower:
            return 'briefs'
        elif 'trunk' in msg_lower:
            return 'trunks'
        elif 'panties' in msg_lower or 'pantie' in msg_lower:
            return 'panties'
        elif 'vest' in msg_lower:
            return 'vests'
        
        return 'underwear'
    
    def _adapt_message(self, successful_msg: str, new_product: str) -> str:
        """Adapt winning message to different product."""
        products = ['bras', 'boxers', 'briefs', 'trunks', 'panties', 'vests', 'underwear']
        result = successful_msg
        
        for prod in products:
            if prod in successful_msg.lower():
                result = re.sub(rf'\b{prod}\b', new_product, result, flags=re.IGNORECASE)
                break
        
        return result
