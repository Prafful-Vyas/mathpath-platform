from practice_service import rating


def test_expected_success_is_half_at_equal_rating_and_monotonic():
    assert rating.expected_success(900, 900) == 0.5
    assert rating.expected_success(900, 700) > rating.expected_success(900, 900) > rating.expected_success(900, 1100)


def test_target_problem_gives_seventy_percent_success():
    for student in (500, 800, 1200):
        assert abs(rating.expected_success(student, rating.target_problem_rating(student)) - 0.7) < 0.01


def test_update_moves_rating_and_steps_shrink_with_evidence():
    up = rating.update(800, 0, 800, True)
    down = rating.update(800, 0, 800, False)
    assert up > 800 > down
    assert rating.update(800, 20, 800, True) - 800 < up - 800


def test_mastery_levels():
    assert [rating.mastery(r) for r in (600, 850, 1000, 1200)] == ["starting", "developing", "proficient", "mastered"]


def test_simulated_adaptive_policy_hits_target_success_rate():
    from scripts.simulate import run
    adaptive, random_ = run("adaptive", seed=3), run("random", seed=3)
    assert 0.65 <= adaptive["success_rate"] <= 0.75
    assert abs(adaptive["success_rate"] - 0.7) < abs(random_["success_rate"] - 0.7)
