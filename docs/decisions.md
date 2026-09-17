Polski | [English](decisions.en.md)

# Decyzje techniczne i produktowe

## Status dokumentu

To skrócony rejestr decyzji dla ukończonego MVP.
Canonical Plans w [`docs/plans/`](plans/01_system_specification.md) pozostają nadrzędnym opisem zakresu produktu.

## Przyjęte decyzje

### Modularny monolit Django

Jedna aplikacja wdrożeniowa upraszcza transakcje i spójność.
Rozdział następuje przez moduły domenowe, serwisy i selektory, nie przez przedwczesne mikroserwisy.

### PostgreSQL w development, testach i produkcji

Produkt polega na blokadach wierszy, constraints i semantyce współbieżności.
SQLite nie jest równoważnym środowiskiem dla tych kontraktów.

### REST jako autorytet, WebSocket jako dostawa

Komendy przechodzą przez REST.
WebSocket publikuje stan po commit, a reconnect kończy się pobraniem snapshotu REST.
Eliminuje to drugą ścieżkę mutacji.

### Relacyjne role

Konto pozostaje neutralne. Organizator i uczestnik są relacjami z konkretnym turniejem.
Globalna flaga organizatora prowadziłaby do zbyt szerokich uprawnień.

### Jeden profil, wiele uczestnictw, historyczne snapshoty

`PlayerProfile` nie jest kopiowany na turniej.
Uczestnictwo przechowuje tylko niezbędny snapshot nazwy,
dzięki czemu późniejsza edycja profilu nie zmienia historii.

### Pełny `Roll`

Każdy rzut zapisuje wszystkie pięć wartości oraz zatrzymania,
także gdy część kości nie była ponownie losowana.
Replay nie musi rekonstruować stanu z różnic.

### Surowy wynik rankingu

Ranking grupowy i Porównywarka sumują `raw_score`.
`final_score` nie zastępuje tego kontraktu i może służyć innym,
przyszłym mechanizmom rozliczenia.

### Jawne kontrolowane losowanie

Dogrywki powtarzają się dla nadal remisujących.
Losowanie jest audytowalną komendą organizatora w stanie `OVERTIME`,
gdy dalsza dogrywka jest obiektywnie niemożliwa.
Zapisana decyzja jest trwała i odtwarzana przy retry.

### Celery poza gameplay

Powiadomienia i utrzymanie działają asynchronicznie.<br>
Rzut, zatrzymania, punktacja i przejście tury pozostają synchroniczne,
aby użytkownik natychmiast znał wiążący rezultat.

### Dwie jawne ścieżki development

Local development używa lokalnego Pythona, Daphne i PostgreSQL;
może pożyczyć Redis z Dockera. Docker development uruchamia cały stos w Compose.<br>
Mieszanie obu bez zmiany portów prowadzi do konfliktów, dlatego README opisuje je osobno.

### Dokumentacja dwujęzyczna

Polski plik nie ma sufiksu językowego, angielski używa `.en.md`.
Przełącznik jest pierwszym elementem i prowadzi do drugiej wersji językowej.<br>
Wersje przekazują te same decyzje, ale są redagowane naturalnie dla odbiorcy, nie tłumaczone 1:1.

## Świadomie odrzucone w MVP

- faza pucharowa i formalne `Stage`, `Group`, `Match`;
- trwałe zespoły oraz ranking drużyn;
- publiczne wyniki, eksporty i wykresy;
- WebAuthn, SMS i klient 3D;
- pełny subsystem audytu, alarmów i korekt;
- automatyczne strategiczne rekomendacje kategorii;
- infinite scroll historii;
- logika biznesowa w consumerze WebSocket;
- sekrety w repozytorium i automatyczne seedy produkcyjne.

## Następne wersje

V1 może dodać knockout, pełny audyt i korekty.<br>
V2 może dodać trwałe drużyny, analitykę i dodatkowych klientów.<br>
Każde rozszerzenie wymaga nowej decyzji produktowej zamiast cichego poszerzania MVP.
