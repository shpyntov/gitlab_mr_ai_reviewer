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
        "LLM_API_KEY",
        "GITLAB_TOKEN",
        "GITLAB_PROJECT_ID",
        "GITLAB_MERGE_REQUEST_ID",
        "GITLAB_BASE_URL",
    ]

    missing = []
    for var in required_vars:
        if var not in os.environ:
            missing.append(var)

    if missing:
        print(f"Error: Missing required environment variables: {', '.join(missing)}")
        print("\nRequired variables:")
        print("  LLM_API_KEY                - LLM API key")
        print("  GITLAB_TOKEN               - GitLab personal access token")
        print("  GITLAB_PROJECT_ID          - GitLab project ID")
        print("  GITLAB_MERGE_REQUEST_ID    - Merge request ID")
        print("  GITLAB_BASE_URL            - GitLab base URL (e.g., https://gitlab.com)")
        print("\nOptional variables:")
        print("  REVIEW_LANGUAGE            - Language for review comments (default: ru)")
        sys.exit(1)


def get_review_language() -> str:
    """Get review language from environment."""
    language = os.environ.get("REVIEW_LANGUAGE", "ru").lower()

    if language not in ("en", "ru"):
        print(f"Warning: Invalid REVIEW_LANGUAGE '{language}', defaulting to 'ru'")
        return "ru"

    return language


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
    logger.info("[INFO] Review mode: summary")

    # Get review language
    review_language = get_review_language()
    logger.info(f"[INFO] Review language: {review_language}")

    # Get GitLab base URL
    gitlab_base_url = os.environ.get("GITLAB_BASE_URL")
    # Append /api/v4 to the base URL
    gitlab_api_url = f"{gitlab_base_url.rstrip('/')}/api/v4"

    # Initialize components
    try:
        gitlab_config = GitLabConfig(
            token=os.environ["GITLAB_TOKEN"],
            api_url=gitlab_api_url,
            project_id=os.environ["GITLAB_PROJECT_ID"],
            merge_request_iid=os.environ["GITLAB_MERGE_REQUEST_ID"],
        )

        gitlab_client = GitLabClient(gitlab_config)

        # Load config for AI settings
        config_loader = ConfigLoader()

        llm_client = LLMClient(
            api_key=os.environ["LLM_API_KEY"],
            model=config_loader.get("ai", "model"),
            temperature=config_loader.get("ai", "temperature", default=0.3),
            max_tokens=config_loader.get("ai", "max_tokens", default=2000),
        )

        review_engine = ReviewEngine(
            gitlab_client=gitlab_client,
            llm_client=llm_client,
            config_loader=config_loader,
            language=review_language,
        )

        # Run review
        success = review_engine.run_review()

        # Log token usage summary
        llm_client.log_session_summary()

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
