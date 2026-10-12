# Mini Ticket Tracker

A small support-ticket tracker built with Django and PostgreSQL. A JSON REST API and a
server-rendered single-page UI (HTMX) share one model and one set of validation rules.

## Stack

| Layer    | Choice                                                     |
|----------|------------------------------------------------------------|
| API      | Python 3.12+, Django 5.2 LTS (plain views, no DRF)         |
| Database | PostgreSQL 16 via psycopg 3, Django migrations             |
| UI       | Django templates + HTMX 2 (no JavaScript build step)       |
| Tests    | Django `TestCase` against a real Postgres test database    |

## Running it

### 1. Start PostgreSQL

The quickest route is the bundled compose file, which runs Postgres only and maps it to port
`55432` to avoid clashing with a local install:

```bash
docker compose up -d db
```

Using your own Postgres instead is fine: set `DATABASE_URL`
(default `postgres://tickets:tickets@localhost:55432/tickets`).

### 2. Install and run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python manage.py migrate
python manage.py runserver        # UI at http://localhost:8000, API under /tickets
```

The API and the UI are served by the same Django process, so there is nothing else to start.

### Running the tests

```bash
python manage.py test
```

Django creates and destroys a `test_tickets` database on the same server, so the database user
needs `CREATEDB` (the compose user has it).

- `tickets/tests/test_api.py`: create (defaults, trimming, persistence, validation), list
  (status filter, pagination, ordering, bad params), update (partial, 404, non-updatable field)
  and stats.
- `tickets/tests/test_ui.py`: the HTMX views render, validate, mutate and send the refresh trigger.

## API

All responses are JSON. Errors share one shape:

```json
{ "error": { "code": "validation_error", "message": "Request validation failed",
             "fields": { "title": "is required" } } }
```

| Method  | Path             | Notes |
|---------|------------------|-------|
| `POST`  | `/tickets`       | Body: `title` (required, 1–200 characters after trimming), `description`, `priority` (default `medium`), `status` (default `open`). Returns `201`. |
| `GET`   | `/tickets`       | Query: `status`, `page` (default 1), `limit` (default 20, max 100). Returns `{ data, pagination: { page, limit, total, total_pages } }`, newest first. |
| `PATCH` | `/tickets/<id>`  | Body: `status` and/or `priority`. Other fields are rejected with `400`; unknown id is `404`. |
| `GET`   | `/tickets/stats` | `{ "open": n, "in_progress": n, "closed": n }`, always all three keys. |

```bash
curl -X POST localhost:8000/tickets -H 'Content-Type: application/json' \
  -d '{"title": "Printer on fire", "priority": "high"}'
curl 'localhost:8000/tickets?status=open&page=1&limit=10'
curl -X PATCH localhost:8000/tickets/1 -H 'Content-Type: application/json' -d '{"status": "closed"}'
curl localhost:8000/tickets/stats
```

## How the UI works

`/` renders the full page. HTMX then handles the interactions without a page reload:

- **Create:** the form posts to `/ui/tickets/new` and is swapped back in, either with field
  errors or reset after a successful save.
- **Change status:** each row's `<select>` posts to `/ui/tickets/<id>/status` on change.
- **Refresh:** after a successful create or status change, the server responds with
  `HX-Trigger: tickets-changed`. The list and the stats panel listen for that event and re-fetch
  themselves, keeping the current filter and page. No view needs to know which parts of the page
  depend on it.
- **Filter and pagination:** these are links that swap the list and push the URL, so `/?status=closed&page=2` is bookmarkable and works without JavaScript.

## Project layout

```
config/                settings (env-driven), root URLs, JSON 404/500 handlers
tickets/
  models.py            Ticket, Status/Priority choices, CHECK constraints, indexes
  forms.py             validation shared by the API and the UI
  api.py               JSON endpoints
  views.py             HTMX page + partials
  templates/tickets/   index.html and partials/
  tests/               API and UI tests
```

## Decisions & Tradeoffs

I chose plain Django views over Django REST Framework. Four endpoints over one model don't need
serializers or viewsets, and keeping validation in Django forms lets the JSON API and the HTMX UI
enforce exactly the same rules. Status and priority are `TextChoices` backed by `VARCHAR` columns
plus database `CHECK` constraints, because Django's choices are only enforced by forms and I wanted
the table itself to reject bad values. HTMX gives a single-page feel with no frontend build. The
server owns all rendering, and the `tickets-changed` event keeps the list and stats in sync without
the mutation views knowing about either panel. The cost is a little less interactivity than a SPA,
for example no optimistic updates. The API is `csrf_exempt` because it is a token-less JSON API,
while the UI endpoints stay CSRF-protected through an `X-CSRFToken` header on every HTMX request.
Pagination is offset-based on `-created_at, -id` with matching indexes, which is fine at this scale
but would move to keyset pagination for large tables. Shortcuts I took: no authentication, no admin,
HTMX loaded from a CDN (pinned with an SRI hash) rather than vendored, and Django's debug 404 page
appears for unmatched URLs while `DEBUG=1`. With more time I'd add auth, an OpenAPI schema, browser
tests for the HTMX flows, CI against a Postgres service container, and a production setup
(gunicorn, WhiteNoise, container image).

### Assumptions

- `id` is an auto-incrementing integer; UUIDs weren't needed for a single-database app.
- A new ticket may be created with any status, but defaults to `open` / `medium`.
- A blank description is stored as `NULL`.
- `limit` above 100 is rejected rather than silently clamped.
- Stats count all tickets and ignore the list's filter and pagination.
- The UI shows 10 tickets per page; invalid filter or page values in the UI URL fall back to
  defaults instead of erroring, while the API rejects them.
