#!/usr/bin/env python3
# Entry point for Kasparro FB Analyst

import sys
import yaml
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv
import os

from src.utils import AgentLogger
from src.orchestrator import AgentOrchestrator


def load_config(config_path="config/config.yaml"):
    # Load config from YAML file
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def initialize_llm_client(config):
    # Setup LLM client based on config
    load_dotenv()

    provider = config["llm"]["provider"]

    if provider == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found")
        return Groq(api_key=api_key)

    elif provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found")
        from openai import OpenAI
        return OpenAI(api_key=api_key)

    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


def main():
    # Read user query from command line
    if len(sys.argv) < 2:
        print("Usage: python run.py 'your question here'")
        print("Example:")
        print("  python run.py 'Why did ROAS drop?'")
        sys.exit(1)

    user_query = sys.argv[1]

    print("=" * 70)
    print("KASPARRO FB ANALYST")
    print("=" * 70)
    print(f"\nQuery: {user_query}\n")

    try:
        config = load_config()

        logger = AgentLogger(config["output"]["logs_dir"])

        # attach some metadata for logs
        logger.set_metadata(
            query=user_query,
            config_file="config.yaml",
            llm_provider=config["llm"]["provider"],
            llm_model=config["llm"]["model"]
        )

        llm_client = initialize_llm_client(config)

        orchestrator = AgentOrchestrator(config, llm_client, logger)

        results = orchestrator.run(user_query)

        logger.save_logs()

        print("\n" + "=" * 70)
        print("Done. Analysis finished.")
        print("=" * 70)
        print("\nOutput files:")
        print(" - reports/insights.json")
        print(" - reports/creatives.json")
        print(" - reports/report.md")
        print(" - reports/archives/")
        print(" - logs/")
        print()

    except FileNotFoundError as e:
        print(f"\nError: {e}")
        print("Check:")
        print(" - config.yaml exists")
        print(" - data folder is present")
        sys.exit(1)

    except ValueError as e:
        print(f"\nConfig error: {e}")
        print("Make sure your API key is set in .env")
        sys.exit(1)

    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()

        try:
            logger.save_logs()
            print("\nSee logs folder for details")
        except:
            pass

        sys.exit(1)


if __name__ == "__main__":
    main()
