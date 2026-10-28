"""5.125: „Jaká baterie“ – přehrání skutečné historie pro různé baterie.

Výroba: model záření → kWh na panel (pocasi.model_for – učí se jen ze dnů, kdy baterie nebyla brzy plná, takže
ukazuje, kolik by panely daly bez přiškrcení ve Floatu) × počet zapojených panelů ten den (panely.label_panels).
Spotřeba: obvyklá spotřeba chaty z historie – den i noc stejné jako ve výpočtech hlídače (energy_model / night_w),
Petr: „chata bere víceméně pořád stejně“. Den a noc podle východu a západu slunce.
Každá varianta: využitelná energie (Ah × napětí × hloubka vybití), účinnost nabíjení. Výsledek po měsících:
kolik nocí by baterie nestačila (chata by musela na River), kolik Wh by dodala River, kolik energie by se zahodilo
(baterie plná). Předpoklady jsou vypsané v data["bsim"]["pred"], ať jsou vidět na webu.
"""
from datetime import date as Date, datetime, timedelta

# název, Ah, jmenovité V, hloubka vybití, účinnost nabíjení, ztráta kapacity za rok
VARIANTS = [
    ("AGM 100 Ah", 100, 12.0, 0.5, 0.85, 0.15),
    ("AGM 200 Ah (nová, jako máš)", 200, 12.0, 0.5, 0.85, 0.15),
    ("LiFePO4 50 Ah", 50, 12.8, 0.9, 0.95, 0.02),
    ("LiFePO4 100 Ah", 100, 12.8, 0.9, 0.95, 0.02),
    ("LiFePO4 150 Ah", 150, 12.8, 0.9, 0.95, 0.02),
    ("LiFePO4 200 Ah", 200, 12.8, 0.9, 0.95, 0.02),
]


def simulate(days, usable_wh, eff):
    """days = [(klíč, výroba Wh do regulátoru, odběr přes den Wh DC, odběr v noci Wh DC)] chronologicky.
    Začíná plná. Vrací {měsíc: {n, short, river_wh, waste_wh}}."""
    soc, out = usable_wh, {}
    for k, prod, day_use, night_use in days:
        m = out.setdefault(k[:7], {"n": 0, "short": 0, "river_wh": 0.0, "waste_wh": 0.0})
        m["n"] += 1
        soc += prod * eff - day_use
        if soc > usable_wh:
            m["waste_wh"] += (soc - usable_wh) / eff
            soc = usable_wh
        short = False
        if soc < 0:                                # už přes den – zbytek dne z River
            m["river_wh"] += -soc
            short, soc = True, 0.0
        soc -= night_use
        if soc < 0:
            m["river_wh"] += -soc
            short, soc = True, 0.0
        m["short"] += short                        # dny (den + následující noc), kdy by baterie nestačila
    for m in out.values():
        m["river_wh"] = round(m["river_wh"])
        m["waste_wh"] = round(m["waste_wh"])
    return out


def update(data, st, now, cfg, sun_times, model_for, label_panels, night_w, day_w, cur_ah=None):
    """Jednou denně: data["bsim"] = {t, od, do, n, var: [{name, years: {0: {...}, 3: {...}}}], pred}."""
    if st.get("bsim_day") == now.strftime("%Y-%m-%d") and (data.get("bsim") or {}).get("nv") == len(VARIANTS):
        return
    st["bsim_day"] = now.strftime("%Y-%m-%d")
    wx = data.get("wx") or {}
    lab, _ = label_panels(data, cfg, now.date())
    idle = (cfg.get("menic_vlastni_W") or 6) + (cfg.get("desulfator_W") or 0)
    nw, dw = night_w, day_w
    cache, days = {}, []
    today = now.date()
    for k in sorted(wx):
        w = wx.get(k)
        if not w or k >= today.isoformat():
            continue
        d = Date.fromisoformat(k)
        m = model_for(data, cfg, sun_times, d, today, cache, lab)
        if not m:
            continue
        a, b, _ = m
        n_p = (lab or {}).get(k) or int(cfg.get("panely_pocet") or 1)
        prod = (a * w[1] + b * max(w[0] - w[1], 0)) * n_p * 1000          # Wh
        r, z = sun_times(cfg["sirka"], cfg["delka"], d)
        r2, _ = sun_times(cfg["sirka"], cfg["delka"], d + timedelta(days=1))
        if not (r and z and r2):
            continue
        day_h = (z - r).total_seconds() / 3600
        night_h = (r2 - z).total_seconds() / 3600
        days.append((k, prod, (dw / 0.88 + idle) * day_h, (nw / 0.88 + idle) * night_h))
    if not days:
        data["bsim"] = {"t": int(now.timestamp()), "n": 0}
        return
    var = []
    vs = list(VARIANTS)
    if cur_ah:      # současná baterie tak, jak se používá (z plné do alarmu 12,0 V ≈ 80 %) – pro srovnání se skutečností
        vs = [(f"Tvoje současná AGM (změřeno ~{round(cur_ah)} Ah)", cur_ah, 12.0, 0.8, 0.85, 0.0)] + vs
    for name, ah, v, dod, eff, loss in vs:
        yrs = {}
        for y in (0, 3):
            usable = ah * v * dod * (1 - loss) ** y
            res = simulate(days, usable, eff)
            yrs[str(y)] = {"usable_wh": round(usable), "months": res,
                           "short": sum(x["short"] for x in res.values()),
                           "river_wh": sum(x["river_wh"] for x in res.values()),
                           "waste_wh": sum(x["waste_wh"] for x in res.values())}
        var.append({"name": name, "ah": ah, "years": yrs})
    data["bsim"] = {"t": int(now.timestamp()), "nv": len(VARIANTS), "od": days[0][0], "do": days[-1][0], "n": len(days), "var": var,
                    "pred": {"night_w": round(nw), "day_w": round(dw), "idle_w": idle,
                             "var": [{"name": n, "dod": d, "eff": e, "loss": l} for n, _, _, d, e, l in vs]}}
