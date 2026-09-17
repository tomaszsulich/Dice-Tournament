[Polski](decisions.md) | English

# Product and technical decisions

## Document status

This is a compact decision record for the completed MVP.<br>
The canonical plans under [`docs/plans/`](plans/01_system_specification.en.md) remain the primary definition of product scope.

## Accepted decisions

### Modular Django monolith

A single deployable application keeps transactions and consistency manageable.<br>
Domain modules, services and selectors provide separation without premature microservices.

### PostgreSQL everywhere meaningful

Development, tests and production rely on row locks, constraints and real concurrency semantics.<br>
SQLite is not an equivalent environment for those contracts.

### REST owns state; WebSockets deliver it

Commands use REST.
WebSockets publish after commit and reconnect always ends with a REST snapshot.
This avoids a second mutation path.

### Relationship-based roles

An account is neutral. Organizer and player access are relationships to a specific tournament.<br>
A global organizer flag would grant excessive authority.

### One profile, many entries, durable snapshots

`PlayerProfile` is reused rather than copied into each tournament.<br>
The entry stores only the name snapshot needed for history, so later profile edits cannot rewrite past events.

### Complete `Roll` snapshots

Every roll stores all five values and hold flags, even when some dice were not thrown again.
Replay never has to reconstruct state from deltas.

### Raw-score ranking

Group ranking and comparison aggregate `raw_score`.<br>
`final_score` does not replace that contract and remains available for future settlement mechanics.

### Explicit controlled draw

Overtime repeats for players who remain tied.<br>
A draw is an auditable organizer command in `OVERTIME` when another game is objectively impossible.<br>
The stored decision is durable and replayed on retry.

### Celery stays outside gameplay

Notifications and maintenance are asynchronous.<br>
Rolls, holds, scoring and turn advancement remain synchronous so the user immediately receives a binding result.

### Two explicit development routes

Host-local development uses local Python, Daphne and PostgreSQL and may borrow Docker Redis.<br>
Docker development starts the complete Compose stack.<br>
The README keeps these routes separate and explains port collisions.

### Bilingual documentation

Polish is the unsuffixed file; English uses `.en.md`.
The language switch is the first element and targets the same anchor.<br>
Both versions communicate the same decisions in natural prose
instead of mirroring each sentence mechanically.

## Intentionally excluded from the MVP

- knockout brackets and formal `Stage`, `Group`, `Match` models;
- persistent teams and team rankings;
- public results, exports and charts;
- WebAuthn, SMS and a 3D client;
- a complete audit, alert and correction subsystem;
- strategic category recommendations;
- infinite history scrolling;
- business logic in WebSocket consumers;
- repository secrets or automatic production seeding.

## Later releases

V1 may add knockout play, full auditing and corrections.<br>
V2 may introduce persistent teams, analytics and additional clients.<br>
Each extension requires an explicit product decision instead of silently expanding the MVP.
