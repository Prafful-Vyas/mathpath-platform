"""Checks the adaptive engine against simulated students whose true ability is known.

Each simulated student answers correctly with the Elo probability for their hidden ability.
Compared with serving problems at random, adaptive selection should (1) keep the success
rate near the 70% target and (2) estimate ability at least as accurately.
Run: python -m scripts.simulate"""

import json
import random
import statistics
from pathlib import Path

from practice_service import rating

PROBLEMS = json.loads((Path(__file__).resolve().parent.parent / "seed" / "problems.json").read_text(encoding="utf-8"))
ATTEMPTS = 30
STUDENTS = 2000


def run(policy: str, seed: int) -> dict:
    rng = random.Random(seed)
    by_topic: dict[str, list[dict]] = {}
    for p in PROBLEMS:
        by_topic.setdefault(p["topic"], []).append(p)
    errors_10, errors_30, successes, total = [], [], 0, 0
    for _ in range(STUDENTS):
        pool = by_topic[rng.choice(sorted(by_topic))]
        ability = rng.gauss(950, 200)
        est, recent = float(rating.START_RATING), []
        for n in range(ATTEMPTS):
            fresh = [p for p in pool if p["id"] not in recent] or pool
            if policy == "adaptive":
                target = rating.target_problem_rating(est)
                problem = min(fresh, key=lambda p: (abs(p["rating"] - target), p["id"]))
            else:
                problem = rng.choice(fresh)
            correct = rng.random() < rating.expected_success(ability, problem["rating"])
            est = rating.update(est, n, problem["rating"], correct)
            recent = (recent + [problem["id"]])[-15:]
            successes += correct
            total += 1
            if n == 9:
                errors_10.append(abs(est - ability))
        errors_30.append(abs(est - ability))
    return {"policy": policy, "success_rate": round(successes / total, 3),
            "mae_after_10": round(statistics.mean(errors_10)), "mae_after_30": round(statistics.mean(errors_30))}


if __name__ == "__main__":
    rng = random.Random(1)
    start_error = round(statistics.mean(abs(rng.gauss(950, 200) - rating.START_RATING) for _ in range(20000)))
    print(f"rating error before any attempt (MAE): {start_error}")
    for policy in ("random", "adaptive"):
        print(run(policy, seed=11))
