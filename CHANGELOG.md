# Verze

Číslo verze: soubor `VERSION` (hlídač), `WEB_VER` / `FLIP_VER` ve `web/index.html`, `versionName` v `android/app/build.gradle`.
Každá změna = +0.1. Aplikace pro Flip dostane nové číslo jen, když se mění její kód (FLIP_VER pak ukazuje, co je nejnovější).

## 3.9 – 13. 10. 2026
- **Ciferník Chata 1.9 + hodinky 1.6:** horní řádek bere jen komplikaci slunce z aplikace Chata (ikonka podle toho, co přijde); aplikace na hodinkách ukazuje svou verzi
- **Ciferník Chata 1.8:** horní řádek (slunce) se už nepřekrývá s levým subdialem – v editoru se dají spolehlivě vybrat
- **Ciferník Chata 1.7 + hodinky 1.5:** teplota z vlastní komplikace „Chata – teplota venku“ (Open-Meteo, poloha hodinek, jinak chata) – počasí systému na Xiaomi nefungovalo; ikonky východu/západu jsou přímo v ciferníku (obrázek z komplikace se nezobrazoval)
- **Ciferník Chata 1.6 + hodinky 1.4:** u východu/západu ikonka slunce na obzoru s výraznou šipkou (nahoru/dolů) místo šipky v textu (pletla se s jedničkou)
- **Ciferník Chata 1.5:** v úsporném režimu stejný ciferník (bez černého podkladu), jen bez vteřinovky
- **Ciferník Chata 1.4:** realističtější vzhled – tmavší modrý sunburst se světlými a tmavými výsečemi, zapuštěné subdialy s leštěnou obrubou a vrženým stínem, kovové hodinové číslice (kromě míst se subdialy), odlesk sklíčka pod 45° středem, výraznější vteřinovka, široké „zploštělé“ písmo Saira Expanded
- **Ciferník Chata 1.3:** tři větší symetrické subdialy s trojúhelníkem po obvodu a velkým číslem, ikonky místo nápisů, den (PO) a datum rovně pod horními subdialy, nahoře jen nejbližší východ/západ, hodinové čárky na vnějším věnci, diagonální odlesk sklíčka; napětí na 1 desetinné místo
- **Hodinky 1.3:** otevřením aplikace Chata na hodinkách se hned obnoví komplikace (napětí, slunce) i dlaždice
- **Hodinky 1.2:** komplikace slunce ukazuje jen nejbližší událost, obnova každých 10 min
- **Ciferník Chata 1.2:** všechno písmo zhruba 2× větší, datum po obvodu nahoře místo číslic 11–12–1, subdialy bez drobných čísel stupnice
- **Ciferník Chata 1.1:** oprava – hodinky ho odmítaly (náhradní typ komplikace musí být mezi podporovanými)
- **Ciferník Chata** pro hodinky (Watch Face Format): analogový letecký styl, subdialy napětí chaty / baterie hodinek / teplota, datum po obvodu, východ a západ slunce, úsporný režim
- **Hodinky 1.1:** nová komplikace „východ / západ slunce“; napětí v ukazateli na 2 desetinná místa
- Hlídač posílá hodinkám polohu chaty

## 3.8 – 13. 10. 2026
- **Kabely a spoje**: porovnání napětí regulátoru a měniče → odhad odporu kabelů a spojů. Při zvýšené ztrátě karta na hlavní stránce (regulátor pak baterii nedobíjí).
- Ťuknutím **návod krok za krokem**: schéma s měřicími body, políčka pro naměřená napětí s okamžitým vyhodnocením, hledání špatného spoje, oprava, ověření. Odškrtávání kroků.

## 3.7 – 13. 10. 2026
- Nová dlaždice **Bilance teď** nahoře přes celou šířku: kolik opravdu jde do baterie / z baterie (i s odběrem měniče, který regulátor nevidí). Když regulátor hlásí Float/Boost, ale baterie se vybíjí, napíše to na rovinu. Ťuknutím graf bilance za den s režimy regulátoru a napětí.

## 3.6 – 13. 10. 2026
- Automatika River: vypnout hned, když se baterie vybíjí (čistý proud pod −2 A) nebo ve Float napětí klesne pod ~13,3 V; po neúspěšném pokusu delší pauza (20 → 40 → 80 → 120 min)
- Štítek stavu: „Vybíjí se · Float/Boost“, když regulátor hlásí Float/Boost, ale baterie se vybíjí (už ne „Nabito“)
- Dlaždice Nabití: vysvětlení, že regulátor při odběru ukazuje méně

## 3.5 – 13. 10. 2026
- **Flip 1.2:** oprava čtení Victronu na pozadí – filtr skenu „výrobce Victron + první bajt 0x10“ (prázdný filtr Samsung nepřijal, takže na pozadí nic nechodilo, i když Test Bluetooth fungoval)
- **Flip 1.2:** přesné budíky po 10 min i v úsporném režimu (dřív Android běh natahoval na ~17 min)

## 3.4 – 13. 10. 2026
- Notifikace: ťuknutí otevře zprávu v ntfy, přehled je tlačítko „Přehled“ pod notifikací

## 3.3 – 13. 10. 2026
- Upozornění na odběr z baterie jen při odběru NAVÍC nad běžný (lednice + světla, kamery, wifi) ≥ 40 W; kvůli běžnému odběru (zašlé slunce) nepřijde

## 3.2 – 13. 10. 2026
- Oprava: přechod Boost → Float (pokles na ~13,7 V) už River nevypíná jako „regulátor neudrží napětí“
- Nové upozornění „⚡ Odběr X W – bere se z baterie“: přes den chata bere víc, než panely dají (čistý proud do baterie pod −2 A)
- Spotřebováno dnes: velké číslo = vše za měničem (jako zásuvka), rozpad lednice · běžný odběr · navíc (nabíjení, River)
- Stav River na hlavní stránce: kdy znovu zkusí a proč se naposledy vypnula; Float text bez rozporu

## 3.1 – 13. 10. 2026
- Dokumentace: Návod (docs/navod.md), Technická dokumentace (docs/technicka.md) a Historie změn – v aplikaci přes „📖 Návod“ dole na stránce (vlastní převod Markdownu, bez cizích knihoven)
- Notifikace „🔋 Baterie nabitá (Float)“ místo „na 100 %“

## 3.0 – 13. 10. 2026
- Graf výkonu panelů (detail dlaždice i sekce Grafy): barevné pozadí podle režimu nabíjení (Boost / Float / vyrovnávací), režim i v bublině

## 2.9 – 13. 10. 2026
- Dlaždice na hlavní stránce otevřou graf (Dnes / Týden): nabití + napětí, panely + proud z regulátoru, výroba po hodinách + přírůstek, spotřeba + přírůstek
- Oprava hlavičky oken (Nastavení, zásuvka, graf) – křížek vedle nadpisu

## 2.8 – 13. 10. 2026
- Automatika River: zapnout po 1 měření, pauza po vypnutí 20 min, zapnutí/vypnutí potichu (Deník + souhrn; notifikace volitelně)

## 2.7 – 13. 10. 2026
- Automatika River i v Boostu: zapnout, když regulátor drží nabíjecí napětí (s teplotní kompenzací), vypnout hned, když ho neudrží (River by brala z baterie)
- Hlavní stránka: proud z regulátoru a čistý proud do baterie (po odečtení měniče)

## 2.6 – 13. 10. 2026
- Automatika River: priorita solární baterie – vypnout hned, když napětí spadne pod 13,0 V (baterie se vybíjí); slabé panely stačí jedno čerstvé měření po přepnutí; bez 30min tolerance

## 2.5 – 13. 10. 2026
- Oprava automatiky River: ve Float regulátor škrtí panely, takže zapnutí už nečeká na 150 W; zapne se ve Float (2 kontroly) 1 h po východu až 2 h před západem, po zapnutí 30 min tolerance, vypnutí při slabém slunci / poklesu napětí, pak 1 h pauza
- Hlavní stránka: režim nabíjení (Boost / Float / vyrovnávací)

## 2.4 – 13. 10. 2026
- Procenta jen z regulátoru (dlaždice Nabití, hodinky); všude jinde napětí: předpověď do rána, výhled, zimní doporučení, notifikace, souhrn
- Zimní prahy připojení solární baterie ve voltech (zima_pripojit_od_V / do_V)

## 2.3 – 13. 10. 2026
- Kalibrace napětí → % na Petrovu baterii (plná = klidové napětí večer po dni ve Float), používá odhad nabití, předpověď do rána, výhled
- Výhled: pod sloupci očekávané napětí ráno (léto) / večer (zima) místo procent
- Popisky: „z baterie i se ztrátami měniče“, „Victron (Bluetooth): nic nepřichází“

## 2.2 – 13. 10. 2026
- Hodinky (Wear OS, Xiaomi Watch 5): nová aplikace `hodinky/` – komplikace s napětím baterie a dlaždice se základními údaji; hlídač posílá shrnutí do ntfy `<téma>-hodinky`

## 2.1 – 13. 10. 2026
- Spotřeba chaty = lednice + ostatní (světla, kamery, wifi), bez nabíjení River přebytkem; popisek výhledu odlišuje spotřebu chaty a potřebnou výrobu (vč. ztrát)
- Dlaždice Spotřebováno dnes: nabíjení River zvlášť

## 2.0 – 12. 10. 2026
- Zdraví baterie: verdikt jen z nočních měření nad 12,1 V (hlubší vybití nadsazuje), nabíjecí metoda jen orientačně (Float ≠ plná → podhodnocuje); přepočet
- Kapacita z noci nezávislá na nastavení (~10400 / mV na 10 Ah)
- Předpověď do rána, výhled a odhad nabití počítají se skutečnou (naměřenou) kapacitou, ne s 200 Ah

## 1.9 – 12. 10. 2026
- Panely: hranice podle skutečného chování pojistky – přidat 2. panel do 100 % (30 A), radit odpojení nad 115 %, okamžité varování nad 110 %; na webu „nejvíc naměřeno se 2 panely – pojistka vydržela“

## 1.8 – 12. 10. 2026
- Web: hlavní obrazovka (baterie, odběr, dlaždice, počasí) + rozbalovací sekce Zásuvky, Panely, Zdraví baterie, Grafy, Deník, Tabulka s jednořádkovým shrnutím; pamatuje si otevřené sekce
- Panely: sekce se zobrazí i bez předpovědi počasí; když chybí naměřené proudy, napíše to

## 1.7 – 12. 10. 2026
- Oprava: planý poplach „odpoj druhý panel“ – proud dvou panelů se bere ze dnů, kdy opravdu jely 2 panely (dřív dělení odhadnutým počtem a násobení 2 → dvojnásobek); chybné hodnoty > 45 A pryč
- „Odpoj panel“ až nad 95 % pojistky; web ukazuje, ze kterých dnů výpočet vychází

## 1.6 – 12. 10. 2026
- Panely 1/2 a pojistka 30 A: denní špička nabíjecího proudu (i z historie), rozpoznání počtu panelů v minulých letech, nejhorší případ podle roční doby
- Doporučení: přidat druhý panel (jen když jeden nestačí a dva jsou bezpečné do jara), počkat, odpojit s předstihem na jaře; okamžité varování při proudu ≥ 90 % pojistky
- Předpověď výroby počítá s počtem zapojených panelů
- Web: sekce Panely v kartě Počasí, nastavení Panely a pojistka

## 1.5 – 12. 10. 2026
- Předpověď výroby podle počasí (Open-Meteo): model difúzní + přímé záření po ročních obdobích, učí se z historie (archiv počasí), vynechává přiškrcené dny (Float), zpětná vazba předpověď → skutečnost → oprava
- Letní / zimní provoz (automaticky podle měniče a River, nebo ručně); v zimě „kdy připojit solární baterii“, upozornění den předem; upozornění na přechod sezón
- Vlastní odhad stavu nabití (počítání Ah + klidové napětí v noci + Float)
- Ostatní odběr za měničem (světla, kamery, wifi) + upozornění na změnu v noci
- Hluboká vybití pod 12,0 / 11,8 V po měsících
- Web: karta Počasí a výroba, řádek Ostatní v zásuvkách, nové nastavení

## 1.4 – 12. 10. 2026
- Web: dlaždice „Spotřebováno dnes“ (výstup měniče, odběr ze solární baterie vč. ztrát, River); proud baterie přesunut pod „Panely teď“

## 1.3 – 12. 10. 2026
- Web: jedna karta „Zdraví baterie“ – verdikt slovy (dobrá / opotřebovaná / slabá / vyměnit), zbývající Ah a %, posledních 14 dní, srovnání s loňskem / začátkem sledování
- Graf: medián po týdnech / měsících s barevnými pásmy místo jednotlivých teček; poslední měření rozepsaná slovy

## 1.2 – 12. 10. 2026
- Kapacita baterie z nabíjení do plna (Ah od rána do Float, odečtený odběr měniče), i zpětně z historie Solar Guardianu
- Web: graf „Kapacita baterie – odhad“ (noc vs. nabíjení, jmenovitá kapacita)
- Flip beze změny (1.1)

## 1.1 – 12. 10. 2026
- Večerní souhrn s deníkem (automatika, upozornění, chyby, spolehlivost), Deník událostí na webu
- Ověření, že zásuvka River povel provedla
- Web: nadpis velkými písmeny, číslo verze, kontrola verzí (web · hlídač · Flip), sevřenější horní karta
- Flip: posílá svou verzi, verze v nadpisu aplikace

## 1.0 – do 12. 10. 2026
- Vše předchozí (hlídač, web, brána na Flipu, zdraví baterie, automatika River)
