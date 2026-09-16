[Polski](mvp_test_matrix.md) | **English**

# MVP test matrix

This matrix shows which MVP requirements and risks are covered by automated
tests and where focused additions close genuine gaps in coverage.

| Contract | Primary automated coverage |
| --- | --- |
| School categories (1–6), scoring figures, Pair ambiguity and the first-roll bonus | `src/tournaments/tests/unit/dice/scoring/test_strategies.py`, `src/tournaments/tests/unit/dice/test_contracts.py` |
| Table sizes 2–6 and the 1/7/128/129 boundaries | `src/tournaments/tests/unit/tournament/test_table_sizes.py` |
| Deterministic allocation, conflict handling and repeated opponents | `src/tournaments/tests/unit/tournament/allocation/` |
| End-to-end tournament registration, rejection of backend-owned fields<br>and the last-slot race | `src/tournaments/tests/api/test_registration_api.py`, `src/tournaments/tests/services/test_participant_registration.py` |
| Roll/hold/category flow and idempotency | `src/tournaments/tests/api/test_roll_api.py`, `src/tournaments/tests/api/test_turn_flow_api.py`, `src/tournaments/tests/services/test_roll_service.py`, `src/tournaments/tests/services/test_turn_flow_service.py` |
| Concurrent rolls, category selection and round transitions | `src/tournaments/tests/concurrency/`, `src/tournaments/tests/services/test_round_barrier.py` |
| Object-level authorization / IDOR protection | `src/tournaments/tests/api/test_tournament_permissions.py`, `src/tournaments/tests/api/test_participant_comparison.py`, organizer-dashboard API tests |
| Reconnect, authoritative state restoration and constant query counts for active-table lookup, and assignment context | `src/tournaments/tests/api/test_reconnect_api.py`, `src/tournaments/tests/services/test_connection_state.py` |
| WebSocket admission rules<br>and post-commit event delivery | `src/tournaments/tests/realtime/test_realtime_contract.py` with `WebsocketCommunicator` |
| Celery routing and task behavior without requiring a live broker in the normal suite | `src/tournaments/tests/tasks/`; test settings run Celery eagerly |
| Compose runtime with PostgreSQL, Redis, ASGI, two Celery workers and Beat | isolated smoke enabled with `RUN_COMPOSE_SMOKE=1` in `tests/test_compose_contract.py`;<br>the host-side web port is assigned dynamically |
| Organizer-dashboard and participant-comparison protection against N+1 regressions at MVP scale | `src/tournaments/tests/performance/test_dashboard_queries.py`, `src/tournaments/tests/api/test_organizer_dashboard.py`, `src/tournaments/tests/api/test_participant_comparison.py` |
| Demo data sets at 16/64/128, scoped reset, safe synthetic identities and production protection | `src/tournaments/tests/test_seed_demo.py` |
| `completed`: 2‑4 tournaments, shared profiles, complete participant histories, 18 categories, 1‑3 rolls, holds and representative School/figure results | `src/tournaments/tests/test_seed_demo.py` |

## Test execution and infrastructure rules

- ORM behavior is exercised through the real Django ORM rather than mocked away.
- Transaction and concurrency tests run against PostgreSQL.
- Randomness, time, and external transports may use controlled fakes at explicit
  system boundaries.
- No test may depend on execution order or on state left behind by another test.
- Coverage is used to locate gaps, not to manufacture a 100% score.
- Features that belong exclusively to V1 or V2 are outside the MVP test scope;
  their tests are added alongside the corresponding feature.

## Full `completed` scenario

The full `completed` scenario test is marked `slow` because it goes through the
real gameplay services and stores complete history.<br>It may be run separately,
followed by the remaining suite without repeating that case:

```powershell
pytest -vv --durations=0 "src/tournaments/tests/test_seed_demo.py::test_seed_demo_supports_each_mvp_scenario[completed]"
pytest -q --deselect="src/tournaments/tests/test_seed_demo.py::test_seed_demo_supports_each_mvp_scenario[completed]"
```

Together, these two runs constitute complete verification only when the
deselected case passed separately in the same verification cycle.<br>
A result with `deselected` does not replace the full test result on its own.
