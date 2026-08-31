# System organizacji uniwersalnych turniejów gry w kości

## 1. Wizja i kontekst biznesowy

### 1.1. Wizja

System ma być jedynym, wiarygodnym miejscem do przygotowania, przeprowadzenia i późniejszej analizy uniwersalnych turniejów gry w kości. Ma automatyzować czynności organizacyjne, ale nie zastępować decyzji strategicznych uczestników ani ukrywać reguł, według których powstają wyniki i awanse.

### 1.2. Kontekst biznesowy

Projekt odpowiada na problem organizowania turniejów gry w kości, w których uczestnicy rozgrywają wiele rund przy kilku stołach, a wyniki, rankingi, awanse i historia rozgrywek muszą być kontrolowane w jednym miejscu.

W tradycyjnym przebiegu turnieju wyniki są zapisywane ręcznie, ranking jest przeliczany po kolejnych rundach, a organizator musi jednocześnie pilnować kolejności graczy, poprawności punktacji i zasad awansu. Przy większej liczbie uczestników prowadzi to do opóźnień, pomyłek i utraty szczegółowej historii rozgrywek.

W odpowiedzi na te problemy aplikacja webowa:

- prowadzi turniej od zapisów do ogłoszenia końcowych wyników;
- obsługuje fazę grupową i następującą po niej fazę pucharową;
- automatycznie tworzy grupy, oblicza rankingi i wyznacza awanse;
- pilnuje kolejności oraz poprawności akcji wykonywanych przy wielu stołach;
- przechowuje nie tylko końcowe wyniki, lecz także historię każdego rzutu i decyzji uczestnika;
- buduje uniwersalną historię zakończonych turniejów gry w kości;
- pozwala porównywać wyniki tego samego uczestnika, a docelowo także drużyn, wyłącznie pomiędzy zakończonymi turniejami.

„Uniwersalny” oznacza tutaj możliwość konfigurowania przebiegu turnieju i wybranych reguł punktacji w ramach tej samej rodziny gier kościanych. Nie oznacza możliwości obsługi dowolnej gry.

---

## 2. Problem i cele biznesowe

### 2.1. Problemy

- ręczne zapisywanie i sumowanie wyników;
- ryzyko wpisania nieprawidłowej liczby punktów;
- trudność w prowadzeniu równoległych rozgrywek przy kilku stołach;
- brak jednej, wiarygodnej historii turniejów, rund, rozgrywek i rzutów;
- trudność w odtworzeniu przebiegu spornej rozgrywki;
- brak bezpiecznego porównywania rezultatów uczestnika z różnych turniejów;
- czasochłonne tworzenie możliwie równych grup i drabinki pucharowej.

### 2.2. Cele

- skrócenie czasu obsługi turnieju;
- ograniczenie błędów przez wyliczanie punktów po stronie systemu;
- zapewnienie jednego źródła prawdy o przebiegu turnieju;
- rozdzielenie interfejsu aktywnej gry od interfejsu późniejszej analizy;
- zachowanie danych źródłowych, z których można ponownie wyliczyć wyniki;
- umożliwienie organizatorowi nadzorowania wszystkich stołów;
- przygotowanie projektu jako dopracowanego zestawu pionowych przekrojów funkcjonalnych, a nie zbioru przypadkowych endpointów.

### 2.3. Priorytety

1. Poprawność zasad i punktacji.
2. Integralność i historia danych.
3. Bezpieczeństwo oraz właściwe uprawnienia.
4. Szybka i czytelna obsługa przy stole.
5. Czytelny ranking i archiwum.
6. Analityka i efekty wizualne.

Zakres nie wynika z liczby modeli, endpointów ani wykorzystanych bibliotek. Projekt koncentruje się na kilku kompletnych przepływach obejmujących poprawne reguły, świadomy model danych, uprawnienia, walidację, testy i dokumentację. Funkcja albo technologia trafia do projektu tylko wtedy, gdy wspiera konkretny przypadek użycia.

---

## 3. Role i podstawowe pojęcia

### 3.1. Konto użytkownika

`User` oznacza neutralne konto w systemie, a nie organizatora turniejów. Uprawnienia organizatora lub uczestnika wynikają z relacji użytkownika z konkretnym turniejem.

Ta sama osoba może być uczestnikiem jednego turnieju i organizatorem innego. System nie zakłada globalnej roli „organizator”.

Konto może nie mieć profilu zawodnika i służyć wyłącznie do oglądania jawnych
informacji oraz kibicowania. Aplikacja nie udostępnia obserwatorom sterowania
rozgrywką ani strategicznych podpowiedzi dla uczestników.

### 3.2. Organizator

Zalogowany użytkownik przypisany do turnieju jako organizator. Tworzy i konfiguruje turniej, zarządza uczestnikami, uruchamia etapy, nadzoruje stoły, reaguje na nieprawidłowości i zatwierdza zakończenie turnieju.

Turniej może mieć więcej niż jednego organizatora. Osobna rola sędziego ani
operatora stołu nie należy do projektu; nadzór realizują organizatorzy,
a fizyczny wynik rejestruje aktywny uczestnik pod kontrolą osób przy stole.

### 3.3. Uczestnik

Osoba biorąca udział w rywalizacji. Konto uczestnika jest reprezentowane przez profil zawodnika, a udział w konkretnym turnieju przez encję pośrednią `TournamentParticipant`.

### 3.4. Drużyna

Stała jednostka współpracy w obrębie turnieju. Uczestnik może należeć najwyżej do jednej drużyny w danym turnieju. Drużyna:

- służy do dodatkowej klasyfikacji drużynowej;
- jest uwzględniana przy rozdzielaniu uczestników do grup;
- nie wpływa na indywidualny awans do fazy pucharowej;
- może mieć różny skład w różnych turniejach.

### 3.5. Grupa i stół

Grupa jest tymczasowym przydziałem uczestników wynikającym z mechanizmu turnieju
w konkretnej rundzie fazy grupowej. Nie jest drużyną i nie ma własnego
długoterminowego rankingu. Stół jest konkretną jednostką rozgrywki, przy której
realizowany jest przydział grupy.

Stoły są prezentowane użytkownikom przez prosty numer porządkowy, np. `Stół #1`.
Nazwa widoczna nie jest technicznym kluczem rekordu ani dowolną nazwą nadawaną
przez uczestnika.

### 3.6. Etap, runda, rozgrywka, tura i rzut

Aby uniknąć niejednoznaczności, projekt przyjmuje następującą hierarchię:

```text
Turniej
└── Etap: faza grupowa albo faza pucharowa
    └── Runda turniejowa: np. runda grupowa nr 3 albo ćwierćfinał
        └── Rozgrywka: gra przy jednym stole albo jedna gra w meczu
            └── Tura uczestnika: maksymalnie trzy rzuty zakończone wyborem kategorii
                └── Rzut: wartości kości i informacja o zatrzymanych kościach
```

„Runda” w dalszej części dokumentu zawsze oznacza rundę turniejową. Pojedyncza kolejka uczestnika przy stole jest nazywana „turą”.

### 3.7. Niezmienna zasada pierwszego rzutu

**Każda nowa tura ZAWSZE zaczyna się od jednoczesnego rzutu wszystkimi pięcioma kośćmi.** Przed pierwszym rzutem nie można zatrzymać żadnej kości. Dopiero po zapisaniu jego wyniku uczestnik może wybrać zatrzymania; drugi i trzeci rzut obejmują wyłącznie kości niezatrzymane. Następna tura ponownie zaczyna się od pięciu niezatrzymanych kości.

### 3.8. Administrator systemowy

Użytkownik z `is_staff` i odpowiednimi permissions, zarządzający działaniem całej instalacji przez Django Admin. Nie jest automatycznie organizatorem każdego turnieju. Ma dostęp techniczny tylko w zakresie potrzebnym do obsługi kont, diagnostyki, sporów i retencji; `is_superuser` pozostaje kontem wyjątkowym, a nie rolą używaną do codziennej pracy.

### 3.9. Granica domeny turniejowej i gry kościanej

System obejmuje dwa współpracujące, lecz rozdzielone obszary odpowiedzialności.

- **Domena turniejowa** zarządza turniejem, organizatorami, uczestnikami,
  drużynami turniejowymi, etapami, rundami, przydziałami do grup i stołów,
  rankingami, awansem oraz cyklem życia wydarzenia.
- **Domena gry kościanej** zarządza przebiegiem gry przy stole: kolejnością tur,
  rzutami pięcioma kośćmi, zatrzymaniami, kategoriami formularza i obliczaniem
  punktacji.

Domena turniejowa przyjmuje zatwierdzony wynik rozgrywki, ale nie zna reguł
rozpoznawania figur ani obsługi kości. Domena gry otrzymuje skład stołu i zestaw
reguł obowiązujący w turnieju, ale nie decyduje o zapisach, przydziale do rundy,
awansie ani klasyfikacji. Granica ta nie wymaga osobnej aplikacji `gameplay` ani
budowy silnika dla dowolnych gier. Oba obszary pozostają modułami aplikacji
`tournaments`, ponieważ rozgrywka nie istnieje w produkcie poza turniejem.

### 3.10. Forma wydarzenia, sieć i sposób rzutu

Forma wydarzenia i sposób komunikacji są niezależnymi osiami. Turniej
stacjonarny odbywa się w jednym miejscu, a zdalny przez Internet. Połączenie
online może działać przez Internet albo lokalną sieć LAN. Realtime oznacza
aktualizowanie stanu, a nie osobny rodzaj turnieju. Brak publicznego Internetu
nie jest trybem offline, jeżeli urządzenia nadal łączą się z serwerem przez LAN.

Turniej stacjonarny używa fizycznych kości, a aktywny uczestnik rejestruje wynik
w aplikacji pod kontrolą pozostałych osób przy stole. Turniej zdalny korzysta
z wirtualnego rzutu generowanego przez backend. Jedno wydarzenie nie łączy obu
form w tryb hybrydowy. Nie powstaje osobna rola sędziego ani operatora stołu;
nadzór i rozstrzyganie incydentów należą do organizatorów.

---

## 4. Zasady turnieju

Sekcja opisuje pełny kontrakt produktu docelowego. MVP implementuje z niego fazę grupową z wieloma rundami, rotacją stołów i rankingiem końcowym. Faza pucharowa, pełny audyt oraz cykl anulowania dochodzą w wersji 1.0 bez zmiany zasad już zaimplementowanej rozgrywki grupowej.

### 4.1. Cykl życia turnieju

Turniej przechodzi przez kontrolowane statusy:

1. `DRAFT` — konfiguracja i przygotowanie;
2. `REGISTRATION` — zapisy i ustalanie składów;
3. `ACTIVE` — trwająca faza grupowa lub pucharowa;
4. `COMPLETED` — rozgrywki zostały zakończone, a rezultaty zablokowane;
5. `ARCHIVED` — turniej pozostaje w historii, ale nie jest eksponowany w bieżących widokach;
6. `CANCELLED` — turniej został anulowany bez ogłoszenia końcowych rezultatów; dotychczasowa historia pozostaje czasowo dostępna do audytu, ale nie uczestniczy w porównaniach.

Nie można ponownie otworzyć zakończonego ani anulowanego turnieju zwykłą akcją użytkownika. Ewentualna korekta administracyjna musi być jawna, audytowalna i nie może nadpisywać historii bez śladu.

Anulowanie jest sytuacją wyjątkową, ale potrzebną w modelu. Może wynikać np. ze zbyt małej liczby uczestników, niedostępności miejsca lub organizatora, poważnej awarii infrastruktury albo błędu konfiguracji wykrytego przed rozpoczęciem. Szkic `DRAFT`, dla którego nie rozpoczęto zapisów, można trwale usunąć bez tworzenia anulowanego turnieju. W `REGISTRATION` uprawniony organizator może anulować turniej po podaniu powodu. Anulowanie turnieju `ACTIVE` wymaga dodatkowego jawnego potwierdzenia, zapisu osoby wykonującej operację i niepustego uzasadnienia. Nie tworzy zwycięzcy i nie kwalifikuje turnieju do historii porównawczej.

Pełne dane turnieju `CANCELLED` są domyślnie przechowywane przez 30 dni od anulowania, aby umożliwić wyjaśnienie sporu, awarii albo podejrzanego zdarzenia. Po upływie tego okresu szczegółowe dane, powiązania z kontami, zgłoszenia, rzuty i swobodny opis powodu są trwale usuwane. Pozostaje wyłącznie anonimowy rekord zbiorczy bez kluczy obcych do użytkowników: data anulowania, etap, kategoria powodu oraz liczba uczestników i rozpoczętych rund. Udokumentowany, nierozstrzygnięty spór może czasowo wstrzymać usunięcie; blokada wymaga uprawnienia administracyjnego, powodu, terminu końcowego i wpisu audytowego.

### 4.2. Konfiguracja przed rozpoczęciem

Organizator ustala co najmniej:

- tryb zapisów: `ORGANIZER_ONLY` albo `OPEN`;
- minimalną liczbę uczestników oraz limit maksymalnie 128 aktywnych uczestników jednego turnieju;
- opcjonalny termin zakończenia zapisów;
- liczbę rund fazy grupowej — domyślnie 5, ale większa liczba, np. 20, jest dopuszczalna przy odpowiednio licznej obsadzie;
- preferowaną liczebność grup od 2 do 6 osób;
- liczbę uczestników awansujących do fazy pucharowej;
- liczbę rozgrywek składających się na jeden mecz pucharowy;
- wariant punktowania pokerów;
- kolejność uczestników przy stole;
- maksymalny czas na decyzję: bez limitu, 30, 60 albo 90 sekund;
- zasady publikacji końcowych wyników.

Konfiguracja wpływająca na wynik nie może zostać zmieniona po rozpoczęciu turnieju. Turniej zachowuje wersję zestawu reguł, dzięki czemu historyczne wyniki pozostają interpretowalne po zmianach aplikacji.

Limit 128 dotyczy pojedynczego turnieju, a nie łącznej liczby kont ani uczestnictw historycznych przechowywanych w systemie. Większa skala wymaga osobnych testów obciążeniowych i ponownej oceny sposobu prezentowania oraz synchronizowania wielu stołów.

#### 4.2.1. Zapisy do turnieju

Turniej obsługuje dwa tryby zapisów:

- `ORGANIZER_ONLY` — uczestników dodaje lub zaprasza wyłącznie organizator;
- `OPEN` — zalogowany użytkownik z `PlayerProfile` może zapisać się samodzielnie.

W trybie `OPEN` dołączenie jest możliwe tylko wtedy, gdy turniej ma status `REGISTRATION`, zapisy nie zostały ręcznie zamknięte, nie minął termin i pozostaje wolne miejsce. Serwis wykonuje sprawdzenie po zablokowaniu rekordu turnieju w transakcji, aby przy jednym ostatnim miejscu dwa równoległe żądania nie zapisały dwóch osób. Pierwsze poprawne żądanie tworzy lub reaktywuje `TournamentParticipant`, a drugie otrzymuje konflikt `409`.

Samodzielny zapis nie pozwala uczestnikowi wybrać numeru startowego, rozstawienia,
grupy ani stołu. Numer startowy i rozstawienie ustala organizator, przydział do
grup i stołów wyznacza backend, a deklarowany przed turniejem skład drużyny
zatwierdza organizator. Endpoint `join` nie może służyć do wpływania na żaden
z tych elementów.

Uczestnik może sam zrezygnować tylko przed rozpoczęciem turnieju. Operacja `leave` ustawia status `WITHDRAWN` i zachowuje informację o wcześniejszym zapisie zamiast usuwać rekord. Ponowne dołączenie przed zamknięciem zapisów jest dozwolone, jeżeli nadal istnieje wolne miejsce. Po przejściu turnieju do `ACTIVE` samodzielne `leave` jest odrzucane; organizator może oznaczyć uczestnika jako wycofanego, podając powód, a operacja trafia do audytu.

Organizator może dodawać uczestników w obu trybach oraz zamknąć zapisy przed terminem. Turniej można rozpocząć dopiero po osiągnięciu minimalnej liczby uczestników i spełnieniu ograniczeń wymaganych przez skonfigurowane grupy oraz fazę pucharową.

Lista turniejów z otwartymi zapisami jest dostępna wyłącznie po zalogowaniu. Przed dołączeniem pokazuje podstawowe informacje, termin, skrót zasad, limit i liczbę wolnych miejsc, ale nie ujawnia pełnej listy uczestników ani danych rozgrywek.

### 4.3. Faza grupowa

- Pierwszy podział wykorzystuje ten sam mechanizm twardych ograniczeń i oceny
  kosztu co kolejne rundy. Kontrolowane losowanie może wybrać tylko pomiędzy
  równoważnymi wariantami o identycznym najlepszym koszcie.
- W fazie grupowej nie ma eliminacji.
- Każdy uczestnik rozgrywa jedną rozgrywkę w każdej rundzie grupowej.
- Po zakończeniu rundy surowe wyniki uczestnika są dodawane do jego łącznego wyniku.
- Po każdej rundzie powstaje aktualny ranking indywidualny.
- Uczestnicy nie muszą zagrać ze wszystkimi pozostałymi osobami; nie jest to pełny system „każdy z każdym”.
- Kolejna runda grupowa może zostać utworzona dopiero po zakończeniu wszystkich stołów bieżącej rundy, ponieważ jej podział zależy od aktualnego rankingu.

W obrębie tej samej rundy stoły działają niezależnie. Nie trzeba czekać, aż uczestnik przy innym stole zakończy swoją turę.

### 4.4. Tworzenie koszyków, wężyka i grup

1. Uczestnicy są sortowani malejąco według łącznego wyniku.
2. Przy remisie stosuje się reguły opisane w punkcie 4.7.
3. Ranking jest dzielony na kolejne koszyki rankingowe. Maksymalna liczba osób w koszyku odpowiada liczbie tworzonych grup.
4. Koszyki są kolejnymi warstwami rankingu: pierwszy zawiera najwyżej sklasyfikowanych uczestników, następny kolejne miejsca itd.
5. Kierunek przydzielania koszyków do grup zmienia się naprzemiennie zgodnie z mechanizmem wężykowym: od pierwszej do ostatniej grupy, następnie od ostatniej do pierwszej.
6. W obrębie każdego koszyka algorytm wyszukuje dopuszczalne permutacje
   uczestników pomiędzy grupami. Jeżeli istotnego konfliktu nie da się ograniczyć
   lokalnie, uczestnik może zostać porównany lub zamieniony wyłącznie z osobą
   z koszyka bezpośrednio sąsiedniego. Poszukiwanie nie przechodzi kaskadowo do
   dalszych koszyków.
7. Ograniczenia twarde, funkcja kosztu i ocena przydziałów są deterministyczne.
   Jeżeli istnieje jeden najlepszy wariant, zostaje wybrany. Kontrolowane
   losowanie jest dopuszczalne wyłącznie pomiędzy wariantami o dentycznym
   najlepszym koszcie i nie może pogorszyć kosztu ani rozszerzyć obszaru
   poszukiwania.
8. Do jednej grupy trafia maksymalnie jedna osoba z danego koszyka.
9. Uczestnicy są rozdzielani do możliwie równych grup liczących od 2 do 6 osób.
10. Różnica liczebności największej i najmniejszej grupy nie może przekraczać jednej osoby.

Dla 16 uczestników i 4 grup bazowy wężyk wygląda następująco:

```text
Koszyk 1:  1 → A,  2 → B,  3 → C,  4 → D
Koszyk 2:  5 → D,  6 → C,  7 → B,  8 → A
Koszyk 3:  9 → A, 10 → B, 11 → C, 12 → D
Koszyk 4: 13 → D, 14 → C, 15 → B, 16 → A
```

Otrzymujemy więc bazowo grupy `A: 1, 8, 9, 16`, `B: 2, 7, 10, 15`, `C: 3, 6, 11, 14` i `D: 4, 5, 12, 13`. Jeżeli taki przydział łączy członków tej samej drużyny albo powtarza wcześniejsze spotkanie, algorytm zamienia uczestników wewnątrz odpowiedniego koszyka. Losowość rozstrzyga pomiędzy równie dobrymi, dozwolonymi wariantami.

Ograniczenia twarde:

- każdy aktywny uczestnik trafia dokładnie do jednej grupy w danej rundzie;
- liczebność grup mieści się w dozwolonym zakresie;
- grupy są możliwie równe;
- do grupy trafia maksymalnie jedna osoba z koszyka, o ile matematycznie jest to możliwe.

Ograniczenia preferowane:

- unikanie osób z tej samej drużyny przy jednym stole;
- unikanie ponownych spotkań tych samych uczestników w fazie grupowej.

Jeżeli idealny przydział nie istnieje, algorytm wybiera rozwiązanie o najmniejszej liczbie i wadze naruszeń preferowanych. Naruszenia oraz przyczyna zastosowania przydziału zastępczego są zapisywane dla organizatora.

Koszyk jest strukturą obliczeniową algorytmu, a nie obowiązkowo osobnym modelem bazodanowym ani widocznym elementem ceremonii. W bazie trzeba zachować końcowy przydział `GroupParticipant`, wersję algorytmu, użyte wagi ograniczeń i ziarno losowania, aby dało się odtworzyć sposób utworzenia grup.

### 4.5. Faza pucharowa i eliminacje

- Do fazy pucharowej awansują najlepiej sklasyfikowani uczestnicy rankingu indywidualnego po fazie grupowej.
- Liczba awansujących odpowiada klasycznej drabince, np. 8, 16 albo 32 osoby, i nie może przekraczać liczby aktywnych uczestników.
- Rozstawienie wynika z rankingu: pierwszy gra z ostatnim rozstawionym, drugi z przedostatnim itd.
- Runda pucharowa może oznaczać 1/16 finału, 1/8 finału, ćwierćfinał, półfinał albo finał.
- Mecz składa się z jednej lub skonfigurowanej liczby rozgrywek.
- Domyślnie o zwycięstwie w meczu decyduje wyższa suma surowych wyników ze składających się na niego rozgrywek.
- Zwycięzca meczu zostaje przypisany do odpowiedniego miejsca w następnej rundzie; przegrany odpada z rywalizacji indywidualnej.
- Następna runda pucharowa rozpoczyna się dopiero po rozstrzygnięciu wszystkich meczów poprzedniej rundy.
- Remis decydujący o awansie wymaga dogrywki; losowanie jest dopuszczalne tylko wtedy, gdy dogrywka nie może się odbyć.

Oznacza to, że relacje pomiędzy rundami są dwojakie: rundy grupowe budują wspólny ranking bez eliminacji, natomiast rundy pucharowe tworzą drabinkę, w której wynik meczu wskazuje uczestnika następnego meczu.

### 4.6. Ranking indywidualny i drużynowy

Ranking indywidualny powstaje z sumy surowych wyników uczestnika w fazie grupowej. Ranking ten decyduje o awansie i rozstawieniu.

Podstawowe statystyki uczestnika obejmują sumę, średnią rundową, najlepszą rundę
i liczbę rozegranych rund. W porównaniach pomiędzy turniejami średnia jest
pokazywana razem z liczbą rund. Mediana i odchylenie standardowe mogą zostać
dodane w V2 jako analityka uzupełniająca.

Dla drużyny występują dwie różne miary:

- **średnia rundowa drużyny** — łączna suma punktów zdobytych przez członków
  podzielona przez liczbę faktycznie rozegranych wyników uczestnik–runda;
- **średni dorobek punktowy na członka zatwierdzonego składu** — suma punktów drużyny
  podzielona przez historyczną liczebność zatwierdzonego składu.

Podstawowym porównaniem wyników drużyn pomiędzy turniejami jest średnia rundowa
drużyny. Statystyki pokazują również łączną sumę punktów, historyczny skład i jego
liczebność, liczbę osób nadal grających oraz liczbę faktycznie rozegranych wyników
uczestnik–runda, aby żadna miara nie była analizowana bez kontekstu.

Ranking drużynowy:

- jest dodatkową klasyfikacją;
- nie wpływa na awans indywidualny;
- nie wpływa na rozstawienie drabinki;
- nie ogranicza liczebności drużyny.

### 4.7. Rozstrzyganie remisów

Jeżeli uczestnicy mają taki sam łączny wynik w rankingu indywidualnym, porównuje się kolejno:

1. najwyższy wynik uzyskany w pojedynczej rundzie;
2. drugi najwyższy wynik uzyskany w pojedynczej rundzie;
3. kolejne wyniki po posortowaniu malejąco;
4. wynik dogrywki, jeżeli remis wpływa na awans, rozstawienie lub inne istotne miejsce;
5. wynik losowania, tylko jeśli dogrywka jest niemożliwa.

Kolejność rozegrania rund nie wpływa na tie-break. Porównywane są malejąco posortowane wyniki rundowe.

### 4.8. Punktacja

- System przechowuje wynik wynikający z zasad gry, ale nie pozwala uczestnikowi wpisać punktów ręcznie.
- Uczestnik wybiera kategorię punktową, a backend wylicza wartość i zapisuje ją jako pochodną historii rzutów.
- Te same źródłowe wyniki zasilają ranking indywidualny, średnią rundową drużyny
  i średni dorobek punktowy na członka zatwierdzonego składu.
- Wynik uzyskany „z pierwszej ręki”, czyli po pierwszym rzucie tury, jest mnożony razy dwa.
- Brak wymaganej „szkółki” oznacza karę 50 punktów.
- Nieskreślenie żadnej figury daje premię 100 punktów.

Dokładna lista kategorii i ich funkcje punktujące znajduje się w wersjonowanym zestawie reguł. Silnik punktacji ma być niezależny od warstwy widoków i testowany osobno.

#### Wariant A — malejąca punktacja pokerów

| Poker | Punkty |
| --- | ---: |
| Szóstki | 100 |
| Piątki | 95 |
| Czwórki | 90 |
| Trójki | 85 |
| Dwójki | 80 |
| Jedynki | 75 |

#### Wariant B — rosnąca punktacja pokerów

| Poker | Punkty |
| --- | ---: |
| Jedynki | 50 |
| Dwójki | 55 |
| Trójki | 60 |
| Czwórki | 65 |
| Piątki | 70 |
| Szóstki | 75 |

Wybrany wariant obowiązuje przez cały turniej i zostaje zablokowany po jego rozpoczęciu.

### 4.9. Przebieg tury uczestnika

1. Backend sprawdza, czy trwa tura danego uczestnika, i rozpoczyna ją bez zatrzymanych kości.
2. Uczestnik wybiera akcję „Rzuć”.
3. Pierwszy rzut każdej tury zawsze obejmuje wszystkie pięć kości naraz. Przed tym rzutem nie można zatrzymać żadnej kości.
4. W turnieju zdalnym backend losuje wartości, a w stacjonarnym przyjmuje
   zweryfikowany przy stole odczyt fizycznych kości. W obu przypadkach zapisuje
   pełny wynik rzutu i sam oblicza punktację.
5. Dopiero po pierwszym rzucie uczestnik może kliknąć albo dotknąć wybrane kości. Interfejs automatycznie przenosi je do wydzielonej strefy „Zatrzymane kości” albo z powrotem do obszaru rzutu. Frontend wysyła zmianę zatrzymania do backendu, a dopiero zapisany stan określa, które kości pozostają i które zostaną przerzucone. Przeciąganie nie jest wymaganym sposobem obsługi.
6. Drugi i trzeci rzut obejmują wyłącznie kości niezatrzymane; wartości kości zatrzymanych pozostają bez zmian.
7. W turze można wykonać maksymalnie trzy rzuty.
8. Uczestnik może wcześniej wybrać dostępną kategorię punktową.
9. Wybór kategorii jest jednoznaczną decyzją kończącą turę i blokuje następne rzuty.
10. Po trzecim rzucie przycisk pozostaje w stałym miejscu jako nieaktywny.
    Uczestnik musi wybrać kategorię; dopóki backend nie przyjmie tej decyzji,
    system nie przechodzi do kolejnej osoby.
11. Backend oblicza punkty, zapisuje decyzję i przekazuje kolejkę następnej osobie zgodnie z `turn_order`.

Każda kolejna tura ponownie zeruje zatrzymania i zaczyna się obowiązkowym rzutem wszystkimi pięcioma kośćmi. Zatrzymania nigdy nie przechodzą pomiędzy uczestnikami ani turami.

Kolejność przy stole jest przechowywana jako pozycja. Może być ustawiona przez organizatora; domyślne sortowanie alfabetyczne nie jest regułą domenową.

### 4.10. Widoczność w trakcie i po turnieju

Podczas aktywnej rozgrywki uczestnicy danego stołu widzą wspólny formularz wyników, aktualną kolejkę oraz dostępne i zajęte kategorie wszystkich osób przy tym stole. Edytowalna jest wyłącznie komórka aktualnej tury należąca do zalogowanego uczestnika; pozostałe komórki są tylko do odczytu.

Obowiązuje zasada zera podpowiedzi. System nie wskazuje najlepszej kategorii, nie proponuje kości do zatrzymania, nie pokazuje prawdopodobieństw ani przewidywanych punktów przed podjęciem decyzji. Formularz informuje jedynie, które pozycje są jeszcze dostępne, a które zostały już wykorzystane. Szczegółowej historii rzutów nie można otworzyć podczas trwania turnieju.

Po zakończeniu etapu uczestnicy tracą dostęp do wspólnego formularza tego etapu. Do chwili zakończenia całego turnieju nie mogą otworzyć historii rzutów — także własnej. Formularz nie jest jednak usuwany: dla organizatora przechodzi w nieedytowalny widok historyczny powiązany z osią zdarzeń, aby można było wyjaśnić nieprawidłowości.

Po zakończeniu turnieju:

- uczestnik może przeglądać wyłącznie własne rzuty, zatrzymania, decyzje i wyniki;
- organizator może przeglądać pełną historię wszystkich uczestników swojego turnieju oraz odtworzyć stan wspólnego formularza krok po kroku;
- uczestnik nie otrzymuje historii rzutów innych osób;
- dostęp do porównań jest ograniczony do turniejów ze statusem `COMPLETED` lub `ARCHIVED`.

---

## 5. Rozstrzygnięcia pytań projektowych

### 5.1. Przebieg turnieju

| Pytanie | Decyzja |
| --- | --- |
| Czy kolejne rundy eliminują uczestników? | W fazie grupowej nie. Wyniki są sumowane i budują ranking. Eliminacje rozpoczynają się dopiero w fazie pucharowej; zwycięzcy ćwierćfinałów przechodzą do półfinałów itd. |
| Czy turniej działa w systemie „każdy z każdym”? | Nie. Uczestnicy są łączeni w grupy na podstawie rankingu, koszyków i ograniczeń. System ogranicza powtórne spotkania, ale nie wymaga spotkania każdej pary. |
| Czy następna runda ma czekać na wszystkie stoły, czy dopiero następny etap? | Przy obecnej zasadzie ponownego układania grup z aktualnego rankingu następna runda grupowa musi czekać na zakończenie wszystkich stołów bieżącej rundy. Czekanie wyłącznie przed następnym etapem wymagałoby ustalenia wszystkich grup z góry albo pozostawienia stałych grup, dlatego ten wariant nie został wybrany. Stoły nie czekają natomiast na siebie pomiędzy turami i działają równolegle w obrębie rundy. |
| Koszyki czy mechanizm wężykowy? | Oba elementy tworzą jeden mechanizm MVP. Ranking jest dzielony na kolejne koszyki o maksymalnej wielkości równej liczbie grup, a koszyki są rozkładane naprzemiennie wężykiem. Wewnątrz koszyka algorytm minimalizuje koszt wspólnych stołów członków tej samej drużyny i powtórnych spotkań. Losuje tylko pomiędzy równoważnymi wariantami o identycznym najlepszym koszcie. „Bezpośredni snake bez koszyków” jest tylko uproszczonym opisem tego samego bazowego rozkładu, w którym koszyki pozostają niejawne. |
| Czy zakaz spotkania członków tej samej drużyny i ponownego spotkania jest bezwzględny? | Nie, ponieważ dla części składów byłby matematycznie niewykonalny. Są to ograniczenia preferowane o wysokiej wadze. System minimalizuje naruszenia i pokazuje je organizatorowi. |
| Jak wyłania się zwycięzcę meczu pucharowego złożonego z kilku rozgrywek? | Wygrywa uczestnik z wyższą sumą surowych wyników wszystkich rozgrywek danego meczu. Remis rozstrzyga dogrywka, a losowanie jest ostatecznością. |
| Czy ranking drużynowy wpływa na awans? | Nie. Awans i rozstawienie wynikają wyłącznie z rankingu indywidualnego. Ranking drużynowy jest dodatkową klasyfikacją, której podstawową miarą porównawczą jest średnia rundowa drużyny. |
| Po co status `CANCELLED` i czy jego dane zostają na zawsze? | Status obsługuje rzadkie, ale realne zakończenie bez zwycięzcy, np. przy zbyt małej liczbie chętnych, utracie miejsca, niedostępności organizatora, poważnej awarii lub błędzie konfiguracji. Pełne dane są dostępne przez 30 dni na audyt i spory, po czym zostają trwale usunięte. Pozostaje wyłącznie anonimowy rekord zbiorczy. Turniej nigdy nie trafia do porównań. |

### 5.2. Dane, historia i interfejs gry

| Pytanie | Decyzja |
| --- | --- |
| Czy baza zawiera tylko wyniki? | Nie. Przechowuje każdy zaakceptowany wynik rzutu, jego źródło fizyczne albo wirtualne, zatrzymania, kolejność, wybór kategorii oraz obliczone punkty. Sumy i średnie są agregatami możliwymi do ponownego wyliczenia. |
| Czy istnieje historia pojedynczej rozgrywki? | Tak. Można odtworzyć tury i rzuty uczestnika oraz wskazać, z jakich danych powstał wynik. Widoczność historii zależy od roli i statusu turnieju. |
| Kiedy uczestnik widzi historię? | W trakcie rozgrywki widzi wspólny formularz i bieżący stan, ale nie szczegółową historię rzutów. Po zakończeniu turnieju widzi wyłącznie własną historię. Nigdy nie otrzymuje szczegółowej historii innych uczestników. Organizator widzi historię nadzorowanego turnieju. |
| Co dzieje się z formularzem po zakończeniu etapu? | Przestaje być dostępny uczestnikom jako wspólny formularz, ale nie znika z systemu. Dla organizatora staje się nieedytowalnym widokiem historycznym. Organizator może wybrać rundę, stół i rozgrywkę, zobaczyć końcowy formularz oraz odtworzyć jego zmiany krok po kroku. Dostęp pozostaje także po zakończeniu turnieju. Do zakończenia całego turnieju uczestnik nie może otworzyć ani cudzej, ani własnej historii rzutów. |
| Czy system podpowiada decyzję? | Nie. Pokazuje jedynie dostępność pól wynikającą ze wspólnego formularza. Nie rekomenduje kategorii lub zatrzymań, nie pokazuje prawdopodobieństw ani prognozowanej punktacji przed wyborem. |
| Czy wybór kategorii wymaga dodatkowego zatwierdzenia? | Nie. Kliknięcie dozwolonej kategorii we własnej turze jest jednoznaczną decyzją i natychmiast kończy turę. Backend zabezpiecza operację przed powtórzeniem. |
| Gdzie znajduje się formularz punktacji? | Na ekranie desktopowym stół i kości znajdują się po lewej, a wspólny formularz punktacji po prawej. Na wąskim ekranie formularz przechodzi pod stół, aby zachować czytelność i obsługę dotykową. |
| Czy przycisk „Rzuć” znika, czy jest wyszarzony? | Nie znika. Pozostaje w stałym miejscu i jest nieaktywny poza własną turą, po trzecim rzucie, po wyborze kategorii oraz podczas obsługi żądania. Etykieta zmienia się z „Rzuć” na „Rzuć ponownie” po pierwszym legalnym rzucie. |
| Czy obowiązuje limit czasu decyzji? | Domyślnie nie. Organizator może przed startem wybrać 30, 60 albo 90 sekund. Upływ czasu wywołuje alert dla organizatora, ale nie automatyzuje wyboru kategorii i nie pozwala przejść do następnej osoby bez ważnej decyzji. |
| Czy punkty można wpisać ręcznie? | Nie. Uczestnik wybiera kategorię, a wynik, sumy oraz dodatnie i ujemne składniki punktacji gry są polami tylko do odczytu wyliczanymi przez backend. Nie jest to system sankcji nakładanych przez organizatora. |
| Czy wszystkie dane mają być append-only? | Nie. Niezmienne pozostają zaakceptowane rzuty i zdarzenia audytowe, dopóki turniej podlega zwykłemu cyklowi życia lub okresowi retencji. Rankingi oraz inne agregaty mogą być aktualizowane lub odbudowywane. Korekta nie usuwa starego śladu, lecz tworzy jawne zdarzenie korygujące. Kontrolowany purge anulowanego turnieju po retencji jest usunięciem całego wygasłego zbioru, a nie edycją pojedynczego zdarzenia. |

### 5.3. Konta, role i dostęp

| Pytanie | Decyzja |
| --- | --- |
| Czy `User` oznacza organizatora? | Nie. `User` jest kontem systemowym. Organizatorem staje się przez `TournamentOrganizer`, a uczestnikiem przez profil zawodnika i `TournamentParticipant`. |
| Czy potrzebna jest rola sędziego? | Nie. Turniej może mieć kilku organizatorów realizujących nadzór, a fizyczny wynik wprowadza aktywny uczestnik pod kontrolą pozostałych osób przy stole. |
| Czy uczestnik może sam zapisać się do turnieju? | Tak, gdy organizator wybierze tryb `OPEN`. Zapis wymaga zalogowania i profilu zawodnika oraz jest możliwy tylko podczas `REGISTRATION`, przed terminem, przed ręcznym zamknięciem zapisów i przy wolnym miejscu. W trybie `ORGANIZER_ONLY` uczestników dodaje organizator. |
| Czy uczestnik może sam opuścić turniej? | Tak, ale tylko przed startem. Rekord udziału otrzymuje status `WITHDRAWN` zamiast zostać usunięty. Po rozpoczęciu turnieju wycofanie wykonuje organizator z obowiązkowym powodem i wpisem audytowym. |
| Kto może zmienić hasło po zalogowaniu? | Każdy uwierzytelniony użytkownik, niezależnie od roli w turnieju. |
| Jak użytkownik odzyskuje zapomniane hasło? | W MVP przez jednorazowy, wygasający link wysłany e-mailem. Passkeys/WebAuthn wchodzą do V2 jako dodatkowy sposób logowania. SMS nie znajduje się w roadmapie i może zostać rozważony wyłącznie po pojawieniu się konkretnej potrzeby biznesowej. Aplikacja jest sieciowa; pełny reset e-mail nie działa w trybie offline. |
| JWT czy sesje Django? | Projekt wykorzystuje JWT, aby zapewnić spójne uwierzytelnianie DRF, klienta webowego i połączeń czasu rzeczywistego. Nie pozostaje to wariantem „do potwierdzenia”. |
| Jak długo żyje access token? | 15 minut. Nie oznacza to 15-minutowej sesji: klient odnawia token automatycznie krótko przed wygaśnięciem albo jednokrotnie po odpowiedzi `401`. |
| Jak długo żyje refresh token? | Maksymalnie 8 godzin od zalogowania, z dodatkowym wygaśnięciem sesji po 30 minutach rzeczywistej bezczynności. Przy każdym użyciu następuje rotacja, a poprzedni token trafia na blacklistę. Rotacja nie przesuwa pierwotnej ośmiogodzinnej granicy. Po jej osiągnięciu wymagane jest ponowne logowanie. |
| Gdzie przechowywane są tokeny? | W bezpiecznych ciasteczkach `HttpOnly`, `Secure` i `SameSite`; operacje wykorzystujące ciasteczka są chronione przed CSRF. Tokenów nie przechowuje się w `localStorage`. |
| Co może zobaczyć gość? | W MVP nic poza ekranami rejestracji i logowania. W V1 może zobaczyć dedykowany, tylko do odczytu widok końcowych rezultatów turnieju `COMPLETED` lub `ARCHIVED`, ale wyłącznie gdy organizator jawnie go opublikuje. Gość nigdy nie ma dostępu do trwającego turnieju, historii rzutów, porównań, roboczych endpointów API ani dokumentacji Swagger/ReDoc/OpenAPI. |

### 5.4. Porównania, technologia i asynchroniczność

| Pytanie | Decyzja |
| --- | --- |
| Kto może porównywać wyniki uczestnika? | Porównywanie wielu turniejów jest narzędziem organizatora i administratora systemowego. Organizator może porównywać uczestnika wyłącznie w zakresie zakończonych turniejów, do których ma uprawnienia; administrator ma dostęp wynikający z funkcji administracyjnej. Uczestnik może przeglądać własną historię pojedynczego zakończonego turnieju, ale nie otrzymuje przekrojowego narzędzia porównawczego. |
| Jak wygląda porównanie wielu turniejów? | Maksymalnie cztery turnieje na jednej stronie: tabela zbiorcza, układ szczegółów 2 × 2 i jeden współdzielony modal do historii rozgrywki. Nie otwiera się wielu kart ani wielu nakładających się modali. |
| Czy porównujemy drużyny? | Tak, ale w V2. Porównanie wykorzystuje trwałą tożsamość `Team` i historyczny `TournamentTeam`. Podstawową miarą jest średnia rundowa drużyny; uzupełniają ją średni dorobek punktowy na członka zatwierdzonego składu, suma, historyczna liczebność i skład z konkretnego turnieju. |
| Czy można porównać trwający turniej? | Nigdy. Frontend nie pokazuje takiej możliwości, a backend odrzuca identyfikator turnieju innego niż `COMPLETED` lub `ARCHIVED`. |
| Gdzie występuje element asynchroniczny? | Stoły prowadzą rozgrywki równolegle, a ich stan i panel organizatora aktualizują się bez przeładowania strony. Następna runda lub etap jest jednak otwierany dopiero po spełnieniu warunków kompletności. |
| Czy WebSocket należy do MVP? | Tak, lecz jako jeden ograniczony pionowy przekrój: aktualizacja stanu stołu i zbiorczego panelu organizatora przez Django Channels. Pełny rejestr przyjętych i odrzuconych akcji, alarmy inicjowane przez organizatora oraz obieg wyjaśnień pozostają w V1. |
| Redis, Celery i Nginx? | Redis obsługuje Channel Layer i broker Celery. Dwie kolejki, dwóch workerów oraz Celery Beat realizują wymagania kursowe bez przenoszenia do kolejki operacji rozgrywki. Nginx pozostaje opcją wdrożenia produkcyjnego, a nie częścią logiki domenowej. |
| Pygame czy zwykły frontend webowy? | MVP wykorzystuje HTML/CSS/JavaScript oraz Canvas. W V2 może powstać osobny klient Pygame korzystający z tego samego API i WebSocketów. Backend zawsze kontroluje kolejkę i punktację, a losuje kości w turnieju zdalnym. |
| Czy akcje organizatora wymagają ręcznego zatwierdzania każdej tury? | Nie. Uczestnik wykonuje dozwolone akcje samodzielnie, backend pilnuje reguł, a organizator obserwuje zdarzenia i może wszcząć oznaczoną w audycie procedurę wyjaśniającą. |
| Django Templates czy SPA? | MVP wykorzystuje Django Templates oraz niewielki JavaScript lub HTMX, a WebSocket obsługuje stan czasu rzeczywistego. SPA i klient desktopowy nie wchodzą do MVP. |
| Czy listy używają infinite scrolla? | Nie. Widoki aktualizują się i doładowują fragmentami bez pełnego przeładowania strony, ale kolejną porcję danych pobiera świadoma akcja użytkownika, np. „Załaduj więcej”, zmiana filtra albo rozwinięcie turnieju. System nie pobiera automatycznie niekończącej się treści po samym przewijaniu. |
| Czy aplikacja ma działać offline? | Nie jako aplikacja `offline-first` i nie z przeglądarką jako lokalnym źródłem prawdy. Turniej może działać bez dostępu do publicznego Internetu, jeżeli urządzenia mają dostęp przez sieć lokalną do serwera Django; JWT i WebSocket działają wtedy w LAN. Reset hasła przez e-mail wymaga jednak działającej wysyłki poczty i podczas całkowicie odizolowanej pracy pozostaje niedostępny. Po krótkiej utracie połączenia klient synchronizuje stan z backendem. |
| Czy ograniczamy model do 4–6 encji? | Nie sztucznie. Pełna historia rzutów oraz dwie fazy wymagają większego modelu logicznego. Zakres implementuje się pionowymi przekrojami, aby każda dodana encja miała działający przypadek użycia, walidację i testy. |
| Czy projekt ma wykorzystywać jak najwięcej technologii i dziesiątki endpointów? | Nie. Priorytetem są kompletne pionowe przekroje najważniejszych operacji. Cache, SPA i inne elementy są dodawane tylko z uzasadnieniem biznesowym. |
| Jaka jest zakładana skala? | Pojedynczy turniej obsługuje maksymalnie 128 aktywnych uczestników oraz jego organizatorów. Baza może przechowywać więcej kont i zakończonych turniejów, ale MVP nie deklaruje identycznego działania dla milionów ani miliardów jednoczesnych użytkowników. |

### 5.5. Technologie użyte i świadomie pominięte

| Temat z notatek | Decyzja dla projektu |
| --- | --- |
| Djoser, SimpleJWT i drf-spectacular | Tak. Djoser obsługuje typowe operacje konta, SimpleJWT tokeny, a drf-spectacular kontrakt OpenAPI. Własny kod koncentruje się na domenie turnieju, permissions i bezpieczeństwie sesji. |
| Django Admin | Tak. Jest osobnym narzędziem administratora systemowego i zostaje skonfigurowany, a nie tylko włączony. Nie zastępuje panelu organizatora. |
| Django Channels i Redis | Tak, ale tylko dla aktualizacji stołów oraz nadzoru w czasie rzeczywistym. Stan rozgrywki nadal zapisuje PostgreSQL. |
| Cache | Nie w aktywnej rozgrywce. Po pomiarze można cache'ować wyłącznie bezpieczne, rzadko zmienne podsumowania zakończonych turniejów z jawnym unieważnianiem. |
| Celery | Należy do wymagań kursowych: projekt obejmuje co najmniej dwóch workerów z osobnymi kolejkami oraz Celery Beat. Celery obsługuje wyłącznie zadania poza krytyczną ścieżką rozgrywki. |
| GraphQL | Nie. Ograniczone, stabilne REST API oraz osobne serializery listy i szczegółu rozwiązują problem nadmiarowych danych przy mniejszej złożoności. |
| LLM lub agent AI | Nie. Losowanie, punktacja i wykrywanie dozwolonych akcji muszą być deterministyczne, testowalne i wyjaśnialne. Model językowy nie bierze udziału w przebiegu turnieju. |
| `offline-first`, lokalna baza i synchronizacja konfliktów | Nie. Równoległe stoły wymagają jednego serwera będącego źródłem prawdy. LAN bez publicznego Internetu jest dozwolony, ale nie oznacza niezależnej pracy klientów. |
| SPA | Nie w MVP. Django Templates, HTMX lub mały JavaScript zapewniają wymagane dynamiczne fragmenty bez tworzenia drugiej rozbudowanej aplikacji. |

---

## 6. User stories

User stories celowo poprzedzają model danych. Modele mają wynikać z zachowania systemu, a nie odwrotnie.

Historie opisują cały zaprojektowany produkt; ich kolejność wdrażania i granicę MVP określa sekcja 8. Obecność historii dla wersji 1.0 lub V2 nie oznacza, że odpowiadający jej model ma powstać w pierwszej migracji.

### 6.1. Każdy zalogowany użytkownik

- Jako zalogowany użytkownik chcę zmienić własne hasło, aby móc zabezpieczyć konto bez względu na rolę w turnieju.
- Jako użytkownik, który zapomniał hasła, chcę otrzymać wiadomość z bezpiecznym linkiem resetującym, aby odzyskać dostęp do konta.
- Jako zalogowany użytkownik chcę wylogować się ze wszystkich lub wybranych sesji, aby ograniczyć skutki utraty urządzenia.

### 6.2. Organizator

- Jako organizator chcę utworzyć turniej i ustalić jego reguły przed startem, aby wszyscy grali według tej samej konfiguracji.
- Jako organizator chcę wybrać zapisy zarządzane albo otwarte, ustalić limit i termin oraz móc zamknąć zapisy wcześniej.
- Jako organizator chcę przypisywać uczestników do turnieju, aby jedna osoba mogła brać udział w wielu turniejach bez duplikowania profilu.
- Jako organizator chcę anulować turniej z podaniem powodu, aby wyjątkowe zakończenie bez zwycięzcy zachowało dane na czas wyjaśnienia zamiast usuwać je natychmiast.
- Jako organizator chcę tworzyć drużyny i przypisywać do nich uczestników, aby prowadzić dodatkową klasyfikację drużynową.
- Jako organizator chcę wygenerować możliwie równe grupy, aby ograniczyć ręczne układanie stołów.
- Jako organizator chcę widzieć wszystkie stoły lub jeden wybrany stół, aby nadzorować równoległe rozgrywki.
- Jako organizator chcę widzieć aktualną turę i każdą akcję uczestnika, aby móc wykryć próbę obejścia zasad.
- Jako organizator chcę oznaczyć podejrzaną akcję i rozpocząć procedurę wyjaśniającą, aby nie zmieniać wyniku bez śladu.
- Jako organizator chcę automatycznie przeliczać ranking po zamknięciu rundy, aby szybko przygotować kolejne grupy.
- Jako organizator chcę automatycznie utworzyć drabinkę z końcowego rankingu fazy grupowej, aby prawidłowo rozstawić uczestników.
- Jako organizator chcę zakończyć i zablokować turniej, aby jego rezultaty mogły bezpiecznie trafić do historii.
- Jako organizator chcę otworzyć pełną historię rozgrywki dowolnego uczestnika, aby zweryfikować wynik lub rozstrzygnąć spór.
- Jako organizator chcę odtworzyć zakończoną rozgrywkę krok po kroku w nieedytowalnym formularzu, aby zobaczyć kolejność rzutów, zatrzymań i wyborów kategorii.
- Jako organizator chcę porównać wyniki jednej osoby pomiędzy kilkoma zakończonymi turniejami, aby ocenić zmianę jej rezultatów.
- Jako organizator chcę docelowo porównywać drużyny pomiędzy zakończonymi turniejami, aby analizować wyniki zespołów mimo różnej liczebności składów.

### 6.3. Uczestnik

- Jako zalogowany uczestnik chcę zobaczyć turnieje z otwartymi zapisami i liczbę wolnych miejsc bez ujawniania pełnej listy zawodników.
- Jako uczestnik chcę samodzielnie dołączyć do otwartego turnieju, jeżeli zapisy trwają i pozostało miejsce.
- Jako uczestnik chcę wycofać własne zgłoszenie przed startem oraz móc ponownie dołączyć, jeżeli zapisy nadal są otwarte.
- Jako uczestnik chcę widzieć, kiedy przypada moja tura, aby nie wykonać akcji poza kolejnością.
- Jako uczestnik chcę rzucać kośćmi i wybierać kości do zatrzymania, aby realizować strategię gry.
- Jako uczestnik chcę wybrać kategorię wyniku, a nie wpisywać liczbę punktów, aby punktacja była wyliczana jednoznacznie.
- Jako uczestnik chcę widzieć wspólny formularz bieżącej rozgrywki, aby znać stan gry przy stole.
- Jako uczestnik chcę widzieć swój ranking, gdy regulamin turnieju na to pozwala, aby śledzić postęp.
- Jako uczestnik chcę po zakończeniu turnieju przejrzeć własną historię rzutów, aby przeanalizować swoje decyzje.

### 6.4. System

- Jako system chcę odrzucać rzut wykonany poza kolejnością, aby zachować integralność rozgrywki.
- Jako system chcę uniemożliwić zmianę reguł po rozpoczęciu turnieju, aby wynik był porównywalny i audytowalny.
- Jako system chcę dopuścić wybór tylko niewykorzystanej kategorii, aby formularz wyniku pozostał poprawny.
- Jako system chcę blokować przejście do kolejnej tury bez decyzji po ostatnim rzucie, aby nie powstał niekompletny wynik.
- Jako system chcę udostępniać porównania tylko dla zakończonych turniejów, aby analityka nie dawała przewagi w trwającej rywalizacji.
- Jako system chcę otworzyć następną rundę dopiero po zamknięciu wszystkich wymaganych rozgrywek, aby ranking i awanse były kompletne.
- Jako system chcę transakcyjnie przydzielić ostatnie wolne miejsce tylko jednej osobie, aby równoległe zapisy nie przekroczyły limitu.
- Jako system chcę po upływie retencji trwale usunąć szczegółowe dane anulowanego turnieju i pozostawić wyłącznie anonimowy rekord zbiorczy, aby ograniczyć ryzyko oraz rozmiar bazy.

### 6.5. Administrator systemowy

- Jako administrator chcę wyszukiwać i filtrować turnieje, konta i rozgrywki w Django Admin, aby diagnozować problemy bez otwierania każdego rekordu.
- Jako administrator chcę widzieć pola źródłowe zakończonej rozgrywki jako tylko do odczytu, aby nie zmienić historii przez przypadkową edycję.
- Jako administrator chcę wykonywać wyjątkowe operacje przez te same serwisy domenowe co API, aby panel administracyjny nie omijał walidacji i audytu.
- Jako administrator wersji 1.0 chcę czasowo wstrzymać purge tylko dla udokumentowanego sporu, aby zachować dowody bez bezterminowego przechowywania danych.

---

## 7. Widoki i przepływy użytkownika

Widoki są rozwijane iteracyjnie. Opisy oznaczone jako wersja 1.0 lub V2 nie blokują prostszego, kompletnego interfejsu MVP.

### 7.1. Panel główny

- Domyślnie pokazuje aktywne turnieje.
- Zalogowany użytkownik ma osobną sekcję „Otwarte zapisy”, zawierającą wyłącznie turnieje `REGISTRATION` w trybie `OPEN`, których termin nie minął i które nie zostały ręcznie zamknięte.
- Karta otwartego turnieju pokazuje nazwę, termin, skrót zasad, limit, zajęte i wolne miejsca oraz przycisk „Dołącz”. Nie pokazuje pełnej listy uczestników przed dołączeniem.
- Uczestnik zapisany przed startem widzi akcję „Zrezygnuj”; po rezygnacji może ponownie dołączyć, jeżeli warunki zapisów nadal są spełnione.
- Po zmianie statusu na `COMPLETED` turniej znika z listy aktywnych i trafia do osobnej sekcji ostatnio zakończonych; ta lista jest sortowana malejąco według czasu zakończenia, więc najnowszy turniej znajduje się na górze.
- Od wersji 1.0 turniej `CANCELLED` jest wyraźnie oznaczony jako anulowany i nie trafia do listy zakończonych wyników ani porównań. Uprawniony organizator może otworzyć zachowane dane i powód anulowania wyłącznie przed upływem terminu retencji albo podczas audytowanej blokady związanej z nierozstrzygniętym sporem.
- Zarówno na liście aktywnej, jak i zakończonej kafel lub wiersz turnieju pokazuje najpierw wyłącznie dane skrócone: nazwę, status, organizatorów i uczestników. Nie rozwija od razu rund ani wyników.
- Kliknięcie turnieju rozwija jego rundy, a kliknięcie rundy dopiero jej szczegóły. Interfejs działa jak akordeon: na każdym poziomie domyślnie otwarty jest najwyżej jeden element, aby użytkownik widział jedną rzecz naraz.
- Rozwinięcie elementu doładowuje przez HTMX lub JavaScript tylko potrzebny fragment. Ukryte rundy, wyniki i historie rzutów nie są pobierane z wyprzedzeniem; każde żądanie szczegółów ponownie przechodzi kontrolę uprawnień po stronie backendu.
- Widok zakończonych turniejów początkowo pokazuje ograniczoną porcję najnowszych rekordów. Pełne archiwum otrzymuje filtrowanie i paginację po stronie serwera, prezentowaną jako jawna akcja „Załaduj więcej” albo przejście do następnej strony.
- Kolejna porcja może zostać dołączona do bieżącego widoku bez jego przeładowania, lecz aplikacja nie uruchamia automatycznego infinite scrolla. Użytkownik widzi liczbę wyświetlonych i dostępnych rekordów, może zatrzymać przeglądanie oraz zawsze zachowuje dostęp do filtrów i stopki.
- Zdarzenia WebSocket aktualizują wyłącznie stan trwających turniejów i stołów. Nie służą do samoczynnego podawania kolejnych rekordów archiwum.

### 7.2. Widok stołu

- na ekranie desktopowym stół i kości znajdują się po lewej, a wspólny formularz punktacji po prawej;
- na wąskim ekranie formularz przechodzi pod stół zamiast zmniejszać obszar kości;
- w pobliżu obszaru rzutu znajduje się wyraźnie wydzielona strefa „Zatrzymane kości”; jej położenie dostosowuje się do szerokości ekranu. Kliknięcie myszą albo dotknięcie kości wysyła zmianę zatrzymania do backendu, a interfejs automatycznie przenosi kość do tej strefy lub z powrotem;
- we wspólnym formularzu edytowalna jest wyłącznie własna komórka podczas aktywnej tury; pola pozostałych uczestników są tylko do odczytu;
- zapisany wynik, liczba pozostałych rzutów oraz punkty obliczone po dokonanym wyborze są tylko do odczytu;
- bieżące wartości kości, suma oczek, liczba pozostałych przerzutów i całkowity wynik uczestnika są wyliczane przez system i nigdy nie są ręcznie edytowane;
- interfejs nie podpowiada kategorii, kości do zatrzymania, prawdopodobieństwa ani prognozowanego wyniku;
- przycisk „Rzuć” pozostaje w stałym miejscu; gdy akcja jest niedozwolona,
  pozostaje widoczny w stanie nieaktywnym;
- wybranie kategorii wysyła do backendu ostateczną komendę i po jej przyjęciu kończy turę bez dodatkowego przycisku „Zapisz” lub „Potwierdź”;
- organizator nie zatwierdza każdej tury; nadzoruje zdarzenia i reaguje wyłącznie na nieprawidłowości;
- po trzecim rzucie pozostaje wyłącznie wybór kategorii.

### 7.3. Panel nadzoru organizatora

- jednoczesne porównanie wszystkich stołów w zwartej siatce obejmującej co najmniej aktualnego uczestnika, numer tury, ostatnią akcję, stan rozgrywki i alerty;
- możliwość przełączenia tego samego panelu na szczegółowy widok jednego stołu bez otwierania nowej karty przeglądarki;
- aktualizacja tur, rzutów, decyzji i statusów w czasie zbliżonym do rzeczywistego;

MVP kończy się na powyższym monitoringu aktualnego stanu i ostatniej zaakceptowanej akcji. Wersja 1.0 dodaje:

- wgląd w każdą przyjętą i odrzuconą akcję uczestników wraz ze stołem, czasem serwera i przyczyną odrzucenia;
- wyróżnienie braku aktywności, konfliktu kolejności albo podejrzanej akcji;
- możliwość oznaczenia zdarzenia jako podejrzanego i wszczęcia alarmu wymagającego wyjaśnienia, bez automatycznego uznawania uczestnika za oszusta;
- historię zdarzeń dostępną do kontroli, ale bez zwykłego nadpisywania danych źródłowych.

### 7.4. Historia pojedynczej rozgrywki

Dla uczestnika historia staje się dostępna dopiero po zakończeniu całego turnieju i obejmuje wyłącznie jego własne rozgrywki. Organizator może korzystać z pełnej historii wcześniej wyłącznie w ramach nadzoru i wyjaśniania zdarzeń.

Organizator otrzymuje również tryb „Odtwórz przebieg”. Wybiera rundę, stół i rozgrywkę, po czym może przechodzić do poprzedniego lub następnego zaakceptowanego zdarzenia. Formularz pokazuje wtedy stan kategorii, wyniki, aktualnego uczestnika, wartości kości i zatrzymania odpowiadające wybranemu krokowi. Jest to rekonstrukcja z danych domenowych, nie nagranie ekranu ani ponowne wykonanie losowania.

Od wersji 1.0 odrzucone próby pozostają widoczne na równoległej osi audytu wraz z przyczyną odmowy, ale nie zmieniają rekonstruowanego stanu formularza. Tryb historyczny jest zawsze tylko do odczytu. Ewentualna korekta wymaga osobnej, uprawnionej operacji i tworzy kolejne zdarzenie audytowe zamiast modyfikować przeszłość bez śladu.

Najpierw widoczny jest wynik skrócony: runda, kategoria i liczba punktów. Dopiero akcja „Szczegóły” rozwija:

- kolejne rzuty;
- wartości wszystkich kości;
- kości zatrzymane po każdym rzucie;
- moment wyboru kategorii;
- zastosowane premie lub kary;
- końcowy wynik tury i rozgrywki.

### 7.5. Porównywanie zakończonych turniejów

Podstawowy widok porównania wyników uczestnika wchodzi do MVP, ponieważ korzysta z już zapisanej historii i nie wymaga dodatkowego modelu. Jest to narzędzie organizatora lub administratora, a nie przekrojowa porównywarka udostępniana uczestnikowi. Porównanie działa na osobnej stronie aplikacji, a nie przez otwieranie wielu kart przeglądarki. Porównanie drużynowe pozostaje w V2.

Podstawowy przepływ:

```text
Organizator lub administrator → uczestnik → zakończone turnieje
→ runda → rozgrywka → wynik → szczegóły rzutów
```

Opcjonalny przepływ drużynowy:

```text
Drużyna → zakończone turnieje → uczestnik → runda → wynik
```

Interfejs porównania:

- jest dostępny wyłącznie organizatorowi w zakresie jego turniejów oraz administratorowi systemowemu;
- najpierw pokazuje zwartą tabelę zbiorczą, np. turniej, miejsce, suma, średnia rundowa, najlepsza runda i liczba rozegranych rund;
- pozwala wybrać maksymalnie cztery turnieje jednocześnie;
- na dużym ekranie układa szczegóły w siatce 2 × 2, a na mniejszym w zwijane sekcje;
- używa jednego, wielokrotnie wykorzystywanego modala do szczegółów wybranej rozgrywki i rzutów;
- nie otwiera osobnego modala dla każdej komórki i nie wymaga wielu kart przeglądarki;
- filtruje listę po stronie serwera do statusów `COMPLETED` i `ARCHIVED`;
- ponownie sprawdza status przy wykonaniu zapytania, więc ręczne podanie identyfikatora aktywnego turnieju kończy się odmową;
- od V2 przy porównaniu drużyn pokazuje średnią rundową drużyny jako podstawową
  miarę oraz średni dorobek punktowy na członka zatwierdzonego składu, sumę,
  historyczną liczebność i skład użyty w każdym turnieju.

Nie należy przechowywać osobnego wyniku porównania, jeśli można go obliczyć z historii. Ewentualny cache ma być unieważniany po audytowanej korekcie danych.

---

## 8. Zakres MVP

### 8.1. Funkcje MVP

MVP pozwala przeprowadzić **jeden pełny turniej grupowy z kilkoma rundami i rotacją stołów**, zakończony rankingiem z sumy wyników. Nie zawiera jeszcze fazy pucharowej.

Zakres funkcjonalny MVP:

- rejestracja konta, logowanie, odświeżanie tokenu i wylogowanie przez Djoser oraz SimpleJWT;
- zmiana hasła dla każdego zalogowanego użytkownika i reset przez e-mail w środowisku online;
- utworzenie, skonfigurowanie i rozpoczęcie turnieju przez organizatora;
- przypisanie wielu organizatorów oraz relacja M:N pomiędzy profilami zawodników i turniejami;
- tryby zapisów `ORGANIZER_ONLY` i `OPEN`, samodzielne `join`/`leave`, termin oraz transakcyjnie chroniony limit miejsc;
- kilka rund grupowych, a w każdej nowy przydział do stołów wężykiem z ograniczaniem ponownych spotkań i wspólnego stołu osób z tym samym oznaczeniem drużyny;
- równoległe działanie stołów w ramach rundy oraz bariera przed wygenerowaniem następnej rundy;
- prowadzenie tury: maksymalnie trzy zaakceptowane rzuty, zatrzymywanie kości
  i obowiązkowy wybór kategorii;
- punktacja i kolejka wyliczane wyłącznie przez backend;
- źródłowa historia rzutów pozwalająca odtworzyć wynik;
- ranking końcowy turnieju grupowego wraz z tie-breakami;
- podstawowy panel organizatora i jeden ograniczony przekrój WebSocket aktualizujący stany stołów;
- zakończenie turnieju, własna historia uczestnika po zakończeniu oraz replay tylko do odczytu dla organizatora;
- porównanie jednego uczestnika pomiędzy maksymalnie czterema zakończonymi turniejami, dostępne wyłącznie właściwemu organizatorowi lub administratorowi;
- skonfigurowany Django Admin, OpenAPI/Swagger, wersjonowana kolekcja Postmana lub pliki `.http`;
- testy najważniejszej logiki, permissions, API i konfliktów współbieżnych;
- Docker Compose z Django, PostgreSQL, Redis, wymaganymi workerami Celery
  i Celery Beat oraz podstawowy pipeline CI.

Po utracie połączenia WebSocket klient synchronizuje stan przez zwykłe API. Integralność rozgrywki nie zależy od frontendu ani od dostarczenia wiadomości czasu rzeczywistego.

### 8.2. Funkcje późniejszych wersji

Wersja 1.0 rozszerza MVP o:

- osobne `Stage`, pełne grupy domenowe i faza pucharowa z drabinką;
- rozbudowany `AuditEvent`, alarmy, obieg wyjaśnień i korekty;
- pełny cykl `CANCELLED`, 30-dniowa retencja oraz automatyczny purge;
- eksporty, rozbudowane wykresy i publiczne wyniki końcowe.

V2 dodaje trwałą tożsamość drużyn, ranking drużynowy, historyczne składy i porównania drużyn pomiędzy zakończonymi turniejami.

To nie jest drugie MVP. MVP istnieje tylko jedno, natomiast powyższe elementy tworzą kolejne pionowe przekroje prowadzące do wersji 1.0 i V2. Szczegółowe zasady opisane wcześniej pozostają docelowym kontraktem produktu i nie są usuwane tylko dlatego, że ich implementacja nastąpi później.

---

## 9. Model domenowy

Poniższy model opisuje docelowy produkt, a nie listę tabel tworzonych jednocześnie. MVP korzysta z dziewięciu własnych modeli domenowych oraz wbudowanego `User`. Każdy model obsługuje konkretny przepływ: relację M:N, równoległe stoły albo źródłową historię rzutów. Dalsze encje powstają dopiero wraz z kolejnym przypadkiem użycia.

Modele są pogrupowane według odpowiedzialności. `Tournament`, uczestnictwo,
etapy, rundy, grupy, mecze i klasyfikacja należą do domeny turniejowej. `Game`,
`GameParticipant`, `Turn`, `Roll` oraz wpisy formularza należą do domeny gry
kościanej. Powiązanie `Game` z przydziałem stołu jest granicą integracyjną:
turniej uruchamia grę dla wskazanego składu, a następnie odbiera zatwierdzony
rezultat bez przejmowania reguł kości i punktacji.

| Zakres | Modele |
| --- | --- |
| Wbudowany mechanizm Django | `User` |
| MVP | `PlayerProfile`, `Tournament`, `TournamentOrganizer`, `TournamentParticipant`, `Round`, `Game`, `GameParticipant`, `Turn`, `Roll` |
| Wersja 1.0 | `TournamentRuleSet`, `Stage`, `Group`, `GroupParticipant`, `Match`, `AuditEvent`, `TournamentCancellationSummary` |
| V2 | `Team`, `TournamentTeam` oraz trwałe członkostwa potrzebne do porównań drużynowych |

W MVP `Round` należy bezpośrednio do `Tournament`, a `Game` pełni rolę stołu w danej rundzie. Wersja 1.0 dodaje osobne etapy, grupy i mecze dopiero wtedy, gdy pojawia się faza pucharowa. Dzięki temu pierwszy schemat pozostaje mały, ale nie zamyka drogi do pełnego modelu opisanego poniżej.

### 9.1. `User`

Konto systemowe oparte na mechanizmie użytkowników Django. Zawiera dane uwierzytelniające, ale nie ma globalnego pola roli turniejowej.

Najważniejsze dane:

- `id`;
- `username` albo adres e-mail używany do logowania;
- `email`;
- hash hasła zarządzany przez Django;
- `is_active`;
- `created_at`.

### 9.2. `PlayerProfile`

Profil zawodnika powiązany 1:1 z kontem użytkownika. Przechowuje dane prezentacyjne wspólne dla udziałów w różnych turniejach.

- `id`;
- `user_id`;
- `display_name`;
- `nickname`;
- `created_at`.

### 9.3. `Tournament`

- `id`;
- `name`;
- `status` jako `TextChoices`: w MVP `DRAFT`, `REGISTRATION`, `ACTIVE`, `COMPLETED`; od wersji 1.0 także `ARCHIVED` i `CANCELLED`;
- `registration_mode` jako `TextChoices`: `ORGANIZER_ONLY`, `OPEN`;
- `min_participants` i `max_participants`, przy czym `max_participants` nie może przekroczyć 128;
- `registration_deadline`, opcjonalnie;
- `registration_closed_at`, opcjonalnie;
- `starts_at`;
- `completed_at`;
- od wersji 1.0: `cancelled_at` i `cancelled_by`, tylko dla `CANCELLED`;
- od wersji 1.0: `cancellation_reason_code` jako `TextChoices`: `INSUFFICIENT_PARTICIPANTS`, `VENUE_UNAVAILABLE`, `ORGANIZER_UNAVAILABLE`, `TECHNICAL_FAILURE`, `INVALID_CONFIGURATION`, `SAFETY`, `OTHER`, oraz opcjonalne `cancellation_details`;
- od wersji 1.0: `retention_until`, tylko dla `CANCELLED`;
- od wersji 1.0: `retention_hold_until` i `retention_hold_reason`, opcjonalnie;
- `created_at`;
- w MVP: jawne pola podstawowej konfiguracji, m.in. liczba rund, liczebność stołu, wariant punktacji i limit czasu;
- w MVP: niezmienny po rozpoczęciu tryb wydarzenia — stacjonarny albo zdalny;
- od wersji 1.0: `rule_set_id` wskazujące niezmienny snapshot rozbudowanych zasad.

Relacje M:N:

```python
participants = ManyToManyField(
    PlayerProfile,
    through="TournamentParticipant",
)

organizers = ManyToManyField(
    User,
    through="TournamentOrganizer",
)
```

### 9.4. `TournamentRuleSet`

Model wersji 1.0. Niezmienna po rozpoczęciu konfiguracja zasad:

- liczba rund grupowych;
- preferowana liczebność grup;
- liczba awansujących;
- liczba rozgrywek w meczu;
- wariant pokerów;
- limit czasu decyzji;
- wersja silnika punktacji;
- pozostałe parametry reguł.

### 9.5. `TournamentOrganizer`

Encja pośrednia pomiędzy `Tournament` i `User`.

- `tournament_id`;
- `user_id`;
- zakres uprawnień;
- `assigned_at`.

Unikalność: jedna para użytkownik–turniej może wystąpić tylko raz.

### 9.6. `TournamentParticipant`

Encja pośrednia realizująca wymaganą relację M:N pomiędzy zawodnikami i turniejami.

- `id`;
- `tournament_id`;
- `player_profile_id`;
- w MVP opcjonalne, turniejowe `team_label` wykorzystywane wyłącznie do ograniczania wspólnych stołów;
- od V2 `tournament_team_id`, jeśli wdrożono trwałe drużyny i historyczne składy;
- numer startowy;
- status udziału jako `TextChoices`: `REGISTERED`, `ACTIVE`, `WITHDRAWN`, `ELIMINATED`;
- `joined_at`;
- `withdrawn_at`, `withdrawn_by` i `withdrawal_reason`, opcjonalnie;
- pozycja startowa lub rozstawienie;
- pomocniczy łączny wynik.

Unikalność: jeden profil zawodnika może wystąpić w danym turnieju tylko raz.

Ponowne dołączenie nie tworzy drugiego rekordu. Serwis zmienia istniejący status `WITHDRAWN` z powrotem na `REGISTERED`, aktualizuje czas dołączenia i ponownie sprawdza dostępność miejsca.

### 9.7. `Team` i `TournamentTeam`

Modele V2. `Team` nadaje drużynie trwałą tożsamość, a `TournamentTeam` opisuje
jej udział, nazwę prezentacyjną i zatwierdzony skład w konkretnym turnieju.
Późniejsze wycofanie, zakończenie udziału lub dyskwalifikacja nie usuwa
historycznego członkostwa i nie zmniejsza liczebności migawki. Osobno wyliczana
jest liczba osób nadal grających. Wyniki uzyskane przed zakończeniem udziału
pozostają w historii i statystykach, natomiast za nierozgrywane późniejsze rundy
nie dopisuje się zer. MVP nie tworzy trwałej encji wyłącznie na potrzeby
grupowania.

### 9.8. `Stage`

Model wersji 1.0, potrzebny po dodaniu fazy pucharowej.

- `tournament_id`;
- typ: `GROUP` albo `KNOCKOUT`;
- kolejność;
- status jako `TextChoices`: `WAITING`, `ACTIVE`, `COMPLETED`, `CANCELLED`;
- czas rozpoczęcia i zakończenia.

### 9.9. `Round`

- w MVP `tournament_id` i typ `GROUP`;
- od wersji 1.0 `stage_id` zamiast bezpośredniego powiązania;
- numer i nazwa, np. „Runda grupowa 2” albo „Ćwierćfinał”;
- status jako `TextChoices`: `WAITING`, `ACTIVE`, `COMPLETED`, `CANCELLED`;
- czas rozpoczęcia i zakończenia.

### 9.10. `Group` i `GroupParticipant`

Modele wersji 1.0. `Group` reprezentuje formalny przydział w rundzie grupowej, a `GroupParticipant` przypisuje uczestnika do grupy i przechowuje jego kolejność przy stole. W MVP tę samą rolę techniczną pełnią `Game` oraz `GameParticipant`, co usuwa dwie tabele z pierwszego schematu.

### 9.11. `Match`

Model wersji 1.0. Węzeł drabinki pucharowej:

- `round_id`;
- dwóch uczestników;
- zwycięzca;
- status;
- odwołanie do następnego meczu i pozycji w nim;
- sposób rozstrzygnięcia remisu.

### 9.12. `Game`

Pojedyncza pełna rozgrywka przy stole. W MVP należy bezpośrednio do rundy i ma numer stołu. W wersji 1.0 należy do grupy albo meczu; reguła spójności wymaga wtedy dokładnie jednego z tych powiązań.

### 9.13. `GameParticipant`

Łączy rozgrywkę z uczestnikiem turnieju i zawiera:

- kolejność tur;
- status ukończenia formularza;
- pomocniczy surowy wynik;
- dodatnie i ujemne składniki punktacji gry;
- końcowy wynik rozgrywki.

### 9.14. `Turn`

Jedna tura uczestnika zakończona wyborem kategorii:

- `game_participant_id`;
- numer tury;
- wybrana kategoria;
- punkty wyliczone przez silnik;
- znacznik zakończenia.

### 9.15. `Roll`

Źródłowy zapis pojedynczego rzutu:

- `turn_id`;
- numer rzutu od 1 do 3;
- pięć wartości kości;
- stan zatrzymania kości po rzucie;
- czas wykonania;
- identyfikator żądania zapewniający idempotencję.

Każdy `Roll` zapisuje pełną migawkę wszystkich pięciu kości po danym rzucie. Przy drugim i trzecim rzucie wartości kości zatrzymanych pozostają w migawce bez zmian, a nowe wartości otrzymują wyłącznie pozycje niezatrzymane. Dzięki temu replay nie musi odtwarzać stanu z domysłów ani z samej sumy oczek.

Wartości można przechowywać w walidowanym polu tablicowym albo JSON, jeśli baza i wymagania projektu to uzasadniają. Nie wolno przechowywać wyłącznie sumy oczek.

### 9.16. `AuditEvent`

Model wersji 1.0. Rejestruje istotne zdarzenia, np. rzut, zmianę zatrzymanych kości, wybór kategorii, korektę, alarm organizatora, odrzuconą akcję lub zmianę statusu. Zdarzenie zawiera co najmniej uczestnika, turniej, stół lub rozgrywkę, typ akcji, czas serwera, wynik walidacji, bezpieczny opis przyczyny odrzucenia oraz jednoznaczny numer kolejny w strumieniu zdarzeń rozgrywki. Ograniczenie unikalności `(game_id, sequence_number)` pozwala odtworzyć kolejność także wtedy, gdy kilka zdarzeń ma ten sam znacznik czasu.

Organizator może oznaczyć zdarzenie jako podejrzane i utworzyć alarm z komentarzem oraz statusem wyjaśnienia. Alarm nie zmienia automatycznie wyniku i nie stanowi samodzielnego dowodu oszustwa.

`AuditEvent` nie jest ogólnym rejestrem każdej zmiany każdego modelu. W wersji 1.0 obejmuje wyłącznie działania potrzebne do integralności gry, panelu organizatora, alarmów i odtworzenia przebiegu. Dzięki temu pozostaje uzasadnioną funkcją domenową, a nie rozbudowaną infrastrukturą audytową tworzoną na zapas.

Nie wszystkie tabele muszą być append-only. Niezmienność jest szczególnie ważna dla zaakceptowanych rzutów i zdarzeń audytowych.

Niezmienność nie oznacza bezterminowej retencji. Dla turnieju `CANCELLED` zdarzenia pozostają nieedytowalne w okresie wyjaśniającym, a następnie cały wygasły zbiór jest usuwany przez kontrolowany mechanizm.

Append-only zwiększa zużycie przestrzeni dyskowej, a nie automatycznie pamięci operacyjnej. Rozmiar kontrolują indeksy, retencja logów technicznych i archiwizacja; źródłowych rzutów zakończonego turnieju nie należy usuwać tylko dlatego, że wynik został zagregowany.

### 9.17. Agregaty i dane źródłowe

Źródłem prawdy są rzuty, decyzje i konfiguracja reguł. Wyniki rozgrywek, sumy
rankingowe, średnia rundowa drużyny i średni dorobek punktowy na członka
zatwierdzonego składu mogą być zapisane jako wartości pomocnicze dla wydajności,
ale muszą dać się ponownie wyliczyć z właściwymi mianownikami.

Porównanie między turniejami nie wymaga osobnego modelu. Jest zapytaniem analitycznym po zakończonych danych. Model zapisanych zestawów porównawczych można dodać dopiero wtedy, gdy pojawi się potrzeba biznesowa.

### 9.18. Konwencje modeli i pól

- Mutowalne modele domenowe mają `created_at` i `updated_at`, najlepiej przez prosty abstrakcyjny model bazowy. Zdarzenia append-only, takie jak zaakceptowany rzut lub wpis audytowy, wymagają czasu utworzenia, ale nie otrzymują pozornego `updated_at`, skoro zwykła edycja jest zabroniona.
- Statusy i inne zamknięte zbiory wartości korzystają z `models.TextChoices`, a nie z dowolnych napisów.
- `unique=True` albo `UniqueConstraint` stosuje się tam, gdzie duplikat łamie regułę domenową, np. dla pary uczestnik–turniej, organizator–turniej lub numeru rzutu w turze.
- `null=True` oznacza rzeczywisty brak wartości w bazie, np. brak zwycięzcy przed końcem meczu. `blank=True` dotyczy walidacji formularza lub serializera; dla pól tekstowych nie tworzy się bez potrzeby dwóch reprezentacji braku wartości: `NULL` i pustego napisu.
- Ograniczenia, które można jednoznacznie wyrazić w bazie, otrzymują constraint. Reguły zależne od bieżącego stanu kilku encji pozostają w serwisie domenowym i są wykonywane transakcyjnie.

### 9.19. `TournamentCancellationSummary`

Model wersji 1.0. Minimalny, anonimowy rekord tworzony bezpośrednio przed trwałym usunięciem szczegółów anulowanego turnieju. Nie zawiera klucza obcego do `User`, `PlayerProfile`, `TournamentParticipant` ani surowych rzutów.

- własny identyfikator;
- techniczny identyfikator usuniętego turnieju bez relacji zwrotnej;
- `cancelled_at` i `purged_at`;
- etap osiągnięty przed anulowaniem;
- `cancellation_reason_code`, bez swobodnego opisu;
- liczba uczestników;
- liczba rozpoczętych i ukończonych rund.

Rekord służy wyłącznie do potwierdzenia wykonania cyklu retencji i podstawowych statystyk operacyjnych. Nie pozwala odtworzyć rozgrywki, ustalić tożsamości uczestników ani wykorzystać wyników w porównaniach.

Jeden taki rekord zastępuje potencjalnie tysiące powiązanych rzutów i zdarzeń, dlatego jego koszt jest pomijalny w porównaniu z anonimizowaniem oraz pozostawieniem całego grafu turnieju. Jeżeli skala systemu kiedyś będzie tego wymagać, również te rekordy można agregować i usuwać według osobnej polityki operacyjnej.

---

## 10. Najważniejsze relacje i ograniczenia

| Relacja | Kardynalność | Realizacja | Od wersji |
| --- | --- | --- | --- |
| `User` — `PlayerProfile` | 1:0 lub 1:1 | profil zawodnika | MVP |
| `PlayerProfile` — `Tournament` | M:N | `TournamentParticipant` | MVP |
| `User` — `Tournament` jako organizator | M:N | `TournamentOrganizer` | MVP |
| `Tournament` — `Round` | 1:N | bezpośrednie rundy grupowe | MVP |
| `Round` — `Game` | 1:N | równoległe stoły danej rundy | MVP |
| `Game` — `TournamentParticipant` | M:N | `GameParticipant` | MVP |
| `GameParticipant` — `Turn` | 1:N | kolejne kategorie formularza | MVP |
| `Turn` — `Roll` | 1:N, maks. 3 | pełna historia tury | MVP |
| `Tournament` — `Stage` | 1:N | etapy turnieju | 1.0 |
| `Stage` — `Round` | 1:N | rundy grupowe lub pucharowe | 1.0 |
| `Round` — `Group` | 1:N | formalne grupy fazy grupowej | 1.0 |
| `Round` — `Match` | 1:N | faza pucharowa | 1.0 |
| `Group` — `TournamentParticipant` | M:N | `GroupParticipant` | 1.0 |
| `Team` — `Tournament` | M:N | `TournamentTeam` | V2 |

Kluczowe ograniczenia bazodanowe i domenowe:

- brak duplikatu uczestnika w turnieju;
- brak duplikatu organizatora w turnieju;
- liczba uczestników ze statusem zajmującym miejsce nie może przekroczyć `max_participants`;
- samodzielny zapis wymaga `OPEN`, statusu `REGISTRATION`, otwartego terminu i wolnego miejsca;
- samodzielne wycofanie jest możliwe tylko przed `ACTIVE`;
- maksymalnie jedna drużyna uczestnika w turnieju;
- jeden uczestnik najwyżej raz w rundzie grupowej;
- jedna kategoria najwyżej raz w rozgrywce danego uczestnika;
- numer rzutu od 1 do 3 i unikalny w turze;
- dokładnie pięć wartości kości, każda od 1 do 6;
- brak akcji po zakończeniu tury, rozgrywki lub turnieju;
- brak porównań dla `DRAFT`, `REGISTRATION`, `ACTIVE` i `CANCELLED`;
- zwycięzca meczu musi być jego uczestnikiem;
- następny etap nie może ruszyć przed zakończeniem poprzedniego.

---

## 11. API i pionowe przekroje funkcjonalne

### 11.1. Podejście API-first i podział odpowiedzialności

Backend jest projektowany w podejściu DRF API-first. Interfejs webowy korzysta z tego samego kontraktu, który można przetestować niezależnie w Swaggerze, Postmanie albo pliku `.http`. Nie oznacza to budowania osobnego SPA w MVP.

Odpowiedzialności pozostają proste:

- model przechowuje dane, relacje, constraints i niewielkie reguły dotyczące samej encji;
- serializer definiuje kontrakt wejścia i wyjścia oraz sprawdza poprawność struktury i pojedynczych pól;
- view uwierzytelnia żądanie, uruchamia permission, wywołuje właściwy serwis i mapuje wynik na odpowiedź HTTP;
- permission sprawdza rolę systemową oraz relację użytkownika z konkretnym obiektem;
- service realizuje przypadek użycia i reguły zależne od stanu wielu encji, zarządza transakcją i zwraca jawny rezultat;
- czysty silnik punktacji pozostaje niezależny od Django.

Na początku wystarcza jeden czytelny `services.py` na aplikację domenową. Podział na mniejsze moduły następuje dopiero, gdy plik przestaje mieć jedną spójną odpowiedzialność. Projekt nie wprowadza warstwy repozytoriów, CQRS, mikroserwisów ani własnego frameworka bez rzeczywistej potrzeby.

`ModelViewSet` służy do prostych operacji CRUD, list i odczytu. Akcje zmieniające przebieg turnieju, takie jak `start`, `close-round`, `choose-category` lub `complete`, są osobnymi komendami przez `@action`, `APIView` albo niewielki wyspecjalizowany widok. Przykładowo zakończenie turnieju jest wyrażone jako `POST /api/tournaments/{id}/complete`, a nie dowolny `PATCH` pola `status`.

API korzysta ze standardowych reprezentacji i kodów odpowiedzi DRF. Własna koperta odpowiedzi, linki hipermedialne i rozbudowane metadane pojawiają się tylko wtedy, gdy konkretny klient ich potrzebuje.

Administrator systemowy korzysta ze standardowych mechanizmów Django: `is_staff`, `is_superuser`, grup i permissions. Nie powstaje własne pole `is_admin`, a zwykłe API nie pozwala użytkownikowi zmieniać pól administracyjnych. Uprawnienia organizatora wynikają z `TournamentOrganizer`, ponieważ turniej może mieć kilku organizatorów.

### 11.2. Przykładowe endpointy

API jest projektowane wokół akcji domenowych, a nie wyłącznie generycznego CRUD-u.

Przykładowe zasoby i komendy MVP:

```text
POST   /api/auth/register
POST   /api/auth/token
POST   /api/auth/token/refresh
POST   /api/auth/logout
POST   /api/auth/password/change
POST   /api/auth/password/reset

GET    /api/tournaments
GET    /api/tournaments?available_to_join=true
POST   /api/tournaments
POST   /api/tournaments/{id}/participants
POST   /api/tournaments/{id}/join
POST   /api/tournaments/{id}/leave
POST   /api/tournaments/{id}/registration/close
POST   /api/tournaments/{id}/start
POST   /api/tournaments/{id}/rounds/generate-next
POST   /api/tournaments/{id}/rounds/{id}/close
POST   /api/tournaments/{id}/complete

POST   /api/games/{id}/roll
POST   /api/games/{id}/holds
POST   /api/games/{id}/choose-category
GET    /api/games/{id}/state
GET    /api/tournaments/{id}/ranking
GET    /api/tournaments/{id}/history
GET    /api/comparisons/participants/{player_id}
```

Komendy wersji 1.0 i V2:

```text
POST   /api/tournaments/{id}/generate-bracket
POST   /api/tournaments/{id}/cancel
POST   /api/games/{id}/alarms
GET    /api/comparisons/teams/{team_id}
```

Endpoint odświeżania przyjmuje wyłącznie refresh token. Wylogowanie unieważnia przekazany refresh token i usuwa jego ciasteczko; wykrycie ponownego użycia tokenu lub wylogowanie ze wszystkich urządzeń unieważnia całą rodzinę zgodnie z zasadami bezpieczeństwa.

`join`, `leave`, `registration/close`, a w wersji 1.0 także `cancel`, są komendami domenowymi, nie dowolną zmianą pól przez `PATCH`. Serwis `join` blokuje rekord turnieju przez `select_for_update()`, ponownie sprawdza liczbę zajętych miejsc wewnątrz transakcji i dopiero wtedy tworzy lub reaktywuje udział. Brak wolnego miejsca, duplikat aktywnego zapisu albo równoczesna przegrana walka o ostatnie miejsce zwracają `409 Conflict`.

W wersji 1.0 komenda `cancel` zapisuje osobę, kategorię i szczegóły powodu, ustawia `cancelled_at` oraz wylicza `retention_until`; nie usuwa danych w tym samym żądaniu. Trwałe czyszczenie wykonuje oddzielne, idempotentne polecenie administracyjne po upływie retencji, dzięki czemu odpowiedź API nie zależy od rozmiaru historii turnieju.

### 11.3. Kontrakt i ręczna weryfikacja

Kontrakt API jest ręcznie sprawdzany w uporządkowanej, wersjonowanej kolekcji Postmana albo za pomocą plików `.http`. Scenariusze są grupowane w obszarach `auth`, `tournaments`, `registration`, `games` i `history`, korzysta ze zmiennych środowiskowych oraz nie zawiera prawdziwych tokenów ani haseł. Scenariusze obejmują co najmniej logowanie i odświeżanie tokenu, listę otwartych zapisów, `join`, `leave`, konflikt ostatniego miejsca, rzut, zmianę zatrzymanych kości, wybór kategorii, ranking oraz odpowiedzi `400`, `401`, `403`, `404`, `409` i `429`. Testy manualne API nie zastępują automatycznych testów w pytest, lecz ułatwiają niezależne sprawdzenie backendu przed ukończeniem frontendu.

Serializery jawnie wymieniają udostępniane pola zamiast używać `fields = "__all__"`. Lista turniejów, szczegół turnieju, stan gry i historia korzystają z osobnych serializerów, aby ograniczyć over-fetching oraz ryzyko przypadkowego ujawnienia danych. OpenAPI dokumentuje przykłady żądań, odpowiedzi sukcesu i istotnych odmów.

API zachowuje standardowe reprezentacje błędów DRF, ale błędy domenowe otrzymują stabilny kod maszynowy, np. `NOT_YOUR_TURN`, `CATEGORY_ALREADY_USED`, `ROUND_NOT_COMPLETE` albo `TOURNAMENT_FULL`. Klient nie otrzymuje tracebacka ani surowego komunikatu wyjątku; nieoczekiwany błąd jest logowany po stronie serwera i zwracany jako bezpieczne `500`.

Endpoint porównania uczestnika wymaga roli organizatora powiązanego ze wszystkimi wskazanymi turniejami albo uprawnień administratora. Przyjmuje ograniczoną listę identyfikatorów i odrzuca każde żądanie zawierające turniej niezakończony. Filtrowanie oraz ukrycie przycisku wyłącznie w interfejsie nie są wystarczającym zabezpieczeniem.

### 11.4. Pionowe przekroje i kolejność implementacji

Każdy ważny pionowy przekrój obejmuje:

```text
Żądanie → uwierzytelnienie → uprawnienia → walidacja → logika domenowa
→ transakcja i modele → odpowiedź lub zdarzenie → test → dokumentacja
```

Kolejność implementacji:

1. konto użytkownika, JWT, refresh, logout i podstawowe permissions;
2. utworzenie oraz odczyt turnieju z relacją organizatora;
3. przypisanie uczestnika przez relację M:N, zapisy `OPEN`, `join`/`leave`, limit miejsc i odmowa duplikatu;
4. synchroniczne rozegranie jednej tury przy jednym stole: rzut, zatrzymania, wybór kategorii i punktacja;
5. ukończenie pojedynczej rozgrywki i odtworzenie wyniku ze źródłowych rzutów;
6. kolejne rundy grupowe, rotacyjne przydziały do stołów, zamknięcie rundy, ranking i zakończenie turnieju;
7. zakończenie turnieju, własna historia, replay organizatora i ograniczone porównanie uczestnika tylko po zakończonych turniejach;
8. wiele równoległych stołów oraz aktualizacje WebSocket dopiero po ustabilizowaniu komend REST;
9. konfiguracja Django Admin, scenariusz demonstracyjny, dokumentacja, Docker oraz CI w ramach MVP;
10. wersja 1.0: osobne etapy, kwalifikacja, drabinka pucharowa i przekazywanie zwycięzców;
11. wersja 1.0: audyt, alarmy, anulowanie, retencja oraz korekty;
12. V2: trwałe drużyny i przekrojowe porównanie drużynowe.

Każdy punkt kończy się działającym endpointem lub przepływem, testem poprawnego przypadku, testem odmowy oraz aktualizacją OpenAPI i README. Nie rozpoczyna się kolejnego rozszerzenia technologicznego, dopóki wcześniejszy przekrój nie działa od żądania do bazy.

---

## 12. Element asynchroniczny i współbieżność

Naturalnym elementem asynchronicznym są równoległe stoły. Każdy stół zmienia własny stan, a organizator obserwuje wiele rozgrywek bez przeładowywania całej strony.

Docelowa realizacja:

- komendy zmieniające stan, np. rzut albo wybór kategorii, przechodzą przez transakcyjne API;
- po zatwierdzeniu transakcji backend publikuje zdarzenie do właściwej grupy WebSocket;
- Django Channels aktualizuje uczestników danego stołu i panel organizatora;
- Redis może pełnić rolę warstwy kanałów, ale nie jest źródłem prawdy;
- klient po utracie połączenia pobiera aktualny stan przez zwykłe API;
- wiadomość czasu rzeczywistego nie może ujawniać historii, do której odbiorca nie ma uprawnień.

Logika biznesowa pozostaje w serwisach domenowych, a nie w konsumencie WebSocket. Akcje rzutów wymagają transakcji, blokady aktualnego stanu tury i idempotencyjnego identyfikatora, aby dwa kliknięcia lub dwa równoczesne żądania nie utworzyły dwóch rzutów.

Asynchroniczność nie znosi barier domenowych:

- stoły mogą działać równolegle w obrębie rundy;
- uczestnicy przy jednym stole działają kolejno;
- nowa runda grupowa czeka na wszystkie stoły bieżącej rundy;
- nowa runda pucharowa czeka na wszystkie wymagane mecze;
- nowy etap czeka na zamknięcie poprzedniego.

Celery obsługuje wyłącznie operacje niewymagające natychmiastowego wyniku,
takie jak powiadomienia i zadania retencyjne. Dwie kolejki i dwóch workerów
spełniają wymagania kursowe. Rzuty, zatrzymania, wybór kategorii, zamykanie rund
i ranking pozostają synchroniczne oraz transakcyjne.

---

## 13. Architektura techniczna

### 13.1. Backend

- Python 3.12;
- Django;
- Django REST Framework;
- Djoser i SimpleJWT dla standardowych operacji konta oraz JWT;
- drf-spectacular dla OpenAPI i Swagger UI;
- PostgreSQL;
- serwisy domenowe dla punktacji, grupowania, rankingu i awansów;
- Django Channels i Redis w wersji czasu rzeczywistego;
- serwer ASGI Daphne, ponieważ aplikacja obsługuje WebSocket;
- `uv`, `pyproject.toml` i plik blokady wersji dla powtarzalnych zależności.

Aplikacja jest systemem sieciowym obsługującym równoległe urządzenia i stoły. Może zostać uruchomiona w sieci lokalnej bez dostępu do publicznego Internetu, ale wszystkie urządzenia muszą mieć połączenie z centralnym serwerem Django. Tryb `offline-first` oraz przechowywanie stanu turnieju jako źródła prawdy w przeglądarce nie wchodzą do zakresu; chwilowa utrata WebSocketu jest obsługiwana przez ponowną synchronizację z API. Reset przez e-mail wymaga dostępu serwera do usługi pocztowej.

### 13.2. Silnik gry

Moduł gry kościanej obejmuje walidację rzutów, analizę pięciu kości i punktację.
Czysty rdzeń punktacji nie zależy od Django, bazy ani interfejsu, dzięki czemu
można testować go jednostkowo. Serwisy aplikacyjne otaczające ten rdzeń pilnują
tury, uprawnień, transakcji i zapisu, ale nie przejmują odpowiedzialności domeny
turniejowej za rundy, przydziały, ranking ani awans.

Każda figura lub kategoria ma osobną funkcję rozpoznającą układ i osobną funkcję punktującą albo jedną małą funkcję łączącą oba zadania. Rejestr kategorii mapuje stabilny identyfikator kategorii na odpowiednią funkcję i metadane reguły. Wybór użytkownika jest obsługiwany przez ten rejestr zamiast przez jeden rozbudowany łańcuch `if/elif`.

```text
rzut → walidacja stanu tury → wybór kategorii przez uczestnika
→ funkcja punktująca → zapis wyniku → przekazanie wyniku domenie turniejowej
```

Silnik nie ujawnia podczas aktywnej tury możliwych układów, rekomendacji,
najlepszego wyboru ani prognozowanych punktów. Frontend zna pola wykorzystane
oraz reguły kategorii, ale decyzję podejmuje uczestnik bez podpowiedzi systemu.

W MVP obsługa stołu powstaje w HTML/CSS/JavaScript oraz Canvas. Backend pozostaje
autorytetem kolejności, legalności akcji i punktacji. W turnieju zdalnym jest
również autorytetem losowania; w stacjonarnym waliduje zarejestrowany wynik
fizycznych kości, ale nie rozstrzyga samodzielnie sporu o zdarzenie przy stole.

Wirtualny rzut korzysta z małego interfejsu `DiceGenerator`. Implementacja
produkcyjna używa źródła losowości systemu operacyjnego, a test generatora
zwracającego ustaloną sekwencję. W tym trybie klient nie przesyła wartości ani
ziarna. Fizyczny tryb przyjmuje od aktywnego uczestnika odczyt pięciu kości
i waliduje go zgodnie ze stanem tury.

Serwis rzutu wymusza liczbę rozliczanych kości na podstawie stanu tury. Pierwszy
rzut zawsze obejmuje pięć wartości i nie przyjmuje zatrzymań. Drugi oraz trzeci
zmieniają wyłącznie kości niezatrzymane, a następna tura usuwa zatrzymania.

Losowość przydziału do stołów jest oddzielona od losowania kości. Serwis grupowania może przyjąć kontrolowany generator na potrzeby testów, natomiast w działającym turnieju jego parametrów nie wybiera uczestnik. Zapis wersji algorytmu i danych wejściowych pozwala wyjaśnić przydział bez ujawniania informacji pozwalających przewidzieć rzuty kośćmi.

W V2 można zbudować osobny klient desktopowy Pygame. Nie implementuje on ponownie
zasad gry, lecz korzysta z tego samego Django API, silnika domenowego po stronie
backendu oraz zdarzeń WebSocket. W turnieju zdalnym Pygame może losować wizualny
przebieg animacji, ale kończy go wartościami wygenerowanymi przez backend. 
W turnieju stacjonarnym prezentuje wartości fizycznego rzutu zaakceptowane
przez backend. Pierwszy rzut tury obejmuje wszystkie pięć kości, a drugi i trzeci tylko
kości niezatrzymane.

### 13.3. Frontend

Rozwój iteracyjny:

1. Django Templates, HTML i CSS;
2. JavaScript lub HTMX dla częściowych aktualizacji;
3. WebSocket dla stołów i nadzoru;
4. opcjonalny SPA dopiero wtedy, gdy złożoność interfejsu to uzasadni.

Zaawansowany frontend nie jest warunkiem poprawnego modelu domenowego.

Interfejs stosuje progresywne ujawnianie i doładowywanie na żądanie: akordeony, jeden współdzielony modal, częściowe aktualizacje formularza oraz ograniczone porcje list. Daje to płynność kojarzoną z aplikacją jednostronicową bez automatycznego infinite scrolla i bez odbierania użytkownikowi wyraźnego końca aktualnie przeglądanego zbioru. Stan filtrów, rozwinięty element i pozycja widoku powinny pozostać zachowane po częściowej aktualizacji.

Warstwa przeglądarkowa w MVP pozostaje możliwie cienka. Prezentuje stan oraz wysyła intencje użytkownika, natomiast autoryzacja, walidacja, losowanie, kolejność, punktacja i przejścia stanów należą do API oraz serwisów domenowych. Dzięki temu backend można sprawdzić niezależnie od gotowości interfejsu.

Podstawowymi sposobami obsługi interfejsu MVP są mysz i dotyk. Kliknięcie albo dotknięcie kości automatycznie przenosi ją do oznaczonego obszaru zatrzymań lub z powrotem; przeciąganie i specjalna warstwa obsługi klawiatury nie są wymagane. Semantyczne przyciski zachowują naturalną obsługę klawiatury oferowaną przez przeglądarkę. Fokus po aktualizacji częściowej trafia w przewidywalne miejsce; modal zatrzymuje fokus do czasu zamknięcia i oddaje go elementowi otwierającemu. Kolor, animacja ani dźwięk nie są jedynym nośnikiem statusu, a `prefers-reduced-motion` ogranicza animację kości i przejścia bez zmiany przebiegu gry.

### 13.4. Uwierzytelnianie

Projekt wykorzystuje JWT:

- access token: 15 minut;
- refresh token: maksymalnie 8 godzin od logowania;
- wygaśnięcie sesji po 30 minutach rzeczywistej bezczynności;
- rotacja refresh tokenu przy każdym użyciu;
- natychmiastowe unieważnienie poprzedniego refresh tokenu;
- zachowanie pierwotnej ośmiogodzinnej granicy podczas rotacji;
- automatyczne odświeżenie access tokenu, niewidoczne dla użytkownika;
- ponowne logowanie po wygaśnięciu refresh tokenu;
- brak długoterminowego „zapamiętaj mnie” w MVP.

Djoser udostępnia standardowe operacje rejestracji, zmiany i resetu hasła, a SimpleJWT tworzy oraz weryfikuje tokeny. Cienka warstwa aplikacyjna ustawia tokeny przeglądarkowe w bezpiecznych ciasteczkach i realizuje przyjęte zasady rotacji, bezczynności oraz unieważniania rodziny tokenów. Projekt nie implementuje własnego hashowania haseł ani własnego formatu JWT.

Krótki access token nie skraca użytkownikowi sesji do 15 minut. Dopóki ważny jest refresh token, klient odnawia dostęp krótko przed wygaśnięciem albo wykonuje pojedynczą próbę odświeżenia po odpowiedzi `401`.

Automatyczne odświeżanie jest wykonywane tylko podczas aktywnego korzystania z aplikacji. Samo otwarcie strony, heartbeat WebSocketu ani odbieranie zdarzeń nie zeruje limitu bezczynności. Backend przechowuje identyfikator rodziny tokenów, pierwotny czas logowania i czas ostatniej aktywności, aby rotacja nie mogła przedłużać sesji bez końca. Wylogowanie, zmiana hasła albo wykrycie ponownego użycia unieważnionego refresh tokenu odwołuje całą rodzinę tokenów.

Tokeny są przenoszone w ciasteczkach `HttpOnly`, `Secure` i `SameSite` oraz nie trafiają do `localStorage`. Ponieważ uwierzytelnianie wykorzystuje ciasteczka, żądania modyfikujące dane podlegają ochronie CSRF.

### 13.5. Hasła i dostęp anonimowy

- Django przechowuje wyłącznie hashe haseł z indywidualną solą; Argon2 jest pierwszym skonfigurowanym hasherem, a mechanizmy Django obsługują migrację starszego hasha przy poprawnym logowaniu;
- każdy zalogowany użytkownik może zmienić własne hasło;
- reset zapomnianego hasła w MVP odbywa się przez jednorazowy, krótko ważny link e-mailowy; odpowiedź formularza jest taka sama niezależnie od tego, czy adres istnieje, aby nie ułatwiać enumeracji kont;
- passkeys/WebAuthn wchodzą do V2 jako dodatkowa metoda logowania;
- SMS nie znajduje się w roadmapie bez konkretnego uzasadnienia biznesowego;
- operacje turniejowe wymagają uwierzytelnienia i odpowiedniej relacji z turniejem;
- anonimowy użytkownik nie ma dostępu do roboczego API;
- w MVP gość widzi wyłącznie rejestrację i logowanie;
- lista turniejów `OPEN` jest widoczna dopiero po zalogowaniu i zwraca minimalny zakres danych potrzebny do decyzji o zapisie;
- dokumentacja Swagger/ReDoc/OpenAPI w środowisku produkcyjnym wymaga uwierzytelnienia i uprawnienia technicznego albo pozostaje wyłączona;
- w V1 publiczny widok może pokazywać tylko jawnie opublikowane rezultaty zakończonego turnieju przez osobny endpoint z minimalnym zakresem pól.

Endpointy logowania, odświeżania tokenu i resetu hasła otrzymują ścisłe limity żądań uwzględniające adres IP oraz identyfikator konta. Komendy gry otrzymują łagodniejszy limit per użytkownik i rozgrywka, aby ograniczyć spam, ale throttling nigdy nie zastępuje permission, idempotencji, transakcji ani blokad w bazie.

### 13.6. Panel administratora Django

Django Admin jest wymaganym, skonfigurowanym narzędziem administratora systemowego. Nie jest tym samym co panel organizatora turnieju i nie jest dostępny na podstawie samej relacji `TournamentOrganizer`.

Konfiguracja obejmuje:

- `list_display` z najważniejszym stanem, właścicielem, liczbą uczestników i datami;
- `search_fields` dla nazwy turnieju, adresu e-mail, nazwy wyświetlanej i identyfikatora rozgrywki;
- `list_filter` dla statusów, dat, trybu zapisów i etapów;
- domyślne `ordering` od najnowszych lub najpilniejszych rekordów;
- `autocomplete_fields` albo `raw_id_fields` dla dużych relacji;
- pola wyliczane i techniczne jako `readonly_fields`;
- rzuty i zakończone wyniki bez zwykłej możliwości ręcznej edycji;
- brak surowych haseł, tokenów, sekretów i zbędnych danych osobowych na listach.

Zmiany stanu turnieju wymagające reguł biznesowych nie są realizowane przez dowolną edycję pola `status` ani masową akcję admina. Administrator korzysta z tego samego serwisu domenowego albo specjalnie zabezpieczonej akcji, dzięki czemu nie omija transakcji, walidacji i audytu.

### 13.7. Docker, konfiguracja i README

Środowisko projektu obejmuje aplikację ASGI, PostgreSQL, Redis, wymagane workery
Celery oraz harmonogram zadań okresowych. Docker Compose zapewnia powtarzalne
uruchomienie tych usług, trwałość danych i kontrolę ich gotowości.

Konfiguracja development i production pozostaje rozdzielona. Sekrety, dane
dostępowe, klucze JWT i konfiguracja poczty pochodzą ze zmiennych środowiskowych
i nie trafiają do repozytorium. Publiczne wdrożenie stosuje ASGI, bezpieczne
ustawienia oraz ochronę usług bazodanowych i kolejkowych przed bezpośrednim
dostępem z Internetu.

README powstaje jako końcowa, dwujęzyczna dokumentacja projektu. Polska i
angielska wersja opisują ten sam zamrożony stan funkcjonalny, architekturę,
uruchomienie, API, testy, bezpieczeństwo oraz granice kolejnych wersji. Wersja
angielska jest redagowana naturalnie w tym języku, a nie tłumaczona mechanicznie.

### 13.8. Organizacja kodu, docstringi i typowanie

Kod rozdziela uniwersalną domenę turniejową od domeny konkretnej gry w kości.
Konta i tożsamość użytkownika pozostają osobnym obszarem. Turnieje, uczestnicy,
rundy, stoły, role i cykl życia nie zależą od zasad punktowania kości, natomiast
rzuty, zatrzymania, kategorie i punktacja należą do modułu gry kościanej.

Konfiguracja aplikacji Django pozostaje w jednoznacznie nazwanym obszarze
`config`; konfiguracje poszczególnych aplikacji są umieszczane w ich własnych
przestrzeniach nazw. Integracje z zewnętrznymi mechanizmami otrzymują małe
adaptery tylko wtedy, gdy przynosi to rzeczywistą wymienność albo testowalność.

Zasady dokumentowania:

- nie każda funkcja i klasa wymaga docstringa;
- publiczne API modułu, serwisy domenowe i nieoczywiste algorytmy otrzymują krótki docstring wyjaśniający cel, ważne ograniczenia, skutki uboczne lub przyczynę decyzji;
- docstring powtarzający nazwę funkcji jest usuwany;
- dla zwykłej metody wystarcza jedno lub dwa zdania; uporządkowany styl Google albo NumPy jest używany tylko wtedy, gdy złożone argumenty, wyjątki lub wartość zwracana rzeczywiście wymagają osobnych sekcji;
- komentarze opisują powód nietypowego rozwiązania, nie tłumaczą kolejno oczywistych instrukcji;
- decyzje obejmujące kilka modułów trafiają do README lub krótkiego ADR, zamiast do rozbudowanego komentarza w przypadkowym pliku.

Zasady typowania:

- funkcje i metody mają typy argumentów oraz wartości zwracanych, szczególnie na granicach serwisów i czystego silnika gry;
- lokalne zmienne są anotowane tylko wtedy, gdy poprawia to czytelność lub pomaga narzędziu statycznemu;
- jeżeli struktura słownika jest znana, stosuje się `TypedDict`, dataclass albo dedykowany obiekt zamiast ogólnego `dict[str, Any]`;
- serializer DRF pozostaje kontraktem danych HTTP; typy Pythona nie zastępują walidacji danych pochodzących od klienta;
- skomplikowane typy generyczne nie są celem samym w sobie. Czytelny typ domenowy jest ważniejszy niż maksymalnie abstrakcyjna adnotacja.

### 13.9. Narzędzia jakościowe, Git i CI

Projekt wykorzystuje przede wszystkim `pytest`, automatyczną kontrolę jakości,
pre-commit oraz CI w GitHub Actions. Kontrole obejmują własną logikę, API,
migracje i spójność dokumentowanego kontraktu. Pokrycie kodu wskazuje luki, ale
nie jest sztucznie podnoszone do 100%.

Historia Gita składa się z małych, zamkniętych i sprawdzonych zmian. Do
repozytorium nie trafiają sekrety ani lokalne artefakty.

### 13.10. Zapytania ORM, paginacja i cache

Lista turniejów korzysta z lekkiego serializera podsumowania, a rozwinięcie, ranking i replay z osobnych serializerów szczegółowych. QuerySety używają `select_related()`, `prefetch_related()`, adnotacji i indeksów wyłącznie tam, gdzie wynik pomiaru lub test liczby zapytań pokazuje korzyść. Szczególną uwagę otrzymują panel wielu stołów, lista uczestników oraz historia rzutów, ponieważ łatwo w nich utworzyć problem N+1.

Paginacja jest wykonywana po stronie serwera. Dynamiczne „Załaduj więcej” zmienia prezentację kolejnej strony, ale nie pobiera całego archiwum w jednym żądaniu.

Redis w MVP pełni rolę channel layer, a nie automatycznie cache wszystkiego. Nie cache'uje się wartości kości, kolejki, permissions, tokenów ani zmiennego stanu aktywnego stołu. Ewentualny cache niezmiennych podsumowań zakończonych turniejów powstaje dopiero po pomiarze, ma ograniczony TTL i jawne unieważnianie po audytowanej korekcie.

Wydajność aktywnej rozgrywki jest projektowana i profilowana dla turnieju liczącego do 128 uczestników. Przy stołach czteroosobowych oznacza to 32 równoległe stoły; przy minimalnej liczebności dwóch osób górną granicą jest 64 stoły. Limit nie stanowi obietnicy obsługi dowolnie większej liczby jednoczesnych klientów bez dalszych pomiarów.

### 13.11. Obserwowalność i diagnostyka

Logi aplikacji mają strukturę pozwalającą powiązać błąd z identyfikatorem żądania, użytkownikiem technicznym, turniejem i rozgrywką bez zapisywania tokenów, haseł, pełnych payloadów ani nadmiarowych danych osobowych. Nieoczekiwane wyjątki trafiają do logów z tracebackiem, natomiast klient otrzymuje bezpieczny komunikat i identyfikator zdarzenia.

Diagnostyka obejmuje gotowość usług, błędy HTTP, czas kluczowych operacji,
połączenia WebSocket i problemy z publikowaniem zdarzeń. Optymalizacje wynikają
z pomiarów, ze szczególnym uwzględnieniem kosztownych zapytań i problemu N+1.

Własne middleware do identyfikatora żądania albo pomiaru czasu jest dopuszczalne tylko wtedy, gdy rzeczywiście zasila logi i diagnostykę. Nie powstaje bez realnego odbiorcy tych danych.

---

## 14. Bezpieczeństwo i integralność danych

- Backend, a nie frontend, pilnuje kolejki, limitu rzutów i dostępności kategorii.
- Wszystkie operacje zmieniające przebieg gry są autoryzowane względem konkretnego turnieju i stołu.
- Zakończone rzuty są niezmienne; korekta tworzy jawne zdarzenie i wymaga uprawnienia organizatora.
- Zmiana statusu rundy, etapu i turnieju odbywa się przez dozwolone przejścia maszyny stanów.
- Porównania sprawdzają status turnieju zarówno w zapytaniu, jak i w warstwie serwisowej.
- Uczestnik nie może pobrać cudzej historii przez bezpośrednią zmianę identyfikatora w adresie.
- Organizator ma dostęp wyłącznie do turniejów, z którymi jest powiązany.
- Uczestnik może dołączyć wyłącznie we własnym imieniu; identyfikator zawodnika wynika z uwierzytelnionego konta, a nie z dowolnego pola żądania.
- `join` ignoruje lub odrzuca próby przesłania drużyny, numeru startowego, rozstawienia albo statusu udziału; pola te pozostają pod kontrolą organizatora i serwisu domenowego.
- Endpointy `join` i `leave` podlegają limitowaniu żądań, lecz poprawność limitu miejsc opiera się na transakcji i blokadzie w bazie, nie na throttlingu.
- Anulowanie wymaga uprawnienia organizatora, jawnego powodu i dodatkowego potwierdzenia dla turnieju `ACTIVE`; `COMPLETED` ani `ARCHIVED` nie mogą przejść do `CANCELLED`.
- W trybie zdalnym backend losuje kości. W trybie stacjonarnym backend przyjmuje
  wartości fizycznego rzutu i rygorystycznie waliduje legalność ich zapisu.
- Dane wejściowe przechodzą walidację serializera, a zamknięte zbiory korzystają z `TextChoices`; aplikacja nie używa `eval()` ani nie buduje surowego SQL-a z tekstu użytkownika.
- Szablony zachowują domyślne escape'owanie Django, a generowany HTML korzysta z `format_html()` tylko z bezpiecznie przekazanymi argumentami.
- Połączenie WebSocket sprawdza uwierzytelnienie i relację użytkownika
  z turniejem przed dołączeniem do grupy odbiorców WebSocket. Komendy zmieniające
  stan przechodzą przez autoryzowane REST API; utrata uprawnień kończy subskrypcję
  albo wymusza ponowne połączenie.
- Operacje krytyczne używają transakcji, ograniczeń bazy i blokad zapobiegających wyścigom.
- Logi techniczne nie powinny zawierać tokenów, haseł ani nadmiarowych danych osobowych.

### 14.1. Retencja anulowanych turniejów

Poniższa polityka obowiązuje od wersji 1.0, gdy zostanie wdrożony pełny status `CANCELLED`.

Domyślna retencja pełnych danych turnieju `CANCELLED` wynosi 30 dni od `cancelled_at`. Jest ustawieniem wdrożeniowym kontrolowanym przez administratora systemu, a nie opcją wybieraną przez organizatora turnieju. Okres ma umożliwić rozstrzygnięcie typowego sporu, ale nie uzasadnia bezterminowego przechowywania danych, które nie będą publikowane ani porównywane.

Ta polityka nie obejmuje turniejów `COMPLETED` ani `ARCHIVED`, ponieważ ich historia stanowi właściwy rezultat produktu i źródło dozwolonych analiz.

Po osiągnięciu `retention_until` idempotentne polecenie zarządzające, np. `purge_cancelled_tournaments`, wykonuje transakcyjnie:

1. blokadę rekordu turnieju i ponowne sprawdzenie statusu oraz terminu;
2. pominięcie turnieju objętego ważną, czasową blokadą retencji;
3. utworzenie anonimowego `TournamentCancellationSummary`;
4. trwałe usunięcie turnieju i szczegółowego grafu zależności, w tym udziałów, relacji z kontami, rozgrywek, tur, rzutów, swobodnego opisu anulowania i zdarzeń audytowych;
5. zapis technicznego wyniku operacji bez danych osobowych.

Nie stosuje się soft delete dla całego szczegółowego grafu po upływie retencji, ponieważ nadal zajmowałby miejsce i zwiększał ryzyko niezamierzonego ujawnienia. Anonimizacja jest ograniczona do małego rekordu zbiorczego, który ma dalszy, jasno określony cel.

Blokadę retencji można ustanowić wyłącznie dla udokumentowanego, nierozstrzygniętego sporu. Wymaga uprawnienia administracyjnego, uzasadnienia, terminu wygaśnięcia i wpisu audytowego; nie może być bezterminowa. Kopie zapasowe mają własny ograniczony cykl życia, a procedura odtworzenia bazy musi ponownie uruchomić purge dla rekordów, których termin już minął.

Okresowy purge jest zadaniem utrzymaniowym uruchamianym przez Celery Beat poza
krytyczną ścieżką rozgrywki.

---

## 15. Strategia testów

Testy powstają razem z każdym pionowym przekrojem, a nie dopiero po ukończeniu całej aplikacji. Przekrój bez testu najważniejszej reguły i przypadku odmowy nie jest uznawany za zakończony.

Celem nie jest przetestowanie każdej linijki ani osiągnięcie sztucznego 100% pokrycia. Priorytet mają czysta logika punktacji i grupowania, reguły biznesowe w serwisach, permissions oraz główne endpointy API. Proste mapowanie pól dostarczone przez Django lub DRF nie wymaga osobnego testu, jeżeli nie zawiera własnego zachowania.

Lista poniżej obejmuje również funkcje 1.0 i V2. Test powstaje razem z odpowiadającą mu pionową funkcją; pozycje odłożone w roadmapie nie należą do zakresu testów MVP.

### 15.1. Testy jednostkowe

- każda kategoria punktowa;
- kompletność rejestru kategorii i wywołanie właściwej funkcji bez rozbudowanego łańcucha `if/elif`;
- oba warianty pokerów;
- premia za pierwszy rzut oraz pozostałe dodatnie i ujemne składniki punktacji gry;
- porównywanie remisów po posortowanych wynikach;
- od V2: średnia rundowa drużyny i średni dorobek punktowy na członka
  zatwierdzonego składu, z osobnym sprawdzeniem obu mianowników;
- bazowy rozkład wężykowy, np. dla 16 uczestników i 4 grup;
- permutacje wewnątrz koszyka ograniczające wspólne stoły członków drużyny i ponowne spotkania;
- ocena jakości przydziału do grup oraz powtarzalność wyniku dla zapisanego ziarna losowania;
- kontrolowana sekwencja rzutów oraz brak zależności testu od prawdziwej losowości;
- pierwszy rzut każdej tury obejmujący dokładnie pięć kości oraz reset zatrzymań przy rozpoczęciu następnej tury;
- drugi i trzeci rzut zmieniające wyłącznie wartości kości niezatrzymanych;
- jawne przypadki graniczne czasu decyzji i terminów przy użyciu kontrolowanego zegara.

### 15.2. Testy modeli i serwisów

- relacja M:N uczestnika z turniejem;
- zakaz podwójnego zapisu uczestnika;
- dołączenie do otwartego turnieju oraz reaktywacja wcześniejszego `WITHDRAWN`;
- odmowa dołączenia po terminie, po ręcznym zamknięciu zapisów, do trybu `ORGANIZER_ONLY` i po wyczerpaniu miejsc;
- wycofanie przed startem oraz odmowa samodzielnego `leave` po przejściu do `ACTIVE`;
- odmowa rozpoczęcia turnieju poniżej minimalnej liczby uczestników;
- od wersji 1.0: anulowanie z obowiązkowym powodem, wyliczeniem `retention_until` i czasowym zachowaniem dotychczasowych danych;
- od wersji 1.0: odmowa purge przed terminem oraz pominięcie turnieju objętego ważną blokadą retencji;
- od wersji 1.0: utworzenie anonimowego `TournamentCancellationSummary` i trwałe usunięcie szczegółowego grafu po terminie;
- od wersji 1.0: idempotentne ponowienie polecenia purge;
- niezmienność konfiguracji po starcie;
- kompletność rundy przed jej zamknięciem;
- od wersji 1.0: awans zwycięzcy do właściwego meczu;
- ponowne przeliczenie agregatów ze źródłowych rzutów.

### 15.3. Testy API i uprawnień

- anonimowa próba wyświetlenia otwartych zapisów i użycia `join`;
- lista otwartych zapisów dla zalogowanego użytkownika bez ujawnienia pełnej listy uczestników;
- zapis użytkownika wyłącznie we własnym imieniu;
- odmowa ustawienia przez `join` drużyny, numeru startowego, rozstawienia lub własnego statusu;
- ponowne `join` aktywnie zapisanego uczestnika zakończone konfliktem `409`;
- odmowa zmiany trybu zapisów, limitu i terminu bez uprawnień organizatora;
- od wersji 1.0: odmowa anulowania bez uprawnienia, bez powodu oraz ze statusu `COMPLETED` lub `ARCHIVED`;
- od wersji 1.0: odmowa ustanowienia blokady retencji bez uprawnienia administracyjnego, uzasadnienia lub terminu końcowego;
- rzut we własnej i cudzej turze;
- odmowa zatrzymania kości przed pierwszym rzutem;
- pierwszy rzut każdej tury obejmujący wszystkie pięć kości oraz kolejne rzuty obejmujące tylko kości niezatrzymane;
- zapis zatrzymanych kości we własnej turze i odmowa modyfikacji cudzej tury;
- czwarty rzut w tej samej turze;
- odmowa przejścia do następnego uczestnika bez wyboru kategorii po trzecim rzucie;
- ponowny wybór wykorzystanej kategorii;
- dostęp uczestnika do własnej i cudzej historii;
- odmowa dostępu uczestnika do historii przed zakończeniem całego turnieju;
- odmowa dostępu uczestnika do wspólnego formularza zakończonego etapu;
- odmowa dostępu uczestnika do przekrojowego porównania wielu turniejów;
- dostęp organizatora do własnego i obcego turnieju;
- od wersji 1.0: utworzenie alarmu przez organizatora bez automatycznej zmiany wyniku uczestnika;
- zmiana hasła przez uczestnika oraz organizatora;
- odmowa anonimowego dostępu do roboczych endpointów i dokumentacji API;
- od wersji 1.0: brak danych trwającego turnieju w publicznym endpoincie końcowych rezultatów;
- odrzucenie refresh tokenu po 30 minutach bezczynności i po 8 godzinach od logowania;
- zachowanie pierwotnej daty końca sesji po rotacji refresh tokenu;
- unieważnienie całej rodziny tokenów po ponownym użyciu tokenu z blacklisty, wylogowaniu albo zmianie hasła;
- odmowa porównania aktywnego turnieju, także po ręcznym podaniu jego identyfikatora;
- limit maksymalnie czterech turniejów w porównaniu.

### 15.4. Testy współbieżności

- dwa równoczesne zgłoszenia na jedno ostatnie miejsce, z których tylko jedno kończy się zapisem;
- dwa równoczesne żądania rzutu;
- ponowienie tego samego żądania z identycznym kluczem idempotencji;
- równoległe akcje przy różnych stołach;
- próba zamknięcia rundy podczas niedokończonej rozgrywki;
- ponowne połączenie WebSocket i synchronizacja aktualnego stanu;
- odtworzenie formularza po kolejnych zaakceptowanych zdarzeniach bez zmiany stanu przez zdarzenia odrzucone.

### 15.5. Organizacja i środowisko testów

Testy pozostają deterministyczne, niezależne od kolejności i od prawdziwych usług
zewnętrznych. Czysta logika jest sprawdzana bez bazy, a integracje obejmują
reprezentatywny przepływ od API do PostgreSQL, autoryzację obiektową, WebSocket,
Celery, współbieżność i ochronę przed N+1.

---

## 16. Roadmapa po MVP

Każda kolejna funkcja powinna powstać jako uzasadniony pionowy przekrój, bez osłabiania poprawności istniejącego systemu.

### 16.1. Wersja 1.0 — pełny zaprojektowany turniej

- niezmienny `TournamentRuleSet` oraz osobne etapy turnieju;
- formalne grupy rundy grupowej;
- kwalifikacja z rankingu, drabinka pucharowa, mecze i przekazywanie zwycięzców;
- pełne bariery pomiędzy rundami i etapami opisane w zasadach turnieju;
- `AuditEvent`, alarmy organizatora, komentarze, statusy wyjaśnienia i audytowane korekty;
- status `CANCELLED`, 30-dniowa retencja szczegółów, kontrolowany purge i anonimowe podsumowanie;
- rozbudowane komunikaty i odporność połączeń czasu rzeczywistego;
- płynne animacje rzutów 2D, efekty przyznania punktów i dopracowany responsywny dashboard;
- eksport wyników i historii;
- wykres postępu uczestnika pomiędzy zakończonymi turniejami;
- filtrowanie, sortowanie i paginacja archiwum;
- opcjonalne publikowanie wyłącznie końcowych rezultatów.

### 16.2. V2 — analityka drużynowa i rozszerzenia

- trwała tożsamość drużyn i historyczne składy w poszczególnych turniejach;
- porównywanie drużyn pomiędzy zakończonymi turniejami;
- zaawansowane statystyki rzutów, zatrzymań i kategorii;
- analiza rozkładu figur oraz skuteczności decyzji;
- rozbudowany dashboard i wykresy;
- passkeys/WebAuthn jako dodatkowa metoda logowania i odpowiedni mechanizm odzyskiwania dostępu;
- opcjonalny klient desktopowy Pygame korzystający z tego samego API i WebSocketów;
- opcjonalna wizualizacja kości 3D/WebGL jako warstwa prezentacyjna klienta webowego;
- ulepszanie mechanizmu przydziału wyłącznie wtedy, gdy testy lub rzeczywiste turnieje wykażą zbyt częste powtórki spotkań albo wspólne stoły członków jednej drużyny; możliwe zmiany obejmują korektę zdefiniowanych wag funkcji kosztu lub sprawdzanie większej liczby dopuszczalnych permutacji wewnątrz koszyków, bez naruszania ograniczeń twardych;
- opcjonalny osobny frontend SPA, jeżeli złożoność interfejsu uzasadni migrację.
