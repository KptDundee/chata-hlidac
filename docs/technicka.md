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
| Ciferník | `hodinky/cifernik/` (`cz.petr.chatahodinky.cifernik`) | Watch Face Format v2 (jen XML + PNG, bez kódu), minSdk 34 |
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
Zapnutí: (Float ≥ 1 měření, napětí ≥ 12,8 V) nebo (Boost a napětí ≥ boost_V + kompenzace − 0,08 V); okno východ + 1 h … západ − 2 h; pauza po vypnutí 20 min × 2^neúspěchy (max 120 min; neúspěch = vypnuto kvůli vybíjení / slabým panelům do 40 min od zapnutí). Kompenzace = (25 − T_baterie) × 0,018 V, max ± 0,3 V.
Vypnutí: čistý proud do baterie (`bat_a` − (odběr měniče / 0,88 + 6 W) / U) < −`odber_z_baterie_A`; Float a napětí < `float_V` − 0,4 V; Boost a napětí < nabíjecí − 0,2 V a zároveň < `float_V` − 0,15 V (pokles na Float = konec Boostu, ne nedostatek slunce); napětí < `river_auto_v_drzet` (13,0) nebo < `river_auto_v_off` (12,5); panely < `river_auto_pv_off` v prvním měření pořízeném > 10 min po zapnutí; západ − 30 min; zastaralá data.
Povel se jednou za hodinu zopakuje; ověřuje se stav zásuvky z brány (do Deníku chyba, když nesedí).

### Odběr z baterie přes den (`overload_check`)
Od východu + 30 min do západu: čistý proud = `bat_a` − (odběr měniče / 0,88 + 6 W) / U. Běžný odběr = lednice (teď) + noční medián „ostatní“ (8 dní); navíc = měnič − běžný. Pod −`odber_z_baterie_A` (2 A) **a** navíc ≥ `odber_navic_W` (40 W) a River není zapnutá automatikou → notifikace, nejvýš 1× za hodinu. Uloží se `data.net_a`.

**Kabely a spoje (web 3.8)**: body s `bat_v` (regulátor) i `iv` (Victron) za 3 dny; I_reg = max(`bat_a`, 0), I_měnič = (`lw` nebo `mw`)/0,88 + 6 W)/`iv`; ΔU = `bat_v` − `iv`. Offset přístrojů = medián ΔU v bodech bez proudu (I_reg < 0,5 A a I_měnič < 3 A, aspoň 3 body). R = medián (ΔU − offset)/(I_reg + I_měnič) z bodů s proudem ≥ 8 A (aspoň 4, jinak poslední bod při ≥ 5 A). ≥ 10 mΩ = karta oranžově, ≥ 20 mΩ červeně. Počítá se jen ve webu; zápis měření v návodu je v localStorage (`wire_meas`).

**Dlaždice Bilance (web 3.7)**: bilance W = (`bat_a` − (`mw`/0,88 + 6 W)/`bat_v`) × `bat_v`; ±0,5 A = „vyrovnané“. Graf z historie bodů (stejný vzorec po bodech, `modes:true`, referenční čára 0), denní součty kWh kladné/záporné části zvlášť.

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

Krátké shrnutí pro hodinky (ntfy `<téma>-hodinky`): `t, v, soc (regulátor), pv, w, st, fc, lvl (0/1/2), day, ra, vmin, lat, lon`.

**Ciferník (WFF v2)**: `res/raw/watchface.xml`, plátno 480×480. Grafiku kreslí `cifernik/grafika/generuj.py` (pycairo) – polohy subdialů a ruček musí odpovídat XML. Slot 0 = `VoltComplication` (RANGED_VALUE, trojúhelník −135…+135° podle min/max), slot 1 = `SunComplication` (RANGED_VALUE 1 = příští východ / 0 = západ, text = čas; ikonky sun_up/sun_down přímo v ciferníku přes Condition; náhradní systémový SUNRISE_SUNSET), slot 2 = `TempComplication` (Open-Meteo current temperature_2m, poloha getLastKnownLocation / chata / Praha, mezipaměť 20 min, RANGED −20…40). Baterie hodinek `[BATTERY_PERCENT]`. AMBIENT: stejný ciferník, jen vteřinovka skrytá (Variant alpha 0) a místo ní ocelová krytka; vteřiny bez Sweep (skok 1×/s). Validace: XSD z github.com/google/watchface (`xmlschema.XMLSchema11`).

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


**Deník nocí a učení (3.18)**: `night_log` – hodinu po západu `nlog[YYYY-MM-DD] = {p (s opravou), raw, corr, until, t, v0, w, cap}`; po `until` + 15 min `a` = minimum napětí v [until − 1 h, until + 15 min], `min` = minimum přes noc. `night_corr` = medián (a − raw) z posledních 10 nocí (≥ 3), omezeno ±0,4 V; `forecast` přičte opravu k `v_until` (a nastaví t_crit/t_off na `until`, když opravené napětí padne pod hranici). Jednorázový zpětný výpočet ~12 nocí z bodů (`nlog_bf`). Web: `dayPhase` (predawn / day / evening podle `data.sun`), dlaždice Dnes / Příští noc podle fáze, sekce Uplynulé (Minulá noc z bodů + nlog, Včera z `days` + `wxo.acc`).

**Relativní dny (3.20)**: web `relN / relDay / relGen / nightName / rano / doRana` (podle `dkey` v Europe/Prague), hlídač `rel_day / do_rana`. Každé ráno / noc / večer v textech nese dnes / zítra / včera; noc se pojmenuje podle rána, kterým končí (`f.until`, jinak zítřejší, před východem dnešní). Pozor: `wxo.ol.days[i].mv` je ráno **po** dni i – pro „zítra ráno“ se bere řádek dneška.
**Denní energie zásuvek (3.18)**: `day.tp[ip]` = součet přírůstků počítadla `wh` (pokles = reset → přírůstek = nová hodnota); poslední hodnoty v `state.tp_raw`.

**Odběr navíc (3.21)**: `overload_check` počítá `extra = mw − lednice_w − medián on` ; od 3.22 se neměřená lednice (`err`/`off`/chybí) počítá jako `lednice_max_W` (80 W), notifikace hned při první kontrole (nejvýš 1× za hodinu), každý zásah do Deníku s rozpadem.

**Rozbor nocí (3.23)**: web `nightRows` z `points` (14 dní): západ/východ = poslední/první bod s pv_w ≥ 3, `v0` 1 h po západu, `vmin` do východu + 1,5 h, `ah` = Σ (mw/0,88 + idle)/V·dt, `fr` = Wh lednice, `dah` = čistý přítok přes den (bat_a − odběr), `slope` = mV na 10 Ah, `tmin` z bat_t. `nightAnalysisHtml` porovná posledních 5 nocí se staršími.

**Historie nocí (3.24)**: `night_history` / `night_row` – po 10 dnech odzadu (max 60 s za běh) stáhne ze SG `bat_v, bat_a, status, pv_w, bat_t` a pro každou noc k (večer k → ráno k+1, časy ze `sun_times`) uloží `data.nh[k] = {hrs, v0 (západ+45–75 min), vmin (do východu+1,5 h), ve, ai (Ah z regulátoru přes den), fl, bm (min v Boostu), vmax, tn, prod, nwh/dwh (Wh zásuvky za měničem z plug_hourly), nah (Ah z baterie přes noc), dnet (Ah čistě do baterie přes den)}`. Web `nightRowsHist` – je-li ≥ 8 nocí, použije je místo bodů.

**River jako zdroj (3.26)**: `river_supply` – aktivní River = online, out_w − in_w > 3 W (nejvyšší výstup); průměr výstupu z `points[].rv[i].o` za 3 h; `h = max(0, soc − river_rezerva_pct)/100 · river_Wh · 0,9 / průměr`; `data.river_sup = {name, soc, w, h, until, cap, res}`; večer (západ + 1 h až východ) notifikace, když `until` < příští východ + 1 h. Hodinky: `fc` = River, `rv` v těle zprávy. Web `riverMorning`, `tileRiver`, `tileNight`. **Záloha bez EcoFlow (3.44)**: `river_supply_plugs` – zásuvka z `zasuvky_river` s odběrem > 3 W (nejvyšší) → `river_sup = {name, w, now, t0, wh, id, plug: True}`; `t0` = začátek souvislého úseku bodů `points[].tp[id] > 3`, `wh` = integrál za ten úsek; průměr za 3 h. Hodinky: `fc` = „🔋 jméno · W / od HH:MM · kWh“, `w` = mw + rw.


**3.45 Solární baterie**: web `tileSolar`, `batAcute` (jen akutní: regStale, < CRIT/WARN, odběr navíc), `batFlow` (z `netB`); `homeData` přidává `menicOff` (Flip čerstvý, `inv.mw` chybí a zásuvka měniče off/gone/err/nenalezena), `loadB` (W ze solární baterie, 0 při vypnutém měniči), `netB`, `rvOn`. `riverBands(pts, ids)` = úseky, kdy `points[].tp[id River] > 3` → `lineChart(..., {bands})` šedé pozadí. Graf odběru/bilance: `ld = mw/0.88 + idle`, při River a mw null → 0; `b = bat_a·bat_v − ld`. Denní grafy aspoň 30 dní. Hlídač: `days[k].soc_max` (živě), `import_soc_history` (stav `soc_hist_*`, 40 s na běh, po měsících zpět, konec po 3 prázdných / 60 měsících) → `soc_min`/`soc_max`.
**3.46**: `lineChart` volba `k2 = {key, color, name}` = druhá řada ve stejném grafu (napětí: `bat_v` + `iv`). Detail baterie: grafy → čísla → výklad; `dotChart` nejnižšího napětí dne (poloměr bodu podle počtu dní).
**3.47**: `backfill_points` (před `record`): historie SG za 3 h (bat_v, bat_a, pv_w, status, bat_soc), body s `bf: 1` tam, kde chybí bod ±5 min; aktualizuje min/max dne. `record`: min/max dne jen z `bat_v`, registr regulátoru → `days[k].min_vr`. `import_history`: `hist_v7` → nový průchod s `minmax_over` (min/max dne přepsány vzorky z historie, kromě dneška). Web: `k2` kreslena čárkovaně nad první řadou, graf `dc_vd` (bat_v − iv), `#boot` při načítání.
**3.48**: `days[k].min_t` = čas minima (record, backfill, import). `backfill_points` poprvé za 14 dní (`st.bf14`), pak 3 h; při plném doplnění přepočítá dnešní min/max z bodů. Web: `lineChart` volba `dayMin` (kroužek + hodnota nejnižšího bodu každého dne), `dotChart` bublina s časem minima.
**3.49**: `night_modes` (každý běh, posledních 120 dní): okno [min_t − 6 h, min_t] (bez min_t 00:00–06:00); body s `mw`/`tp`: mw > 5 → solár, zásuvka River > 3 nebo chybí mw → River (≥ 3 body); jinak `plug_hourly` průměr > 5 Wh/h → "s", jinak "r" (≥ 3 hodiny). → `days[k].mn`. Web: `dotChart` (○ pro "r", čára jen přes ostatní), `dayMin` značka šedá, `dayExt("min_v")` vynechá "r".
**3.50**: `night_modes` – dny před `river_noci_od` (výchozí 2026-10-15) vždy "s".
**3.51 Spotřeba**: hlídač – v cyklu přírůstků zásuvek `fs = S/(S+R)` (S = zásuvka měniče W, R = Σ zásuvek River W; před `river_noci_od` 1) → `days[k].tps[id] = {s, r}` Wh. `migrate_plug_ids` (`st.tp_mig1`): stará jména bez „(N)“ podle regexu měnič/220, lednice, wifi/router → nová čísla v `days.tp` a `points.tp`; `data.tp_mig` = {stará IP: [nové id, staré jméno]}. `DEFAULTS.desulfator_W` 0,25. Web: `useModel`, `useAt` (bod: S, R, zásuvky, `_o` = max(0, S+R − Σ zásuvek)), `useDay` (den z `tp`/`tps`; před 14. 10. jen 220 V, lednice, Wi‑Fi), `stackChart` (složené plochy W, pásy River), `stackBars` (složené sloupce kWh/den), `detUse`, `tileUseTotal`; CSS `--s4..--s8`, `.ut` tabulka.
**3.52**: `fs` = 1 když zásuvka měniče > 3 W, 0 když ne a River > 3 W. `ptRiver` (web) = měnič ≤ 3 W a River > 3 W; `river_supply_plugs` jen když `inv.mw` ≤ 3; `rvOn` taky.
**3.53**: `detUse(body, src)` src a/s/r (DET `use`, `use_s`, `use_r`). `useAt` → {m, a, s, r}: zdroj hlavního okruhu m = `ptMode` (od `USE_FROM` 14. 10.); měřené zásuvky patří m; `s._o = S − Σ (m=s)`, `r._o = R − Σ (m=r)`; null, když zdroj neběžel. `useDay`: podíl River u zásuvky z bodů dne (`useShares`), jinak `tps`, aplikovaný na `tp` → s + r = celkem. Dlaždice Ze soláru / Z River = `useDay(...).s/r._sum`.
**3.54**: `sync_inverter_voltage` – čas měření Victronu `inv.t − inv.age`, regulátoru `now − age_min` (poslední bod) / `t` (doplněné body); nejbližší bod do 150 s dostane `iv`, `lw`, `ivs` (posun s). `wiring_check`: řádky s `ivs` za 3 dny; `off` = medián dv v klidu (ir < 0,5 A, ii < 3 A); akutní: poslední < 30 min, dv − off ≥ `kabely_ubytek_V` → ntfy (6 h); odpor = medián (dv − off)/(ir + ii) při ≥ 8 A za 24 h (≥ 4 vzorky) ≥ `kabely_odpor_mOhm` → ntfy 1× denně; `data.wire_off`, `data.wire_mo`. Web `wiring()` jen body s `ivs`; graf `dc_vd` = dv − off.
**3.56**: okna `detm`, `plugm`, `wirem`, `set` – MutationObserver na třídě `hide`: otevření → `history.pushState`, zavření křížkem → `history.back()` (popstate přeskočen); `popstate` zavře poslední otevřené okno.
**3.57**: `read_inverter` → `inv_from_msg(m, now, cfg)` (parsování jedné zprávy) + `data._inv_msgs` (všechny zprávy za 12 h, neukládá se). `backfill_flip`: zprávy kromě poslední → k bodu ±300 s bez `tp`/`mw` doplní `ac_w`, `mw`, `gw`, `tp`, jinak nový bod `bf: 2`; napětí Victronu k bodu regulátoru ±150 s (`iv`, `ivs`, `lw`).