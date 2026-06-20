from __future__ import annotations

from repopilot_lite.models import PlanStep, TaskRecord


class Planner:
    """Builds a small fixed analysis plan for repository-reading tasks."""

    def create_plan(self, task: TaskRecord) -> list[PlanStep]:
        keywords = self._extract_keywords(task.question)
        return [
            PlanStep(
                name="list_files",
                description="List repository files to understand project shape.",
                args={"max_files": 200},
            ),
            PlanStep(
                name="read_readme",
                description="Read README content when one exists.",
                args={},
            ),
            PlanStep(
                name="search_keywords",
                description="Search question keywords in repository text files.",
                args={"keywords": keywords},
            ),
            PlanStep(
                name="summarize",
                description="Summarize repository context and suggest next modifications.",
                args={},
            ),
        ]

    @staticmethod
    def _extract_keywords(question: str) -> list[str]:
        stop_words = {
            "a",
            "an",
            "and",
            "for",
            "how",
            "in",
            "is",
            "of",
            "on",
            "or",
            "the",
            "to",
            "what",
            "with",
        }
        words = []
        for raw_word in question.replace("_", " ").replace("-", " ").split():
            word = "".join(char for char in raw_word.lower() if char.isalnum())
            if len(word) >= 3 and word not in stop_words and word not in words:
                words.append(word)
        return words[:8]
