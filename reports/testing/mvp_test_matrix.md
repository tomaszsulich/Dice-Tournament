**Polski** | [English](mvp_test_matrix.en.md)

# Macierz testów MVP

Ta macierz pokazuje, które wymagania i ryzyka MVP są objęte testami
automatycznymi oraz gdzie dodano testy uzupełniające rzeczywiste luki w pokryciu.

| Kontrakt | Główne pokrycie automatyczne |
| --- | --- |
| Kategorie punktacji, Szkółka, figury, niejednoznaczność Pary i premia za pierwszy rzut | `src/tournaments/tests/unit/dice/scoring/test_strategies.py`, `src/tournaments/tests/unit/dice/test_contracts.py` |
| Rozmiary stołów 2–6 oraz granice 1/7/128/129 | `src/tournaments/tests/unit/tournament/test_table_sizes.py` |
| Deterministyczny przydział, konflikty i powtórni przeciwnicy | `src/tournaments/tests/unit/tournament/allocation/` |
| Pełny przepływ zapisu do turnieju, odrzucenie pól kontrolowanych przez backend i wyścig o ostatnie miejsce | `src/tournaments/tests/api/test_registration_api.py`, `src/tournaments/tests/services/test_participant_registration.py` |
| Pełny przepływ rzut/zatrzymanie/kategoria oraz idempotencja | `src/tournaments/tests/api/test_roll_api.py`, `src/tournaments/tests/api/test_turn_flow_api.py`, `src/tournaments/tests/services/test_roll_service.py`, `src/tournaments/tests/services/test_turn_flow_service.py` |
| Współbieżne rzuty, wybór kategorii i przejścia rund | `src/tournaments/tests/concurrency/`, `src/tournaments/tests/services/test_round_barrier.py` |
| Autoryzacja obiektowa / IDOR | `src/tournaments/tests/api/test_tournament_permissions.py`, `src/tournaments/tests/api/test_participant_comparison.py`, testy API panelu organizatora |
| Ponowne połączenie, odtworzenie stanu z autorytatywnego źródła oraz stała liczba zapytań aktywnego stołu i kontekstu przypisań | `src/tournaments/tests/api/test_reconnect_api.py`, `src/tournaments/tests/services/test_connection_state.py` |
| Uprawnienia połączeń WebSocket i dostarczanie zdarzeń dopiero po commitcie | `src/tournaments/tests/realtime/test_realtime_contract.py` z `WebsocketCommunicator` |
| Routing i zachowanie zadań Celery bez zależności zwykłego zestawu testów od realnego brokera | `src/tournaments/tests/tasks/`; ustawienia testowe uruchamiają Celery w trybie eager |
| Uruchomienie stosu Compose z PostgreSQL, Redis, ASGI, dwoma workerami Celery i Beat | izolowany smoke uruchamiany przez `RUN_COMPOSE_SMOKE=1` w `tests/test_compose_contract.py`; hostowy port web jest przydzielany dynamicznie |
| Ochrona panelu organizatora i porównania uczestnika przed N+1 w skali MVP | `src/tournaments/tests/performance/test_dashboard_queries.py`, `src/tournaments/tests/api/test_organizer_dashboard.py`, `src/tournaments/tests/api/test_participant_comparison.py` |
| Zestawy danych demonstracyjnych 16/64/128, zakresowy reset, bezpieczne syntetyczne tożsamości i blokada produkcji | `src/tournaments/tests/test_seed_demo.py` |
| Scenariusz `completed`: 2–4 turnieje tych samych profili, historia wszystkich uczestników, 18 kategorii, 1–3 rzuty, zatrzymania oraz reprezentatywne wyniki Szkółki i figur | `src/tournaments/tests/test_seed_demo.py` |

## Zasady wykonywania testów i infrastruktury

- Zachowanie ORM jest sprawdzane na prawdziwym Django ORM; ORM nie jest mockowany.
- Testy transakcji i współbieżności muszą działać na PostgreSQL.
- Losowość, czas i transporty zewnętrzne mogą korzystać z kontrolowanych atrap na
  jawnych granicach systemu.
- Testy nie mogą zależeć od kolejności wykonania ani danych pozostawionych przez
  inny test.
- Raport pokrycia służy do wskazywania luk, a nie do wymuszania sztucznego 100%.
- Funkcje należące wyłącznie do V1 lub V2 nie wchodzą w zakres testów MVP;
  ich testy powstają razem z odpowiadającymi im funkcjami.

## Pełny scenariusz `completed`

Pełny test scenariusza `completed` jest oznaczony `slow`, ponieważ przechodzi
przez rzeczywiste serwisy gry i zapisuje kompletną historię.<br>Można wykonać go
osobno, a następnie uruchomić pozostały zestaw bez powtarzania tego przypadku:

```powershell
pytest -vv --durations=0 "src/tournaments/tests/test_seed_demo.py::test_seed_demo_supports_each_mvp_scenario[completed]"
pytest -q --deselect="src/tournaments/tests/test_seed_demo.py::test_seed_demo_supports_each_mvp_scenario[completed]"
```

Takie dwa uruchomienia łącznie stanowią pełną weryfikację tylko wtedy, gdy
pominięty przypadek przeszedł osobno w tym samym cyklu sprawdzania.<br>Sam wynik
z `deselected` nie zastępuje wyniku pełnego testu.
