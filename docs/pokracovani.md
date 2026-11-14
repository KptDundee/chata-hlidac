# Pokračování v novém chatu (stav k 23. 10. 2026)

Tenhle soubor je pro Clauda v novém chatu: přečti ho celý, pak CHANGELOG.md (poslední verze nahoře), docs/navod.md a docs/technicka.md.

## Projekt
- Repo KptDundee/chata-hlidac (veřejné). Hlídač `hlidac.py` běží v GitHub Actions (`hlidac.yml`), zapisuje šifrované `data.enc` na gh-pages; web `web/index.html` (PWA); aplikace pro Flip `android/` (cz.petr.chatabrana); hodinky `hodinky/`.
- Data z Flipu jdou přes GitHub (workflow_dispatch s parametrem `flip`), ntfy jen pro upozornění, probouzení, povely (`-cmd`), povolení nabíjení Flipu (`-fc`).

## Pravidla od Petra (dodržovat)
- Každou změnu očíslovat (VERSION, WEB_VER / FLIP_VER, versionName), zapsat do CHANGELOG, docs/navod.md, docs/technicka.md.
- Commit s atribučními řádky, push, pak spustit hlídače:
  `gh api -X POST repos/KptDundee/chata-hlidac/actions/workflows/hlidac.yml/dispatches -f ref=main -F 'inputs[test]=false' -F 'inputs[wake]=false'` (GraphQL `gh workflow run` nefunguje).
- Nikdy nepsat Petrova hesla / přihlašovací údaje; nikdy nezveřejnit ntfy téma (repo je veřejné).
- Systémová nastavení jen popsat (návod), neměnit; nesahat do úložiště prohlížeče ani na tokeny.
- Procenta (%) jen tak, jak je hlásí regulátor; # je náš vlastní stav (100 = Float, 0 = prázdná). # a % neprohazovat.
- Solární baterie má přednost. Detaily: nejdřív grafy, pak čísla, pak výklad (výjimka EcoFlow – tabulka nahoře).
- Upozornění jen na mimořádné věci; raději zbytečný poplach než pozdní. Časy vždy s dnes / zítra / včera, ve zobrazení ne dny v týdnu (kromě rozvrhu v nastavení).
- Zásuvky označovat číslem v závorce, nikdy IP. Data nezkreslovat průměrováním. Nespekulovat – Petr vymyšlená vysvětlení nemá rád.
- Optimalizaci generátoru zatím neprogramovat (čeká na EcoFlow). Petr nemá rád časté matoucí změny – menší kroky, ptát se u větších.
- Petr: 1 River na celý den nevydrží, na den jsou potřeba obě. V zimě se v chatě topí každý den, solární baterie je venku.

## Čeká se na
- **Přístup k EcoFlow API** → pak: kdy přepnout žlutou ↔ červenou River, kdy dobít generátorem (oznámení předem), upozornění „River nabitá“.
- **Flip 1.7.1 nainstalovat** (nový vzhled, čtení baterie routeru M7000 – zatím jen čtení; když funguje, přidat řízení nabíjení zásuvky (5): 40–80 %, pod 30 % vždy, pojistka).
- Ověřit na skutečném zařízení: řízení nabíjení Flipu zásuvkou (9) (odpočet „za 3 h zapnout“ – jestli ho zásuvka přijme), teploměry Xiaomi (klíče BLE KEY z Xiaomi Cloud Tokens Extractor, Petr jich má 6), start po restartu bez odemčení (Direct Boot).
- Vzdálený přístup na Flip (AnyDesk / TeamViewer Host) – nastavit na chatě.
- Zásuvky .115 / .122 hlásí 401 (kompatibilita s třetími stranami / firmware).

## Nápady na později (Petr souhlasil s pořadím)
- Týdenní souhrn, motohodiny generátoru (výměna oleje).
