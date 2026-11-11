"""Adaptive difficulty with an Elo-style rating per student per topic.

Problems carry a fixed difficulty rating; the student's rating moves after every attempt.
The next problem is picked so the predicted success rate is about 70%: hard enough to
learn from, easy enough not to discourage."""

import math

START_RATING = 800
TARGET_SUCCESS = 0.7
MASTERY_LEVELS = [(1100, "mastered"), (950, "proficient"), (800, "developing"), (0, "starting")]


def expected_success(student: float, problem: float) -> float:
    return 1 / (1 + 10 ** ((problem - student) / 400))


def k_factor(attempts: int) -> float:
    """Large steps while the estimate is uncertain, smaller once there is evidence."""
    return max(16.0, 64.0 - 4.0 * attempts)


def update(student: float, attempts: int, problem: float, correct: bool) -> float:
    return student + k_factor(attempts) * ((1.0 if correct else 0.0) - expected_success(student, problem))


def target_problem_rating(student: float, p: float = TARGET_SUCCESS) -> int:
    return round(student - 400 * math.log10(p / (1 - p)))


def mastery(student: float) -> str:
    return next(label for floor, label in MASTERY_LEVELS if student >= floor)
