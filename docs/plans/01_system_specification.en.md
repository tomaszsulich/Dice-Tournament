[Polski](01_system_specification.md) | English

# Universal dice tournament system

## 1. Vision and business context

Dice Tournament turns a paper-based multi-table dice event into a consistent,
replayable process. It serves organizers who need to allocate players, <br>monitor
concurrent tables and publish trustworthy results, while keeping gameplay clear
for participants.

The system is not a generic board-game engine. It owns tournament orchestration
and one defined five-dice ruleset. The first release prioritizes correctness,
traceable history and a usable event flow over breadth.

## 2. Product goals

The MVP must:

- run a complete group-stage tournament for up to 128 active entrants;
- keep tables independent during a round and synchronize only at its barrier;
- calculate scores and rankings on the server;
- preserve enough information to replay every turn;
- give organizers a live overview without exposing other players' data;
- support both remote server-generated rolls and validated in-person rolls;
- remain reproducible, testable and operable in local or Docker development.

## 3. Roles and vocabulary

### 3.1. User account

An account is a neutral identity. It is not globally marked as an organizer
or player. It may own zero or one `PlayerProfile` and may hold different roles<br>
in different tournaments.

### 3.2. Organizer

An organizer is a user linked to a particular tournament
through `TournamentOrganizer`. A tournament may have multiple organizers.<br>
Organizer access never follows merely from having a player profile.

### 3.3. Participant

A participant is a `PlayerProfile` entered into one tournament
through `TournamentParticipant`. Historical display-name snapshots
belong to the entry; the reusable profile is not cloned.

### 3.4. Team, group and table

In the MVP, `team_label` is a soft allocation preference
rather than a persistent team entity. A group-stage table
is represented by a `Game`.<br>Formal teams, groups and knockout
matches remain later extension points.

### 3.5. Stage, round, game, turn and roll

A round contains concurrent games. Every entrant plays once in a group round.
A game orders its participants. A turn owns up to three rolls and ends<br>
with one unused scoring category. A roll is a full five-die snapshot, not a delta.

### 3.6. First-roll invariant

Every new turn begins by rolling all five dice.
Holds do not carry between turns and cannot exist before the first roll.

### 3.7. System administrator

A Django superuser maintains the installation and uses Django Admin
for diagnostics. System administration does not silently create
an organizer relationship in the tournament domain.

### 3.8. Event mode

Events are either `REMOTE` or `IN_PERSON`.
Remote dice come from the backend randomizer.
In-person dice are submitted and validated by the backend.<br>
A hybrid mode is intentionally absent.

## 4. Tournament rules

### 4.1. Lifecycle

The MVP lifecycle is `DRAFT → REGISTRATION → ACTIVE → COMPLETED`.
Configuration that affects play or scoring becomes immutable after start.<br>
A completed event cannot be reopened through an ordinary update.

### 4.2. Configuration and registration

Before start, an organizer chooses registration mode, participant limits,
timezone, number of group rounds, preferred table size, scoring variant
and event mode. Active participation is capped at 128.

`ORGANIZER_ONLY` lets organizers add entrants. `OPEN` allows an authenticated profile
to join itself. Joining never accepts table, seed, team or tournament number assignments
from the client. Leaving before start deactivates the same entry; rejoining reactivates it
instead of creating a duplicate.<br>The final place is protected against races.

### 4.3. Group rounds

Every active participant appears exactly once in each group round.
Games within the round progress independently.<br>The next round may start only after all games
in the current round are complete.

### 4.4. Table allocation

Tables contain 2–6 people, are as even as possible and differ
in size by at most one. Allocation uses rankings, baskets and a snake pattern.<br>
The optimizer prefers fewer repeated pairings and separation of equal `team_label` values
but those are soft costs rather than impossible constraints.<br>
Equal minimum-cost solutions may be selected reproducibly from a seed.

### 4.5. Rankings

Individual group ranking is based on the sum of each participant's raw game
scores. The system also exposes total, average per completed round, best round<br>
and rounds played. A team ranking is not part of the MVP.

### 4.6. Ties

Rank equal totals by comparing sorted round scores from highest to lowest.
A material tie at the advancement boundary starts an overtime round<br>containing
only the tied participants. Overtime repeats while necessary. A controlled draw
is an explicit, auditable organizer action of last resort<br>when another overtime
game is objectively impossible. Once stored, that decision is replayed on retry.

### 4.7. Scoring

The backend owns scoring. The card contains six School fields
(`ONES` through `SIXES`) and twelve figure categories, for 18 categories in total.
Each category may be used once per game. Bonuses, penalties, multipliers
and variant-specific rules are domain strategies.
The UI may explain a rule but must not recommend a strategic move.

### 4.8. Player turn

The active player rolls all five dice, may set holds after a roll,
and may roll unheld dice until the third roll.
They may select a legal unused category after any roll.
The selection records the score and advances the game.
After the third roll, category selection is mandatory.

### 4.9. Visibility

During play, participants see the state needed for their own table and turn.
Organizers see all active tables and attention state.<br>
After completion, a participant can read only their own tournament history.
An assigned organizer can replay completed games<br>
and compare one to four completed tournaments for a selected participant.
Active and cancelled events never enter comparison.

## 5. Resolved design questions

- Tables do not wait for each other between turns; only the round barrier waits.
- Full roll snapshots make replay independent from reconstruction logic.
- Profile edits do not rewrite participant snapshots.
- Realtime delivery is not an alternative command channel.
- Pagination belongs to long history; active organizer tables are unpaginated.
- History uses an explicit “Load more” action, never infinite scroll.
- The MVP uses one group phase; knockout play is planned, not partially hidden.

## 6. User stories

### 6.1. Authenticated user

Register, sign in, refresh or end a session, reset or change a password
and create or update a player profile without duplicating unchanged data.

### 6.2. Organizer

Create and configure an event, assign co-organizers, manage registration,
start rounds, watch all tables, resolve a tie when permitted, complete the tournament,
replay history and compare completed results.

### 6.3. Participant

Join an open event or accept organizer registration, find the assigned table,
play only their own turn, recover after reconnect and later inspect private history.

### 6.4. System

Validate every command, score dice, allocate tables, prevent duplicate effects,
publish state after commit, run background maintenance and preserve a stable API contract.

### 6.5. Administrator

Diagnose accounts and tournament records through Django Admin, inspect OpenAPI
and operate health checks without receiving ordinary organizer privileges.

## 7. Views and user flows

The browser application provides account pages, profile setup, a participant table,
private history, the organizer dashboard and participant comparison.<br>
The dashboard keeps every table visible and distinguishes playing, completed,
waiting and attention states. Comparison uses a shared table and one history modal,<br>
with at most four tournament cards in a 2×2 layout.

## 8. MVP scope

### 8.1. Included

Accounts and password flows; tournament-scoped roles; profiles and historical snapshots;
registration; the group lifecycle; balanced allocation; remote and in-person dice;
all 18 categories; independent tables; ranking and overtime; controlled draw;
organizer realtime; private history; comparison; Django Admin; OpenAPI; Celery maintenance;
PostgreSQL, Redis and Docker development; automated tests and reproducible demo worlds.

### 8.2. Later releases

Knockout stages, formal `Stage`/`Group`/`Match`, persistent teams, team rankings,
public result pages, exports, charts, a complete audit and correction workflow,<br>
cancelled-event retention, WebAuthn, 3D clients and presentation material.

## 9. Domain model

- `User`: authentication identity.
- `PlayerProfile`: optional one-to-one player identity.
- `Tournament`: configuration and lifecycle aggregate.
- `TournamentOrganizer`: many-to-many organizer assignment.
- `TournamentParticipant`: reusable profile entry plus historical snapshots.
- `Round`: numbered group or overtime round.
- `Game`: one concurrent table.
- `GameParticipant`: table seat, order and raw/final score fields.
- `Turn`: active player attempt and hold state.
- `Roll`: full dice, roll number, holds, source and timestamp.
- `ScoreEntry`: chosen category and authoritative score.
- `IdempotencyRecord`: command fingerprint and stored response.
- `TieBreakDecision`: durable controlled-draw decision.

The database enforces unique organizer assignments, participation,
round numbers, seats, category use, roll numbers, idempotency keys<br>
and one tie-break decision per round. Derived dashboards and rankings
remain selectors rather than new sources of truth.

## 10. Relationships and invariants

One account has at most one profile; one profile has at most one entry
in a tournament; organizer assignment is unique per user and event;
a participant occupies one seat in a game and plays once per group round.
Round numbers, table display numbers, turn numbers, roll numbers and category use
are unique in their natural parent scope. A completed record remains historical input
rather than a mutable summary.

## 11. API and vertical slices

REST endpoints are organized around account management, tournament lifecycle,
registration, gameplay, barriers, rankings, dashboard snapshots, history
and comparison. OpenAPI is generated from the DRF contract and supplemented
with runnable `.http` examples. A vertical slice includes model, domain rule,
service, API, UI, permissions and regression tests.

## 12. Asynchrony and concurrency

PostgreSQL transactions protect domain changes. Gameplay commands use row locks
and a shared `Game → Turn` order. Idempotency keys protect retryable effects.
Celery is limited to notifications and maintenance; gameplay is synchronous.
Channels publishes after commit. A reconnect fetches REST state
rather than assuming every event arrived.

## 13. Technical architecture

The backend uses Python 3.12, Django, DRF, Djoser, SimpleJWT, drf-spectacular,
Channels, Daphne and Celery. PostgreSQL is the database and Redis is the channel
layer and broker. The frontend uses Django templates, semantic HTML, CSS
and JavaScript with mouse, touch and reduced-motion support.

Development, test and production settings are separate. Secrets come from env.
Production disables debug and requires HTTPS hardening. CI checks formatting,
lint, Django configuration, migrations, PostgreSQL tests and coverage.

## 14. Security and integrity

The application uses object-scoped permissions, password validation,
non-enumerating reset, JWT rotation, session-family expiry,
CSRF for cookie mutations<br>and endpoint-specific throttling.
Database constraints supplement application validation.
Demo seeding is development-only and destructive reset requires<br>an explicit command.

## 15. Test strategy

Pure scoring and allocation rules have unit tests. Models, selectors, services,
API, permissions, WebSocket consumers, Celery tasks, reconnect and UI contracts
have integration tests. Native concurrency tests use PostgreSQL.
The 128-player dashboard has a query-profile regression test.<br>
Compose smoke is opt-in and does not make ordinary pytest depend on Docker.

## 16. Roadmap

MVP establishes the complete group tournament.<br>V1 adds knockout play,
complete auditing, alerts and correction flows.<br>V2 adds persistent teams,
team analytics and additional clients.<br>Each version must preserve the authoritative backend,
history and permission boundaries established here.
