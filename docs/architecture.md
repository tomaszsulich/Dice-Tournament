Polski | [English](architecture.en.md)

# Architektura

## Kontekst

Dice Tournament jest modularnym monolitem Django.
MVP prowadzi pełny turniej grupowy i utrzymuje jeden autorytatywny stan w PostgreSQL.<br>
REST służy do komend i snapshotów, a WebSocket wyłącznie dostarcza aktualizacje już zatwierdzonego stanu.

## Komponenty

| Komponent | Odpowiedzialność |
|---|---|
| Django + DRF | HTTP, walidacja wejścia, autoryzacja i thin views |
| PostgreSQL | stan domenowy, constraints, transakcje i blokady wierszy |
| Daphne + Channels | ASGI i ograniczone aktualizacje czasu rzeczywistego |
| Redis | channel layer oraz broker Celery |
| Celery | powiadomienia i okresowe zadania utrzymaniowe |
| HTML/CSS/JavaScript | dostępny interfejs i odświeżanie ze snapshotu REST |

## Moduły aplikacji

`accounts` odpowiada za neutralne konto, opcjonalny `PlayerProfile`, JWT,
rodziny sesji, reset i zmianę hasła oraz throttling.<br>
`tournaments` zawiera modele i przepływy turnieju, grę kościaną, selektory paneli, realtime i zadania.<br>
`api` utrzymuje wspólny kontrakt błędów i rozszerzenia schematu.

Widoki są cienkie. Mutacje przechodzą do serwisów, odczyty do selektorów, a czyste reguły do `domain/`.<br>
Modele przechowują stan i constraints, ale nie stają się przypadkową warstwą orkiestracji.

## Dwie granice domenowe

### Turniej

Cykl życia, zapisy, uczestnicy, rundy, stoły, przydział, ranking, remisy,
dogrywki i kontrolowane losowanie. Ranking grupowy sumuje `raw_score`.

### Gra kościana

Tura, maksymalnie trzy rzuty, zatrzymania, wybór niewykorzystanej kategorii i punktacja.<br>
Każdy `Roll` jest pełną migawką pięciu kości.<br>
Pierwszy rzut zawsze rzuca wszystkimi pięcioma.

Granice współpracują przez jawne modele `Game`, `GameParticipant`, `Turn`,
`Roll` i `ScoreEntry`; frontend nie oblicza wiążącego wyniku.

## Przepływ komendy

1. DRF uwierzytelnia użytkownika i waliduje payload.
2. Serwis sprawdza relację użytkownika z turniejem lub polem gry.
3. `transaction.atomic()` i `select_for_update()` chronią współbieżną mutację.
4. Constraint bazy zabezpiecza niezmiennik także poza ścieżką aplikacyjną.
5. Odpowiedź idempotentnej komendy zostaje zapisana.
6. `transaction.on_commit()` publikuje zdarzenie WebSocket albo zleca zadanie.
7. Klient po reconnect pobiera autorytatywny snapshot REST.

Komendy aktywnej tury blokują rekordy w kolejności `Game → Turn`.
Stoły jednej rundy nie blokują się wzajemnie; bariera rundy działa dopiero po ich ukończeniu.

## Dane i historia

`User` ma najwyżej jeden `PlayerProfile`, który może uczestniczyć w wielu turniejach.<br>
`TournamentParticipant` utrwala snapshot nazwy potrzebny historii, ale nie duplikuje profilu.<br>
Rzuty, zatrzymania, kategorie i wyniki umożliwiają replay.<br>
Historia uczestnika jest prywatna, a organizer otrzymuje odczyt tylko w zakresie własnego turnieju.

## Środowiska

- `development`: PostgreSQL i Redis, `DEBUG=True`, opcjonalny bezpieczny seed;
- `test`: PostgreSQL, in-memory Channels i eager Celery;
- `production`: `DEBUG=False`, HTTPS-only cookies, SMTP i sekrety z env;
- Compose development: web, baza, Redis, dwa workery, Beat i usługa migracji.

Docker development i local development są odrębnymi ścieżkami.
Local może wykorzystać tylko kontener Redis, ale porty obu środowisk nie mogą kolidować.

## Skala i wydajność

MVP obsługuje do 128 aktywnych uczestników.<br>
Panel organizatora celowo pokazuje wszystkie aktywne stoły bez paginacji,
dlatego selektory korzystają z `select_related` i `prefetch_related`,<br>
a budżet zapytań ma osobny test.<br>
Długie historie są paginowane i ładowane świadomym przyciskiem „Load more”.

## Dalszy rozwój

Model przewiduje rozszerzenie o fazę pucharową, formalne etapy, pełny audyt i trwałe drużyny.<br>
Nie są one ukrytymi częściami MVP; granice rozszerzeń opisują plany w [`docs/plans/`](plans/01_system_specification.md).
