"""
LLM client for AI-powered code review.

Integrates with OpenAI-compatible APIs for code analysis.
"""

import json
import logging
import os
from typing import Any

from openai import OpenAI

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for LLM-based code review."""

    DEFAULT_MODEL = "zai-org/GLM-4.6"
    DEFAULT_BASE_URL = "https://foundation-models.api.cloud.ru/v1"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> None:
        """
        Initialize LLM client.

        Args:
            api_key: API key for the LLM service
            base_url: Base URL for the API
            model: Model name to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
        """
        self.api_key = api_key or os.environ.get("API_KEY")
        if not self.api_key:
            raise ValueError("API_KEY is required. Set via constructor or API_KEY env var.")

        self.base_url = base_url or self.DEFAULT_BASE_URL
        self.model = model or self.DEFAULT_MODEL
        self.temperature = temperature
        self.max_tokens = max_tokens

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

        logger.info(f"[INFO] LLM client initialized with model: {self.model}")

    def review_line_changes(
        self,
        diff_content: str,
        file_path: str,
        prompt_template: str,
    ) -> list[dict[str, Any]]:
        """
        Review line changes and return structured feedback.

        Args:
            diff_content: Diff content for the file
            file_path: Path to the file being reviewed
            prompt_template: Prompt template to use

        Returns:
            List of review items with file, line, issue, suggestion
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert code reviewer. Analyze code changes and provide "
                    "concise, actionable feedback. Focus on bugs, security issues, "
                    "performance problems, and code quality. Ignore formatting unless critical. "
                    "Return ONLY valid JSON array, no other text."
                ),
            },
            {
                "role": "user",
                "content": prompt_template.format(
                    file_path=file_path,
                    diff_content=diff_content,
                ),
            },
        ]

        logger.info(f"[INFO] Sending diff to LLM for {file_path}")

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                presence_penalty=0,
                top_p=0.95,
                messages=messages,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content

            if not content:
                logger.warning("Empty response from LLM")
                return []

            return self._parse_line_review_response(content, file_path)

        except Exception as e:
            logger.error(f"LLM API error: {e}")
            return []

    def review_summary(
        self,
        all_changes: str,
        prompt_template: str,
    ) -> str:
        """
        Generate a summary review for the entire MR.

        Args:
            all_changes: Combined diff content for all changes
            prompt_template: Prompt template to use

        Returns:
            Markdown-formatted review summary
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert code reviewer. Provide a concise, high-level "
                    "summary of code changes. Focus on significant issues, potential bugs, "
                    "and important improvements. Be brief and actionable. "
                    "Return markdown-formatted response."
                ),
            },
            {
                "role": "user",
                "content": prompt_template.format(all_changes=all_changes),
            },
        ]

        logger.info("[INFO] Generating summary review with LLM")

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                presence_penalty=0,
                top_p=0.95,
                messages=messages,
            )

            content = response.choices[0].message.content
            return content or "No issues found."

        except Exception as e:
            logger.error(f"LLM API error: {e}")
            return "Error generating review summary."

    def _parse_line_review_response(
        self, content: str, file_path: str
    ) -> list[dict[str, Any]]:
        """
        Parse LLM response into structured review items.

        Args:
            content: Raw LLM response
            file_path: Path to the file being reviewed

        Returns:
            List of review items
        """
        try:
            # Try to parse as JSON
            data = json.loads(content)

            if isinstance(data, dict):
                # Handle case where response is wrapped in an object
                if "reviews" in data:
                    data = data["reviews"]
                elif "items" in data:
                    data = data["items"]
                else:
                    data = [data]

            if not isinstance(data, list):
                logger.warning(f"Unexpected response format: {type(data)}")
                return []

            # Normalize and validate items
            result = []
            for item in data:
                if not isinstance(item, dict):
                    continue

                review_item = {
                    "file": item.get("file", file_path),
                    "line": item.get("line", 0),
                    "issue": item.get("issue", "Code issue"),
                    "suggestion": item.get("suggestion", ""),
                }

                # Validate required fields
                if review_item["line"] > 0 and review_item["issue"]:
                    result.append(review_item)

            return result

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            # Fallback: try to extract JSON from markdown code blocks
            return self._extract_json_from_markdown(content, file_path)

    def _extract_json_from_markdown(
        self, content: str, file_path: str
    ) -> list[dict[str, Any]]:
        """
        Extract JSON from markdown code blocks.

        Args:
            content: Raw response content
            file_path: File path for fallback

        Returns:
            Parsed review items
        """
        import re

        # Look for JSON in code blocks
        json_pattern = r"```(?:json)?\s*([\s\S]*?)```"
        matches = re.findall(json_pattern, content)

        for match in matches:
            try:
                data = json.loads(match)
                if isinstance(data, list):
                    return self._parse_line_review_response(json.dumps(data), file_path)
            except json.JSONDecodeError:
                continue

        # Last resort: return empty
        logger.warning("Could not extract valid JSON from response")
        return []
