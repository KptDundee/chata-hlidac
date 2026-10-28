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

### Data z Flipu (od Flip 1.4.0)
Flip po měření spustí workflow `hlidac.yml` s `inputs.flip` = JSON pole zpráv (nejnovější + starší z `ghbuf`, do ~40 000 znaků; každá zpráva se pošle 3×, starší než den pryč). Hlídač (`read_inverter`) je čte z `FLIP_DATA`, spojí se zprávami z ntfy `<topic>-menic` (záloha) a s `state.flip_last` (poslední 2), duplicity podle textu zprávy. `state.flip_gh` = kdy naposledy přišla data přes GitHub (pak `wake_flip` nečeká na ntfy). Bez tokenu / při chybě GitHubu Flip posílá postaru do ntfy (+ fronta `outbox`).

### Výhled do rána – učení (`night_learn`, od 4.42)
Při prvním běhu po západu (chata na soláru) `state.dfl_pend` = {t0, t1 = zítřejší východ, pred = noční odběr bez opravy × hodiny}. Po východu: skutečnost = rozdíl `hq` (Ah od plné) mezi t0 a t1, jen když ≥80 % bodů v noci má měnič > 3 W. `state.dfl_log` (10), oprava `data.dfl.f` = medián `act/pred` z posledních 7 (≥2 noci, 0,6–1,6), násobí noční odběr ve `day_outlook`. Délka noci se bere z východu/západu slunce pro konkrétní den.

### Výhled dne – nabídka soláru (`day_outlook`)
Chata na River: „Dnes můžeš přepnout na solár“ se pošle, když `res.ok` a je po dnešním čase z `den_kontrola` (`due` nebo `after`) a před `den_do`; jednou za den (`st.do_conn`). Od 4.30 i během dne, ne jen v čase kontroly.

### Web – grafy (`lineChart`, `pinch`)
Každý čárový graf má zvětšení prsty (`pinch`, od 4.25 všude). Výřez času je v `el._zw` a `lineChart` ho použije i při obnovení dat; `el._lc` drží poslední data a volby. Dvojité ťuknutí výřez zruší. Graf má `touch-action: none` (svislý posun stránky jedním prstem dělá `pinch` sám, s doběhem). `touchmove`/`touchend` se poslouchají přímo na prvku, kterého se prst dotkl (Chrome je posílá i odstraněnému prvku, z něj ale neprobublají), a na `document` (prst mimo graf); stejná událost se zpracuje jednou.

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
**3.58**: `.tip` z-index 40 (okna 20); `pointerleave` schová bublinu jen u myši; ťuknutí mimo svg / posun → `hideAllTips`. `dotChart` popisky poslední hodnoty a minima (bez nocí na River). `fmtT` bez dne v týdnu.
**3.59 / Flip 1.3.4**: Flip `ts` (s) v každé zprávě; neodeslaná zpráva → 1 opakování po 20 s → `outbox` v Prefs (max 150), `flushOutbox` před dalším odesláním; wake lock 4 min. Hlídač: `inv_from_msg` bere `t` z `ts` (když ≤ čas zprávy + 60 s a mladší 2 dnů), `read_inverter` řadí zprávy podle `ts`; `backfill_points` 6 h.
**3.60 / Flip 1.3.5**: workflow vstup `wake` → env `WAKE=1` → `wake_flip`: POST `<topic>-wake`, pak po 10 s kontrola `<topic>-menic/json?poll=1&since=<t0>` (max 110 s). Flip: vlákno `wake` v `GatewayService` – streamované `…-wake/json` (read timeout 150 s, ntfy keepalive 45 s), zpráva → `tick()` (min. 60 s mezi probuzeními), chyba → znovu za 30 s. Web `triggerLive` posílá `inputs.wake = true`, čeká až 330 s. Timeout jobu 7 min.
**3.61**: `overload_check` – `river_on` (st.ra_on nebo zásuvka `river_auto_ip` hlásí `on=1`) nebo `ra_off_ts` < 20 min + zapnutá automatika → bez upozornění; text upozornění + měřené zásuvky (kromě měniče, lednice, River) a čas měření. Web `homeData.extraW` = null, když je zásuvka 8 zapnutá a neměří.
**3.62 / Flip 1.3.6**: `readPlugOnce` vždy `get_device_info` (jméno, model, `d` = posledních 6 znaků device_id); id zásuvky z čerstvého jména, mapa adres jen záloha; nesoulad → `tapo_rescan`. Hlídač drží `d` v `inverter.tp`; upozornění na odběr navíc vypíše jméno / IP / otisk zásuvky měniče.
**3.63**: `read_inverter` – `inv.avg` = {id: W} z rozdílu `wh` (today_energy) mezi dvěma posledními zprávami (300–1800 s), `inv.avg_dt`. `overload_check`: `extra_avg = avg[měnič] − (avg[lednice] nebo okamžitá lednice) − base`; upozornění jen když `extra ≥ 300` nebo `extra_avg ≥ odber_navic_W` (bez průměru jako dřív); jinak záznam „Krátká špička“ do Deníku; `data.extra_avg_w`.
**3.64 / Flip 1.3.7**: `GatewayService.tick` → `ble.ensureRunning(true)` po každém měření; `Collector` burst 40 s. Hlídač `data.vic_t` = čas posledního napětí z Victronu (ze zpráv Flipu); web upozornění při > 60 min.
**3.65 Okno River**: web `rivModel` (River ze `zasuvky_river` + EcoFlow podle jména, generátor `zasuvka_generator`), `rivState`, `tileRivers` (záložky vč. generátoru), `timelineChart` (řádek na zařízení: plný pruh = napájí chatu, světlejší = jen spotřebič, generátor `gw`/zásuvka > 5 W), `detRiver` (DET `river`; původní sekce pod `plugs`). Hlídač `ecoflow_reminder` (`st.ef_remind`).
**3.71 / Flip 1.3.8**: manifest `ACCESS_BACKGROUND_LOCATION`; `BleListener.burstOpen` (sken bez filtru 15 s po neúspěšném 40s filtrovaném, záznam se stavem displeje); `Collector.label(ip)` = „(N) jméno“ v Deníku; `TapoScan` chyby 401 srozumitelně.
**3.75 Nabití #**: `hash_soc` – průchod bodů od `st.hq_t`; `i = bat_a − odběr/bat_v`, odběr = poslední `mw` (≤ 30 min)/0,88 + vlastní spotřeba + desulfátor, chata na River → jen desulfátor, bez dat +30 W; kladné × 0,9. Float ≥ 30 min → `q = 0` (`st.hq_full_t`). Kotva: plné nabití do 7 dní, jinak max `q` za 7 dní. Body `q`, `hq` (Ah od kotvy ≤ 0); `data.hq = {ah, cap (eff_cap), kind full/best, ref_t, pct, full_t}`.
**3.76 Test kapacity**: `capacity_check` 1× denně po východu + 1 h: plné nabití (`st.hq_full_t`) do 30 h před východem, ranní body (východ −2 h … +15 min, pv < 5 W, mw < 120 W, ne `rc`), nejnižší napětí + 10 mV/A odběru → `ocv_soc` (AGM: 11,95 V = 10 % … 12,85 V = 100 %); `ah = −q`; podmínka ah ≥ 20 a soc ≤ 85; `cap = ah / (1 − soc/100)` v 40–300 → `days[k].qc`. `eff_cap`: ≥ 2 testy za 45 dní → medián, jinak dosavadní (noci / štítek). `data.hq.capsrc`, `nqc`.
**3.78**: `hash_soc` přepočítá vše z bodů: `qr` souvislý součet; plná = Float nepřetržitě ≥ 30 min (`fulls`); bod po plném (≤ 3 dny): `qr − max qr od plného`, před plným (≤ 3 dny): `min(0, qr − qr(plné))`, jinak `qr − max qr za 2 dny`. `q = hq`. `days.hq_min` přepisován z bodů. `data.hq.fl_since`.
**3.83 / Flip 1.3.10 / hodinky 1.8**: Flip – `Prefs.GH_TOKEN`; `Collector.runOnce(dispatch)` po úspěšném odeslání `dispatchWatcher()`: POST `api.github.com/repos/KptDundee/chata-hlidac/actions/workflows/hlidac.yml/dispatches` `{"ref":"main","inputs":{"test":false,"wake":false}}`, očekává 204, chyba do Deníku. `GatewayService.tick(dispatch)`: pravidelné měření a wake se zprávou `hodinky` → dispatch; wake z hlídače (`mer`, už běží) → bez dispatch. Souběh hlídá `concurrency: hlidac` (čekající běh se nahradí novějším). Hodinky – `Data.wake`: POST `hodinky` na `<topic>-wake` (Priority 1, min. 2 min mezi), `wake_t` v prefs; `Data.waiting` do 5 min, dokud `d.t*1000 < wake_t`; `fresh()` pak stahuje po 20 s, dlaždice freshness 60 s, jinak 10 min.
**3.86 / Flip 1.3.11**: služba `foregroundServiceType="connectedDevice|location"` + `FOREGROUND_SERVICE_LOCATION`. `GatewayService.startFg`: `startForeground(…, CONNECTED_DEVICE | LOCATION)` (LOCATION jen s ACCESS_FINE_LOCATION); výjimka (Android 14 nepustí typ poloha při startu z pozadí) → jen CONNECTED_DEVICE + záznam do Deníku. `MainActivity.onResume` → `GatewayService.refreshForeground` (akce `fg`: jen znovu `startFg`, bez měření). Důvod: BLE výsledky (BLUETOOTH_SCAN bez neverForLocation) jsou podmíněné přístupem k poloze; bez typu location a bez ACCESS_BACKGROUND_LOCATION ho služba po odchodu aplikace do pozadí ztrácí. Stav ACCESS_BACKGROUND_LOCATION v UI i v Deníku.
**3.87**: `day_yield(vals, rise, base0)` – výroba dne z počítadla `day_kwh`: před východem 0 a základ = poslední hodnota; po východu výroba = max(hodnota − základ), pokles pod základ − 0,01 → základ 0. `record(…, cfg)`: dny mají `dkr` (poslední hodnota) a `dkb` (základ, nastaví se při prvním běhu po východu z `dkr` dneška / včerejška). `import_history`: hodnoty `day_kwh` po dnech → `day_yield` (základ z konce předchozího dne), přepisuje `solar_kwh` (kromě dneška); `hist_v8` spustí nový průchod.
**3.89**: `fix_ts(cfg)` z `oprava_spoju` – `wiring_check` (a web `wiring`) jen body po něm; `hash_soc` nebere Float před ním jako plnou; `capacity_check`: test 1 (od plné, `full_t ≥ fix`) a test 2 `m="2b"` (večer = první bod 2–3 h po západu, ráno = nejnižší napětí před východem; Ah = rozdíl `qr`, nabití z `ocv_soc` klidového napětí, ≥ 12 Ah a ≥ 12 %); oba vyžadují `mw` (Victron) v ≥ 80 % bodů. `qc` = {ok, m, ah, v, soc, t, [ve, soce, te], cap | why}; test starší verze (bez `m`) se zopakuje. `eff_cap` = medián (sudý počet = průměr prostředních) testů po opravě. Web `renderCap`: verdikt z `qc.ok` po `oprava_spoju` (≥ 2), jinak „Zatím neznámo“; noční odhad `h` jen orientační graf.
**3.92**: `capacity_check` projde každé ráno od `oprava_spoju` (body 14 dní) a `qc` přepíše, když se výsledek změní; plné nabití = poslední začátek Float (status 1) před ranním bodem, ≤ 30 h před východem; `qc.tf` = čas toho Floatu. Pokrytí odběru = `mw` (zásuvka za měničem).

**4.67 EcoFlow zkouška 1006**: `ecoflow.probe` pro zařízení s `qerr` – `get_quota` (POST `/iot-open/sign/device/quota`, tělo `{sn, params:{quotas:[…]}}`, podpis přes `_flat`) na obou hostech, seznam `PROBE_Q` (gen: pd.oilVal, pd.type, pd.acPower, pd.totalPower, pd.motorState, pd.oilMaxOutPower, pd.sysMode, pd.ecoMode, pd.remainTime, pd.motorUseTime, pd.errCode; river: pd.soc, pd.wattsInSum, pd.wattsOutSum, bms_bmsStatus.soc, inv.cfgSlowChgWatts); `mqtt_listen` – `/iot-open/sign/certification` → paho-mqtt TLS, odběr `/open/{acct}/{sn}/quota|status|get_reply`, publikace `get` (latestQuotas), 35 s. Spouští se při `ECOFLOW_DEBUG=1` nebo když je generátor online a `st.eco_probe.t` starší 30 min. `st.eco_probe = {t, devs:{sn4:{http, mqtt, on}}}` → `data.eco_probe`; web `ecoProbeHtml`. Workflow instaluje `paho-mqtt`.

**4.68 Nabíjení z generátoru**: `gen_charge_ctl` (krok po `gen_sessions`). Generátor běží = zásuvka `zasuvka_generator` > 5 W (`inverter.gen.w`). `gmax` = `gen_max_benzin_W` / `gen_max_lpg_W` podle `gen_palivo`, `budget = gmax − gen_rezerva_W`. Velké River = online, bez `qerr`, model obsahuje „pro“; nabíjí se = `ac_in_w` (inv.inputWatts) > 20 W. Malá = `gw − Σ ac_in_w` (pod 20 W = 0), počítá se s max(teď, minule). `avail = budget − malá`; rozdělení úměrně `need = (100 − soc) % × wh`, meze `PRO_CHG_W` 200–940 W s dorovnáním, zaokrouhleno na 10 W; když minimum nevejde, nejprázdnější dostane zbytek, ostatní 200 W. `apply`: `ecoflow.set_ac_charge`, změna jen při rozdílu ≥ 50 W proti `st.gen_ctl.w[sn]`, pořadí snížení → zvýšení. Konec běhu → `st.gen_ctl.reset` = River s jiným výkonem než `gen_po_behu_W`, nastaví se, jakmile jsou online. Naprázdno: zásuvka generátoru přítomná (ne `gone`), ≤ 5 W a v tomto běhu už brala → ntfy prio 4 jednou za běh. `data.gen_plan = {t, fuel, gmax, budget, gw, small, avail, rv:[{n, sn, soc, need, w, in, fin}], fin, set, t_on, end}`; `fin = need / (w · 0,9)`. Web `genPlanHtml` (detRiver, detGen), `rivState` generátoru „vypnout ~HH:MM“, skupina nastavení „Generátor“.

**4.69 / Flip 1.7.3 Rychlý režim generátoru**: `Collector.GEN_PLUG = "7"`. Po čtení zásuvek: zásuvka 7 bez `off`/`err` a `w > 5` → pref `fast_until = teď + 5 min`; `gen_missing` = zásuvka 7 v mapě, ale nečte se. `GatewayService.scheduleAlarm`: `fast_until` v budoucnu → `FAST_MS` 2 min, jinak `INTERVAL_MS` 10 min; volá se i po každém `runOnce`. `plugMap`: hledání při `tapo_force` (tlačítko Odeslat teď), nebo `tapo_rescan` a stáří > 8 min při `gen_missing` (jinak 30 min); `TapoScan.scan(…, quiet)` – časté hledání generátoru se nezapisuje, dokud nenajde změnu. Hlídač se spouští s každým odesláním Flipu → při generátoru každé 2 min (`gen_charge_ctl` při každém běhu).

**4.70**: `ecoflow.probe` jen když je generátor online a `st.eco_probe.t` starší 24 h (dřív i při každém `ECOFLOW_DEBUG=1`, tj. každém workflow_dispatch včetně odeslání Flipu); MQTT 35 s.

**4.71 / Flip 1.7.4 Přestěhované zásuvky**: čtení zásuvek ve dvou průchodech. Když v 1. průchodu známá zásuvka (v `tapo_map`) hlásí `off`, `Collector.remap` zavolá `TapoScan.scan(…, quiet, skip)` – test portu 80 na celé podsíti, KLAP jen na adresy mimo `skip` (adresy fungujících zásuvek) a mimo `refused` (401 v poslední hodině). Výsledek s `named` (číslo ve jméně) a jinou IP → přepis `tapo_map`, přenos `offIps` / `goneAt` / `lastGood` na novou IP, log „Zásuvky na nové adrese“, 2. průchod čte znovu. Plné hledání (`plugMap`): prázdná mapa, 6 h, `tapo_force` (Odeslat teď), nebo `tapo_rescan` (záměna jmen / nic nefunguje) po 30 min. Zrušeno `gen_missing` z 1.7.3.

**4.72 Zásuvky vidět**: `plug_watch` – `zasuvky_stale` (čísla), `inverter.tp` podle `ip` (= číslo ze jména). Chybí / `off` / `gone` / `err` → `st.plug_watch[id] = {since, n (počet nových zpráv Flipu), why, warned}`; upozornění prio 4 při `n ≥ 2` a `zasuvky_stale_min`, návrat prio 2. Zásuvka měniče (`zasuvka_menic` / `inv.mip`, výchozí 1) jen při `inv.st == "INVERTING"`. Jména z posledního úspěšného čtení (`st.plug_watch.names`). `data.plug_miss = [{id, n, since, why}]` → web `tileSystem` probs.

**4.73 Lednice po dnech**: `fridge_days` – body se zásuvkou lednice, váha = čas do dalšího bodu (≤ 15 min, jinak se interval vynechá), běží = > 20 W. `days[k].fd` (% času), `fh` (pokryté hodiny), `fn` (rozběhy), `fw` (průměrný příkon za běhu, W·s / s). Přepisuje se jen při stejném nebo lepším pokrytí. Web `detFridge` graf `dl_duty` (barChart, `op` = průhlednost sloupce pro den < 20 h).

**4.74 Jeden verdikt „do rána“**: `nightRow` (dlaždice Solární baterie) – když běží noční předpověď (`forecast.until` > teď, chata ze soláru) rozhoduje ona (`ok_base && cut_by` → „sniž odběr do“, `t_off` → ne, `t_crit` → těsně, jinak ano), teprve pak `day_fc`. `tileNight` přes den (bez běžící předpovědi) bere verdikt z `day_fc` (čerstvý ≤ 30 min, ne River), hodnotu napětí z `wxo.ol` jen když `day_fc` říká vydrží; jinak „došla by ~HH:MM“.

**4.75 Noci na River mimo učení**: `night_log` – po skončení noci (`until`) z bodů s daty Flipu (`tp`, ≥ 6) `nlog[k].riv = podíl bodů s mw > 3 W < 0,8` (i zpětně pro uložené noci). `night_corr` a web `nightCorr` vynechají `riv`. Web: dlaždice Minulá noc, detail a seznam nocí „na River – nepočítá se“.

**4.76 EcoFlow aplikace**: `ecoflow_app.py` – `login` (POST `https://{api-e|api}.ecoflow.com/auth/login` {email, password base64, scene IOT_APP, userType ECOFLOW} → token, userId; GET `/iot-auth/app/certification?userId=` s Bearer → certificateAccount/Password, url, port), `read` (paho TLS, client id `ANDROID_{uuid}_{uid}`, odběr `/app/device/property/{sn}` a `/app/{uid}/{sn}/thing/property/get_reply`, publikace `…/get` {from Android, version 1.1, moduleType 0, operateType latestQuotas}; odpověď `data.online`, `data.quotaMap`; max 14 s). `hlidac.read_ecoflow_app` jen pro zařízení s `qerr`; `st.efp` = relace (nový login po 7 dnech nebo při odmítnutí MQTT), `st.efp_fail` = 1 h pauza po neúspěšném přihlášení. Doplní `KEYS` (soc, in_w, …), `src = "app"`, generátor `gd` podle `GEN_KEYS` a `q` (≤ 80 číselných údajů). `data.eco_app = {t, ok | err, devs}`. Web: karta „EcoFlow – připojení“.

**4.77**: `gen_sessions` – `active = gen_on or (not zasuvka_generator and River nabíjí)`; `gen_cur` se `src == "river"` se při nastavené zásuvce generátoru zahodí (bez záznamu a upozornění). Web `rivState`: generátor jen `x.w > 5`; River `in_w > 20` → zdroj = jiná River s `out_w` ±max(40 W, 40 %), jinak generátor (jen `G.w > 5`), jinak bez zdroje; `out_w > 20` → „dodává … → nabíjí X“.

**4.78**: `tileRivers` – `onX` (River: `ef.online`, jinak zásuvka bez `off`/`miss`; generátor `w > 5`) → třída `on` (plné písmo, ●), `sel` = rámeček; CSS `.rtabs`. `rivState` bez párování River↔River. `batOutlook` → `cls` dlaždice Solární baterie (noční předpověď: `t_off` před `day_fc.end` bad, jinak warn; `t_crit`/`cut_by` warn; přes den `day_fc.ok === false` bad, `night_ok === false` warn). `tileProdSolar` `cls = na` při `pv < 1`.

**4.83**: `read_ecoflow_app` pro všechna zařízení z `/device/list` (ne jen `qerr`); když aplikace vrátí `quotaMap`, smažou se hodnoty z vývojářského rozhraní (soc, in_w, out_w, …) a doplní z aplikace (`src = "app"`). Web `ecoProbeHtml` jen při `qerr`.

**4.85 / Flip 1.7.5 Světla**: `readPlugOnce` – model `L…` → `get_device_info` (device_on → `on`), `get_device_usage` → `result.power_usage.today` → `wh` (jinak `nm`), `lt = 1`. Hlídač propouští `lt`; web `tileUse` řádek „kWh odhad · svítí / nesvítí“.

**4.86**: `river_auto` – zásuvka `river_auto_ip` v `inverter.tp` chybí / `off` / `gone` / `err` ve 3 měřeních → `st.ra_paused` (žádné povely, `data.river_auto = {paused, reason}`); znovu vidět → `ra_paused = False`, ntfy prio 2, automatika pokračuje.

**4.87 Generátor – relace a smyčka**: workflow vstup `gen` (start / stop) → `GEN_CMD`; `permissions: actions: write`, `GH_TOKEN`. `gen_charge_ctl`: `st.gen_ctl = {w (nastaveno), active, btn, first (začátek nabíjení), idle, t_on, ever, stop, reset, safe}`. `step`: velké River `ac_in_w ≤ 20` s jiným než bezpečným výkonem → `gen_po_behu_W` (200); nabíjí se (velká > 20 W, malá `in_w` > 20, nebo generátor > 20 W) → relace aktivní; po 30 s od `first` výpočet (dorovnání mezí 200–940 W), `apply` při rozdílu ≥ 30 W. Konec: `stop` nebo `idle` ≥ 600 s (1800 s po tlačítku bez nabíjení) → všem bezpečný výkon, naprázdno ntfy. Smyčka: `while aktivní and < 180 s: sleep 30; read_ecoflow_app(force)`; `data.gen_cont` → po `save_data` POST dispatch (GH_TOKEN). Výkon generátoru: `inverter.gen.w` (≤ 10 min) nebo `ef_gens[].gd.w`. Web `genPlanHtml` (tlačítko, `genCmd` → dispatch `{gen, wake}`), karta nahoře v detailu EcoFlow.

**4.88**: `ecoflow_app.set_ac_charge(sess, sn, W)` – MQTT `/app/{uid}/{sn}/thing/property/set` {moduleType 5, operateType acChgCfg, params {chgWatts, chgPauseFlag 255}}, čeká na `set_reply`. `gen_charge_ctl`: ovládané = velké (vývojářské rozhraní) + malá se `src == "app"`; meze `PRO_CHG_W` / `SMALL_CHG_W` (100–360), klidové `gen_po_behu_W` / `gen_mala_po_behu_W`. `r.cfg_w` (mppt.cfgChgWatts z aplikace) → `st.gen_ctl.w` (skutečnost); v klidu se odchylka vrací na klidový výkon.

**5.34 / Flip 1.9.0 – nabíjení routeru**: hlídač v povolení `<téma>-fc` posílá navíc `rip` = `zasuvka_router` (prázdné, když `router_nabijeni_rizeni` vypnuto); posílá se i při změně `rip`. Flip `Collector.routerCharge()` (po čtení routeru): `rc_ip` z povolení; baterie z `rt_last`, platná jen když `rt_t` < 25 min; b < 0 → zapnout, ≤ 40 → zapnout, `fc_allow` čerstvé (< 3 h, River / přebytek) → zapnout, ≥ 80 → vypnout, jinak beze změny. Před vypnutím `add_countdown_rule` delay 7200 → on; chyba → nevypínat (`rc_cd_log`). Odesílá `rc` = {on, why, ip} nebo {miss, why, ip}; hlídač `inv.rc`, `data.router_chg` = {ip, rc}. Upozornění `fs.rlow` pod 25 %, reset od 35 %. Web `routerCtl()` (verze < 1.9 → „až s Flip 1.9.0“), řádek v `detFlip`, dlaždice Flip „zásuvka zapnutá / z baterie“.

**5.35 – nápověda nastavení**: `SET_HELP` {klíč: text} u `SETTINGS`; `qh(k)` tlačítko „?“ za popiskem, `qb(k)` skrytý box `#qb_<klíč>` za řádkem; v `renderSettings` klik (preventDefault – řádek přepínače je `<label>`) přepíná `hidden`. CSS `.qh`, `.qb`.

**5.36 – chladnuti.py**: `update(data, st, now, cfg)` v seznamu kontrol („Chladnutí pokoje“). Venkovní teplota `_outdoor` – Open-Meteo hourly temperature_2m (past 2 d, forecast 2 d, unixtime), nejvýš 1× za hodinu, `st.wo` = {t, ll, h: {ts: °C}} 15 dní. Řada pokoje z `points[].th[chladnuti_teplomer]`. `_segments`: vrchol → dokud T ≤ min + 0,3 °C, mezera > 40 min ukončí. `_fit`: vynechá 60 min po vrcholu, větrání (pokles ≥ 0,5 °C mezi měřeními ≤ 15 min) + 60 min; kus ≥ 3 h, pokles ≥ 0,8 °C, T − Tvenku ≥ 4 °C; k = ΔT / ∫(T − Tvenku)dt (lichoběžník). `st.cool_ev` {ta: úsek} max 40, `live` = poslední ještě chladne. Model = medián k z 10 posledních ukončených. Od `chladnuti_min_vecery` (5): simulace krokem 10 min s předpovědí; `pred` = T_teď → ráno, `need_T` z linearity (T_ráno = a·T0 + b). `data.cool` = {room, n, need, k, half_h, T_now, trend, out_now, out, ev, morning, target, pred, need_T}. Web `coolCard()` v `detTemps`.

**5.37**: `_segments` mezera > 70 min (4200 s) ukončí úsek. `_fit` větrání: pokles ≥ 0,5 °C mezi body ≤ 15 min a rychlost od prvního výskytu předchozí hodnoty ≥ max(2,5; 0,3·(T − Tvenku)) °C/h.

**5.38**: `thermo_check` – `st.th_bat` {klíč jména: [b, ts]}; do `inverter.th[]` doplní chybějící `b` a `bt` (kdy změřeno). Web: dlaždice Teploty šedě „(b %)“ po 3 dnech, detail „(změřeno …)“.

**5.39**: `river_supply` (větev EcoFlow): průměr `avg` jen ze souvislého úseku bodů s `rv[k=SN].o` > 3 W (od konce, max 3 h; body bez EcoFlow se přeskočí); `now` = aktuální out − in, `t0`, `wh` jako u zásuvkové větve. Hodinky 🏠 = `rv.now`.

**5.40 / Flip 1.9.1**: povolení -fc má `rfree` = chata na soláru a přebytek (`on_solar and allow`); Flip `rc_free` → router „zadarmo“ jen při `rfree` a b < 100. Chata na River → router jen podle 40 / 80 %.

**5.41 / Flip 1.9.2**: `flip_charge_cmd` – když ne (na soláru a přebytek): `ftgt` = clamp(20 + rate·h + 5, 25, 80), h = do (východ + 3 h), rate = `flip_fc.rate` (`st.flip_rate`, jinak 2 %/h); v -fc `ftgt`, znovu poslat při změně ≥ 5 %. `data.flip_chg.ftgt/f_until/rate`. Flip: `fc_low` (nastaví se pod 20 %), dokud zásuvka zapnutá a není povolení → nabíjet do `fc_tgt` (bez spojení 40 %), pak vypnout a `fc_low` smazat.

**5.42**: body `rbc` (router hlásí nabíjení), `rcon` (zásuvka routeru zapnutá, `inverter.rc.on`). Web `detFlip` graf `df_r` z `rb`, pásy z `rcon` (jinak `rbc`).

**5.43**: `cabin_on_river(data, cfg, now, st)` – měnič ≤ 3 W a zásuvka River > 3 W, nebo `river_sup.w`; paměť `st.onriv_t` 30 min (zruší se hned, když měnič dodává > 3 W). Použito v `hash_alert` (nic), `check` – úrovně napětí (warn přeskočí, crit/off jiný text), noční předpověď (f = None). `other_load` vrací None při mw ≤ 3; `other_load_check` bere jen body s mw > 3, jednorázově (`st.on_fix1`) smaže `days.on` za 14 dní.

**5.44 / Flip 1.9.3**: `RouterM7000.Result.net` = číselné klíče z `wan` obsahující statistic/flow/speed, `_wk` (klíče wan), `_k` (klíče stavu), `dev` (connectedDevices.number) → `rt.net`. Flip `nb` = {up (s od zapnutí), app (TrafficStats uid rx+tx), ph (celkem), mob (mobilní)}. Hlídač `net_usage`: čítače v `st.netc`, přírůstky (pokles / restart telefonu = nová hodnota), `days[k].net` = {rt, ph (Wi‑Fi = ph − mob), app}; `data.net` = {day, dev, rt_day, info}. Web `netCard`, graf `df_net`.

**5.45**: `river_supply` – řada (t, soc) z `points[].rv[k=SN].s` od konce, nejvýš 12 h, stop při nabíjení (i > 20 W) nebo když % zpátky v čase klesne o > 1; rate = Δ% / h (≥ 1,5 h, ≥ 3 %) → h = (soc − rezerva) / rate. `river_sup.rate`, `r_t0`. Web `riverMorning` socM podle rate.

**5.46**: `chladnuti._fit(..., inwin)` – body jen v okně `chladnuti_noc_od`–`chladnuti_noc_do` (místní čas); `st.cool_ver` 2 smaže staré úseky. `data.cool` + `r10` (= k·10 °C/h), `loss_now` (k·(T − Tvenku)), `live` {rate, dif, r10} z trendu za hodinu, `out_err`, `win`. `_outdoor`: pokus unixtime, pak ISO GMT; chyba → `wo.err`, další pokus za 10 min. Web `coolCard` přepsána; EcoFlow graf % – důvod prázdného grafu.

**5.48**: `showTip` – dotyk: bublina nad horní hranou SVG (nebo 70 px nad prstem), vodorovně na střed u prstu. `coolCard` graf venku `gap:7300`. `detRiver` – River bez `soc` (ani v bodech) → karta s větou místo grafu. `chladnuti._fit`: `k` z posledních 3 h kousku (≥ 4 h), `k_all` celý, `avg` = (Ta − Tb)/h; `cool_ver` 3.

**5.49**: `data.cool.out` 8 dní zpět + 24 h dopředu. Web `coolCard` (dlaždice, řádky, tabulka v `<details>`), `coolNight(d, h, n)` – vlastní SVG: okno 20:00–8:00, pokoj z `points[].th`, venku interpolace `out`, předpověď Euler 10 min s `cool.k` od začátku okna `win[0]` (probíhající noc od teď), pás pokoj–venku, šedé okno učení, svislá čára teď.

**5.50**: `data.cool.nights` = noci (okno `win`) za 8 dní přímo z bodů: {ta, tb, Ta, Tb, avg °C/h, To, heat (vzestup ≥ 0,5 °C)}; `data.cool.why` = důvody odmítnutých kousků (`_fit(..., why)`); `cool_ver` 4.

**5.52**: `net_usage` zapisuje přírůstky do posledního bodu: `nr` (router, bajty), `np` (Flip Wi‑Fi). Web `detFlip` – záložky `df_seg` (localStorage `df_tab`), graf `df_nh` (součty po hodinách z `nr`), `netCard` vypíše `*Statistics` čítače routeru.

**5.53 / Flip 1.9.5**: `Collector.countdownOn(t, sec)` – add_countdown_rule, při chybě get_countdown_rules → edit_countdown_rule (id prvního pravidla); vrací null / text chyby. `routerCharge`: vypnout → odpočet 7200 s → při chybě hned zapnout (`rc.err`). `flipCharge` používá stejný pomocník (10800 s).

**5.54**: `thermo_check` – `st.th_last` {klíč: t, h, tm}; teploměr bez hodnot dostane poslední (≤ 7 dní) s `old: 1` a původním `tm` (body grafů jen tm < 30 min). Web: šedě + stáří; `tileFridge` ignoruje `old`. `flip_charge_cmd`: `rfree` = na soláru a pv − mw ≥ 20 W.

**5.56 / Flip 1.9.6**: -fc `fmin` (cfg `flip_min_pct`, 30) → Flip `fc_min` místo pevných 20 %; `ftgt` = clamp(fmin + rate·h + 5, fmin + 5, 80); bez spojení cíl max(40, fmin + 10). Router „zadarmo“ jen b < 90. `data.router_chg.rfree/pv/load`.


**5.57 / Flip 1.9.7**: dokud je zásuvka (9 / 5) vypnutá a má zůstat, Brána každých 30 min znovu nastaví odpočet (`countdownOn`, `fc_cd_t` / `rc_cd_t`) – pojistka zabere jen když Brána neběží.

**5.58 / Flip 1.9.8**: `flip_charge_cmd` – `free_sun` = na soláru, data regulátoru < 30 min, (status 1 a U ≥ float_V − 0,3) nebo (status 2 a U ≥ boost_V(komp.) − 0,1), pv ≥ 20 W a net_w = 0,95·pv − (mw/0,88 + menic_vlastni_W) ≥ −5 W. `allow` (Flip) = `rfree` (router) = `free_sun` na soláru, jinak False. `data.sun_free` pro web. Flip: `fc_allow` výchozí false; router po neúspěšné pojistce 6 h nevypíná (`rc_cd_fail_t`); `fc.err` = chyba pojistky Flipu.

**5.59**: `flip_charge_cmd` – okno `eve` = západ − 3 h … západ − 1 h; `eve_flip` = na soláru, regulátor čerstvý, net_w − 15 W (když zásuvka Flipu vypnutá) ≥ 0 (zapnutá: net_w ≥ −10); `allow` = free_sun nebo eve_flip; `rfree` = free_sun nebo (okno a net_w − 8 W − (15 W, když se Flip teprve zapne) ≥ 0). `data.sun_free.eve/eve_flip/set`.


**5.60**: `data.flip_chg.t_hit` (kdy Flip při rate klesne na flip_min_pct), `tgt_hit` (cíl dobití v tu chvíli), `ok_until` (vydrží do světla bez nabíjení).


**5.61**: `tileFlip` – záložky `data-ftab` (flip / wifi, localStorage `df_tab` společné s detailem), klik v `#home` → `renderHome`.

**5.62**: `hash_soc` – kotvy klidu `rests` (t, qr, Ah od plné = −(100 − soc_from_v(U))/100·cap): úsek ≥ 60 min s |i_net| < 0,8 A a pv < 5 W (i_net z odběru měniče), konec úseku. Bod bez Float do 3 dnů: h = Ah kotvy + (qr − qr kotvy), kotva ≤ 4 dny před (nebo ≤ 1 den po); jinak dřívější „nejlepší stav za 2 dny“. `data.hq.kind` = full / rest / best, `ref_t` = čas kotvy.

**5.63**: kotva klidu až po ≥ 2 h; `data.hq.rest` = {v, soc, h, ah}, `hq.vfull/vempty` (VCAL). Web `detBat` řádek „Jak se # spočítalo“.

**5.64**: kotva klidu v `hash_soc` – `ocv_soc(U)` (AGM_OCV) místo `soc_from_v` (VCAL). Kapacitní testy a předpovědi zatím beze změny (používají VCAL).


**5.65 / Flip 1.9.9**: Flip ukládá poslední úspěšné přečtení routeru (`rt_good_b/t`); `routerCharge` ho 60 min použije, když je ≥ 50 
**5.65 / Flip 1.9.9**: Flip ukládá poslední úspěšné přečtení routeru (`rt_good_b/t`); `routerCharge` ho 60 min použije, když je ≥ 50 procent. Web u „nejde přečíst“ ukáže `rt.err`.

**5.66**: web `small12(x)` – River s kapacitou < 500 Wh, online, výstup z EcoFlow > 2 W a nenabíjí se → „napájí 12 V (světla)“ + výdrž (soc − 5 %) · Wh · 0,9 / W. Volá se na začátku `rivState`.

**5.69**: `river_capacity` – pro každou River (SN) z bodů `rv[k].s/i/o` + zásuvka (`river_for_plug` → `tp[pid]`) úseky vybíjení (i ≤ 20 W, % neroste o > 1, mezera ≤ 40 min); energie lichoběžníkem do posledního poklesu %; hotový úsek = pokles ≥ 20 % a 3 h bez dalšího poklesu nebo ≤ 2 %. `st.rv_ses[SN]` (20), `data.rv_cap[SN]` = {name, nom, cap (medián 8), n, ses, live, src}. Web `rvCapCard` v `detRiver`.

**5.72**: `river_capacity` – energie úseku z `tp_hist[pid][den]` (hodiny, poměrné krajní), jinak integrace W (src „s dírami“, když mezera > 40 min); úsek se přeruší až mezerou > 3 h; překrývající se starší úseky se nahradí; `st.rv_ses_v` 2. `rv_cap[SN].drop_sum`. Web `rvCapCard` – „pojme asi“, spolehlivost (n ≥ 2 a součet poklesů ≥ 80 %), nová ≈ 0,87 × štítek.

**5.74**: `river_capacity` – nabíjení: souvislé body s `rv.i` > 20 W (mezera ≤ 40 min), energie = integrál `i` do posledního nárůstu %, nárůst ≥ 20 %; `st.rv_chg[SN]`, `rv_cap[SN].chg` = {per100 (medián 8), n, ses}. Web „nabití 0 → 100 % potřebuje ~X Wh … zpátky dá Y %“.

**5.77 / Flip 1.9.11**: BleListener – před startScan vždy `stopScan(cb)`, v `onScanFailed` `stopScan(this)`, po úspěchu `lastError = null`. GatewayService `dailyRestart()` (čas z -fc `rst`, Prefs `rst_at`; jednou denně do 2 h po čase): `collector.softReset()` (tapo/names/models, tapo_rescan, tapo_force), `ble.stop()+ensureRunning(true)`, nový wake listener, 20 s čekání. Collector přidá `rst` {t, ble_ok, ble_err, plugs_ok, plugs} do prvního měření (do 30 min). Hlídač `check_gateway`: zpráva podle `inv.rst` (jednou na t), a „neozvala se“ 25 min – 2 h po čase restartu, když inv.t < čas (jen Flip ≥ 1.9.11).

**5.79**: `wiring_check` – platný bod: pv < 5 W, nebo |pv − pv předchozího bodu| ≤ 10 W a |ivs| ≤ 60 s. Akutní upozornění až po 2 platných překročeních do 1 h (`st.wire_pend`), pak `wire_acute` s n = 2.

**5.80**: `wiring_check` – `r_mo` = úbytek / (ir + ii) od 5 A; překročení = úbytek ≥ kabely_ubytek_V nebo r_mo ≥ kabely_odpor_mOhm; stálé slunce |Δpv| ≤ max(10 W, 10 %). Denní odpor od 5 A, ne do 24 h po akutním upozornění.

**5.83**: obecné `tabsHead(key, tabs)` / `tabsWire(key, ids)` (tlačítka `#<key>_seg`, obsah `#<key>_<id>`, localStorage `<key>`). `detBat` – `bt_tab` (data / now), `detTemps` – `tt_tab` (data / cool, `coolCard(coolBox,…)`).

**5.84**: `detUse` – `us_tab` (g / n, společné pro všechny zdroje), `detGen` – `gn_tab` (data / start: `genPlanHtml` + `fuelHtml`).

**5.85**: `data.rv_last[sn6] = {soc, t}` (jen online). `check_river`: `supplying` = out_w > 20 a in_w ≤ 20 – podmínka pro 15/10/5 %. `gen_charge_ctl.step`: `gs.rp/rwh/rs` – příjem každé River (acw, lichoběžník, mezera ≤ 300 s), `days[d].rv[sn6].gi`; konec relace → `gen_sum_msg` (ntfy), `st.gen_sum_t` potlačí „Generátor doběhl“ z `gen_sessions` (2 h). Web `rvSoc`, graf `dg_rv` bere `gi ?? i`.

**5.86**: blok „Předpověď do rána“ v `check` odstraněn (st.night_warned / night_cut). `urgent_river` bez výjimky `ok_base/cut_by`. `predpoved_noc` se nepoužívá (odstraněno z webu).

**5.87**: `check_gateway` – stupně `telefon_upozornit` při funkčním řízení (zásuvka `zasuvka_flip` vidět, bez off/err) jen < `flip_min_pct` − 5.

**5.88**: `day_outlook` – `load_a` z `cons_cmp.day_typ_wh / 24` (fallback průměr 3 h).

**5.89**: `river_capacity` – přerušení úseku, když výstup ≤ 3 W aspoň 1 h (`idle0`), `rv_ses_v` 3.

**5.91**: `flip_charge_cmd` – `allow` = na soláru, regulátor čerstvý, pv ≥ 20 a `net_w` ≥ 15 W (vypnuto) / ≥ −15 W (zapnuto, nabíječka je v `mw`). `rfree = allow`. `data.sun_free` → `data.flip_sun {on, solar, river, pv, load, net_w, need, chg, fmin}`.

**5.92 / 1.9.12**: -fc `full` (na soláru, regulátor čerstvý, status 1 a U ≥ float_V − 0,3) → allow; Brána `fc_full` (≤ 75 min) → nabíjet do 100 % před pravidly 80 / 75 %. Web `menicOff` bez `err`.

**5.93**: `store_inverter` – `log("err", "Zásuvka (N) nejde přečíst: …")` pro zásuvky s číslem (≤ 2 číslice) a `err`; slučuje `flush_log`.

**5.94 / 1.9.13**: zásuvka „off“ nese `ow` = druh chyby · .IP; hlídač ho drží v `inv.tp`, `plug_watch` ho dá do důvodu, do Deníku `log("err", "Zásuvka (N) nedostupná: …")`.

**5.95**: `alarm(st, topic, key, active, …)` – stav v `st.al[key] = {t0, last, title, ack, snz}`, opakování `ALARM_REPEAT_S` (570 s), tlačítka posílají do `<téma>-ack` „ok|30|60:<klíč>“ (staré bez klíče = `night`), zpracuje `alarm_acks` na začátku běhu. `digest(st, title, msg)` → `st.digest`, vypíše `daily_summary` („👀 K pozornosti“, pak smaže); aktivní alarmy „🚨 Trvá“. `data.alarms` pro web (`alertItems`). Klíče: bat_low, reg, pv, fuse, wire, inv_al, gw, wifi, plugs, flip_low, flip_hot, router, fridge, frost, rv_<sn6>, night, day, gen_off. `urgent_river` bere i `st._rvn` z `river_supply`. Odstraněno `hash_alert`, `ecoflow_reminder`.

**5.97 / 1.9.14**: -fc `stale` = zasuvky_stale (bez měniče, když nedodává); Brána `mustOff` – zásuvka ze seznamu off/err/nevidět ≥ 10 min → `tapo_force` (plné hledání, 1× za 30 min). MainActivity: záznam `setTextIsSelectable`, tlačítko Kopírovat.

**5.101**: `capacity_check` z `data.rests` (kotvy klidu z `hash_soc`, i `qr`) a `data.fulls`; body s neznámým odběrem `lu`. `eff_cap` = medián `qc` s `v2 == 2` (≥ 2), jinak `kapacita_odhad_Ah`. `calibrate` vypnuto (VCAL 12,85 / 11,80). `forecast` z `hq.pct` + `night_load_a` (sdíleno s `day_outlook`), corr = 0. `track_soc` bere `hq.pct`. Web `nightCorr` = 0.

**5.103 / 1.9.15**: `Collector` druhý průchod – když je mezi off zásuvkami některá ze `stale_ids` a poslední plné hledání > 5 min → `tapo_force` + `plugMap` (plné hledání, nové relace) a nové čtení; jinak rychlé `remap` jako dřív.

**5.104 / 1.9.16**: Brána přidá do měření `pdown` = [{ip, n, ow, back}] (zařízení s vypršením spojení před plným hledáním a jestli se vrátila); hlídač `inv_from_msg` → `inv.pdown`, `plug_watch` (nová zpráva) → Deník + `days[d].pdn[jméno]`, `daily_summary` řádek.

**5.114**: `record()` – bod v čase měření (`now − age_min`), stejné měření ±90 s se jen doplní; `data.updated` = čas měření. `attach_flip(data, st, inv, now, cfg, topic)` (dřív v `main` jen při čerstvém regulátoru): `flip_point(data, t)` = nejbližší bod ±300 s (přednostně s `bat_v`), jinak nový `bf: 2`; počítadla zásuvek `st.tp_raw` + `st.tp_raw_t`, měření ≤ `tp_raw_t` se přeskočí, přírůstek `split_days(t0, t1, x)` podle půlnoci. `attach_rivers` stejně (čas běhu). `sync_inverter_voltage(data, inv)` porovnává s `p.t`. `hash_soc` bere `mw`/`cs` z nejbližšího bodu Flipu ±300 s. `flip_charge_cmd` = poslední bod s `bat_v`.

**5.113**: `cabin_src(mw, rw, vst)` → s / r / 0 / ? (mw None a Victron ne OFF → ?; rw None → ?); `river_w`, `vic_state` (st jen při `age` ≤ 1200 s), `inv_src(inv, cfg)`, `pt_src(p, cfg)` (bod `cs`; starší body: mw None a River > 3 W → r). Bod dostane `cs` v `main` i `backfill_flip`. Používají: rozdělení `tps` (`u` = nevíme), `hash_soc` (zátěž desulfátor jen při mw None a cs r/0), `night_modes`, `river_days`, `night_log.riv`, `night_load_a`, `night_learn`, `cabin_on_river` (EcoFlow `river_sup` jen při cs None), `detect_mode`, `river_supply(_plugs)`, `flip_charge_cmd`, `day_outlook`. `data.cabin = {cs, riv, vst, t}`. Web `cabinSrc/invSrc/ptSrc` (stejné pravidlo, test 96 kombinací), `homeData.cs/srcUnk`, `menicOff` = mw null a Victron OFF, `rvOn` = `cabin.riv`, `ptMode` „u“.

**5.112**: hodinová energie zásuvek – `hourly_merge(store, dk, arr, today)` (minulý den nepřepsat řadou s o > 20 % a 20 Wh menším součtem), `inv_hourly(data, cfg, dk)` (zdroj `tp_hist[mip]`, záloha `plug_hourly`; platí jen když součet ∈ 0,6–1,5 × `days[dk].tpl[mip]` (živý součet, jinak `tp`), pokud ten ≥ 100 Wh; jinak None). Používají ho `night_plug`, `battery_health` (přepočet `h_v3`), `load_lookup`, `night_modes` (`mns` = zdroj p/h; odhad z historie bez ověřených dat se smaže). `tp_hist` drží `HIST_KEEP_DAYS = 120`. `read_tp_history` minulý den nesníží pod 0,6 × dosavadního součtu. `days[k].tpl` = jen živé přírůstky. Rozbor nocí: `night_plug` při každém běhu pro všechny noci. Web `invPlugCheck(d, R)`.

**5.111**: `night_plug(row, k, …)` – spotřeba za měničem v noci (`nwh`, `nah`, `dwh`, `dnet`) oddělená od `night_row`; `night_history` ji při každém běhu doplní u nocí, kde `nah` (nebo `dnet`) chybí. Důvod: `-menic-hist` nese jen celé uplynulé dny, ranní hodiny noci k dorazí až v den k+2; noc se přitom zapisuje už 2 h po východu dne k+1 a dál se nepřepočítávala. Chyba stahování SG už nekončí `return`, ale `break`.

**5.110**: jeden noční verdikt – když běží `forecast` (`until` > teď), `nightRow`, `tileNight`, banner 🌙, `dayFcBlock` (řádek „Do rána“), `forecast_text` i souhrn/watch berou jen `forecast`; `day_fc.night_ok` jen přes den. `t_crit` (pod `baterie_kriticka_V`) = „nevydrží“ všude (dřív „těsně“), `t_off` = „měnič se vypne“.

**5.109**: web `withHist(pts, U, t0, t1)` – chybějící `tp[id]` v bodě z `tp_hist[id][den][hodina]` (Wh = W průměr), hodiny bez bodu → 3 body (:10, :30, :50), označené `_h`. Použito v `detUse`.
