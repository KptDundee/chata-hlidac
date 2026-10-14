# Verze

Číslo verze: soubor `VERSION` (hlídač), `WEB_VER` / `FLIP_VER` ve `web/index.html`, `versionName` v `android/app/build.gradle`.
Každá změna = +0.1. Aplikace pro Flip dostane nové číslo jen, když se mění její kód (FLIP_VER pak ukazuje, co je nejnovější).

## 3.41 – 14. 10. 2026
- **Flip 1.3.2 hlásí, jestli je na Wi‑Fi.** Po restartu routeru se Flip umí přepnout na mobilní data a pak nevidí zásuvky (14. 10. se to stalo). Hlídač pošle notifikaci „📶 Flip není na Wi‑Fi chaty“ a web to ukáže v liště k řešení.
- Flip 1.3.1: hledání zásuvek zapisuje do záznamu výsledek (sítě, kolik adres odpovídá, kolik zásuvek Tapo, chyby)

## 3.40 – 14. 10. 2026
- Hlídač sám převede zásuvku na číslo z jejího jména („(3) (R) …“ → 3), i když Flip pošle starou IP – funguje se starším Flipem i s ručním seznamem adres

## 3.39 – 14. 10. 2026
- Zásuvky přenastaveny na čísla z názvů (Flip 1.3): (1) měnič 220, (2) River žlutý, (3) River červený, (4) lednice, (5) wifi router, (6) malá River, (7) nabíjení z generátoru, (8) nabíjení River ze solár (automatika)

## 3.38 – 14. 10. 2026
- **Historie přímo ze zásuvek:** zásuvka Tapo si sama pamatuje hodinovou energii. Flip 1.3 ji z každé měřicí zásuvky pošle jednou denně a hned, když se zásuvka znovu objeví (generátor naskočil) – 7 dní zpět. Hlídač podle ní **opraví denní součty** zásuvek a **doplní / opraví běhy generátoru**, i když je Flip nezachytil (v seznamu „z historie zásuvky“ / „opraveno podle zásuvky“).
- Rychlé 30s hlídání z verze 3.37 zrušeno (Flip není na nabíječce, Android by ho stejně uspal). Pro přesný konec stačí před vypnutím generátoru dát na Flipu „Odeslat teď“.
- Flip si pamatuje i zásuvky, které při hledání v síti neměly proud; u zásuvky, která se znovu objeví, posílá čas objevení, a když zmizí, ještě 40 min poslední stav počítadla a čas zmizení.

## 3.36 – 14. 10. 2026
- **Flip 1.3: zásuvky podle čísla ve jménu, ne podle IP.** Flip sám prohledá síť (při spuštění, každých 6 h a když zásuvka zmizí), najde všechny zásuvky Tapo a pozná je podle čísla v první závorce jména v aplikaci Tapo – „(3) (R) River žlutý“ = zásuvka 3. Router může přidělovat adresy, jak chce. V Nastavení hlídače se pak zásuvky zadávají tímto číslem. Bez čísla ve jménu platí konec IP adresy jako dřív. Ruční seznam adres na Flipu dál funguje (a určí i další podsíť k prohledání).
- Web: jména zásuvek bez úvodních závorek, u zásuvky vidět číslo a IP

## 3.35 – 14. 10. 2026
- Zásuvky River přenastaveny na .188 (žlutá), .170 (červená), .166 (malá) – zásuvky dostaly od routeru nové adresy
- Dlaždice River řekne, když Flip zásuvku River nečte („? R3 · Flip zásuvku .165 nečte – přidej ji na Flipu“), a upozorní na zásuvky s „River“ v názvu, které nejsou přiřazené v Nastavení

## 3.34 – 14. 10. 2026
- **River podle zásuvek Tapo** (každá River má svou zásuvku na výstupu): dlaždice River má vždy záložky pro všechny River (● svítí ta, která právě napájí), ukazuje okamžitý výkon a „↑ dnes“ dodanou energii, i když EcoFlow data nechodí; % a nabíjení z EcoFlow, když jsou
- Spotřeba chaty: „teď: solár 30 W + R1 65 W“ – vidět, když chatu napájí víc zdrojů naráz; po zdrojích ze zásuvek (● = právě napájí)

## 3.33 – 14. 10. 2026
- **Pevná struktura hlavní stránky** – dlaždice se už nepřeskupují, mění se jen jejich obsah:
  - hlavička: vlevo čas dat z regulátoru a baterie Flipu, vpravo Načíst · ↻ · ⚙
  - tenká lišta **„Nic k řešení“ / „N věcí k řešení“** jen pro mimořádné věci (regulátor nebo Flip mlčí, Flip se vybíjí, baterie pod alarmem, odběr navíc, River skoro prázdná, vadné spoje…); ťuknutím podrobnosti. Pravidelné věci (noc, zítřek) tam nejsou
  - **Teď:** Solární baterie · River se záložkami pro každou River (● svítí = napájí nebo se nabíjí, šedá = vypnutá; i vypnutá ukáže poslední % a dnešní ↓ nabito / ↑ dodáno)
  - **Dnes:** Spotřeba chaty (celkem + solár + každá River) · Výroba a nabíjení (slunce → baterie, slunce → River, generátor, do River celkem)
  - **Výhled:** noc, zítřek · Uplynulé · Dlouhodobě – pevné pořadí
- Hlídač počítá pro každou River denní energii: nabito a dodáno (z EcoFlow), první a poslední %

## 3.32 – 14. 10. 2026
- **Záznam běhů generátoru:** hlídač si pamatuje každý běh (od–do, kolik dodal přes zásuvku Tapo, River z → na %, nabito kWh, účinnost). Na hlavní stránce dlaždice „⛽ Generátor běží“ a po vypnutí „poslední běh …“ ještě 36 h; ťuknutím seznam všech běhů. Po skončení běhu notifikace „⛽ Generátor doběhl“ se souhrnem.

## 3.31 – 14. 10. 2026
- **Generátor a nabíjení River na hlavní stránce:** když generátor dodává (zásuvka Tapo generátoru) nebo je online v EcoFlow, nebo když se River nabíjí mimo automatiku, nahoře se objeví dlaždice „⛽ Generátor běží / River se nabíjí“ – výkon, % River, za jak dlouho bude plná, kolik dnes dodal generátor. Dřív to bylo schované jen v detailu baterie.

## 3.30 – 14. 10. 2026
- **Baterie Flipu nahoře na stránce:** „📱 Flip 64 % · ⚡ nabíjí se“ / „nenabíjí se!“ (oranžově), pod 20 % červeně, a když Flip mlčí, „mlčí před …“
- **Notifikace po stupních** 50, 30, 20, 10 a 0 % (když se nenabíjí) – každý stupeň jednou, po nabití znovu; od 20 % vyšší priorita. Nastavení `telefon_upozornit`
- Notifikace „Brána neposílá data“ řekne, kolik % měl Flip naposledy a jestli se nabíjel (vybitý Flip vs. jiná příčina)

## 3.29 – 14. 10. 2026
- **Generátor EcoFlow Smart Generator** (SN „DG…“) z účtu EcoFlow se už nepočítá jako River (nepletl by výdrž River ani automatiku). Na webu v sekci River vlastní karta „⛽ … (EcoFlow)“ s online stavem a rozbalovacím seznamem všeho, co generátor posílá – podle toho se pak udělá pořádná dlaždice (výkon, palivo, olej, motohodiny).

## 3.28 – 14. 10. 2026
- Regulátor mlčí: místo jedné „diagnózy“ seznam možných příčin (zaseknutý Wi‑Fi modul regulátoru, vypadlá Wi‑Fi / router, regulátor bez napájení, výpadek cloudu) a tip „vypni a zapni Wi‑Fi modul regulátoru“; když je router na zásuvce Tapo, řekne, jestli má proud

## 3.27 – 14. 10. 2026
- **Regulátor neposílá data:** poplach už po **30 min** (dřív 120). Notifikace řekne, od kdy mlčí a proč nejspíš: když Flip posílá, internet na chatě jde → regulátor nemá napájení z baterie (pojistka, kabel) nebo vypadl Wi‑Fi modul; přidá napětí z Victronu. Když se zase ozve, přijde „Regulátor zase posílá data“.
- Web při mlčícím regulátoru: červený verdikt „Regulátor neposílá data – údaje níže nejsou aktuální“, červená hlavička „Regulátor mlčí od dnes 12:06 – jeho údaje jsou STARÉ“, dlaždice baterie ukazuje aktuální napětí z Victronu a zvlášť poslední (staré) z regulátoru.

## 3.26 – 14. 10. 2026
- **River jako zdroj chaty:** hlídač pozná, která River teď chatu napájí (výstup EcoFlow > příjem), a spočítá, na jak dlouho vydrží při průměrném odběru za poslední 3 h (kapacita 768 Wh, rezerva 5 %, ztráty měniče River ~10 % – vše v Nastavení).
  - Web: nahoře široká dlaždice **„River 2 Pro – napájí chatu“** (%, výdrž v hodinách, „Do zítřejšího rána vydrží – zítra ráno ~35 %“ / „Vybije se dnes ~23:40 – do zítřejšího rána nevydrží“); dlaždice noci počítá s River; baterie se jmenuje „Solární baterie teď“
  - Notifikace večer: „🔋 River do zítřejšího rána nevydrží“ (jednou za noc)
  - Hodinky (dlaždice): „🔋 River 62 % · ~10 h / do zítra 3:40“ místo předpovědi solární baterie – bez nové verze aplikace v hodinkách; komplikace dál ukazuje napětí

## 3.25 – 14. 10. 2026
- Dlaždice Baterie teď při odběru navíc už neradí „vypni River“ naslepo: ukáže rozpad (za měničem X W: lednice, světla/kamery/wifi, River) a „Co dalšího je zapnuté? Odpoj to“. Když se opravdu nabíjí River, napíše to zvlášť (automatika ho při vybíjení vypne sama). Nabíjení River se do „navíc“ nepočítá.

## 3.24 – 14. 10. 2026
- **Rozbor nocí z historie:** hlídač si z historie regulátoru (Solar Guardian: napětí, proud, režim, teplota baterie) a z hodinové spotřeby zásuvky za měničem (Tapo) spočítá posledních **90 nocí** (`nh`) – večerní napětí, ranní minimum, kolik Ah regulátor přes den dodal a kolik z toho čistě zůstalo v baterii, od kdy byla ve Float, kolik se přes noc odebralo, délka noci, teplota. Karta 🔎 tak porovnává posledních 5 nocí s obdobím, kdy to bylo v pořádku (ne jen s 14 dny vlastních měření). Načítá se postupně, plně za ~1 h.

## 3.23 – 14. 10. 2026
- **🔎 Proč je ranní minimum takové** (detail noci z dneška na zítřek i noci ze včerejška na dnešek): porovná posledních 5 nocí se staršími (14 dní podrobných měření) a vypíše, co se změnilo – jak moc se baterie přes den nabila (čistý přítok Ah, výroba, Float), kolik se přes noc odebralo (Ah, W, lednice, světla/kamery/wifi, délka noci), jak rychle napětí klesá na 10 Ah a teplota baterie. Pod tím tabulka po nocích.

## 3.22 – 14. 10. 2026
- „Odběr navíc“ zase hned při první kontrole (bez čekání na 2 běhy – radši falešný poplach než vybitá baterie, třeba při 600 W)
- Když zásuvka lednice nepošle hodnotu, počítá se s lednicí naplno (**80 W**, Nastavení → „Lednice naplno“), ne s 0 W. Notifikace pak píše „lednice neměřená – počítám ~80 W“
- Potvrzeno z notifikace 14. 10. 8:43: „běžně ~13 W“ = lednice chyběla, 66 W za měničem byl běžící kompresor

## 3.21 – 14. 10. 2026
- **Falešný poplach „Odběr navíc“:** když zásuvka lednice zrovna neposlala hodnotu (chyba čtení), brala se lednice jako 0 W a běžící kompresor (~60 W) se hlásil jako odběr navíc. Teď se bez platného měření lednice nic nepočítá, poplach přijde až když odběr navíc trvá **2 kontroly po sobě** a notifikace i Deník ukazují celý rozpad: měnič = lednice + běžně + navíc

## 3.20 – 14. 10. 2026
- **Jedno pravidlo pro čas:** ráno / noc / večer / den se všude píše vždy s *dnes / zítra / včera* (nebo *dnešní / zítřejší / včerejší*), žádné názvy dní v týdnu vedle toho. Platí pro dlaždice, verdikt, detaily, kartu Počasí, Nastavení, notifikace i hodinky.
  - Noci se jmenují oběma dny: **Noc z dneška na zítřek** (přes den a večer), **Noc ze včerejška na dnešek (běží)** (po půlnoci do východu), v Uplynulých **Noc ze včerejška na dnešek**
  - Napětí „12,11 V zítra ráno“, texty „Do zítřejšího rána vydrží“, „Zítra ráno bude baterie slabá“, „Včera večer 12,54 → dnes ráno 11,98 V“, „Od dnešní půlnoci chata spotřebovala…“
  - Notifikace: „Baterie do zítřejšího rána nejspíš nevydrží“, „měnič se vypne zítra ~3:40“; hodinky „🌙 zítra ráno ~12,2 V ✓“
- Opraveno: karta Počasí psala u varování den, *po kterém* je ráno slabé, místo dne toho rána; pod sloupcem dne je teď napětí **ten den ráno**
- Opraveno: večerní souhrn psal u zítřka napětí „ráno pak“ z pozítřího rána – teď „zítra ráno … · pozítří ráno …“

## 3.19 – 14. 10. 2026
- Noci se jmenují podle rána: **Noc na čtvrtek**, **Minulá noc (na středu)**; napětí „V čt ráno“, text „Zítra (čt) ráno bude baterie slabá“ – žádné „ráno“ bez určení dne

## 3.18 – 14. 10. 2026
- **Oddělená minulost a budoucnost.** Dlaždice podle denní doby:
  - **Dnes** – ráno předpověď výroby na dnešek, přes den „vyrobeno zatím z předpovědi“, po západu výsledek dne a bilance; spotřeba vždy „od půlnoci“
  - **Příští noc** – přes den „Dnes v noci“ (odhad ráno podle počasí), po západu přesná předpověď („Dnešní noc“ / „Noc teď“)
  - nová sekce **Uplynulé**: **Minulá noc** (večer → nejníž → ráno, odebráno, předpověď vs skutečnost) a **Včera** (výroba vs předpověď, spotřeba)
- **Noční předpověď se učí:** hlídač si hodinu po západu zapíše očekávané ranní napětí, ráno změří skutečnost a medián rozdílu z posledních 10 nocí opravuje další předpovědi (max ±0,4 V); zpětně doplněno ~12 nocí
- **Oprava spotřeby zásuvek za den:** počítá se z přírůstků počítadla Tapo (počítadlo se nenuluje přesně o půlnoci – dřív se do nového dne přenesla část včerejška, např. 0,95 kWh už v 8 ráno)
- Opraveno: odhad „Dnes v noci“ bral napětí o den později

## 3.17 – 13. 10. 2026
- Detail Baterie teď a Dnes: přepínač i **Rok** a **Vše** – nejnižší a nejvyšší napětí dne a výroba po měsících za poslední rok / celou historii (i minulé roky)

## 3.16 – 13. 10. 2026
- Graf do baterie / z baterie: část pod nulou (vybíjení) červeně, nad nulou zeleně

## 3.15 – 13. 10. 2026
- V detailech vždy nejdřív data, potom vysvětlení (Baterie, Noc, Počasí – sloupce před doporučením, Zdraví baterie – verdikt a graf před vysvětlením)
- Detail Dnes: výroba po dnech / měsících / letech (dlouhodobý přehled)
- Všechny údaje: co zatím není na žádné dlaždici, je označené fialovým rámečkem NEPOUŽITO (odběr teď s údaji Victronu, graf nabití v %, graf odběru z měniče)

## 3.14 – 13. 10. 2026
- Dlaždice Dnes je oranžová, když baterii za den po ztrátách ubylo (jen informace – nepočítá se do „věcí k řešení“)

## 3.13 – 13. 10. 2026
- Detail **Dnes**: přehledné účetnictví energie – výroba, spotřeba chaty (lednice, běžný odběr, navíc), ztráty (účinnost a vlastní spotřeba měniče, nabíjení AGM) a výsledná bilance baterie; dlaždice Dnes říká, kolik baterii po všech ztrátách přibylo / ubylo

## 3.12 – 13. 10. 2026
- Každá dlaždice otevře jen to, co k ní patří (Baterie, Noc, Dnes mají vlastní přehled a grafy s přepínačem Dnes / 48 h / Týden)
- Patička: 🗂 Všechny údaje – kompletní původní přehled, aby se nic neztratilo

## 3.11 – 13. 10. 2026
- **Nová hlavní stránka**: nahoře verdikt (Všechno v pořádku / 1 věc k řešení + co udělat), pod tím dlaždice Teď (baterie, noc, zítra, River, dnes) a Dlouhodobě (kabely a spoje, zdraví baterie, panely, systém). Problémové dlaždice jsou vždy první, barevný proužek ukazuje stav.
- Podrobnosti, grafy a vysvětlení se otevřou až po ťuknutí na dlaždici (detail); Deník v patičce

## 3.10 – 13. 10. 2026
- Upozornění „blíží se zimní provoz“ a karta počasí: místo matoucího „chata potřebuje 1,07 kWh“ rozpad – kolik spotřebuje chata sama, kolik vezme měnič (účinnost + vlastní spotřeba) a kolik ztráty při nabíjení baterie

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
