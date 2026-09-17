Polski | [English](security.en.md)

# Bezpieczeństwo

## Model zaufania

Backend jest jedynym autorytetem dla tożsamości, uprawnień, stanu turnieju, wyniku rzutu i punktacji.<br>
Identyfikatory oraz wartości przesłane przez klienta nie nadają mu relacji z turniejem.<br>
WebSocket nie wykonuje komend domenowych.

Konto nie ma globalnej roli organizatora.<br>
Uprawnienie wynika z `TournamentOrganizer`; uczestnictwo z `TournamentParticipant`<br>
połączonego z własnym `PlayerProfile`.<br>
Superuser jest administratorem systemowym, a nie automatycznym organizatorem dowolnego turnieju.

## Uwierzytelnienie i sesje

- JWT może być przesłany nagłówkiem albo cookies HttpOnly;
- mutacje oparte na cookies wymagają poprawnego CSRF;
- access token żyje 15 minut, refresh maksymalnie 8 godzin i jest rotowany;
- rodzina sesji ma limit bezczynności oraz absolutne wygaśnięcie;
- logout, wygaśnięcie lub naruszenie sesji unieważnia rodzinę;
- reset hasła nie ujawnia, czy adres e-mail istnieje;
- produkcja wymaga HTTPS, secure cookies, jawnych hostów i `DEBUG=False`.

## Autoryzacja

Każdy endpoint sprawdza relację aktora z konkretnym obiektem.<br>
Uczestnik może wykonać komendę wyłącznie w swojej aktywnej turze.<br>
Organizator działa tylko w turniejach, do których został przypisany.<br>
Historia uczestnika jest dostępna po zakończeniu i tylko właścicielowi;<br>
przekrojowa Porównywarka jest narzędziem organizatora lub administratora.

Django Admin służy diagnostyce.
Nie zastępuje panelu organizatora i nie nadaje automatycznie relacji domenowych.

## Integralność i współbieżność

Mutacje są atomowe. Blokady wierszy i constraints chronią ostatnie miejsce,
cykl życia, kolejną rundę, aktywną turę, kategorię oraz pojedynczą decyzję tie-break.
Komendy tury używają jednej kolejności locków `Game → Turn`.

Rzut i wybór kategorii korzystają z idempotency key.
Ponowienie po utracie odpowiedzi nie tworzy nowego wyniku.<br>
Zdarzenia realtime i zadania są publikowane dopiero w `transaction.on_commit()`.

`Roll` jest append-only w zwykłym przebiegu i przechowuje pięć kości.<br>
Snapshot nazwy uczestnika powstaje przy uczestnictwie;
aktualizacja profilu nie nadpisuje historii.<br>
API odrzuca zapis identycznych danych tam, gdzie byłby semantic no-op.

## Ochrona przed nadużyciami

Osobne throttles obejmują logowanie, refresh, reset hasła, mutacje API, komendy gry i zapisy.<br>
Walidatory haseł Django pozostają aktywne.<br>
Błędy nie zwracają sekretów ani danych obcego użytkownika.<br>
Brak zasobu i brak uprawnienia mogą być celowo nierozróżnialne przez `404`.

## Sekrety i dane demonstracyjne

Sekrety pochodzą z env.<br>
`.env.example` zawiera wyłącznie wartości przykładowe;
lokalny `.env` nie jest commitowany.<br>
Seed wymaga jednocześnie `DEBUG=True` i `ALLOW_DEMO_SEED=true`.<br>
`--reset-database` jest świadomie destrukcyjny i wymaga PostgreSQL.<br>
`DEMO_PASSWORD`, tokeny, cookies i dane osobowe nie trafiają do manual evidence.

## Operacje i zależności

Health checks rozdzielają żywotność od gotowości.<br>
PostgreSQL i Redis nie są publicznymi usługami aplikacji.<br>
CI instaluje zależności z repozytorium, sprawdza Ruff,
konfigurację Django, brak migracji i cały zestaw testów.<br>
Aktualizacje zależności oraz deployment pozostają świadomą operacją utrzymaniową.

## Świadome ograniczenia MVP

MVP nie implementuje WebAuthn, publicznego API wyników, pełnego `AuditEvent`,<br>
retencji anulowanych turniejów ani workflow korekt.<br>
Brak tych funkcji nie może być kompensowany słabszym endpointem administracyjnym.<br>
Ich dodanie wymaga osobnego modelu zagrożeń i przeglądu uprawnień.
