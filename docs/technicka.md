# Chata – elektřina: technická dokumentace

Popis architektury, výpočtů a dat. Pro běžné používání je **Návod**, změny jsou v **Historii změn** (`CHANGELOG.md`).
Číslo verze je v souboru `VERSION` (hlídač), `WEB_VER` / `FLIP_VER` ve `web/index.html` a `versionName` v `android/app/build.gradle`. Každá změna = +0,1.

---

## 1. Architektura

```
Regulátor EPEVER XTRA-N ──Wi-Fi modul──► Solar Guardian (cloud) ─┐
                                                                 │  každých 10 min
Flip (Chata brána) ─ Tapo KLAP (LAN) ─ zásuvky                    ├─► GitHub Actions: hlidac.py
                   ─ Victron BLE (Instant Readout) ─ měnič         │      │
                   ─► ntfy <téma>-menic, -menic-hist ─────────────┘      ├─► data.enc (AES-GCM) → gh-pages → web
                   ◄─ ntfy <téma>-cmd (povely zásuvkám) ◄─────────────────┤
                                                                         ├─► ntfy <téma> (upozornění)
Open-Meteo (předpověď + archiv počasí) ◄────────────────────────────────┤
EcoFlow API (až budou klíče) ◄──────────────────────────────────────────┤
Hodinky Wear OS ◄── ntfy <téma>-hodinky ◄─────────────────────────────────┘
```

| Část | Kde | Popis |
|---|---|---|
| Hlídač | `hlidac.py`, `pocasi.py`, `panely.py`, `ecoflow.py` | Python 3, bez knihoven; GitHub Actions cron `3-59/10 * * * *` |
| Nastavení | `nastaveni.txt` | klíč = hodnota; „vypnuto“ = None; mění se i z webu (GitHub Contents API) |
| Web | `web/index.html` (+ `sw.js`, manifest) | jedna stránka, WebCrypto, bez knihoven; PWA |
| Dokumentace | `docs/*.md`, `CHANGELOG.md`, `web/doc.html` | zveřejňuje se do `gh-pages/docs/` |
| Brána | `android/` (Chata brána, `cz.petr.chatabrana`) | Java, minSdk 31, bez závislostí |
| Hodinky | `hodinky/` (`cz.petr.chatahodinky`) | Java, Wear OS (minSdk 30), Tiles + Complications |
| Workflow | `.github/workflows/hlidac.yml` | běh hlídače, zveřejnění webu, data.enc a dokumentace |

**Tajné údaje (GitHub Secrets):** `SG_ACCOUNT`, `SG_PASSWORD`, `NTFY_TOPIC`, `DATA_KEY`, `ECOFLOW_ACCESS_KEY`, `ECOFLOW_SECRET_KEY`. Téma ntfy je tajné. Repozitář je veřejný, proto se nikdy nezapisuje do kódu.

---

## 2. Datové zdroje

### Solar Guardian (EPEVER)
- Přihlášení: MD5 hesla, hlavička `AppId`; adresa serveru přes `device/getDevServerAddr`.
- Poslední hodnoty: `/history/lastDatapoint`. Historie: `/history/getDatapointHistory0` (stránkuje se po 1000).
- Datové body (`POINTS`): pv_w, bat_v, **bat_a = proud z regulátoru do baterie** (ne čistý proud baterie; odběr měniče jde přímo z baterie), bat_soc (regulátor, z napětí), bat_t, status (0 nenabíjí, 1 Float, 2 Boost, 3 Equalize), day_kwh, min_v, max_v, month_kwh, total_kwh.
- Regulátor v noci nuluje denní počítadla → hlídač drží denní maximum / minimum.
- Import historie: postupně po měsících zpět (90 s na běh), přidává `nv` (noční napětí), `c` (kapacita z nabíjení), `fl` (čas Float), `mp` (nejnižší napětí), `pa` (špička proudu mimo Float). Verze importu `hist_vN` vynutí nový průchod.

### Brána Flip (ntfy `<téma>-menic`)
JSON: `w` (VA Victron průměr), `max`, `lw` + `v` (odběr a napětí ve stejném okamžiku), `st`, `al`, `age`, `n`, `tp` (zásuvky: `ip, n, w, wh, on, off, nm, err`), `ph` (telefon: `b, c, t`), `av` (verze aplikace).
- Tapo: protokol KLAP v2 (místní HTTP), `get_device_info`, `get_energy_usage`, `get_energy_data`, `set_device_info {device_on}`.
- Victron: BLE Instant Readout, výrobce 0x02E1, AES-128-CTR, Phoenix 12/800 = 0x2403. MAC je náhodná statická → sken na pozadí s filtrem výrobce 0x02E1 + první bajt 0x10 (maska 0xFF; prázdná data Samsung nepřijme) + MAC, měnič se pozná dešifrováním klíčem. Test Bluetooth hledá bez filtru (jen s rozsvíceným displejem).
- Plánování: `setExactAndAllowWhileIdle` po 10 min (oprávnění `USE_EXACT_ALARM`), jinak `setAndAllowWhileIdle`.
- Hodinová historie zásuvky měniče jednou denně do `<téma>-menic-hist`.
- Povely: hlídač → `<téma>-cmd` `{ip, on, id, why}`, Flip provede a zapamatuje `cmd_done`.

### Open-Meteo
- Předpověď: `api.open-meteo.com/v1/forecast` (hodinové `shortwave_radiation`, `diffuse_radiation`, denní `weather_code`, teploty), 5 dní zpět + 8 dopředu.
- Archiv: `archive-api.open-meteo.com/v1/archive` (ERA5, ~5 dní zpoždění), dny s výrobou bez počasí, až 900 dní na běh.
- Ukládá se denní součet kWh/m² `[globální, difúzní]` do `data.wx`.

---

## 3. Výpočty

### Upozornění na napětí
Hranice z `nastaveni.txt` (slábne 12,2 / kritická 12,0 / měnič 11,6 V) s návratovými hodnotami (hystereze). Float = 2 kontroly po sobě.

### Kalibrace napětí → stav nabití (interní)
Obecná tabulka AGM (11,80 V = 0 %, 12,85 V = 100 %) natažená mezi 11,80 V a „plnou“ = medián klidového napětí na začátku noci (západ + 2 h) po dni ve Float (+0,04 V za pokles pod nočním odběrem), min. 5 nocí. Uživateli se ukazuje **napětí**, procenta jen z regulátoru.

### Odhad nabití (interní, `track_soc`)
Počítání Ah: `bat_a × 0,92 − (odběr měniče / 0,88 + 6 W) / U`; v noci se pomalu dorovnává ke klidovému napětí; 2× Float = 100 %. Kapacita = naměřená (`eff_cap`).

### Předpověď do rána (`forecast`)
Po západu: stav z napětí (průměr 30 min, bez slunce), odběr = naměřený za měničem (jinak `noc_spotreba_W`), DC = W / 0,88 + 6 W, do `východ + nabijeni_od_vychodu_min`. Výstup: napětí teď a ráno, časy pod alarm / vypnutí měniče.

### Zdraví baterie
- **Noc** (`battery_health`): okno západ + 2 h → východ; pokles napětí (medián prvních/posledních 30 min) na 10 Ah odebraných (živé body, jinak hodinová historie zásuvky; pokrytí ≥ 80 %, ≥ 5 Ah). Noci s koncem pod 12,10 V se nepočítají. Kapacita ≈ 10 400 / (mV na 10 Ah).
- **Nabíjení** (`charge_metric`, orientační): Ah od východu do Float minus odběr, ranní stav z napětí ≤ 85 %, kapacita = Ah / 1,08 / (100 − ranní %). Float ≠ úplně plná → podhodnocuje.
- Verdikt = medián nočních odhadů za 14 dní; pásma 80 / 60 / 45 % z 200 Ah. Upozornění: medián 14 nocí > výchozí stav × 1,2.

### Předpověď výroby (`pocasi.py`)
- Model na **1 panel**: `kWh = a · difúzní + b · přímé` (denní součty kWh/m²), vážené nejmenší čtverce z dní ± 30 dní roční doby (všechny roky, váha `exp(−vzdálenost/15) · 0,6^stáří_v_letech`).
- Vynechané dny: bez počasí, bez `fl`, nebo plná před západ − 1,5 h (přiškrcená výroba).
- Zápornost → jednodušší model (v zimě se naučí b ≈ 0).
- **Zpětná vazba:** večer (po 18 h) se uloží předpověď na zítřek (`fclog`), druhý den se doplní skutečnost; oprava = medián (skutečnost / předpověď) z posledních 14 nepřiškrcených dní, omezeno 0,6–1,6.
- Výsledek × počet zapojených panelů.

### Výhled a provoz (`outlook`, `detect_mode`)
- Provoz: auto (zásuvka měniče vypnutá / Victron OFF a odběr na River > 3 W → zima; odběr za měničem → léto; přepnutí po 3 bězích) nebo ručně.
- Spotřeba chaty = lednice + noční medián „ostatní“ × 24 (bez nabíjení River), jinak zásuvka měniče ve dnech bez River; zima = zásuvky River. Medián 7 dní.
- Léto: ráno → den (+ výroba × 0,9 − denní spotřeba) → noc (− noční spotřeba) → napětí příští ráno.
- Zima: solární baterie se jen nabíjí; den k připojení = ráno ≥ `zima_pripojit_od_V` a po dni s chatou ≥ `zima_pripojit_do_V`.
- Upozornění: zítra připojit solár (zima, večer); přechod sezón (5 dní výhledu vs. spotřeba, max. 1× za 14 dní).

### Panely a pojistka (`panely.py`)
- Denní špička proudu mimo Float `pa`. Počet panelů v historii: od `np_hist` (změny v nastavení; letos 2 panely od 1. 9. 2026), starší: každý rok hledá skok normalizovaného proudu (proud / síla slunce v poledne, Haurwitz) nahoru v srpnu–říjnu a dolů v únoru–květnu (> 1,4×); jinak zvyk 1. 9. / 20. 3.
- Nejhorší případ se 2 panely pro datum: max ze dnů ± 15 dní se 2 panely (přepočteno na sílu slunce); když nejsou, 1 panel × 2; hodnoty > 45 A vyřazeny.
- Přidat 2. panel: jeden nestačí (5 dní výhledu < 0,9 × potřeba) a nejhorší případ ≤ `pojistka_A × pojistka_rezerva` aspoň 90 dní dopředu.
- Odebrat: nejhorší případ > 115 % pojistky do 14 dní. Okamžité varování: naměřený proud > 110 %.

### Automatika River (`river_auto`)
Zapnutí: (Float ≥ 1 měření, napětí ≥ 12,8 V) nebo (Boost a napětí ≥ boost_V + kompenzace − 0,08 V); okno východ + 1 h … západ − 2 h; 20 min po posledním vypnutí. Kompenzace = (25 − T_baterie) × 0,018 V, max ± 0,3 V.
Vypnutí: Boost a napětí < nabíjecí − 0,2 V a zároveň < `float_V` − 0,15 V (pokles na Float = konec Boostu, ne nedostatek slunce); napětí < `river_auto_v_drzet` (13,0) nebo < `river_auto_v_off` (12,5); panely < `river_auto_pv_off` v prvním měření pořízeném > 10 min po zapnutí; západ − 30 min; zastaralá data.
Povel se jednou za hodinu zopakuje; ověřuje se stav zásuvky z brány (do Deníku chyba, když nesedí).

### Odběr z baterie přes den (`overload_check`)
Od východu + 30 min do západu: čistý proud = `bat_a` − (odběr měniče / 0,88 + 6 W) / U. Běžný odběr = lednice (teď) + noční medián „ostatní“ (8 dní); navíc = měnič − běžný. Pod −`odber_z_baterie_A` (2 A) **a** navíc ≥ `odber_navic_W` (40 W) a River není zapnutá automatikou → notifikace, nejvýš 1× za hodinu. Uloží se `data.net_a`.

### Ostatní odběr
`ow = měnič − lednice` (bez doby nabíjení River); noční medián 0–5 h → `day.on`; upozornění při změně > max(5 W, 50 %) proti mediánu 14 nocí.

---

## 4. Data (`data.enc`)

AES-GCM, klíč PBKDF2-SHA256 (200 000 iterací) z `DATA_KEY`. Hlavní klíče:

| Klíč | Obsah |
|---|---|
| `points` | body po 10 min, 14 dní: `t, bat_v, bat_a, bat_soc, pv_w, bat_t, status, ac_w, mw, ow, iv, lw, gw, tp{ip:W}, rv` |
| `days` | po dnech: `solar_kwh, min_v, max_v, mp, soc_min, fl, pa, tp{ip:Wh}, ra_min, on, nv, h, c` |
| `log` | Deník (14 dní): `t, k (ev/auto/err), x, t2, n` |
| `runs` | běhy hlídače (3 dny): `[t, regulátor, brána, Victron]` |
| `wx`, `wxf`, `fclog`, `wxo` | počasí, předpověď, log předpovědí, výstup pro web |
| `inverter`, `last`, `forecast`, `river_auto`, `mode`, `soc_est`, `vcal`, `cfg`, `state` | aktuální stav |
| `plug_hourly`, `plug_names`, `np_hist`, `health_base` | historie zásuvky, názvy, změny panelů, výchozí zdraví |

Krátké shrnutí pro hodinky (ntfy `<téma>-hodinky`): `t, v, soc (regulátor), pv, w, st, fc, lvl (0/1/2), day, ra, vmin`.

---

## 5. Instalace a obnova

1. **GitHub:** repozitář `KptDundee/chata-hlidac`, Secrets (viz výše), Pages z větve `gh-pages`.
2. **Web:** `https://kptdundee.github.io/chata-hlidac/` → heslo = `DATA_KEY`. Pro ⚡ Načíst a Nastavení GitHub token (fine-grained, jen tento repozitář, *Actions* a *Contents: Read and write*).
3. **Flip:** Android Studio → otevřít složku `android` (mimo OneDrive) → ▶ Run. V aplikaci: téma ntfy, Tapo e-mail/heslo, IP zásuvek, MAC a klíč Victronu → *Uložit a spustit*, povolit běh na pozadí.
4. **Hodinky:** složka `hodinky` → ▶ Run přes bezdrátové ladění → zadat téma ntfy.
5. **Ztráta dat:** špatný `DATA_KEY` = nová prázdná historie; historie ze Solar Guardianu se doplní sama importem.

---

## 6. Pravidla pro změny

- Každá změna: zvýšit verzi (`VERSION`, `WEB_VER`), zapsat do `CHANGELOG.md` (nahoru, starší zůstávají) a aktualizovat tyto dokumenty.
- Změna aplikace Flip: zvýšit `versionName`/`versionCode` a `FLIP_VER` ve webu.
- Commity končí řádky `Co-Authored-By` a `Claude-Session`.
