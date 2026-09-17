[Polski](api.md) | English

# API

## Contract source

The generated OpenAPI schema at `/api/schema/` is the authoritative HTTP reference.
Swagger UI is available at `/api/docs/`.<br>
Both are restricted to system administrators.
Files under [`manual-api/`](../manual-api/README.en.md) provide runnable examples;<br>
they do not replace the schema or automated contract tests.

## Authentication

The API accepts JWT through `Authorization: Bearer …` or HttpOnly cookies.
Cookie-authenticated mutations require CSRF.<br>
Access tokens are short-lived, refresh tokens rotate, and logout revokes the whole session family.

Core account endpoints:

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/auth/users/` | account registration |
| POST | `/api/auth/jwt/create/` | login and session-family creation |
| POST | `/api/auth/jwt/refresh/` | token-pair rotation |
| POST | `/api/auth/logout/` | session revocation |
| POST | `/api/auth/users/set-password/` | authenticated password change |
| POST | `/api/auth/users/reset-password/` | non-enumerating reset request |
| POST | `/api/auth/users/reset-password-confirm/` | new password confirmation |
| GET/PATCH | `/api/profile/` | profile read or genuine update |

## Tournaments

| Method | Path | Permission / meaning |
|---|---|---|
| POST | `/api/tournaments/create/` | create a tournament |
| GET | `/api/tournaments/` | actor-scoped list |
| GET/PATCH | `/api/tournaments/{id}/` | details; configuration before start |
| POST | `/api/tournaments/{id}/open-registration/` | organizer |
| POST | `/api/tournaments/{id}/close-registration/` | organizer |
| POST | `/api/tournaments/{id}/participants/` | organizer-managed entry |
| POST | `/api/tournaments/{id}/join/` | self-registration in `OPEN` mode |
| POST | `/api/tournaments/{id}/leave/` | leave before the event starts |
| POST | `/api/tournaments/{id}/start/` | organizer, valid field required |
| POST | `/api/tournaments/{id}/complete/` | organizer, all games complete |
| GET | `/api/tournaments/{id}/ranking/` | ranking from raw scores |

## Gameplay and round barrier

| Method | Path | Contract |
|---|---|---|
| GET | `/api/games/{id}/state/` | authoritative game snapshot |
| POST | `/api/games/{id}/roll/` | active turn owner's roll |
| PUT | `/api/games/{id}/holds/` | set all five hold flags |
| POST | `/api/games/{id}/choose-category/` | persist category and score |
| POST | `/api/rounds/{id}/barrier/` | evaluate round completion |
| POST | `/api/rounds/{id}/draw/` | controlled draw during overtime |

Roll and category commands require the idempotency key documented in the schema.<br>
A retry with the same fingerprint replays the stored response;
reusing the key for a different command is a conflict.<br>
Holds are full state assignments and reject semantic no-ops.

## Dashboard, history and comparisons

| Method | Path | Scope |
|---|---|---|
| GET | `/api/tournaments/{id}/organizer-dashboard/` | tournament organizer |
| GET | `/api/comparisons/participants/{id}/` | organizer or administrator |
| GET | `/api/comparisons/participants/{id}/history/` | authorized replay / own history |

History is paginated and ordered by round, table, turn and roll number.<br>
Every entry contains all five dice and hold flags;
category and score appear where a completed decision applies.

## Errors and rate limits

DRF errors have stable HTTP status codes and a shared shape documented in OpenAPI.<br>
Object permissions are checked after resolving identifiers; request data cannot widen actor scope.<br>
Authentication, general mutations, game commands and registration use separate throttles.<br>
`429 Too Many Requests` is an expected contract response.

## WebSockets

WebSockets publish a limited table or organizer snapshot after commit.
They do not execute domain commands.<br>
After reconnect, the client fetches REST state,
so a missed event cannot become authoritative drift.
