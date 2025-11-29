#!/usr/bin/env python3
"""
Kasparro Agentic FB Analyst - Main Entry Point
UPDATED: Now sets metadata for better logging

Usage:
    python run.py "Why did ROAS drop in March?"
    python run.py "Analyze low-CTR campaigns"
"""

import sys
import yaml
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv
import os

from src.utils import AgentLogger
from src.orchestrator import AgentOrchestrator


def load_config(config_path: str = "config/config.yaml") -> dict:

    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def initialize_llm_client(config: dict):
    """Initialize LLM client based on config."""
    # Load environment variables
    load_dotenv()
    
    provider = config['llm']['provider']
    
    if provider == "groq":
        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        return Groq(api_key=api_key)
    elif provider == "openai":
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        from openai import OpenAI
        return OpenAI(api_key=api_key)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


def main():
    """Main execution function."""
    
    # Check command line arguments
    if len(sys.argv) < 2:
        print("Usage: python run.py 'Your query here'")
        print("\nExample queries:")
        print("  - 'Why did ROAS drop?'")
        print("  - 'Which campaigns should I pause?'")
        print("  - 'Why is my CPC increasing?'")
        print("  - 'What ad messages perform best?'")
        sys.exit(1)
    
    user_query = sys.argv[1]
    
    print("="*80)
    print("🚀 KASPARRO AGENTIC FB ANALYST")
    print("="*80)
    print(f"\n📝 Query: {user_query}\n")
    
    try:
        # Load configuration
        config = load_config()
        
        # Initialize logger
        logger = AgentLogger(config['output']['logs_dir'])
        
        # ✅ NEW: Set metadata with query information
        logger.set_metadata(
            query=user_query,
            config_file="config.yaml",
            llm_provider=config['llm']['provider'],
            llm_model=config['llm']['model']
        )
        
        # Initialize LLM client
        llm_client = initialize_llm_client(config)
        
        # Create orchestrator
        orchestrator = AgentOrchestrator(config, llm_client, logger)
        
        # Run analysis
        results = orchestrator.run(user_query)
        
        # Save logs (now with enhanced naming)
        logger.save_logs()
        
        print("\n" + "="*80)
        print("✅ SUCCESS - Analysis Complete!")
        print("="*80)
        print(f"\n📁 Check outputs in:")
        print(f"   - reports/insights.json")
        print(f"   - reports/creatives.json")
        print(f"   - reports/report.md")
        print(f"   - reports/archives/ (archived copies)")
        print(f"   - logs/ (detailed execution logs)")
        print()
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print("Make sure you have:")
        print("  1. Created config.yaml")
        print("  2. Placed dataset in data/ folder")
        sys.exit(1)
        
    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}")
        print("\nTo fix:")
        print("  1. Create a .env file in project root")
        print("  2. Add: GROQ_API_KEY=your_key_here")
        print("  3. Or: export GROQ_API_KEY=your_key_here")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()
        
        # Still save logs on error
        try:
            logger.save_logs()
            print(f"\nCheck logs/ folder for details")
        except:
            pass
        
        sys.exit(1)


if __name__ == "__main__":
    main()
