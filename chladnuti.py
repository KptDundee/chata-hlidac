"""5.36: jak rychle chladne pokoj, když se přestane topit (Newtonův zákon ochlazování).

dT/dt = −k · (T_pokoj − T_venku)    k [1/h] = vlastnost chaty (izolace, větrání netěsnostmi)

Učení: z teplot pokoje (teploměr Xiaomi, body po 10 min, 14 dní) se hledají úseky chladnutí – od nejvyšší
teploty (dotopeno) dokud teplota znovu nestoupne o 0,3 °C (zase se topí / konec); výpadek teploměru do 70 min úsek nepřeruší. Prvních 60 min se vynechá
(kamna ještě hřejí). Větrání = prudký pokles (≥ 0,5 °C, rychlostí od poslední změny hodnoty aspoň 2× rychlejší než nejrychlejší běžné chladnutí) – ten kus a 60 min po něm
se vynechá. Z každého použitelného úseku (≥ 3 h, pokles ≥ 0,8 °C, pokoj aspoň o 4 °C tepleji než venku):
    k = (T_začátek − T_konec) / ∫ (T_pokoj − T_venku) dt
Venkovní teplota: Open-Meteo po hodinách (Praha-Hrdlořezy, venku_sirka / venku_delka), historie se drží 15 dní.
Model = medián k z posledních 10 ukončených úseků; předpovědi až od chladnuti_min_vecery (5) úseků.
Předpověď: krokem 10 min s předpovědí venkovní teploty. Kamna po dotopení ještě hřejí, takže skutečnost bývá
spíš o něco tepleji (předpověď je opatrná).
"""
import json
import math
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

FC_URL = "https://api.open-meteo.com/v1/forecast"
from zoneinfo import ZoneInfo
_TZ = ZoneInfo("Europe/Prague")


def _outdoor(st, cfg, now, log=print):
    """Venkovní teplota po hodinách → st["wo"] = {"t": poslední stažení, "h": {ts: °C}} (15 dní zpět + 2 dny dopředu)."""
    wo = st.setdefault("wo", {"t": 0, "h": {}})
    ts = int(now.timestamp())
    lat, lon = cfg.get("venku_sirka") or cfg["sirka"], cfg.get("venku_delka") or cfg["delka"]
    if wo.get("ll") != [lat, lon]:
        wo.update(t=0, h={}, ll=[lat, lon])
    if ts - wo.get("t", 0) >= 3600:
        errs = []
        for extra in ({"timeformat": "unixtime"}, {"timezone": "GMT"}):
            try:
                q = urllib.parse.urlencode({"latitude": lat, "longitude": lon, "hourly": "temperature_2m",
                                            "past_days": 2, "forecast_days": 2, **extra})
                with urllib.request.urlopen(f"{FC_URL}?{q}", timeout=25) as r:
                    js = json.loads(r.read().decode())
                h = js.get("hourly") or {}
                n = 0
                for t, c in zip(h.get("time", []), h.get("temperature_2m", [])):
                    if c is None:
                        continue
                    if isinstance(t, str):                  # ISO v GMT
                        t = datetime.strptime(t, "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc).timestamp()
                    wo["h"][str(int(t))] = round(float(c), 1)
                    n += 1
                if not n:
                    raise ValueError(f"prázdná odpověď ({str(js)[:120]})")
                wo["t"], wo["err"] = ts, None
                break
            except Exception as e:
                errs.append(str(e)[:120])
        else:
            wo["err"] = " | ".join(errs)
            wo["t"] = ts - 3000                           # zkusit znovu za 10 min
            log(f"Venkovní teplota: {wo['err']}")
    wo["h"] = {k: v for k, v in wo["h"].items() if int(k) >= ts - 15 * 86400}
    return sorted((int(k), v) for k, v in wo["h"].items())


def _interp(ser, t):
    if not ser:
        return None
    if t <= ser[0][0]:
        return ser[0][1] if ser[0][0] - t <= 3 * 3600 else None
    if t >= ser[-1][0]:
        return ser[-1][1] if t - ser[-1][0] <= 3 * 3600 else None
    lo, hi = 0, len(ser) - 1
    while hi - lo > 1:
        m = (lo + hi) // 2
        if ser[m][0] <= t:
            lo = m
        else:
            hi = m
    (t0, a), (t1, b) = ser[lo], ser[hi]
    if t1 - t0 > 3 * 3600:
        return None
    return a + (b - a) * (t - t0) / (t1 - t0)


def _segments(R):
    """R = [(t, T)] seřazené → úseky chladnutí [(i_vrchol, i_konec)]."""
    segs, i, n = [], 0, len(R)
    while i < n - 1:
        s = i                                         # vrchol: dokud teplota roste, posouvat
        j = i + 1
        while j < n and R[j][1] >= R[s][1] and R[j][0] - R[j - 1][0] <= 4200:
            s = j
            j += 1
        mn = s
        j = s + 1
        while j < n and R[j][0] - R[j - 1][0] <= 4200 and R[j][1] <= R[mn][1] + 0.3:
            if R[j][1] < R[mn][1]:
                mn = j
            j += 1
        if mn > s:
            segs.append((s, mn, j >= n))              # True = ještě chladne (poslední data)
        i = max(mn, s + 1) if j < n else n
        if j < n and R[j][0] - R[j - 1][0] > 4200:    # mezera v datech
            i = j
    return segs


def _fit(R, s, e, tout, inwin=lambda t: True, why=None):
    """Úsek chladnutí → použitelné kousky bez větrání a bez první hodiny → [(k, ta, tb, Ta, Tb, To, h, okna)]."""
    t_peak = R[s][0]
    bad_until, wins, pieces, cur = 0, 0, [], []
    first = R[s][0]                                   # kdy se předchozí hodnota poprvé objevila
    for i in range(s, e + 1):
        t, T = R[i]
        if i > s and R[i][1] != R[i - 1][1]:
            prev_first, first = first, t
        else:
            prev_first = first
        # větrání: prudký pokles. Teploměr někdy chvíli nevysílá a do bodů se opakuje poslední hodnota –
        # pokles se proto měří od chvíle, kdy se předchozí hodnota poprvé objevila; hranice = 2× nejrychlejší běžné chladnutí
        drop = R[i - 1][1] - T if i > s else 0
        o_ = tout(t) if i > s else None
        lim_rate = max(2.5, 0.3 * (R[i - 1][1] - o_)) if o_ is not None else 2.5   # 2× nejrychlejší běžné chladnutí
        if i > s and drop >= 0.5 and t - R[i - 1][0] <= 900 and drop / max(t - prev_first, 600) * 3600 >= lim_rate:
            wins += 1
            bad_until = t + 3600
            if len(cur) >= 2:
                pieces.append(cur)
            cur = []
            continue
        if t < t_peak + 3600 or t < bad_until or not inwin(t):
            continue
        cur.append((t, T))
    if len(cur) >= 2:
        pieces.append(cur)
    out = []
    for pc in pieces:
        (ta, Ta), (tb, Tb) = pc[0], pc[-1]
        h = (tb - ta) / 3600
        if h < 3 or Ta - Tb < 0.8:
            if why is not None and h >= 1:
                why.append(f"{datetime.fromtimestamp(ta, _TZ).strftime('%d.%m. %H:%M')}: {int(h)}:{int(round(h % 1 * 60)):02d} h, pokles {Ta - Tb:.1f} °C – málo (aspoň 3 h a 0,8 °C)")
            continue
        integ, ok, outs = 0.0, True, []
        for (t0, T0), (t1, T1) in zip(pc, pc[1:]):
            o0, o1 = tout(t0), tout(t1)
            if o0 is None or o1 is None:
                ok = False
                break
            outs += [o0, o1]
            integ += ((T0 - o0) + (T1 - o1)) / 2 * (t1 - t0) / 3600
        if not ok or not outs or Ta - outs[0] < 4 or integ <= 0:
            if why is not None:
                why.append(f"{datetime.fromtimestamp(ta, _TZ).strftime('%d.%m. %H:%M')}: " + ("chybí venkovní teplota" if not ok or not outs else "malý rozdíl proti venku"))
            continue
        k_all = (Ta - Tb) / integ
        # 5.48: kamna po dotopení ještě dlouho hřejí → začátek noci chladne pomaleji, než odpovídá chatě. Rychlost
        # chladnutí chaty se proto bere z posledních 3 h noci (kamna už studená); celá noc jen pro srovnání.
        k = k_all
        late = [q for q in pc if q[0] >= tb - 3 * 3600]
        if h >= 4 and len(late) >= 4 and late[0][1] - late[-1][1] >= 0.3:
            il = 0.0
            for (t0, T0), (t1, T1) in zip(late, late[1:]):
                il += ((T0 - tout(t0)) + (T1 - tout(t1))) / 2 * (t1 - t0) / 3600
            if il > 0:
                k = (late[0][1] - late[-1][1]) / il
        if not 0.003 < k < 1.0 and why is not None:
            why.append(f"{datetime.fromtimestamp(ta, _TZ).strftime('%d.%m. %H:%M')}: nesmyslná rychlost {k:.3f}")
        if 0.003 < k < 1.0:
            out.append({"t0": t_peak, "ta": ta, "tb": tb, "T0": round(R[s][1], 1), "Ta": round(Ta, 1), "Tb": round(Tb, 1),
                        "To": round(sum(outs) / len(outs), 1), "k": round(k, 4), "k_all": round(k_all, 4),
                        "avg": round((Ta - Tb) / h, 2), "h": round(h, 1), "win": wins})
    return out


def _sim(T, t0, t1, k, tout):
    t = t0
    while t < t1:
        dt = min(600, t1 - t)
        o = tout(t)
        if o is None:
            return None
        T += -k * (T - o) * dt / 3600
        t += dt
    return T


def update(data, st, now, cfg, log=print):
    room = str(cfg.get("chladnuti_teplomer") or "Pokoj").strip()
    data.pop("cool", None)
    if not room:
        return
    ts = int(now.timestamp())
    R = []
    for p in data.get("points", []):
        th = p.get("th") or {}
        v = next((th[k] for k in th if str(k).strip(" ,;:.") == room), None)
        if v is not None and (not R or p["t"] > R[-1][0]):
            R.append((p["t"], float(v)))
    if len(R) < 6:
        return
    O = _outdoor(st, cfg, now, log)
    tout = lambda t: _interp(O, t)
    if st.get("cool_ver") != 4:                       # 5.46: učí se jen z noci (bez udržovacího topení) – přepočítat
        st["cool_ev"] = {}
        st["cool_ver"] = 4
    ev = st.setdefault("cool_ev", {})
    seen_live = set()
    why = []

    def _min(txt, dflt):
        try:
            a, b = (str(txt or dflt).split(":") + ["0"])[:2]
            return int(a) * 60 + int(b)
        except ValueError:
            a, b = dflt.split(":")
            return int(a) * 60 + int(b)
    w0, w1 = _min(cfg.get("chladnuti_noc_od"), "0:00"), _min(cfg.get("chladnuti_noc_do"), "7:00")

    def inwin(t):                                     # 5.46: jen noc, kdy se netopí (přes den se topí udržovacím topením)
        lt = datetime.fromtimestamp(t, now.tzinfo)
        m = lt.hour * 60 + lt.minute
        return w0 <= m < w1 if w0 <= w1 else (m >= w0 or m < w1)
    for s, e, live in _segments(R):
        for f in _fit(R, s, e, tout, inwin, why):
            key = str(f["ta"])
            # úsek, který ještě běží, se při dalším běhu přepočítá (jiný konec) – starý kus se stejným vrcholem pryč
            for k_ in [k_ for k_, x in ev.items() if x.get("t0") == f["t0"] and k_ != key and x.get("live")]:
                ev.pop(k_, None)
            f["live"] = 1 if live and ts - R[e][0] < 1800 else 0
            ev[key] = f
            if f["live"]:
                seen_live.add(key)
    for k_, x in list(ev.items()):
        if x.get("live") and k_ not in seen_live:
            x["live"] = 0                              # úsek mezitím skončil
    for k_ in sorted(ev, key=lambda z: ev[z]["ta"])[:-40]:
        ev.pop(k_, None)
    done = sorted((x for x in ev.values() if not x.get("live")), key=lambda x: x["ta"])
    ks = sorted(x["k"] for x in done[-10:])
    need = int(cfg.get("chladnuti_min_vecery") or 5)
    c = {"room": room, "n": len(done), "need": need,
         "ev": sorted(ev.values(), key=lambda x: x["ta"])[-8:],
         "out_now": None if tout(ts) is None else round(tout(ts), 1),
         "out": [[t, v] for t, v in O if ts - 8 * 86400 <= t <= ts + 24 * 3600]}      # 5.49: týden zpět pro graf nocí
    if R and ts - R[-1][0] < 1800:
        c["T_now"] = round(R[-1][1], 1)
        prev = [T for t, T in R if R[-1][0] - 3600 <= t < R[-1][0] - 1200]
        if prev:
            c["trend"] = round(R[-1][1] - sum(prev) / len(prev), 1)   # za poslední ~hodinu
    c["out_err"] = (st.get("wo") or {}).get("err")
    c["why"] = why[-6:]
    # 5.50: každá noc přímo z naměřených teplot (bez výpočtu modelu) – průměrný pokles v okně noci
    nights = []
    for dd in range(8, -1, -1):
        day = (now - timedelta(days=dd)).replace(hour=0, minute=0, second=0, microsecond=0)
        a = day + timedelta(minutes=w0) if w0 < w1 else day - timedelta(days=1) + timedelta(minutes=w0)
        b = day + timedelta(minutes=w1)
        ta_, tb_ = a.timestamp(), b.timestamp()
        if tb_ > ts:
            continue
        pts = [(t, T) for t, T in R if ta_ <= t <= tb_]
        if len(pts) < 6 or pts[0][0] - ta_ > 3600 or tb_ - pts[-1][0] > 3600:
            continue
        hrs = (pts[-1][0] - pts[0][0]) / 3600
        mx_rise = max(0.0, max(pts[i][1] - min(T for _, T in pts[:i + 1]) for i in range(len(pts))))
        os_ = [tout(t) for t, _ in pts[::6] if tout(t) is not None]
        nights.append({"ta": int(pts[0][0]), "tb": int(pts[-1][0]), "Ta": pts[0][1], "Tb": pts[-1][1],
                       "avg": round((pts[0][1] - pts[-1][1]) / hrs, 2) if hrs > 0 else None,
                       "To": round(sum(os_) / len(os_), 1) if os_ else None, "heat": 1 if mx_rise >= 0.5 else 0})
    c["nights"] = nights
    # 5.51: dokud se model nenaučí z úseků, hrubý odhad rychlosti přímo z nocí bez topení: k ≈ pokles/h ÷ (průměr uvnitř − venku)
    if not ks:
        kn = sorted(x["avg"] / ((x["Ta"] + x["Tb"]) / 2 - x["To"]) for x in nights
                    if not x["heat"] and x.get("avg") and x["avg"] > 0 and x.get("To") is not None and (x["Ta"] + x["Tb"]) / 2 - x["To"] > 3)
        if kn:
            k = kn[len(kn) // 2]
            c.update(k=round(k, 4), half_h=round(math.log(2) / k, 1), r10=round(k * 10, 2), k_src="noci", k_n=len(kn))
            if c.get("T_now") is not None and c.get("out_now") is not None:
                c["loss_now"] = round(k * (c["T_now"] - c["out_now"]), 2)
    c["win"] = [cfg.get("chladnuti_noc_od") or "0:00", cfg.get("chladnuti_noc_do") or "7:00"]
    for x in c["ev"]:
        x["r10"] = round(x["k"] * 10, 2)              # °C/h při rozdílu 10 °C proti venku
    if c.get("trend") is not None and c["trend"] < -0.05 and c.get("out_now") is not None and c["T_now"] - c["out_now"] > 2:
        dif = c["T_now"] - c["out_now"]                # 5.46: právě teď měřené chladnutí (za poslední hodinu)
        c["live"] = {"rate": round(-c["trend"], 2), "dif": round(dif, 1), "r10": round(-c["trend"] / dif * 10, 2)}
    if ks:
        k = ks[len(ks) // 2]
        c["k"] = k
        c["half_h"] = round(math.log(2) / k, 1)
        c["r10"] = round(k * 10, 2)
        if c.get("T_now") is not None and c.get("out_now") is not None:
            c["loss_now"] = round(k * (c["T_now"] - c["out_now"]), 2)
    if len(done) >= need and ks and c.get("T_now") is not None:
        k = c["k"]
        hh, mm = (str(cfg.get("chladnuti_rano") or "7:00").split(":") + ["0"])[:2]
        m = now.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
        if m <= now:
            m += timedelta(days=1)
        tm = int(m.timestamp())
        target = float(cfg.get("chladnuti_cil_C") or 21)
        a0, a1 = _sim(0.0, ts, tm, k, tout), _sim(1.0, ts, tm, k, tout)
        if a0 is not None and a1 is not None and a1 - a0 > 0.001:
            c.update(morning=tm, target=target, pred=round(a0 + (a1 - a0) * c["T_now"], 1),
                     need_T=round((target - a0) / (a1 - a0), 1))
    if ks or c.get("k"):
        # 5.156 (Petr): kolik °C mít v pokoji, když jdu spát (chladnuti_spat, 0:00), aby ráno (chladnuti_rano) bylo
        # chladnuti_cil_C – stejný model a předpověď venku, od spaní do rána se netopí (přiložení před spaním = rezerva)
        k = c["k"]
        hh, mm = (str(cfg.get("chladnuti_rano") or "7:00").split(":") + ["0"])[:2]
        bh, bm = (str(cfg.get("chladnuti_spat") or "0:00").split(":") + ["0"])[:2]
        bed = now.replace(hour=int(bh), minute=int(bm), second=0, microsecond=0)
        mor = now.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
        if mor <= now:
            mor += timedelta(days=1)
        while bed >= mor:
            bed -= timedelta(days=1)
        if bed < now - timedelta(hours=1):
            bed += timedelta(days=1)
            mor += timedelta(days=1) if mor <= bed else timedelta(0)
        target = float(cfg.get("chladnuti_cil_C") or 21)
        b0, b1 = _sim(0.0, bed.timestamp(), mor.timestamp(), k, tout), _sim(1.0, bed.timestamp(), mor.timestamp(), k, tout)
        if b0 is not None and b1 is not None and b1 - b0 > 0.001:
            c.update(bed=int(bed.timestamp()), bed_mor=int(mor.timestamp()), target=target,
                     need_bed=round((target - b0) / (b1 - b0), 1))
    data["cool"] = c


def curve(st, k, T0, t0, t1, step=600):
    """5.153: předpověď chladnutí od teď (T0) do t1 po 10 min – stejný model jako na ráno. [(t, T)] nebo None."""
    O = sorted((int(t), v) for t, v in ((st.get("wo") or {}).get("h") or {}).items())
    if not O or not k:
        return None
    out, T, t = [(int(t0), round(T0, 2))], float(T0), int(t0)
    while t < t1:
        dt = min(step, t1 - t)
        o = _interp(O, t)
        if o is None:
            return out if len(out) > 1 else None
        T += -k * (T - o) * dt / 3600
        t += dt
        out.append((t, round(T, 2)))
    return out
