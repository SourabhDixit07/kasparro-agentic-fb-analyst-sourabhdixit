"""
Data loader utility for Facebook Ads dataset.
Handles loading, cleaning, and summarizing data.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional


class DataLoader:
    """Load and preprocess Facebook Ads data."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.df: Optional[pd.DataFrame] = None
        self.summary: Dict[str, Any] = {}
    
    def load_data(self) -> pd.DataFrame:
        """Load dataset from CSV."""
        data_path = Path(self.config['data']['dataset_path'])
        
        if not data_path.exists():
            raise FileNotFoundError(f"Dataset not found at {data_path}")
        
        self.df = pd.read_csv(data_path)
        
        # Map column names to expected format
        column_mapping = {
            'adset_name': 'ad_set_name',
            'purchases': 'conversions'
        }
        self.df = self.df.rename(columns=column_mapping)
        
        # Add missing columns if needed
        if 'age_group' not in self.df.columns:
            self.df['age_group'] = 'Unknown'
        if 'gender' not in self.df.columns:
            self.df['gender'] = 'Unknown'
        
        # Convert date to datetime
        self.df['date'] = pd.to_datetime(self.df['date'], format='%d-%m-%Y')
        
        # Sample mode for testing
        if self.config['data']['sample_mode']:
            sample_size = self.config['data']['sample_size']
            self.df = self.df.sample(n=min(sample_size, len(self.df)), random_state=42)
        
        return self.df
    
    def clean_data(self) -> pd.DataFrame:
        """Clean and prepare data."""
        if self.df is None:
            raise ValueError("Data not loaded. Call load_data() first.")
        
        # Handle missing values
        # For numerical columns, we'll keep NaN for now (agents can handle it)
        # Remove rows where critical columns are missing
        self.df = self.df.dropna(subset=['date', 'campaign_name'], how='any')
        
        return self.df
    
    def generate_summary(self) -> Dict[str, Any]:
        """Generate comprehensive data summary."""
        if self.df is None:
            raise ValueError("Data not loaded. Call load_data() first.")
        
        df = self.df
        
        # Basic stats
        self.summary = {
            "total_records": len(df),
            "date_range": {
                "start": df['date'].min().strftime('%Y-%m-%d'),
                "end": df['date'].max().strftime('%Y-%m-%d'),
                "days": (df['date'].max() - df['date'].min()).days
            },
            "dimensions": {
                "unique_campaigns": df['campaign_name'].nunique(),
                "unique_adsets": df['ad_set_name'].nunique(),
                "countries": df['country'].unique().tolist(),
                "platforms": df['platform'].unique().tolist(),
                "creative_types": df['creative_type'].unique().tolist(),
                "audience_types": df['audience_type'].unique().tolist()
            },
            "metrics": {
                "total_spend": float(df['spend'].sum()),
                "total_impressions": int(df['impressions'].sum()),
                "total_clicks": int(df['clicks'].sum()),
                "total_conversions": int(df['conversions'].sum()),
                "total_revenue": float(df['revenue'].sum()),
                "avg_ctr": float(df['ctr'].mean()),
                "avg_roas": float(df['roas'].mean()),
                "median_roas": float(df['roas'].median())
            },
            "data_quality": {
                "missing_spend": int(df['spend'].isna().sum()),
                "missing_clicks": int(df['clicks'].isna().sum()),
                "missing_revenue": int(df['revenue'].isna().sum()),
                "zero_roas_records": int((df['roas'] == 0).sum())
            },
            "performance_by_segment": {
                "by_country": df.groupby('country')['roas'].agg(['mean', 'median', 'count']).to_dict(),
                "by_platform": df.groupby('platform')['roas'].agg(['mean', 'median', 'count']).to_dict(),
                "by_creative_type": df.groupby('creative_type')['roas'].agg(['mean', 'median', 'count']).to_dict(),
                "by_audience_type": df.groupby('audience_type')['roas'].agg(['mean', 'median', 'count']).to_dict()
            }
        }
        
        return self.summary
    
    def filter_low_performers(self, metric: str = 'ctr', threshold: float = 0.009) -> pd.DataFrame:
        """Filter campaigns/adsets with low performance."""
        if self.df is None:
            raise ValueError("Data not loaded.")
        
        if metric == 'ctr':
            return self.df[self.df['ctr'] < threshold].copy()
        elif metric == 'roas':
            return self.df[self.df['roas'] < threshold].copy()
        else:
            raise ValueError(f"Unknown metric: {metric}")
    
    def get_creative_patterns(self, top_n: int = 20) -> Dict[str, Any]:
        """Extract creative message patterns and performance."""
        if self.df is None:
            raise ValueError("Data not loaded.")
        
        creative_performance = self.df.groupby('creative_message').agg({
            'spend': 'sum',
            'impressions': 'sum',
            'clicks': 'sum',
            'conversions': 'sum',
            'revenue': 'sum',
            'ctr': 'mean',
            'roas': 'mean'
        }).reset_index()
        
        # Sort by spend to get most significant creatives
        creative_performance = creative_performance.sort_values('spend', ascending=False).head(top_n)
        
        return creative_performance.to_dict('records')
    
    def get_segment_comparison(self, dimension: str) -> pd.DataFrame:
        """Compare performance across a dimension."""
        if self.df is None:
            raise ValueError("Data not loaded.")
        
        valid_dimensions = ['country', 'platform', 'creative_type', 'audience_type', 'campaign_name']
        
        if dimension not in valid_dimensions:
            raise ValueError(f"Invalid dimension. Choose from: {valid_dimensions}")
        
        comparison = self.df.groupby(dimension).agg({
            'spend': 'sum',
            'revenue': 'sum',
            'roas': ['mean', 'median'],
            'ctr': ['mean', 'median'],
            'impressions': 'sum',
            'clicks': 'sum',
            'conversions': 'sum'
        }).reset_index()
        
        # Flatten column names
        comparison.columns = ['_'.join(col).strip('_') for col in comparison.columns.values]
        
        return comparison
