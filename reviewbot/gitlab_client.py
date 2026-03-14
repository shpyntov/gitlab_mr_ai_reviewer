"""
GitLab API client for interacting with Merge Requests.

Handles authentication, API calls, and comment management.
"""

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
        self.session.headers.update(
            {
                "PRIVATE-TOKEN": config.token,
                "Content-Type": "application/json",
            }
        )
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
        endpoint = f"/projects/{self.config.project_id}/merge_requests/{self.config.merge_request_iid}/changes"

        logger.info("[INFO] Fetching MR changes")

        response = self._make_request("GET", endpoint)
        data = response.json()

        changes = data.get("changes", [])
        logger.info(f"[INFO] Found {len(changes)} changed files")

        return changes

    def get_existing_comments(self) -> list[dict[str, Any]]:
        """
        Get all existing comments on the merge request.

        Returns:
            List of comment dictionaries
        """
        if self._existing_comments is not None:
            return self._existing_comments

        endpoint = f"/projects/{self.config.project_id}/merge_requests/{self.config.merge_request_iid}/notes"

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
        endpoint = f"/projects/{self.config.project_id}/merge_requests/{self.config.merge_request_iid}/notes"

        data: dict[str, Any] = {"body": body}

        logger.info("[INFO] Posting comment")

        response = self._make_request("POST", endpoint, data)
        return response.json()

    def update_comment(self, comment_id: int, body: str) -> dict[str, Any]:
        """
        Update an existing comment on the merge request.

        Args:
            comment_id: ID of the comment to update
            body: New comment text (markdown supported)

        Returns:
            Updated comment data
        """
        endpoint = (
            f"/projects/{self.config.project_id}/merge_requests/{self.config.merge_request_iid}/notes/{comment_id}"
        )

        data: dict[str, Any] = {"body": body}

        logger.info(f"[INFO] Updating comment {comment_id}")

        response = self._make_request("PUT", endpoint, data)
        return response.json()

    def find_summary_comment(self) -> dict[str, Any] | None:
        """
        Find an existing summary comment by looking for the main header.

        Returns:
            Comment dict if found, None otherwise
        """
        existing = self.get_existing_comments()

        # Check for summary header (any language variant)
        summary_headers = [
            "## AI Code Review Summary",
            "## ИИ код-ревью",
        ]

        for comment in existing:
            existing_body = comment.get("body", "")

            for header in summary_headers:
                if header in existing_body:
                    return comment

        return None

    def post_summary_comment(self, body: str) -> dict[str, Any]:
        """
        Post or update a summary comment to the MR discussion.

        If a summary comment already exists, it will be updated.
        Otherwise, a new comment will be created.

        Args:
            body: Summary comment text

        Returns:
            Created or updated comment data
        """
        # Check for existing summary comment
        existing_comment = self.find_summary_comment()

        if existing_comment:
            comment_id = existing_comment.get("id")
            if comment_id:
                return self.update_comment(comment_id, body)

        # No existing comment, create new one
        return self.post_comment(body)
