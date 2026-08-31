# Plan biznesowy produktu — system organizacji turniejów gry w kości

## 1. Discovery / Product Definition

### 1.1. Definicja produktu

Aplikacja webowa wspiera organizację wielorundowych turniejów gry w kości prowadzonych równolegle przy kilku stołach. Łączy zapisy, przebieg rozgrywek, automatyczne naliczanie punktów, ranking, nadzór organizatora oraz historię zakończonych turniejów w jednym systemie.

„Uniwersalny turniej” oznacza możliwość konfigurowania przebiegu i wybranych reguł punktacji w ramach jednej rodziny gier kościanych. Produkt nie jest konstruktorem dowolnej gry.


### 1.2. Problem

Przy tradycyjnej organizacji większego turnieju organizator musi jednocześnie:

- prowadzić zapisy i pilnować liczby uczestników;
- rozdzielać zawodników pomiędzy stoły;
- kontrolować kolejność gry i poprawność wyników;
- ręcznie sumować punkty i tworzyć ranking;
- przygotowywać kolejne rundy;
- rozstrzygać spory bez pełnej historii zdarzeń.

Powoduje to opóźnienia, pomyłki, niejednolite zasady oraz trudność w odtworzeniu przebiegu rozgrywki. Problem rośnie wraz z liczbą uczestników i równoległych stołów.

### 1.3. Grupy docelowe

- organizatorzy szkolnych, klubowych, lokalnych i hobbystycznych turniejów gry w kości;
- uczestnicy takich turniejów;
- administratorzy utrzymujący wspólną instalację systemu.

Pierwszą grupą docelową są organizatorzy wydarzeń odbywających się w jednym miejscu, gdzie wiele urządzeń może korzystać z jednego serwera przez Internet albo sieć lokalną.

Pojedynczy turniej może mieć maksymalnie 128 aktywnych uczestników; organizatorzy turnieju nie są wliczani do tego limitu. Minimalna liczba uczestników jest określana w konfiguracji konkretnego turnieju i musi być zgodna z wymaganiami jego struktury. Limit nie ogranicza łącznej liczby kont ani zakończonych turniejów przechowywanych w systemie.

### 1.4. Propozycja wartości

Produkt daje organizatorowi jedno źródło prawdy o turnieju, a uczestnikowi prosty i jednoznaczny interfejs gry. Najważniejsze korzyści to:

- mniej ręcznego liczenia i mniej błędów;
- sprawniejsze prowadzenie kilku stołów równocześnie;
- jednakowe egzekwowanie zasad wobec wszystkich uczestników;
- możliwość odtworzenia wyniku ze źródłowych rzutów i decyzji;
- bezpieczna historia zakończonych turniejów;
- ograniczone porównywanie wyników bez ujawniania danych trwającej rywalizacji.

### 1.5. Zasada wyróżniająca produkt

System automatyzuje organizację, kontrolę kolejki i punktację, ale nie podejmuje
decyzji strategicznych za uczestnika. W turnieju zdalnym generuje również
wirtualne rzuty. Waliduje reguły i utrwala decyzje, lecz nie zastępuje człowieka
w rozstrzyganiu sporu o fizyczny rzut.

### 1.6. Hipotezy do sprawdzenia

- organizator rzeczywiście oszczędza czas w porównaniu z prowadzeniem turnieju na papierze;
- uczestnicy potrafią samodzielnie obsługiwać wspólny formularz bez dodatkowego zatwierdzania każdej akcji przez organizatora;
- panel wielu stołów pozwala wykryć problem bez ciągłego przechodzenia między stanowiskami;
- rotacja stołów ogranicza powtarzalność spotkań i utrudnia trwałe porozumienia między uczestnikami;
- historia rzutów wystarcza do wyjaśnienia sporu i odtworzenia wyniku;
- podstawowa porównywarka zakończonych turniejów daje organizatorowi wartość bez przeciążania uczestnika analityką.

---

## 2. Core Architecture Assumptions

Założenia te opisują planowany sposób działania produktu z punktu widzenia użytkownika i organizacji turnieju. Są koncepcyjnym mostem pomiędzy częścią biznesową a przyszłą implementacją, a nie opisem już zbudowanego systemu. Ich rozwinięcie techniczne nastąpi podczas realizacji kolejnych pionowych przekrojów.

**Niezmienna zasada rzutu: każda nowa tura ZAWSZE zaczyna się od jednoczesnego rzutu wszystkimi pięcioma kośćmi.** Przed pierwszym rzutem nie można niczego zatrzymać. Zatrzymania są wybierane dopiero później, a drugi i trzeci rzut obejmują wyłącznie kości niezatrzymane.

- produkt działa przede wszystkim w przeglądarce;
- głównym stanowiskiem organizatora jest laptop lub tablet, natomiast uczestnik może korzystać także z telefonu;
- wiele urządzeń łączy się z jednym centralnym systemem będącym źródłem prawdy;
- turniej może działać przez publiczny Internet albo w sieci lokalnej bez dostępu do Internetu;
- aplikacja nie działa jako rozwiązanie offline-first; urządzenie bez połączenia nie prowadzi niezależnej kopii turnieju;
- stoły działają równolegle i niezależnie w obrębie tej samej rundy;
- stoły nie czekają na siebie między turami ani rozgrywkami;
- następna runda grupowa czeka na zakończenie wszystkich stołów bieżącej rundy, ponieważ korzysta z aktualnego rankingu;
- następny etap turnieju czeka na pełne zakończenie etapu poprzedniego;
- backend jest autorytetem kolejności, dostępności akcji i punktacji; w turnieju
  zdalnym generuje kości, a w stacjonarnym waliduje zarejestrowany fizyczny rzut;
- interfejs pokazuje stan i przekazuje decyzje użytkownika, ale nie może samodzielnie zmienić wyniku;
- aktualizacje stołów i panelu organizatora pojawiają się bez przeładowania strony;
- po utracie połączenia klient pobiera aktualny, wiarygodny stan z systemu;
- sztuczna inteligencja nie uczestniczy w rozgrywce i nie podpowiada decyzji;
- aplikacja nie wykorzystuje automatycznego infinite scrolla; kolejne porcje historii są doładowywane świadomą akcją użytkownika;
- podstawowa wersja jest aplikacją webową; osobny klient desktopowy pozostaje późniejszym rozszerzeniem.

### 2.1. Granica odpowiedzialności produktu

Produkt łączy organizację turnieju z prowadzeniem konkretnej gry kościanej, ale
nie traktuje ich jako jednego nierozdzielnego procesu.

- Część turniejowa odpowiada za uczestnictwo, zatwierdzone składy drużynowe,
  rundy, grupy, stoły, ranking, awans i zakończenie wydarzenia.
- Część kościana odpowiada za turę przy stole, rzuty, zatrzymania, formularz,
  wybór kategorii oraz wynik uzyskany według zamrożonych reguł.

Turniej wykorzystuje końcowy rezultat gry, ale nie ingeruje w sposób rozpoznania
figur. Gra kościana zna skład aktualnego stołu, ale nie ustala kolejnych grup,
rankingu ani awansu. Dzięki temu reguły organizacyjne można rozwijać niezależnie
od punktacji, bez deklarowania obsługi dowolnych innych gier.

### 2.2. Forma turnieju i sposób komunikacji

Turniej może być stacjonarny albo zdalny. Wydarzenie stacjonarne korzysta
z fizycznych kości i może działać przez LAN bez publicznego Internetu. Wydarzenie
zdalne korzysta z wirtualnych rzutów generowanych przez backend. MVP nie łączy
obu form w jednym turnieju hybrydowym.

Online oznacza bieżące połączenie z serwerem, LAN lub Internet opisują sieć,
a WebSocket/realtime sposób aktualizacji stanu. Pojęcia te nie określają formy
wydarzenia. Brak Internetu przy działającym LAN nie jest trybem offline.

W MVP nie powstaje osobna rola sędziego. Przy fizycznym stole aktywny uczestnik
rejestruje wynik, pozostali mogą go zweryfikować, a organizator rozstrzyga
incydenty. Nie powstaje również osobna rola operatora stołu.

---

## 3. User Requirements (User Stories)

### 3.1. Wspólne wymagania konta

- Jako użytkownik chcę się zarejestrować, zalogować i wylogować, aby bezpiecznie korzystać z funkcji przypisanych do mojego konta.
- Jako zalogowany użytkownik chcę zmienić własne hasło, aby samodzielnie zabezpieczyć konto niezależnie od pełnionej roli.
- Jako użytkownik, który zapomniał hasła, chcę odzyskać dostęp przez bezpieczny link e-mailowy.

### 3.2. Organizator

- Jako organizator chcę utworzyć i skonfigurować turniej przed jego rozpoczęciem, aby wszyscy grali według tych samych zasad.
- Jako organizator chcę wybrać zapisy otwarte albo zarządzane, ustalić limit i termin oraz móc zamknąć zapisy wcześniej.
- Jako organizator chcę przypisywać uczestników i dodatkowych organizatorów do konkretnego turnieju.
- Jako organizator chcę automatycznie tworzyć możliwie równe stoły, ograniczając powtarzające się spotkania i wspólną grę członków tej samej drużyny.
- Jako organizator chcę obserwować wszystkie stoły jednocześnie albo jeden wybrany stół.
- Jako organizator chcę widzieć aktualnego uczestnika, kolejkę oraz bieżący stan każdej rozgrywki.
- Jako organizator chcę zamknąć rundę dopiero wtedy, gdy wszystkie jej stoły zakończą grę.
- Jako organizator chcę otrzymać automatycznie przeliczony ranking potrzebny do utworzenia kolejnej rundy.
- Jako organizator chcę zakończyć turniej i zablokować jego wyniki przed zwykłą edycją.
- Jako organizator chcę odtworzyć zakończoną rozgrywkę krok po kroku w trybie tylko do odczytu.
- Jako organizator chcę porównać wynik jednej osoby pomiędzy maksymalnie czterema zakończonymi turniejami, do których mam uprawnienia.

### 3.3. Uczestnik

- Jako uczestnik chcę zobaczyć dostępne turnieje z otwartymi zapisami bez ujawniania nadmiarowych danych innych osób.
- Jako uczestnik chcę samodzielnie dołączyć do otwartego turnieju, jeżeli są wolne miejsca.
- Jako uczestnik chcę wycofać zgłoszenie przed rozpoczęciem turnieju.
- Jako uczestnik chcę jednoznacznie widzieć, kiedy przypada moja tura.
- Jako uczestnik chcę zatrzymywać wybrane kości i wykonywać kolejne rzuty, aby realizować własną strategię.
- Jako uczestnik chcę wybierać kategorię we własnym polu wspólnego formularza, bez wpisywania punktów ręcznie.
- Jako uczestnik chcę widzieć podczas rozgrywki bieżący wspólny formularz, w tym dostępne i wykorzystane pozycje innych osób przy stole.
- Jako uczestnik chcę po zakończeniu całego turnieju przejrzeć wyłącznie własną historię rzutów i decyzji.
- Jako uczestnik nie chcę otrzymywać sugestii strategicznych, aby wynik zależał od moich decyzji.

### 3.4. Administrator systemowy

- Jako administrator chcę diagnozować konta, turnieje i rozgrywki bez uzyskiwania przez zwykłych użytkowników uprawnień globalnych.
- Jako administrator chcę mieć możliwość porównania uczestnika w zakończonych turniejach w uzasadnionym zakresie administracyjnym.
- Jako administrator chcę chronić dane źródłowe przed przypadkową ręczną edycją.

---

## 4. Functional Specification

### 4.1. Konta i dostęp

- rejestracja, logowanie, wylogowanie oraz bezpieczne odnawianie sesji;
- zmiana hasła dla każdego zalogowanego użytkownika;
- reset zapomnianego hasła przez e-mail;
- role wynikające z powiązania z konkretnym turniejem, a nie z globalnej etykiety „organizator”;
- brak dostępu gościa do roboczego API, aktywnych turniejów, historii rzutów i porównań;
- dostęp organizatora tylko do turniejów, które organizuje.

### 4.2. Przygotowanie turnieju

- tworzenie szkicu turnieju;
- konfiguracja liczby rund, wielkości stołów, wariantu punktacji, zapisów i opcjonalnego czasu decyzji;
- dodawanie wielu organizatorów;
- powiązanie zawodnika z wieloma turniejami bez duplikowania jego profilu;
- zapisy `ORGANIZER_ONLY` albo `OPEN`;
- konfigurowalny limit miejsc nieprzekraczający 128 aktywnych uczestników jednego turnieju;
- limit miejsc odporny na równoczesne zgłoszenia;
- wycofanie i ponowne dołączenie przed startem, jeśli nadal jest miejsce;
- zablokowanie zmian reguł wpływających na wynik po rozpoczęciu turnieju.

### 4.3. Rundy grupowe i przydział do stołów

- kilka rund bez eliminacji w podstawowej wersji;
- jedna rozgrywka uczestnika w każdej rundzie;
- nowy przydział do stołów w każdej rundzie;
- mechanizm rankingowy i wężykowy równomiernie rozkładający siłę uczestników;
- kontrolowana losowość pozostawiająca grupy nieprzewidywalne;
- preferowane unikanie wspólnego stołu członków tej samej drużyny;
- preferowane unikanie ponownych spotkań tych samych uczestników;
- wybór najlepszego możliwego przydziału, gdy wszystkich ograniczeń nie można spełnić;
- bariera uniemożliwiająca wygenerowanie następnej rundy przed zakończeniem wszystkich stołów.

### 4.4. Rozgrywka przy stole

- wspólny formularz punktacji dla całego stołu;
- możliwość działania wyłącznie we własnym polu i podczas własnej tury;
- rozpoczęcie każdej tury bez zatrzymanych kości;
- pierwszy rzut każdej tury obejmujący zawsze wszystkie pięć kości naraz;
- możliwość zatrzymywania kości dopiero po pierwszym rzucie;
- wybór zatrzymania przede wszystkim kliknięciem myszy albo dotknięciem,<br>po którym interfejs automatycznie przenosi kość do oznaczonego obszaru lub z powrotem;
- drugi i trzeci rzut obejmujący wyłącznie kości niezatrzymane, bez zmiany wartości kości zatrzymanych;
- maksymalnie trzy rzuty kośćmi w turze;
- wybór kości zatrzymywanych przed następnym rzutem;
- stałe położenie przycisku „Rzuć” oraz jego nieaktywny stan poza turą, <br>po
  trzecim rzucie, po wyborze kategorii i podczas obsługi żądania;
- jednoznaczny wybór kategorii przez kliknięcie, bez dodatkowego zatwierdzania;
- obowiązkowy wybór kategorii po ostatnim rzucie przed przejściem kolejki dalej;
- automatyczne wyliczanie punktów, wynikających z reguł premii, wartości
  ujemnych i sum;
- brak ręcznej edycji wartości wyliczanych przez system;
- brak rekomendacji kategorii, zatrzymań i opłacalności ruchu.

### 4.5. Równoległe stoły i nadzór

- niezależny przebieg stołów w tej samej rundzie;
- aktualizacja bieżącego stanu stołu bez przeładowania strony;
- zbiorczy panel wszystkich stołów dla organizatora;
- przełączenie na szczegół jednego stołu bez otwierania kolejnych kart;
- synchronizacja pełnego stanu po przerwaniu i odzyskaniu połączenia;
- w wersji 1.0 wgląd organizatora w każdą przyjętą i odrzuconą akcję uczestników<br>wraz z czasem serwera i przyczyną odmowy;
- w wersji 1.0 możliwość oznaczenia zdarzenia jako podejrzanego i rozpoczęcia audytowalnego wyjaśnienia;<br>decyzję o alarmie podejmuje człowiek, a system nie uznaje samodzielnie uczestnika za oszusta.

### 4.6. Ranking i zakończenie

- suma wyników z rund grupowych;
- podstawowe statystyki uczestnika: suma, średnia rundowa, najlepsza runda
  i liczba rozegranych rund;
- prezentowanie średniej razem z liczbą rund;
- jednoznaczne reguły rozstrzygania remisów;
- aktualizacja rankingu dopiero z kompletnych danych rundy;
- zakończenie turnieju po zamknięciu wszystkich wymaganych rozgrywek;
- zablokowanie rezultatów zakończonego turnieju przed zwykłą edycją;
- przeniesienie zakończonego turnieju z widoku aktywnych do historii.

W V2 statystyki drużyny obejmują łączną sumę punktów, średnią rundową drużyny,
średni dorobek punktowy na członka zatwierdzonego składu, historyczną liczebność
składu oraz liczbę faktycznie rozegranych wyników uczestnik–runda. Podstawową
miarą porównywania drużyn pomiędzy turniejami jest średnia rundowa drużyny.
Historyczny skład i wcześniejsze wyniki nie maleją po zakończeniu dalszego udziału
członka, a za rundy, których już nie rozegrał, nie powstają zera. Mediana
i odchylenie standardowe są wyłącznie późniejszą analityką uzupełniającą.

### 4.7. Historia i porównania

- zapis wartości każdego rzutu, zatrzymanych kości, kolejności i wybranej kategorii;
- możliwość ponownego wyliczenia wyniku z danych źródłowych;
- brak dostępu uczestnika do historii rzutów w czasie trwania turnieju;
- po zakończeniu turnieju dostęp uczestnika wyłącznie do własnej historii;
- nieedytowalny replay całej rozgrywki dla właściwego organizatora;
- porównanie jednego uczestnika pomiędzy maksymalnie czterema zakończonymi turniejami;
- tabela zbiorcza, szczegóły w ograniczonym układzie i jeden współdzielony modal;
- bezwzględne wykluczenie turniejów aktywnych i anulowanych z porównań;
- brak przekrojowej porównywarki po stronie uczestnika.

### 4.8. Widoki list i archiwum

- domyślny widok aktywnych turniejów;
- osobna lista zakończonych turniejów z najnowszymi na górze;
- na początku wyłącznie podstawowe informacje o turnieju;
- rozwijanie jednej wybranej rundy lub rozgrywki na żądanie;
- filtrowanie, sortowanie i stronicowanie po stronie systemu;
- świadome „Załaduj więcej” zamiast automatycznego infinite scrolla.

---

## 5. User Flow Specification

### 5.1. Główny przepływ organizatora

1. Organizator zakłada konto albo loguje się.
2. Tworzy szkic turnieju.
3. Ustala zasady, liczbę rund, wielkość stołów, sposób zapisów i limit miejsc.
4. Dodaje innych organizatorów i uczestników albo otwiera samodzielne zapisy.
5. Sprawdza kompletność konfiguracji i rozpoczyna turniej.
6. System tworzy pierwszą rundę i przydziela uczestników do stołów.
7. Organizator obserwuje wszystkie stoły w jednym panelu lub otwiera szczegół wybranego stołu.
8. Stoły kończą rozgrywki niezależnie od siebie.
9. Po zakończeniu wszystkich stołów system zamyka rundę i przelicza ranking.
10. Organizator generuje następną rundę z nowym przydziałem uczestników.
11. Kroki 7–10 powtarzają się do rozegrania skonfigurowanej liczby rund.
12. Organizator kończy turniej, a system blokuje rezultaty i przenosi wydarzenie do historii.
13. Organizator może odtworzyć rozgrywkę albo porównać wynik uczestnika z innymi zakończonymi turniejami.

### 5.2. Główny przepływ uczestnika

1. Uczestnik zakłada konto albo loguje się.
2. Dołącza do turnieju z otwartymi zapisami albo zostaje dodany przez organizatora.
3. Po rozpoczęciu rundy otwiera przypisany stół.
4. Obserwuje wspólny formularz i czeka na swoją kolej.
5. Gdy rozpoczyna się jego tura, wykonuje obowiązkowy pierwszy rzut wszystkimi pięcioma kośćmi naraz.
6. Dopiero po tym rzucie zatrzymuje wybrane kości i opcjonalnie wykonuje drugi oraz trzeci rzut obejmujący wyłącznie kości niezatrzymane.
7. Wybiera kategorię we własnym polu formularza.
8. System natychmiast wylicza i zapisuje punkty, po czym przekazuje kolejkę następnej osobie.
9. Po zakończeniu turnieju uczestnik może zobaczyć rezultat i wyłącznie własną historię.

### 5.3. Bariera pomiędzy rundami

1. Każdy stół samodzielnie przechodzi pomiędzy turami i kończy własną rozgrywkę.
2. Zakończony stół otrzymuje status oczekiwania i nie rozpoczyna następnej rundy.
3. Organizator nadal widzi stan pozostałych stołów.
4. Dopiero po ukończeniu wszystkich stołów system uznaje rundę za kompletną.
5. Ranking zostaje przeliczony ze wszystkich wyników.
6. Na jego podstawie może powstać kolejna runda i nowy skład stołów.

### 5.4. Zakończony formularz i replay

1. Po zakończeniu etapu wspólny formularz przestaje być aktywnym widokiem uczestników.
2. Uczestnik nie może przeglądać historii rzutów aż do zakończenia całego turnieju.
3. Organizator wybiera turniej, rundę, stół i rozgrywkę.
4. System otwiera formularz w trybie tylko do odczytu.
5. Organizator przechodzi przez kolejne rzuty, zatrzymania i wybór kategorii bez zmiany zapisanego wyniku.

### 5.5. Porównanie zakończonych turniejów

1. Organizator wybiera uczestnika.
2. System pokazuje tylko zakończone turnieje, do których organizator ma dostęp.
3. Organizator wybiera od jednego do czterech turniejów.
4. System przedstawia wyniki w jednej tabeli i ograniczonym układzie szczegółów.
5. Szczegóły konkretnej rozgrywki otwierają się w jednym współdzielonym modalu.
6. Próba użycia aktywnego lub anulowanego turnieju zostaje odrzucona niezależnie od sposobu wysłania żądania.

---

## 6. Non-Functional Requirements

### 6.1. Poprawność i integralność

- serwer jest jedynym źródłem prawdy o stanie turnieju;
- każda zaakceptowana akcja ma jednoznaczny skutek;
- dwukrotne kliknięcie lub ponowienie żądania nie może utworzyć dwóch rzutów;
- wynik musi być możliwy do ponownego wyliczenia z danych źródłowych;
- kolejna runda nie może korzystać z niekompletnego rankingu;
- konfiguracja wpływająca na wynik jest niezmienna po rozpoczęciu turnieju.

### 6.2. Bezpieczeństwo i prywatność

- dostęp wynika z konta i relacji z konkretnym turniejem;
- gość nie otrzymuje danych roboczych ani dokumentacji operacyjnego API;
- uczestnik nie może wykonać akcji w imieniu innej osoby;
- uczestnik nie może odczytać cudzej historii przez zmianę adresu lub identyfikatora;
- dane aktywnego turnieju nie są dostępne w porównaniach;
- hasła i sesje korzystają ze standardowych, bezpiecznych mechanizmów;
- komunikat resetu hasła nie ujawnia, czy adres istnieje w systemie;
- logi nie przechowują haseł, tokenów ani zbędnych danych osobowych;
- dane anulowanego turnieju w wersji 1.0 są przechowywane przez 30 dni na potrzeby sporów,<br>a następnie trwale usuwane z pozostawieniem wyłącznie anonimowego podsumowania;<br>czasowe przedłużenie wymaga udokumentowanego, nierozstrzygniętego sporu.

### 6.3. Niezawodność i współbieżność

- kilka stołów może wykonywać akcje równolegle bez wzajemnego blokowania;
- jedno ostatnie miejsce w zapisach może otrzymać tylko jedna osoba;
- chwilowa utrata aktualizacji na żywo nie może zmienić stanu turnieju;
- po ponownym połączeniu klient odzyskuje pełny stan;
- awaria animacji lub interfejsu nie wpływa na wartości kości ani punktację.

### 6.4. Wydajność i czytelność

- akcje przy stole powinny dawać szybką, jednoznaczną informację zwrotną;
- interfejs obejmuje czytelne warianty dla desktopu lub laptopa, tabletu
  i telefonu,<br>bez narzucania w planie dokładnych breakpointów;
- panel wielu stołów powinien pozostać czytelny na typowym laptopie lub tablecie;
- działanie aktywnego turnieju jest planowane dla maksymalnie 128 uczestników;<br>większa skala wymaga ponownego pomiaru i decyzji architektonicznej;
- historia i archiwum są pobierane porcjami;
- jeden ekran nie otwiera nieograniczonej liczby modali ani kart;
- optymalizacje powstają na podstawie pomiaru, a nie przewidywania problemów bez danych.

### 6.5. Dostępność

- podstawowymi sposobami obsługi interfejsu MVP są mysz i dotyk; nie powstaje
  własny system skrótów klawiaturowych,<br>natomiast semantyczne kontrolki zachowują
  standardową obsługę przez `Tab`, `Enter` i spację;
- kliknięcie albo dotknięcie kości automatycznie przenosi ją do strefy zatrzymań lub z powrotem; przeciąganie nie jest wymagane;
- kolor, animacja i dźwięk nie są jedynym nośnikiem informacji;
- interfejs respektuje ograniczenie animacji ustawione przez użytkownika;
- fokus pozostaje przewidywalny po aktualizacji widoku i podczas używania modala.

### 6.6. Utrzymywalność i jakość

- funkcje są rozwijane jako kompletne pionowe przekroje, a nie jako zbiór niepołączonych ekranów;
- najważniejsze zasady gry, dostępu i współbieżności mają testy automatyczne;
- projekt ma powtarzalny sposób uruchomienia i scenariusz demonstracyjny;
- publiczny kontrakt systemu i decyzje biznesowe są udokumentowane.

---

## 7. Domain Model (Conceptual)

### 7.1. Główne pojęcia biznesowe

Pojęcia dzielą się na dwa obszary. Turniejowy obejmuje wydarzenie, udział,
drużyny, rundy, grupy, stoły, ranking i awans. Kościany obejmuje rozgrywkę,
turę, rzut, zatrzymania, kategorię i wynik formularza. Stół łączy oba obszary:
otrzymuje skład z turnieju i zwraca wynik gry, ale nie przenosi reguł punktacji
do klasyfikacji ani reguł awansu do silnika kości.

- **Konto użytkownika** — neutralna tożsamość w systemie; samo konto nie oznacza organizatora.
- **Profil zawodnika** — dane osoby biorącej udział w turniejach.
- **Turniej** — wydarzenie posiadające organizatorów, uczestników, konfigurację, status i wynik końcowy.
- **Organizator turnieju** — powiązanie konta z konkretnym turniejem i zakresem uprawnień.
- **Udział w turnieju** — powiązanie zawodnika z turniejem; pozwala jednej osobie uczestniczyć w wielu wydarzeniach.
- **Runda** — część fazy grupowej obejmująca komplet równoległych stołów.
- **Stół / rozgrywka** — jedna pełna gra przypisana do rundy i określonego zestawu uczestników.
- **Uczestnik stołu** — przypisanie zawodnika do konkretnej rozgrywki oraz jego miejsce w kolejności.
- **Tura** — decyzje jednego uczestnika zakończone wyborem kategorii.
- **Rzut** — wartości kości oraz stan zatrzymań w konkretnym kroku tury.

### 7.2. Najważniejsze zależności

- jedno konto może organizować wiele turniejów, a turniej może mieć wielu organizatorów;
- jeden profil zawodnika może uczestniczyć w wielu turniejach, a turniej ma wielu zawodników;
- turniej składa się z wielu rund;
- runda składa się z wielu działających równolegle stołów;
- zawodnik może być przypisywany do innego stołu w każdej rundzie;
- rozgrywka składa się z uporządkowanych tur uczestników;
- tura zawiera od jednego do trzech rzutów i dokładnie jeden końcowy wybór kategorii;
- ranking i porównania są wyliczane ze źródłowych wyników, a nie przechowywane jako niezależna prawda.

### 7.3. Cykl życia turnieju

W MVP:

```text
Szkic → Zapisy → Aktywny → Zakończony
```

Od wersji 1.0 dochodzą archiwizacja oraz kontrolowane anulowanie. Zakończony turniej zachowuje pełną historię jako rezultat produktu. Anulowany turniej nie ma zwycięzcy, nie trafia do porównań i po okresie przeznaczonym na wyjaśnienia traci szczegółowe dane.

### 7.4. Rozszerzenia modelu

Wersja 1.0 dodaje formalne etapy, grupy, mecze fazy pucharowej oraz historię zdarzeń potrzebną do alarmów i korekt. V2 dodaje trwałą tożsamość drużyny oraz jej historyczne składy, gdy pojawia się rzeczywista potrzeba porównań drużynowych.

---

## 8. Implementation Roadmap

Roadmapa jest uporządkowana według wartości użytkowej. Każdy etap powinien zakończyć się działającym przepływem, testami kluczowych reguł i możliwością zaprezentowania rezultatu.

### 8.1. MVP (Core Value: Complete Group Tournament)

Cel: sprawdzić, czy system pozwala sprawnie i poprawnie przeprowadzić pełny wielorundowy turniej grupowy przy kilku równoległych stołach.

- konta, logowanie, zmiana hasła i reset e-mailowy;
- tworzenie i konfiguracja turnieju;
- wielu organizatorów oraz relacja uczestnik–turniej;
- zapisy zarządzane i otwarte z limitem miejsc;
- kilka rund grupowych z nowym przydziałem do stołów;
- mechanizm wężykowy, kontrolowana losowość i ograniczanie ponownych spotkań;
- pełna tura: rzuty, zatrzymania, wybór kategorii i automatyczna punktacja;
- równoległe stoły oraz aktualizowany na żywo panel organizatora;
- bariera przed wygenerowaniem następnej rundy;
- ranking końcowy bez fazy pucharowej;
- źródłowa historia rzutów i replay organizatora;
- własna historia uczestnika dostępna dopiero po zakończeniu turnieju;
- porównanie jednego uczestnika pomiędzy maksymalnie czterema zakończonymi turniejami;
- podstawowe narzędzia administratora, dokumentacja systemu, testy i powtarzalne uruchomienie.

MVP nie obejmuje fazy pucharowej, pełnego audytu, anulowania z retencją, trwałych drużyn, publicznych wyników, zaawansowanych wykresów ani osobnego klienta desktopowego.

### 8.2. V1 (Full Tournament + Audit)

Cel: rozszerzyć sprawdzony rdzeń o pełny, wieloetapowy przebieg turnieju i formalną obsługę sytuacji wyjątkowych.

- niezmienny, wersjonowany zestaw reguł;
- formalne etapy i grupy;
- kwalifikacja z rankingu do fazy pucharowej;
- drabinka, mecze i przekazywanie zwycięzców;
- alarmy organizatora oraz audytowalny obieg wyjaśnień;
- kontrolowane korekty bez nadpisywania historii;
- status anulowania z obowiązkowym powodem;
- 30-dniowa retencja szczegółów anulowanego turnieju, kontrolowane przedłużenie wyłącznie dla sporu i późniejsze trwałe usunięcie;
- odporniejsza obsługa połączeń czasu rzeczywistego;
- dopracowany interfejs, animacje 2D i responsywny dashboard;
- eksport, wykres postępu, rozbudowane archiwum i opcjonalna publikacja końcowych wyników.

### 8.3. V2 (Team Analytics + Additional Clients)

Cel: rozbudować produkt dopiero po potwierdzeniu użyteczności podstawowego przebiegu i zebraniu rzeczywistych potrzeb użytkowników.

- trwałe drużyny i historyczne składy;
- porównywanie drużyn pomiędzy zakończonymi turniejami;
- zaawansowane statystyki rzutów, zatrzymań i kategorii;
- analiza skuteczności decyzji bez udzielania podpowiedzi podczas gry;
- dodatkowa metoda logowania oparta na passkeys/WebAuthn;
- opcjonalny klient desktopowy Pygame korzystający z tego samego systemu;
- opcjonalna wizualizacja kości 3D w kliencie webowym;
- ulepszanie mechanizmu przydziału do stołów na podstawie testów i rzeczywistych turniejów,<br>jeżeli obecny algorytm zbyt często powtarza spotkania albo łączy członków tej samej drużyny;
- ewentualny osobny frontend, jeżeli złożoność produktu uzasadni jego utrzymanie.

### 8.4. Poza zakresem bez nowego uzasadnienia biznesowego

- podejmowanie decyzji strategicznych przez AI;
- rekomendowanie uczestnikowi ruchów podczas turnieju;
- SMS jako podstawowa metoda odzyskiwania dostępu;
- pełna praca offline z niezależnym stanem na każdym urządzeniu;
- automatyczny infinite scroll;
- nieograniczona liczba jednocześnie otwartych porównań, modali lub kart;
- technologie dodawane wyłącznie po to, aby zwiększyć ich liczbę w projekcie.

---

## 9. Udział, drużyny i przebieg

### 9.1. Drużyna, grupa i stół

- **Drużyna** to dobrowolny skład uczestników zatwierdzony dla danego turnieju
  i wykorzystywany w klasyfikacji drużynowej.
- **Skład turniejowy** to osoby reprezentujące drużynę w jednym turnieju.
- **Grupa** to tymczasowy przydział uczestników w jednej rundzie.
- **Stół** to miejsce rozegrania gry przez grupę.

W interfejsie stół otrzymuje prosty numer porządkowy, np. `Stół #1`. Uczestnik
nie nadaje mu własnej nazwy ani nie wybiera go samodzielnie.

Uczestnicy drużyny nie tworzą automatycznie grupy i nie wybierają stołu.

### 9.2. Zapisy i skład

Samodzielny zapis pozwala wyłącznie zgłosić własny udział. Uczestnik nie może
przez formularz, API ani `join` ustawić numeru startowego, rozstawienia, drużyny,
koszyka, grupy ani stołu. Pola są nieobecne w kontrakcie albo odrzucane. Numer
startowy i rozstawienie ustala organizator, grupę i stół wyznacza backend,
a zgłoszony przed turniejem skład drużyny organizator zatwierdza.

Drużyna może mieć dowolną liczebność. Organizator zatwierdza jej skład przed
`ACTIVE`. Po starcie skład jest historyczną migawką; zmiana wymaga formalnej,
audytowanej interwencji.

### 9.3. Przydział do grup

Algorytm najpierw tworzy możliwie równe stoły po 2–6 osób, z różnicą liczebności
nieprzekraczającą jednej. Następnie **ogranicza**, lecz nie obiecuje zawsze
wyeliminować, powtórne spotkania<br>i wspólne stoły członków drużyny.

Po bazowym wężyku algorytm wybiera ograniczone korekty zmniejszające ważony koszt
konfliktów. W pierwszej kolejności działa wewnątrz koszyka. Jeżeli istotnego
konfliktu nie da się ograniczyć lokalnie, porównanie lub zamiana może objąć
wyłącznie koszyk bezpośrednio sąsiedni. Poszukiwanie nie przechodzi kaskadowo
do dalszych koszyków. Gdy nadal nie istnieje układ bez konfliktu, pozostaje
najlepszy deterministycznie rozstrzygnięty wariant.

### 9.4. `Team` i `TournamentTeam`

W V2 `Team` jest trwałą tożsamością drużyny, a `TournamentTeam` jej udziałem
i historycznym składem w jednym turnieju:

```text
Team 1 ─── N TournamentTeam N ─── 1 Tournament
                         │
                         └── uczestnicy składu turniejowego
```

Zmiana bieżącej nazwy lub członków `Team` nie przepisuje historii.
Porównanie po `Team.id` obejmuje zakończone turnieje, a każdy wiersz oznacza
jeden `TournamentTeam`.

Zatwierdzony skład jest historyczną migawką. Wycofanie, zakończenie udziału lub
dyskwalifikacja nie usuwa członka z `TournamentTeam` i nie zmniejsza historycznej
liczebności. Osobno pokazywana jest liczba osób nadal grających. Dotychczasowe
wyniki pozostają, a za późniejsze nierozgrywane rundy nie dopisuje się zer.

Podstawową miarą porównania drużyn pomiędzy turniejami jest **średnia rundowa
drużyny**: suma punktów podzielona przez liczbę faktycznie rozegranych wyników
uczestnik–runda. Uzupełniający **średni dorobek punktowy na członka zatwierdzonego
składu** dzieli tę samą sumę przez historyczną liczebność zatwierdzonego składu.
Obok obu miar widoczne są ich mianowniki, łączna suma i historyczny skład.

### 9.5. Tożsamość uczestnika i listy

System przechowuje pełne imię i nazwisko. `nickname` jest odrębnym, dowolnym
pseudonimem. Przy zapisie powstaje migawka tożsamości turniejowej; po starcie
replay, ranking i historia korzystają z niej. Skracanie nazwy jest dozwolone
tylko w określonym widoku prezentacyjnym.

Kafel turnieju pokazuje nazwę, status, organizatorów, liczbę uczestników oraz opcjonalnie drużyn.
Po rozwinięciu uczestnicy są grupowani według składów, a osoby bez drużyny są wyświetlane osobno,
w sekcji **„Udział indywidualny”**. Przed dołączeniem do otwartych zapisów widoczna jest tylko liczebność i wolne miejsca.


### 9.6. Remis, dogrywka i losowanie

Przy równej sumie procedura porównania — nie dogrywka — zestawia najlepszy,
drugi najlepszy i kolejne wyniki rund po posortowaniu malejąco. Nieistotne
miejsce może pozostać ex aequo. Gdy remis wpływa na zwycięstwo, awans lub
rozstawienie, dogrywkę grają wyłącznie nadal remisujący, z równą liczbą tur.

Dogrywki powtarza się do rozstrzygnięcia. Losowanie jest jawną, audytowaną
komendą organizatora i ostatecznością, gdy dalsza dogrywka jest niemożliwa.

### 9.7. Historia, audyt i czas

Historia/replay zawiera przyjęte fakty gry. Audyt zawiera również odrzucone
próby, działania organizatora, zmiany statusów i uzasadnienia. Czas audytu jest
rzeczywistym czasem zegarowym, nie czasem od początku turnieju. Backend zapisuje
UTC, a UI pokazuje czas w jawnej strefie turnieju.

### 9.8. Rozłączenie

Krótkie zerwanie uruchamia tolerancję i reconnect. Potem uczestnik ma stan
`disconnected`, a organizator alert; nie ma automatycznego wyrzucenia. Powrót
przywraca oficjalny stół i najnowszy stan bez resetowania czasu decyzji.
Wycofanie lub dyskwalifikacja są osobną, audytowaną decyzją. Uczestnictwo
i historia pozostają w bazie, choć szansa dalszej gry może przepaść.<br>Ogólna
awaria wydarzenia nie jest winą pojedynczego uczestnika.
