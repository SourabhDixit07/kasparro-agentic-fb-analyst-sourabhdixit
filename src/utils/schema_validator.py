"""
Schema Validator - Validates dataset structure and data types.
P0 REQUIREMENT: Upfront validation to prevent runtime failures
"""

import pandas as pd
from typing import Dict, List, Tuple, Any
from pathlib import Path


class SchemaValidator:
    """Validates dataset schema and data quality."""
    
    # Required columns that MUST exist (✅ FIXED to match actual CSV)
    REQUIRED_COLUMNS = [
        'date',
        'campaign_name',
        'adset_name',  # ✅ Changed from 'ad_set_name'
        'creative_message',
        'platform',
        'audience_type',
        'creative_type',
        'impressions',
        'clicks',
        'spend',
        'purchases',  # ✅ Changed from 'conversions'
        'revenue',
        'ctr',
        'roas'
    ]
    
    # Expected data types (✅ FIXED to match actual CSV)
    EXPECTED_TYPES = {
        'date': ['object', 'datetime64[ns]'],
        'campaign_name': ['object'],
        'adset_name': ['object'],  # ✅ Changed
        'creative_message': ['object'],
        'platform': ['object'],
        'audience_type': ['object'],
        'creative_type': ['object'],
        'impressions': ['int64', 'float64'],
        'clicks': ['int64', 'float64'],
        'spend': ['float64', 'int64'],
        'purchases': ['int64', 'float64'],  # ✅ Changed
        'revenue': ['float64', 'int64'],
        'ctr': ['float64'],
        'roas': ['float64']
    }
    
    def __init__(self, logger=None):
        """Initialize validator with optional logger."""
        self.logger = logger
        self.validation_errors = []
        self.validation_warnings = []
    
    def validate_schema(self, df: pd.DataFrame) -> Tuple[bool, List[str], List[str]]:
        """
        Validate dataframe schema.
        
        Args:
            df: Pandas DataFrame to validate
            
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        self.validation_errors = []
        self.validation_warnings = []
        
        try:
            # Check 1: DataFrame is not empty
            if df is None or len(df) == 0:
                self.validation_errors.append("DataFrame is empty or None")
                return False, self.validation_errors, self.validation_warnings
            
            # Check 2: Required columns exist
            missing_columns = self._check_required_columns(df)
            if missing_columns:
                self.validation_errors.extend([
                    f"Missing required column: {col}" for col in missing_columns
                ])
            
            # Check 3: Data types are correct
            type_errors = self._check_data_types(df)
            if type_errors:
                self.validation_warnings.extend(type_errors)
            
            # Check 4: No all-null columns
            null_columns = self._check_null_columns(df)
            if null_columns:
                self.validation_warnings.extend([
                    f"Column '{col}' is entirely null" for col in null_columns
                ])
            
            # Check 5: Critical metrics have reasonable values
            value_warnings = self._check_value_ranges(df)
            if value_warnings:
                self.validation_warnings.extend(value_warnings)
            
            # Check 6: Date column is parseable
            date_error = self._check_date_column(df)
            if date_error:
                self.validation_errors.append(date_error)
            
            # Log results
            if self.logger:
                self.logger.log_agent_action(
                    "SchemaValidator",
                    "validation_complete",
                    {
                        "errors": len(self.validation_errors),
                        "warnings": len(self.validation_warnings),
                        "status": "PASS" if len(self.validation_errors) == 0 else "FAIL"
                    },
                    status="success" if len(self.validation_errors) == 0 else "error"
                )
            
            is_valid = len(self.validation_errors) == 0
            return is_valid, self.validation_errors, self.validation_warnings
            
        except Exception as e:
            error_msg = f"Schema validation failed with exception: {str(e)}"
            self.validation_errors.append(error_msg)
            if self.logger:
                self.logger.log_error("SchemaValidator", error_msg)
            return False, self.validation_errors, self.validation_warnings
    
    def _check_required_columns(self, df: pd.DataFrame) -> List[str]:
        """Check if all required columns are present."""
        existing_columns = set(df.columns)
        required_columns = set(self.REQUIRED_COLUMNS)
        missing = required_columns - existing_columns
        return list(missing)
    
    def _check_data_types(self, df: pd.DataFrame) -> List[str]:
        """Check if data types match expected types."""
        type_errors = []
        
        for col, expected_types in self.EXPECTED_TYPES.items():
            if col in df.columns:
                actual_type = str(df[col].dtype)
                if actual_type not in expected_types:
                    type_errors.append(
                        f"Column '{col}' has type '{actual_type}', expected one of {expected_types}"
                    )
        
        return type_errors
    
    def _check_null_columns(self, df: pd.DataFrame) -> List[str]:
        """Check for columns that are entirely null."""
        null_columns = []
        
        for col in self.REQUIRED_COLUMNS:
            if col in df.columns:
                if df[col].isna().all():
                    null_columns.append(col)
        
        return null_columns
    
    def _check_value_ranges(self, df: pd.DataFrame) -> List[str]:
        """Check if values are in reasonable ranges."""
        warnings = []
        
        # Check for negative values in metrics that should be positive
        positive_columns = ['impressions', 'clicks', 'spend', 'purchases', 'revenue']  # ✅ Changed
        for col in positive_columns:
            if col in df.columns:
                if (df[col] < 0).any():
                    warnings.append(f"Column '{col}' contains negative values")
        
        # Check for unrealistic ROAS values
        if 'roas' in df.columns:
            extreme_roas = df[df['roas'] > 1000]
            if len(extreme_roas) > 0:
                warnings.append(f"Found {len(extreme_roas)} records with ROAS > 1000 (possible data quality issue)")
        
        # Check for CTR > 100%
        if 'ctr' in df.columns:
            invalid_ctr = df[df['ctr'] > 1.0]
            if len(invalid_ctr) > 0:
                warnings.append(f"Found {len(invalid_ctr)} records with CTR > 100%")
        
        return warnings
    
    def _check_date_column(self, df: pd.DataFrame) -> str:
        """Check if date column is valid and parseable."""
        if 'date' not in df.columns:
            return "Date column missing"
        
        try:
            # Try to parse dates
            if df['date'].dtype == 'object':
                pd.to_datetime(df['date'], errors='coerce')
            return None
        except Exception as e:
            return f"Date column cannot be parsed: {str(e)}"
    
    def get_validation_report(self) -> Dict[str, Any]:
        """Get detailed validation report."""
        return {
            "is_valid": len(self.validation_errors) == 0,
            "errors": self.validation_errors,
            "warnings": self.validation_warnings,
            "error_count": len(self.validation_errors),
            "warning_count": len(self.validation_warnings)
        }
