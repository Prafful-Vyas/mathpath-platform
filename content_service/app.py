"""Content service (Flask): topic catalogue and problem bank.

Public routes never return answer keys; the practice service reads them through the
/internal route with a service token."""

import hmac
import os
import uuid
from typing import Literal

from botocore.exceptions import ClientError
from flask import Flask, jsonify, request
from pydantic import BaseModel, Field, ValidationError

from content_service.repository import ContentRepository
from mathpath_common.dynamo import resource

PUBLIC_FIELDS = ("id", "topic", "rating", "prompt", "answer_type", "hint")


class TopicIn(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9-]{2,40}$")
    title: str = Field(min_length=2, max_length=80)
    grade: int = Field(ge=1, le=12)
    order: int = Field(ge=0, le=999)
    description: str = Field(max_length=400)


class ProblemIn(BaseModel):
    rating: int = Field(ge=100, le=3000)
    prompt: str = Field(min_length=3, max_length=500)
    answer_type: Literal["numeric", "fraction", "expression"]
    answer: str = Field(min_length=1, max_length=100)
    hint: str = Field(default="", max_length=300)
    id: str | None = Field(default=None, pattern=r"^[a-z0-9-]{3,60}$")


def _check(header: str, expected: str) -> bool:
    return hmac.compare_digest(request.headers.get(header, ""), expected)


def create_app(ddb=None) -> Flask:
    app = Flask(__name__)
    repo = ContentRepository(ddb or resource())
    admin_key = os.getenv("ADMIN_KEY", "dev-admin-key")
    service_token = os.getenv("SERVICE_TOKEN", "dev-service-token")

    @app.errorhandler(ValidationError)
    def invalid(err):
        return jsonify(error="validation_error", detail=err.errors(include_url=False, include_context=False)), 422

    @app.get("/health")
    def health():
        return jsonify(status="ok", service="content")

    @app.get("/topics")
    def list_topics():
        return jsonify(repo.list_topics())

    @app.post("/topics")
    def create_topic():
        if not _check("X-Admin-Key", admin_key):
            return jsonify(error="forbidden"), 403
        topic = TopicIn.model_validate(request.get_json(force=True))
        repo.put_topic(topic.model_dump())
        return jsonify(topic.model_dump()), 201

    @app.get("/topics/<slug>")
    def get_topic(slug):
        topic = repo.get_topic(slug)
        return (jsonify(topic), 200) if topic else (jsonify(error="topic_not_found"), 404)

    @app.post("/topics/<slug>/problems")
    def create_problem(slug):
        if not _check("X-Admin-Key", admin_key):
            return jsonify(error="forbidden"), 403
        if not repo.get_topic(slug):
            return jsonify(error="topic_not_found"), 404
        problem = ProblemIn.model_validate(request.get_json(force=True)).model_dump()
        problem["id"] = problem["id"] or f"{slug}-{uuid.uuid4().hex[:8]}"
        problem["topic"] = slug
        try:
            repo.put_problem(problem)
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return jsonify(error="problem_exists"), 409
            raise
        return jsonify({k: problem[k] for k in PUBLIC_FIELDS}), 201

    @app.get("/topics/<slug>/problems")
    def problems_near(slug):
        if not repo.get_topic(slug):
            return jsonify(error="topic_not_found"), 404
        try:
            near = int(request.args.get("near", 800))
            limit = min(max(int(request.args.get("limit", 1)), 1), 20)
        except ValueError:
            return jsonify(error="near and limit must be integers"), 400
        exclude = {x for x in request.args.get("exclude", "").split(",") if x}
        found = repo.problems_near(slug, near, exclude, limit)
        return jsonify([{k: p[k] for k in PUBLIC_FIELDS} for p in found])

    @app.get("/problems/<problem_id>")
    def get_problem(problem_id):
        p = repo.get_problem(problem_id)
        return (jsonify({k: p[k] for k in PUBLIC_FIELDS}), 200) if p else (jsonify(error="problem_not_found"), 404)

    @app.get("/internal/problems/<problem_id>")
    def get_problem_with_answer(problem_id):
        if not _check("X-Service-Token", service_token):
            return jsonify(error="forbidden"), 403
        p = repo.get_problem(problem_id)
        return (jsonify(p), 200) if p else (jsonify(error="problem_not_found"), 404)

    return app
