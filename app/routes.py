import json
import uuid
from datetime import date, datetime

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, url_for

from .ai import AIServiceError, generate
from .db import get_db

bp = Blueprint("main", __name__)
EVENT_TYPES = {"Wedding", "Birthday", "Community Event"}
STYLES = {"Elegant", "Minimal", "Traditional", "Modern", "Luxury", "Casual", "Colorful", "Custom"}
FOOD = {"Vegetarian", "Non-vegetarian", "Mixed", "Custom"}
PRIORITIES = {"Budget", "Food", "Decor", "Entertainment", "Guest Experience", "Photography", "Venue"}
VENDOR_STATUSES = {"Not Started", "Contacted", "Shortlisted", "Booked"}


def error(message, status=400):
    return jsonify(error=message), status


def event_context(row):
    data = dict(row)
    data["plan"] = json.loads(data["plan"])
    return data


def fetch_event(event_id):
    row = get_db().execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    return event_context(row) if row else None


@bp.get("/")
def home():
    return render_template("index.html")


@bp.get("/create")
def create():
    return render_template("create.html")


@bp.post("/api/events")
def create_event():
    data = request.get_json(silent=True) or {}
    required = ("name", "event_type", "event_date", "location", "guests", "budget", "currency", "style", "food_preference", "priority")
    if any(not str(data.get(field, "")).strip() for field in required):
        return error("Complete every required field before generating your plan.")
    if data["event_type"] not in EVENT_TYPES or data["style"] not in STYLES or data["food_preference"] not in FOOD or data["priority"] not in PRIORITIES:
        return error("Choose valid event preferences.")
    try:
        event_date = date.fromisoformat(data["event_date"])
        guests = int(data["guests"])
        budget = float(data["budget"])
    except (ValueError, TypeError):
        return error("Enter a valid date, guest count, and budget.")
    if event_date < date.today() or guests < 1 or guests > 1000000 or budget <= 0 or budget > 1000000000000:
        return error("Use a future date, at least one guest, and a positive budget.")
    if len(data["name"].strip()) > 120 or len(data["location"].strip()) > 160 or len(data.get("notes", "")) > 2000:
        return error("Some event details are longer than allowed.")
    context = {key: data.get(key, "") for key in required}
    context.update(guests=guests, budget=budget, notes=str(data.get("notes", "")).strip())
    try:
        plan = generate(context)
    except AIServiceError as exc:
        return error(str(exc), 503)
    categories = plan.get("budget", {}).get("categories") if isinstance(plan, dict) else None
    if not isinstance(categories, list) or not categories:
        return error("The planner returned an incomplete budget. Please try again.", 502)
    try:
        amounts = [float(item["amount"]) for item in categories]
        if any(amount < 0 for amount in amounts) or sum(amounts) > budget:
            return error("The planner returned a budget allocation outside your total. Please try again.", 502)
    except (KeyError, TypeError, ValueError):
        return error("The planner returned an incomplete budget. Please try again.", 502)
    event_id = str(uuid.uuid4())
    db = get_db()
    db.execute("INSERT INTO events (id,name,event_type,event_date,location,guests,budget,currency,style,food_preference,priority,notes,plan) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (event_id, context["name"].strip(), context["event_type"], context["event_date"], context["location"].strip(), guests, budget, context["currency"].upper()[:3], context["style"], context["food_preference"], context["priority"], context["notes"], json.dumps(plan)))
    for item in plan["timeline"]:
        db.execute("INSERT INTO tasks(event_id,title,date,description,priority,status,task_group) VALUES (?,?,?,?,?,?,?)", (event_id, item.get("title", "Planning milestone"), item.get("date", ""), item.get("description", ""), item.get("priority", "Medium"), item.get("status", "pending"), "timeline"))
    for item in plan["next_steps"]:
        db.execute("INSERT INTO tasks(event_id,title,date,description,priority,status,task_group) VALUES (?,?,?,?,?,?,?)", (event_id, item.get("task", "Next step"), item.get("timing", ""), item.get("reason", ""), item.get("priority", "Medium"), item.get("status", "pending"), "next_steps"))
    for item in plan["vendors"]:
        db.execute("INSERT INTO vendors(event_id,category,service,priority,status,notes) VALUES (?,?,?,?,?,?)", (event_id, item.get("category", "Vendor"), item.get("service", ""), item.get("priority", "Medium"), item.get("status", "Not Started"), item.get("notes", "")))
    db.commit()
    return jsonify(event_id=event_id, redirect=url_for("main.dashboard", event_id=event_id)), 201


@bp.get("/events/<event_id>")
def dashboard(event_id):
    event = fetch_event(event_id)
    if not event:
        return render_template("404.html"), 404
    db = get_db()
    tasks = [dict(row) for row in db.execute("SELECT * FROM tasks WHERE event_id = ? ORDER BY date, id", (event_id,)).fetchall()]
    vendors = [dict(row) for row in db.execute("SELECT * FROM vendors WHERE event_id = ? ORDER BY id", (event_id,)).fetchall()]
    return render_template("dashboard.html", event=event, tasks=tasks, vendors=vendors, today=date.today().isoformat())


@bp.get("/api/events/<event_id>")
def get_event(event_id):
    event = fetch_event(event_id)
    if not event:
        return error("Event not found.", 404)
    event["tasks"] = [dict(row) for row in get_db().execute("SELECT * FROM tasks WHERE event_id = ? ORDER BY date,id", (event_id,)).fetchall()]
    event["vendors"] = [dict(row) for row in get_db().execute("SELECT * FROM vendors WHERE event_id = ? ORDER BY id", (event_id,)).fetchall()]
    return jsonify(event)


@bp.patch("/api/tasks/<int:task_id>")
def update_task(task_id):
    data = request.get_json(silent=True) or {}
    if data.get("status") not in ("pending", "completed"):
        return error("Task status must be pending or completed.")
    cursor = get_db().execute("UPDATE tasks SET status = ? WHERE id = ?", (data["status"], task_id))
    get_db().commit()
    if not cursor.rowcount:
        return error("Task not found.", 404)
    return jsonify(status=data["status"])


@bp.patch("/api/vendors/<int:vendor_id>")
def update_vendor(vendor_id):
    data = request.get_json(silent=True) or {}
    if data.get("status") not in VENDOR_STATUSES:
        return error("Choose a valid vendor status.")
    cursor = get_db().execute("UPDATE vendors SET status = ? WHERE id = ?", (data["status"], vendor_id))
    get_db().commit()
    if not cursor.rowcount:
        return error("Vendor not found.", 404)
    return jsonify(status=data["status"])


@bp.patch("/api/guests/<event_id>")
def update_guests(event_id):
    data = request.get_json(silent=True) or {}
    category = str(data.get("category", "")).strip()
    if category not in ("Family", "Friends", "Colleagues", "Community", "Children", "Other"):
        return error("Choose a valid guest category.")
    try:
        estimated, confirmed = int(data.get("estimated")), int(data.get("confirmed"))
    except (ValueError, TypeError):
        return error("Guest counts must be whole numbers.")
    if estimated < 0 or confirmed < 0 or confirmed > estimated:
        return error("Confirmed guests must be between zero and the estimated count.")
    db = get_db()
    row = db.execute("SELECT guest_categories FROM events WHERE id=?", (event_id,)).fetchone()
    if not row:
        return error("Event not found.", 404)
    categories = json.loads(row["guest_categories"])
    item = {"category": category, "estimated": estimated, "confirmed": confirmed}
    if next((i for i, current in enumerate(categories) if current["category"] == category), None) is not None:
        index = next(i for i, current in enumerate(categories) if current["category"] == category)
        categories[index] = item
    else:
        categories.append(item)
    db.execute("UPDATE events SET guest_categories=? WHERE id=?", (json.dumps(categories), event_id))
    db.commit()
    return jsonify(categories=categories)


@bp.post("/api/events/<event_id>/ai")
def ai_action(event_id):
    event = fetch_event(event_id)
    if not event:
        return error("Event not found.", 404)
    data = request.get_json(silent=True) or {}
    action = data.get("action")
    if action not in ("chat", "ideas", "optimize"):
        return error("Choose a supported planner action.")
    prompt = str(data.get("message", "")).strip()
    if action == "chat" and (not prompt or len(prompt) > 1200):
        return error("Enter a question under 1,200 characters.")
    context = {**event, "plan": event["plan"]}
    try:
        result = generate(context, action, prompt or None)
    except AIServiceError as exc:
        return error(str(exc), 503)
    if action == "ideas":
        if not isinstance(result, dict) or not isinstance(result.get("ideas"), list):
            return error("The planner returned an incomplete response. Please try again.", 502)
        return jsonify(result)
    if action == "optimize":
        if not isinstance(result, dict) or not isinstance(result.get("categories"), list):
            return error("The planner returned an incomplete response. Please try again.", 502)
        try:
            total = sum(max(0, float(item["amount"])) for item in result["categories"])
        amounts = [float(item["amount"]) for item in result["categories"]]
        if any(amount < 0 for amount in amounts) or total > event["budget"]:
                return error("The optimized allocation exceeded your budget. Please try again.", 502)
        except (KeyError, TypeError, ValueError):
            return error("The planner returned an incomplete response. Please try again.", 502)
        event["plan"]["budget"] = result
        get_db().execute("UPDATE events SET plan=? WHERE id=?", (json.dumps(event["plan"]), event_id))
        get_db().commit()
        return jsonify(result)
    if not isinstance(result, str):
        result = json.dumps(result)
    return jsonify(answer=result)
