import json

import pytest

from app.ai import AIServiceError, parse_plan


def valid_event():
    return {"name": "Mira's Birthday", "event_type": "Birthday", "event_date": "2099-08-10", "location": "Pune", "guests": "35", "budget": "75000", "currency": "INR", "style": "Colorful", "food_preference": "Vegetarian", "priority": "Guest Experience", "notes": "Garden party"}


def test_application_startup(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Celebrio" in response.data


def test_event_creation_and_retrieval(client, monkeypatch, plan):
    monkeypatch.setattr("app.routes.generate", lambda context: plan)
    response = client.post("/api/events", json=valid_event())
    assert response.status_code == 201
    event_id = response.json["event_id"]
    detail = client.get(f"/api/events/{event_id}")
    assert detail.status_code == 200
    assert detail.json["name"] == "Mira's Birthday"
    assert len(detail.json["tasks"]) == 2
    assert len(detail.json["vendors"]) == 1
    assert client.get(response.json["redirect"]).status_code == 200


@pytest.mark.parametrize("update", [
    {"name": ""},
    {"event_type": "Retirement"},
    {"event_date": "2001-01-01"},
    {"guests": "zero"},
    {"budget": "-2"},
    {"style": "Unknown"},
])
def test_event_validation(client, update):
    data = valid_event()
    data.update(update)
    assert client.post("/api/events", json=data).status_code == 400


def test_event_rejects_missing_fields(client):
    response = client.post("/api/events", json={"name": "Incomplete"})
    assert response.status_code == 400
    assert "required" in response.json["error"]


def test_task_and_vendor_updates(client, monkeypatch, plan):
    monkeypatch.setattr("app.routes.generate", lambda context: plan)
    created = client.post("/api/events", json=valid_event()).json
    event = client.get(f"/api/events/{created['event_id']}").json
    task_id = event["tasks"][0]["id"]
    vendor_id = event["vendors"][0]["id"]
    assert client.patch(f"/api/tasks/{task_id}", json={"status": "completed"}).json["status"] == "completed"
    assert client.patch(f"/api/tasks/{task_id}", json={"status": "wrong"}).status_code == 400
    assert client.patch(f"/api/vendors/{vendor_id}", json={"status": "Booked"}).json["status"] == "Booked"
    assert client.patch(f"/api/vendors/{vendor_id}", json={"status": "Paid"}).status_code == 400


def test_guest_categories_persist(client, monkeypatch, plan):
    monkeypatch.setattr("app.routes.generate", lambda context: plan)
    event_id = client.post("/api/events", json=valid_event()).json["event_id"]
    response = client.patch(f"/api/guests/{event_id}", json={"category": "Family", "estimated": 12, "confirmed": 8})
    assert response.status_code == 200
    assert response.json["categories"][0]["estimated"] == 12
    assert client.get(f"/api/events/{event_id}").json["guest_categories"][0]["confirmed"] == 8


def test_budget_values_calculated(client, monkeypatch, plan):
    monkeypatch.setattr("app.routes.generate", lambda context: plan)
    event_id = client.post("/api/events", json=valid_event()).json["event_id"]
    page = client.get(f"/events/{event_id}")
    assert page.status_code == 200
    assert b"budget-table" in page.data
    assert sum(category["amount"] for category in client.get(f"/api/events/{event_id}").json["plan"]["budget"]["categories"]) == 75000


def test_ai_actions_use_event_context(client, monkeypatch, plan):
    monkeypatch.setattr("app.routes.generate", lambda context, action, extra: {"ideas": plan["ideas"]} if action == "ideas" else "Start with the venue.")
    event_id = client.post("/api/events", json=valid_event()).json["event_id"]
    ideas = client.post(f"/api/events/{event_id}/ai", json={"action": "ideas"})
    assert ideas.status_code == 200
    chat = client.post(f"/api/events/{event_id}/ai", json={"action": "chat", "message": "What first?"})
    assert chat.json["answer"] == "Start with the venue."


def test_ai_budget_optimizer_validates_limit(client, monkeypatch, plan):
    monkeypatch.setattr("app.routes.generate", lambda context, action, extra: {"categories": [{"category": "Venue", "amount": 80000, "priority": "High"}], "summary": "Reduced"})
    event_id = client.post("/api/events", json=valid_event()).json["event_id"]
    response = client.post(f"/api/events/{event_id}/ai", json={"action": "optimize"})
    assert response.status_code == 502


def test_ai_response_parsing(plan):
    assert parse_plan(json.dumps(plan)) == plan
    assert parse_plan("```json\n" + json.dumps(plan) + "\n```") == plan


def test_invalid_ai_response_handling():
    with pytest.raises(AIServiceError, match="unreadable"):
        parse_plan("not json")
    with pytest.raises(AIServiceError, match="incomplete"):
        parse_plan({"event_summary": "missing sections"})


def test_missing_gemini_key_is_controlled(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    from app.ai import generate
    with pytest.raises(AIServiceError, match="GEMINI_API_KEY"):
        generate({})


def test_404_behavior(client):
    assert client.get("/events/no-such-event").status_code == 404
    assert client.get("/api/events/no-such-event").json["error"] == "Event not found."


def test_ai_failure_does_not_create_event(client, monkeypatch):
    def unavailable(context):
        raise AIServiceError("Gemini is not configured yet.")
    monkeypatch.setattr("app.routes.generate", unavailable)
    response = client.post("/api/events", json=valid_event())
    assert response.status_code == 503
    with client.application.app_context():
        from app.db import get_db
        assert get_db().execute("SELECT count(*) FROM events").fetchone()[0] == 0
