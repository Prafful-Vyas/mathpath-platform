import time

import pytest

from practice_service.grading import InvalidAnswer, grade, parse


@pytest.mark.parametrize("kind,key,answer", [
    ("expression", "x^2 + 5x + 6", "(x+2)(x+3)"),
    ("expression", "x^2 + 5x + 6", "6 + 5x + x^2"),
    ("expression", "16x^4", "16 x⁴".replace("⁴", "^4")),
    ("expression", "x^7", "x*x^6"),
    ("expression", "4x^3", "4x³"),
    ("fraction", "3/4", "0.75"),
    ("fraction", "-5/6", "-5/6"),
    ("numeric", "637.5", "1275/2"),
    ("numeric", "-6", "−6"),
])
def test_equivalent_answers_are_accepted(kind, key, answer):
    assert grade(kind, key, answer).correct


@pytest.mark.parametrize("kind,key,answer", [
    ("expression", "x^2 + 5x + 6", "x^2 + 5x + 7"),
    ("expression", "x^2 + 6x + 9", "x^2 + 9"),  # classic (a+b)^2 = a^2 + b^2 misconception
    ("numeric", "11", "7"),
    ("numeric", "5", "x"),
])
def test_wrong_answers_are_rejected(kind, key, answer):
    assert not grade(kind, key, answer).correct


def test_unsimplified_fraction_gets_specific_feedback():
    g = grade("fraction", "3/4", "6/8")
    assert not g.correct and "simplify" in g.feedback


@pytest.mark.parametrize("raw", ["__import__('os')", "x;y", "lambda", "xyz", "((((", "", "a" * 61])
def test_unsafe_or_malformed_input_is_rejected(raw):
    with pytest.raises(InvalidAnswer):
        parse(raw)


@pytest.mark.parametrize("raw", ["9^9^9", "2^(3^4)", "10^999"])
def test_huge_exponents_are_rejected_quickly(raw):
    start = time.perf_counter()
    with pytest.raises(InvalidAnswer):
        parse(raw)
    assert time.perf_counter() - start < 0.5


def test_every_seed_answer_key_grades_itself_correct():
    import json
    from pathlib import Path
    problems = json.loads((Path(__file__).parent.parent / "seed" / "problems.json").read_text(encoding="utf-8"))
    assert [p["id"] for p in problems if not grade(p["answer_type"], p["answer"], p["answer"]).correct] == []
