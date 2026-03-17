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
        logger.info(f"[INFO] Input diff size: {len(all_changes)} chars")

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

            # Проверка на пустой или None ответ
            if not content or not content.strip():
                logger.warning(
                    "[WARNING] LLM returned empty response. "
                    f"Model: {self.model}, max_tokens: {self.max_tokens}, "
                    f"input_size: {len(all_changes)} chars"
                )
                # Возвращаем информативное сообщение вместо "No issues found"
                return self._generate_no_issues_message()

            # Проверка на стандартные сообщения об отсутствии проблем
            no_issues_patterns = [
                "no issues found",
                "no significant issues",
                "no problems found",
                "значительных проблем не обнаружено",
                "проблем не обнаружено",
                "ошибок не найдено",
            ]
            content_lower = content.lower().strip()
            if any(pattern in content_lower for pattern in no_issues_patterns):
                logger.info(
                    "[INFO] LLM returned standard 'no issues' message. "
                    "Replacing with localized detailed message."
                )
                return self._generate_no_issues_message()

            # Проверка на возможное обрезание ответа
            finish_reason = response.choices[0].finish_reason
            if finish_reason == "length":
                logger.warning(
                    "[WARNING] LLM response was truncated due to max_tokens limit. "
                    f"Consider increasing LLM_MAX_TOKENS (current: {self.max_tokens}). "
                    f"Response length: {len(content)} chars"
                )

            logger.info(f"[INFO] LLM response generated: {len(content)} chars")
            return content

        except Exception as e:
            logger.error(f"LLM API error: {e}")
            raise

    def _generate_no_issues_message(self) -> str:
        """Generate a message when no significant issues are found."""
        return """## ИИ код-ревью

### Возможные проблемы
Значительных проблем не обнаружено. Изменения выглядят корректными.

### Рекомендации
Продолжайте в том же духе! Убедитесь, что код проходит тесты и соответствует стандартам проекта.

### Положительные моменты
- Код готов к ревью человеком
"""
