# Verze

Číslo verze: soubor `VERSION` (hlídač), `WEB_VER` / `FLIP_VER` ve `web/index.html`, `versionName` v `android/app/build.gradle`.
Každá změna = +0.1. Aplikace pro Flip dostane nové číslo jen, když se mění její kód (FLIP_VER pak ukazuje, co je nejnovější).

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
