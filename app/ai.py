import json
import os
from datetime import date


REQUIRED_SECTIONS = ("event_summary", "budget", "timeline", "vendors", "ideas", "guest_plan", "food_plan", "risks", "next_steps")


class AIServiceError(Exception):
    pass


def parse_plan(raw):
    if isinstance(raw, dict):
        data = raw
    else:
        value = str(raw).strip()
        if value.startswith("```"):
            value = value.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        try:
            data = json.loads(value)
        except (json.JSONDecodeError, TypeError) as exc:
            raise AIServiceError("The planner returned an unreadable response. Please try again.") from exc
    if not isinstance(data, dict) or any(key not in data for key in REQUIRED_SECTIONS):
        raise AIServiceError("The planner returned an incomplete plan. Please try again.")
    for key in ("timeline", "vendors", "ideas", "risks", "next_steps"):
        if not isinstance(data[key], list) or any(not isinstance(item, dict) for item in data[key]):
            raise AIServiceError("The planner returned an incomplete plan. Please try again.")
    if not isinstance(data["budget"], dict) or not isinstance(data["guest_plan"], dict) or not isinstance(data["food_plan"], dict):
        raise AIServiceError("The planner returned an incomplete plan. Please try again.")
    if not isinstance(data["event_summary"], str) or not isinstance(data["budget"].get("categories"), list):
        raise AIServiceError("The planner returned an incomplete plan. Please try again.")
    if any(not isinstance(item, dict) for item in data["budget"]["categories"]):
        raise AIServiceError("The planner returned an incomplete plan. Please try again.")
    return data


def _prompt(context, action="plan", extra=None):
    brief = {key: context.get(key) for key in ("name", "event_type", "event_date", "location", "guests", "budget", "currency", "style", "food_preference", "priority", "notes")}
    today = date.today().isoformat()
    instructions = "Create a practical, personalized event plan that respects the budget and event date. Include realistic budget categories whose sum does not exceed the total, dated timeline milestones, actionable vendor checklist items, personalized ideas, guest planning, food plan, practical risks with mitigations and backups, and prioritized next steps. For community events cover permits, crowd safety, volunteers, facilities, and waste. For birthdays cover cake, activities, food, and guest experience. For weddings include detailed venue, catering, decor, photography, attire, entertainment, invitations, transport, accommodation and contingency planning where relevant. Return valid JSON only, with keys event_summary, budget, timeline, vendors, ideas, guest_plan, food_plan, risks, next_steps. Budget must have categories array with category, amount, priority fields. Timeline items need title, date, description, priority, status. Vendor items need category, service, priority, status, notes. Ideas need title, description, cost_level, reason. Risks need risk, likelihood, impact, mitigation, backup_plan. next_steps items need task, priority, reason, timing, status. No markdown fences. Current date: " + today
    if action == "chat":
        instructions = "You are Celebrio AI Planner. Answer using the supplied event context and plan. Be concrete, concise, and safety-conscious. Do not invent vendor bookings or claim actions were completed. If asked to change the plan, suggest specific edits."
    elif action == "ideas":
        instructions = "Create six fresh, event-specific ideas that fit the event context. Return valid JSON only as {\"ideas\":[{\"title\":string,\"description\":string,\"cost_level\":string,\"reason\":string}]} with no markdown."
    elif action == "optimize":
        instructions = "Optimize the current event budget for the user's priority. Keep every amount nonnegative and total at or below the budget. Return valid JSON only as {\"categories\":[{\"category\":string,\"amount\":number,\"priority\":string}],\"summary\":string} with no markdown."
    return instructions + "\nEvent context: " + json.dumps(brief, ensure_ascii=False) + ("\nCurrent plan: " + json.dumps(context.get("plan", {}), ensure_ascii=False) if context.get("plan") else "") + ("\nUser request: " + str(extra) if extra else "")


def generate(context, action="plan", extra=None):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise AIServiceError("Gemini is not configured yet. Add GEMINI_API_KEY to the server environment and try again.")
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"), contents=_prompt(context, action, extra))
        output = response.text
    except AIServiceError:
        raise
    except Exception as exc:
        raise AIServiceError("Gemini could not complete that request. Please try again in a moment.") from exc
    if action == "plan":
        return parse_plan(output)
    if action == "chat":
        if not isinstance(output, str) or not output.strip():
            raise AIServiceError("The planner returned an empty response. Please try again.")
        return output.strip()
    value = str(output).strip()
    if value.startswith("```"):
        value = value.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        parsed = json.loads(value)
    except (json.JSONDecodeError, AttributeError) as exc:
        raise AIServiceError("The planner returned an unreadable response. Please try again.") from exc
    return parsed
