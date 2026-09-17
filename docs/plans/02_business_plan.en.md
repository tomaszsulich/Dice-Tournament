[Polski](02_business_plan.md) | English

# Product plan — dice tournament management

## 1. Product definition

Dice Tournament helps organizers run a multi-table dice event without manual seat calculations,
ambiguous scores or lost game history.<br>Players receive a focused table experience;
organizers receive one live operational view.

The differentiator is not a large catalogue of dice games.
It is a dependable end-to-end tournament: registration, balanced allocation,<br>
concurrent play, authoritative scoring, rankings and replay.

### Target users

- clubs, schools and community organizers running small or medium events;
- participants using a phone or desktop at the assigned table;
- maintainers who need diagnostics and reproducible environments.

### Value proposition

The product reduces setup work, prevents contradictory calculations, makes concurrent tables observable
and turns the completed event into inspectable history.<br>Its main hypotheses are that organizers value correctness
and live overview more than advanced visualization, and that players can use the game
without training<br>when only legal actions are offered.

## 2. Core assumptions

Tournament orchestration and one five-dice game belong to the same product but remain separate domains.
The event is explicitly remote or in-person.<br>REST is authoritative; WebSockets improve timeliness.
PostgreSQL is required wherever concurrency matters.

## 3. User requirements

### Shared account needs

Users can register, authenticate, refresh and end sessions, manage passwords
and keep one optional player profile. Password reset must not reveal account existence.

### Organizer needs

An organizer can create an event, add co-organizers, configure registration
and rules, manage entrants, start play, monitor tables, resolve eligible ties,
complete the event, replay results and compare completed tournaments.

### Participant needs

A participant can join when registration permits, discover the assigned table,
play only when active, reconnect safely and inspect only their own completed history.

### Administrator needs

The system administrator can diagnose the installation through Django Admin,
OpenAPI and health endpoints without being treated as an ordinary tournament organizer by default.

## 4. Functional specification

### Accounts and access

Roles are tournament relationships, not account flags.
All mutations are authenticated and object-scoped.
Cookie JWT mutations require CSRF;<br>header JWT remains suitable for explicit API clients.

### Tournament setup

The organizer selects limits, rounds, table preference, scoring variant,
event mode, timezone and registration policy before start.
Up to 128 people may be active.<br>Open registration handles the final place atomically.

### Rounds and tables

Each group round seats every active participant exactly once. Tables contain
2–6 people and are balanced. Ranking baskets, snake allocation, rematch cost<br>
and `team_label` separation produce a deterministic best allocation for the seed.

### Dice play

A turn starts with all five dice, permits at most three rolls and allows holds
only after a roll. The player selects one unused category; the backend calculates
the result.<br>All five dice and hold flags are retained for every roll.

### Concurrent operations

Tables advance independently. The organizer dashboard shows every active table,
connection state and actionable problems without paging.<br>
A round barrier opens the next round only after all games complete.

### Completion and ranking

Group ranking sums raw scores. Equal totals use descending round-score vectors.
A material tie creates overtime among tied players;<br>
an organizer-controlled draw is the auditable last resort. Completed results become read-only.

### History and comparison

Players receive private post-event history. Organizers can replay their
tournament and compare a selected player's total, round average, best round<br>
and round count across one to four completed events. Active events are excluded.

### Lists and archives

Operational tables remain together on the dashboard.
Potentially long history uses backend pagination and an explicit “Load more” interaction.

## 5. Primary flows

### Organizer flow

Create event → configure rules → open or manage registration → verify the field
→ start round → monitor independent tables → pass the barrier <br>→ resolve any material tie
→ complete → replay or compare.

### Participant flow

Create account/profile → join or receive entry → open assigned table
→ roll and hold → choose a category → continue when active<br>
→ reconnect from REST snapshot if needed → inspect private history after completion.

### Completed-game replay

Replay is read-only and sourced from stored `Roll`, `ScoreEntry` and snapshot
records. It does not synthesize a history from aggregate scores.

## 6. Non-functional requirements

### Correctness and integrity

The backend owns scoring and transitions. Transactions, locks,
constraints and idempotency prevent duplicate or contradictory effects.<br>
Snapshots preserve historical identity.

### Security and privacy

Use least privilege, strong password validation, session rotation and expiry,
CSRF where relevant, non-enumerating resets, throttling and secrets from env.<br>
Return no other participant's private history.

### Reliability and concurrency

One slow table does not block another.
Lost WebSocket events recover through a REST snapshot.
Accepted commands have one unambiguous durable effect.

### Performance

The 128-player dashboard has a query budget and eager-loading strategy.
Avoid N+1 reads. Paginate history, not the live set of active tables.

### Accessibility

Use semantic controls, keyboard-compatible native elements, mouse and touch,
clear status text and reduced-motion support. Do not encode state only by color.

### Maintainability

Keep views thin, rules testable and documentation linked.
CI runs Ruff, Django checks, migration checks, PostgreSQL tests and coverage.
Demo data is seeded reproducibly.

## 7. Conceptual domain

The core chain is `User → PlayerProfile → TournamentParticipant → GameParticipant → Turn → Roll/ScoreEntry`.<br>
`TournamentOrganizer` grants event authority.<br>
`Tournament → Round → Game` defines structure.<br>
Later `Stage`, `Group`, `Match`, `Team` and audit models extend rather than redefine this chain.

## 8. Delivery roadmap

### MVP — complete group tournament

Accounts, roles, registration, group rounds, balanced tables, dice gameplay,
ranking, overtime, controlled draw, realtime organizer view, history,
comparison, operations and automated verification.

### V1 — full tournament and audit

Knockout play, formal stages, complete audit events, alerts, corrections,
cancellation and retention.

### V2 — team analytics and clients

Persistent teams, team ranking and comparisons, public or additional clients,
exports and richer analytics.

Features outside these releases need a new business justification.
The MVP does not gain scope merely because the data model leaves an extension point.

## 9. Participation and history policies

An entry preserves the name used during the event. Leaving and rejoining before start reuse the same entry.<br>
Team labels are soft allocation metadata.<br>
Ties are resolved by score vectors, overtime and only then a controlled draw.<br>
Stored timestamps use UTC; presentation uses tournament timezone where relevant.<br>
Connection state helps operations but never determines the winner or score.
