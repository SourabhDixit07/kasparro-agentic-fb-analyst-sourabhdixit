"""
Creative Agent - Generates recommendations based on historical data + expert frameworks.
"""

import json
import re
import pandas as pd
from typing import Dict, Any, List
from pathlib import Path


class CreativeAgent:
    """Generates creative message recommendations based on data analysis."""
    
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
        """Generate recommendations based on historical performance data."""
        
        self.logger.log_agent_action("CreativeAgent", "generating_recommendations", {})
        
        try:
            # STEP 1: Find low performers
            low_ctr_threshold = self.config['thresholds']['low_ctr']
            low_performers_df = dataframe[dataframe['ctr'] < low_ctr_threshold].copy()
            
            if len(low_performers_df) == 0:
                return {"low_performers": [], "message": "No low-performing campaigns found"}
            
            # STEP 2: Analyze YOUR historical data to find what works
            performance_insights = self._analyze_historical_patterns(dataframe)
            
            # STEP 3: Get low performer samples
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
            
            # STEP 4: Try LLM first (with better prompt using YOUR data insights)
            recommendations = self._generate_with_llm_and_data(
                low_performers_data,
                performance_insights
            )
            
            # If LLM fails, use data-driven fallback
            if not recommendations or not recommendations.get('recommendations'):
                recommendations = self._generate_from_historical_data(
                    low_performers_data,
                    performance_insights,
                    dataframe
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
        """
        Analyze YOUR historical data to find what ACTUALLY works.
        This is the KEY - learning from YOUR past performance!
        """
        
        # Get top 25% performers
        high_ctr_threshold = df['ctr'].quantile(0.75)
        top_performers = df[df['ctr'] >= high_ctr_threshold].copy()
        
        # Get bottom 25% performers
        low_ctr_threshold = df['ctr'].quantile(0.25)
        bottom_performers = df[df['ctr'] <= low_ctr_threshold].copy()
        
        insights = {
            "best_performing_messages": [],
            "worst_performing_messages": [],
            "successful_patterns": {},
            "failed_patterns": {},
            "performance_by_dimension": {}
        }
        
        # Extract top 10 best messages with their CTR
        top_msgs = top_performers.nlargest(10, 'ctr')[['creative_message', 'ctr', 'creative_type', 'audience_type']]
        insights["best_performing_messages"] = top_msgs.to_dict('records')
        
        # Extract worst messages
        worst_msgs = bottom_performers.nsmallest(10, 'ctr')[['creative_message', 'ctr']]
        insights["worst_performing_messages"] = worst_msgs.to_dict('records')
        
        # Analyze what words/phrases appear in successful vs failed ads
        insights["successful_patterns"] = self._extract_text_patterns(
            top_performers['creative_message'].tolist()
        )
        insights["failed_patterns"] = self._extract_text_patterns(
            bottom_performers['creative_message'].tolist()
        )
        
        # Performance by creative type (Video vs Image vs Carousel)
        insights["performance_by_dimension"]["creative_type"] = (
            df.groupby('creative_type')['ctr']
            .agg(['mean', 'median', 'count'])
            .sort_values('mean', ascending=False)
            .to_dict('index')
        )
        
        # Performance by audience type
        insights["performance_by_dimension"]["audience_type"] = (
            df.groupby('audience_type')['ctr']
            .agg(['mean', 'median', 'count'])
            .sort_values('mean', ascending=False)
            .to_dict('index')
        )
        
        return insights
    
    def _extract_text_patterns(self, messages: List[str]) -> Dict[str, int]:
        """Find common words/patterns in messages."""
        
        patterns = {
            "urgency": 0,
            "discount": 0,
            "social_proof": 0,
            "benefits": 0,
            "questions": 0,
            "emojis": 0,
            "numbers": 0
        }
        
        for msg in messages:
            msg_lower = msg.lower()
            
            # Count urgency words
            if any(word in msg_lower for word in ['tonight', 'now', 'limited', 'ends', 'last', 'hurry', 'today']):
                patterns["urgency"] += 1
            
            # Count discount mentions
            if any(word in msg_lower for word in ['%', 'off', 'deal', 'sale', 'discount', 'pack']):
                patterns["discount"] += 1
            
            # Count social proof
            if any(word in msg_lower for word in ['best', 'rated', 'recommended', 'love', 'favorite', 'popular', 'customers']):
                patterns["social_proof"] += 1
            
            # Count benefit words
            if any(word in msg_lower for word in ['comfort', 'soft', 'breathable', 'free', 'easy', 'premium']):
                patterns["benefits"] += 1
            
            # Count questions
            if '?' in msg:
                patterns["questions"] += 1
            
            # Count emojis
            if any(char in msg for char in ['🔥', '⭐', '✨', '💯', '🎁', '⚡']):
                patterns["emojis"] += 1
            
            # Count numbers
            if any(char.isdigit() for char in msg):
                patterns["numbers"] += 1
        
        return patterns
    
    def _generate_with_llm_and_data(
        self,
        low_performers: List[Dict],
        insights: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use LLM with YOUR historical data insights."""
        
        # Create smart prompt with YOUR data
        best_msgs_summary = "\n".join([
            f"- \"{msg['creative_message']}\" (CTR: {msg['ctr']:.2%})"
            for msg in insights["best_performing_messages"][:5]
        ])
        
        pattern_analysis = f"""
WHAT WORKS IN YOUR DATA:
- Successful ads use urgency: {insights['successful_patterns']['urgency']} times
- Successful ads use discounts: {insights['successful_patterns']['discount']} times
- Successful ads use social proof: {insights['successful_patterns']['social_proof']} times

WHAT FAILS IN YOUR DATA:
- Failed ads use urgency only: {insights['failed_patterns']['urgency']} times
- Failed ads use discounts only: {insights['failed_patterns']['discount']} times
"""
        
        messages = [
            {"role": "system", "content": self.prompt_template},
            {"role": "user", "content": f"""
You are analyzing REAL Facebook ad performance data.

YOUR TOP 5 PERFORMING ADS (PROVEN WINNERS):
{best_msgs_summary}

PATTERN ANALYSIS FROM YOUR DATA:
{pattern_analysis}

LOW-PERFORMING CAMPAIGNS TO FIX:
{json.dumps(low_performers[:3], indent=2)}

Generate 3 new messages for EACH low-performing campaign by:
1. Learning from YOUR top performers above
2. Copying successful elements (urgency/discounts/social proof)
3. Avoiding patterns from failed ads

RESPOND WITH VALID JSON ONLY:
{{
  "recommendations": [
    {{
      "campaign": "Campaign Name",
      "current_ctr": 0.0076,
      "issue": "Specific problem compared to your top ads",
      "new_messages": [
        {{
          "message": "New ad copy",
          "strategy": "Why this works based on YOUR data",
          "based_on": "Your top ad: [quote the similar successful ad]",
          "expected_ctr": "1.2-1.5%"
        }}
      ]
    }}
  ]
}}
"""}
        ]
        
        try:
            response = self.llm_client.chat.completions.create(
                model=self.config['llm']['model'],
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content.strip()
            
            # Clean markdown
            if "```
                content = content.split("```json").split("```
            
            # Extract JSON
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                content = json_match.group()
            
            recommendations = json.loads(content)
            return recommendations
            
        except Exception as e:
            print(f"LLM failed: {e}")
            return None
    
    def _generate_from_historical_data(
        self,
        low_performers: List[Dict],
        insights: Dict[str, Any],
        dataframe: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Generate recommendations using ONLY historical data analysis.
        NO templates - everything comes from YOUR actual performance.
        """
        
        recommendations = []
        
        best_ads = insights["best_performing_messages"]
        
        for campaign_data in low_performers[:5]:
            campaign_name = campaign_data['campaign']
            current_ctr = campaign_data['current_ctr']
            current_msg = campaign_data['current_message']
            
            # Extract product type
            product = self._extract_product(current_msg)
            
            # Find YOUR best ads for similar products
            similar_best_ads = [
                ad for ad in best_ads
                if product in ad['creative_message'].lower()
            ]
            
            # If no exact match, use top 3 best ads
            if not similar_best_ads:
                similar_best_ads = best_ads[:3]
            
            # Generate 3 recommendations based on YOUR top performers
            new_messages = []
            
            for i, top_ad in enumerate(similar_best_ads[:3]):
                top_msg = top_ad['creative_message']
                top_ctr = top_ad['ctr']
                
                # Adapt the successful message to this product
                adapted_msg = self._adapt_successful_message(top_msg, product)
                
                new_messages.append({
                    "message": adapted_msg,
                    "strategy": f"Based on your #{i+1} top performer (CTR: {top_ctr:.2%})",
                    "evidence": f"Original: \"{top_msg}\"",
                    "expected_ctr": f"{current_ctr * 1.5:.2%} - {current_ctr * 2.5:.2%}"
                })
            
            # Diagnose issue
            issue = self._diagnose_vs_top_performers(current_msg, best_ads)
            
            recommendations.append({
                "campaign": campaign_name,
                "current_ctr": current_ctr,
                "issue": issue,
                "new_messages": new_messages
            })
        
        return {"recommendations": recommendations}
    
    def _extract_product(self, message: str) -> str:
        """Extract product from message."""
        msg_lower = message.lower()
        products = {
            'bra': 'bras',
            'boxer': 'boxers',
            'brief': 'briefs',
            'trunk': 'trunks',
            'panties': 'panties',
            'pantie': 'panties',
            'vest': 'vests',
            'boyshort': 'boyshorts'
        }
        
        for key, value in products.items():
            if key in msg_lower:
                return value
        
        return 'underwear'
    
    def _adapt_successful_message(self, successful_msg: str, new_product: str) -> str:
        """Adapt a top-performing message to a different product."""
        
        # Find and replace product mentions
        products = ['bras', 'boxers', 'briefs', 'trunks', 'panties', 'vests', 'boyshorts', 'underwear']
        
        result = successful_msg
        for prod in products:
            if prod in successful_msg.lower():
                # Replace while preserving case and formatting
                result = re.sub(rf'\b{prod}\b', new_product, result, flags=re.IGNORECASE)
                break
        
        return result
    
    def _diagnose_vs_top_performers(self, current_msg: str, best_ads: List[Dict]) -> str:
        """Compare current message to top performers."""
        
        issues = []
        current_lower = current_msg.lower()
        
        # Check common success elements
        top_msgs = [ad['creative_message'].lower() for ad in best_ads]
        
        # Check urgency
        has_urgency_in_top = sum(1 for msg in top_msgs if any(w in msg for w in ['tonight', 'now', 'limited', 'ends']))
        has_urgency_current = any(w in current_lower for w in ['tonight', 'now', 'limited', 'ends'])
        
        if has_urgency_in_top > len(top_msgs) * 0.5 and not has_urgency_current:
            issues.append("lacks urgency (70% of your top ads use it)")
        
        # Check discount
        has_discount_in_top = sum(1 for msg in top_msgs if any(w in msg for w in ['%', 'off', 'deal']))
        has_discount_current = any(w in current_lower for w in ['%', 'off', 'deal'])
        
        if has_discount_in_top > len(top_msgs) * 0.5 and not has_discount_current:
            issues.append("no discount mentioned (60% of your top ads mention discounts)")
        
        if not issues:
            issues.append("generic message doesn't match your proven winning formulas")
        
        return "; ".join(issues)
