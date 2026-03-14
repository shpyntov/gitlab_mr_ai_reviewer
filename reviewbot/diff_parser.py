"""
Diff parser for GitLab Merge Request changes.

Parses unified diff format and extracts changed lines with metadata.
"""

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DiffHunk:
    """Represents a single hunk in a diff."""

    old_start: int
    old_lines: int
    new_start: int
    new_lines: int
    content: str
    added_lines: list[tuple[int, str]] = field(default_factory=list)
    removed_lines: list[tuple[int, str]] = field(default_factory=list)


@dataclass
class FileDiff:
    """Represents changes to a single file."""

    old_path: str
    new_path: str
    hunks: list[DiffHunk] = field(default_factory=list)

    @property
    def path(self) -> str:
        """Get the current file path (new path if available)."""
        return self.new_path or self.old_path


@dataclass
class MRDiff:
    """Represents the complete diff for a Merge Request."""

    files: list[FileDiff] = field(default_factory=list)


class DiffParser:
    """Parses GitLab MR diff response into structured data."""

    # Regex patterns for parsing unified diff
    HUNK_PATTERN = re.compile(
        r"^@@ -(?P<old_start>\d+)(?:,(?P<old_lines>\d+))? \+(?P<new_start>\d+)(?:,(?P<new_lines>\d+))? @@"
    )

    def parse_gitlab_diff_response(self, changes: list[dict[str, Any]]) -> MRDiff:
        """
        Parse GitLab API diff response into structured MRDiff.

        Args:
            changes: List of change dictionaries from GitLab API

        Returns:
            MRDiff object containing parsed changes
        """
        mr_diff = MRDiff()

        # Group changes by file
        files_map: dict[str, FileDiff] = {}

        for change in changes:
            old_path = change.get("old_path", "")
            new_path = change.get("new_path", "")
            diff = change.get("diff", "")

            path = new_path or old_path

            if path not in files_map:
                files_map[path] = FileDiff(
                    old_path=old_path,
                    new_path=new_path,
                )
                mr_diff.files.append(files_map[path])

            # Parse individual diff lines
            if diff:
                file_diff = files_map[path]
                added_lines = self._extract_added_lines(diff)
                file_diff.hunks.append(
                    DiffHunk(
                        old_start=0,
                        old_lines=0,
                        new_start=0,
                        new_lines=0,
                        content=diff,
                        added_lines=added_lines,
                    )
                )

        return mr_diff

    def _extract_added_lines(self, diff: str) -> list[tuple[int, str]]:
        """Extract added lines from a diff string with line numbers."""
        added_lines = []
        current_line = 0

        for line in diff.split("\n"):
            if line.startswith("@@"):
                # Parse hunk header to get starting line number
                match = self.HUNK_PATTERN.match(line)
                if match:
                    current_line = int(match.group("new_start"))
            elif line.startswith("+") and not line.startswith("+++"):
                added_lines.append((current_line, line[1:]))
                current_line += 1
            elif not line.startswith("-") and not line.startswith("\\"):
                current_line += 1

        return added_lines

    def build_context_diff(self, mr_diff: MRDiff, max_context_lines: int = 3) -> str:
        """
        Build a readable diff with context for LLM consumption.

        Args:
            mr_diff: Parsed MR diff
            max_context_lines: Maximum context lines around changes

        Returns:
            Formatted diff string for LLM
        """
        result = []

        for file_diff in mr_diff.files:
            result.append(f"### File: {file_diff.path}\n")

            for hunk in file_diff.hunks:
                # Show added lines with surrounding context
                for line_num, content in hunk.added_lines:
                    result.append(f"+{line_num}: {content}")

            result.append("")

        return "\n".join(result)
