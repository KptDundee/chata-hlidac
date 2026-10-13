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

### Nahoře
- **CHATA – ELEKTŘINA v3.10**: číslo verze webu. Úplně dole je řádek *Verze: web · hlídač · Flip*. Když je něco červeně, je potřeba aktualizovat (typicky aplikaci na Flipu).
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
- **🌙 Do rána vydrží / těsně / nevydrží**: předpověď na noc (po západu slunce): napětí teď a odhad k ránu.
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
| 🌙 Baterie do rána nejspíš nevydrží | Podle odběru a stavu baterie dojde v noci pod alarm | Odpoj něco, ráno počítej s River |
| ⚡ Nabíjecí proud X A – blízko pojistky | Proud z regulátoru nad 33 A (110 % pojistky 30 A) | Pokud jsou zapojené 2 panely, jeden odpoj |
| ⚠️ Odpoj druhý panel | Blíží se jaro, za jasného dne by hrozilo přes ~34,5 A | Odpoj druhý panel do uvedeného data, přepni v Nastavení |
| 🔆 Zapoj druhý panel / ⏳ jeden nestačí, druhý ještě ne | Podzim: jeden panel nestačí; druhý je / ještě není bezpečný | Podle zprávy; po přepojení přepni v Nastavení |
| 🍂 Blíží se zimní provoz / 🌱 Můžeš přejít na letní | Výroba na příští dny nestačí / už stačí | Zvaž přepojení chaty na River / zpět |
| ☀️ Zítra můžeš chatu připojit na solární baterii | Zima: solární baterie bude ráno dost nabitá | Přes den připoj chatu na solár, večer zpět na River |
| 💡 V noci šlo víc/míň proudu na světla/kamery/wifi | Ostatní odběr se výrazně změnil | Nezůstalo něco zapnuté? Nevypadla kamera / wifi? |
| ⚡ Odběr navíc ~X W – bere se z baterie | Přes den je odběr za měničem aspoň o 40 W nad běžný (lednice + světla, kamery, wifi) **a** baterie se vybíjí (pod −2 A). Kvůli běžnému odběru (zašlé slunce) nepřijde | Omez nabíjení zařízení; nejvýš 1× za hodinu |
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

## 8. Hodinky

- **Komplikace** „Chata – napětí baterie“: dlouze podrž ciferník → Upravit → místo komplikace. *V?* = data starší než hodina, *V!* = kritické napětí.
- **Dlaždice** „Chata“: napětí (barevně), nabití podle regulátoru, panely, odběr, předpověď. Ťuknutím se obnoví.
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
