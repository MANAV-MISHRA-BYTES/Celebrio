import pytest

from app import create_app


@pytest.fixture
def app(tmp_path):
    return create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.sqlite3"), "SECRET_KEY": "test-secret"})


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def plan():
    return {
        "event_summary": "An intimate garden wedding with thoughtful details.",
        "budget": {"categories": [{"category": "Venue", "amount": 40000, "priority": "High"}, {"category": "Food", "amount": 35000, "priority": "High"}]},
        "timeline": [{"title": "Book the venue", "date": "12 weeks before", "description": "Visit and reserve the garden.", "priority": "High", "status": "pending"}],
        "vendors": [{"category": "Venue", "service": "Garden venue", "priority": "High", "status": "Not Started", "notes": "Ask about rain cover."}],
        "ideas": [{"title": "Golden-hour vows", "description": "A warm outdoor ceremony.", "cost_level": "Low", "reason": "Fits the garden setting."}],
        "guest_plan": {"estimated_guests": 80, "categories": []},
        "food_plan": {"meal_structure": "A relaxed vegetarian dinner", "menu_ideas": [{"course": "Starter", "suggestion": "Seasonal chaat"}], "special_considerations": "Ask about allergies."},
        "risks": [{"risk": "Rain", "likelihood": "Medium", "impact": "High", "mitigation": "Check the forecast.", "backup_plan": "Reserve an indoor space."}],
        "next_steps": [{"task": "Shortlist venues", "priority": "High", "reason": "Popular dates fill early.", "timing": "This week", "status": "pending"}],
    }
