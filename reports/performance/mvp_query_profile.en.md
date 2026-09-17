[Polski](mvp_query_profile.md) | **English**

# MVP query and performance profile

## Purpose

This report documents the MVP performance contracts that are actively guarded.<br>
It is not a synthetic benchmark and should not be used to justify speculative
indexes.

## Product boundaries

- An active MVP tournament supports up to 128 participants.
- Active tables on the organizer dashboard are not paginated.
- Historical and archive views may use their own pagination.
- PostgreSQL remains the authoritative source of persistent state.

## Guarded query-count contract

The organizer-dashboard selector has a regression guard for both 16 and 128
participants. The current test contract expects **6 ORM queries**<br>
for a complete state snapshot.
More participants may increase the amount of data returned
but they should not increase the number of database queries.

The remaining fixed budgets guard:

- participant comparison across 1–4 tournaments: **3 ORM queries**;
- active-table lookup for a user: **1 ORM query**, independently of the number
  of participations;
- the WebSocket context of watched participations and active assignments:
  **2 ORM queries**, independently of the number of participations.

Roll history uses `select_related()`, `prefetch_related()` and pagination
but does not currently have a separate fixed query budget.<br>
It must not be described as query-count guarded until such a test actually exists.

Indexes are not added merely because a path might need optimization in the future.<br>
Any future index should be justified by a recorded PostgreSQL query plan
and by measurements taken before and after the change.

## Demo data sets

`seed_demo` builds logically reproducible data sets for 16, 64 and 128 participants.<br>
The `--seed` value stabilizes domain content and allocations.<br>
The number of tournaments in the `completed` scenario is the exception:<br>
it is chosen independently from two to four
so that the Comparison view never demonstrates only a single tournament.
Each of those tournaments retains content reproducible from the supplied seed.

Execution time varies by machine and runtime environment.<br>
Record timing results as evidence from a specific local or CI run;
do not enforce them as fixed repository-level performance thresholds.

The `completed` scenario intentionally records the complete history of every participant,<br>
so it is not the performance profile for the active dashboard.
The measurements below use active scenarios; `completed` is verified
as a functional scenario.

The full `test_seed_demo_supports_each_mvp_scenario[completed]` test is intentionally marked `slow`:<br>
it builds two to four complete tournaments through the real roll, hold and category-selection services.<br>
The scoped-reset test does not replay that history; it verifies replacement of the whole namespace,
protection of unrelated data and the absence of duplicate users using a lightweight game result.<br>
A separate functional test retains the full-history coverage.

Local measurements recorded on 16 September 2026 on Windows, Python 3.12.10,
Django 6.1, and PostgreSQL:

- reset test before separating responsibilities: **472.69 s**;
- reset test after the change: **2.96 s**;
- full `completed` test: **350.36 s** when run separately;
- remaining suite: **1243 passed, 1 skipped, 1 deselected** in **559.34 s**.

These values document specific runs and are not CI thresholds.<br>
The full `completed` test may take longer inside the complete suite because of the state
and load of PostgreSQL and the operating system.

For local manual checks, the most convenient option is a Git-ignored `.env` file:

```text
ALLOW_DEMO_SEED=true
DEMO_PASSWORD=your-local-demo-password
```

`DEMO_PASSWORD` is optional. If it is not set, the command generates a random password and prints it once.<br>
Do not include that password in captured evidence.

Example measurements on the target development machine:

```powershell
Measure-Command {
    python src/manage.py seed_demo --size 16 --scenario active-round --seed 20260831 --reset
}

Measure-Command {
    python src/manage.py seed_demo --size 64 --scenario mixed-table-states --seed 20260831 --reset
}

Measure-Command {
    python src/manage.py seed_demo --size 128 --scenario active-round --seed 20260831 --reset
}
```

Record timing results together with a short description of the environment.
Treat them as a sanity check for that run, not as a universal performance
guarantee.
