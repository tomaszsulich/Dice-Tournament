Polski | [English](api.en.md)

# API

## Źródło kontraktu

Autorytatywną, generowaną dokumentacją HTTP jest schema OpenAPI pod `/api/schema/`.
Swagger UI działa pod `/api/docs/`.<br>
Oba widoki wymagają konta administratora systemowego.
Pliki w [`manual-api/`](../manual-api/README.md) zawierają przykładowe żądania,<br>
ale nie zastępują schematu ani testów.

## Uwierzytelnienie

API akceptuje JWT w nagłówku `Authorization: Bearer …` albo w cookies HttpOnly.
Mutacje korzystające z cookies wymagają CSRF.<br>
Access token jest krótki, refresh jest rotowany, a logout unieważnia rodzinę sesji i usuwa cookies.

Najważniejsze endpointy konta:

| Metoda | Ścieżka | Cel |
|---|---|---|
| POST | `/api/auth/users/` | rejestracja konta |
| POST | `/api/auth/jwt/create/` | logowanie i utworzenie rodziny sesji |
| POST | `/api/auth/jwt/refresh/` | rotacja pary tokenów |
| POST | `/api/auth/logout/` | unieważnienie sesji |
| POST | `/api/auth/users/set-password/` | zmiana hasła |
| POST | `/api/auth/users/reset-password/` | żądanie resetu bez enumeracji |
| POST | `/api/auth/users/reset-password-confirm/` | ustawienie nowego hasła |
| GET/PATCH | `/api/profile/` | odczyt lub rzeczywista zmiana profilu |

## Turnieje

| Metoda | Ścieżka | Uprawnienie / znaczenie |
|---|---|---|
| POST | `/api/tournaments/create/` | utworzenie turnieju |
| GET | `/api/tournaments/` | lista w zakresie użytkownika |
| GET/PATCH | `/api/tournaments/{id}/` | szczegóły; konfiguracja tylko przed startem |
| POST | `/api/tournaments/{id}/open-registration/` | organizator |
| POST | `/api/tournaments/{id}/close-registration/` | organizator |
| POST | `/api/tournaments/{id}/participants/` | dodanie przez organizatora |
| POST | `/api/tournaments/{id}/join/` | własny zapis do trybu `OPEN` |
| POST | `/api/tournaments/{id}/leave/` | wyjście przed startem |
| POST | `/api/tournaments/{id}/start/` | organizator, legalny skład |
| POST | `/api/tournaments/{id}/complete/` | organizator, ukończone gry |
| GET | `/api/tournaments/{id}/ranking/` | ranking z surowych wyników |

## Gra i bariera rundy

| Metoda | Ścieżka | Kontrakt |
|---|---|---|
| GET | `/api/games/{id}/state/` | autorytatywny snapshot gry |
| POST | `/api/games/{id}/roll/` | rzut właściciela aktywnej tury |
| PUT | `/api/games/{id}/holds/` | ustawienie flag pięciu kości |
| POST | `/api/games/{id}/choose-category/` | zapis kategorii i wyniku |
| POST | `/api/rounds/{id}/barrier/` | ocena końca rundy |
| POST | `/api/rounds/{id}/draw/` | kontrolowane losowanie w dogrywce |

Rzut i wybór kategorii wymagają klucza idempotencji zgodnie ze schemą.<br>
Retry z tym samym fingerprintem odtwarza wynik;
ponowne użycie klucza dla innej komendy jest konfliktem.<br>
Zatrzymania ustawiają pełny stan i odrzucają semantic no-op.

## Dashboard, historia i porównania

| Metoda | Ścieżka | Zakres |
|---|---|---|
| GET | `/api/tournaments/{id}/organizer-dashboard/` | organizator turnieju |
| GET | `/api/comparisons/participants/{id}/` | organizator lub administrator |
| GET | `/api/comparisons/participants/{id}/history/` | dozwolony replay / własna historia |

Historia jest paginowana. Kolejność to runda, stół, tura i numer rzutu.
Każdy element zawiera pełną migawkę kości oraz zatrzymania;<br>
kategoria i wynik pojawiają się tam, gdzie dotyczą zakończonej decyzji.

## Błędy i throttling

Błędy DRF mają stabilny kod HTTP i ujednoliconą strukturę opisaną w OpenAPI.<br>
Permissions są sprawdzane ponownie po identyfikatorze obiektu;
payload nie może poszerzyć zakresu użytkownika.<br>
Endpointy auth, mutacje API, komendy gry i zapisy
mają osobne limity. `429 Too Many Requests` jest częścią kontraktu, nie awarią.

## WebSocket

WebSocket przekazuje ograniczony snapshot stołu lub dashboardu po commit.
Nie przyjmuje komend domenowych.<br>
Po utracie połączenia klient pobiera stan REST,
dzięki czemu pominięte zdarzenie nie prowadzi do rozjazdu danych.
