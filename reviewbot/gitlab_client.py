"""
GitLab API client for interacting with Merge Requests.

Handles authentication, API calls, and comment management.
"""

import json
import logging
import time
from dataclasses import dataclass
from typing import Any

import requests

logger = logging.getLogger(__name__)


@dataclass
class GitLabConfig:
    """GitLab API configuration."""

    token: str
    api_url: str
    project_id: str
    merge_request_iid: str


class GitLabClient:
    """Client for GitLab REST API."""

    def __init__(self, config: GitLabConfig) -> None:
        """
        Initialize GitLab client.

        Args:
            config: GitLab configuration with token and project info
        """
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "PRIVATE-TOKEN": config.token,
            "Content-Type": "application/json",
        })
        self._existing_comments: list[dict[str, Any]] | None = None

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
        retry_count: int = 3,
        retry_delay: float = 1.0,
    ) -> requests.Response:
        """
        Make HTTP request with retry logic.

        Args:
            method: HTTP method
            endpoint: API endpoint (relative to base URL)
            data: Optional JSON data
            retry_count: Number of retry attempts
            retry_delay: Delay between retries in seconds

        Returns:
            Response object

        Raises:
            requests.RequestException: If all retries fail
        """
        url = f"{self.config.api_url.rstrip('/')}/{endpoint.lstrip('/')}"

        last_exception: Exception | None = None

        for attempt in range(retry_count):
            try:
                response = self.session.request(
                    method,
                    url,
                    json=data,
                    timeout=30,
                )

                if response.status_code == 429:  # Rate limited
                    retry_after = int(response.headers.get("Retry-After", retry_delay))
                    logger.warning(f"Rate limited, waiting {retry_after}s")
                    time.sleep(retry_after)
                    continue

                if response.status_code >= 500:  # Server error, retry
                    logger.warning(f"Server error {response.status_code}, retrying...")
                    time.sleep(retry_delay * (attempt + 1))
                    continue

                response.raise_for_status()
                return response

            except requests.RequestException as e:
                last_exception = e
                logger.warning(f"Request failed (attempt {attempt + 1}/{retry_count}): {e}")
                time.sleep(retry_delay * (attempt + 1))

        if last_exception:
            raise last_exception
        raise requests.RequestException("All retry attempts failed")

    def get_merge_request_changes(self) -> list[dict[str, Any]]:
        """
        Get all changes in the merge request.

        Returns:
            List of change dictionaries with diff information
        """
        endpoint = (
            f"/projects/{self.config.project_id}"
            f"/merge_requests/{self.config.merge_request_iid}/changes"
        )

        logger.info("[INFO] Fetching MR changes")

        response = self._make_request("GET", endpoint)
        data = response.json()

        changes = data.get("changes", [])
        logger.info(f"[INFO] Found {len(changes)} changed files")

        return changes

    def get_merge_request_info(self) -> dict[str, Any]:
        """
        Get merge request metadata.

        Returns:
            MR information dictionary
        """
        endpoint = (
            f"/projects/{self.config.project_id}"
            f"/merge_requests/{self.config.merge_request_iid}"
        )

        response = self._make_request("GET", endpoint)
        return response.json()

    def get_existing_comments(self) -> list[dict[str, Any]]:
        """
        Get all existing comments on the merge request.

        Returns:
            List of comment dictionaries
        """
        if self._existing_comments is not None:
            return self._existing_comments

        endpoint = (
            f"/projects/{self.config.project_id}"
            f"/merge_requests/{self.config.merge_request_iid}/notes"
        )

        response = self._make_request("GET", endpoint)
        self._existing_comments = response.json()

        logger.info(f"[INFO] Found {len(self._existing_comments)} existing comments")
        return self._existing_comments

    def post_comment(
        self,
        body: str,
    ) -> dict[str, Any]:
        """
        Post a comment to the merge request.

        Args:
            body: Comment text (markdown supported)

        Returns:
            Created comment data
        """
        endpoint = (
            f"/projects/{self.config.project_id}"
            f"/merge_requests/{self.config.merge_request_iid}/notes"
        )

        data: dict[str, Any] = {"body": body}

        logger.info(f"[INFO] Posting comment")

        response = self._make_request("POST", endpoint, data)
        return response.json()

    def post_summary_comment(self, body: str) -> dict[str, Any]:
        """
        Post a summary comment to the MR discussion.

        Args:
            body: Summary comment text

        Returns:
            Created comment data
        """
        return self.post_comment(body)

    def is_duplicate_comment(
        self,
        body: str,
    ) -> bool:
        """
        Check if a similar comment already exists.

        Args:
            body: Comment body to check

        Returns:
            True if duplicate found, False otherwise
        """
        existing = self.get_existing_comments()

        # Normalize body for comparison
        normalized_body = " ".join(body.split())

        for comment in existing:
            # Check if it's a bot comment (from this reviewer)
            if not self._is_bot_comment(comment):
                continue

            # Check body similarity
            existing_body = comment.get("body", "")
            normalized_existing = " ".join(existing_body.split())

            # Simple deduplication: check if core message is the same
            if self._messages_similar(normalized_body, normalized_existing):
                return True

        return False

    def _is_bot_comment(self, comment: dict[str, Any]) -> bool:
        """Check if comment is from the review bot."""
        author = comment.get("author", {})
        username = author.get("username", "")

        # Check for bot username patterns
        bot_patterns = ["reviewbot", "ai-reviewer", "gitlab-ai", "ai_bot"]
        return any(pattern in username.lower() for pattern in bot_patterns)

    def _messages_similar(self, msg1: str, msg2: str, threshold: float = 0.8) -> bool:
        """
        Check if two messages are similar enough to be duplicates.

        Simple implementation using substring matching.
        """
        if not msg1 or not msg2:
            return False

        # Extract issue/suggestion content
        msg1_lower = msg1.lower()
        msg2_lower = msg2.lower()

        # Check if one contains the other
        if msg1_lower in msg2_lower or msg2_lower in msg1_lower:
            return True

        # Check for common key phrases
        key_phrases = ["issue:", "suggestion:", "warning:", "error:"]
        for phrase in key_phrases:
            if phrase in msg1_lower and phrase in msg2_lower:
                # Extract content after the phrase
                idx1 = msg1_lower.find(phrase)
                idx2 = msg2_lower.find(phrase)
                content1 = msg1[idx1 + len(phrase):idx1 + len(phrase) + 50].strip()
                content2 = msg2[idx2 + len(phrase):idx2 + len(phrase) + 50].strip()

                if content1 and content2 and content1.lower() == content2.lower():
                    return True

        return False

    def get_commit_id(self) -> str | None:
        """
        Get the latest commit SHA for the merge request.

        Returns:
            Commit SHA or None if not found
        """
        mr_info = self.get_merge_request_info()
        return mr_info.get("sha") or mr_info.get("diff_refs", {}).get("head_sha")
