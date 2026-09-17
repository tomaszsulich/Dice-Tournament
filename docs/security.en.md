[Polski](https://github.com/tomaszsulich/Dice-Tournament/blob/main/docs/security.md) | English

# Security

## Trust model

The backend is authoritative for identity, permissions, tournament state, dice results and scoring.<br>
Client-supplied identifiers never grant a tournament relation.<br>
WebSockets carry updates and cannot execute domain commands.

Accounts have no global organizer flag.<br>
Organizer access comes from `TournamentOrganizer`;
player access comes from `TournamentParticipant`
linked to the actor's `PlayerProfile`.<br>
A superuser is a system administrator, not an implicit organizer of every event.

## Authentication and sessions

- JWT is accepted through a header or HttpOnly cookies;
- cookie-authenticated mutations require valid CSRF;
- access tokens last 15 minutes; rotating refresh tokens last at most 8 hours;
- session families enforce inactivity and absolute expiry limits;
- logout, expiry and session violations revoke the family;
- password reset does not disclose whether an email address exists;
- production requires HTTPS, secure cookies, explicit hosts and `DEBUG=False`.

## Authorization

Every endpoint evaluates the actor's relationship to the resolved object.
A player may issue commands only for their active turn.<br>
Organizers are limited to assigned tournaments.<br>
Players can read only their own completed history;
cross-tournament comparison belongs to an organizer or system administrator.

Django Admin is a diagnostic interface.
It neither replaces the organizer dashboard nor creates domain relationships implicitly.

## Integrity and concurrency

Mutations are atomic.<br>
Row locks and database constraints protect the final registration place,
lifecycle transitions, round creation, active turns,<br>
category use and the single tie-break decision.<br>
Turn commands share one lock order: `Game → Turn`.

Roll and category commands use idempotency keys.<br>
Retrying after a lost response does not create a second result.<br>
Real-time events and tasks are dispatched only from `transaction.on_commit()`.

Normal gameplay treats `Roll` records as append-only and stores all five dice.<br>
Participant names are snapshotted at entry; profile edits do not rewrite history.<br>
The API rejects identical assignments where they would be semantic no-ops.

## Abuse controls

Separate throttles cover login, refresh, password reset, general mutations, game commands and registration.<br>
Django password validators remain enabled.<br>
Errors do not expose secrets or another user's data.<br>
Missing objects and denied access may deliberately share a `404` response.

## Secrets and demo data

Secrets come from environment variables.<br>
`.env.example` contains placeholders; the local `.env` is never committed.<br>
Seeding requires both `DEBUG=True` and `ALLOW_DEMO_SEED=true`.<br>
`--reset-database` is deliberately destructive and PostgreSQL-only.<br>
Manual evidence must not include `DEMO_PASSWORD`, tokens, cookies or personal data.

## Operations and dependencies

Health checks separate liveness from readiness.<br>
PostgreSQL and Redis are not public application services.<br>
CI installs repository dependencies and checks Ruff,
Django configuration, migrations and the complete test suite.<br>
Dependency updates and deployment remain explicit maintenance activities.

## Known MVP boundaries

The MVP does not include WebAuthn, public result APIs,
a full `AuditEvent` subsystem, cancelled-event retention or a correction workflow.<br>
Those gaps must not be bypassed with a weaker administrative endpoint.<br>
Each future feature requires its own permission and threat-model review.
