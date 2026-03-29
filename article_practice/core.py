from __future__ import annotations

from dataclasses import dataclass, field
import re
import time
from typing import Any
from uuid import uuid4


ARTICLE_WORDS = {"a", "an", "the"}
PROTECTED_PHRASES = {"a": {"lot", "few", "little", "bit"}}
TOKEN_RE = re.compile(r"\s+|[A-Za-z]+(?:'[A-Za-z]+)?|[^\w\s]", re.UNICODE)


@dataclass(frozen=True)
class Blank:
    index: int
    answer: str
    display: str
    context: str


@dataclass
class Exercise:
    exercise_id: str
    original_text: str
    segments: list[dict[str, Any]]
    blanks: list[Blank]
    created_at: float = field(default_factory=time.time)

    def prompt_payload(self) -> dict[str, Any]:
        return {
            "exercise_id": self.exercise_id,
            "segments": self.segments,
            "blank_count": len(self.blanks),
            "article_count": len(self.blanks),
        }


def normalize_source_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = []
    for block in re.split(r"\n\s*\n+", normalized):
        cleaned = re.sub(r"\s*\n\s*", " ", block).strip()
        if cleaned:
            paragraphs.append(cleaned)
    return "\n\n".join(paragraphs)


def build_exercise(text: str, exercise_id: str | None = None) -> Exercise:
    source_text = normalize_source_text(text)
    if not source_text:
        raise ValueError("Paste a passage before generating an exercise.")

    tokens = TOKEN_RE.findall(source_text)
    if not tokens:
        raise ValueError("The passage could not be parsed.")

    segments: list[dict[str, Any]] = []
    blanks: list[Blank] = []
    blank_index = 0

    for token_index, token in enumerate(tokens):
        if _should_blank(tokens, token_index):
            answer = token.lower()
            blanks.append(
                Blank(
                    index=blank_index,
                    answer=answer,
                    display=token,
                    context=_build_context(tokens, token_index),
                )
            )
            segments.append(
                {
                    "type": "blank",
                    "index": blank_index,
                    "width": max(5, len(token) + 2),
                }
            )
            blank_index += 1
            continue

        _append_text_segment(segments, token)

    if not blanks:
        raise ValueError("No removable articles were found. Try a longer passage.")

    return Exercise(
        exercise_id=exercise_id or uuid4().hex,
        original_text=source_text,
        segments=segments,
        blanks=blanks,
    )


def grade_exercise(exercise: Exercise, answers: list[str]) -> dict[str, Any]:
    if len(answers) > len(exercise.blanks):
        raise ValueError("Too many answers were submitted.")

    padded_answers = answers + [""] * (len(exercise.blanks) - len(answers))
    results: list[dict[str, Any]] = []
    mistakes: list[dict[str, Any]] = []
    correct_count = 0

    for blank, actual in zip(exercise.blanks, padded_answers):
        submitted = actual.strip().lower()
        correct = submitted == blank.answer
        results.append(
            {
                "index": blank.index,
                "expected": blank.display,
                "actual": actual.strip(),
                "correct": correct,
            }
        )
        if correct:
            correct_count += 1
            continue

        mistakes.append(
            {
                "index": blank.index,
                "expected": blank.display,
                "actual": actual.strip() or "(blank)",
                "context": blank.context,
            }
        )

    total = len(exercise.blanks)
    score = round((correct_count / total) * 100, 1) if total else 0.0
    return {
        "score": score,
        "correct_count": correct_count,
        "total_count": total,
        "comment": comment_for_score(score),
        "results": results,
        "mistakes": mistakes,
        "original_text": exercise.original_text,
    }


def comment_for_score(score: float) -> str:
    if score == 100:
        return "Clean pass. Every article is in place."
    if score >= 90:
        return "Very strong. Only minor misses."
    if score >= 75:
        return "Solid attempt. Review the misses and rerun it."
    if score >= 50:
        return "Useful draft. The problem spots are now visible."
    return "Needs another pass. Slow down and watch noun phrases."


def _append_text_segment(segments: list[dict[str, Any]], token: str) -> None:
    if segments and segments[-1]["type"] == "text":
        segments[-1]["content"] += token
    else:
        segments.append({"type": "text", "content": token})


def _should_blank(tokens: list[str], token_index: int) -> bool:
    token = tokens[token_index]
    if not _is_word(token):
        return False

    token_lower = token.lower()
    if token_lower not in ARTICLE_WORDS:
        return False

    next_word = _next_word(tokens, token_index)
    protected_options = PROTECTED_PHRASES.get(token_lower, set())
    return next_word not in protected_options


def _is_word(token: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z]+(?:'[A-Za-z]+)?", token))


def _next_word(tokens: list[str], start_index: int) -> str | None:
    for token in tokens[start_index + 1 :]:
        if _is_word(token):
            return token.lower()
    return None


def _build_context(tokens: list[str], token_index: int, radius: int = 4) -> str:
    start = max(0, token_index - radius)
    end = min(len(tokens), token_index + radius + 1)
    snippet = tokens[start:end]
    snippet[token_index - start] = "___"
    compact = "".join(snippet)
    compact = re.sub(r"\s+", " ", compact).strip()
    return compact
