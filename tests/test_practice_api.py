import threading
import uuid

import httpx
from fastapi.testclient import TestClient

from practice_service.app import create_app
from practice_service.content_client import ContentClient
from practice_service.repository import DuplicateAttempt, PracticeRepository, VersionConflict


def answer_key(content_app, problem_id):
    r = content_app.test_client().get(f"/internal/problems/{problem_id}", headers={"X-Service-Token": "dev-service-token"})
    return r.get_json()["answer"]


def submit(practice, student, problem_id, answer, attempt_id=None):
    return practice.post(f"/students/{student}/attempts", json={
        "attempt_id": attempt_id or uuid.uuid4().hex, "problem_id": problem_id, "answer": answer})


def test_next_problem_targets_seventy_percent_for_new_student(practice):
    body = practice.get("/students/asha/topics/fractions/next").json()
    assert body["student_rating"] == 800 and body["target_rating"] == 653
    assert "answer" not in body["problem"]
    assert 0.6 < body["expected_success"] < 0.8


def test_correct_answer_raises_rating_and_wrong_answer_reveals_key(practice, content_app):
    p = practice.get("/students/asha/topics/integers/next").json()["problem"]
    ok = submit(practice, "asha", p["id"], answer_key(content_app, p["id"])).json()
    assert ok["correct"] and ok["rating_after"] > ok["rating_before"] and ok["correct_answer"] is None
    p2 = practice.get("/students/asha/topics/integers/next").json()["problem"]
    assert p2["id"] != p["id"]  # recently attempted problems are not repeated
    bad = submit(practice, "asha", p2["id"], "123456").json()
    assert not bad["correct"] and bad["rating_after"] < bad["rating_before"]
    assert bad["correct_answer"] == answer_key(content_app, p2["id"])


def test_retried_submission_is_idempotent(practice, content_app):
    p = practice.get("/students/ravi/topics/fractions/next").json()["problem"]
    first = submit(practice, "ravi", p["id"], answer_key(content_app, p["id"]), attempt_id="retry-attempt-1").json()
    again = submit(practice, "ravi", p["id"], "wrong", attempt_id="retry-attempt-1").json()
    assert again["replayed"] and again["correct"] == first["correct"] and again["rating_after"] == first["rating_after"]
    assert practice.get("/students/ravi/progress").json()[0]["attempts"] == 1


def test_concurrent_submissions_are_all_counted(practice, content_app):
    p = practice.get("/students/meera/topics/integers/next").json()["problem"]
    key = answer_key(content_app, p["id"])
    results = []
    threads = [threading.Thread(target=lambda: results.append(submit(practice, "meera", p["id"], key).status_code))
               for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    progress = practice.get("/students/meera/progress").json()[0]
    assert progress["attempts"] == results.count(200)
    assert results.count(200) + results.count(409) == 5 and results.count(200) >= 1


def test_progress_reports_accuracy_and_mastery(practice, content_app):
    for _ in range(4):
        p = practice.get("/students/zoya/topics/exponents/next").json()["problem"]
        submit(practice, "zoya", p["id"], answer_key(content_app, p["id"]))
    [row] = practice.get("/students/zoya/progress").json()
    assert row == {**row, "topic": "exponents", "attempts": 4, "accuracy": 1.0}
    assert row["rating"] > 850 and row["mastery"] == "developing"  # easy problems: small gains


def test_malformed_answer_is_422_and_not_counted(practice):
    p = practice.get("/students/kabir/topics/expressions/next").json()["problem"]
    r = submit(practice, "kabir", p["id"], "import os")
    assert r.status_code == 422
    assert practice.get("/students/kabir/progress").json() == []


def test_input_validation(practice):
    assert practice.get("/students/bad id!/topics/fractions/next").status_code in (404, 422)
    assert practice.post("/students/asha/attempts", json={"attempt_id": "x", "problem_id": "p", "answer": "1"}).status_code == 422
    assert submit(practice, "asha", "no-such-problem", "1").status_code == 404
    assert practice.get("/students/asha/topics/unknown-topic/next").status_code == 404


def test_content_service_outage_returns_503(ddb):
    def down(request):
        raise httpx.ConnectError("connection refused", request=request)
    client = ContentClient(base_url="http://content", transport=httpx.MockTransport(down))
    practice = TestClient(create_app(ddb, client))
    assert practice.get("/students/asha/topics/fractions/next").status_code == 503
    assert practice.get("/health").json()["status"] == "ok"


def test_stale_skill_version_and_reused_attempt_id_are_rejected_atomically(ddb):
    repo = PracticeRepository(ddb)
    skill = {"topic": "fractions", "rating": 820, "attempts": 1, "correct": 1, "version": 1}
    attempt = {"attempt_id": "a1", "topic": "fractions", "problem_id": "p", "answer": "1", "correct": True,
               "at": "2026-11-11T10:00:00.000+00:00"}
    repo.record_attempt("s1", attempt, skill, 0, {"ok": 1})
    stale = {**attempt, "attempt_id": "a2"}
    try:
        repo.record_attempt("s1", stale, {**skill, "version": 2}, 0, {"ok": 2})  # read version 0, now 1
        raise AssertionError("expected VersionConflict")
    except VersionConflict:
        pass
    try:
        repo.record_attempt("s1", attempt, {**skill, "version": 2}, 1, {"ok": 3})
        raise AssertionError("expected DuplicateAttempt")
    except DuplicateAttempt:
        pass
    # neither rejected transaction left partial writes behind
    assert repo.get_skill("s1", "fractions")["version"] == 1
    assert repo.get_replay("s1", "a2") is None
    assert repo.recent_problem_ids("s1", "fractions") == ["p"]
