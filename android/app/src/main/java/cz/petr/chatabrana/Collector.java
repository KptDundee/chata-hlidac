package cz.petr.chatabrana;

import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.BatteryManager;
import android.os.SystemClock;
import android.util.Base64;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;

/** Jeden cyklus: posbírá měnič + zásuvky + baterii telefonu a pošle to do ntfy. */
public final class Collector {
    private final Context ctx;
    private final BleListener ble;
    private final Map<String, TapoKlap> tapo = new HashMap<>();
    private final Map<String, String> names = new HashMap<>();
    private final Map<String, String> models = new HashMap<>();
    private final Map<String, String> lastState = new HashMap<>();   // ať se do záznamu nepíše pořád dokola totéž
    // rychlé hlídání zásuvek, které jsou většinu času bez proudu (např. za generátorem)
    private final java.util.Set<String> offIps = new java.util.HashSet<>();      // při posledním čtení nedostupné
    private final Map<String, Long> onSince = new HashMap<>();                    // IP → kdy se objevila
    private final Map<String, Long> goneAt = new HashMap<>();                     // IP → kdy zmizela
    private final Map<String, JSONObject> lastGood = new HashMap<>();             // IP → poslední úspěšné čtení

    static final String GEN_PLUG = "7";                 // číslo zásuvky generátoru (jako zasuvka_generator v nastavení hlídače)

    public Collector(Context ctx, BleListener ble) {
        this.ctx = ctx.getApplicationContext();
        this.ble = ble;
    }

    /** @return krátký popis výsledku do notifikace */
    public String runOnce() { return runOnce(true); }

    /** @param dispatch po odeslání spustit hlídače na GitHubu (když je zadaný token) */
    public String runOnce(boolean dispatch) {
        try {
            JSONObject o = new JSONObject();
            o.put("ver", 1);
            o.put("ts", System.currentTimeMillis() / 1000);     // kdy se měřilo (zpráva může odejít později z fronty)
            StringBuilder sum = new StringBuilder();

            // 1) měnič Victron (Bluetooth)
            if (ble.samples() == 0) ble.burst(20_000);   // trvalý poslech nic nechytil → 20 s intenzivně (jako do 1.3.6)
            if (ble.samples() == 0) {                    // ani tak nic → zkusit bez filtru (jako Test Bluetooth) a zapsat proč
                android.os.PowerManager pm = ctx.getSystemService(android.os.PowerManager.class);
                String r = ble.burstOpen(15_000);
                boolean bg = ctx.checkSelfPermission(android.Manifest.permission.ACCESS_BACKGROUND_LOCATION) == android.content.pm.PackageManager.PERMISSION_GRANTED;
                Prefs.log(ctx, "Victron – záložní hledání (" + (pm != null && pm.isInteractive() ? "displej svítí" : "displej zhasnutý")
                        + ", poloha " + (bg ? "vždy" : "jen při používání") + "): " + r);
            }
            BleListener.Snapshot s = ble.takeSnapshot();
            // 1.5: teploměry Xiaomi (poslední hodnoty mladší než hodina)
            try {
                JSONArray th = new JSONArray();
                for (BleListener.Thermo t : ble.thermo()) {
                    // 1.7.7: posílat i teploměry bez dat – s diagnostikou (zachyceno / přečteno), ať je vidět proč
                    boolean has = !(t.ageSec < 0 || t.ageSec > 3600 || (t.t == null && t.h == null));
                    JSONObject x = new JSONObject().put("n", t.name).put("sn", t.seen).put("ok", t.ok);
                    if (!has) { th.put(x); continue; }
                    x.put("age", t.ageSec);
                    if (t.t != null) x.put("t", t.t);
                    if (t.h != null) x.put("h", t.h);
                    if (t.b != null) x.put("b", t.b);
                    th.put(x);
                }
                if (th.length() > 0) o.put("th", th);
            } catch (Exception ignored) { }
            if (s.avgVa != null) {
                o.put("w", round(s.avgVa, 1));
                o.put("max", s.maxVa);
                sum.append(String.format(Locale.US, "měnič %.0f W", s.avgVa));
            } else if (s.last != null && s.last.acVa != null && s.ageSec >= 0 && s.ageSec < 1800) {
                // tentokrát nic nechytil, ale poslední hodnota je mladší než 30 min → poslat ji (označenou stářím)
                o.put("w", s.last.acVa);
                o.put("age", s.ageSec);
                sum.append(String.format(Locale.US, "měnič %d W (před %d min)", s.last.acVa, s.ageSec / 60));
            } else {
                o.put("w", -1);
                sum.append("měnič: ").append(s.error != null ? s.error : "žádná data");
            }
            if (s.last != null && s.ageSec >= 0 && s.ageSec < 1800) {
                if (s.last.batteryV != null) o.put("v", s.last.batteryV);
                if (s.last.acVa != null) o.put("lw", s.last.acVa);   // odběr ve stejném okamžiku jako napětí v
                o.put("st", s.last.stateName());
                o.put("al", s.last.alarmName());
            }
            o.put("n", s.samples);

            // 2) zásuvky Tapo (místní Wi-Fi)
            JSONArray plugs = new JSONArray();
            String email = Prefs.s(ctx, Prefs.TAPO_EMAIL), pass = Prefs.s(ctx, Prefs.TAPO_PASSWORD);
            int ok = 0, total = 0, off = 0;
            if (!email.isEmpty()) applyCommands(email, pass);
            if (!email.isEmpty()) {
                Map<String, String> map = plugMap(email, pass);            // číslo zásuvky → IP (hledá se v síti)
                boolean missing = false;
                JSONArray pdown = null;                                      // 1.9.16: výpadky obnovené prohledáním sítě
                Map<String, String> idIp = new HashMap<>();
                // 1.7.4: dva průchody – když některá známá zásuvka na své adrese neodpovídá (River / generátor /
                // nabíjení se zapnou a dostanou novou IP), hned v tomtéž měření se prohledá síť (jen nové adresy,
                // podle čísla ve jméně) a zásuvky se přečtou znovu na nových adresách
                for (int pass_ = 0; pass_ < 2; pass_++) {
                if (pass_ == 1) {
                    if (!missing || map.isEmpty()) break;
                    // 1.9.15: důležitá zásuvka (seznam od hlídače) neodpovídá → hned celé prohledání sítě (nejvýš 1× za 5 min).
                    // 28. 10. se (1), .150 a .193 třikrát vrátily přesně po celém prohledání, samy ne.
                    java.util.Set<String> must = new java.util.HashSet<>(java.util.Arrays.asList(Prefs.get(ctx).getString("stale_ids", "").split(",")));
                    boolean mustDown = false;
                    for (int k = 0; k < plugs.length(); k++) {
                        JSONObject p0 = plugs.optJSONObject(k);
                        if (p0 != null && p0.has("off") && must.contains(p0.optString("ip"))) mustDown = true;
                    }
                    if (mustDown && System.currentTimeMillis() - Prefs.get(ctx).getLong("tapo_scan_t", 0) > 5 * 60_000L) {
                        Prefs.log(ctx, "Důležitá zásuvka neodpovídá – hned prohledám celou síť");
                        pdown = new JSONArray();                             // co neodpovídalo (i světla) – hlídač zapíše do Deníku
                        for (int k = 0; k < plugs.length(); k++) {
                            JSONObject p0 = plugs.optJSONObject(k);
                            if (p0 == null || !p0.has("off") || !p0.optString("ow").startsWith("spojení vypršelo")) continue;
                            try { pdown.put(new JSONObject().put("ip", p0.optString("ip")).put("n", p0.optString("n", "")).put("ow", p0.optString("ow"))); } catch (Exception ignored) { }
                        }
                        Prefs.get(ctx).edit().putBoolean("tapo_force", true).apply();
                        Map<String, String> m2 = plugMap(email, pass);
                        map.clear(); map.putAll(m2);
                    } else {
                        java.util.Set<String> okIps = new java.util.HashSet<>();
                        for (String ip0 : map.values()) if (!offIps.contains(ip0)) okIps.add(ip0);
                        if (!remap(email, pass, map, okIps)) break;              // nic se nepřestěhovalo
                    }
                    plugs = new JSONArray(); ok = 0; total = 0; off = 0; missing = false; idIp.clear();
                }
                java.util.LinkedHashSet<String> ipsAll = new java.util.LinkedHashSet<>(map.values());
                if (map.isEmpty()) ipsAll.addAll(Prefs.tapoIps(ctx));       // ruční adresy jen když hledání nic nenašlo
                for (String ip : ipsAll) {
                    total++;
                    JSONObject p = readPlug(ip, email, pass);
                    if (p == null) continue;
                    String octet = ip.substring(ip.lastIndexOf('.') + 1), id = null;
                    String byMap = null;
                    for (Map.Entry<String, String> en : map.entrySet()) if (en.getValue().equals(ip)) byMap = en.getKey();
                    id = TapoScan.idFromName(names.get(ip));                // rozhoduje jméno přečtené právě teď
                    if (id != null && byMap != null && !id.equals(byMap)) {   // adresy se přeházely → najít zásuvky znovu
                        Prefs.log(ctx, "Zásuvka na ." + octet + " je teď (" + id + "), ne (" + byMap + ") – hledám znovu");
                        Prefs.get(ctx).edit().putBoolean("tapo_rescan", true).apply();
                    }
                    if (id == null) id = byMap;
                    if (id == null) id = octet;
                    p.put("ip", id);                                         // hlídač zásuvky rozlišuje podle čísla
                    idIp.put(id, ip);
                    if (!id.equals(octet)) p.put("a", octet);
                    plugs.put(p);
                    if (p.has("off")) {
                        off++; missing |= map.containsValue(ip);
                        // poslední počítadlo před výpadkem proudu a čas zmizení posílat ještě 40 min (hlídač běží po 10 min)
                        Long g = goneAt.get(ip);
                        if (g == null && onSince.containsKey(ip)) { g = System.currentTimeMillis(); goneAt.put(ip, g); }
                        if (g != null && System.currentTimeMillis() - g < 40 * 60_000L) {
                            p.put("gone", g / 1000);
                            JSONObject lg = lastGood.get(ip);
                            if (lg != null && lg.has("wh")) p.put("wh", lg.getInt("wh"));
                        } else { goneAt.remove(ip); lastGood.remove(ip); }
                        onSince.remove(ip);
                        offIps.add(ip);
                    } else if (!p.has("err")) {
                        ok++;
                        if (offIps.remove(ip) && !onSince.containsKey(ip)) onSince.put(ip, System.currentTimeMillis());
                        goneAt.remove(ip);
                        if (onSince.containsKey(ip)) { p.put("since", onSince.get(ip) / 1000); lastGood.put(ip, p); }
                    }
                }
                }                                                            // konec průchodů (1.7.4)
                if (ok == 0 && total > 0) Prefs.get(ctx).edit().putBoolean("tapo_rescan", true).apply();
                // 1.9.14: zásuvka, která má být vidět (seznam od hlídače), nejde aspoň 10 min → při dalším měření celé
                // prohledání sítě (nejvýš 1× za 30 min). 28. 10. se zásuvka (1) ozvala hned po celém prohledání.
                try {
                    android.content.SharedPreferences sp2 = Prefs.get(ctx);
                    java.util.Set<String> must = new java.util.HashSet<>(java.util.Arrays.asList(sp2.getString("stale_ids", "").split(",")));
                    long nowMs = System.currentTimeMillis();
                    String bad = null;
                    for (int k = 0; k < plugs.length(); k++) {
                        JSONObject p = plugs.optJSONObject(k);
                        if (p == null || !must.contains(p.optString("ip"))) continue;
                        String id = p.optString("ip");
                        if (p.has("off") || p.has("err")) {
                            if (!mustOff.containsKey(id)) mustOff.put(id, nowMs);
                            if (nowMs - mustOff.get(id) >= 10 * 60_000L) bad = id;
                        } else mustOff.remove(id);
                    }
                    for (String id : must) {                                   // v seznamu, ale vůbec nepřečtená
                        boolean seen = false;
                        for (int k = 0; k < plugs.length(); k++) { JSONObject p = plugs.optJSONObject(k); if (p != null && id.equals(p.optString("ip"))) seen = true; }
                        if (!seen && !id.isEmpty()) { if (!mustOff.containsKey(id)) mustOff.put(id, nowMs); if (nowMs - mustOff.get(id) >= 10 * 60_000L) bad = id; }
                    }
                    if (bad != null && nowMs - sp2.getLong("tapo_scan_t", 0) > 30 * 60_000L && !sp2.getBoolean("tapo_force", false)) {
                        sp2.edit().putBoolean("tapo_force", true).apply();
                        Prefs.log(ctx, "Zásuvka (" + bad + ") nejde 10 min – příště prohledám celou síť");
                    }
                } catch (Exception ignored) { }
                // 1.7.3: generátor – dokud jeho zásuvka bere proud, měřit a posílat každé 2 min (hlídač hned řídí
                // nabíjení River)
                boolean genOn = false;
                for (int k = 0; k < plugs.length(); k++) {
                    JSONObject p = plugs.optJSONObject(k);
                    if (p == null || !GEN_PLUG.equals(p.optString("ip"))) continue;
                    if (!p.has("off") && !p.has("err") && p.optDouble("w", 0) > 5) genOn = true;
                }
                if (genOn) Prefs.get(ctx).edit().putLong("fast_until", System.currentTimeMillis() + 5 * 60_000L).apply();
                // historie ze zásuvky (hodinová energie za 7 dní): jednou denně a hned, když se zásuvka znovu objeví
                sendPlugHistories(email, pass, plugs, idIp);
                if (plugs.length() > 0) o.put("tp", plugs);
                if (pdown != null && pdown.length() > 0) {                   // 1.9.16: vrátily se po prohledání?
                    for (int k = 0; k < pdown.length(); k++) {
                        JSONObject d0 = pdown.optJSONObject(k);
                        boolean back = false;
                        for (int q = 0; q < plugs.length(); q++) {
                            JSONObject p1 = plugs.optJSONObject(q);
                            if (p1 != null && p1.optString("ip").equals(d0.optString("ip")) && !p1.has("off") && !p1.has("err")) back = true;
                        }
                        d0.put("back", back);
                    }
                    o.put("pdown", pdown);
                }
                sum.append(", zásuvky ").append(ok).append('/').append(total);
                if (off > 0) sum.append(" (").append(off).append(" vypnuté)");
            }

            // 2b) 1.9.17: hodinovou historii „zásuvky za měničem“ (hledanou podle jména – „220“ sedělo i na River) už neposílá;
            //     hlídač ji bere z historie každé zásuvky podle jejího čísla (<topic>-tp-hist)

            // 3) baterie telefonu
            Intent b = ctx.registerReceiver(null, new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
            if (b != null) {
                int lvl = b.getIntExtra(BatteryManager.EXTRA_LEVEL, -1);
                int scale = b.getIntExtra(BatteryManager.EXTRA_SCALE, 100);
                int plugged = b.getIntExtra(BatteryManager.EXTRA_PLUGGED, 0);
                int temp = b.getIntExtra(BatteryManager.EXTRA_TEMPERATURE, Integer.MIN_VALUE);
                JSONObject ph = new JSONObject();
                int pct = lvl >= 0 ? Math.round(100f * lvl / scale) : -1;
                ph.put("b", pct);
                ph.put("c", plugged != 0 ? 1 : 0);
                if (temp != Integer.MIN_VALUE) ph.put("t", temp / 10.0);
                o.put("ph", ph);
                sum.append(", telefon ").append(pct).append(" %");
                // 1.6: řízení nabíjení Flipu zásuvkou (povolení od hlídače + bezpečnost podle teploty, místně)
                if (!email.isEmpty() && pct >= 0) {
                    try { flipCharge(email, pass, pct, plugged != 0, temp != Integer.MIN_VALUE ? temp / 10.0 : Double.NaN, plugs, o); }
                    catch (Exception e) { Prefs.log(ctx, "Nabíjení Flipu: " + e.getMessage()); }
                }
            }

            // 1.7: baterie routeru M7000 (jen čtení)
            String rpass = Prefs.get(ctx).getString(Prefs.ROUTER_PASS, "");
            // 1.8: nejvýš 1× za 9 min (router dovolí jen jedno přihlášení správce; při generátoru měří Flip po 2 min)
            boolean rtDue = System.currentTimeMillis() - Prefs.get(ctx).getLong("rt_t", 0) > 9 * 60_000L;
            if (!rpass.isEmpty() && !rtDue) {
                try { String lr = Prefs.get(ctx).getString("rt_last", ""); if (!lr.isEmpty()) o.put("rt", new JSONObject(lr)); } catch (Exception ignored) { }
            } else if (!rpass.isEmpty()) {
                Prefs.get(ctx).edit().putLong("rt_t", System.currentTimeMillis()).apply();
                RouterM7000.Result rr = RouterM7000.read(gateway(), rpass);
                JSONObject rt = new JSONObject();
                if (rr.pct != null) { rt.put("b", rr.pct); if (rr.charging != null) rt.put("c", rr.charging ? 1 : 0); sum.append(", router ").append(rr.pct).append(" %");
                    Prefs.get(ctx).edit().putInt("rt_good_b", rr.pct).putLong("rt_good_t", System.currentTimeMillis()).apply(); }   // 1.9.9
                if (rr.net != null) rt.put("net", rr.net);                 // 1.9.3: data přenesená routerem
                if (rr.err != null) {
                    rt.put("err", rr.err);
                    if (!rr.err.equals(Prefs.get(ctx).getString("rt_err", ""))) Prefs.log(ctx, "Router: " + rr.err);
                }
                Prefs.get(ctx).edit().putString("rt_err", rr.err == null ? "" : rr.err).putString("rt_last", rt.toString()).apply();
                o.put("rt", rt);
            }
            // 1.9: řízení nabíjení routeru zásuvkou (5)
            if (!email.isEmpty() && !rpass.isEmpty()) {
                try { routerCharge(email, pass, plugs, o); }
                catch (Exception e) { Prefs.log(ctx, "Nabíjení routeru: " + e.getMessage()); }
            }
            if (o.has("th")) sum.append(", teploměry ").append(o.getJSONArray("th").length());
            o.put("av", appVersion());
            // 1.9.11: první měření po plánovaném restartu → hlídač pošle zprávu, jestli je všechno v pořádku
            long rstT = Prefs.get(ctx).getLong("rst_t", 0);
            if (rstT > 0 && System.currentTimeMillis() - rstT < 30 * 60_000L && !Prefs.get(ctx).getBoolean("rst_sent", true)) {
                JSONObject rs = new JSONObject().put("t", rstT / 1000).put("ble_ok", s.error == null || s.samples > 0 ? 1 : 0);
                if (s.error != null && s.samples == 0) rs.put("ble_err", s.error);
                if (o.has("tp")) { int rOk = 0, rTot = 0; JSONArray rTp = o.getJSONArray("tp");
                    for (int ri = 0; ri < rTp.length(); ri++) { JSONObject rp = rTp.getJSONObject(ri); rTot++; if (!rp.has("off") && !rp.has("err")) rOk++; }
                    rs.put("plugs_ok", rOk).put("plugs", rTot); }
                o.put("rst", rs);
                Prefs.get(ctx).edit().putBoolean("rst_sent", true).apply();
            }
            // 1.9.3: kolik dat přenesla aplikace Brána a celý telefon (bajty od zapnutí telefonu; hlídač počítá přírůstky)
            try {
                int uid = android.os.Process.myUid();
                long ar = android.net.TrafficStats.getUidRxBytes(uid), at = android.net.TrafficStats.getUidTxBytes(uid);
                long pr = android.net.TrafficStats.getTotalRxBytes(), pt = android.net.TrafficStats.getTotalTxBytes();
                long mr = android.net.TrafficStats.getMobileRxBytes(), mt = android.net.TrafficStats.getMobileTxBytes();
                JSONObject nb = new JSONObject().put("up", android.os.SystemClock.elapsedRealtime() / 1000);
                if (ar >= 0 && at >= 0) nb.put("app", ar + at);
                if (pr >= 0 && pt >= 0) nb.put("ph", pr + pt);
                if (mr >= 0 && mt >= 0) nb.put("mob", mr + mt);
                o.put("nb", nb);
            } catch (Exception ignored) { }
            // je Flip na Wi‑Fi? (po restartu routeru se umí přepnout na mobilní data a pak nevidí zásuvky)
            try {
                android.net.ConnectivityManager cm = ctx.getSystemService(android.net.ConnectivityManager.class);
                boolean wifi = false;
                for (android.net.Network n : cm.getAllNetworks()) {
                    android.net.NetworkCapabilities nc = cm.getNetworkCapabilities(n);
                    if (nc != null && nc.hasTransport(android.net.NetworkCapabilities.TRANSPORT_WIFI)) wifi = true;
                }
                o.put("wifi", wifi ? 1 : 0);
                if (!wifi) sum.append(", BEZ Wi‑Fi");
            } catch (Exception ignored) { }

            // 4) odeslat
            String topic = Prefs.s(ctx, Prefs.NTFY_TOPIC);
            if (topic.isEmpty()) return "Chybí ntfy téma v nastavení";
            String url = "https://ntfy.sh/" + topic + "-menic";
            // 1.4: data jdou rovnou na GitHub se spuštěním hlídače (ntfy.sh odmítal zprávy z chaty – HTTP 429).
            // ntfy jen jako záloha, když GitHub nejde (bez tokenu, bez internetu).
            int gh = sendGitHub(o.toString());
            if (gh >= 0) {
                Prefs.get(ctx).edit().putLong(Prefs.LAST_SENT, System.currentTimeMillis()).apply();
                Prefs.log(ctx, "Odesláno (GitHub): " + sum + (gh > 1 ? " (+ " + (gh - 1) + " starších)" : ""));
                return sum.toString() + " · GitHub";
            }
            int sentOld = flushOutbox(url);
            try {
                post(url, o.toString());
            } catch (Exception e) {
                SystemClock.sleep(20_000);                       // krátký výpadek internetu (router, 4G) → jednou znovu
                try { post(url, o.toString()); }
                catch (Exception e2) {
                    int n = queue(o.toString());
                    Prefs.log(ctx, "Neodesláno (" + e2.getMessage() + ") – ve frontě " + n + ", pošle se příště");
                    return "Neodesláno – ve frontě " + n + " · " + sum;
                }
            }
            Prefs.get(ctx).edit().putLong(Prefs.LAST_SENT, System.currentTimeMillis()).apply();
            Prefs.log(ctx, "Odesláno: " + sum + (sentOld > 0 ? " (+ " + sentOld + " z fronty)" : ""));
            if (dispatch) dispatchWatcher();
            return sum.toString() + (sentOld > 0 ? " · +" + sentOld + " z fronty" : "");
        } catch (Exception e) {
            String m = "Chyba: " + e.getMessage();
            Prefs.log(ctx, m);
            return m;
        }
    }

    /**
     * 1.7.4: rychlé dohledání přestěhovaných zásuvek – prohledá síť, přihlásí se jen na adresy, které teď nepatří
     * žádné fungující zásuvce, a podle čísla ve jméně („(7) …“) přepíše mapu. Vrací true, když se něco přestěhovalo.
     */
    private final Map<String, Long> mustOff = new HashMap<>();          // 1.9.14: od kdy nejde zásuvka, která má být vidět

    private boolean remap(String email, String pass, Map<String, String> map, java.util.Set<String> okIps) {
        Map<String, JSONObject> found = TapoScan.scan(ctx, email, pass, true, okIps);
        if (found.isEmpty()) return false;
        android.content.SharedPreferences sp = Prefs.get(ctx);
        JSONObject j;
        try { j = new JSONObject(sp.getString("tapo_map", "{}")); } catch (Exception e) { j = new JSONObject(); }
        StringBuilder sb = new StringBuilder();
        for (Map.Entry<String, JSONObject> en : found.entrySet()) {
            String id = en.getKey(), ip = en.getValue().optString("ip"), old = map.get(id);
            if (ip.equals(old)) continue;
            if (!en.getValue().optBoolean("named")) continue;         // zásuvka bez čísla ve jméně – podle adresy, nechat na plné hledání
            try { j.put(id, en.getValue()); } catch (Exception ignored) { }
            map.put(id, ip);
            names.remove(ip);
            if (old != null) {                                        // přenést stav „vypnutá od…“ na novou adresu
                if (offIps.remove(old)) offIps.add(ip);
                Long g = goneAt.remove(old); if (g != null) goneAt.put(ip, g);
                JSONObject lg = lastGood.remove(old); if (lg != null) lastGood.put(ip, lg);
                tapo.remove(old);
            }
            sb.append(sb.length() > 0 ? ", " : "").append("(").append(id).append(") → .").append(ip.substring(ip.lastIndexOf('.') + 1));
        }
        if (sb.length() == 0) return false;
        sp.edit().putString("tapo_map", j.toString()).apply();
        Prefs.log(ctx, "Zásuvky na nové adrese: " + sb);
        return true;
    }

    /** Čtení zásuvky; když zásuvka zrušila relaci (HTTP 403/401), jednou hned znovu s novým přihlášením. */
    private JSONObject readPlug(String ip, String email, String pass) {
        JSONObject p = readPlugOnce(ip, email, pass);
        String err = p.optString("err", "");
        if (err.contains("HTTP 403") || err.contains("HTTP 401")) {
            tapo.remove(ip);
            JSONObject p2 = readPlugOnce(ip, email, pass);
            if (!p2.has("err")) return p2;
        }
        return p;
    }

    private JSONObject readPlugOnce(String ip, String email, String pass) {
        JSONObject p = new JSONObject();
        try {
            p.put("ip", ip.substring(ip.lastIndexOf('.') + 1));
            TapoKlap t = tapo.get(ip);
            if (t == null) { t = new TapoKlap(ip, email, pass); tapo.put(ip, t); }
            // jméno VŽDY čerstvě ze zásuvky: po restartu routeru se IP adresy přehází a jméno z mezipaměti
            // (dřív až hodinu staré) by přiřadilo naměřené W jiné zásuvce
            {
                JSONObject info = new JSONObject(t.call("get_device_info")).optJSONObject("result");
                if (info != null) {
                    String did = info.optString("device_id", "");
                    if (did.length() > 6) p.put("d", did.substring(did.length() - 6));   // otisk zařízení (kontrola záměny)
                    String nick = info.optString("nickname", "");
                    try { nick = new String(Base64.decode(nick, Base64.DEFAULT), StandardCharsets.UTF_8); } catch (Exception ignored) {}
                    names.put(ip, nick.isEmpty() ? ip : nick);
                    models.put(ip, info.optString("model", ""));
                    if (info.has("device_on")) p.put("on", info.optBoolean("device_on") ? 1 : 0);   // 1.7.8: i měřicí zásuvky (P110)
                }
            }
            p.put("n", names.containsKey(ip) ? names.get(ip) : ip);
            String model = models.containsKey(ip) ? models.get(ip) : "";
            p.put("m", model);
            if (model.startsWith("L")) {                                  // 1.7.5: světla / pásky Tapo (L900, L920…)
                JSONObject info = new JSONObject(t.call("get_device_info")).optJSONObject("result");
                if (info != null) p.put("on", info.optBoolean("device_on") ? 1 : 0);
                // spotřebu světlo samo neměří, odhaduje ji (jako aplikace Tapo): Wh dnes z get_device_usage
                try {
                    JSONObject u = new JSONObject(t.call("get_device_usage")).optJSONObject("result");
                    JSONObject pu = u != null ? u.optJSONObject("power_usage") : null;
                    if (pu != null && pu.has("today")) p.put("wh", pu.optInt("today"));
                    else p.put("nm", 1);
                } catch (Exception ue) { p.put("nm", 1); }
                p.put("lt", 1);
                note(ip, "ok", null);
                return p;
            }
            if (model.startsWith("P100") || model.startsWith("P105")) {   // tyto zásuvky spotřebu neměří
                JSONObject info = new JSONObject(t.call("get_device_info")).optJSONObject("result");
                if (info != null) p.put("on", info.optBoolean("device_on") ? 1 : 0);
                p.put("nm", 1);
                note(ip, "ok", null);
                return p;
            }
            JSONObject res = new JSONObject(t.call("get_energy_usage"));
            JSONObject e = res.optJSONObject("result");
            if (res.optInt("error_code", 0) == 0 && e != null) {
                if (e.has("current_power")) p.put("w", round(e.getDouble("current_power") / 1000.0, 1));
                if (e.has("today_energy")) p.put("wh", e.getInt("today_energy"));
            } else {
                p.put("nm", 1);   // zásuvka spotřebu neměří
            }
            note(ip, "ok", null);
        } catch (Exception ex) {
            tapo.remove(ip);   // příště nové přihlášení
            String msg = String.valueOf(ex.getMessage());
            boolean unreachable = ex instanceof java.net.SocketTimeoutException || ex instanceof java.net.ConnectException
                    || ex instanceof java.net.NoRouteToHostException || msg.contains("Failed to connect") || msg.contains("timed out");
            // 1.9.13: přesně proč nedostupná – odmítla spojení / adresa v síti není / spojení vypršelo / neodpověděla
            String m = msg.toLowerCase(Locale.US), kind;
            if (m.contains("refused")) kind = "odmítla spojení";
            else if (ex instanceof java.net.NoRouteToHostException || m.contains("ehostunreach") || m.contains("no route")) kind = "adresa v síti není";
            else if (ex instanceof java.net.SocketTimeoutException && (m.contains("connect") || m.contains("failed to connect"))) kind = "spojení vypršelo";
            else if (ex instanceof java.net.SocketTimeoutException) kind = "spojila se, ale neodpověděla";
            else kind = ex.getClass().getSimpleName();
            String ow = kind + " · ." + ip.substring(ip.lastIndexOf('.') + 1);
            String full = kind + " · " + (msg.length() > 140 ? msg.substring(0, 140) : msg);   // 1.9.15: i odkud Flip volal („from /…“)
            try {
                if (!p.has("n") && names.containsKey(ip)) p.put("n", names.get(ip));
                if (unreachable) { p.put("off", 1); p.put("ow", ow); } else p.put("err", msg);
            } catch (Exception ignored) {}
            note(ip, unreachable ? "off" : "err", unreachable ? "nedostupná – " + full : msg);
        }
        return p;
    }

    /**
     * Zásuvka si energii pamatuje sama (hodinově). Hlídač podle toho zpětně opraví denní součty i běhy generátoru,
     * i když Flip zásuvku zrovna nezachytil. Posílá do <topic>-tp-hist: {"id":"3","h":{"2026-10-14":[24× Wh]}}.
     */
    private void sendPlugHistories(String email, String pass, JSONArray plugs, Map<String, String> idIp) {
        String topic = Prefs.s(ctx, Prefs.NTFY_TOPIC);
        if (topic.isEmpty() || histBackoff()) return;
        java.text.SimpleDateFormat df = new java.text.SimpleDateFormat("yyyy-MM-dd", Locale.US);
        String today = df.format(new java.util.Date());
        for (int k = 0; k < plugs.length(); k++) {
            JSONObject p = plugs.optJSONObject(k);
            if (p == null || p.has("off") || p.has("err") || p.has("nm") || !p.has("wh")) continue;
            String id = p.optString("ip"), key = "hist_" + id;
            boolean cameBack = p.has("since");
            if (!cameBack && today.equals(Prefs.get(ctx).getString(key, ""))) continue;
            String ip = idIp.get(id);
            if (ip == null) continue;
            try {
                TapoKlap t = tapo.get(ip);
                if (t == null) { t = new TapoKlap(ip, email, pass); tapo.put(ip, t); }
                JSONObject days = new JSONObject();
                java.util.Calendar cal = java.util.Calendar.getInstance();
                cal.set(java.util.Calendar.HOUR_OF_DAY, 0); cal.set(java.util.Calendar.MINUTE, 0);
                cal.set(java.util.Calendar.SECOND, 0); cal.set(java.util.Calendar.MILLISECOND, 0);
                for (int back = 0; back < 7; back++) {
                    java.util.Calendar d = (java.util.Calendar) cal.clone();
                    d.add(java.util.Calendar.DAY_OF_MONTH, -back);
                    long start = d.getTimeInMillis() / 1000;
                    java.util.Calendar dn = (java.util.Calendar) d.clone();         // 1.7.9: konec dne = další půlnoc
                    dn.add(java.util.Calendar.DAY_OF_MONTH, 1);                     // (den změny času má 23 / 25 h)
                    long end = dn.getTimeInMillis() / 1000;
                    int hours = (int) Math.round((end - start) / 3600.0);
                    JSONObject r = new JSONObject(t.call("get_energy_data",
                            "{\"start_timestamp\":" + start + ",\"end_timestamp\":" + (end - 1) + ",\"interval\":60}"));
                    JSONObject res = r.optJSONObject("result");
                    if (r.optInt("error_code", 0) != 0 || res == null) break;
                    JSONArray data = res.optJSONArray("data");
                    if (data == null) continue;
                    JSONArray h = new JSONArray();
                    for (int i = 0; i < hours; i++) h.put(data.optInt(i, -1));
                    days.put(df.format(d.getTime()), h);
                }
                if (days.length() > 0) {
                    post("https://ntfy.sh/" + topic + "-tp-hist", new JSONObject().put("id", id).put("h", days).toString());
                    Prefs.get(ctx).edit().putString(key, today).apply();
                    Prefs.log(ctx, "Historie zásuvky (" + id + ") odeslána: " + days.length() + " dní");
                }
            } catch (Exception e) {
                Prefs.log(ctx, "Historie zásuvky (" + id + "): " + e.getMessage());
                histFailed();
                return;                                  // ntfy nejde → další zásuvky zkusit až za hodinu
            }
        }
    }

    /** Číslo zásuvky → IP. Síť se prohledá při prvním spuštění, každých 6 h a když mapovaná zásuvka nejde (nejvýš 1× za 30 min). */
    private Map<String, String> plugMap(String email, String pass) {
        Map<String, String> m = new HashMap<>();
        android.content.SharedPreferences sp = Prefs.get(ctx);
        try {
            JSONObject j = new JSONObject(sp.getString("tapo_map", "{}"));
            for (java.util.Iterator<String> it = j.keys(); it.hasNext(); ) { String k = it.next(); m.put(k, j.getJSONObject(k).optString("ip")); }
        } catch (Exception ignored) { }
        long age = System.currentTimeMillis() - sp.getLong("tapo_scan_t", 0);
        boolean force = sp.getBoolean("tapo_force", false);
        boolean want = force || (m.isEmpty() ? age > 3 * 60_000L : age > 6 * 3600_000L
                || (sp.getBoolean("tapo_rescan", false) && age > 30 * 60_000L));
        if (force) sp.edit().putBoolean("tapo_force", false).apply();
        if (!want) return m;
        boolean quiet = false;
        Map<String, JSONObject> found = TapoScan.scan(ctx, email, pass, quiet);
        tapo.clear();                                            // hledání se přihlásilo znovu → staré relace zásuvky zrušila (HTTP 403)
        sp.edit().putLong("tapo_scan_t", System.currentTimeMillis()).putBoolean("tapo_rescan", false).apply();
        if (found.isEmpty()) return m;
        JSONObject j;                                           // známé zásuvky si pamatovat, i když teď nemají proud (generátor)
        try { j = new JSONObject(sp.getString("tapo_map", "{}")); } catch (Exception e) { j = new JSONObject(); }
        StringBuilder sb = new StringBuilder();
        for (Map.Entry<String, JSONObject> en : found.entrySet()) {
            try { j.put(en.getKey(), en.getValue()); } catch (Exception ignored) { }
            String ip = en.getValue().optString("ip");
            if (!ip.equals(m.get(en.getKey()))) sb.append(sb.length() > 0 ? ", " : "").append("(").append(en.getKey()).append(") → ").append(ip);
            names.remove(ip);                                    // ať se jméno načte znovu
        }
        sp.edit().putString("tapo_map", j.toString()).apply();
        if (!quiet || sb.length() > 0)
            Prefs.log(ctx, "Hledání zásuvek: nalezeno " + found.size() + (sb.length() > 0 ? " · změny: " + sb : " · beze změn"));
        m.clear();
        for (java.util.Iterator<String> it = j.keys(); it.hasNext(); ) { String k = it.next(); m.put(k, j.optJSONObject(k) != null ? j.optJSONObject(k).optString("ip") : ""); }
        return m;
    }

    /** Povely od hlídače (ntfy téma <topic>-cmd): {"ip":"157","on":true,"id":…,"why":"…"} → přepnout zásuvku. */
    private void applyCommands(String email, String pass) {
        String topic = Prefs.s(ctx, Prefs.NTFY_TOPIC);
        if (topic.isEmpty()) return;
        try {
            HttpURLConnection c = (HttpURLConnection) new URL("https://ntfy.sh/" + topic + "-cmd/json?poll=1&since=3h").openConnection();
            c.setConnectTimeout(15000);
            c.setReadTimeout(15000);
            String body;
            try (java.io.InputStream in = c.getInputStream()) {
                java.io.ByteArrayOutputStream bo = new java.io.ByteArrayOutputStream();
                byte[] buf = new byte[4096];
                int n;
                while ((n = in.read(buf)) > 0) bo.write(buf, 0, n);
                body = bo.toString("UTF-8");
            } finally { c.disconnect(); }
            JSONObject last = null;
            for (String ln : body.split("\n")) {
                if (ln.trim().isEmpty()) continue;
                JSONObject m = new JSONObject(ln);
                if (!"message".equals(m.optString("event"))) continue;
                try { last = new JSONObject(m.optString("message")); } catch (Exception ignored) {}
            }
            if (last == null) return;
            long id = last.optLong("id", 0);
            long done = Prefs.get(ctx).getLong("cmd_done", 0);
            if (id <= done) return;
            String ip = last.optString("ip", "");
            String mapped = plugMap(email, pass).get(ip);                // číslo zásuvky → aktuální IP
            if (mapped != null && !mapped.isEmpty()) ip = mapped;
            else if (ip.matches("\\d+")) ip = "192.168.0." + ip;
            boolean on = last.optBoolean("on", false);
            TapoKlap t = tapo.get(ip);
            if (t == null) { t = new TapoKlap(ip, email, pass); tapo.put(ip, t); }
            JSONObject r = new JSONObject(t.call("set_device_info", "{\"device_on\":" + on + "}"));
            if (r.optInt("error_code", -1) == 0) {
                Prefs.get(ctx).edit().putLong("cmd_done", id).apply();
                Prefs.log(ctx, "Zásuvka " + label(ip) + " " + (on ? "ZAPNUTA" : "VYPNUTA") + " (" + last.optString("why", "povel") + ")");
            } else {
                Prefs.log(ctx, "Povel pro zásuvku " + label(ip) + " selhal: " + r);
            }
        } catch (Exception e) {
            Prefs.log(ctx, "Povely: " + e.getMessage());
        }
    }

    /**
     * 1.6: zásuvka s nabíječkou Flipu. Povolení posílá hlídač do ntfy <téma>-fc ({"allow", "ip", "why", "id"}):
     * na soláru nabíjet jen přes den, když panely dodávají; na River kdykoli. Místně (i bez internetu):
     * • teplota baterie ≥ 42 °C → vypnout (bezpečnost), zpět až pod 36 °C
     * • pod 20 % → nabíjet vždy (pokud není horko) – 1.9.2: bez povolení jen na cíl „ftgt“ od hlídače (vydrží do slunce)
     * • od 80 % vypnout (telefon má limit 80 %), znovu až pod 75 %
     * • bez spojení s hlídačem (povolení starší než 3 h) → nabíjet pod 40 %
     * Při vypnutí se v zásuvce nastaví odpočet „za 3 h zapnout“ – kdyby aplikace spadla, telefon se nevybije.
     */
    private void flipCharge(String email, String pass, int pct, boolean charging, double tempC, JSONArray plugs, JSONObject o) throws Exception {
        android.content.SharedPreferences P = Prefs.get(ctx);
        String topic = Prefs.s(ctx, Prefs.NTFY_TOPIC);
        try {                                                            // povolení od hlídače
            HttpURLConnection c = (HttpURLConnection) new URL("https://ntfy.sh/" + topic + "-fc/json?poll=1&since=6h").openConnection();
            c.setConnectTimeout(15000); c.setReadTimeout(15000);
            String body;
            try (java.io.InputStream in = c.getInputStream()) {
                java.io.ByteArrayOutputStream bo = new java.io.ByteArrayOutputStream();
                byte[] buf = new byte[4096]; int n;
                while ((n = in.read(buf)) > 0) bo.write(buf, 0, n);
                body = bo.toString("UTF-8");
            } finally { c.disconnect(); }
            JSONObject last = null;
            for (String ln : body.split("\n")) {
                if (ln.trim().isEmpty()) continue;
                JSONObject m = new JSONObject(ln);
                if ("message".equals(m.optString("event"))) try { last = new JSONObject(m.optString("message")); } catch (Exception ignored) {}
            }
            if (last != null && last.optLong("id") * 1000 > P.getLong("fc_t", 0)) {
                P.edit().putBoolean("fc_allow", last.optBoolean("allow", false)).putLong("fc_t", last.optLong("id") * 1000)
                        .putString("fc_ip", last.optString("ip", "9")).putString("fc_why", last.optString("why", ""))
                        .putString("rc_ip", last.optString("rip", ""))                   // 1.9: zásuvka routeru
                        .putBoolean("rc_free", last.optBoolean("rfree", false))           // 1.9.1: přebytek ze slunce
                        .putInt("fc_tgt", last.optInt("ftgt", 0))                          // 1.9.2: dobít na (noc)
                        .putInt("fc_min", last.optInt("fmin", 30))                         // 1.9.6: spodní hranice (Nastavení)
                        .putBoolean("fc_full", last.optBoolean("full", false))            // 1.9.12: Float → doplna
                        .putString("stale_ids", last.has("stale") ? last.optJSONArray("stale") != null ? last.optJSONArray("stale").join(",").replace("\"", "") : "" : "")   // 1.9.14
                        .putString("rst_at", last.optString("rst", "22:10")).apply();      // 1.9.11: čas denního restartu
            }
        } catch (Exception e) { /* bez internetu – platí poslední povolení / záloha pod 40 % */ }
        String id = P.getString("fc_ip", "9");
        if (id.isEmpty()) return;                                        // řízení vypnuté
        boolean fresh = System.currentTimeMillis() - P.getLong("fc_t", 0) < 3 * 3600_000L;
        boolean hot = P.getBoolean("fc_hot", false);
        if (!Double.isNaN(tempC)) {
            if (tempC >= 42) hot = true; else if (tempC <= 36) hot = false;
        }
        JSONObject cur = null;
        for (int k = 0; k < plugs.length(); k++) { JSONObject p = plugs.optJSONObject(k); if (p != null && id.equals(p.optString("ip"))) cur = p; }
        if (cur == null || cur.has("off") || cur.has("err") || !cur.has("on")) {
            if (!P.getBoolean("fc_miss", false)) Prefs.log(ctx, "Nabíjení Flipu: zásuvka (" + id + ") nenalezena / nejde přečíst");
            P.edit().putBoolean("fc_miss", true).putBoolean("fc_hot", hot).apply();
            o.put("fc", new JSONObject().put("miss", 1).put("ip", id)
                    .put("why", cur == null ? "zásuvka nenalezena" : cur.has("off") ? "zásuvka nedostupná" : cur.has("err") ? "zásuvka hlásí chybu" : "zásuvka neposílá stav zapnuto/vypnuto"));
            return;
        }
        P.edit().putBoolean("fc_miss", false).apply();
        boolean isOn = cur.optInt("on", 0) == 1, want;
        String why;
        if (hot) { want = false; why = String.format(Locale.US, "baterie Flipu %.1f °C – bezpečnost", tempC); }
        else if (pct <= P.getInt("fc_min", 30)) { want = true; why = "pod " + P.getInt("fc_min", 30) + " %"; P.edit().putBoolean("fc_low", true).apply(); }
        else if (fresh && System.currentTimeMillis() - P.getLong("fc_t", 0) < 75 * 60_000L && P.getBoolean("fc_allow", false)
                && P.getBoolean("fc_full", false) && pct < 100) {
            // 1.9.12: solární baterie plná (Float) – energie by se zahodila → doplna, bez ohledu na 75 / 80 %
            want = true; why = P.getString("fc_why", "solární baterie plná – doplna");
        }
        else if (pct >= 80) { want = false; why = "nabito 80 %"; }
        else if (pct >= 75 && !isOn) { want = false; why = "nabito (pod 75 % znovu)"; }
        else if (fresh && P.getBoolean("fc_allow", false)) { want = true; why = P.getString("fc_why", ""); }
        else if (P.getBoolean("fc_low", false) && isOn) {
            // 1.9.2: po poklesu pod 20 % dobít jen na cíl od hlídače (vydrží do slunce), ne do plna; bez spojení na 40 %
            int tgt = fresh && P.getInt("fc_tgt", 0) > 0 ? P.getInt("fc_tgt", 0) : Math.max(40, P.getInt("fc_min", 30) + 10);
            want = pct < tgt;
            why = want ? "dobíjí na " + tgt + " % (vydrží do slunce)" : "dobito na " + tgt + " % – vydrží do slunce";
        }
        else if (fresh) { want = false; why = P.getString("fc_why", ""); }
        else { want = pct < 40; why = "bez spojení s hlídačem – nabíjí pod 40 %"; }
        if (!want || pct >= 80) P.edit().putBoolean("fc_low", false).apply();
        if (want != isOn) {
            String ip = plugMap(email, pass).get(id);
            if (ip == null) ip = id.matches("\\d+") ? null : id;
            if (ip != null) {
                TapoKlap t = tapo.get(ip);
                if (t == null) { t = new TapoKlap(ip, email, pass); tapo.put(ip, t); }
                JSONObject r = new JSONObject(t.call("set_device_info", "{\"device_on\":" + want + "}"));
                if (r.optInt("error_code", -1) == 0) {
                    Prefs.log(ctx, "Nabíjení Flipu " + (want ? "ZAPNUTO" : "VYPNUTO") + " (" + why + ")");
                    isOn = want;
                    if (!want) {                                         // pojistka: za 3 h se zásuvka sama zapne
                        String cdErr = countdownOn(t, 10800);
                        P.edit().putString("fc_cd_err", cdErr == null ? "" : cdErr).apply();
                        if (cdErr == null) P.edit().putLong("fc_cd_t", System.currentTimeMillis()).apply();
                        if (cdErr != null && !P.getBoolean("fc_cd_log", false)) {
                            Prefs.log(ctx, "Pojistka (odpočet zapnutí) zásuvka nepřijala: " + cdErr);
                            P.edit().putBoolean("fc_cd_log", true).apply();
                        }
                    }
                } else Prefs.log(ctx, "Nabíjení Flipu: zásuvka odmítla " + r);
            }
        }
        // 1.9.7: dokud Brána běží a zásuvka má zůstat vypnutá, odpočet „zapnout za 3 h“ každých 30 min obnovit –
        // jinak by po 3 h zásuvku zapnul a Flip by se zbytečně nabíjel (pojistka má zabrat jen když Brána nejede)
        if (!isOn && !want && System.currentTimeMillis() - P.getLong("fc_cd_t", 0) > 30 * 60_000L) {
            try {
                String ip2 = plugMap(email, pass).get(id);
                if (ip2 != null) {
                    TapoKlap t2 = tapo.get(ip2);
                    if (t2 == null) { t2 = new TapoKlap(ip2, email, pass); tapo.put(ip2, t2); }
                    if (countdownOn(t2, 10800) == null) P.edit().putLong("fc_cd_t", System.currentTimeMillis()).apply();
                }
            } catch (Exception ignored) { }
        }
        P.edit().putBoolean("fc_hot", hot).apply();
        JSONObject fco = new JSONObject().put("on", isOn ? 1 : 0).put("why", why).put("hot", hot ? 1 : 0).put("fresh", fresh ? 1 : 0).put("ip", id);
        String fce = P.getString("fc_cd_err", "");
        if (!fce.isEmpty()) fco.put("err", fce.length() > 120 ? fce.substring(0, 120) : fce);   // 1.9.8: pojistku zásuvka nepřijala
        o.put("fc", fco);
    }

    /**
     * 1.9: zásuvka, ze které se napájí router M7000 (číslo posílá hlídač v povolení -fc jako „rip“; prázdné = neřídit).
     * Router dělá Wi‑Fi, přes kterou Flip zásuvky ovládá – vybitý router už nikdo nezapne. Proto:
     * • baterie routeru nejde přečíst (nebo je údaj starší než 25 min) → zapnout
     * • pod 40 % → zapnout, od 80 % vypnout, mezi tím nechat jak je
     * • přebytek ze slunce (povolení od hlídače „rfree“) → zapnout; z River ne (1.9.1)
     * Při vypnutí se v zásuvce nastaví odpočet „za 2 h zapnout“ – kdyby spadla aplikace, Flip nebo Wi‑Fi.
     */
    private void routerCharge(String email, String pass, JSONArray plugs, JSONObject o) throws Exception {
        android.content.SharedPreferences P = Prefs.get(ctx);
        String id = P.getString("rc_ip", "");
        if (id.isEmpty() || plugs == null) return;
        JSONObject cur = null;
        for (int k = 0; k < plugs.length(); k++) { JSONObject p = plugs.optJSONObject(k); if (p != null && id.equals(p.optString("ip"))) cur = p; }
        if (cur == null || cur.has("off") || cur.has("err") || !cur.has("on")) {
            o.put("rc", new JSONObject().put("miss", 1).put("ip", id).put("why", cur == null ? "zásuvka nenalezena" : "zásuvka nejde přečíst"));
            return;
        }
        int b = -1;
        String bNote = "";
        try {
            JSONObject lr = new JSONObject(P.getString("rt_last", "{}"));
            if (lr.has("b") && System.currentTimeMillis() - P.getLong("rt_t", 0) < 25 * 60_000L) b = lr.optInt("b", -1);
        } catch (Exception ignored) { }
        // 1.9.9: občas se router nepřečte (přihlášený správce v aplikaci tpMiFi, router zaneprázdněný) – baterie routeru
        // se mění pomalu, takže do 60 min platí poslední úspěšné přečtení; „pro jistotu nabíjet“ až potom, nebo pod 50 %
        if (b < 0) {
            long age = System.currentTimeMillis() - P.getLong("rt_good_t", 0);
            int gb = P.getInt("rt_good_b", -1);
            if (gb >= 50 && age < 60 * 60_000L) { b = gb; bNote = " (poslední přečtení před " + (age / 60_000L) + " min)"; }
        }
        boolean fresh = System.currentTimeMillis() - P.getLong("fc_t", 0) < 3 * 3600_000L;
        // 1.9.1: „zadarmo“ = jen přebytek ze slunce (River zadarmo není – musí vydržet noc)
        boolean free = fresh && P.getBoolean("rc_free", false);
        boolean isOn = cur.optInt("on", 0) == 1, want;
        String why;
        if (b < 0) { want = true; why = "baterie routeru nejde přečíst déle než hodinu – pro jistotu nabíjí"; }
        else if (b <= 40) { want = true; why = "pod 40 %"; }
        else if (free && b < 90) { want = true; why = "slunce navíc"; }
        else if (b >= 80) { want = false; why = "nabito 80 % – jede z baterie"; }
        else { want = isOn; why = isOn ? "nabíjí do 80 %" : "jede z baterie do 40 %"; }
        // 1.9.8: když zásuvka nepřijala pojistku, nezkoušet ji vypínat každých 10 min znovu (přepínala by se) – zkusit za 6 h
        if (!want && isOn && !P.getString("rc_cd_err", "").isEmpty()
                && System.currentTimeMillis() - P.getLong("rc_cd_fail_t", 0) < 6 * 3600_000L) {
            o.put("rc", new JSONObject().put("on", 1).put("why", "zásuvka nepřijala pojistku – nechávám zapnutou, zkusím znovu za pár hodin")
                    .put("err", P.getString("rc_cd_err", "")).put("ip", id));
            return;
        }
        if (want != isOn) {
            String ip = plugMap(email, pass).get(id);
            if (ip == null) ip = id.matches("\\d+") ? null : id;
            if (ip != null) {
                TapoKlap t = tapo.get(ip);
                if (t == null) { t = new TapoKlap(ip, email, pass); tapo.put(ip, t); }
                // 1.9.5: Tapo přijme „zapnout za …“ jen u VYPNUTÉ zásuvky (jako v aplikaci Tapo) – proto napřed vypnout,
                // hned nastavit odpočet; když ho zásuvka nepřijme, okamžitě zase zapnout (router bez pojistky nevypínat)
                JSONObject r = new JSONObject(t.call("set_device_info", "{\"device_on\":" + want + "}"));
                if (r.optInt("error_code", -1) == 0) {
                    isOn = want;
                    if (!want) {
                        String cdErr = countdownOn(t, 7200);
                        if (cdErr != null) {
                            JSONObject r2 = new JSONObject(t.call("set_device_info", "{\"device_on\":true}"));
                            isOn = r2.optInt("error_code", -1) == 0 ? true : isOn;
                            if (!cdErr.equals(P.getString("rc_cd_err", ""))) Prefs.log(ctx, "Router: zásuvka nepřijala pojistku (odpočet) – nechávám zapnutou: " + cdErr);
                            P.edit().putString("rc_cd_err", cdErr).putLong("rc_cd_fail_t", System.currentTimeMillis()).apply();
                            o.put("rc", new JSONObject().put("on", isOn ? 1 : 0).put("why", "zásuvka nepřijala pojistku – nechávám zapnutou").put("err", cdErr.length() > 120 ? cdErr.substring(0, 120) : cdErr).put("ip", id));
                            return;
                        }
                        P.edit().putString("rc_cd_err", "").putLong("rc_cd_t", System.currentTimeMillis()).apply();
                    }
                    Prefs.log(ctx, "Nabíjení routeru " + (want ? "ZAPNUTO" : "VYPNUTO") + " (" + b + " %, " + why + ")");
                } else Prefs.log(ctx, "Nabíjení routeru: zásuvka odmítla " + r);
            }
        }
        if (!isOn && !want && System.currentTimeMillis() - P.getLong("rc_cd_t", 0) > 30 * 60_000L) {   // 1.9.7: obnovit pojistku
            try {
                String ip2 = plugMap(email, pass).get(id);
                if (ip2 != null) {
                    TapoKlap t2 = tapo.get(ip2);
                    if (t2 == null) { t2 = new TapoKlap(ip2, email, pass); tapo.put(ip2, t2); }
                    if (countdownOn(t2, 7200) == null) P.edit().putLong("rc_cd_t", System.currentTimeMillis()).apply();
                }
            } catch (Exception ignored) { }
        }
        o.put("rc", new JSONObject().put("on", isOn ? 1 : 0).put("why", why + bNote).put("ip", id));
    }

    /** 1.9.5: odpočet „za sec zapnout“ v zásuvce Tapo. Napřed add_countdown_rule; když už pravidlo existuje
     *  (zásuvka má jen jedno), upraví ho přes edit_countdown_rule. → null = OK, jinak text chyby. */
    private String countdownOn(TapoKlap t, int sec) {
        String prm = "\"delay\":" + sec + ",\"desired_states\":{\"on\":true},\"enable\":true,\"remain\":" + sec;
        String err;
        try {
            JSONObject cr = new JSONObject(t.call("add_countdown_rule", "{" + prm + "}"));
            if (cr.optInt("error_code", -1) == 0) return null;
            err = "add " + cr;
        } catch (Exception e) { err = "add " + e.getMessage(); }
        try {
            JSONObject g = new JSONObject(t.call("get_countdown_rules"));
            JSONObject res = g.optJSONObject("result");
            org.json.JSONArray rl = res != null ? res.optJSONArray("rule_list") : null;
            if (rl != null && rl.length() > 0) {
                String rid = rl.getJSONObject(0).optString("id", "");
                JSONObject er = new JSONObject(t.call("edit_countdown_rule", "{\"id\":\"" + rid + "\"," + prm + "}"));
                if (er.optInt("error_code", -1) == 0) return null;
                err += " | edit " + er;
            } else err += " | get " + g;
        } catch (Exception e) { err += " | " + e.getMessage(); }
        return err;
    }

    /** Adresa routeru = výchozí brána Wi-Fi (jinak 192.168.0.1). */
    private String gateway() {
        try {
            android.net.ConnectivityManager cm = ctx.getSystemService(android.net.ConnectivityManager.class);
            for (android.net.Network n : cm.getAllNetworks()) {
                android.net.NetworkCapabilities nc = cm.getNetworkCapabilities(n);
                if (nc == null || !nc.hasTransport(android.net.NetworkCapabilities.TRANSPORT_WIFI)) continue;
                android.net.LinkProperties lp = cm.getLinkProperties(n);
                if (lp == null) continue;
                for (android.net.RouteInfo ri : lp.getRoutes())
                    if (ri.isDefaultRoute() && ri.getGateway() != null) return ri.getGateway().getHostAddress();
            }
        } catch (Exception ignored) { }
        return "192.168.0.1";
    }

    /** Historie zásuvek přes ntfy: po chybě (např. 429) další pokus nejdřív za hodinu, ne v každém kole. */
    private boolean histBackoff() { return System.currentTimeMillis() - Prefs.get(ctx).getLong("hist_fail", 0) < 3600_000L; }
    private void histFailed() { Prefs.get(ctx).edit().putLong("hist_fail", System.currentTimeMillis()).apply(); }

    /**
     * Data na GitHub: spuštění hlídače s daty v parametru „flip“ (pole zpráv). Posílá se vždy nejnovější zpráva
     * a k ní co nejvíc starších z vyrovnávací paměti (od nejstarších) – každá zpráva jde 3× (kdyby GitHub čekající
     * běh zrušil, přijde znovu v dalším). Hlídač zprávy pozná podle "ts", dvakrát je nezapočítá.
     * @return počet poslaných zpráv, -1 = nejde (bez tokenu / chyba) → záloha přes ntfy
     */
    private synchronized int sendGitHub(String msg) {
        String tok = Prefs.s(ctx, Prefs.GH_TOKEN);
        if (tok.isEmpty()) return -1;
        try {
            JSONArray buf = new JSONArray();
            // 1.4.1: zprávy, které čekaly ve frontě pro ntfy (ntfy je odmítal), pošlou se taky – přes GitHub
            JSONArray ob = new JSONArray(Prefs.get(ctx).getString("outbox", "[]"));
            for (int i = 0; i < ob.length(); i++) buf.put(new JSONObject().put("m", ob.getString(i)).put("n", 0));
            JSONArray old = new JSONArray(Prefs.get(ctx).getString("ghbuf", "[]"));
            for (int i = 0; i < old.length(); i++) buf.put(old.getJSONObject(i));
            buf.put(new JSONObject().put("m", msg).put("n", 0));
            long cut = System.currentTimeMillis() / 1000 - 24 * 3600;
            JSONArray keep = new JSONArray();                       // starší než den pryč, nejvýš 150 zpráv
            for (int i = Math.max(0, buf.length() - 150); i < buf.length(); i++) {
                JSONObject b = buf.getJSONObject(i);
                if (new JSONObject(b.getString("m")).optLong("ts", 0) >= cut) keep.put(b);
            }
            buf = keep;
            JSONArray arr = new JSONArray();
            java.util.List<Integer> used = new java.util.ArrayList<>();
            int size = msg.length();
            arr.put(msg); used.add(buf.length() - 1);
            for (int i = 0; i < buf.length() - 1; i++) {             // starší, od nejstarších, do ~40 000 znaků
                String m = buf.getJSONObject(i).getString("m");
                if (size + m.length() > 40000) break;
                arr.put(m); used.add(i); size += m.length();
            }
            JSONObject body = new JSONObject().put("ref", "main").put("inputs",
                    new JSONObject().put("test", "false").put("wake", "false").put("flip", arr.toString()));
            HttpURLConnection c = (HttpURLConnection) new URL("https://api.github.com/repos/KptDundee/chata-hlidac/actions/workflows/hlidac.yml/dispatches").openConnection();
            c.setConnectTimeout(15000);
            c.setReadTimeout(20000);
            c.setRequestMethod("POST");
            c.setDoOutput(true);
            c.setRequestProperty("Authorization", "Bearer " + tok);
            c.setRequestProperty("Accept", "application/vnd.github+json");
            c.setRequestProperty("Content-Type", "application/json");
            try (OutputStream o = c.getOutputStream()) { o.write(body.toString().getBytes(StandardCharsets.UTF_8)); }
            int code = c.getResponseCode();
            String err = code == 204 ? "" : errText(c);
            c.disconnect();
            if (code != 204) {
                Prefs.get(ctx).edit().putString("ghbuf", buf.toString()).putString("outbox", "[]").apply();
                Prefs.log(ctx, "GitHub odpověděl " + code + (code == 401 || code == 403 ? " – zkontroluj token (Actions: Read and write)" : "") + " " + err + " – zkusím ntfy");
                return -1;
            }
            JSONArray rest = new JSONArray();
            for (int i = 0; i < buf.length(); i++) {
                JSONObject b = buf.getJSONObject(i);
                if (used.contains(i)) b.put("n", b.optInt("n") + 1);
                if (b.optInt("n") < 3) rest.put(b);
            }
            Prefs.get(ctx).edit().putString("ghbuf", rest.toString()).putString("outbox", "[]").apply();
            return arr.length();
        } catch (Exception e) {
            Prefs.log(ctx, "GitHub: " + e.getMessage() + " – zkusím ntfy");
            return -1;
        }
    }

    /** Text chybové odpovědi (pro záznam – ať je vidět, proč server odmítl). */
    private static String errText(HttpURLConnection c) {
        try (java.io.InputStream in = c.getErrorStream()) {
            if (in == null) return "";
            byte[] b = new byte[300]; int n = in.read(b);
            return n > 0 ? "(" + new String(b, 0, n, StandardCharsets.UTF_8).replaceAll("\\s+", " ").trim() + ")" : "";
        } catch (Exception e) { return ""; }
    }

    /** Do záznamu jen změny stavu zásuvky. */
    /** Zásuvka v Deníku podle našeho čísla „(N) jméno“, IP jen když číslo neznáme. */
    private String label(String ip) {
        String nm = names.get(ip), id = TapoScan.idFromName(nm);
        if (id != null) return "(" + id + ") " + nm.replaceFirst("^\\s*(\\([^)]*\\)\\s*)+", "");
        return "na ." + ip.substring(ip.lastIndexOf('.') + 1) + " (číslo neznámé)";
    }

    private void note(String ip, String state, String msg) {
        String prev = lastState.put(ip, state);
        if (state.equals(prev)) return;
        if (msg != null) Prefs.log(ctx, "Zásuvka " + label(ip) + ": " + msg);
        else if (prev != null) Prefs.log(ctx, "Zásuvka " + label(ip) + ": zase dostupná");
    }

    /** Po hodině se znovu načtou názvy zásuvek (kdyby se přejmenovaly). */
    public void forgetNames() { names.clear(); models.clear(); }

    /** 1.9.11: plánovaný restart Brány – zahodit spojení se zásuvkami (přihlášení se udělá znovu) a znovu prohledat síť. */
    public synchronized void softReset() {
        tapo.clear(); names.clear(); models.clear();
        Prefs.get(ctx).edit().putBoolean("tapo_rescan", true).putBoolean("tapo_force", true).apply();
    }

    /** Spustí hlídače na GitHubu hned (GitHub plánovaná spuštění zdržuje na 30–45 min). Bez tokenu nic. */
    private void dispatchWatcher() {
        String tok = Prefs.s(ctx, Prefs.GH_TOKEN);
        if (tok.isEmpty()) return;
        try {
            HttpURLConnection c = (HttpURLConnection) new URL("https://api.github.com/repos/KptDundee/chata-hlidac/actions/workflows/hlidac.yml/dispatches").openConnection();
            c.setConnectTimeout(15000);
            c.setReadTimeout(15000);
            c.setRequestMethod("POST");
            c.setDoOutput(true);
            c.setRequestProperty("Authorization", "Bearer " + tok);
            c.setRequestProperty("Accept", "application/vnd.github+json");
            try (OutputStream o = c.getOutputStream()) { o.write("{\"ref\":\"main\",\"inputs\":{\"test\":false,\"wake\":false}}".getBytes(StandardCharsets.UTF_8)); }
            int code = c.getResponseCode();
            c.disconnect();
            if (code != 204) Prefs.log(ctx, "Spuštění hlídače: GitHub odpověděl " + code + (code == 401 || code == 403 ? " – zkontroluj token" : ""));
        } catch (Exception e) {
            Prefs.log(ctx, "Spuštění hlídače: " + e.getMessage());
        }
    }

    /** Fronta neodeslaných zpráv (max ~1 den) – po obnovení internetu se pošlou, hlídač je zařadí podle "ts". */
    private synchronized int queue(String msg) {
        try {
            JSONArray q = new JSONArray(Prefs.get(ctx).getString("outbox", "[]"));
            q.put(msg);
            while (q.length() > 150) q.remove(0);
            Prefs.get(ctx).edit().putString("outbox", q.toString()).apply();
            return q.length();
        } catch (Exception e) { return 0; }
    }

    private synchronized int flushOutbox(String url) {
        int sent = 0;
        try {
            JSONArray q = new JSONArray(Prefs.get(ctx).getString("outbox", "[]"));
            if (q.length() == 0) return 0;
            JSONArray rest = new JSONArray();
            boolean fail = false;
            for (int i = 0; i < q.length(); i++) {
                if (!fail) {
                    try { post(url, q.getString(i)); sent++; continue; }
                    catch (Exception e) { fail = true; }
                }
                rest.put(q.getString(i));
            }
            Prefs.get(ctx).edit().putString("outbox", rest.toString()).apply();
        } catch (Exception ignored) { }
        return sent;
    }

    private static void post(String url, String body) throws Exception {
        HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
        c.setConnectTimeout(15000);
        c.setReadTimeout(15000);
        c.setRequestMethod("POST");
        c.setDoOutput(true);
        c.setRequestProperty("Title", "data");
        c.setRequestProperty("Priority", "1");
        try (OutputStream o = c.getOutputStream()) { o.write(body.getBytes(StandardCharsets.UTF_8)); }
        int code = c.getResponseCode();
        String err = code >= 300 ? errText(c) : "";
        c.disconnect();
        if (code >= 300) throw new Exception("ntfy HTTP " + code + (err.isEmpty() ? "" : " " + err));
    }

    /** Verze aplikace (versionName z build.gradle) – hlídač ji ukáže na webu. */
    static String appVersion(Context c) {
        try { return c.getPackageManager().getPackageInfo(c.getPackageName(), 0).versionName; }
        catch (Exception e) { return "?"; }
    }

    private String appVersion() { return appVersion(ctx); }

    private static double round(double v, int d) {
        double f = Math.pow(10, d);
        return Math.round(v * f) / f;
    }
}
