"""
Review engine that orchestrates the code review process.

Coordinates between GitLab client, LLM client, and diff parser.
"""

import logging
from pathlib import Path
from typing import Any

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
            "summary_title": "Итоги код-ревью",
            "potential_issues": "Возможные проблемы",
            "improvements": "Рекомендации",
            "positive_notes": "Положительные моменты",
            "no_issues": "Значительных проблем не обнаружено.",
        },
        "zh": {
            "summary_title": "AI 代码审查总结",
            "potential_issues": "潜在问题",
            "improvements": "改进建议",
            "positive_notes": "优点",
            "no_issues": "未发现重大问题。",
        },
        "es": {
            "summary_title": "Resumen de revisión de código",
            "potential_issues": "Problemas potenciales",
            "improvements": "Mejoras",
            "positive_notes": "Aspectos positivos",
            "no_issues": "No se encontraron problemas significativos.",
        },
        "de": {
            "summary_title": "Zusammenfassung der Code-Überprüfung",
            "potential_issues": "Mögliche Probleme",
            "improvements": "Verbesserungen",
            "positive_notes": "Positive Aspekte",
            "no_issues": "Keine wesentlichen Probleme festgestellt.",
        },
        "fr": {
            "summary_title": "Résumé de la revue de code",
            "potential_issues": "Problèmes potentiels",
            "improvements": "Améliorations",
            "positive_notes": "Points positifs",
            "no_issues": "Aucun problème significatif trouvé.",
        },
    }

    def __init__(
        self,
        gitlab_client: GitLabClient,
        llm_client: LLMClient,
        config_loader: ConfigLoader,
        mode: str = "line",
        language: str = "en",
    ) -> None:
        """
        Initialize review engine.

        Args:
            gitlab_client: GitLab API client
            llm_client: LLM client for AI analysis
            config_loader: Configuration loader
            mode: Review mode ('line' or 'summary')
            language: Language for review comments (e.g., 'en', 'ru', 'zh')
        """
        self.gitlab_client = gitlab_client
        self.llm_client = llm_client
        self.config_loader = config_loader
        self.mode = mode
        self.language = language
        self.diff_parser = DiffParser()

        self._prompt_templates: dict[str, str] = {}

    def load_prompts(self, prompts_dir: str | None = None) -> None:
        """
        Load prompt templates from files.

        Args:
            prompts_dir: Directory containing prompt templates
        """
        if prompts_dir is None:
            # Default location relative to this module
            prompts_dir = str(Path(__file__).parent.parent / "prompts")

        prompts_path = Path(prompts_dir)

        for prompt_file in ["line_review_prompt.md", "summary_review_prompt.md"]:
            file_path = prompts_path / prompt_file
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    key = prompt_file.replace("_prompt.md", "")
                    self._prompt_templates[key] = f.read()
            else:
                logger.warning(f"Prompt file not found: {file_path}")
                self._prompt_templates[key] = self._get_default_prompt(key)

        # Apply language-specific headers to summary prompt
        if "summary" in self._prompt_templates:
            self._apply_language_headers()

    def _apply_language_headers(self) -> None:
        """Apply language-specific headers to the summary prompt template."""
        headers = self.SECTION_HEADERS.get(self.language, self.SECTION_HEADERS["en"])

        # Replace English headers with localized ones
        replacements = {
            "## AI Code Review Summary": f"## {headers['summary_title']}",
            "### Potential Issues": f"### {headers['potential_issues']}",
            "### Improvements": f"### {headers['improvements']}",
            "### Positive Notes": f"### {headers['positive_notes']}",
            "No significant issues found.": headers["no_issues"],
        }

        prompt = self._prompt_templates["summary"]
        for old, new in replacements.items():
            prompt = prompt.replace(old, new)
        self._prompt_templates["summary"] = prompt

    def _get_default_prompt(self, prompt_type: str) -> str:
        """Get default prompt template."""
        headers = self.SECTION_HEADERS.get(self.language, self.SECTION_HEADERS["en"])

        if prompt_type == "line":
            return f"""Analyze the following code changes in file `{{file_path}}`:

```diff
{{diff_content}}
```

Language: All feedback must be written in: {{language}}

Return a JSON array of review items. Each item must have:
- "file": the file path
- "line": the line number (new version)
- "issue": brief description of the issue
- "suggestion": how to fix it (optional)

Focus on:
- Bugs and potential errors
- Security vulnerabilities
- Performance issues
- Code quality problems

Ignore:
- Formatting (unless critical)
- Obvious/trivial changes
- Comments and documentation

Example output:
[
  {{"file": "app.py", "line": 42, "issue": "Possible None dereference", "suggestion": "Add null check"}}
]"""
        else:
            return f"""Analyze the following code changes and provide a summary review:

```diff
{{all_changes}}
```

Language: All feedback must be written in: {{language}}

Provide a structured review in markdown format:

## {headers["summary_title"]}

### {headers["potential_issues"]}
- List significant issues

### {headers["improvements"]}
- Suggest improvements

### {headers["positive_notes"]}
- Highlight good practices

Be concise. Focus on high-impact issues only. Limit to top 10 items total.

If no significant issues found, state: "{headers["no_issues"]}"
"""

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

            # Execute review based on mode
            if self.mode == "summary":
                return self._run_summary_review(mr_diff, files_to_review)
            else:
                return self._run_line_review(mr_diff, files_to_review)

        except Exception as e:
            logger.error(f"Review failed: {e}")
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
        prompt = self._prompt_templates.get(
            "summary", self._get_default_prompt("summary")
        )

        # Inject language into prompt (use double braces to escape other placeholders)
        prompt = prompt.replace("{language}", self.language)

        # Generate review
        summary = self.llm_client.review_summary(all_changes, prompt)

        # Post comment
        max_comments = self.config_loader.get("review", "max_comments", default=10)

        comment_body = self._format_summary_comment(summary, max_comments)

        if not self.gitlab_client.is_duplicate_comment(comment_body):
            self.gitlab_client.post_summary_comment(comment_body)
            logger.info("[INFO] Summary comment posted")
        else:
            logger.info("[INFO] Skipping duplicate summary comment")

        return True

    def _run_line_review(
        self, mr_diff: MRDiff, files_to_review: list[FileDiff]
    ) -> bool:
        """Execute line review mode."""
        logger.info("[INFO] Running line review")

        max_comments = self.config_loader.get("review", "max_comments", default=10)
        comments_posted = 0

        # Get commit ID for inline comments
        commit_id = self.gitlab_client.get_commit_id()

        prompt = self._prompt_templates.get("line", self._get_default_prompt("line"))

        # Inject language into prompt (use double braces to escape other placeholders)
        prompt = prompt.replace("{language}", self.language)

        for file_diff in files_to_review:
            if comments_posted >= max_comments:
                logger.info(f"[INFO] Reached max comments limit ({max_comments})")
                break

            # Build diff for this file
            diff_content = ""
            for hunk in file_diff.hunks:
                diff_content += hunk.content

            if not diff_content.strip():
                continue

            # Get LLM review
            reviews = self.llm_client.review_line_changes(
                diff_content, file_diff.path, prompt
            )

            # Post comments
            for review in reviews:
                if comments_posted >= max_comments:
                    break

                line_num = review.get("line", 0)
                issue = review.get("issue", "")
                suggestion = review.get("suggestion", "")

                if not line_num or not issue:
                    continue

                comment_body = self._format_line_comment(issue, suggestion)

                if not self.gitlab_client.is_duplicate_comment(
                    comment_body, file_diff.path, line_num
                ):
                    self.gitlab_client.post_line_comment(
                        comment_body,
                        file_diff.path,
                        line_num,
                        commit_id,
                    )
                    comments_posted += 1
                    logger.info(
                        f"[INFO] Posted comment on {file_diff.path}:{line_num}"
                    )
                else:
                    logger.info(
                        f"[INFO] Skipping duplicate comment on {file_diff.path}:{line_num}"
                    )

        logger.info(f"[INFO] Posted {comments_posted} comments")
        return True

    def _format_line_comment(self, issue: str, suggestion: str = "") -> str:
        """Format a line comment."""
        comment = f"⚠️ Issue:\n{issue}\n"

        if suggestion:
            comment += f"\n💡 Suggestion:\n{suggestion}"

        return comment

    def _format_summary_comment(self, summary: str, max_items: int = 10) -> str:
        """Format a summary comment."""
        # LLM already includes the header in its response
        return summary[:5000]  # Limit total size
