# Verze

Číslo verze: soubor `VERSION` (hlídač), `WEB_VER` / `FLIP_VER` ve `web/index.html`, `versionName` v `android/app/build.gradle`.
Každá změna = +0.1. Aplikace pro Flip dostane nové číslo jen, když se mění její kód (FLIP_VER pak ukazuje, co je nejnovější).

## 4.86 – 23. 10. 2026
- Nabíjení River ze soláru se zase samo zapne: místo vypnutí v nastavení (4.85) automatika pozná, že zásuvka (8) není vidět (vypínač – 3 měření po sobě), čeká a nic neposílá. Jakmile se zásuvka objeví (na jaře zapneš vypínač), běží sama dál a přijde zpráva „Nabíjení River ze soláru zase běží“. Nastavení vráceno na zapnuto.

## 4.85 – 23. 10. 2026 · Flip 1.7.5
- Flip 1.7.5: světelné pásky / světla Tapo (modely L…) – zapnuto / vypnuto a spotřeba dnes (Wh) z get_device_usage. Je to odhad světla (jako v aplikaci Tapo), okamžitý příkon světlo neměří. Na webu ve Spotřebičích „0,02 kWh odhad · svítí“.
- Dlaždice „Ze soláru“ přejmenována na „Ze solární baterie“ (je to odběr přes měnič, ne výroba panelů).

## 4.84 – 23. 10. 2026
- Dlaždice EcoFlow: River zapnutá, ale její zásuvka se nečte → „zapnutá · zásuvka (6) nečte“ (dřív chybně „AC výstup vypnutý“ – nerozlišíme, jestli je zásuvka bez proudu, nebo ji Flip nevidí).

## 4.83 – 23. 10. 2026
- EcoFlow: všechny River i generátor se čtou přes přihlášení aplikace (živá data, u River 2 Pro 175 údajů místo 20). Vývojářské rozhraní u červené vracelo starou hodnotu „nabíjí 150 W“ (inv.inputWatts), když už nenabíjela. Vývojářské rozhraní zůstává jako záloha, když aplikace neodpoví. Řádek „zkouška …“ jen u zařízení, které nejde přečíst.

## 4.82 – 23. 10. 2026
- Oprava: dlaždice Generátor, Ze soláru a Z River ukazovaly „undefined“ (chyba ve 4.79 / 4.80 – hodnota zakomentovaná).
- Malá River už nedostává „do rána nevydrží“ ani „vyměň River“ – chatu nenapájí. Upozornění „River do rána nevydrží“ jen když chata opravdu jede z velké River (ne ze soláru).
- Dlaždice EcoFlow: zásuvka na výstupu River bez proudu není chyba – „vypnutá“, nebo když ji EcoFlow vidí online „zapnutá · AC výstup vypnutý“ (místo „Flip zásuvku (6) nenašel“).
- Karta „EcoFlow – připojení“: u každé River všechny výkony, které EcoFlow hlásí (k vyřešení „nabíjí 151 W“, když nenabíjí).

## 4.81 – 23. 10. 2026
- EcoFlow: River, která je offline, má výkon nabíjení / odběru 0 – EcoFlow u offline zařízení vrací poslední hodnoty, takže „nabíjí se 150 W“ viselo i po odpojení. U výkonu River na dlaždici EcoFlow stáří údaje („před 8 min“), když je starší než 5 min.

## 4.80 – 23. 10. 2026
- Spotřeba dnes: dlaždice Z River zelená jen když některá River právě dodává proud (zásuvka na jejím výstupu > 2 W), jinak šedá. Stejně Ze soláru – šedá, když měnič nic nedodává.

## 4.79 – 23. 10. 2026
- Dlaždice Generátor (Výroba dnes) šedá, když generátor neběží (jako Solár v noci).

## 4.78 – 23. 10. 2026
- Dlaždice EcoFlow – záložky: vypnutá River šedě, zapnutá plným písmem se zelenou tečkou (EcoFlow ji vidí online; bez EcoFlow = zásuvka na jejím výstupu má proud; generátor = běží), rámeček = údaje pod záložkami patří téhle. Nabíjení z jiné River se nerozlišuje (výjimečná situace) – „nabíjí se · W“, z generátoru jen když běží; River, která něco napájí: „dodává W“.
- Dlaždice Solární baterie – barva podle výhledu: zelená jen když vydrží do rána; do 22:00 ano, do rána ne → oranžová; ani do 22:00 → červená (po západu podle noční předpovědi: vypne se před 22:00 červená, později oranžová; těsně / „sniž odběr“ oranžová). Chata na River: beze změny.
- Dlaždice Solár (výroba): šedá, když panely nevyrábí (noc).

## 4.77 – 23. 10. 2026
- Oprava vymyšlených stavů na dlaždici EcoFlow: „generátor běží“ a „nabíjí se z generátoru“ u River, které se vůbec nenabíjely. Hlídač bral jako běh generátoru i to, že se některá River nabíjí (červená z malé). Teď běh generátoru jen podle jeho zásuvky (7); „běh“ vzniklý jen z nabíjení River se zahodí. River: „nabíjí se z generátoru“ jen když generátor opravdu běží, „nabíjí se z malé“ když jiná River dává podobný výkon, jinak „nabíjí se · W“ bez zdroje; River, která dává výkon, „dodává W → nabíjí červenou“. River bez dat z EcoFlow při běžícím generátoru: „generátor běží – nabíjí se?“.

## 4.76 – 23. 10. 2026
- EcoFlow přes přihlášení aplikace (krok 2): generátor a malá River (u vývojářského rozhraní 1006) se čtou stejnou cestou jako aplikace EcoFlow – přihlášení e-mailem a heslem (GitHub Secrets ECOFLOW_EMAIL, ECOFLOW_PASSWORD), MQTT aplikace, dotaz „latestQuotas“. Malá River: % a nabíjení jako u velkých. Generátor: palivo %, výkon, max. výkon, typ, stav motoru, režim + všechny číselné údaje k dohledání benzín / plyn (karta „EcoFlow – připojení“ → „Všechny údaje generátoru“). Neoficiální cesta – když EcoFlow přihlášení odmítne, další pokus až za hodinu (ať účet nezablokuje). Token se pamatuje ve stavu hlídače (šifrovaná data), přihlášení nejvýš 1× za týden.

## 4.75 – 23. 10. 2026
- Oprava: noci, kdy chata jela z River (aspoň 20 % noci bez odběru přes měnič), se už nepočítají do učení noční předpovědi napětí – solární baterie neměla odběr, takže „bylo o 0,44 V víc“ nic neříká a kazilo opravu dalších předpovědí. Označí se i zpětně (body za 14 dní). Na webu „chata jela z River – nepočítá se“. (Výhled dne v Ah takové noci vynechával už dřív.)

## 4.74 – 23. 10. 2026
- Oprava: dlaždice Solární baterie („do rána ne“) a Noc („do zítřejšího rána vydrží“) si odporovaly – každá brala jiný výpočet. Teď obě stejně: po západu noční předpověď (napětí, odběr za poslední hodinu, oprava z minulých nocí – podle ní chodí i večerní upozornění), přes den výhled dne (stejný jako „do 22:00 / do rána“ na dlaždici baterie).

## 4.73 – 23. 10. 2026
- Lednice: graf „Jak dlouho kompresor běžel“ – % dne po dnech (30 dní). Z měření zásuvky lednice, každé měření váží čas do dalšího (bez průměrování; mezery nad 15 min se nepočítají). V bublině hodiny běhu, počet rozběhů, příkon za běhu a za kolik hodin jsou data; den s daty pod 20 h je světlejší. Hlídač si to ukládá do denních součtů, takže graf vydrží i po smazání podrobných bodů (14 dní).

## 4.72 – 23. 10. 2026
- Upozornění „🔌 (1) 220 měnič není vidět“: zásuvky, které mají být vidět pořád (Nastavení → Zásuvky, výchozí 1, 4, 5, 9), hlídač hlídá podle čísla a jména. Když je Flip nepřečte ve 2 měřeních po sobě a aspoň 8 min (přepnutí solár / River chvíli trvá), přijde upozornění s důvodem (nenalezena / bez proudu / odmítá přihlášení) a po návratu „je zase vidět“. Zásuvka měniče jen když Victron hlásí, že měnič běží. Na webu dlaždice Systém → Problém. Zásuvky, které mají proud jen někdy (River, generátor, nabíjení ze soláru), se nehlídají.

## 4.71 – 23. 10. 2026 · Flip 1.7.4
- Flip 1.7.4 – zásuvky s novou adresou hned: když některá známá zásuvka na své adrese neodpovídá (River, generátor, nabíjení se zapnou a router jim dá jinou IP), Flip v tomtéž měření prohledá síť, přihlásí se jen na adresy, které nepatří fungujícím zásuvkám, pozná zásuvku podle čísla ve jméně („(7) …“) a hned ji přečte na nové adrese. Do záznamu: „Zásuvky na nové adrese: (7) → .xxx“. Zásuvky, které odmítají přihlášení (401), zkouší jen 1× za hodinu. Nahrazuje hledání generátoru z 1.7.3.
- Zásuvky bez čísla ve jméně se takhle dohledat nedají (jen plným hledáním po 6 h) – v aplikaci Tapo jim dej číslo do jména.

## 4.70 – 23. 10. 2026
- EcoFlow zkouška generátoru / malé River (4.67) už jen 1× za den, když je generátor online (35 s). Spouštěla se při každém ručním spuštění – to je i každé odeslání z Flipu, a s Flipem po 2 min by hlídač zbytečně zdržovala (běh 1 min 45 s místo ~20 s).

## 4.69 – 23. 10. 2026 · Flip 1.7.3
- Flip 1.7.3 – nabíjení z generátoru: dokud zásuvka generátoru (7) bere proud, Flip měří a posílá každé 2 min (jinak 10 min) → hlídač běží stejně často a hned přerozděluje výkon River. Po vypnutí generátoru ještě ~5 min po 2 min (zaznamená konec), pak zpět na 10 min.
- Flip 1.7.3: když zásuvka generátoru chybí, Flip ji v síti hledá při každém měření (po startu generátoru může mít jinou adresu – dřív nejdřív za 30 min). Tlačítko „Odeslat teď“ síť prohledá vždy. Častá hledání se do záznamu nezapisují, dokud se nic nezmění.

## 4.68 – 23. 10. 2026
- Nabíjení z generátoru (krok 1 – bez dat z generátoru): hlídač při běhu generátoru nastavuje nabíjecí výkon velkých River (River 2 Pro přes EcoFlow) tak, aby se nabily zároveň a generátor jel naplno = co nejkratší běh. K dispozici = max. generátoru podle paliva (benzín 1800 W / plyn 1600 W ze štítku) − rezerva 100 W − co bere malá River (zásuvka generátoru − příjem velkých). Rozdělení podle toho, kolik které chybí do 100 %, 200–940 W na River; nejdřív se snižuje, pak zvyšuje. Po běhu nastaví velkým 650 W, ať příští start nepřetíží generátor. Upozornění „Generátor běží naprázdno – vypni ho“, když je zásuvka generátoru pod proudem a nic nebere.
- Web: karta „Nabíjení z generátoru“ (detail EcoFlow i Generátor) – výkon generátoru, malá River, nastavení každé River, kdy bude plná a kdy generátor vypnout. Nastavení → Generátor: řízení, palivo, max. výkony, rezerva, výkon po běhu.
- EcoFlow zkouška (4.67) potvrdila: generátor a malá River i při zapnutí 1006, MQTT od nich nic – údaje přes vývojářské rozhraní nedávají.

## 4.67 – 23. 10. 2026
- EcoFlow: u generátoru a malé River (chyba 1006 u „všech údajů“) hlídač zkouší jiné cesty – vybrané údaje (POST /device/quota: palivo pd.oilVal, typ pd.type, výkon, max. výkon pd.oilMaxOutPower …) na obou serverech EcoFlow a 35 s poslech MQTT (oficiální certifikát pro vývojáře). Spouští se při ručním spuštění a sám, když je generátor online (nejvýš 1× za 30 min, generátor rychle usíná). Výsledek v kartě „EcoFlow – připojení“ pod zařízením („zkouška …“).

## 4.66 – 23. 10. 2026
- EcoFlow: zkušební nastavení nabíjecího výkonu River (workflow vstup `efset` „konec SN:W“, PUT /device/quota, acChgCfg). V kartě „EcoFlow – připojení“ odpověď EcoFlow a nastavené nabíjecí výkony (klíče *chg*watt*) k ověření.

## 4.65 – 23. 10. 2026
- EcoFlow funguje: žlutá a červená (River 2 Pro) posílají nabití, spárování podle jména sedí. Malá (River 2) a Smart Generator: EcoFlow přes vývojářské rozhraní údaje nedává (chyba 1006) – na webu „EcoFlow % neposílá“ / „tento model … nepodporuje“ místo chyby.

## 4.64 – 23. 10. 2026
- EcoFlow diagnostika: u každého zařízení v kartě „EcoFlow – připojení“ kolik údajů EcoFlow vrátil (nebo chyba) a všechna čísla nabití, která posílá (k porovnání s displejem).

## 4.63 – 23. 10. 2026
- EcoFlow: zrušeno párování zásuvek s River „podle pořadí“ (přiřazovalo procenta jiné River). Páruje se ručně podle konce SN (Nastavení), podle jména, nebo podle prvních 3 písmen prvního slova (zlu / cer / mal).

## 4.62 – 23. 10. 2026
- EcoFlow: spárování podle jména bez diakritiky („Žlutá“ = „ZLUTA“). Kapacita každé River podle modelu z EcoFlow (River 2 Pro 768 Wh, menší modely méně) – nabití z generátoru a výdrž se počítají s ní. Když model posílá nabití pod jinými názvy (malá River), v kartě „EcoFlow – připojení“ se ukáže, co posílá – podle toho se doplní.

## 4.61 – 23. 10. 2026
- Nastavení: nový typ pole pro volný text – jména teploměrů a spárování River (dřív pole nechávalo jen číslice a jména teploměrů by se smazala).
- EcoFlow: ruční spárování zásuvek River se zařízeními EcoFlow (Nastavení „Spárování River s EcoFlow“: `číslo zásuvky:konec SN`). Karta „EcoFlow – připojení“ ukazuje, jak je co spárované.

## 4.60 – 23. 10. 2026
- EcoFlow: při chybě se ukáže odpověď obou serverů (Evropa api-e i USA api), ne jen posledního.

## 4.59 – 23. 10. 2026
- EcoFlow – diagnostika: hlídač ukládá, co EcoFlow API vrátilo (seznam zařízení na účtu: jméno, konec SN, online, %), nebo chybu. V detailu EcoFlow karta „EcoFlow – připojení“; v dlaždici místo „až z EcoFlow“ „EcoFlow chyba“ / „EcoFlow nespárováno“.

## 4.58 – 23. 10. 2026 (Flip 1.7.2)
- Flip 1.7.2: router M7000 posílá odpovědi zakódované v base64 – aplikace je teď rozbalí (dřív chyba „Value ewoJ… cannot be converted to JSONObject“).

## 4.57 – 23. 10. 2026 (Flip 1.7.1)
- Flip 1.7.1: tlačítko „Zastavit bránu“ neutrální barvou (červená vypadala jako chyba).
- docs/pokracovani.md – shrnutí pravidel a otevřených věcí pro pokračování v novém chatu.

## 4.56 – 23. 10. 2026 (Flip 1.7.0)
- **Flip 1.7.0 – nový vzhled aplikace:** karty (Stav, Ovládání, Nastavení, Oprávnění, Záznam), tmavý vzhled. Nastavení je zamčené – jen přehled (hesla skrytá), upravuje se po „✏️ Upravit nastavení“ → Uložit / Zrušit. U každého tlačítka „?“ s vysvětlením. Záznam se rozbaluje.
- **Baterie routeru M7000 – zatím jen čtení:** Flip se přihlásí do webového rozhraní routeru (heslo správce ve Flipu) a pošle stav baterie. Na webu v dlaždici Flip řádek „router M7000“ (nebo důvod, proč čtení nejde). Řízení nabíjení až po ověření.

## 4.55 – 23. 10. 2026
- Solární baterie / hlavička: „chata na River“ jen když River opravdu dodává. Když měnič nemá proud a River nedodává (třeba právě při přepínání River → solár, než zásuvky naběhnou), píše se „měnič vypnutý“ / „měnič bez proudu“.

## 4.54 – 23. 10. 2026
- Dlaždice Flip: místo „až s Flip 1.6“ skutečný důvod, proč řízení nabíjení neběží – stará verze (s číslem), Flip nevidí zásuvku (9), zásuvka nedostupná / odmítá přihlášení.

## 4.53 – 22. 10. 2026 (Flip 1.6.0)
- **Nabíjení Flipu zásuvkou (9):** hlídač posílá povolení (ntfy <téma>-fc): chata na River → kdykoli, chata na soláru → jen když panely dodávají (≥ 30 W). Flip sám a i bez internetu: pod 20 % nabíjí vždy, od 80 % vypne (znovu pod 75 %), **nad 42 °C vypne** (zpět pod 36 °C), bez spojení s hlídačem nabíjí pod 40 %. Při vypnutí odpočet v zásuvce „za 3 h zapnout“ (pojistka, když aplikace spadne). Upozornění „🔥 Flip je horký“ nad 40 °C.
- **Po restartu telefonu brána naběhne sama i bez odemčení** (Direct Boot – nastavení v úložišti dostupném před zadáním PIN, start při LOCKED_BOOT_COMPLETED). Dřív po restartu (aktualizace) čekala, až někdo Flip odemkne.
- Web: dlaždice **📱 Flip** (baterie, nabíjení a proč, teplota, vydrží do) s grafy baterie a teploty, a **🧊 Lednice** (kompresor teď, podíl běhu za 24 h vs obvykle, rozběhy, teplota z teploměru) s grafy a doporučeními. Historie baterie a teploty Flipu se ukládá do bodů.
- Nastavení: zásuvka nabíječky Flipu, řídit nabíjení, Flip horký nad.

## 4.52 – 22. 10. 2026 (Flip 1.5.0)
- **Teploměry Xiaomi** (Mi Temperature and Humidity Monitor 2 / LYWSD03MMC, originální firmware): Flip poslouchá jejich Bluetooth vysílání (MiBeacon, šifrované – klíč „BLE KEY“ z účtu Xiaomi) a posílá teplotu, vlhkost a baterii. Ve Flipu nové pole „Teploměry Xiaomi“: řádky `MAC KLÍČ jméno`.
- Web: dlaždice **Teploty** (u Spotřebičů). Nastavení: teploměr u solární baterie (jeho teplota má přednost před regulátorem – mráz, kapacita v chladu), teploměr v lednici + upozornění, když je v lednici tepleji než 8 °C déle než 30 min.

## 4.51 – 22. 10. 2026
- **Výdrž Flipu:** hlídač si pamatuje baterii Flipu (24 h) a z posledního úseku bez nabíjení spočítá, jak rychle ubývá. Když se nenabíjí a pod 15 % klesne do 12 h → „📱 Flip se nenabíjí – vydrží jen do ~HH:MM“ (jednou za vybíjení). V ranní čas z rozvrhu (před odjezdem), když se vybije do 48 h → „📱 Než odjedeš: Flip se nenabíjí…“. Stupně 50/30/20/10/0 % zůstávají.
- Web: v hlavičce u Flipu „vydrží do …“, upozornění nahoře i s časem.

## 4.50 – 22. 10. 2026
- **Zvýšený odběr večer (PC…):** když by baterie do rána nevydržela jen kvůli tomu, že teď chata bere víc než běžně v noci, přijde nejdřív rada „🌙 Aby solár vydržel do rána, sniž odběr do HH:MM“ (běžný noční odběr = medián nocí za 7 dní, s rezervou 10 %). „Nevydrží – přepni na River“ a naléhavé ve 22:00 až když se do té doby odběr nesníží. Dlaždice Noc ukazuje totéž.
- Noční předpověď bere odběr za **poslední hodinu** (dřív 3 h) – po vypnutí PC se spraví do hodiny.
- Stav baterie z napětí: při větším odběru se počítá s větším poklesem napětí (~10 mΩ) – dřív pod zátěží vycházel horší.

## 4.49 – 22. 10. 2026
- **Plné nabití solární baterie:** když regulátor 14 dní nepřešel do Floatu, jedna klidná připomínka (Výchozí, přes den), další nejdřív za týden. Na webu jen tichý řádek nahoře (jako zdraví baterie). V Zdraví baterie „Naposledy plně nabitá“. Nastavení: Připomenout plné nabití po (dní).

## 4.48 – 22. 10. 2026
- **Hlídání lednice** (zásuvka lednice): upozornění, když kompresor stojí déle než 3 h (nechladí – porucha, vypnutá), běží bez přestávky déle než 2 h (dveře, námraza), nebo zásuvka lednice ≥ 1 h nejde přečíst, když ostatní jdou. Hranice se přizpůsobí posledním 7 dnům (×1,5 nejdelšího běžného stání / běhu) – v zimě ve studené chatě stojí kompresor déle. Po návratu do normálu „✓ Lednice zase normálně běží“. Na webu nahoře.
- **Mráz u solární baterie** (teplota z regulátoru): první mráz v sezóně – informace; mráz a nabití pod 40 # → upozornění (vybitá AGM může zamrznout). Na webu nahoře.
- **Kapacita v chladu:** výhled dne / do rána i noční předpověď počítají s menší kapacitou (−0,6 %/°C pod 15 °C; 0 °C ×0,91). V rozpisu výhledu řádek „Kapacita v chladu“.
- Nastavení: Hlídat lednici, hranice v hodinách; Hlídat mráz, teplota, hranice #.

## 4.47 – 21. 10. 2026
- Kabely a spoje: web bere stejnou hranici jako upozornění hlídače (Nastavení – odpor kabelů, 20 mΩ). Dřív byla dlaždice žlutá a nahoře upozornění už od 10 mΩ – po opravě spojů (~10 mΩ) svítilo, i když hlídač napsal „v normě“. Teď: pod hranicí zelená a nic nahoře; nad hranicí nebo při nepotvrzeném/potvrzeném poplachu upozornění + návod.

## 4.46 – 21. 10. 2026
- Poplach „🔥 Velký úbytek napětí na kabelech“ má vždy pokračování z dalšího spárovaného měření: **potvrzení** („trvá – 2., 3., 4. měření po sobě“, pak asi jednou za hodinu) nebo **vyvrácení** („✓ zase v normě – poplach se nepotvrdil“). Platí i pro dnešní poplach z 12:01.
- Kabely a spoje: dlaždice zase trvale (zelená = v normě). V okně kontroly nahoře **graf úbytku** (3 dny), pod ním stav; návod jen při problému a při každém novém poplachu s čistým zápisem. Po vyvrácení návod zmizí.

## 4.45 – 21. 10. 2026
- Kabely a spoje (spoje opraveny, ztráta v normě): dlaždice na hlavní stránce jen při problému. Při **zvýšené i velké** ztrátě upozornění nahoře + dlaždice s návodem (dřív nahoře jen velká). Zapsaný postup (měření, odškrtnuté kroky) se po návratu do normy smaže – příště návod začne od začátku. V normě je stav dál v detailu Zdraví baterie → Kabely a spoje.

## 4.44 – 21. 10. 2026
- Dlaždice Solární baterie: „do rána ano ✓“ a „ráno zbude ~N #“ na dvou řádcích (dřív se nevešlo – „do …“).
- **Zdraví baterie** (výměna na jaře) už neotravuje: když je to jediné upozornění, nahoře jen malý řádek „✓ Nic naléhavého · baterie: …“. Když jsou i jiná upozornění, je na konci seznamu jako připomínka (+ N další). Ostatní upozornění beze změny.

## 4.43 – 20. 10. 2026
- Noční odběr pro výhled do rána: i z nocí na River (zásuvky River měří stejný odběr chaty), okno 7 nocí – v zimě, kdy noci jedou z River, je pořád z čeho brát.
- Oprava z učení výhledu jen z nocí za posledních 45 dní – po zimě bez nocí na soláru se stará oprava nepoužije (×1).

## 4.42 – 20. 10. 2026
- **Výhled do rána se učí:** při západu slunce si hlídač zapíše, kolik Ah chata do rána spotřebuje, při východu to porovná se skutečností (z #). Oprava noční spotřeby = medián poměru skutečnost / odhad z posledních až 7 nocí (aspoň 2, ×0,6–1,6). Poměr místo rozdílu – sedí i když se noci prodlužují. Jen noci celé na soláru.
- Rozpis výhledu: oprava a posledních 5 nocí „čekal → bylo“.

## 4.41 – 20. 10. 2026
- Dlaždice Solární baterie: u „do rána: ano ✓“ i odhad, kolik # zbude ráno (např. „ráno ~35 #“).

## 4.40 – 20. 10. 2026
- Výhled „do rána“ přes den: po západu počítá s **nočním** odběrem (medián nocí za poslední 3 dny, chata na soláru), ne s denním průměrem za 3 h; v noci bez rezervy +15 % a do „východ + nabíjení od východu“ – stejně jako noční předpověď. Dřív byl zbytečně pesimistický.
- Rozpis výhledu (detail Solární baterie): noční spotřeba a kolik Ah ráno zbude nad alarmem.

## 4.39 – 20. 10. 2026
- Výhled dne / do rána: když byl regulátor dnes ve Floatu (baterie plná, výrobu přiškrtil), nesnižuje se zbývající výroba podle dnešní (přiškrcené) výroby – oprava ×1 místo nižší.

## 4.38 – 19. 10. 2026
- Graf „Výroba a spotřeba po dnech“ i v detailu **Chata celkem** (první graf; při rozsahu rok / celkem po měsících). V detailu Solár zůstává.

## 4.37 – 19. 10. 2026
- **Výroba a spotřeba po dnech / měsících** (graf „Výroba po dnech“ – detail Solár i Grafy): u každého dne výroba a vedle ní spotřeba chaty **celkem** – ze soláru (i se ztrátami měniče) a z River. Po ťuknutí: „výroba pokryla spotřebu“ nebo „chybělo X kWh“.
- Zrušen graf „Výroba vs. spotřeba ze solární baterie“ (počítal jen spotřebu ze soláru – ve dny na River ukazoval falešný přebytek).

## 4.36 – 19. 10. 2026
- Dlaždice EcoFlow: River, u které je napsáno „nabíjí se z generátoru / ze soláru“, má zelený pruh a tečku (dřív šedé – počítal se jen výstup přes její zásuvku).

## 4.35 – 19. 10. 2026
- Detail Generátor: nahoře grafy – výkon generátoru (W, zásuvka generátoru, 48 h) a kolik dodal po dnech (kWh, 14 dní); pod nimi seznam běhů.

## 4.34 – 19. 10. 2026
- Generátor: energie běhu = počítadlo zásuvky generátoru minus to, co dnes dodaly už ukončené běhy. Dřív se počítalo až od chvíle, kdy hlídač běh poprvé uviděl – když začal v mezeře (Flip nemohl posílat), web ukazoval méně (0,29 kWh místo 1,3 kWh). Opraví i právě běžící běh.

## 4.33 – 19. 10. 2026 (Flip 1.4.1)
- Flip 1.4.1: zprávy, které čekaly ve frontě pro ntfy (ntfy je odmítal), pošle taky přes GitHub – hlídač jimi doplní mezeru v grafech.

## 4.32 – 19. 10. 2026 (Flip 1.4.0)
- **Data z Flipu jdou rovnou na GitHub** se spuštěním hlídače (parametr `flip`), ne přes ntfy. ntfy.sh od 12:21 odmítal zprávy z chaty (HTTP 429 – limit). ntfy zůstává na upozornění, probouzení Flipu a jako záloha, když GitHub nejde.
- Flip posílá s nejnovější zprávou i starší (každou 3×, kdyby GitHub čekající běh zrušil); hlídač je spáruje podle času, dvakrát nic nezapočítá. Poslední dvě zprávy si hlídač pamatuje pro běhy bez dat z Flipu.
- Historie zásuvek přes ntfy: po chybě další pokus až za hodinu (dřív 3 zprávy navíc v každém kole).
- Flip do záznamu píše i text odpovědi serveru při chybě (ať je vidět, který limit).

## 4.31 – 19. 10. 2026
- Návod: záložní spouštění hlídače každých 10 min přes cron-job.org (GitHub vynechal plánované běhy 12:22–12:57 při výpadku internetu na chatě → upozornění „Regulátor neposílá data“ přišlo pozdě).

## 4.30 – 19. 10. 2026
- „☀️ Dnes můžeš chatu přepnout na solární baterii“ přijde i **během dne**, jakmile to poprvé vyjde (baterie se dobíjí a do 22:00 ubývá hodin) – nejen ráno v čas z rozvrhu. Jednou za den, jen do 22:00, jen když chata jede z River a den má v rozvrhu čas.

## 4.29 – 19. 10. 2026
- Dlaždice Solární baterie: když chata jede z River, řádek „🏠 odběr 0 W · měnič vyp.“ (zkrácený na „o…“) zmizel – že chata jede z River, je napsané nad ním.

## 4.28 – 19. 10. 2026
- Zvětšení prsty opravdu opraveno: Chrome posílal pohyb prstu jen původnímu (už překreslenému) grafu, takže reagovalo jen první nepatrné zvětšení. Teď plynule, oba prsty v grafu.
- Graf si dotyk bere celý (prohlížeč při mírném svislém pohybu začal posouvat stránku a druhý prst ignoroval); posun stránky prstem přes graf dělá graf sám, i s doběhem. Při posouvání se neukazuje hodnota.

## 4.27 – 19. 10. 2026
- Oprava zvětšení prsty: po prvním překreslení grafu přestal reagovat pohyb prstů (dotyk zůstal na starém, vyměněném grafu). Pohyb teď sleduje celá stránka.

## 4.26 – 19. 10. 2026
- Dlaždice Solární baterie, když chata jede z River: místo dvou řádků jeden **„přepnout na solár?“** – **ano ✓** (vydrží do rána), **do 22:00** (přes den ano, večer zpět na River), **ne**. Rozpis v detailu.
- Web se po vydání nové verze **sám načte znovu** (zkontroluje při obnovení dat, nejvýš jednou za 5 min); service worker už nebere starou kopii z mezipaměti prohlížeče.

## 4.25 – 19. 10. 2026
- Zvětšení prsty funguje v **každém grafu** (i bez otevření přes celou obrazovku); stránka se dál posouvá nahoru/dolů. Výřez zůstane i po obnovení dat, dvojité ťuknutí = zpět na celé období.
- Dlaždice Solární baterie (chata na River): „na soláru do 22:00“ ukazuje krátce **ano ✓ / ne** (dřív „nestačila by“, popisek se zkracoval na „na soláru…“).

## 4.24 – 19. 10. 2026
- Graf přes celou obrazovku: **zvětšení prsty** – dva prsty od sebe = podrobnější časová osa (popisky času se zjemní, osa y se přizpůsobí výřezu), jeden prst = posun v čase, dvojité ťuknutí = zpět na celé období. Ťuknutím dál hodnoty.

## 4.23 – 19. 10. 2026
- Když chata jede z River (měnič vypnutý), už se nehlásí „Victron neposílá“ (lišta nahoře ani Systém); v hlavičce „Victron vypnutý (chata na River)“.

## 4.22 – 18. 10. 2026
- Hlavní stránka, řádek Teď: když chatu napájí River, je **dlaždice EcoFlow první** a Solární baterie druhá; po přepojení na solár zase naopak.

## 4.21 – 18. 10. 2026
- **Hodinky 1.9 – dlaždice při chatě na River:** jde o chatu, ne o solár. Nahoře která River napájí, velké číslo **% nabití River** (s EcoFlow; do té doby odběr ve W a „% až z EcoFlow“), **vydrží do ~HH:MM ✓/✗** (do rána), řádek 🏠 odběr · od kdy · kWh, malým řádkem solár (V a #). Barva podle toho, jestli River vydrží do rána. Hlídač posílá hodinkám i od kdy River napájí, kolik dodala a jestli vydrží do rána.

## 4.20 – 18. 10. 2026
- Dlaždice Solární baterie: když chata jede z River (měnič vypnutý), místo „V klidu“ **„Odpojená – chata jede z River“**; při nabíjení ze slunce „Nabíjí se · … · chata na River“.

## 4.19 – 18. 10. 2026
- Dlaždice Solární baterie: pod „do 22:00“ řádek **„do rána: ano ✓ / ne“** (do hodiny po zítřejším východu). Přes den stejný opatrný výpočet jako výhled dne (pokračuje přes noc bez výroby), v noci noční předpověď (pod 12,0 V = ne). Při chatě na River „na soláru do rána“.

## 4.18 – 18. 10. 2026
- Graf přes celou obrazovku: bilance a Nabití # (jedna karta) se zvětšují **každý zvlášť** – ťukni na nadpis toho, který chceš. Zvětšené okno se dá posouvat, kdyby bylo vyšší než obrazovka.

## 4.17 – 18. 10. 2026
- Detail Solární baterie: **Nabití #** je teď v jedné kartě **pod grafem bilance** („Nabití # – kam to vede“, stejná časová osa) – samostatný graf # nahoře zmizel.
- **Pozadí podle režimu regulátoru** (oranžová Boost, zelená Float) ve všech grafech solární baterie: napětí, proud, odběr, úbytek na kabelech, #, nabití %, noc.
- **Svislé čáry pro orientaci v čase** ve všech časových grafech (do 16 dní): půlnoc (slabá plná) a východ ☀ / západ ☾ slunce (tečkovaně); od 5 dní jen půlnoci.

## 4.16 – 18. 10. 2026
- Detail **Solární baterie**, graf Do baterie / z baterie: nad grafem souhrn „Dnes: do baterie … , z baterie … → baterie +/− X kWh · nabití A # → B #“ (graf Nabití # je hned nad ním). (4.15 to dalo jen do staré dlaždice Bilance v Podrobnostech.)

## 4.15 – 18. 10. 2026
- Dlaždice **Bilance** – kam to vede: nahoře souhrn s výsledkem „→ baterie +/− X kWh · nabití A # → B #“; pod grafem bilance (místo napětí) graf **Nabití #** se stejnou časovou osou – stoupá = nabíjí, klesá = vybíjí. Do grafu bilance se # nepřidává (jiná jednotka, byl by v tom zmatek).

## 4.14 – 18. 10. 2026
- Graf bilance přehledněji: místo dvou čárkovaných čar **plochy** – panely do baterie jako světle oranžová plocha **nahoru**, odběr chaty jako světle modrá plocha **dolů**, výsledek (bilance) zůstává jako plná čára.

## 4.13 – 18. 10. 2026
- Graf **Do baterie (+) / z baterie (−)** (detail baterie i dlaždice Bilance): k bilanci přibyly čárkovaně **panely do baterie** (oranžová) a **odběr chaty** (modrá, i se ztrátami měniče) – je vidět, jestli bilance klesla kvůli slunci nebo kvůli odběru. Ťuknutím všechny tři hodnoty.

## 4.12 – 18. 10. 2026
- **Ráno v čas z rozvrhu i nabídka soláru:** když chata jede z River a solární baterie by s dnešní výrobou (s rezervou) vydržela do 22:00, přijde „☀️ Dnes můžeš chatu přepnout na solární baterii – večer zase přepoj na River“ (Výchozí). Večerní „Zítra můžeš…“ zůstává. Na dlaždici při River řádek „na soláru do 22:00: vydržela by ✓ / nestačila by“.

## 4.11 – 18. 10. 2026
- Detail Solární baterie: **Výhled do 22:00** jako přehledný rozpis – v baterii nad alarmem (Ah), ještě vyrobí (+Ah), spotřebuje (−Ah), bilance. Řádky s dlouhou hodnotou (např. Nabití #) jsou pod popiskem přes celou šířku – texty se už nepřekrývají.

## 4.10 – 18. 10. 2026
- Detail Solární baterie → Teď: řádek **Výhled do 22:00** s rozpisem (z kolika #, kolik ještě dnes vyrobí, odběr), ať je vidět, z čeho „dojde ~…“ vychází.

## 4.09 – 18. 10. 2026
- **Oprava výhledu dne (planý poplach):** zbývající výroba se počítala jako „předpověď na den − co už vyrobil“. Když dnes panely dávaly víc, než předpověď čekala, vyšlo, že už nic nevyrobí, a přišlo varování, i když se baterie nabíjela. Teď se předpověď opraví podle dnešní skutečné výroby (vyrábí-li dnes 2× víc, čeká se 2× víc i odpoledne) a rozdělí podle tvaru dne; rezerva −20 % výroby, +15 % odběru.

## 4.08 – 18. 10. 2026
- Nastavení: čas se vybírá ze dvou rozbalovacích seznamů (hodina : minuta po 5 min) – políčko „čas“ prohlížeče na telefonu nešlo otevřít. Zkontrolována všechna pole Nastavení.

## 4.07 – 18. 10. 2026
- Nastavení: **Kontrola před odjezdem** má po rozkliknutí řádek pro každý den (přepínač + čas); „Vydržet do“ a „Naléhavě: přepni na River“ mají výběr času (a vypínač). Oprava: čas se dřív při ukládání poškodil (dvojtečka a písmena se mazaly).

## 4.06 – 18. 10. 2026
- Výhled dne počítá **s rezervou**: výroba podle předpovědi −30 %, odběr +15 % – rozhodující je ranní kontrola; raději zbytečně přepnout na River, než aby přes den došla energie.

## 4.05 – 18. 10. 2026
- **Výhled dne – vydrží chata na soláru do večera?** Když chata jede ze solární baterie, hlídač po každém měření spočítá: co je v baterii nad alarmem 12,0 V (z #) + výroba, kterou podle předpovědi ještě dnes dají panely − odběr chaty (průměr 3 h). Na dlaždici Solární baterie řádek **„do 22:00: vydrží ✓ / dojde ~14:30“**.
- Upozornění **„⚠️ Dnes ~14:30 solární baterie dojde – přepni chatu na River“** (Vysoká): v čas z **týdenního rozvrhu** `den_kontrola` (výchozí út a čt 5:30, ostatní dny 7:00, víkend 8:00 – před odjezdem) a během dne kdykoli, když se výhled zhorší (dřív vycházelo, teď ne). Jednou za den, jen když chata jede ze soláru. Noc dál řeší večerní a 22:00 upozornění. Do kolika vydržet: `den_do` (22:00).

## 4.04 – 18. 10. 2026
- Vráceno: „⛽ Generátor doběhl“ je zase **Malá** priorita (generátor už je vypnutý, jen informace). Akci vyžaduje stav „River nabitá, generátor běží naprázdno“ – to hlásí „⛽ … nabitá na 100 %“ (Vysoká), funguje až s daty z EcoFlow.

## 4.03 – 18. 10. 2026
- „⛽ Generátor doběhl“ je **Vysoká** priorita s pokynem: zavři přívod paliva a vypni hlavní vypínač.

## 4.02 – 18. 10. 2026
- Priority upozornění sjednocené (v ntfy lze každé dát jiný zvuk): **Nejvyšší** = teď jednej, **Vysoká** = důležité, **Výchozí** = doporučení, **Malá** = jen informace. „Baterie nabitá (Float)“ a „Regulátor zase posílá data“ přesunuté do Malé. Přehled v návodu.

## 4.01 – 18. 10. 2026
- **Naléhavé „⚠️ TEĎ přepni chatu na River“:** od 22:00 (nastavení `nutne_river_v`) do rána – když chata jede ze solární baterie a předpověď říká, že baterie v noci klesne pod 12,0 V. Nejvyšší priorita, opakuje se po ~5 min, dokud neťukneš v notifikaci na **„Přepínám“**, chata nepřejde na River (zásuvka měniče ≤ 3 W a River dodává – pak přijde „✓ Chata jede z River“) nebo nevyjde slunce. Jednou za noc. Po potvrzení může dorazit ještě jedno už naplánované připomenutí.
- Večerní předpověď (hodinu po západu) teď jasně: „🌙 Solární baterie do rána nevydrží – přepni chatu na River“.

## 4.00 – 18. 10. 2026
- Oprava: v grafu přes celou obrazovku se po ťuknutí neukazovala hodnota (bublina byla schovaná pod oknem grafu).

## 3.99 – 18. 10. 2026
- Graf přes celou obrazovku bez režimu celé obrazovky Chrome – odpadla otravná hláška „Pokud chcete ukončit režim celé obrazovky…“. Graf dál vyplní celé okno; na šířku otoč telefon.

## 3.98 – 18. 10. 2026
- **Graf přes celou obrazovku:** ťuknutí na **nadpis grafu** (vpravo ⤢) zobrazí jen ten graf na celou obrazovku a otočí ho na šířku; hodnoty po ťuknutí do grafu fungují dál. Zavře se ✕ v nadpisu nebo gestem zpět. (Ťuknutí přímo do grafu dál ukazuje hodnoty.)

## 3.97 – 17. 10. 2026
- Detail **Solár** standardně: nahoře přepínač období a grafy, pod nimi rozpis výroby, spotřeby, ztrát a bilance.

## 3.96 – 17. 10. 2026
- Detail **Solár**: nový graf **Výroba vs. spotřeba ze solární baterie** po dnech (Rok / Vše po měsících) – dva sloupce vedle sebe: výroba podle regulátoru a odběr z baterie (zásuvka za měničem ÷ 0,88 + vlastní spotřeba měniče). Výroba pod odběrem = baterie ten den ubývala. Ťuknutím přebytek / kolik chybělo.

## 3.95 – 17. 10. 2026
- Smazán nepoužitý graf „Odběr z měniče“ (Victron, VA) – ukazoval totéž co zásuvka za měničem; napětí z Victronu zůstává v grafu napětí a v úbytku na kabelech, alarmy měniče chodí jako upozornění.

## 3.94 – 17. 10. 2026
- Dlaždice „Zítra“ přejmenována na **„Zítra a počasí“**.

## 3.93 – 17. 10. 2026
- Zdraví baterie: do 5 testů kapacity je verdikt označený **„Předběžné“** s rozpětím (test od Floatu kapacitu spíš podhodnotí) – o výměně rozhodovat až po týdnu testů.

## 3.92 – 17. 10. 2026
- **Testy kapacity pro každé ráno po opravě spojů** (ne jen dnešní): hlídač při každém běhu projde všechna rána, pro která má body (14 dní) – např. Float 15. 10. → ráno 16. 10. a Float 16. 10. → ráno 17. 10. Oprava chyby: dnešní test bral jako „předchozí plné nabití“ až dnešní odpolední Float (po ránu) a nevyšel. Odběr se bere ze zásuvky 220 V za měničem (ne z Victronu). V seznamu testů je i čas Floatu, od kterého se počítalo.

## 3.91 – 17. 10. 2026
- **Nabití 1446 %** na dlaždici Solární baterie: regulátor (Solar Guardian) poslal nesmyslnou hodnotu. Nabití % mimo 0–100 se teď zahodí (při čtení, při doplňování historie i z už uložených bodů a dnů) a web ho neukáže („–“).

## 3.90 – 17. 10. 2026
- **Oprava # (ráno ~0 #):** kapacita pro # a předpovědi se brala z nočního odhadu z poklesu napětí (ten kolísal až k ~20 Ah) – s tak malou kapacitou vycházelo ráno skoro 0 #, i když baterie prázdná nebyla. Noční odhad se už nepoužívá: do 2 úspěšných testů kapacity se počítá se štítkem (200 Ah), pak s mediánem testů. Zdroj kapacity je u grafu Nabití #.

## 3.89 – 17. 10. 2026
- **Oprava spojů (pojistka) 14. 10.** – nové nastavení `oprava_spoju = 2026-10-14 18:00`: starší data se neberou pro **kontrolu kabelů** (odpor, úbytek), **přechody do Float** (špatný spoj mohl regulátor přepnout do Float dřív, než byla baterie plná – nepočítají se jako „plná“ pro # ani test kapacity) a **testy kapacity**.
- **Zdraví baterie – verdikt jen z testů kapacity z ampérhodin** (s odběrem z Victronu, ne odhad), od 2 úspěšných testů medián; do té doby „Zatím neznámo“. Noční odhad z poklesu napětí (kolísal mezi ~20 a ~125 Ah) zůstává jen jako orientační graf a na verdikt nemá vliv.
- **Nový dvoubodový test kapacity** (pro zimu, kdy baterie do plna nedojde): večer 2 h po západu a ráno před sluncem nabití z klidového napětí, mezi tím spočítané Ah; kapacita = Ah ÷ rozdíl nabití (aspoň 12 Ah a 12 %). Méně přesný než test od plného nabití – rozhoduje medián. Seznam testů (i neúspěšných s důvodem) v okně Zdraví baterie.

## 3.88 – 17. 10. 2026
- Detail solární baterie: v tabulkách **Dnes / Včera** řádek **Nejnižší / nejvyšší nabití #** (nad % regulátoru, které je teď označené „(regulátor)“); v **Nejnižší stav za období** i nejnižší # s datem (# se počítá od poloviny října – v nadpisu „# od …“). Tabulka po dnech má sloupec **Min #**. Hlídač ukládá i nejvyšší # dne (`hq_max`), dopočte se z bodů za posledních 14 dní.

## 3.87 – 17. 10. 2026
- **Oprava výroby „Dnes“:** v 5 ráno ukazovala 0,89 kWh, i když ještě nesvítilo. Denní počítadlo regulátoru se nenuluje o půlnoci, takže po půlnoci ještě hlásí starou hodnotu a hlídač ji připsal k novému dni. Teď: před východem slunce je výroba 0; potom se počítá od poslední hodnoty před východem (a když se počítadlo vynuluje, od nuly). Stejně se znovu přepočítá celá historie výroby ze Solar Guardianu (dny po slunečném dni mohly mít výrobu přičtenou z předchozího dne).

## 3.86 – 17. 10. 2026
- **Flip 1.3.11 – Victron po zavření aplikace:** výsledky Bluetooth skenu Android doručuje jen aplikaci, která smí polohu. Služba Flipu byla jen typu „připojené zařízení“ – s polohou „jen při používání“ o ni přišla, jakmile se aplikace zavřela (proto po instalaci Victron jednou šel a pak už ne). Teď je služba i typu **„poloha“** (z otevřené aplikace se to obnoví vždy při jejím otevření). Když to Android z pozadí nedovolí, zapíše to do Deníku.
- V aplikaci Flipu stav **„✓ Poloha: Povolit vždy“** / „⚠ Poloha není Povolit vždy“ a tlačítko, které otevře nastavení aplikace (Oprávnění → Poloha → Povolit vždy). Řádek „Victron – záložní hledání“ v Deníku uvádí i stav polohy.

## 3.85 – 16. 10. 2026
- Dlaždice Solární baterie: napětí a nabití # **pod sebou** (vedle sebe se pletly).

## 3.84 – 16. 10. 2026
- Dlaždice Solární baterie: **nabití # stejně velké jako napětí** vedle V (např. „12,74 V  86 #“; pod 50 # oranžově, pod 30 # červeně). Z řádku „nabití“ zmizelo, zůstalo tam jen % regulátoru.

## 3.83 – 16. 10. 2026
- **Flip 1.3.10 spouští hlídače sám po každém měření** (každých ~10 min): data na webu i hodinkách jsou pak čerstvá za 2–3 min místo 30–45 min (dřív čekal Flip i hlídač každý na svůj termín). V Nastavení Flipu nové pole **GitHub token** (stejný jako na webu u ⚡ Načíst). Bez tokenu funguje jako dřív. Probuzení z webu (⚡ Načíst) hlídače znovu nespouští – ten už běží.
- **Hodinky 1.8: ťuknutí na dlaždici = změřit hned.** Hodinky pošlou Flipu „hodinky“ (ntfy `…-wake`), Flip změří a spustí hlídače; dlaždice ukáže „⏳ měří se…“ a do 5 min se obnovuje každou minutu, než přijdou nová data. Nejvýš jednou za 2 min. Když Flip spí / je bez internetu, nic se nestane a dlaždice ukáže data z dalšího běhu.

## 3.82 – 16. 10. 2026
- **Hodinky 1.7:** nabití # na dlaždici jako samostatný výrazný řádek pod napětím (menší než V, větší a tučný oproti ostatnímu; pod 50 # oranžově, pod 30 # červeně). Hlídač posílá `hq` zvlášť (ve stavu už ne).

## 3.81 – 16. 10. 2026
- **Flip 1.3.9:** vrácen poslech Victronu jako do 1.3.6 – v 1.3.7 se sken restartoval po každém měření a příjem na pozadí se tím zhoršil (Android sken spuštěný se zhasnutým displejem nemusí rozběhnout); intenzivní hledání zase 20 s. Zůstává z 1.3.8: oprávnění poloha „Povolit vždy“, záložní hledání bez filtru se záznamem do Deníku, zásuvky v Deníku podle čísla. Obsahuje vše z 1.3.4–1.3.6 (fronta, probuzení z aplikace, čerstvá jména zásuvek).

## 3.80 – 16. 10. 2026
- **Upozornění na nabití #:** pod **50 #** (baterie rychle stárne – omez odběr / přepni na River) a pod **30 #** (hrozí poškození); každé jednou, znovu až po nabití nad 60 #. Nastavení `hash_upozornit`.
- Graf Nabití #: čárkovaná hranice s popiskem „50 #“
- Hodinky (dlaždice): místo % regulátoru nabití **#** („86 # · nabíjí“); komplikace dál ukazuje napětí

## 3.79 – 16. 10. 2026
- Nabití #: **100 # = přechod regulátoru do Float**, i když tam vydrží jen chvíli (dřív aspoň 30 min) – je to nejlepší stav, jaký máme. Platí i pro test kapacity.

## 3.78 – 16. 10. 2026
- **Oprava Nabití #:** ve Float ukazovalo 40 # – kotva „nejlepší stav za 7 dní“ se při dopočtu historie (díry v datech, odhadnutý odběr) rozjela vysoko. Teď se každý okamžik vztahuje k **nejbližšímu skutečnému plnému nabití** (Float ≥ 30 min): po něm kolik ubylo, před ním kolik do plného chybělo (do 3 dnů) – i dnešní ráno se tak srovná podle dnešního Floatu. „Nejlepší stav“ jen jako nouzovka za 2 dny. Přepočítává se z bodů při každém běhu. V detailu: „Float od …, plná se počítá od …“.

## 3.77 – 16. 10. 2026
- **Graf Nabití # je v detailu solární baterie první**, s čárkovanou hranicí **50 #** (doporučená spodní hranice pro AGM) a 100 #. Pro Rok / Vše graf **nejnižšího # každého dne** (ukládá se od 16. 10. 2026).
- Výklad: kdy je baterie „prázdná“ – měnič vypíná při ~11,6 V (≈ 10–20 #), pro životnost AGM nejít pod 50 #.

## 3.76 – 16. 10. 2026
- **Kapacita baterie se testuje sama:** jednou denně ráno (hodinu po východu), když byla baterie předchozí den skutečně plná (Float ≥ 30 min) a přes noc z ní ubylo aspoň 20 Ah (do ~85 % podle napětí). Nabití ráno z klidového napětí AGM (opraveno o pokles odběrem), kapacita = odebrané Ah ÷ ubylý podíl. Od 2 úspěšných testů se pro # a předpovědi bere jejich medián (dřív jen Zdraví baterie / štítek). Výsledky testů ve výkladu detailu baterie, zdroj kapacity u grafu Nabití #.

## 3.75 – 16. 10. 2026
- **Nabití # (spočítané z Ah):** vedle % regulátoru (z napětí) nový údaj se značkou **#**. Počítá ampérhodiny – co do baterie přiteklo z regulátoru (účinnost nabíjení ~90 %) a co odteklo do měniče (zásuvka 220 V + ztráty + vlastní spotřeba + desulfátor). **100 #** = baterie skutečně plná (Float aspoň 30 min); když plná nebyla, nejlepší stav za posledních 7 dní. Při každém plném nabití se srovná. Kapacita ze Zdraví baterie; v detailu i odebrané Ah. Dlaždice: „72 % · 86 #“, detail: řádek v Teď, graf **Nabití #**, výklad.

## 3.74 – 16. 10. 2026
- **Okno EcoFlow ukazuje nabíjení:** v řádku Teď nový řádek **Nabíjení ze soláru** (zásuvka 8: nabíjí / vypnuto, a kterou River – pozná se z názvu zásuvky, např. „(8) nabíjení River malý“); River při běžícím generátoru „nabíjí se z generátoru“, při zapnuté zásuvce 8 „nabíjí se ze soláru“. Na časové ose řádek **Ze soláru**, v tabulce doba nabíjení ze soláru (dnes / období). Kolik energie šlo do které River, ukáže až EcoFlow.
- Hlídač ukládá do bodů, kdy byla zásuvka nabíjení ze soláru zapnutá (`rc`).

## 3.73 – 16. 10. 2026
- **Nabíjení River ze soláru jen ve Float** (nastavení „Nabíjet River už v Boostu“ vypnuto): solární baterie se vždy dobije úplně, i za cenu ztráty přebytku. Když je River zapnutá a regulátor je v Boostu, automatika ji vypne.

## 3.72 – 16. 10. 2026
- **Automatika River v Boostu přísnější:** nabíjení River se v Boostu vypne, jakmile napětí klesne o 0,15 V pod nabíjecí (dřív až pod ~13,55 V) – to znamená, že panely nestačí na baterii i River a baterie by nedostávala plný proud. Solární baterie má vždy přednost.

## 3.71 – 16. 10. 2026
- **Flip 1.3.8 – Victron:** test Bluetooth (displej svítí) měnič vidí, poslech na pozadí ne. Aplikace teď umí oprávnění **poloha „Povolit vždy“** (nastavit ručně: Nastavení → Aplikace → Chata brána → Oprávnění → Poloha → Povolit vždy) – Android pak doručuje vysílání Bluetooth i aplikaci na pozadí. Když filtrovaný poslech nic nechytí, zkusí Flip 15 s hledání **bez filtru** (jako Test Bluetooth) a zapíše do Deníku, jestli svítil displej a co viděl – pozná se, kde je příčina.
- **Flip: zásuvky v Deníku podle našeho čísla** „(8) …“, ne podle IP. Zásuvky, které odmítají přihlášení (401), číslo prozradit nemůžou – Deník napíše, ať se v Tapo zapne „Kompatibilita s třetími stranami“.

## 3.70 – 16. 10. 2026
- Hlavička kratší, tři řádky bez slova „před“: „Regulátor 2 min“, „Victron 1 h 7 min“, „Flip 3 min · 54 % ⚡“. Baterie Flipu: nabíjí = zelená s ⚡, nenabíjí = bílá, 20 % a méně = červená.

## 3.69 – 16. 10. 2026
- Dlaždice River v řádku Teď se jmenuje **EcoFlow** (tři River a generátor)
- Hlavička: tři řádky stejného tvaru – **Regulátor: před x min**, **Victron: před y min** (oranžově, když přes hodinu nic), **Flip: před z min · baterie %**

## 3.68 – 16. 10. 2026
- **Okno River – výjimka z „grafy napřed“:** pod přepínačem období je nahoře tabulka čísel. Sloupec **dnes** je vždy, druhý sloupec se řídí přepínačem: Dnes → včera, 48 h, 7 dní, rok, celkem (součty kWh). Navíc řádek River celkem a počet běhů generátoru. Grafy až pod ní.

## 3.67 – 16. 10. 2026
- River žlutý opravdu žlutý (na tmavém pozadí byl oranžový) – vlastní barva `--rvy`

## 3.66 – 16. 10. 2026
- Barvy River podle jména: **žlutý = žlutá, červený = červená, malý = modrá**; generátor fialová (aby se nepletl s červenou)

## 3.65 – 16. 10. 2026
- **Okno River (dlaždice v řádku Teď):** 4 zařízení – tři River a generátor, záložky na dlaždici se stavem teď (napájí chatu / napájí spotřebič / nabíjí se / nic nedělá; generátor běží / neběží). Detail: Teď (všechna 4 zařízení), **Co se dělo** (časová osa – kdy která River napájela a kdy běžel generátor), Z River do chaty, každá River zvlášť, Generátor, Nabití a Nabíjení River (připravené – ukážou se, až poběží EcoFlow), Běhy generátoru, Čísla (dnes / včera / ⌀ 7 dní), Výklad. Pro Rok / Vše sloupce kWh po dnech.
- **Dlaždice Z River** ukazuje jen spotřebu (bez „teď nenapájí“)
- Hlídač pošle jednorázovou **připomínku**, až poprvé dorazí data z EcoFlow (ovládání nabíjení a optimalizace generátoru – `docs/napady.md`)

## 3.64 – 16. 10. 2026
- **Flip 1.3.7 – Victron:** poslech Bluetooth se po každém měření spustí znovu (Android/Samsung dlouho běžící sken na pozadí potichu utlumí – výsledky pak chodily jen, když skenovala jiná aplikace, např. VictronConnect); když nic nechytí, intenzivní hledání 40 s (dřív 20 s)
- Lišta „K řešení“: **Victron neposílá** (od …), když z měniče přes hodinu nepřišla data, i když Flip jinak posílá

## 3.63 – 16. 10. 2026
- **Odběr navíc se potvrzuje průměrem:** 16. 10. v 9:57 přišlo upozornění „za měničem 146 W“, ale graf zásuvky 220 V v aplikaci Tapo celé ráno nepřekročil ~70 W – jedno okamžité měření bylo mimo. Teď se z počítadla energie zásuvky (stejné, ze kterého kreslí graf Tapo) spočítá průměr za posledních ~10 min (dvě poslední zprávy Flipu); upozornění přijde, jen když odběr navíc ukazuje i průměr. Velký odběr (≥ 300 W okamžitě) se hlásí hned jako dřív. Zahozená špička se zapíše do Deníku.
- Upozornění uvádí i průměr za posledních ~10 min

## 3.62 – 16. 10. 2026
- **Flip 1.3.6 – hodnoty zásuvek vždy ke správné zásuvce:** jméno zásuvky se dřív bralo z mezipaměti podle IP adresy (až hodinu staré). Když se po restartu routeru adresy přeházely, naměřené W se mohly připsat jiné zásuvce – web a upozornění pak ukazovaly jinou hodnotu než aplikace Tapo. Teď se jméno čte ze zásuvky při každém měření, číslo zásuvky rozhoduje podle něj (ne podle staré mapy adres) a při nesouladu Flip zásuvky znovu vyhledá. Posílá i otisk zařízení (`d`).
- Upozornění na odběr navíc uvádí, která fyzická zásuvka 220 V hodnotu hlásila (jméno, IP, otisk zařízení) – pro kontrolu s aplikací Tapo.
- (3.61: vysvětlení přes nabíjení River bylo chybné – River nebyl zapojený. Úprava upozornění tam zůstává jen pro případ, že zásuvka 8 je opravdu zapnutá.)

## 3.61 – 16. 10. 2026
- **Odběr navíc a nabíjení River:** zásuvka 8 (nabíjení River ze soláru) je za měničem a neměří – když je zapnutá, celé nabíjení se jevilo jako „odběr navíc“. Když ji ovládá automatika (zapnutá nebo právě vypnutá – Flip povel provede až při dalším měření), upozornění se neposílá; automatika ji při vybíjení vypne sama. Bez automatiky upozornění přijde s poznámkou, že je zapnutá zásuvka nabíjení River.
- Upozornění na odběr navíc vypíše i **měřené zásuvky** v tu chvíli a čas měření

## 3.60 – 16. 10. 2026
- **Nouzové spuštění Flipu z aplikace:** tlačítko ⚡ Načíst teď kromě hlídače probudí i Flip – změří a odešle hned, nečeká na svůj 10min budík. Hlídač počká na jeho data (nejvýš ~2 min) a teprve pak je zpracuje.
- **Flip 1.3.5:** drží trvalé spojení na ntfy téma `<téma>-wake`; po zprávě změří hned (nejvýš 1× za minutu). Bez internetu se spojení obnovuje každých 30 s. Obsahuje i frontu z 1.3.4.

## 3.59 – 16. 10. 2026
- **Flip 1.3.4 – nic se neztratí při výpadku internetu:** když se zpráva nepodaří odeslat (router / 4G na chvíli bez spojení), Flip to za 20 s zkusí znovu a pak ji uloží do fronty (až ~1 den); při dalším odeslání pošle nejdřív frontu. Každá zpráva nese čas měření (`ts`), hlídač ji zařadí na správné místo. Probuzení telefonu prodlouženo na 4 min (hledání zásuvek se do 2 min nemuselo vejít).
- Hlídač: zprávy Flipu řadí podle času měření; doplňování z historie regulátoru za posledních 6 h (dřív 3 h) – pro případ, že GitHub hlídače delší dobu nespustí

## 3.58 – 16. 10. 2026
- **Hodnoty v grafech po ťuknutí:** bublina s hodnotou byla v detailech schovaná pod oknem (byla vidět jen svislá čára). Teď je nahoře a na telefonu zůstane, dokud neťukneš jinam nebo neposuneš stránku.
- **Bodový graf nejnižšího napětí:** přímo v grafu je napsaná poslední hodnota a nejnižší noc se zátěží (hodnota + datum)
- Časy v bublinách „dnes 13:30“, „včera 06:40“, jinak „14. 10. 13:30“ – bez dnů v týdnu

## 3.57 – 15. 10. 2026
- **Díry v datech z Flipu se doplní zpětně:** hlídač (plánované spouštění GitHubu) běží často jen po 30–45 min místo 10. Data regulátoru se doplňovala z historie Solar Guardianu už od 3.47, ale zásuvky, odběr a napětí Victronu se ukládaly jen při běhu. Teď se při každém běhu projdou všechny zprávy Flipu za posledních 12 h (ntfy je drží) a doplní se do mezer – k bodu regulátoru ze stejné chvíle, jinak jako samostatný bod.

## 3.56 – 15. 10. 2026
- **Zpět gestem / tlačítkem telefonu** zavře otevřený detail (i zásuvku, kabely, nastavení) a vrátí na hlavní stránku – dřív aplikace zmizela

## 3.55 – 15. 10. 2026
- **Stav solární baterie rozlišuje fáze nabíjení** (dlaždice i hodinky): **Nabíjí se** (Boost pod ~14,1 V, plný proud) · **Dobíjí se** (Boost nad 14,1 V – napětí drží, proud klesá; regulátor už ukazuje ~100 %, ale baterie ještě není plná) · **Nabito** (Float). Float se už nikdy neukazuje jako „nabíjí se“.

## 3.54 – 15. 10. 2026
- **Rozdíl napětí regulátor − měnič už není záporný:** napětí Victronu se přiřadí jen k bodu regulátoru ze stejné chvíle (do 2,5 min); dřív se porovnávaly údaje až 20 min od sebe. Od rozdílu se odečte stálý rozdíl kalibrace přístrojů změřený v klidu. Graf se jmenuje **Úbytek napětí na kabelech**, s červenou hranicí upozornění.
- **Upozornění na kabely a spoje:** 🔥 hned, když úbytek přesáhne 0,35 V (jako u natavené pojistky – max 1× za 6 h); 🔧 jednou denně, když odpor cesty regulátor → baterie → měnič za 24 h vyjde nad 20 mΩ. Nastavení `kabely_ubytek_V`, `kabely_odpor_mOhm`.
- Dlaždice Kabely a spoje počítá jen ze spárovaných měření (pár hodin po nasazení se data sbírají)

## 3.53 – 15. 10. 2026
- **Tři pohledy na spotřebu:** Chata celkem → vše; **Ze soláru** → jen doba, kdy chatu napájela solární baterie; **Z River** → jen doba, kdy jela River (chata nebo samostatný spotřebič). Platí pro všechny grafy i tabulku.
- Místo složeného grafu po zásuvkách jen **odběr chaty** (součet) daného pohledu
- **Čísla sedí:** ze soláru + z River = celkem. Denní kWh z počítadel zásuvek, rozdělení na solár / River podle průběhu po 10 min (dřív se dělilo až od nasazení 3.51, proto nesouhlasila); dlaždice Ze soláru / Z River počítají stejně jako detail
- Rozdělení podle skutečných dat od 14. 10. 2026 (noc 14./15. 10. jela chata z River)

## 3.52 – 15. 10. 2026
- **Hlavní okruh chaty jede vždy z jednoho zdroje:** když měnič dodává (> 3 W), všechny měřené zásuvky jsou ze soláru a co zároveň dává River, je samostatný neměřený spotřebič (TV, nabíjení telefonu) → „ostatní z River“. Chata je „na River“ jen když měnič nedává nic a River ano. Místo rozdělování podle poměru výkonu.
- Podle toho i šedé pozadí v grafech, hodinky („River napájí chatu“ jen při přepojené chatě) a dlaždice River („napájí chatu“ / „napájí spotřebič“)

## 3.51 – 15. 10. 2026
- **Spotřeba dnes:** nahoře dlaždice **Chata celkem** (kWh dnes, W teď), pod ní **Ze soláru** (měřeno na zásuvce 220 V + řádek „vč. ztrát“ měniče) a **Z River**
- **Detail Spotřeba** (rozklik kterékoli z nich nebo Spotřebičů):
  - **Co bralo kdy** – složený graf: lednice, Wi‑Fi, další zásuvky a „ostatní (neměřené)“; šedé pozadí = chata na River. Rok / Vše = sloupce kWh po dnech
  - **220 V**: změřeno na zásuvce + kolik to vzalo z baterie (+12 % ztráty měniče, měnič naprázdno, desulfátor)
  - Každá zásuvka zvlášť (W; pro delší období kWh po dnech rozdělené ze soláru / z River), pak **Ostatní (neměřené)** = celkem − měřené zásuvky
  - Tabulka: dnes / včera / ⌀ 7 dní, u každého ☀ ze soláru a R z River; výklad dole
- Hlídač: spotřeba každé zásuvky se dělí na solár / River podle výkonu obou zdrojů v tu chvíli (`days.tps`) – od 15. 10. 2026
- Historie: 220 V, lednice a Wi‑Fi se ze staré historie (uložené pod IP adresou) jednou přejmenují na nová čísla podle starého jména; ostatní zásuvky od 14. 10. 2026
- Desulfátor (JCP‑2‑ABC, max 0,02 A ≈ 0,25 W) přičten ke stálému odběru z baterie (`desulfator_W`)

## 3.50 – 15. 10. 2026
- Noci na River se rozpoznávají až **od 15. 10. 2026** (nastavení `river_noci_od`). Dřív v noci River nejel a jeho zásuvky sloužily jinak → všechny starší noci = solární baterie se zátěží.

## 3.49 – 15. 10. 2026
- **Noci na River se nemíchají s nocemi na solární baterii:** u každého dne se pozná, jestli ~6 h před nejnižším napětím chatu napájela solární baterie (odběr za měničem), nebo River (baterie bez zátěže). Zdroj: body hlídače, starší dny hodinová spotřeba zásuvky měniče z Tapo.
  - Bodový graf: ● plný = noc se zátěží (spojené čarou – trend vybíjení), ○ šedý prázdný = noc na River (nesrovnatelné, mimo čáru); v bublině popis
  - Graf napětí: kroužek minima dne šedý, když byla noc na River
  - „Nejnižší stav za období“ počítá napětí jen z nocí se zátěží; u Dnes / Včera poznámka „(noc na River)“

## 3.48 – 15. 10. 2026
- **Čas nejnižšího napětí dne:** v bublině bodového grafu („min 12,31 V v 06:40“) – hned je vidět, jestli to bylo ráno (stav baterie), nebo přes den (spotřebič)
- **Graf napětí:** nejnižší bod každého dne označený červeným kroužkem s hodnotou – stejné číslo jako v bodovém grafu
- Hlídač jednou doplní body za celých 14 dní z historie Solar Guardianu a dnešní minimum přepočítá jen z měření

## 3.47 – 15. 10. 2026
- **Nejnižší napětí dne sedí s grafem napětí:** dřív se do něj počítal i vlastní údaj regulátoru, který chytá okamžité propady (rozběh lednice, měniče) a nuluje se až po setmění – v grafu (body po 10–40 min) ten moment nebyl. Teď min/max dne jen z měření; historie se jednou znovu projde. Okamžitý propad regulátoru je v bublině bodového grafu pro informaci.
- **Hustší graf:** mezi běhy hlídače (v noci i po 30–40 min) se body doplní z historie Solar Guardianu (~10 min)
- **Napětí:** Victron čárkovaně nad regulátorem + nový graf **rozdílu napětí regulátor − měnič** (úbytek na kabelech)
- Při otevření aplikace „Načítám data z chaty… N s“ místo černé obrazovky

## 3.46 – 15. 10. 2026
- **Detail Solární baterie přeskládaný:** nahoře grafy, pod nimi číselné údaje, dole výklad
- Pořadí grafů: do/z baterie (sčítací) → výkon panelů → napětí → odběr z baterie → nejnižší napětí každého dne (body) → výroba
- **Napětí v jednom grafu:** regulátor (modře) a měnič Victron (oranžově); v bublině i jejich rozdíl
- Zpět **bodový graf nejnižšího napětí dne** (bod = den, v bublině i nejnižší % a nejvyšší napětí)
- Pryč: graf nabití % (je to jen přepočet napětí regulátorem), samostatné grafy nejnižšího / nejvyššího napětí a nabití dne

## 3.45 – 15. 10. 2026
- **Dlaždice Solární baterie** (hlavní stránka): napětí, stav (Nabíjí se · Boost / Vybíjí se / Nabito · Float / V klidu) a 3 údaje – nabití % (regulátor), panely W, odběr z baterie W. Žádný výklad; jen u akutního stavu (regulátor mlčí, pod 12,2 / 12,0 V, odběr navíc) blikající ❗.
- **Detail Solární baterie** – nejdřív data, pak grafy, výklad až dole:
  - Teď (napětí, %, panely, odběr, do/z baterie, stav, regulátor, teplota, Victron) · Dnes · Včera (nejnižší/nejvyšší napětí i nabití) · Nejnižší stav za 7 dní / 30 dní / rok / celou historii (s datem)
  - Grafy podle důležitosti: výkon panelů → odběr z baterie → do/z baterie (bilance se ztrátami měniče) → napětí → nabití % → nejnižší napětí dne → **nejnižší nabití dne** → nejvyšší napětí dne → výroba po dnech / měsících
  - Když chata jede z River, grafy to ukazují šedě; odběr ze solární baterie je pak jen měnič (vypnutý = 0 W), spotřeba River se sem nepočítá
- Hlídač: denní **nejnižší a nejvyšší nabití (%)** se ukládá a jednorázově se doplní z historie Solar Guardianu (po měsících zpět, jako napětí)

## 3.44 – 15. 10. 2026
- **Hodinky – River jako zdroj i bez EcoFlow:** dlaždice se dřív přepnula na River jen podle dat z EcoFlow (ta zatím nechodí), proto celou noc ukazovala solár. Teď se River pozná i ze zásuvky na jejím výstupu (zasuvky_river, odběr > 3 W): „🔋 River malý · 45 W / od 22:10 · 0,42 kWh“. Až půjde EcoFlow, přibude % a do kdy vydrží.
- Hodinky: „🏠 W“ = odběr celé chaty (solár + River), ne jen za měničem
- Web, dlaždice Noc: když chatu napájí River a % neznáme, ukáže kterou River a kolik dodala

## 3.43 – 15. 10. 2026
- **Flip 1.3.3:** po hledání v síti se zahodí staré relace se zásuvkami (hledání se přihlásilo znovu a zásuvky staré relace zrušily → „HTTP 403“ a 0/14); při HTTP 403/401 se zásuvka hned zkusí znovu s novým přihlášením; ruční seznam adres se používá jen, když hledání nic nenajde (dřív se míchaly staré neplatné adresy → „6/14 (7 vypnuté)“)
- Spotřebiče: jen zásuvky pojmenované „(N) …“ nebo živé, bez starých záznamů podle IP

## 3.42 – 14. 10. 2026
- **Hlavní stránka po vrstvách:**
  - **Teď:** Solární baterie · River (stav: která napájí chatu a kolik W; % nabití až z EcoFlow)
  - **Výroba dnes:** Solár (kWh, teď W, kolik šlo do River automatikou, předpověď) · Generátor (kWh ze zásuvky nabíjení z generátoru, běží / naposledy, do kterých River – až z EcoFlow)
  - **Spotřeba dnes:** Ze solární baterie (měnič − nabíjení River) · Z River (celkem a po každé River, ● napájí teď)
  - **Spotřebiče:** každá zásuvka, která není zdroj – dnes kWh a teď W (lednice, router…)

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
