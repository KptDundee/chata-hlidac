"""Kolik panelů zapojit (1 v létě, 2 v zimě) a hlídání nabíjecího proudu kvůli pojistce mezi regulátorem a baterií.

Učení: každý den se uloží nejvyšší nabíjecí proud mimo Float (day["pa"]). Vydělený počtem zapojených panelů
a přepočtený na „sílu slunce“ v poledne za jasna (podle výšky slunce) dává, kolik proudu dává jeden panel.
Pro každou roční dobu se bere NEJHORŠÍ naměřený případ (vč. špiček, kdy slunce vykoukne zpoza mraku) –
pojistku pálí právě ty. Počet panelů v historii se pozná sám: se dvěma panely je proud zhruba dvojnásobný.
"""
import math
from datetime import date as Date, datetime, timedelta


def ghi_clear_noon(d, lat):
    """Globální záření za jasna v poledne (W/m², model Haurwitz) – jen jako měřítko síly slunce v roce."""
    doy = d.timetuple().tm_yday
    decl = 23.44 * math.sin(2 * math.pi * (284 + doy) / 365)
    elev = 90 - lat + decl
    cz = math.sin(math.radians(max(elev, 1)))
    return 1098 * cz * math.exp(-0.057 / cz)


def _doy_dist(a, b):
    x = abs(a.timetuple().tm_yday - b.timetuple().tm_yday)
    return min(x, 365 - x)


def label_panels(data, cfg, today):
    """Počet panelů pro každý den historie.

    Od první známé změny v nastavení platí nastavení. Starší historie: Petr přepojuje dvakrát do roka
    (na podzim přidá druhý panel, na jaře ho odpojí), takže se v každém roce hledá skok normalizovaného
    proudu nahoru (srpen–říjen) a dolů (únor–květen). Když skok není jasný, platí zvyk: 1. 9. a 20. 3.
    """
    lat = cfg["sirka"]
    hist = sorted((data.get("np_hist") or []), key=lambda x: x[0])     # [(YYYY-MM-DD od kdy, n)]
    first_known = hist[0][0] if hist else today.isoformat()
    days = data.get("days", {})
    r = {}
    for k, d in days.items():
        if k < first_known and d.get("pa") and d["pa"] >= 2:
            r[k] = d["pa"] / ghi_clear_noon(Date.fromisoformat(k), lat)

    def env(a, b):                              # 85. percentil (≈ jasné dny) v rozmezí [a, b)
        v = sorted(x for k, x in r.items() if a <= k < b)
        return v[int(len(v) * 0.85)] if len(v) >= 6 else None

    def best_switch(y, m0, m1, up):
        best, bd = 0.0, None
        d = Date(y, m0, 1)
        while d < Date(y, m1, 1):
            k = d.isoformat()
            e1, e2 = env((d - timedelta(days=21)).isoformat(), k), env(k, (d + timedelta(days=21)).isoformat())
            if e1 and e2:
                j = math.log(e2 / e1) if up else math.log(e1 / e2)
                if j > best:
                    best, bd = j, k
            d += timedelta(days=2)
        return bd if best > math.log(1.4) else None

    years = sorted({int(k[:4]) for k in days})
    switches = []                               # (od kdy, n)
    found = 0
    for y in years:
        s_ = best_switch(y, 2, 6, False)
        found += bool(s_)
        switches.append((s_ or f"{y}-03-20", 1))
        a_ = best_switch(y, 8, 11, True)
        found += bool(a_)
        switches.append((a_ or f"{y}-09-01", 2))
    switches.sort()
    lab = {}
    for k in days:
        if k >= first_known:
            lab[k] = next((x[1] for x in reversed(hist) if x[0] <= k), hist[0][1] if hist else 1)
        else:
            prev = [n for d0, n in switches if d0 <= k]
            lab[k] = prev[-1] if prev else (2 if int(k[5:7]) in (9, 10, 11, 12, 1, 2) or (k[5:7] == "03" and int(k[8:10]) < 20) else 1)
    return lab, found


def peak_per_panel(data, cfg, target, lab):
    """Nejhorší (nejvyšší) proud na 1 panel pro roční dobu `target` – z historie ± 15 dní, přepočteno na sílu slunce."""
    lat = cfg["sirka"]
    g_t = ghi_clear_noon(target, lat)
    vals = []
    for k, d in data.get("days", {}).items():
        if not d.get("pa") or d["pa"] < 2:
            continue
        dd = Date.fromisoformat(k)
        if _doy_dist(dd, target) > 15:
            continue
        vals.append(d["pa"] / lab.get(k, 1) * g_t / ghi_clear_noon(dd, lat))
    if len(vals) >= 4:
        vals.sort()
        return vals[-1], "měření", len(vals)
    # bez dat: odhad z výkonu panelu (410 Wp, ztráty ~20 %, 13,5 V) a síly slunce
    wp = cfg.get("panel_Wp") or 410
    return wp * 0.8 / 13.5 * min(1.15, g_t / 850), "odhad", 0


def plan(data, st, cfg, now, preds_kwh_1panel, need_kwh, mode):
    """Doporučení kolik panelů zapojit + výhled špičkového proudu. preds_kwh_1panel: [(den, kWh na 1 panel)]."""
    today = now.date()
    lab, thr = label_panels(data, cfg, today)
    n_now = int(cfg.get("panely_pocet") or 1)
    fuse = cfg.get("pojistka_A") or 30
    lim = fuse * (cfg.get("pojistka_rezerva") or 0.85)
    curve = []
    for i in range(0, 181, 5):
        d = today + timedelta(days=i)
        p1, src, n = peak_per_panel(data, cfg, d, lab)
        curve.append({"d": d.isoformat(), "p1": round(p1, 1), "src": src, "n": n})
    p1_now = curve[0]["p1"]
    res = {"n": n_now, "fuse": fuse, "lim": round(lim, 1), "peak_now": round(p1_now * n_now, 1),
           "peak1": round(p1_now, 1), "peak2": round(p1_now * 2, 1), "src": curve[0]["src"],
           "curve": [{"d": c["d"], "p2": round(c["p1"] * 2, 1), "p1": c["p1"]} for c in curve[::3]],
           "found": thr, "rec": None, "msg": None}
    # první den, kdy jsou 2 panely bezpečné natrvalo (do konce zimy), a kdy přestanou být
    safe_from = None
    for i, c in enumerate(curve):
        ahead = curve[i:i + 18]
        if len(ahead) >= 6 and all(x["p1"] * 2 <= lim for x in ahead):   # bezpečné aspoň ~90 dní dopředu
            safe_from = c["d"]
            break
    unsafe_at = next((c["d"] for c in curve if c["p1"] * 2 > lim and c["src"] == "měření"), None)
    res["safe_from"], res["unsafe_at"] = safe_from, unsafe_at
    if curve[0]["src"] != "měření":            # bez naměřených proudů pro tuhle roční dobu neradit (jen odhad)
        return res
    if n_now == 1:
        short = need_kwh and preds_kwh_1panel and \
            sum(k for _, k in preds_kwh_1panel[1:6]) / max(1, len(preds_kwh_1panel[1:6])) < need_kwh * 0.9
        winterish = now.month in (9, 10, 11, 12, 1, 2) or mode == "zima"
        if short and winterish:
            if safe_from and safe_from <= today.isoformat():
                res["rec"] = "add"
                res["msg"] = (f"Jeden panel už nestačí (příští dny ~{sum(k for _, k in preds_kwh_1panel[1:6]) / max(1, len(preds_kwh_1panel[1:6])):.2f} kWh/den, "
                              f"chata potřebuje ~{need_kwh:.2f}). Druhý panel je už bezpečný: za jasného dne max ~{p1_now * 2:.0f} A (pojistka {fuse:.0f} A).")
            else:
                res["rec"] = "wait"
                res["msg"] = (f"Jeden panel už nestačí, ale se dvěma by za jasného dne teklo až ~{p1_now * 2:.0f} A (pojistka {fuse:.0f} A). "
                              + (f"Druhý panel bude bezpečný zhruba od {fmt_d(safe_from)}" if safe_from else "Zatím počkej."))
    else:
        if unsafe_at and unsafe_at <= (today + timedelta(days=14)).isoformat():
            res["rec"] = "remove"
            top = max(c['p1'] for c in curve[:4]) * 2
            res["msg"] = (f"Se dvěma panely už teď může za jasného dne téct až ~{top:.0f} A (pojistka {fuse:.0f} A). Zvaž odpojení druhého panelu."
                          if unsafe_at <= today.isoformat() else
                          f"Slunce sílí: se dvěma panely může za jasného dne téct až ~{top:.0f} A (pojistka {fuse:.0f} A). "
                          f"Odpoj druhý panel nejpozději do {fmt_d(unsafe_at)}")
    return res


def fmt_d(k):
    d = Date.fromisoformat(k)
    return f"{d.day}. {d.month}."
