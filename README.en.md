[Polski](README.md) | English

# Dice Tournament

Dice Tournament is a Django application for running group-stage dice tournaments.<br>
Organizers configure events, manage entrants and monitor every table live.<br>
Players take their own turns and can revisit a complete roll history after a tournament has finished.

The MVP supports up to 128 active entrants, remote and in-person play, concurrent tables, group rankings, overtime rounds<br>
and comparisons across one to four completed tournaments.

## What the MVP does

- neutral user accounts with tournament-scoped organizer and player roles;
- organizer-managed or open tournament registration;
- balanced tables of 2–6 players, ranking baskets and snake allocation;
- three rolls per turn, dice holds and 18 scoring categories;
- authoritative server-side scoring and five-die snapshots for every roll;
- independently progressing tables with a barrier between rounds;
- a WebSocket-powered organizer dashboard;
- private player history and read-only organizer replay;
- comparisons across completed tournaments;
- separate Celery queues for notifications and maintenance;
- OpenAPI, Swagger, automated tests and reproducible demo worlds.

## Deliberate MVP boundary

This release delivers a complete group-stage tournament.<br>
Knockout brackets, persistent teams, public results, a full audit subsystem and exports are later work.<br>
See [decisions](docs/decisions.en.md) for the trade-offs and features that were intentionally left out.

## Architecture at a glance

Django and Django REST Framework run against PostgreSQL.<br>
Daphne serves the ASGI application, Channels uses Redis for WebSocket delivery
and Celery handles background work.<br>
The browser UI is server-rendered HTML enhanced with CSS and JavaScript.<br>
Tournament orchestration and dice rules are separate domains inside the `tournaments` application.

Read more:

- [architecture](docs/architecture.en.md),
- [API](docs/api.en.md),
- [security](docs/security.en.md),
- [product and system plans](docs/plans/01_system_specification.en.md).

## Requirements

- Python 3.12;
- PostgreSQL;
- Redis;
- Git;
- optionally Docker with Docker Compose.

Commands below start in the repository root.<br>
Local Daphne is the one exception: `config.asgi` is imported from `src`, so change into that directory before starting the server.

## Local development

This route runs Python, Django, Daphne and PostgreSQL on the host.
Redis may run locally or as the only Docker service.

### 1. Create the Python environment

```powershell
python -m pip install uv==0.12.15
uv sync --frozen
.\.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
```

The committed `uv.lock` is the dependency source of truth for local development, Docker and CI.<br>
Regenerate it only as part of a deliberate `pyproject.toml` dependency update.

Give `.env` a fresh `SECRET_KEY` and valid local PostgreSQL credentials.<br>
To use demo data, also set `ALLOW_DEMO_SEED=true` and `DEMO_PASSWORD`.<br>
Never commit the resulting `.env` file.

### 2. Start PostgreSQL and Redis

Create the database and user described by `DATABASE_URL`.
Redis must be running before using the WebSocket-enabled UI.<br>
If Redis is not installed locally, run:

```powershell
docker compose up -d redis
```

That exposes Redis at `127.0.0.1:6379` by default.<br>
If a full Docker stack or another process already owns the port, set `REDIS_HOST_PORT` for Compose and use the matching port<br>
in local `REDIS_URL` and `CELERY_BROKER_URL`.<br>
A local web process and the Docker web service cannot share a host port either;
change `WEB_HOST_PORT` when both environments are needed.

### 3. Apply migrations and run Daphne

```powershell
python src/manage.py migrate
python src/manage.py check
Set-Location src
daphne -b 127.0.0.1 -p 8000 config.asgi:application
```

Open `http://127.0.0.1:8000/login/`.<br>
Stop Daphne with `Ctrl+C`, then return to the repository root with `Set-Location ..`.

### 4. Optional Celery processes

Run each command in a separate terminal from the repository root:

```powershell
celery -A config --workdir=src worker -Q notifications --loglevel=INFO
celery -A config --workdir=src worker -Q maintenance --loglevel=INFO
celery -A config --workdir=src beat --loglevel=INFO
```

## Docker development

This route starts separate containers for Daphne, PostgreSQL, Redis, two Celery workers and Beat.<br>
It does not require host Python or PostgreSQL.

```powershell
Copy-Item .env.example .env
docker compose up --build
```

After the health checks pass, visit `http://127.0.0.1:8000/login/`.<br>
The one-shot `migrate` service applies database migrations.<br>
Override `WEB_HOST_PORT` for the web port and `REDIS_HOST_PORT` for the Redis port exposed to the host.

Stop the stack without removing database data:

```powershell
docker compose down
```

Removing the PostgreSQL volume is destructive and is not part of the normal shutdown procedure.

## Demo data

Seeding is accepted only with `DEBUG=True` and `ALLOW_DEMO_SEED=true`.<br>
Supported sizes are `16`, `64` and `128`; the command help lists the available scenarios.

Local command:

```powershell
python src/manage.py seed_demo --size 16 --scenario completed --seed 20260831
```

Docker exposes seeding as an explicit tools profile:

```powershell
docker compose --profile tools run --rm seed-demo python src/manage.py seed_demo --size 16 --scenario completed --seed 20260831
```

`--reset` replaces only the matching demo namespace.<br>
`--reset-database` clears all local application data and restarts PostgreSQL identities;<br>
use it only when that destructive development action is intended.<br>
Demo passwords are local secrets and must not appear in committed evidence.

## API and operational endpoints

- OpenAPI schema: `/api/schema/`;
- Swagger UI: `/api/docs/`;
- Django Admin: `/admin/`;
- health checks: `/health/live/` and `/health/ready/`;
- ready-to-run HTTP examples: [`manual-api/`](manual-api/README.en.md).

The schema and Swagger UI are restricted to system administrators.
The API contract is summarized in [docs/api.en.md](docs/api.en.md).

## Tests and quality checks

Regular pytest does not require Docker.<br>
Test settings still use PostgreSQL, while Channels and Celery switch to deterministic in-process test backends.

```powershell
pytest
python -m ruff check .
python -m ruff format --check .
python src/manage.py check
python src/manage.py makemigrations --check --dry-run
```

CI runs the complete suite with coverage except for one expensive `completed` demo case, which runs separately without coverage.<br>
The Compose smoke test is an explicit opt-in:

```powershell
pytest -m compose_smoke --run-compose-smoke
```

Do not run the Compose smoke test alongside another stack that owns the same ports.

## Roles and security

Accounts are neutral.<br>
A user becomes an organizer through a relation to a specific tournament and a player through a `PlayerProfile` participation.<br>
Superusers have system-wide administration privileges but do not automatically become tournament organizers.<br>
The backend authorizes every domain mutation; gameplay uses transactions, row locks and idempotency keys.<br>
See [docs/security.en.md](docs/security.en.md) for the threat boundaries.

## Roadmap

- **MVP:** complete group tournament, history, live updates and comparisons;
- **V1:** knockout play, full auditing, alerts and correction workflows;
- **V2:** persistent teams, team analytics and additional clients.
