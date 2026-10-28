# Chata – elektřina: návod

Tenhle návod popisuje, co aplikace ukazuje, co znamenají čísla a barvy, jaké chodí upozornění a co s nimi dělat.
Technické podrobnosti (jak to funguje uvnitř) jsou v **Technické dokumentaci**, změny v **Historii změn**.

---

## 1. Jak to celé funguje (v kostce)

- **Regulátor EPEVER** posílá data do cloudu **Solar Guardian** (napětí, proud, výkon panelů, režim nabíjení).
- **Telefon Flip na chatě** (aplikace *Chata brána*) čte zásuvky **Tapo**, měnič **Victron** přes Bluetooth a stav své baterie. Každých 10 minut to pošle dál a provádí povely pro zásuvky (nabíjení River).
- **Hlídač** běží každých 10 minut na GitHubu. Stáhne data, uloží historii, vyhodnotí upozornění, řídí automatiku River, počítá předpovědi a zveřejní tuhle stránku.
- **Upozornění** chodí přes aplikaci **ntfy** do telefonu (a na hodinky). Ťuknutím na notifikaci se otevře zpráva v ntfy, tlačítkem **Přehled** pod ní tahle stránka.
- **Hodinky** (Wear OS) ukazují napětí na ciferníku a základní údaje na dlaždici.

Data jsou zašifrovaná heslem. Bez něj je nikdo nepřečte.

---

## 2. Hlavní obrazovka

**Hlavní stránka = verdikt + dlaždice** (od verze 3.11). Podrobnosti, grafy a vysvětlení jsou až po ťuknutí na dlaždici.
- **Verdikt nahoře**: zeleně *Všechno v pořádku*, oranžově/červeně *1 věc k řešení* a co udělat. Pod ním drobně, co je potřeba řešit **dlouhodobě**. Ťuknutím se otevře detail té věci.
- **Teď** – věci, na které se reaguje hned (problémové jsou vždy první):
  - 🔋 **Baterie teď**: napětí a skutečný proud do/z baterie (i s odběrem měniče). Vybíjí se kvůli odběru navíc → *vypni nabíjení zařízení*. Detail: velká karta baterie, bilance, grafy.
  - 🔌 **River – napájí chatu** (jen když chatu napájí River): kolik má %, na jak dlouho vydrží při průměrném odběru za 3 h, jestli vydrží do zítřejšího rána a s kolika %. Kapacita, rezerva v Nastavení.
  - 🌙 **Noc z dneška na zítřek** (po půlnoci do východu **Noc ze včerejška na dnešek (běží)**): napětí „V zítra ráno“ (resp. „V dnes ráno“). Přes den odhad podle počasí a spotřeby, po dnešním západu přesná předpověď. Obojí s opravou z minulých nocí.
  - **Pravidlo pro čas:** slova ráno / noc / večer / den jsou v aplikaci, notifikacích i na hodinkách vždy s *dnes / zítra / včera* (dnešní / zítřejší / včerejší) – nikdy samotná.
  - ⚡ **Dnes**: ráno předpověď výroby, přes den vyrobeno zatím / předpověď, po západu výsledek dne a bilance. Spotřeba je vždy od půlnoci.
  - ☀️ **Zítra**: výroba podle počasí a jestli dobije. Detail: předpověď na 7 dní.
  - 🔌 **River**: automatika nabíjení přebytkem. Detail: River a zásuvky Tapo.
- **Uplynulé** (jen informace, nepočítá se do „věcí k řešení“):
  - 🔎 **Proč je ranní minimum takové** (v detailu obou nocí): posledních 5 nocí proti starším – nabití přes den, odběr přes noc, lednice, délka noci, teplota; tabulka po nocích. Sloupec „Ah z bat. přes noc“ se u poslední noci objeví až další den (Brána posílá spotřebu zásuvky za měničem za celé dny).
  - 🌘 **Noc ze včerejška na dnešek** (minulá noc): včera večer → nejníž → dnes ráno, kolik se odebralo, předpověď vs skutečnost a oprava pro další noci (detail: graf noci, posledních 10 nocí, jak se předpověď učí).
  - 📅 **Včera**: vyrobeno vs předpověď, spotřeba, bilance, oprava předpovědi výroby (detail: posledních 14 dní).
- **Dlouhodobě** – menší dlaždice dole: 🔧 kabely a spoje (otevře návod na měření), ❤️ zdraví baterie, 🔆 panely, 📡 systém (co posílá data + deník).
- Barevný proužek vlevo: **zelená** v pořádku, **oranžová** pozor, **červená** řešit hned, šedá = zatím bez dat.
- **Každá dlaždice má svůj detail** jen s tím, co k ní patří – vždy nejdřív čísla a grafy, vysvětlení až pod nimi:
  - 🔋 Baterie teď: stav a doporučení, tok do/z baterie, panely, regulátor, odběr chaty, nabití podle regulátoru; grafy bilance, napětí, výkonu panelů a odběru (Dnes / 48 h / Týden); **Rok / Vše**: nejnižší a nejvyšší napětí dne a výroba po měsících za rok nebo celou historii.
  - **Zvětšení grafu prsty** (v každém grafu, i bez celé obrazovky): dva prsty od sebe = podrobnější čas, jeden prst do strany = posun (když je zvětšeno), dvojité ťuknutí = zpět. Ťuknutí na nadpis ⤢ = graf přes celou obrazovku. Nová verze webu se načte sama (do pár minut).
- 🌙 Noc: předpověď do rána, noční odběr, kapacita, hranice upozornění; graf napětí za 48 h a nejnižší napětí dne za 30 dní.
  - ⚡ Dnes (+ výroba po dnech / měsících / letech): účetnictví energie – výroba; spotřeba za měničem (lednice + běžný odběr + navíc); ztráty (převod v měniči ~12 %, vlastní spotřeba měniče, ~10 % při nabíjení AGM); bilance = výroba − nabíjení − odběr z baterie; výroba po hodinách / dnech, odběr za měničem, výroba za 30 dní, tabulka po dnech.
  - ☀️ Zítra = počasí a výroba na 7 dní · 🔌 River = automatika, baterie River a zásuvky · ❤️ / 🔆 / 📡 = zdraví baterie / panely / systém a deník · 🔧 = návod na proměření spojů.
- Dole: Návod · Deník · **🗂 Všechny údaje** (kompletní původní přehled – nic se neztratilo; fialově označené NEPOUŽITO = zatím není na žádné dlaždici) · Nastavení.

Následující popis platí pro obsah **detailů** (původní části stránky):

### Nahoře
- **CHATA – ELEKTŘINA v3.19**: číslo verze webu. Úplně dole je řádek *Verze: web · hlídač · Flip*. Když je něco červeně, je potřeba aktualizovat (typicky aplikaci na Flipu).
- **Data z regulátoru před X min**: jak čerstvá jsou data. Nad 2 hodiny se zobrazí varování.
- **⚡ Načíst**: spustí hlídače hned (jinak běží každých 10 min). Za ~2 minuty jsou nová data.
- **↻** obnoví stránku, **⚙** otevře Nastavení.

### Karta Solární baterie
- **Velké číslo**: napětí baterie.
- **Štítek pod ním**: stav a režim nabíjení:
  - *Nabíjí · Boost*: regulátor nabíjí. Nejdřív plným proudem na ~14,4 V (v chladu víc, *teplotní kompenzace*), pak napětí drží po dobu Boostu (obvykle 2 h).
  - *Nabito · Float*: baterie je plná, regulátor drží ~13,7 V a **škrtí panely** na to, co je zrovna potřeba.
  - *Vybíjí se · Float / Boost*: regulátor sice hlásí Float/Boost, ale za měničem se bere víc, než panely dají, a baterie se vybíjí (oranžově).
  - *Baterie slábne* (pod 12,2 V), *Odpojit spotřebiče* (pod 12,0 V), *Zátěž odpojena* (pod 11,6 V).
  - **☀ X W**: výkon panelů teď.
- **Odběr chaty teď** (vpravo): co se odebírá za měničem (zásuvka „220V měnič“). Pod tím:
  - *z baterie ~X W (A)*: kolik to bere z baterie i se ztrátami měniče.
  - *Victron …*: údaje z měniče přes Bluetooth. *„Victron (Bluetooth): nic nepřichází“* znamená, že Flip měnič neslyší (viz kap. 7).
- **⚡ Měnič měří X V při odběru Y**: napětí a odběr ve stejném okamžiku přímo z měniče.
- **🔌 Nabíjení River zapnuto / vypnuto**: stav automatiky (kap. 5).
- **Kdy přepnout na River (5.116)**: večer (od západu slunce) přijde „🔌 Přepni chatu na River do ~HH:MM“. Před dnem s odjezdem podle rozvrhu (Nastavení → Výhled dne – kontrola před odjezdem) hlídač počítá tak, aby ráno v čase odjezdu zbylo v baterii dost na to, aby solár s předpovědí utáhl chatu do večera (Nastavení → den_do, 22:00). Když by to zítra nevyšlo ani s plnou baterií, hlídá jen „do rána nad alarmem“. Den bez odjezdu = smaž jeho čas v rozvrhu. Na dlaždici Solární baterie řádek „na River“.
- **Nesmyslné hodnoty (5.115)**: údaj mimo možný rozsah (třeba baterie 25 V nebo zásuvka −5 W) aplikace nepoužije a jednou denně ho zapíše do Deníku („Nesmyslné hodnoty zahozeny“).
- **Z čeho chata jede (5.113)**: solár, když zásuvka za měničem ukazuje odběr; River, když měnič nedodává (nebo ho Victron hlásí vypnutý) a River ano. Když zásuvka (1) neodpoví a Victron nehlásí vypnuto, aplikace napíše „nevíme“ a nic si nedomýšlí – takové chvíle se nepočítají do hodin na River ani do typického odběru.
- **🌙 Do rána vydrží / nevydrží**: předpověď na noc (po západu slunce): napětí teď a odhad k ránu. „Nevydrží“ = klesne pod alarm 12,0 V (s časem), nebo se vypne měnič. Po západu ukazují dlaždice, karta Teď i upozornění tentýž výsledek.
- **Modrý pruh**: nabití podle regulátoru.

### 🔧 Kabely a spoje
Aplikace porovnává napětí, které ukazuje **regulátor**, s napětím, které měří **měnič Victron**. Každý měří na svých svorkách; když teče proud a někde je špatný spoj (povolená svorka, koroze, držák pojistky, tenký kabel), regulátor vidí víc, než baterie má, a měnič míň. Regulátor si pak myslí, že je baterie nabitá, a nedobije ji.
- Když je ztráta vyšší než u dobré instalace (odpor kabelů a spojů nad ~10 mΩ, tj. víc než ~0,25 V při 25 A), objeví se pod hlavní kartou **oranžová karta** (nad 20 mΩ červená).
- Ťuknutím (nebo v sekci *Zdraví baterie → Kabely a spoje*) se otevře **návod krok za krokem**: schéma s měřicími body, kam přiložit multimetr, políčka na zapsání naměřených napětí (aplikace hned spočítá ztrátu a řekne, jestli je v pořádku), co hledat a jak to opravit. Zápis i odškrtnuté kroky si telefon pamatuje.
- Po opravě karta sama zmizí (bere se medián za poslední 3 dny).

### Dlaždice (ťuknutím se otevře graf Dnes / Týden)
- **Bilance teď ›** (přes celou šířku, nahoře): kolik **opravdu** teď jde do baterie (zeleně ↑ nabíjí) nebo z ní (červeně ↓ vybíjí), ve wattech a ampérech. Regulátor nevidí odběr měniče (ten bere přímo z baterie), takže může ukazovat Float/Boost a „nabíjím“, i když se baterie ve skutečnosti vybíjí – tahle dlaždice to říká na rovinu. Pod tím: *regulátor dává X W → chata bere Y W i se ztrátami měniče*. Graf: bilance během dne (nad nulou nabíjí, pod nulou vybíjí, pozadí podle režimu regulátoru), součty za den do baterie / z baterie a napětí.
- **Nabití ›**: **procenta podle regulátoru** (při odběru ukazuje méně, protože klesne napětí). Jsou jen orientační: regulátor počítá z napětí i při nabíjení. Při nabíjení ukáže 100 %, po západu spadne napětí na ~12,8 V a ukáže ~60 %. Jinde v aplikaci se proto používá **napětí**.
- **Panely teď ›**: výkon panelů, *z regulátoru X A* (proud do baterie) a **do baterie čistě ~X A** (po odečtení odběru měniče; záporně a červeně = baterie se vybíjí). V grafu je **barevné pozadí podle režimu**: oranžová = Boost, zelená = Float.
- **Vyrobeno dnes ›**: výroba za den, měsíc, celkem. Graf: výroba po hodinách a jak přibývala.
- **Spotřebováno dnes ›**: všechno za měničem (stejně jako zásuvka „220V měnič“). Pod tím rozpad: *lednice · běžný odběr* (světla, kamery, wifi) *· navíc* (nabíjení zařízení, River) a *z baterie i se ztrátami*.

### Počasí a výroba
- **Štítek provozu**: ☀️ *letní* (chata na solární baterii) nebo ❄️ *zimní* (chata na River). Pozná se automaticky, jde nastavit i ručně.
- **Doporučení jednou větou**, např. „baterie ráno neklesne pod ~12,3 V“ nebo v zimě „chatu půjde připojit na solár ve čtvrtek“.
- **7 sloupců**: předpověď výroby na každý den (kWh), ikona počasí. **Čárkovaně**: kolik musí panely vyrobit na spotřebu chaty (i se ztrátami).
  - **Pod sloupcem** (léto): očekávané **napětí příští ráno**, barevně podle hranic 12,2 / 12,0 V. V zimě napětí solární baterie večer.
  - **Zeleně**: den, kdy výroba pokryje spotřebu (v zimě den vhodný k připojení soláru).
- **Jak přesně předpovídá**: předpověď vs. skutečnost za poslední dny. Předpověď se **učí**: porovná včerejší odhad se skutečností a opraví další.

### Rozbalovací sekce (zavřené ukazují jednořádkové shrnutí)
- **🔌 Zásuvky**: všechny zásuvky Tapo (ťuknutím graf Den / Týden / Měsíc), **💡 Ostatní za měničem** (světla, kamery, wifi = měnič − lednice) a telefon na chatě.
- **🔆 Panely**: kolik panelů je zapojeno, nejvyšší proud za jasného dne a **kdy přidat / odpojit druhý panel** (kap. 6).
- **🔋 Zdraví baterie**: verdikt (dobrá / opotřebovaná / slabá / vyměnit), odhad kapacity v Ah, hluboká vybití, graf po týdnech nebo měsících a poslední měření slovy (kap. 4).
- **📈 Grafy**: napětí, výkon panelů (s režimem), odběr, výroba po dnech / měsících / letech, nejnižší napětí dne. Nahoře přepínač 24 h / 48 h / 7 dní / 14 dní.
- **📋 Deník**: co se dělo: automatika, upozornění, chyby (14 dní).
- **📅 Tabulka po dnech**.

Otevřené sekce si telefon pamatuje.

---

## 3. Upozornění (ntfy) a co dělat

| Upozornění | Co znamená | Co udělat |
|---|---|---|
| 🔋 Baterie nabitá (Float) | Regulátor přešel do Float | Můžeš zapojit náročnější spotřebič |
| 🌥 Panely nevyrábí | Za světla (mimo 45 min po východu / před západem) panely 30 min nedávají ani 5 W | Sníh, stín, odpojený panel, jistič |
| ☀️ Panely zase vyrábí | Konec předchozího | – |
| Baterie slábne / kritická / měnič se vypíná | Napětí pod 12,2 / 12,0 / 11,6 V | Omez spotřebu, odpoj nepotřebné |
| 🧊 Lednice nechladí? / běží bez přestávky / bez proudu | Kompresor stojí / běží neobvykle dlouho (podle posledních 7 dní), nebo zásuvka lednice nejde přečíst | Zkontroluj lednici (zapnutá, dveře, námraza). Když chatu vypínáš celou, vypni v Nastavení „Hlídat lednici“ |
| ❄️ Mráz u solární baterie / Vybitá baterie v mrazu | Teplota baterie z regulátoru pod 0 °C; při nabití pod 40 # hrozí zamrznutí | Drž baterii nabitou, nevybíjej ji (chata na River) |
| 🔥 Velký úbytek napětí na kabelech | Jedno spárované měření regulátor − měnič nad hranicí (0,35 V) | Počkej na další zprávu: „trvá – N. měření“ = jdi kontrolovat (návod v Kabely a spoje), „✓ zase v normě“ = nejspíš měření z trochu jiné chvíle |
| 🌙 Baterie do rána nejspíš nevydrží | Podle odběru a stavu baterie dojde v noci pod alarm | Odpoj něco, ráno počítej s River |
| ⚡ Nabíjecí proud X A – blízko pojistky | Proud z regulátoru nad 33 A (110 % pojistky 30 A) | Pokud jsou zapojené 2 panely, jeden odpoj |
| ⚠️ Odpoj druhý panel | Blíží se jaro, za jasného dne by hrozilo přes ~34,5 A | Odpoj druhý panel do uvedeného data, přepni v Nastavení |
| 🔆 Zapoj druhý panel / ⏳ jeden nestačí, druhý ještě ne | Podzim: jeden panel nestačí; druhý je / ještě není bezpečný | Podle zprávy; po přepojení přepni v Nastavení |
| 🍂 Blíží se zimní provoz / 🌱 Můžeš přejít na letní | Výroba na příští dny nestačí / už stačí | Zvaž přepojení chaty na River / zpět |
| ☀️ Zítra můžeš chatu připojit na solární baterii | Zima: solární baterie bude ráno dost nabitá | Přes den připoj chatu na solár, večer zpět na River |
| 💡 V noci šlo víc/míň proudu na světla/kamery/wifi | Ostatní odběr se výrazně změnil | Nezůstalo něco zapnuté? Nevypadla kamera / wifi? |
| ⚡ Odběr navíc ~X W – bere se z baterie | Přes den je odběr za měničem aspoň o 40 W nad běžný (lednice + světla, kamery, wifi) **a** baterie se vybíjí (pod −2 A). Kvůli běžnému odběru (zašlé slunce) nepřijde. Když zásuvka lednice nepošle hodnotu, počítá se s lednicí naplno (80 W, Nastavení), aby kompresor nevypadal jako „navíc“ | Omez nabíjení zařízení; nejvýš 1× za hodinu |
| 🔋 Baterie možná ztrácí kapacitu | Zdraví baterie se zhoršilo o víc než 20 % | Sleduj sekci Zdraví baterie |
| 📡 Regulátor neposílá data | Cloud nemá čerstvá data přes 2 h | Wi-Fi modul regulátoru, internet na chatě |
| 📡 Hlídač nemůže číst Solar Guardian / EcoFlow | Cloud ~2 h neodpovídá | Většinou se spraví samo |
| 📵 Brána na chatě neposílá data / 📱 zase posílá | Flip mlčí (vypnuté v Nastavení) | Vybitý Flip, Wi-Fi, Android uspal aplikaci |
| 🪫 Telefon na chatě má X % | Baterie Flipu pod 15 % | Dobij Flip |
| 🔄 Vyměň River / ⛽ River nabitá na 100 % | River skoro vybitá / nabitá z generátoru | Přepoj / vypni generátor |
| 📊 Chata – souhrn dne | Večer ve 22:00 | Výroba, spotřeba, deník, chyby, zítřek |

**Nabíjení River** (zapnutí / vypnutí) chodí potichu. Je v Deníku a ve večerním souhrnu, notifikaci jde zapnout v Nastavení.

---

## 4. Zdraví baterie: jak číst

- **Verdikt** se počítá z nocí: o kolik kleslo napětí při známém odběru. Počítají se jen noci, kdy baterie zůstala **nad 12,1 V**; při hlubším vybití napětí neodpovídá stavu.
- **Pásma** podle zbývající kapacity: dobrá ≥ 80 %, opotřebovaná 60–80 %, slabá 45–60 %, vyměnit < 45 % (z 200 Ah).
- Jedna noc kolísá klidně o ±15 %, rozhoduje **medián**. V zimě vychází AGM vždy hůř (chlad). Skutečný úbytek ukáže až **srovnání stejné roční doby**.
- **Odhad z nabíjení** je jen orientační: Float nastane podle času Boostu, ne když je baterie opravdu plná.
- **Hluboká vybití** (pod 12,0 / 11,8 V) zkracují život AGM. Čím méně, tím déle baterie vydrží.
- Předpověď do rána i výhled počítají s **naměřenou kapacitou**, ne s 200 Ah.

---

## 5. Automatické nabíjení River přebytkem ze slunce

Zásuvka **.157** (za měničem, neměří) nabíjí River. Priorita je vždy **solární baterie**.

**Zapne se**, když:
- regulátor je ve **Float**, **nebo** v **Boostu drží nabíjecí napětí** (~14,4 V + teplotní kompenzace), tj. baterie dostává plnou dávku a River jede z přebytku,
- je aspoň 1 h po východu a nejpozději 2 h před západem slunce,
- od posledního vypnutí uběhla pauza: 20 min, po každém neúspěšném pokusu (baterie se vybíjela) dvojnásobek – 40, 80, max. 120 min.

**Vypne se hned**, když:
- se baterie **vybíjí** víc než 2 A (čistý proud = z regulátoru − odběr měniče), tj. panely na River nestačí,
- ve Float napětí klesne o víc než 0,4 V pod Float (~13,3 V),
- v Boostu napětí spadne o víc než 0,2 V pod nabíjecí hodnotu **a zároveň pod úroveň Float** (regulátor už neudrží → River by brala z baterie). Pokles jen na ~13,7 V je normální konec Boostu, ne problém,
- napětí klesne pod **13,0 V** (baterie se vybíjí), nebo pod 12,5 V,
- první měření po přepnutí ukáže panely pod 100 W,
- blíží se západ slunce, nebo regulátor neposílá data.

Hlídač i Flip běží po 10 minutách, takže v nejhorším případě se River ~10–20 min nabíjí z baterie, než se to zachytí.
**Ruční zapnutí** v aplikaci Tapo automatika nevypne (není to její povel).
Na hlavní stránce je vidět, proč je River vypnutá, kdy to automatika znovu zkusí a proč se naposledy vypnula.

---

## 6. Panely: 1 nebo 2 a pojistka 30 A

- V létě stačí **1 panel**, v zimě jsou potřeba **2**. Se dvěma panely by v létě teklo přes 30 A a spálila by se **pojistka mezi regulátorem a baterií**.
- Hlídač si z historie bere **nejvyšší naměřený proud** pro danou roční dobu (nejhorší případ, ne předpověď počasí) a z toho radí:
  - **podzim**: přidat druhý panel, až jeden nestačí **a** dva budou bezpečné aspoň 3 měsíce dopředu (do 30 A),
  - **jaro**: odpojit druhý panel s předstihem 14 dní, než by hrozilo přes ~34,5 A,
  - **okamžitě**: když proud skutečně překročí 33 A.
- Pojistka 30 A snese 30 A trvale. Pálí až výrazné přetížení (~135 % do hodiny, 2× do pár sekund).
- **Po fyzickém přepojení přepni v Nastavení „Zapojené panely“.** Předpověď výroby i výpočty s tím počítají.

---

## 7. Když něco nefunguje

- **Červená verze Flipu dole na stránce**: na Flip nahraj novou aplikaci (Android Studio: složka `android`, ▶ Run). Kopíruj celou složku `app` (i `build.gradle`).
- **„Victron (Bluetooth): nic nepřichází“**: na Flipu otevři *Chata brána* → *Test Bluetooth*. Musí být zapnutá poloha a Bluetooth a VictronConnect musí být zavřený (když je k měniči připojený, měnič přestane vysílat). Když test Victron najde, ale na pozadí nic nechodí, je potřeba aplikace Flip aspoň 1.2.
- **Data se nemění**: ⚡ Načíst. Když nepomůže, podívej se do Deníku (chyby červeně).
- **Stránka se neaktualizuje na novou verzi**: aplikaci úplně zavři a otevři. Nová verze bývá vidět do ~15 min po změně.
- **Nastavení nejde uložit**: GitHub token v telefonu vypršel → v Nastavení zadej nový.
- **Android Studio „Unable to delete directory“**: projekt nesmí být v OneDrivu; smaž `app\build` a `.gradle` a spusť znovu.

---

### Flip posílá data přes GitHub (Flip 1.4.0)
Flip od 1.4.0 posílá naměřená data přímo s tokenem na GitHub (stejný token jako pro spouštění hlídače, musí mít **Actions: Read and write**). V záznamu Flipu je pak „Odesláno (GitHub): …“. Když GitHub nejde, pošle data postaru přes ntfy. Bez tokenu to funguje jen přes ntfy, a to má limit na počet zpráv (19. 10. odmítal – HTTP 429).

### Záložní spouštění hlídače (cron-job.org, od 4.31)
Hlídač normálně spouští Flip po každém měření. Když na chatě vypadne internet, zbývá jen plán GitHubu, který umí běhy na desítky minut vynechat (19. 10. 12:22–12:57). Proto ho navíc každých 10 min spouští **cron-job.org** (zdarma):
- GitHub token jen pro tento repozitář, oprávnění **Actions: Read and write**, platnost 1 rok (pak vyměnit).
- Úloha: `POST https://api.github.com/repos/KptDundee/chata-hlidac/actions/workflows/hlidac.yml/dispatches`, hlavičky `Authorization: Bearer <token>`, `Accept: application/vnd.github+json`, `Content-Type: application/json`, tělo `{"ref":"main","inputs":{"test":"false","wake":"false"}}`, každých 10 min. Úspěch = odpověď 204.
- Když token vyprší, cron-job.org pošle e-mail o chybách (401).

## 8. Hodinky

- **Komplikace** „Chata – napětí baterie“: dlouze podrž ciferník → Upravit → místo komplikace. *V?* = data starší než hodina, *V!* = kritické napětí.
- **Dlaždice při chatě na River** (hodinky 1.9): která River napájí, % nabití River (až s EcoFlow, do té doby odběr W), vydrží do ~… ✓/✗, odběr od kdy a kolik kWh, solár jen malým řádkem.
- **Dlaždice** „Chata“: napětí (barevně), nabití #, panely, odběr, předpověď. **Ťuknutím se změří hned** (hodinky 1.8): hodinky probudí Flip, ten změří a spustí hlídače; dlaždice ukazuje „⏳ měří se…“ a za 2–3 min má nová data. Když Flip spí nebo je bez internetu, nic se nestane – data přijdou s dalším pravidelným během.
  - Když chatu napájí **River** (některá ze zásuvek River 2 / 3 / 6 bere víc než 3 W), místo předpovědi ukáže: „🔋 River malý · 45 W / od 22:10 · 0,42 kWh“. Jakmile půjdou data z EcoFlow, ukáže místo toho % a do kdy River vydrží. Odběr 🏠 = celá chata (solár + River).
  - Projeví se do 10 minut od dalšího běhu hlídače – jen když Flip posílá data ze zásuvek (Flip na Wi‑Fi chaty).
- V aplikaci Chata na hodinkách musí být zadané **téma ntfy** (stejné jako v aplikaci ntfy).
- **Komplikace** „Chata – východ / západ slunce“: časy u chaty (počítá se v hodinkách, bez internetu).

### Ciferník Chata
Analogový ciferník v leteckém stylu (tmavě modrý sunburst do černa, zapuštěné subdialy, odlesk sklíčka pod 45°, masivní ručky s luminiscencí, oranžová vteřinovka). Hodiny: tučné čárky na vnějším věnci a kovové číslice (kromě míst se subdialy).
- **Nahoře** nejbližší východ nebo západ slunce u chaty: ikonka slunce na obzoru se šipkou – přes den šipka dolů (západ), v noci nahoru (východ).
- **Tři stejné subdialy** – po obvodu jezdí trojúhelník (ukazatel), uprostřed velké číslo:
  - **vlevo nahoře 🏠 chata** – napětí solární baterie (1 desetinné místo), stupnice 11,6–13 V: červená = kritické, oranžová = slabne, zelená = nabitá. Ťuknutím se otevře aplikace Chata.
  - **vpravo nahoře 🔋 hodinky** – baterie hodinek.
  - **dole 🌡 teplota** venku v místě, kde jsi (komplikace „Chata – teplota venku“ z Open-Meteo; poloha hodinek – aplikace Chata se jednou zeptá na povolení polohy; bez něj teplota u chaty). Jde vyměnit za počasí Xiaomi v editoru ciferníku.
- **Vlevo dole den** (PO, ÚT…), **vpravo dole datum** (21/12).
- **Úsporný režim** (sklopená ruka, je-li zapnutý „vždy zapnutý displej“): ciferník vypadá stejně, jen zmizí vteřinovka.
- Komplikace vlevo a nahoře jdou v editoru ciferníku vyměnit (dlouze podržet → Upravit).


### Kabely a spoje (3.54)
Úbytek napětí = regulátor − měnič, jen z měření ze stejné chvíle a bez stálého rozdílu kalibrace přístrojů. V klidu ~0, s proudem roste. Upozornění: 🔥 nad 0,35 V hned (zkontroluj pojistku a spoje – nejsou horké?), 🔧 odpor nad 20 mΩ za den.

### Regulátor neposílá data
Po 30 min bez dat přijde notifikace a web zčervená („údaje níže nejsou aktuální“). Napětí pak ukazuje Victron. Možné příčiny: zaseknutý Wi‑Fi modul regulátoru, vypadlá Wi‑Fi / router (aplikace řekne, jestli má zásuvka routeru proud), regulátor bez napájení z baterie, výpadek cloudu. 💡 Tip: často pomůže vypnout a zapnout Wi‑Fi modul regulátoru (14. 10. 2026 pomohlo).


## Hlavní stránka (od 3.33) – pevná struktura

**Spotřeba (3.53):** Chata celkem = Ze soláru + Z River. Každá dlaždice otevře svůj pohled – grafy a tabulka jen za dobu, kdy běžel daný zdroj (celkem = vše).
**Spotřeba dnes (3.51):** Chata celkem (přes celou šířku), pod ní Ze soláru a Z River. Rozkliknutím detail: nejdřív složený graf „co bralo kdy“, pak 220 V (změřeno i se ztrátami měniče), každá zásuvka zvlášť, „ostatní (neměřené)“ – světla, kamery a vše bez vlastní zásuvky; pod grafy tabulka dnes / včera / ⌀ 7 dní (☀ ze soláru, R z River). Zásuvka 8 (nabíjení River ze soláru) zatím neměří – když běží, je v „ostatní“.

**Dlaždice Solární baterie (3.45, 3.84):** napětí a pod ním stejně velké **nabití #** (pod 50 # oranžově, pod 30 # červeně), stav (Nabíjí se / Vybíjí se / Nabito / V klidu), nabití % podle regulátoru, panely W, odběr z baterie W (měnič i se ztrátami; „měnič vyp.“ = chata na River). Blikající ❗ jen když je třeba jednat – podrobnosti po rozkliknutí.
Detail (od 3.46): nahoře grafy – do/z baterie, výkon panelů, napětí (regulátor modře + měnič Victron oranžově), odběr z baterie, nejnižší napětí každého dne (body), výroba. Pod nimi čísla (teď, dnes, včera, nejnižší stav za 7 / 30 dní / rok / celou historii), úplně dole výklad. Šedé pozadí v grafech = chata jela z River. V bodovém grafu nejnižšího napětí: plný bod = noc, kdy chatu napájela solární baterie (tyhle se dají porovnávat, spojuje je čára); prázdný šedý kroužek = noc na River (baterie bez zátěže – vyšší napětí, nesrovnatelné).
1. Hlavička: čas dat z regulátoru, baterie Flipu; vpravo Načíst, ↻, ⚙.
2. Lišta „Nic k řešení / N věcí k řešení“ – jen mimořádné věci, podrobnosti po ťuknutí.
3. **Teď:** Solární baterie, River (záložka pro každou River; svítí ta, která napájí nebo se nabíjí).
4. **Dnes:** Spotřeba chaty (celkem a podle zdroje), Výroba a nabíjení (slunce, generátor, River).
5. **Výhled:** noc z dneška na zítřek, zítřek. Pak Uplynulé a Dlouhodobě.
Dlaždice se nepřeskupují – mění se jen čísla a krátký text v nich.


## Zásuvky Tapo – pojmenování (od Flip 1.3)
V aplikaci Tapo dej každé zásuvce jméno začínající číslem v závorce, např. `(3) (R) River žlutý`. První závorka = číslo zásuvky (podle něj ji hlídač pozná, i když router změní IP adresu), druhá závorka třeba Wi‑Fi, zbytek libovolně. Flip síť prohledá sám. V Nastavení hlídače (nastaveni.txt) se pak zásuvky zadávají tímto číslem: `zasuvky_river = 3, 4, 5`, `zasuvka_lednice = 2`… Po přejmenování na Flipu dej „Odeslat teď“ (hledání proběhne do pár minut).


### Výpadky dat (3.59, Flip 1.3.4)
Když Flip nemůže odeslat (výpadek internetu), uloží zprávy do fronty a pošle je, až se spojení obnoví – v grafech se díra dodatečně zaplní. Data regulátoru se doplňují z historie Solar Guardianu. Trvalé díry zůstanou jen, když Flip neměří vůbec (vybitý, vypnutý) nebo zamrzne Wi‑Fi modul regulátoru.

### Victron na pozadí (Flip 1.3.11)
Aby Flip slyšel Victron i se zhasnutým displejem a zavřenou aplikací, musí mít aplikace Chata brána polohu **„Povolit vždy“**. V aplikaci je nahoře stav (✓ / ⚠) a tlačítko **Poloha: Povolit vždy**, které otevře nastavení aplikace → Oprávnění → Poloha → Povolit vždy. Android to aplikaci nedovolí zapnout sama.

### Flip spouští hlídače (3.83, Flip 1.3.10)
V Nastavení Flipu vyplň **GitHub token** (stejný jako na webu u ⚡ Načíst, stačí vložit). Flip pak po každém měření (~10 min) spustí hlídače sám, takže web i hodinky mají data stará jen 2–3 min. Prázdné pole = jako dřív (hlídač podle svého rozvrhu). Když token vyprší, v Deníku Flipu je chyba „GitHub“ – zadej nový.

### ⚡ Načíst (3.60, Flip 1.3.5)
Spustí hlídače a zároveň probudí Flip – ten změří a odešle hned. Za 1–3 minuty jsou na stránce čerstvá data. Když Flip hluboce spí nebo je bez internetu, může odpovědět až při svém dalším pravidelném měření (do 10 min).

### Okno River (3.65)
Dlaždice River v řádku Teď má záložky pro tři River a generátor – co dělají právě teď. Rozkliknutím: časová osa „Co se dělo“ (kdy která River napájela chatu nebo jen spotřebič, kdy běžel generátor), výkon každé River, generátor, běhy generátoru a čísla. Nabití % a nabíjení každé River se objeví, až poběží EcoFlow.

### Zvuky upozornění podle důležitosti (4.02)
Nastavení telefonu → Aplikace → ntfy → Oznámení → Kategorie oznámení → u tématu chaty ťukni na **název** kategorie (ne na přepínač) → Zvuk.
- **Nejvyšší** – TEĎ jednej: přepni na River, měnič se vypíná, odpoj spotřebiče, proud u pojistky, Flip skoro vybitý → výrazný zvuk + přepsat Nerušit.
- **Vysoká** – důležité: baterie nevydrží do rána, alarm měniče, data nechodí, odběr navíc, vyměň River, River nabitá – generátor běží naprázdno, vypni ho (až s EcoFlow), velký úbytek na kabelech, panely nevyrábí, pod 30 #.
- **Výchozí** – doporučení: kabely (odpor), kapacita baterie, letní / zimní provoz, panely, pod 50 #, souhrn dne s chybou.
- **Malá** – jen informace: baterie nabitá (Float), regulátor / brána zase posílá, panely zase vyrábí, nabíjení River zapnuto / vypnuto, generátor doběhl, souhrn dne bez chyb → tichý.
- **Nejnižší** – nepoužívá se pro upozornění.

### Výhled dne – vydrží chata na soláru do večera? (4.05)
Jen když chata jede ze solární baterie. Na dlaždici Solární baterie: **„do 22:00: vydrží ✓“** nebo **„dojde ~14:30“** (odhad ±1–2 h – počasí se plete). Upozornění „⚠️ Dnes ~14:30 solární baterie dojde – přepni chatu na River“ přijde ráno v čas z rozvrhu (Nastavení → *Výhled dne – kontrola před odjezdem*, např. `út 5:30, čt 5:30, po 7:00…`, den bez času = nekontrolovat) a během dne, když se výhled zhorší. Noc řeší zvlášť večerní upozornění a naléhavé ve 22:00. Když chata jede z River a solár by do 22:00 vydržel, přijde ve stejný ranní čas „☀️ Dnes můžeš chatu přepnout na solární baterii“ – a když to ráno nevyjde, tak později během dne, jakmile to poprvé vyjde (jednou za den, do 22:00). Na dlaždici je pak řádek **„přepnout na solár?“**: **ano ✓** = vydrží i do rána, **do 22:00** = přes den ano, večer zpět na River, **ne** = nestačí (rozpis v detailu Solární baterie).

### Naléhavě: přepni na River (4.01)
Když baterie do rána nevydrží (předpověď: pod 12,0 V) a chata ve 22:00 pořád jede ze solární baterie, přijde **„⚠️ TEĎ přepni chatu na River“** s nejvyšší prioritou a opakuje se po ~5 min. Skončí, když ťukneš na **„Přepínám“** v notifikaci, když chata přejde na River (sám to pozná ze zásuvek) nebo ráno. Čas se mění v Nastavení (`nutne_river_v`, „vypnuto“ = nikdy). Aby notifikace zazvonila i v režimu Nerušit: aplikace ntfy → téma → nastavení → povolit přepsání režimu Nerušit pro nejvyšší prioritu.

### Zdraví baterie a test kapacity (3.89)
Verdikt (dobrá / opotřebovaná / slabá / vyměnit) se počítá **jen z testů kapacity z ampérhodin** – hlídač je dělá sám každé ráno: buď od plného nabití (Float), nebo **dvoubodově** večer → ráno (když baterie plná nebyla). Potřebuje odběr z Victronu (Flip). Do 2 úspěšných testů je verdikt „Zatím neznámo“. Seznam testů s výsledkem nebo důvodem, proč nevyšel, je v okně Zdraví baterie. Noční odhad z poklesu napětí je jen orientační graf. Data před opravou spojů (nastavení `oprava_spoju`) se nepočítají – po další opravě spojů tam zapiš nové datum a čas.

### Nabití # (3.75)
Vedle % regulátoru (odhad z napětí – v Boostu ukazuje 100 %, i když baterie plná není) je **#**: spočítané z toho, kolik ampérhodin do baterie přiteklo a kolik odteklo. 100 # = baterie skutečně plná (regulátor aspoň 30 min ve Float); když plná dlouho nebyla, nejlepší stav za posledních 7 dní. Když nic neteče, # se nemění.

Upozornění: pod 50 # a pod 30 # (nastavení `hash_upozornit`). 50 # ≈ 12,3 V v klidu / 12,2 V při nočním odběru; 30 # ≈ 12,0 V. Na hodinkách je na dlaždici #, v komplikaci napětí.
**Generátor a malá River v EcoFlow (4.67)**: EcoFlow u nich neposílá „všechny údaje“ (chyba 1006). Hlídač proto sám zkouší jiné cesty, hlavně když generátor běží (po vypnutí elektronika generátoru rychle usne a pak není co číst). Co zjistil, je v Nastavení → karta „EcoFlow – připojení“ pod generátorem a malou River, řádek „zkouška …“.

**Nabíjení z generátoru (4.68)**: když běží generátor, hlídač sám nastavuje, kolik W si berou velké River (žlutá, červená), aby se nabily zároveň a generátor běžel co nejkratší dobu – jede přitom skoro naplno (benzín 1800 W, plyn 1600 W, rezerva 100 W). Malou River ovládat nejde, hlídač jen odečte, kolik bere. **Když jedeš na plyn, přepni v Nastavení → Generátor → Palivo na „plyn (LPG)“** – jinak by generátor přetížil. V detailu EcoFlow / Generátor je karta „Nabíjení z generátoru“: kolik která River dostala, kdy bude plná a kdy můžeš generátor vypnout. Po běhu dostanou velké River 650 W, aby příští start (než hlídač zareaguje, max ~10 min) generátor nepřetížil. Když generátor běží a nic nebere, přijde „Generátor běží naprázdno – vypni ho“.

**Generátor – častější měření (Flip 1.7.3)**: když běží nabíjení z generátoru, Flip posílá každé 2 minuty místo 10, takže hlídač hned reaguje (jiné nabíjení každé River, odpojená River, konec). Po vypnutí generátoru se vrátí na 10 minut. Zásuvku generátoru (7) Flip po startu generátoru hledá v síti sám při každém měření; rychleji to jde tlačítkem **Odeslat teď** ve Flipu.

**Zásuvky s novou adresou (Flip 1.7.4)**: zásuvky na River, generátoru a nabíjení mají proud jen někdy a router jim pak může dát jinou adresu. Flip to pozná hned při tom měření – najde je podle **čísla ve jméně** (např. „(7) Generátor“) a přečte je na nové adrese. Proto musí mít **každá zásuvka v aplikaci Tapo číslo v závorce na začátku jména** a v aplikaci Tapo musí být zapnutá **Kompatibilita s třetími stranami** (jinak zásuvka odmítne přihlášení – v záznamu Flipu „odmítá přihlášení (401)“).

**Zásuvka není vidět (4.72)**: zásuvky 1 (220 V na měniči), 4 (lednice), 5 (router) a 9 (nabíjení Flipu) mají být vidět pořád. Když je Flip aspoň 8 minut nepřečte, přijde „🔌 (1) … není vidět“ i s důvodem, a až se vrátí, „je zase vidět“. Zásuvka měniče se nehlídá, když je měnič vypnutý (chata na River). Seznam se dá změnit v Nastavení → Zásuvky.

**Nabíjení routeru (Flip 1.9, web 5.34)**: router M7000 se napájí ze zásuvky (5). Flip čte baterii routeru (nejvýš 1× za 9 min, ve Flipu musí být heslo správce routeru) a zásuvku řídí: **pod 40 %** zapne (nabíjí), **od 80 %** vypne a router jede z vlastní baterie; mezi tím nechá jak je. Při přebytku ze slunce nabíjí; z River ne – River musí vydržet noc (Flip 1.9.1). Když baterii nejde přečíst, nabíjí. **Pojistka**: před každým vypnutím nastaví v zásuvce odpočet „za 2 h zapnout“ – kdyby spadla aplikace, Flip nebo Wi‑Fi (vybitý router by už nikdo nezapnul, Flip zásuvky ovládá přes jeho Wi‑Fi). Když zásuvka odpočet nepřijme, nechá ji zapnutou. Pod 25 % přijde upozornění „📶 Router na chatě má jen X %“. V aplikaci Tapo u zásuvky (5) **nesmí být vlastní plán / režim vypínání**. Vypnout řízení: Nastavení → `router_nabijeni_rizeni` (nebo prázdné `zasuvka_router`). Stav: detail Flipu → „Nabíjení routeru“.

**Lednice – kolik běžela (4.73)**: v detailu lednice graf, kolik % dne běžel kompresor. Když to dlouhodobě roste (při podobné teplotě v chatě), lednice chladí hůř – těsnění dveří, námraza, zanesená mřížka vzadu. V zimě ve studené chatě bude číslo přirozeně nižší. Bublina ukáže i hodiny běhu, rozběhy a příkon za běhu.

**EcoFlow přes přihlášení aplikace (4.76)**: generátor a malou River vývojářské rozhraní nepouští, proto je hlídač čte stejně jako aplikace EcoFlow. Potřebuje tvůj e-mail a heslo k účtu EcoFlow – zadáš je sám do GitHubu (repozitář → Settings → Secrets and variables → Actions → New repository secret): `ECOFLOW_EMAIL` a `ECOFLOW_PASSWORD`. Nikde se nevypisují. Jestli to funguje, uvidíš v detailu EcoFlow → karta „EcoFlow – připojení“ (řádek „Přihlášení aplikace“). Generátor je vidět jen když běží (jinak jeho elektronika spí).

**Barvy dlaždic (4.78)**: Solární baterie – zelená = vydrží do rána, oranžová = do 22:00 ano, do rána ne, červená = nevydrží ani do 22:00. EcoFlow – záložka šedě = vypnutá, ● a plné písmo = zapnutá, rámeček = vybraná (údaje pod ní). Solár – šedý, když panely nevyrábí.

**Nabíjení z generátoru – postup (4.87)**: 1) Na webu otevři EcoFlow (nebo Generátor) a zmáčkni **⛽ Spustit nabíjení z generátoru**. 2) Nastartuj generátor a zapoj River (jednu, dvě, tři – jak potřebuješ). 3) Hlídač teď každých 30 s čte EcoFlow: 30 s po začátku nabíjení nastaví výkony tak, aby se velké River nabily zároveň a generátor jel co nejkratší dobu. Plná River dostane hned zpátky 200 W. 4) Až je hotovo, přijde „Generátor běží naprázdno – vypni ho“, nebo zmáčkni **⏹ Ukončit**. Mimo nabíjení mají velké River vždy 200 W, aby start generátoru nic nepřetížil. Když jedeš na plyn, přepni předtím Nastavení → Generátor → Palivo.

**Teploměry (5.13)**: hlídač hlídá šest teploměrů (Koupelna, Pokoj, Loznice, Kuchyne, Baterie, Lednice – Nastavení → Teploměry, které mají hlásit). Když některý hodinu nepošle hodnotu, přijde „🌡️ Teploměr … nehlásí“ i s důvodem, při návratu „zase hlásí“. Baterie teploměru (CR2032): upozornění při 10 % a 5 %. Teploměr „Baterie“ se bere pro mráz a kapacitu v chladu, „Lednice“ pro upozornění nad 8 °C.

**Hlavní stránka – sekce (5.15)**: Teď (vždy rozbalené) · Chata (teploty, lednice, Flip, spotřebiče) · Energie dnes (výroba a spotřeba) · Výhled · Uplynulé · Dlouhodobě. Sekce se rozbalí/sbalí ťuknutím na název; prohlížeč si to pamatuje. Když je v sekci něco červeně nebo oranžově, rozbalí se sama. Sbalená sekce ukazuje v řádku krátký souhrn.

**Spotřeba proti obvyklé (5.22)**: dlaždice Chata celkem ukazuje, kolik chata spotřebovala dnes do teď proti obvyklé (medián posledních 7 dní do stejné doby – jednotlivé výjimečné dny se neprojeví), obvyklou denní spotřebu a minulou noc (18–6 h) proti obvyklé. Když je dnes výrazně víc (o 50 % a aspoň o 0,15 kWh), přijde jedno upozornění za den. Ve večerním souhrnu je řádek „🏠 Chata dnes …“. V grafu výroby po dnech je čárkovaně „potřeba“ – kolik musí solár za den vyrobit, aby pokryl obvyklou spotřebu i se ztrátami nabíjení; v detailu Chata celkem graf spotřeby po dnech s obvyklou hodnotou.

## ⛽ Nabíjení z generátoru – postup (platí od 5.22)

1. **Na webu** otevři **EcoFlow** (nebo Generátor). Nahoře je karta „Nabíjení z generátoru“.
2. **Zmáčkni palivo**, na které generátor pojede: **⛽ Benzín** nebo **🔥 Plyn**. Tím se nabíjení spustí. Je jedno, jestli před startem generátoru nebo po něm – mimo nabíjení mají River vždy malý výkon (velké 200 W, malá 100 W), takže start generátoru nic nepřetíží.
3. **Nastartuj generátor a zapoj River** (1, 2 nebo 3 – podle potřeby). Nech generátor **1–2 minuty zahřát**.
3b. **V aplikaci Tapo zapni zásuvku (7)** (generátor) – tím začne nabíjení. Zásuvka (7) má v Tapo nastavené „Stav po obnovení napájení: Vypnuto“, takže po startu generátoru zůstane vypnutá, dokud se nezahřeje. Hlídač ji sám nepřepíná.
4. Hlídač každých 30 s čte EcoFlow. **30 s po začátku nabíjení** nastaví výkony (generátor naplno: benzín 1800 W / plyn 1600 W − rezerva 100 W, rozdělené podle toho, kolik které River chybí, ať skončí zároveň) – a pak je **nechá být**. Mění je jen, když některá River doběhne (dostane zpět malý výkon a její podíl ostatní) nebo když jednu připojíš / odpojíš.
5. **Když dojde palivo** a přepneš na druhé: River se hned vrátí na malé výkony; po novém startu zmáčkni **tlačítko toho paliva** (např. 🔥 Plyn) – nabíjení se spustí znovu.
6. **Konec:** prostě vypni generátor (hlídač to pozná a za 10 min nabíjení ukončí), nebo zmáčkni **⏹ Ukončit nabíjení**. Když River dojedou a generátor ještě běží, přijde „⛽ Generátor běží naprázdno – vypni ho“.

Na generátoru **Eko režim**: v eko režimu generátor hlásí max ~1100 W a nabíjí pomaleji – pro rychlé nabíjení ho vypni.

**Palivo a cena (5.26)**: v detailu Generátor karta „Palivo a cena“. Při **výměně lahve PB** zmáčkni „+ nová lahev“ (cena, plná / jen částečně), při **tankování benzínu** „+ natankováno“ (cena, litry, do plna?). Hlídač pak měří, kolik kWh generátor z dané lahve / nádrže vyrobil, a po spotřebování první plné lahve ukáže kWh na lahev, cenu za 1 kWh a cenu každého nabíjení. Částečně plná lahev se do průměru nepočítá. Tlačítko mačkej až při skutečné výměně – od té chvíle se energie počítá na novou lahev.

**Nápověda v Nastavení (5.35)**: u každé položky je otazník – klepnutím se rozbalí vysvětlení (co to je, co to řídí, co znamená změna). Dalším klepnutím se zavře.

**Chladnutí pokoje (5.36)**: v detailu Teploty je karta „Chladnutí – Pokoj“. Hlídač si z večerů, kdy po dotopení teplota plynule klesá, učí, jak rychle chata chladne (podle rozdílu proti venkovní teplotě v Hrdlořezích). Větrání (prudký pokles) pozná a vynechá – v tabulce 🪟. Po 5 večerech ukáže, kolik bude ráno (7:00) a kolik musí být v pokoji při dotopení, aby ráno bylo 21 °C. Kamna po dotopení ještě hřejí, takže skutečnost bývá spíš o něco tepleji. Teploměr, čas a cíl: Nastavení → Zásuvky, lednice, teploměry a Flip.

**Noční dobití Flipu (Flip 1.9.2, web 5.41)**: když chata jede ze soláru a slunce nedává přebytek (v noci), Flip se pod 20 % dobije jen na tolik, aby vydržel do doby, kdy panely obvykle mají přebytek (východ slunce + 3 h), s rezervou 5 %. Cíl počítá hlídač z typické rychlosti vybíjení Flipu a během noci se zmenšuje. Je vidět v detailu Flipu („Při poklesu pod 20 % – dobít jen na X %“). Přes den z přebytku a na River se nabíjí do 80 % jako dřív.

**Chata na River a upozornění (5.43)**: když chata jede z River, nechodí upozornění s radou „omez odběr / přepni na River“ (pod 50 #, slábne, noční předpověď). Pokud solární baterie i tak klesne pod kritické napětí, přijde „Solární baterie pod X V, i když chata jede z River“ – něco ji vybíjí. Po návratu na solár (30 min) platí upozornění zase normálně.

**Data internetu (Flip 1.9.3, web 5.44)**: v detailu „Flip (brána) a Wi‑Fi“ je vidět, kolik dat dnes přenesl router (mobilní internet chaty), kolik z toho Flip (celý telefon přes Wi‑Fi), kolik z toho aplikace Brána a kolik ostatní zařízení (kamery…). Graf ukazuje data po dnech. První den se počítá od nahrání Flipu 1.9.3.

**Chladnutí – jak číst (5.46)**: hlavní číslo je „chata ztrácí X °C za hodinu na každých 10 °C rozdílu proti venku“. Při 20 °C uvnitř a 10 °C venku klesá teplota o X °C za hodinu, při rozdílu 20 °C o 2× X. Čím menší číslo, tím líp chata drží teplo. Učí se jen z noci 0:00–7:00 (Nastavení), kdy se netopí.

**Graf noci (5.49)**: v detailu Teploty graf „Noc: Pokoj a venku“ – modře skutečná teplota v pokoji, čárkovaně předpověď (jen orientační), zeleně venku, vybarvený pás = rozdíl teplot, šedě noc bez topení. Tlačítky nad grafem se přepíná noc (poslední týden).

**Nabíjení Flipu (5.55)**: do 80 % se Flip nabíjí jen ze skutečného přebytku slunce (panely dávají aspoň o 15 W víc, než chata bere, nebo je solární baterie plná). Jinak – i když chata jede z River – jen pod 20 % a jen na tolik, aby vydržel do doby, kdy slunce zase dává přebytek.

**Řízení nabíjení Flipu a routeru (5.58 / Flip 1.9.8)** – shrnutí:
- Slunce navíc = regulátor panely škrtí (solární baterie plná, nebo ji drží na nabíjecím napětí). Jen tehdy se Flip nabíjí do 80 % a router do 90 %.
- Jinak Flip jen pod spodní hranicí (30 %, Nastavení) a jen do slunce; router pod 40 % do 80 %.
- Pojistky: v zásuvce odpočet „zapnout za 3 h (Flip) / 2 h (router)“, obnovuje se každých 30 min, dokud Brána běží. Router bez přijaté pojistky nevypne. Baterii routeru nejde přečíst → nabíjí. Nad 42 °C se Flip nenabíjí.
- V detailu „Flip (brána) a Wi‑Fi“ řádek „Slunce navíc“ ukáže, proč se zrovna (ne)nabíjí.
- (5.59) Odpoledne, 3 h až 1 h před západem: Flip do 80 % a router do 90 % přímo z panelů, když panely pokryjí chatu i nabíjení – do noci jdou plné a solární baterie je v noci nemusí živit (ušetří ztrátu nabití a vybití).

**River dochází (5.68)**: upozornění při 15 % (vyměň River), 10 % a 5 % (nejvyšší priorita) a „River se vypnula“, když pod 5 % přestane dodávat. Znovu až po nabití nad 25 %.

**Denní restart Brány (Flip 1.9.11)**: každý den ve 22:10 (Nastavení → Brána) Brána sama restartuje Bluetooth, spojení se zásuvkami a hledání v síti. Aplikace se neukončuje. Po restartu přijde tichá zpráva „✓ Brána úspěšně restartována“, nebo s vysokou prioritou, co nefunguje. Když se Flip do 25 min neozve, přijde naléhavé upozornění.

**Malá River a 12V světla (5.81)**: když malá River napájí 12V osvětlení, přijde upozornění při 20 %, 10 % a 5 % s časem, kdy světla zhasnou, a když se vypne.

**Záložky v detailech (5.83)**: detail Teploty má záložky 🌡️ Data a ❄️ Chladnutí, detail Solární baterie 📊 Data (grafy) a ⏱ Teď a čísla. Web si pamatuje, kterou záložku jste měl otevřenou.

**Záložky (5.84)**: i detaily spotřeby (celkem, ze solární baterie, z River, Spotřebiče) mají 📊 Grafy a 🔢 Čísla, Generátor 📊 Data a ▶️ Start (spuštění nabíjení a palivo).

**River a generátor (5.85)**: vypnutá River ukazuje šedě poslední známé % s časem. Upozornění na málo nabitou River chodí jen když River opravdu dodává. Po skončení nabíjení z generátoru přijde souhrn: kolik dodal generátor, o kolik % a kWh se nabila která River a kolik z energie generátoru do River došlo.

**Noc – jen dvě pravidla (5.86)**: 1) Ve 22:00 (a dál do rána) hlídač spočítá, jestli solární baterie vydrží do rána nad 12,0 V. Když ne a chata jede ze soláru, přijde „⚠️ TEĎ přepni chatu na River“ a opakuje se, dokud nepřepneš nebo neťukneš „Přepínám“. 2) Podle skutečného napětí: pod 12,2 V varování, pod 12,0 V naléhavé. Večerní upozornění před 22:00 („nevydrží“, „sniž odběr“) už nechodí – předpověď je na webu v dlaždici Příští noc.

**Flip – upozornění na baterii (5.87)**: když nabíjení Flipu řídí hlídač, upozornění „Flip se nenabíjí“ přijde až pod 25 % (20 / 10 / 0 %). Nad 30 % se Flip nenabíjí schválně.

**Výhled dne (5.88)**: počítá s obvyklým odběrem chaty (medián posledních 7 dní), ne s posledními 3 hodinami – krátká špička tak výhled nezkazí.

**Nabíjení Flipu (5.91)**: když svítí, nabíjí do 80 % – začne, když panely pokryjí chatu i nabíječku, přestane při 80 % nebo když panely nepokryjí ani chatu. Jinak (noc, mrak, chata na River) jen pod 30 % a jen tolik, aby vydržel do rána. Proč: energie z panelů jde rovnou do nabíječky, večer by se brala ze solární baterie se ztrátou.

**Flip ve Floatu (5.92, Brána 1.9.12)**: když je solární baterie plná (Float), Flip se nabije doplna (100 %).

## Upozornění – tři druhy (5.95)

1. **Ohrožení chodu** (něco přestává fungovat) a 2. **doporučení s úkolem** (22:00 přepni na River, ráno „solár nevydrží“, po generátoru „vypni generátor“): přijde jedno upozornění s tlačítky **Řeším / Za 30 min / Za 1 h**. Dokud to trvá a nic neťukneš, přijde znovu po 10 min. Když se to spraví samo, přijde „✓ …“.
3. **Přehled**: všechno ostatní jen v souhrnu ve 22:00 („👀 K pozornosti“). Co právě trvá, je v souhrnu pod „🚨 Trvá“ a na webu v pruhu „K řešení“.

Solární baterie má jediné upozornění: pod 12,0 V „přepni chatu na River“. River jediné: pod 15 %, když z ní něco jede.

**Spotřeba chaty (5.96)**: jedna dlaždice místo „Chata celkem“ a „Spotřebiče“ – součet za dnešek, odběr teď, srovnání s obvyklou spotřebou a jednotlivé zásuvky.

**Kapacita a předpovědi (5.101)**: kapacitu solární baterie hlídač měří jen z doby, kdy byla baterie aspoň 2 h v klidu. Než má 2 takové testy, počítá se 150 Ah (Nastavení → Kapacita pro výpočty). Předpověď noci i výhled dne vychází z # a obvyklého odběru, takže si navzájem neodporují.
