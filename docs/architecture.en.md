[Polski](architecture.md) | English

# Architecture

## Context

Dice Tournament is a modular Django monolith.
The MVP runs a complete group tournament and keeps one authoritative state in PostgreSQL.<br>
REST carries commands and snapshots; WebSockets only deliver updates for state that has already committed.

## Components

| Component | Responsibility |
|---|---|
| Django + DRF | HTTP, input validation, authorization and thin views |
| PostgreSQL | domain state, constraints, transactions and row locks |
| Daphne + Channels | ASGI and narrowly scoped real-time delivery |
| Redis | Channels layer and Celery broker |
| Celery | notifications and scheduled maintenance |
| HTML/CSS/JavaScript | accessible UI and REST snapshot recovery |

## Application modules

`accounts` owns neutral identities, optional `PlayerProfile` records, JWT,
session families, password workflows and throttling.<br>
`tournaments` contains the tournament and dice domains, dashboard selectors, real-time adapters and tasks.<br>
`api` provides the shared error contract and schema extensions.

Views stay thin. Services execute mutations, selectors shape reads, and pure rules live under `domain/`.<br>
Models hold state and database constraints without becoming a hidden orchestration layer.

## Two domain boundaries

### Tournament

Lifecycle, registration, entrants, rounds, tables, allocation, rankings, ties, overtime and controlled draws.
Group rankings aggregate `raw_score`.

### Dice game

Turns, up to three rolls, holds, category selection and scoring.<br>
Every `Roll` is a complete five-die snapshot, and the first roll always throws all five.

The boundaries meet through explicit `Game`, `GameParticipant`, `Turn`, `Roll` and `ScoreEntry` records.<br>
The browser never calculates an authoritative score.

## Command path

1. DRF authenticates the actor and validates input.
2. A service checks the actor's tournament or game relation.
3. `transaction.atomic()` and `select_for_update()` protect concurrent writes.
4. Database constraints defend invariants outside the expected code path.
5. Idempotent commands persist their response.
6. `transaction.on_commit()` publishes a WebSocket event or queues work.
7. Reconnecting clients fetch a fresh REST snapshot.

Active-turn commands lock rows in `Game → Turn` order.<br>
Tables within a round progress independently; the round barrier is evaluated only after completion.

## Identity and history

A `User` has at most one `PlayerProfile`, reusable across tournaments.<br>
`TournamentParticipant` keeps the historical name snapshot without cloning the profile.<br>
Rolls, holds, chosen categories and scores support replay.<br>
A player can only read their own completed history; organizers are scoped to their events.

## Environments

- `development`: PostgreSQL and Redis, `DEBUG=True`, guarded demo seeding;
- `test`: PostgreSQL, in-memory Channels and eager Celery;
- `production`: `DEBUG=False`, HTTPS-only cookies, SMTP and env secrets;
- Docker development: web, database, Redis, two workers, Beat and migrations.

Docker development and host-local development are separate routes.<br>
A local app may borrow only the Redis container, provided host ports do not collide.

## Scale and read performance

The MVP supports 128 active entrants.<br>
The organizer dashboard intentionally shows every active table without pagination, so selectors use eager loading<br>
and have a query-budget regression test.<br>
Long histories are paginated and exposed through an explicit “Load more” action.

## Extension points

The design leaves room for knockout stages, formal stage models, a complete audit trail and persistent teams.<br>
Those are visible extension points rather than hidden MVP work; see the [plans](plans/01_system_specification.en.md).
