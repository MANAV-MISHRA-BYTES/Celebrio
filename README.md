# Celebrio

AI Event Planning, Simplified

## 1. Overview

Celebrio is a responsive event planning workspace for turning a wedding, birthday, or community celebration into an actionable plan. It keeps budgets, milestones, service checklists, guest estimates, menu suggestions, risks, and next steps together.

## 2. Challenge

Celebrio addresses Challenge 5: Celebration & Event Planner.

## 3. Problem Statement

Planning a celebration means coordinating budgets, people, dates, services, and personal details across many places. Celebrio creates one structured starting plan and helps organizers refine and track it.

## 4. Features

- Guided four-step event creation with server-side validation
- Gemini-generated event plan with event-specific budget, milestones, vendor checklist, ideas, guest and food planning, risks, and next steps
- Persistent SQLite event, task, vendor, and guest-category data
- Budget breakdown, remaining-budget calculation, visual allocation chart, and Gemini budget optimization
- Timeline and next-step completion tracking
- Vendor status tracking without marketplace or booking claims
- Guest-group estimates and confirmations
- Gemini idea refresh and contextual planning chat
- Responsive layout, loading feedback, validation and recovery messages

## 5. Supported Event Types

- Wedding
- Birthday
- Community Event

## 6. How It Works

1. Enter an occasion, event details, preferences, and notes.
2. The Flask server validates the request and sends only the planning context to Gemini.
3. Celebrio validates the structured response, stores it in SQLite, and opens an event workspace.
4. Track tasks and vendor status, adjust guest estimates, and ask the planner for refinements.

## 7. AI Architecture

`app/ai.py` is the dedicated Gemini service. It uses the Google Gen AI Python SDK, reads `GEMINI_API_KEY` and optional `GEMINI_MODEL` from the server environment, asks for JSON-only output, and validates the required plan sections before storage. Follow-up actions use the same event context for chat, more ideas, and budget optimization. Missing credentials, API errors, and invalid responses return controlled messages. There is no fake AI fallback. The browser never receives the API key.

## 8. Technology Stack

- Python and Flask
- SQLite with parameterized SQL
- Google Gemini through `google-genai`
- Jinja templates, accessible HTML, vanilla JavaScript, and CSS
- pytest and Gunicorn

## 9. Project Structure

```text
app/
  ai.py
  db.py
  routes.py
  static/
    app.js
    style.css
  templates/
tests/
  conftest.py
  test_app.py
.env.example
Procfile
requirements.txt
wsgi.py
```

## 10. Installation

Python 3.10 or newer is recommended.

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set a valid Gemini API key in `.env` before using AI generation. The app runs without a key, but AI actions return a clear configuration error.

## 11. Environment Variables

| Variable | Required | Purpose |
| --- | --- | --- |
| `GEMINI_API_KEY` | For AI features | Gemini API credential, server-side only |
| `GEMINI_MODEL` | No | Gemini model identifier; defaults to `gemini-3.8-flash` |
| `SECRET_KEY` | Production | Flask session and signing secret |
| `DATABASE_PATH` | No | SQLite file location; defaults inside `instance/` |

Never commit `.env` or production secrets.

## 12. Running Locally

```powershell
flask --app wsgi run --debug
```

Open `http://127.0.0.1:5000`. The database initializes automatically. The CLI also provides `flask --app wsgi init-db`.

## 13. Running Tests

```powershell
pytest -q
```

Tests use an isolated temporary SQLite database and mock the Gemini service. They do not require network access or a real API key.

## 14. Deployment

The included `Procfile` runs the WSGI app with Gunicorn. Configure `GEMINI_API_KEY`, `SECRET_KEY`, and, if needed, `DATABASE_PATH` in the deployment platform's environment settings. Provide a persistent writable volume for the SQLite database; an ephemeral filesystem will not preserve event data across restarts. For multi-instance traffic, replace SQLite with a managed relational database before scaling horizontally.

## 15. Security

- API keys stay on the server and are excluded from prompt context.
- The API validates required fields, enumerated choices, date, budget, counts, text lengths, and action payloads.
- SQLite queries use placeholders.
- AI output is parsed and validated before it is shown.
- `.env`, local databases, caches, and virtual environments are ignored by Git.
- This initial version has no user authentication or per-user authorization; deploy only in a trusted demo setting until account isolation is implemented.

## 16. Accessibility

The interface uses semantic headings, associated form labels, accessible names for controls, visible validation messages, keyboard-operable native controls, focus styles, reduced-motion preferences, and live status announcements. Color is not the only signal for task completion.

## 17. Assumptions

- Event dates must be in the future.
- A single local SQLite store is sufficient for a hackathon-scale demonstration.
- The organizer makes vendor contact and booking decisions directly.
- AI recommendations are planning suggestions and need human review.
- Currency is stored as an ISO code and amounts are treated as whole-number budgets.

## 18. Future Improvements

- Authentication, shared planning access, and event ownership
- Email invitations, RSVP collection, and reminders
- PostgreSQL deployment profile and database migrations
- Exportable plans and calendar integration
- Currency-aware decimal formatting and editable plan sections
- Budget history and task audit log
