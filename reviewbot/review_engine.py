"""
Review engine that orchestrates the code review process.

Coordinates between GitLab client, LLM client, and diff parser.
"""

import logging
from pathlib import Path

from .config_loader import ConfigLoader
from .diff_parser import DiffParser, FileDiff, MRDiff
from .gitlab_client import GitLabClient
from .llm_client import LLMClient

logger = logging.getLogger(__name__)


class ReviewEngine:
    """Main review engine coordinating all components."""

    # Section headers for different languages
    SECTION_HEADERS: dict[str, dict[str, str]] = {
        "en": {
            "summary_title": "AI Code Review Summary",
            "potential_issues": "Potential Issues",
            "improvements": "Improvements",
            "positive_notes": "Positive Notes",
            "no_issues": "No significant issues found.",
        },
        "ru": {
            "summary_title": "ИИ код-ревью",
            "potential_issues": "Возможные проблемы",
            "improvements": "Рекомендации",
            "positive_notes": "Положительные моменты",
            "no_issues": "Значительных проблем не обнаружено.",
        },
    }

    def __init__(
        self,
        gitlab_client: GitLabClient,
        llm_client: LLMClient,
        config_loader: ConfigLoader,
        language: str = "en",
    ) -> None:
        """
        Initialize review engine.

        Args:
            gitlab_client: GitLab API client
            llm_client: LLM client for AI analysis
            config_loader: Configuration loader
            language: Language for review comments (e.g., 'en', 'ru', 'zh')
        """
        self.gitlab_client = gitlab_client
        self.llm_client = llm_client
        self.config_loader = config_loader
        self.language = language
        self.diff_parser = DiffParser()

        self._prompt_templates: dict[str, str] = {}

    def load_prompts(self, prompts_dir: str | None = None) -> None:
        """
        Load prompt templates from files.

        Args:
            prompts_dir: Directory containing prompt templates

        Raises:
            FileNotFoundError: If prompt file is not found
        """
        if prompts_dir is None:
            # Default location relative to this module
            prompts_dir = str(Path(__file__).parent.parent / "prompts")

        prompts_path = Path(prompts_dir)

        prompt_file = "summary_review_prompt.md"
        file_path = prompts_path / prompt_file

        logger.info(f"[INFO] Loading prompt from {file_path}")

        try:
            with open(file_path, encoding="utf-8") as f:
                key = prompt_file.replace("_prompt.md", "")
                self._prompt_templates[key] = f.read()
            logger.info(f"[INFO] Prompt loaded successfully with key: {key}")
        except FileNotFoundError:
            logger.error(f"[ERROR] Prompt file not found: {file_path}")
            raise
        except Exception as e:
            logger.error(f"[ERROR] Failed to load prompt: {e}")
            raise

        # Apply language-specific headers to summary prompt
        if "summary_review" in self._prompt_templates:
            self._apply_language_headers()

    def _apply_language_headers(self) -> None:
        """Apply language-specific values to the summary prompt template."""
        headers = self.SECTION_HEADERS.get(self.language, self.SECTION_HEADERS["en"])

        prompt = self._prompt_templates["summary_review"]

        # Apply localized headers
        for key, value in headers.items():
            prompt = prompt.replace("{" + key + "}", value)

        # Apply language
        prompt = prompt.replace("{language}", self.language)

        self._prompt_templates["summary_review"] = prompt

    def run_review(self) -> bool:
        """
        Execute the code review process.

        Returns:
            True if review completed successfully, False otherwise
        """
        logger.info("[INFO] Starting code review")

        try:
            # Load prompts
            self.load_prompts()

            # Fetch MR changes
            changes = self.gitlab_client.get_merge_request_changes()

            if not changes:
                logger.info("[INFO] No changes found in MR")
                return True

            # Parse diff
            mr_diff = self.diff_parser.parse_gitlab_diff_response(changes)

            if not mr_diff.files:
                logger.info("[INFO] No parseable changes found")
                return True

            # Filter files based on config
            files_to_review = self._filter_files(mr_diff)

            if not files_to_review:
                logger.info("[INFO] No files match review criteria")
                return True

            # Execute summary review
            return self._run_summary_review(mr_diff, files_to_review)

        except Exception as e:
            logger.error(f"Review failed: {e}")
            # Log the full traceback for better debugging
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return False

    def _filter_files(self, mr_diff: MRDiff) -> list[FileDiff]:
        """Filter files based on configuration."""
        filtered = []

        for file_diff in mr_diff.files:
            if self.config_loader.should_review_file(file_diff.path):
                filtered.append(file_diff)
            else:
                logger.info(f"[INFO] Skipping file (ignored): {file_diff.path}")

        return filtered

    def _run_summary_review(
        self, mr_diff: MRDiff, files_to_review: list[FileDiff]
    ) -> bool:
        """Execute summary review mode."""
        logger.info("[INFO] Running summary review")

        # Build combined diff
        all_changes = self.diff_parser.build_context_diff(mr_diff)

        # Get prompt template
        prompt = self._prompt_templates["summary_review"]

        # Generate review
        summary = self.llm_client.review_summary(all_changes, prompt)

        # Post comment
        comment_body = self._format_summary_comment(summary)

        if not self.gitlab_client.is_duplicate_summary_comment(comment_body):
            self.gitlab_client.post_summary_comment(comment_body)
            logger.info("[INFO] Summary comment posted")
        else:
            logger.info("[INFO] Skipping duplicate summary comment")

        return True

    def _format_summary_comment(self, summary: str) -> str:
        """Format a summary comment."""
        # LLM already includes the header in its response
        return summary[:5000]  # Limit total size
