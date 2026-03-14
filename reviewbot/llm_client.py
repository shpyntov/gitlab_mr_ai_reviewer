"""
LLM client for AI-powered code review.

Integrates with OpenAI-compatible APIs for code analysis.
"""

import logging
import os

from openai import OpenAI

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for LLM-based code review."""

    DEFAULT_MODEL = os.environ.get("LLM_MODEL", "Qwen/Qwen3-Coder-480B-A35B-Instruct")
    DEFAULT_BASE_URL = os.environ.get("LLM_BASE_URL", "https://foundation-models.api.cloud.ru/v1")

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
        self.api_key = api_key or os.environ.get("LLM_API_KEY")
        if not self.api_key:
            raise ValueError("LLM_API_KEY is required. Set via constructor or LLM_API_KEY env var.")

        self.base_url = base_url or self.DEFAULT_BASE_URL
        self.model = model or self.DEFAULT_MODEL
        self.temperature = temperature
        self.max_tokens = max_tokens

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

        logger.info(f"[INFO] LLM client initialized with model: {self.model}")

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
