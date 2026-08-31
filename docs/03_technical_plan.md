# Plan techniczny — system organizacji turniejów gry w kości

## 1. Cel i zakres

Dokument przekłada wymagania produktu na architekturę i kontrakty techniczne.
Nie jest instrukcją implementacji ani harmonogramem commitów.
System obsługuje turnieje jednej rodziny gier kościanych, a nie dowolne gry.


## 2. Architektura systemu

### 2.1. Komponenty

- Django i Django REST Framework obsługują przypadki użycia oraz REST API;
- PostgreSQL jest jedynym autorytatywnym źródłem trwałego stanu;
- Django Channels i Redis dostarczają zatwierdzone aktualizacje WebSocket;
- Daphne uruchamia aplikację jako ASGI;
- Celery wykonuje zadania niewymagające natychmiastowej odpowiedzi;
- Django Templates, HTML, CSS i niewielkie moduły JavaScript tworzą frontend MVP;
- OpenAPI opisuje kontrakt REST.

Redis, WebSocket ani przeglądarka nie zastępują PostgreSQL. Po reconnectcie
klient pobiera aktualny snapshot przez REST, a następnie wraca do właściwej
grupy odbiorców WebSocket.

### 2.2. Granica domeny turniejowej i gry kościanej

Architektura rozdziela odpowiedzialności, nawet gdy kod pozostaje w jednej
aplikacji Django `tournaments`.

**Moduły turniejowe** odpowiadają za:

- turniej, organizatorów, uczestników i składy drużynowe;
- etapy, rundy, grupy, stoły oraz przydziały;
- cykl życia wydarzenia i bariery pomiędzy rundami;
- ranking, awans, dogrywkę i końcową klasyfikację;
- agregaty oraz statystyki uczestników i drużyn pomiędzy rundami i turniejami;
- historię turnieju oraz dostęp do zakończonych danych.

**Moduły gry kościanej** odpowiadają za:

- grę przy stole, kolejność uczestników i tury;
- rzuty pięcioma kośćmi oraz zatrzymania;
- kategorie formularza, analizę kości i punktację;
- `DiceContext`, `ScoringContext`, `ScoringResult` i strategie kategorii.

Warstwa turniejowa przekazuje do gry skład stołu i zamrożony zestaw reguł.
Warstwa gry zwraca zatwierdzony rezultat. Punktacja nie przydziela stołów, nie
tworzy rund i nie ustala awansu.<br>Grupowanie oraz ranking nie analizują kości.

Nie powstaje osobna aplikacja `gameplay`, ponieważ rozgrywka nie ma niezależnego
cyklu życia poza turniejem. Granicę realizują moduły, serwisy, kontrakty i testy,
a nie sztuczne mnożenie aplikacji Django.

### 2.3. Warstwy odpowiedzialności

- endpoint przyjmuje żądanie i formuje odpowiedź;
- serializer waliduje kształt danych;
- permission sprawdza dostęp do konkretnego obiektu;
- serwis domenowy wykonuje przypadek użycia i kontroluje transakcję;
- model i constraints utrwalają niezmienniki;
- publisher ogłasza zdarzenie dopiero po commitcie;
- consumer WebSocket uwierzytelnia połączenie i dostarcza aktualizacje.

Logika biznesowa nie znajduje się w consumerze, serializerze ani JavaScripcie.
Zmiana statusu następuje wyłącznie w wyniku dozwolonej operacji biznesowej
i zgodnie z regułami przejścia między stanami; status nie jest polem,
które można ustawiać bezpośrednio.

## 3. Model danych

### 3.1. Tożsamość i udział

`PlayerProfile.user` jest relacją `OneToOneField`: konto ma zero albo jeden
profil, a każdy profil należy do jednego konta. `TournamentParticipant`
przechowuje migawkę pełnego imienia i nazwiska, nazwy prezentacyjnej i nickname'u
oraz numer startowy i rozstawienie ustalone przez organizatora. Po rozpoczęciu
turnieju migawka jest blokowana.

Nickname jest dowolną nazwą prezentacyjną, lecz walidacja odrzuca określenia
sugerujące wynik lub pozycję turniejową. Skrócenie pełnej nazwy jest wyłącznie
decyzją prezentacyjną widoku.

Konto bez `PlayerProfile` może korzystać wyłącznie z dozwolonych widoków
obserwatora. Nie otrzymuje uprawnień uczestnika, dostępu do sterowania stołem ani
mechanizmu przekazywania strategicznych podpowiedzi.

### 3.2. Drużyny, grupy i stoły

Drużyna oznacza zatwierdzony skład w konkretnym turnieju. Grupa jest tymczasowym
przydziałem rundy, a stół miejscem rozgrywki. Pojęcia nie są zamienne.

Warstwa prezentacji oznacza stoły numerem porządkowym, np. `Stół #1`. Numer
widoczny jest stabilny w ramach turnieju, lecz pozostaje oddzielony od klucza
technicznego i nie podlega edycji przez uczestnika.

W V2 `Team` identyfikuje drużynę pomiędzy wydarzeniami, a `TournamentTeam`
zapisuje jej nazwę, udział i historyczny skład w jednym turnieju. Zmiana bieżącej
drużyny nie zmienia zakończonych wyników.

### 3.3. Modele turniejowe

- `Tournament`, `TournamentRuleSet` i `TournamentOrganizer`;
- `TournamentParticipant`, `Team` i `TournamentTeam` w odpowiednim zakresie;
- `Stage`, `Round`, `Group`, `GroupParticipant` i `Match`;
- dane źródłowe klasyfikacji oraz agregaty odczytowe.

### 3.4. Modele gry kościanej

- `Game` i `GameParticipant`;
- `Turn` jako jedna tura uczestnika;
- `Roll` jako pełna migawka pięciu kości, numer rzutu i zatrzymania;
- wpis formularza z kategorią, wynikiem i znaczeniem symbolu `X`.

`Roll` zapisuje pięć końcowych wartości także wtedy, gdy w drugim lub trzecim
rzucie zmieniła się tylko część kości. Replay nie rekonstruuje stanu z domysłów.

`TournamentTeam` zachowuje zatwierdzony skład historyczny i jego liczebność.
Wycofanie, zakończenie udziału lub dyskwalifikacja zmienia stan uczestnika, ale
nie usuwa członkostwa.<br>Liczba osób nadal grających jest osobnym agregatem.

### 3.5. Historia, replay i audyt

Historia źródłowa obejmuje zaakceptowane rzuty, tury, wyniki, składy grup, rundy
i etapy. Replay rekonstruuje zaakceptowany przebieg gry. `AuditEvent` obejmuje
również odrzucone próby, interwencje organizatora i zmiany statusów. Odrzucona
akcja nie trafia do replay'a.

Czas jest zapisywany w UTC i prezentowany jako rzeczywisty czas zegarowy w jawnej
strefie turnieju, a nie jako czas od rozpoczęcia wydarzenia.

## 4. Cykle życia i reguły

### 4.1. Turniej

Przejścia statusów wykonują komendy domenowe. Rozpoczęcie, zakończenie i anulowanie
sprawdzają rolę, stan źródłowy i warunki. Zwykły `PATCH` nie zmienia dowolnie
statusu.<br>Nowa runda grupowa czeka na zakończenie wszystkich stołów bieżącej rundy.

### 4.2. Tura gry kościanej

Każda tura zaczyna się rzutem wszystkich pięciu kości. Zatrzymania są dostępne
dopiero po pierwszym rzucie. Drugi i trzeci obejmują tylko kości niezatrzymane.
Czwarty rzut jest odrzucany.<br>Tura kończy się po wyborze legalnej, niewykorzystanej
kategorii. Backend sprawdza te reguły niezależnie od stanu interfejsu.

### 4.3. Przydział do stołów

Stół ma 2–6 uczestników. Najpierw ustalane są możliwie równe liczebności,
z różnicą nieprzekraczającą jednej osoby. Następnie stosuje się koszyki, układ
wężykowy i ograniczoną optymalizację powtórnych spotkań oraz konfliktów drużyn.

Algorytm ogranicza konflikty, lecz nie gwarantuje ich usunięcia. Może sprawdzać
permutacje w koszyku, a przy istotnym konflikcie także koszyk bezpośrednio
sąsiedni.<br>Nie przechodzi kaskadowo do dalszych koszyków. Jeżeli lokalny zakres
nie wystarcza, zwraca wariant o najlepszym osiągalnym koszcie.<br>Ograniczenia
twarde, funkcja kosztu i ocena wariantów są deterministyczne. Gdy istnieje jeden
najlepszy wariant, algorytm wybiera właśnie jego.<br>Kontrolowane losowanie jest
dopuszczalne wyłącznie pomiędzy wariantami o identycznym najlepszym koszcie;
nie może pogorszyć kosztu, naruszyć ograniczeń twardych<br>ani rozszerzyć obszaru
poszukiwania poza bezpośrednio sąsiedni koszyk.

### 4.4. Ranking, remis i dogrywka

Przy równej sumie porównuje się malejąco najlepszy, drugi najlepszy i kolejne
wyniki rund. To nie jest dogrywka. Dogrywkę tworzy się tylko dla nadal remisujących,
gdy wynik wpływa na zwycięstwo, awans lub rozstawienie. Kolejne dogrywki obejmują
wyłącznie nierozstrzygniętą grupę. Losowanie jest jawną, audytowaną ostatecznością,
gdy dalsza dogrywka jest obiektywnie niemożliwa.

### 4.5. Agregaty i statystyki turniejowe

Podstawowe agregaty uczestnika to suma, średnia rundowa, najlepsza runda i liczba
rozegranych rund. Dla drużyny **średnia rundowa drużyny** dzieli łączną sumę
punktów przez liczbę faktycznie rozegranych wyników uczestnik–runda i jest
podstawową miarą porównawczą pomiędzy turniejami. **Średni dorobek punktowy na
członka zatwierdzonego składu** dzieli tę samą sumę przez historyczną liczebność
`TournamentTeam`. Statystyki zachowują oba mianowniki, łączną sumę i historyczną
liczebność. Wyniki uzyskane przed zakończeniem udziału pozostają w statystykach,
a brakujące przyszłe rundy nie tworzą fikcyjnych zer.

## 5. Silnik punktacji

Niemutowalny `DiceContext` analizuje pięć kości raz. `ScoringContext` dodaje
zamrożoną konfigurację i numer rzutu, jeśli wpływa on na wynik. Rejestr Strategy
mapuje dozwolony identyfikator kategorii na wspólny kontrakt. Klient wybiera
kategorię, nigdy nazwę funkcji.

`ScoringResult` rozróżnia punkty, zaliczenie szkółki i trwałe odpisanie figury.
`X` w szkółce oznacza sukces, a w figurach definitywne wykorzystanie pola bez
punktów.

Silnik nie pobiera rankingu, rundy ani drużyny. Otrzymuje wyłącznie dane potrzebne
do oceny kategorii. Serwis gry zapisuje rezultat, a domena turniejowa wykorzystuje
go w klasyfikacji i barierze rundy.

Frontend nie otrzymuje rekomendacji ani prognozy punktów. `ⓘ` wyjaśnia stałą
regułę kategorii, ale nie analizuje bieżącego rzutu.

## 6. REST API i komendy

REST obsługuje odczyt snapshotów oraz wszystkie operacje zmieniające stan:
konta, konfigurację turnieju, zapis uczestnictwa, komendy cyklu życia, rzut,
zatrzymania, wybór kategorii, historię, replay i działania organizatora.

Samodzielny zapis nie przyjmuje numeru startowego, rozstawienia, drużyny, koszyka,
grupy ani stołu. Pola zabronione są odrzucane. Odpowiedź zawiera stabilny kod
maszynowy,<br>który frontend mapuje na naturalny komunikat po polsku.

## 7. Uwierzytelnienie i autoryzacja

JWT potwierdza tożsamość użytkownika, ale nie daje mu automatycznie dostępu do każdego obiektu. System osobno sprawdza, czy użytkownik ma prawo wykonać daną operację na konkretnym obiekcie, dzięki czemu nie wystarczy podać lub zmienić jego identyfikatora, aby uzyskać nieuprawniony dostęp (IDOR/BOLA).

Organizator jest reprezentowany przez `TournamentOrganizer` i nie otrzymuje
automatycznie `is_staff`; `is_superuser` pozostaje wyjątkowym pełnym uprawnieniem
systemowym.<br>Uczestnik korzysta z własnych zasobów bez podawania
w payloadzie właściciela akcji. Własną historię widzi dopiero po zakończeniu
turnieju. Gość nie otrzymuje roboczego API ani prywatnych składów.

Żądania uwierzytelniane za pomocą sesji lub ciasteczek są chronione przed CSRF.
W przypadku JWT przesyłanego w nagłówku `Authorization` taka ochrona nie jest potrzebna,
ponieważ przeglądarka nie dołącza tokenu automatycznie do żądania.

## 8. Komunikacja czasu rzeczywistego

REST wykonuje komendę w transakcji. Po commitcie publisher wysyła zdarzenie do
właściwej grupy odbiorców WebSocket.<br>Consumer nie wykonuje rzutu, punktacji ani
przejścia statusu. Przy wykryciu luki klient pobiera snapshot przez REST.

Zwykła zmiana stanu oznacza trwały zapis domenowy i nietrwały push. Problem
wymagający reakcji tworzy trwały incydent, alarm albo wpis audytowy, a następnie
push.<br>Nie powstaje generyczny model `Notification` ani archiwum wszystkich
wiadomości WebSocket; po reconnectcie organizator odzyskuje nierozwiązane sprawy
ze stanu domenowego przez API.

Połączenie trafia do grupy odbiorców dopiero po uwierzytelnieniu i sprawdzeniu
relacji z turniejem. Klient nie wybiera dowolnej grupy ani cudzego stołu.<br>
Nowy oficjalny przydział automatycznie przenosi użytkownika do właściwego widoku.
Ręczna zmiana stołu jest wyjątkową, uzasadnioną i audytowaną interwencją.

Krótkie zerwanie uruchamia reconnect i okres tolerancji. Następnie uczestnik ma
stan `disconnected`, a organizator otrzymuje alert; nie ma automatycznego usunięcia.<br>
Powrót wymaga ponownego uwierzytelnienia i odtwarza najnowszy stan bez cofnięcia
tury, ponowienia zaakceptowanej akcji ani resetu terminu decyzji.<br>Po faktycznym
zakończeniu udziału stan `removed` nie wraca automatycznie do `connected`.<br>
Reconnect WebSocket nie odnawia wygasłej sesji ani nie zastępuje ponownego
logowania wymaganego przez reguły tokenów.<br>
Usunięcie z gry, wycofanie lub dyskwalifikacja są osobnymi decyzjami, a historia
pozostaje w bazie. Awaria ogólna nie obciąża pojedynczego uczestnika.

Otwarcie strony, heartbeat, aktualizacje, animacja, odliczanie i ruch myszy nie
resetują bezczynności. Resetuje ją rzeczywista, uwierzytelniona akcja użytkownika.

### 8.1. Forma wydarzenia i sposób rzutu

Podstawowa konfiguracja `Tournament`, a od wersji 1.0 jej niezmienny snapshot
`TournamentRuleSet`, rozróżnia turniej stacjonarny z fizycznymi kośćmi oraz
turniej zdalny z wirtualnym rzutem backendu. Jedno wydarzenie nie łączy obu form.

W formie stacjonarnej aktywny uczestnik przesyła odczytane wartości.
Backend sprawdza tożsamość, turę, numer rzutu, zatrzymania, zakres wartości
i legalność operacji,<br>ale nie udaje technicznego potwierdzenia układu na stole.
Spór rozstrzyga organizator z uwzględnieniem relacji obecnych osób.

W formie zdalnej klient wysyła wyłącznie intencję rzutu, a wartości generuje
backend. Forma i sposób rzutu są zamrożone przed rozpoczęciem turnieju.

Nie powstaje rola ani model sędziego lub operatora stołu. Fizyczny wynik
rejestruje aktywny uczestnik, a incydenty rozstrzyga organizator.

Online oznacza komunikację z serwerem, LAN i Internet są rodzajami sieci,
a WebSocket mechanizmem aktualizacji.<br>Klient bez połączenia może pokazać ostatni
stan, ale nie zatwierdza wiążących akcji. Po reconnectcie pobiera stan źródłowy.

## 9. Współbieżność i idempotencja

Komendy aktywnej tury blokują właściwy stan przez transakcję i
`select_for_update()` albo równoważną kontrolę wersji.<br>Constraints chronią przed
podwójnym uczestnictwem, wielokrotnym użyciem kategorii i niespójnym rzutem.

Rzut zawiera klucz idempotencji. Ten sam użytkownik, gra i klucz zwracają zapisany
rezultat bez nowego losowania.<br>Nowy legalny rzut używa nowego klucza i może dać
identyczne kości. Idempotencja nie zmienia prawdopodobieństwa.

## 10. Frontend i UX

MVP ma minimalny, funkcjonalny frontend dla desktopu lub laptopa, tabletu
i telefonu, bez zamrażania dokładnych breakpointów w planie. Dopracowanie
wizualne następuje po ustabilizowaniu backendu, API, reguł i testów. Mysz i dotyk
są podstawowe. Nie powstaje własny system skrótów, a semantyczne kontrolki
zachowują standardową obsługę przez `Tab`, `Enter` i spację.
`prefers-reduced-motion` ogranicza animacje.

Przycisk ma etykietę „Rzuć” przed pierwszym rzutem i „Rzuć ponownie” po pierwszym
lub drugim. Pozostaje w stałym miejscu, a po trzecim rzucie, poza własną turą,
po wyborze kategorii i podczas obsługi żądania ma stan `disabled`. Nie istnieje
trwała kolumna `can_roll`; wartość wynika z autorytatywnego stanu. Kliknięcie
nazwy kategorii albo własnej aktywnej komórki wykonuje tę samą komendę wyboru
dla uczestnika aktualnie rozgrywającego turę. Oddzielny `ⓘ` tylko pokazuje regułę
i nigdy nie wybiera kategorii. Cudze pola nie wysyłają komend.

Panel organizatora nie paginuje aktywnych stołów. Obejmuje stałe podsumowanie,
zwartą przewijalną listę lub siatkę, niezależną kolejkę alertów i szczegół jednego
stołu. Alert nie znika wskutek przewinięcia lub filtra. Pełne dane zakończonych
stołów należą do historii; paginacja dotyczy audytu i archiwum.

Publiczny ekran pokazuje etap, rundę, postęp i neutralne komunikaty. Nie ujawnia
alarmów, prywatnych danych ani rankingu w trakcie etapu.

Kafel turnieju pokazuje nazwę, status, organizatorów, liczebność i opcjonalnie liczbę drużyn.
Osoby bez drużyny są wyświetlane osobno pod nagłówkiem **„Udział indywidualny”**.<br>
Przed dołączeniem widoczna jest liczba i dostępność miejsc, nie pełny skład.

## 11. Wydajność i skala

Granica wynosi 128 uczestników. Najdroższe ścieżki używają `select_related()`,
`prefetch_related()`, `Prefetch()`, agregacji i indeksów wynikających z zapytań.
Testy chronią reprezentatywne widoki przed N+1. Aktywny stan gry nie jest
cache'owany bez pomiaru i poprawnej invalidacji. Historia i audyt są paginowane.

## 12. Bezpieczeństwo i integralność

- w turnieju zdalnym backend generuje kości, a w stacjonarnym waliduje wartości
  zgłoszone przez aktywnego uczestnika; zawsze oblicza wiążącą punktację;
- klient nie przesyła właściciela akcji, ziarna ani samodzielnie obliczonej
  punktacji;
- throttling chroni logowanie, refresh, reset hasła i komendy gry;
- reset hasła nie ujawnia istnienia konta;
- sekrety pochodzą ze zmiennych środowiskowych;
- PostgreSQL i Redis nie są wystawiane publicznie;
- logi nie zawierają haseł, tokenów ani pełnych danych wrażliwych;
- ochronę przed wolumetrycznym DDoS realizuje infrastruktura przed Django.

Trwała blokada po kilku błędach, CAPTCHA, własny WAF i automatyczne banowanie
zakresów IP nie należą do MVP.

## 13. Celery

Co najmniej dwie oddzielne kolejki i przypisani do nich workerzy obsługują
powiadomienia organizacyjne oraz zadania utrzymaniowe.<br>Celery Beat uruchamia
zadania cykliczne. Zadania są zlecane po commitcie i otrzymują identyfikatory.

Rzut, zatrzymanie kości, wybór kategorii, zamknięcie rundy, ranking i awans
pozostają synchroniczne oraz transakcyjne.

## 14. Testowalność

Podstawą jest `pytest` z `pytest-django`. Testy obejmują czystą punktację,
algorytm przydziału, modele i constraints, serializery, permissions, serwisy,
reprezentatywne operacje CRUD, API i widoki, autoryzację obiektową, współbieżność,
idempotencję, Channels, Celery oraz reconnect. Testowane są stoły 2–6, odrzucenie
1 i 7 oraz granice 128 i 129. Testy V2 rozróżniają mianowniki obu statystyk
drużynowych, zachowanie historycznej liczebności zatwierdzonego składu po
zakończeniu udziału członka i brak fikcyjnych zer za jego przyszłe rundy.

Testy domeny turniejowej korzystają z gotowego rezultatu gry, gdy nie badają
integracji. Testy punktacji nie tworzą turnieju ani bazy. Testy integracyjne
sprawdzają wąski kontrakt między obszarami.

Dane testowe powstają z fabryk, a ORM nie jest mockowany. Atrapy są stosowane
na granicach losowości, czasu, poczty i usług zewnętrznych. Raport pokrycia
wskazuje luki, lecz nie narzuca sztucznego celu 100%.

## 15. Obserwowalność i audyt operacyjny

Logi mają poziomy, identyfikator korelacji i bezpieczny kontekst turnieju, stołu
oraz komendy. Nie zastępują audytu domenowego. Monitorowane są błędy `4xx`, `5xx`,
odpowiedzi `429`, połączenia WebSocket, opóźnienia komend i stan usług.

Alert ma status `nowy`, `sprawdzany` lub `zamknięty`. Korekta wyłącznie
udowodnionego błędu zapisu oraz decyzja o zakończeniu dalszego udziału wymagają
autora, uzasadnienia i audytu.<br>Korekta nie jest karą punktową ani arbitralnym
przepisaniem wyniku. Nie powstaje dowolny notatnik opinii o uczestnikach.

System nie oferuje taryfikatora kar, ręcznego odejmowania punktów ani zwykłego
przesuwania uczestników między stołami.<br>Skrajna decyzja może zakończyć dalszy
udział, lecz nie usuwa wcześniejszej historii ani uzyskanych wyników.

## 16. Środowiska i wdrożenie

Ustawienia rozdzielają wspólną bazę, development, test i production. Development
również używa PostgreSQL.
Testy zależne od transakcji i constraints używają PostgreSQL. Production wymaga
`DEBUG=False`, TLS, bezpiecznych cookies, jawnych hostów i konfiguracji zewnętrznej.

Docker Compose obejmuje ASGI, PostgreSQL, Redis, dwóch workerów Celery i Beat.
Healthchecki określają gotowość usług. Ten sam zestaw zależności obowiązuje
lokalnie, w kontenerach i CI.

Projekt jest production-aware, lecz publiczne wdrożenie, Nginx, Let's Encrypt,
AWS, WAF i infrastrukturalne kopie zapasowe nie warunkują ukończenia MVP.

Development i production opisują środowisko uruchomienia, natomiast MVP, V1
i V2 zakres funkcjonalny. Są to niezależne osie: ta sama wersja produktu może
działać w konfiguracji development albo production.

## 17. Roadmapa i punkty rozszerzeń

MVP obejmuje kompletny turniej grupowy, autorytatywną grę kościaną, REST,
realtime, testy, PostgreSQL, Docker, Celery i CI.<br>V1 dodaje fazę pucharową,
pełny audyt, alarmy i dopracowanie interfejsu.<br>V2 obejmuje trwałe `Team`,
`TournamentTeam`, porównania drużynowe, Pygame, WebAuthn i opcjonalne 3D.

Punktem rozszerzenia jest rejestr strategii punktacji i zamrożona konfiguracja
reguł w ramach rodziny gier kościanych. Uniwersalne modele turniejowe nie są
obietnicą obsługi dowolnego rodzaju gry.
