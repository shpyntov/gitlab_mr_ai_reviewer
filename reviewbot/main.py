#!/usr/bin/env python3
"""
GitLab MR AI Reviewer - Main entry point.

Runs automated AI code review for GitLab Merge Requests.
"""

import logging
import os
import sys

from reviewbot.config_loader import ConfigLoader
from reviewbot.gitlab_client import GitLabClient, GitLabConfig
from reviewbot.llm_client import LLMClient
from reviewbot.review_engine import ReviewEngine


def setup_logging() -> None:
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def validate_env_vars() -> None:
    """Validate required environment variables."""
    required_vars = [
        "API_KEY",
        "GITLAB_TOKEN",
        "CI_PROJECT_ID",
        "CI_MERGE_REQUEST_IID",
    ]

    missing = []
    for var in required_vars:
        if var not in os.environ:
            missing.append(var)

    if missing:
        print(f"Error: Missing required environment variables: {', '.join(missing)}")
        print("\nRequired variables:")
        print("  API_KEY              - LLM API key")
        print("  GITLAB_TOKEN         - GitLab personal access token")
        print("  CI_PROJECT_ID        - GitLab project ID")
        print("  CI_MERGE_REQUEST_IID - Merge request IID")
        print("\nOptional variables:")
        print("  CI_API_V4_URL        - GitLab API URL (default: https://gitlab.com/api/v4)")
        print("  REVIEW_MODE          - Review mode: 'line' or 'summary' (default: line)")
        sys.exit(1)


def get_review_mode() -> str:
    """Get review mode from environment."""
    mode = os.environ.get("REVIEW_MODE", "line").lower()

    if mode not in ("line", "summary"):
        print(f"Warning: Invalid REVIEW_MODE '{mode}', defaulting to 'line'")
        return "line"

    return mode


def main() -> int:
    """
    Main entry point.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("[INFO] GitLab MR AI Reviewer starting...")

    # Validate environment
    validate_env_vars()

    # Get configuration
    review_mode = get_review_mode()
    logger.info(f"[INFO] Review mode: {review_mode}")

    # Get GitLab API URL
    gitlab_api_url = os.environ.get(
        "CI_API_V4_URL",
        "https://gitlab.com/api/v4"
    )

    # Initialize components
    try:
        gitlab_config = GitLabConfig(
            token=os.environ["GITLAB_TOKEN"],
            api_url=gitlab_api_url,
            project_id=os.environ["CI_PROJECT_ID"],
            merge_request_iid=os.environ["CI_MERGE_REQUEST_IID"],
        )

        gitlab_client = GitLabClient(gitlab_config)

        # Load config for AI settings
        config_loader = ConfigLoader()

        llm_client = LLMClient(
            api_key=os.environ["API_KEY"],
            model=config_loader.get("ai", "model"),
            temperature=config_loader.get("ai", "temperature", default=0.3),
            max_tokens=config_loader.get("ai", "max_tokens", default=2000),
        )

        review_engine = ReviewEngine(
            gitlab_client=gitlab_client,
            llm_client=llm_client,
            config_loader=config_loader,
            mode=review_mode,
        )

        # Run review
        success = review_engine.run_review()

        if success:
            logger.info("[INFO] Review completed successfully")
            return 0
        else:
            logger.error("[ERROR] Review failed")
            return 1

    except Exception as e:
        logger.error(f"[ERROR] Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
