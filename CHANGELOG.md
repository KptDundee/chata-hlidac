# Verze

Číslo verze: soubor `VERSION` (hlídač), `WEB_VER` / `FLIP_VER` ve `web/index.html`, `versionName` v `android/app/build.gradle`.
Každá změna = +0.1. Aplikace pro Flip dostane nové číslo jen, když se mění její kód (FLIP_VER pak ukazuje, co je nejnovější).

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
