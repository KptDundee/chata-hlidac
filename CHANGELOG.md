# Verze

Číslo verze: soubor `VERSION` (hlídač), `WEB_VER` / `FLIP_VER` ve `web/index.html`, `versionName` v `android/app/build.gradle`.
Každá změna = +0.1. Aplikace pro Flip dostane nové číslo jen, když se mění její kód (FLIP_VER pak ukazuje, co je nejnovější).

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
