Polski | [English](./README.en.md)

# Dice Tournament

Dice Tournament to aplikacja Django do prowadzenia grupowych turniejów gry w kości.
Organizator przygotowuje turniej, zarządza uczestnikami<br>
i obserwuje wszystkie stoły w czasie rzeczywistym.
Uczestnik rozgrywa własne tury, a po zakończeniu turnieju może wrócić do pełnej historii rzutów.

MVP obsługuje do 128 aktywnych uczestników, zdalne i stacjonarne wydarzenia, równoległą grę przy stołach, ranking grupowy, dogrywki<br>oraz porównanie od jednego do czterech zakończonych turniejów.

## Najważniejsze funkcje

- konta użytkowników, profile graczy oraz relacyjne role organizatora i uczestnika;
- zamknięte i otwarte zapisy do turnieju;
- równy podział na stoły od 2 do 6 osób, koszyki rankingowe i wężyk;
- trzy rzuty w turze, zatrzymywanie kości i 18 kategorii punktowych;
- autorytatywna punktacja backendowa i pełne migawki pięciu kości;
- niezależne stoły oraz bariera przed rozpoczęciem kolejnej rundy;
- panel organizatora aktualizowany przez WebSocket;
- historia własnych rzutów uczestnika i replay organizatora;
- porównywarka zakończonych turniejów;
- Celery z oddzielnymi kolejkami powiadomień i utrzymania;
- OpenAPI, Swagger, testy automatyczne i powtarzalne światy demonstracyjne.

## Granice MVP

MVP obejmuje kompletny turniej grupowy. Faza pucharowa, trwałe drużyny, publiczne wyniki, pełny rejestr audytowy
i eksporty należą do kolejnych wersji. Szczegóły decyzji i świadomych odrzuceń opisuje [dokument decyzji](docs/decisions.md).

## Architektura w skrócie

Backend stanowią Django, Django REST Framework i PostgreSQL. Daphne obsługuje ASGI, Channels dostarcza aktualizacje WebSocket przez Redis,<br>
a Celery wykonuje zadania poboczne. HTML, CSS i JavaScript są serwowane przez Django.<br>
Logika turnieju i logika kości pozostają rozdzielone w obrębie aplikacji `tournaments`.

Więcej informacji:

- [architektura](docs/architecture.md),
- [API](docs/api.md),
- [bezpieczeństwo](docs/security.md),
- [plany produktu i systemu](docs/plans/01_system_specification.md).

## Wymagania

- Python 3.12;
- PostgreSQL;
- Redis;
- Git;
- opcjonalnie Docker z Docker Compose.

Polecenia w tym README zakładają, że bieżącym katalogiem jest główny katalog
repozytorium. Jedynym wyjątkiem jest uruchomienie Daphne w wariancie lokalnym:
`config.asgi` jest importowane z katalogu `src`, dlatego przed tym poleceniem
trzeba przejść do `src`.

## Local development

Ten wariant uruchamia Python, Django, Daphne i PostgreSQL lokalnie.
Redis może działać lokalnie albo jako jedyna usługa uruchomiona przez Docker.

### 1. Środowisko Pythona

```powershell
python -m pip install uv==0.12.15
uv sync --frozen
.\.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
```

`uv.lock` jest źródłem wersji zależności dla środowiska lokalnego, Dockera i CI.
Aktualizuj go świadomie tylko razem ze zmianą zależności w `pyproject.toml`.

Ustaw w `.env` własny `SECRET_KEY`, dane lokalnego PostgreSQL i — jeśli ma być używany seed — `ALLOW_DEMO_SEED=true`
oraz `DEMO_PASSWORD`. Nie commituj `.env`.

### 2. PostgreSQL i Redis

Utwórz bazę oraz użytkownika zgodne z `DATABASE_URL`. Redis musi działać przed uruchomieniem frontu z WebSocketami.
Jeżeli nie masz lokalnego Redisa, uruchom:

```powershell
docker compose up -d redis
```

Domyślnie Redis jest wtedy dostępny pod `127.0.0.1:6379`.<br>
Jeżeli równolegle działa pełny stos Docker albo inna usługa zajmuje ten port,
ustaw inny `REDIS_HOST_PORT` dla Compose<br>
i odpowiedni port w lokalnych `REDIS_URL` oraz `CELERY_BROKER_URL`.<br>
Lokalny i dockerowy web również nie mogą korzystać z tego samego portu hosta; dla Compose można zmienić `WEB_HOST_PORT`.

### 3. Migracje i serwer

```powershell
python src/manage.py migrate
python src/manage.py check
Set-Location src
daphne -b 127.0.0.1 -p 8000 config.asgi:application
```

Po starcie otwórz `http://127.0.0.1:8000/login/`. Zatrzymaj serwer przez `Ctrl+C`,
a następnie wróć do katalogu repozytorium poleceniem `Set-Location ..`.

### 4. Opcjonalni workerzy

Uruchom w osobnych terminalach, z katalogu repozytorium:

```powershell
celery -A config --workdir=src worker -Q notifications --loglevel=INFO
celery -A config --workdir=src worker -Q maintenance --loglevel=INFO
celery -A config --workdir=src beat --loglevel=INFO
```

## Docker development

Ten wariant uruchamia oddzielne kontenery dla Daphne, PostgreSQL, Redisa, dwóch workerów Celery i Beat.
Nie wymaga lokalnego Pythona ani lokalnej bazy.

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Po przejściu health checks aplikacja jest dostępna pod `http://127.0.0.1:8000/login/`.<br>
Migracje wykonuje jednorazowa usługa `migrate`.<br>
Port aplikacji można zmienić przez `WEB_HOST_PORT`, a port Redisa wystawiony na hosta przez `REDIS_HOST_PORT`.

Zatrzymanie usług:

```powershell
docker compose down
```

Usunięcie wolumenu PostgreSQL jest operacją destrukcyjną i nie należy do zwykłego zatrzymania środowiska.

## Dane demonstracyjne

Seed działa wyłącznie przy `DEBUG=True` i `ALLOW_DEMO_SEED=true`.
Obsługuje rozmiary `16`, `64`, `128` oraz scenariusze dostępne w pomocy komendy.

Lokalnie:

```powershell
python src/manage.py seed_demo --size 16 --scenario completed --seed 20260831
```

W Dockerze usługa narzędziowa jest jawnie opt-in:

```powershell
docker compose --profile tools run --rm seed-demo python src/manage.py seed_demo --size 16 --scenario completed --seed 20260831
```

`--reset` zastępuje tylko odpowiadający namespace demo.<br>
`--reset-database` czyści całą lokalną bazę aplikacji i restartuje sekwencje PostgreSQL;
używaj go wyłącznie świadomie w środowisku developerskim.<br>
Hasła demo są lokalne i nie powinny trafiać do dowodów ani logów publikowanych w repozytorium.

## API i interfejsy

- schema OpenAPI: `/api/schema/`;
- Swagger UI: `/api/docs/`;
- Django Admin: `/admin/`;
- health checks: `/health/live/` i `/health/ready/`;
- przykładowe żądania HTTP: [`manual-api/`](manual-api/README.md).

Schema i Swagger wymagają konta administratora systemowego. Pełny opis kontraktu znajduje się w [docs/api.md](docs/api.md).

## Testy i jakość

Zwykły pytest nie wymaga Dockera. Ustawienia testowe zachowują PostgreSQL jako bazę,
a Channels i Celery przełączają na deterministyczne implementacje testowe.

```powershell
pytest
python -m ruff check .
python -m ruff format --check .
python src/manage.py check
python src/manage.py makemigrations --check --dry-run
```

CI uruchamia pełny zestaw z coverage poza jednym kosztownym wariantem scenariusza `completed`;
ten wariant uruchamia osobno bez coverage.<br>
Compose smoke jest oddzielnym testem opt-in:

```powershell
pytest -m compose_smoke --run-compose-smoke
```

Nie uruchamiaj Compose smoke równolegle z innym stosem używającym tych samych portów.

## Role i bezpieczeństwo

Konto jest neutralne: organizatorem zostaje przez relację z konkretnym turniejem,
a uczestnikiem przez własny `PlayerProfile` i udział.<br>
Superuser ma uprawnienia systemowe, ale nie staje się automatycznie organizatorem turnieju.<br>
Mutacje domenowe są autoryzowane po stronie backendu, a rozgrywka korzysta z transakcji, blokad i kluczy idempotencji.<br>
Szczegóły opisuje [docs/security.md](docs/security.md).

## Roadmapa

- **MVP:** ukończony turniej grupowy, historia, realtime i porównania;
- **V1:** faza pucharowa, pełny audyt, alarmy i obieg korekt;
- **V2:** trwałe drużyny, analityka drużynowa i dodatkowi klienci.
