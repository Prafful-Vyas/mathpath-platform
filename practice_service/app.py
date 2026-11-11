"""Practice service (FastAPI): serves the next problem at the right difficulty, grades
answers and tracks each student's rating per topic."""

import os
from datetime import datetime, timezone
from typing import Annotated

from fastapi import FastAPI, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from mathpath_common.dynamo import resource
from practice_service import rating
from practice_service.content_client import ContentClient, ContentUnavailable
from practice_service.grading import InvalidAnswer, grade
from practice_service.repository import DuplicateAttempt, PracticeRepository, VersionConflict

StudentId = Annotated[str, Path(pattern=r"^[A-Za-z0-9_-]{1,40}$")]
Slug = Annotated[str, Path(pattern=r"^[a-z0-9-]{2,40}$")]
MAX_WRITE_RETRIES = 3


class AttemptIn(BaseModel):
    attempt_id: str = Field(pattern=r"^[A-Za-z0-9_-]{8,64}$", description="client-generated, makes retries safe")
    problem_id: str = Field(max_length=60)
    answer: str = Field(min_length=1, max_length=60)


class AttemptOut(BaseModel):
    attempt_id: str
    problem_id: str
    topic: str
    correct: bool
    feedback: str
    correct_answer: str | None
    rating_before: int
    rating_after: int
    expected_success: float
    mastery: str
    replayed: bool = False


def create_app(ddb=None, content: ContentClient | None = None) -> FastAPI:
    app = FastAPI(title="MathPath practice service", version="1.0.0")
    app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
                       allow_methods=["GET", "POST"], allow_headers=["*"])
    repo = PracticeRepository(ddb or resource())
    content = content or ContentClient()

    def call_content(fn, *args):
        try:
            return fn(*args)
        except ContentUnavailable as e:
            raise HTTPException(503, "content service unavailable") from e

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "practice"}

    @app.get("/students/{student}/topics/{topic}/next")
    def next_problem(student: StudentId, topic: Slug):
        skill = repo.get_skill(student, topic) or {"rating": rating.START_RATING}
        target = rating.target_problem_rating(skill["rating"])
        recent = repo.recent_problem_ids(student, topic)
        found = call_content(content.problems_near, topic, target, recent)
        if found is None:
            raise HTTPException(404, "topic not found")
        if not found:  # every nearby problem was seen recently: allow repeats
            found = call_content(content.problems_near, topic, target, [])
        if not found:
            raise HTTPException(404, "topic has no problems")
        return {"problem": found[0], "student_rating": round(skill["rating"]), "target_rating": target,
                "expected_success": round(rating.expected_success(skill["rating"], found[0]["rating"]), 3)}

    @app.post("/students/{student}/attempts", response_model=AttemptOut)
    def submit(student: StudentId, body: AttemptIn):
        if replay := repo.get_replay(student, body.attempt_id):
            return {**replay, "replayed": True}
        problem = call_content(content.problem_with_answer, body.problem_id)
        if problem is None:
            raise HTTPException(404, "problem not found")
        try:
            result = grade(problem["answer_type"], problem["answer"], body.answer)
        except InvalidAnswer as e:
            raise HTTPException(422, str(e)) from e

        for _ in range(MAX_WRITE_RETRIES):
            skill = repo.get_skill(student, problem["topic"]) or {
                "topic": problem["topic"], "rating": rating.START_RATING, "attempts": 0, "correct": 0, "version": 0}
            before = skill["rating"]
            after = rating.update(before, skill["attempts"], problem["rating"], result.correct)
            new_skill = {**skill, "rating": round(after, 2), "attempts": skill["attempts"] + 1,
                         "correct": skill["correct"] + int(result.correct), "version": skill["version"] + 1}
            response = {
                "attempt_id": body.attempt_id, "problem_id": problem["id"], "topic": problem["topic"],
                "correct": result.correct, "feedback": result.feedback,
                "correct_answer": None if result.correct else problem["answer"],
                "rating_before": round(before), "rating_after": round(after),
                "expected_success": round(rating.expected_success(before, problem["rating"]), 3),
                "mastery": rating.mastery(after),
            }
            attempt = {"attempt_id": body.attempt_id, "topic": problem["topic"], "problem_id": problem["id"],
                       "answer": body.answer, "correct": result.correct,
                       "at": datetime.now(timezone.utc).isoformat(timespec="milliseconds")}
            try:
                repo.record_attempt(student, attempt, new_skill, skill["version"], response)
                return response
            except DuplicateAttempt:
                return {**repo.get_replay(student, body.attempt_id), "replayed": True}
            except VersionConflict:
                continue  # another submission updated the skill first: re-read and recompute
        raise HTTPException(409, "too many concurrent submissions, retry")

    @app.get("/students/{student}/progress")
    def progress(student: StudentId):
        return [{"topic": s["topic"], "rating": round(s["rating"]), "attempts": s["attempts"],
                 "accuracy": round(s["correct"] / s["attempts"], 3) if s["attempts"] else 0.0,
                 "mastery": rating.mastery(s["rating"])}
                for s in repo.list_skills(student)]

    return app
