**Polski** | [English](mvp_query_profile.en.md)

# Profil zapytań i wydajności MVP

## Cel

Raport opisuje kontrakty wydajnościowe MVP. Nie jest syntetycznym benchmarkiem
ani pretekstem do dodawania indeksów „na zapas”.

## Granice produktu

- Aktywny turniej w MVP obsługuje maksymalnie 128 uczestników.
- Aktywne stoły w panelu organizatora nie są paginowane.
- Widoki historyczne i archiwalne mogą mieć własną paginację.
- PostgreSQL pozostaje autorytatywnym źródłem trwałego stanu.

## Chroniony kontrakt liczby zapytań

Selektor panelu organizatora ma regresyjny test liczby zapytań dla 16 i 128 uczestników.
Obecny kontrakt testowy oczekuje **6 zapytań ORM**<br>
dla kompletnego obrazu stanu.
Wzrost liczby uczestników może zwiększać ilość zwracanych danych,
ale nie powinien zwiększać liczby zapytań do bazy.

Pozostałe stałe budżety chronią:

- porównanie uczestnika dla 1–4 turniejów: **3 zapytania ORM**;
- wyszukanie aktywnego stołu użytkownika: **1 zapytanie ORM**, niezależnie od liczby jego uczestnictw;
- kontekst obserwowanych uczestnictw i aktywnych przypisań WebSocket:
  **2 zapytania ORM**, niezależnie od liczby uczestnictw.

Historia rzutów korzysta z `select_related()`, `prefetch_related()` i paginacji,
ale obecnie nie ma osobnego, sztywnego budżetu zapytań. Nie należy przedstawiać
jej jako chronionej testem liczby zapytań, dopóki taki test rzeczywiście nie powstanie.

Indeksów nie dodajemy wyłącznie dlatego, że dane miejsce może kiedyś wymagać
optymalizacji. Każdy przyszły indeks powinien wynikać z zapisanego planu
zapytania PostgreSQL oraz pomiaru przed i po zmianie.

## Zestawy danych demonstracyjnych

`seed_demo` przygotowuje logicznie powtarzalne zestawy danych dla 16, 64 i 128 uczestników. Wartość `--seed` stabilizuje zawartość domenową i przydziały. Wyjątkiem jest liczba turniejów scenariusza `completed`: wynosi od dwóch do czterech
i jest losowana niezależnie, aby Porównywarka nie była demonstracją wyłącznie jednego turnieju. Każdy z tych turniejów
zachowuje powtarzalną zawartość wynikającą z podanego ziarna.

Czas wykonania zależy od maszyny i środowiska uruchomieniowego.
Wyniki pomiarów zapisujemy więc jako dowód z konkretnego uruchomienia lokalnego
lub CI,<br>a nie jako stały próg wydajności w repozytorium.

Scenariusz `completed` celowo zapisuje pełną historię wszystkich uczestników
i dlatego nie służy jako profil wydajności aktywnego dashboardu.<br>
Poniższe pomiary używają scenariuszy aktywnych; `completed` sprawdzamy funkcjonalnie.

Pełny test `test_seed_demo_supports_each_mvp_scenario[completed]` jest świadomie
oznaczony `slow`: tworzy od dwóch do czterech kompletnych turniejów przez rzeczywiste
serwisy rzutu, zatrzymań i wyboru kategorii. Test zakresowego resetu
nie powtarza tej historii; sprawdza wymianę całego namespace'u, zachowanie obcych
danych i brak duplikacji użytkowników, korzystając z lekkiego rezultatu gry.
Pełna historia pozostaje sprawdzana przez osobny test funkcjonalny.

Pomiar lokalny z 16 września 2026 r. na Windows, Pythonie 3.12.10, Django 6.1
i PostgreSQL:

- test resetu przed rozdzieleniem odpowiedzialności: **472,69 s**;
- test resetu po zmianie: **2,96 s**;
- pełny test `completed`: **350,36 s** w osobnym uruchomieniu;
- pozostały zestaw: **1243 passed, 1 skipped, 1 deselected** w **559,34 s**.

Wartości dokumentują konkretne uruchomienia i nie są progami CI. Pełny test
`completed` może trwać dłużej wewnątrz całego zestawu ze względu na stan
oraz obciążenie PostgreSQL i systemu operacyjnego.

Do lokalnego manuala najwygodniej użyć ignorowanego przez Git pliku `.env`:

```text
ALLOW_DEMO_SEED=true
DEMO_PASSWORD=your-local-demo-password
```

`DEMO_PASSWORD` jest opcjonalny. Jeżeli go nie ustawisz, polecenie wygeneruje
losowe hasło i wypisze je jednorazowo. Hasła nie należy zapisywać w materiałach
dowodowych.

Przykładowy pomiar na docelowej maszynie developerskiej:

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

Wyniki czasowe zapisuj wraz z krótkim opisem środowiska. Traktuj je jako kontrolę
rozsądku dla konkretnego uruchomienia, a nie jako uniwersalną obietnicę
wydajności.
