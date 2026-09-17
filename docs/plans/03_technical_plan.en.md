[Polski](03_technical_plan.md) | English

# Technical plan — dice tournament management

## 1. Purpose and scope

This plan maps the product contract to a Django implementation for a complete group-stage MVP.
It favors database-backed invariants, explicit services<br>and observable behavior.
Later stage and team features remain extension points.

## 2. System architecture

### Components

- Python 3.12, Django and Django REST Framework;
- Djoser and SimpleJWT for account operations and JWT;
- PostgreSQL for authoritative state and locking;
- Daphne and Channels for ASGI/WebSockets;
- Redis for Channels and Celery brokering;
- Celery workers for `notifications` and `maintenance`, plus Beat;
- drf-spectacular for OpenAPI;
- Django templates, CSS and JavaScript for the browser UI.

### Domain boundary

Tournament orchestration owns lifecycle, registration, allocation, rounds,
ranking and tie resolution. Dice gameplay owns turns, rolls, holds, categories
and scoring. They share explicit persistence models but not implicit frontend state.

### Layers

Views parse and return HTTP. Serializers validate transport data.
Services execute transactional commands. Selectors build read models.
`domain/` contains pure rules. Models and constraints preserve state.
Realtime and Celery adapters act only after commit.

## 3. Data model

### Identity and entry

Custom `User`; optional one-to-one `PlayerProfile`; many-to-many organizer assignment;
unique tournament/profile entry with active status<br>and historical name snapshots.

### Tournament structure

`Tournament` contains MVP configuration and status.
`Round` is unique by tournament and number and distinguishes group from overtime.
`Game` represents a table; `GameParticipant` stores seat order, completion and scores.

### Dice state

`Turn` belongs to one game participant.
`Roll` stores number, five dice, hold flags, source and timestamp.
`ScoreEntry` stores one category and calculated score.
Unique constraints prevent repeated categories and roll numbers.

### Replay and audit

Rolls and category decisions are the gameplay record.
`IdempotencyRecord` stores request fingerprints and responses.<br>
`TieBreakDecision` stores one controlled draw per round.
A broad `AuditEvent` subsystem is postponed to V1.

## 4. Lifecycles and rules

### Tournament

Only services transition `DRAFT → REGISTRATION → ACTIVE → COMPLETED`
and freeze result-affecting configuration after start.

### Turn

The first roll throws five dice. Later rolls change only unheld positions
and stop after the third. Holds are a five-boolean assignment.<br>
A legal unused category records the score and advances the turn.

### Allocation

Calculate table sizes of 2–6 with a maximum difference of one.
Build ranking baskets and snake candidates.
Minimize repeated opponents and equal team-label pairings;
use a supplied seed only to select between equal minima.

### Rankings and ties

Aggregate `raw_score`. Compare descending round vectors after totals.
Create overtime only for the material tie. Controlled draw is restricted to overtime,<br>
requires an authorized organizer and reason, and replays the existing durable decision.

## 5. Scoring engine

Expose a registry of 18 strategies: six School values and twelve figures.
Strategies accept immutable dice context and return structured results.<br>
The service validates category availability and variant before persisting.
No binding score is calculated in JavaScript.

## 6. REST API and commands

Use function or class views as thin adapters to serializers, permissions,
services and selectors. Mutating gameplay endpoints use stable error codes
and idempotency where repetition could create another effect.
Generated OpenAPI is the primary endpoint reference; `.http` files support manual calls.

## 7. Authentication and authorization

Support header and HttpOnly-cookie JWT. Require CSRF for unsafe cookie requests.
Rotate refresh tokens, blacklist replaced tokens and bind them to a session family with inactivity
and absolute expiry. Scope every resource after lookup; never trust actor or ownership fields from payload data.

## 8. Realtime communication

Channels consumers authenticate the connection and revalidate the actor's relation.
Groups are limited to table or organizer-dashboard scope.<br>
Events carry state/version information and are published from `on_commit`.
Consumers do not execute gameplay. Reconnect fetches a REST snapshot.

Remote mode obtains dice from the backend randomizer. In-person mode accepts a strict five-value payload.
There is no hybrid event.

## 9. Concurrency and idempotency

Wrap domain writes in `transaction.atomic()`. Lock tournament rows for capacity
and lifecycle, and use consistent `Game → Turn` locking for active-turn commands.
Database uniqueness handles last-line races. An idempotency key maps to one actor,
operation and fingerprint; matching retry replays, mismatching reuse conflicts.

## 10. Frontend and UX

Server-render initial pages and enhance them with small JS modules.
The dice surface supports touch and mouse. Native form controls retain keyboard behavior.<br>
Respect `prefers-reduced-motion`. Hide or disable impossible actions,
while keeping the backend authoritative. Use explicit “Load more” for history.

## 11. Performance and scale

Target 128 active participants. Dashboard selectors eager-load related records
and have a fixed query-profile test. Return all active tables without pagination.<br>
Paginate historical rolls and completed-event lists where growth is unbounded.
Add cache only for measured read costs; never use cache as domain truth.

## 12. Security and integrity

Read secrets from env. Production sets `DEBUG=False`, explicit allowed hosts,
secure cookies, HTTPS redirect and HSTS.<br>
Apply password validators, reset non-enumeration and endpoint-specific throttling.<br>
Preserve snapshots and reject semantic no-op updates. Demo seed is development-only.

## 13. Celery

Route invitations to `notifications`.
Route expired idempotency cleanup and expired token cleanup to `maintenance`.
Beat schedules maintenance.<br>
Enqueue tasks only after database commit. Gameplay remains synchronous.

## 14. Testability

Use pytest markers that describe real test characteristics.
Pure domain tests need no infrastructure; ORM, permission and API tests use Django and PostgreSQL;
concurrency tests require native PostgreSQL behavior; Channels and Celery use deterministic test configuration
where their transport is not the subject.<br>
Ordinary pytest must not require Docker.
Compose smoke is explicit opt-in.

CI runs Ruff, format check, Django check, migration check and migrations, then the full test suite with coverage except
for one expensive completed-demo case,<br>which runs separately without coverage.

## 15. Observability and operational audit

Provide liveness and readiness endpoints, structured application logs and diagnostic admin views.
Do not log passwords, tokens or cookies.<br>
Full business audit events, alerts and correction records belong to V1.

## 16. Environments and deployment

Keep `development`, `test` and `production` settings. Host-local developmentuses Python/Daphne and PostgreSQL
and may start Redis through Docker.<br>
Docker development starts the full stack with migration and optional seed services.
Document port overrides when both routes coexist.<br>
Production uses the runtime Docker target and external secrets; public infrastructure is deployment work,
not part of the local MVP.

## 17. Roadmap and extension points

MVP completes the group tournament.<br>
V1 adds formal stages, knockout matches, auditing, alerts, correction and cancellation retention.<br>
V2 adds persistent teams, team analytics and additional clients.<br>
Existing source-of-truth and permission rules remain mandatory when those modules are introduced.
