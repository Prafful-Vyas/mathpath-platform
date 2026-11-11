ADMIN = {"X-Admin-Key": "dev-admin-key"}


def test_topics_are_listed_in_curriculum_order(content):
    topics = content.get("/topics").get_json()
    assert [t["slug"] for t in topics][:2] == ["integers", "fractions"]
    assert len(topics) == 6


def test_public_problem_routes_never_expose_answers(content):
    problem = content.get("/topics/fractions/problems?near=800").get_json()[0]
    assert "answer" not in problem
    assert "answer" not in content.get(f"/problems/{problem['id']}").get_json()


def test_internal_route_requires_service_token(content):
    pid = content.get("/topics/fractions/problems").get_json()[0]["id"]
    assert content.get(f"/internal/problems/{pid}").status_code == 403
    r = content.get(f"/internal/problems/{pid}", headers={"X-Service-Token": "dev-service-token"})
    assert r.status_code == 200 and r.get_json()["answer"]


def test_problems_near_returns_closest_difficulty_and_honours_exclude(content):
    found = content.get("/topics/integers/problems?near=1000&limit=5").get_json()
    distances = [abs(p["rating"] - 1000) for p in found]
    assert distances == sorted(distances) and distances[0] < 60
    again = content.get(f"/topics/integers/problems?near=1000&limit=5&exclude={found[0]['id']}").get_json()
    assert found[0]["id"] not in {p["id"] for p in again}


def test_problems_near_falls_back_outside_the_window(content):
    found = content.get("/topics/integers/problems?near=5000&limit=1").get_json()
    assert found and found[0]["rating"] == max(p["rating"] for p in content.get(
        "/topics/integers/problems?near=5000&limit=20").get_json())


def test_admin_can_create_topic_and_problem_with_validation(content):
    assert content.post("/topics", json={"slug": "ratios"}).status_code == 403
    assert content.post("/topics", json={"slug": "Ratios!"}, headers=ADMIN).status_code == 422
    topic = {"slug": "ratios", "title": "Ratios", "grade": 7, "order": 10, "description": "Ratio and proportion."}
    assert content.post("/topics", json=topic, headers=ADMIN).status_code == 201
    body = {"id": "ratios-001", "rating": 700, "prompt": "Share 20 in the ratio 1:3. Larger part?",
            "answer_type": "numeric", "answer": "15"}
    assert content.post("/topics/ratios/problems", json=body, headers=ADMIN).status_code == 201
    assert content.post("/topics/ratios/problems", json=body, headers=ADMIN).status_code == 409
    assert content.get("/topics/ratios/problems").get_json()[0]["id"] == "ratios-001"


def test_unknown_topic_is_404(content):
    assert content.get("/topics/nope").status_code == 404
    assert content.get("/topics/nope/problems").status_code == 404
