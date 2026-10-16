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

    public Collector(Context ctx, BleListener ble) {
        this.ctx = ctx.getApplicationContext();
        this.ble = ble;
    }

    /** @return krátký popis výsledku do notifikace */
    public String runOnce() {
        try {
            JSONObject o = new JSONObject();
            o.put("ver", 1);
            o.put("ts", System.currentTimeMillis() / 1000);     // kdy se měřilo (zpráva může odejít později z fronty)
            StringBuilder sum = new StringBuilder();

            // 1) měnič Victron (Bluetooth)
            if (ble.samples() == 0) ble.burst(20_000);   // trvalý poslech nic nechytil → 20 s intenzivně
            BleListener.Snapshot s = ble.takeSnapshot();
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
                java.util.LinkedHashSet<String> ipsAll = new java.util.LinkedHashSet<>(map.values());
                if (map.isEmpty()) ipsAll.addAll(Prefs.tapoIps(ctx));       // ruční adresy jen když hledání nic nenašlo
                boolean missing = false;
                Map<String, String> idIp = new HashMap<>();
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
                if (missing || (ok == 0 && total > 0)) Prefs.get(ctx).edit().putBoolean("tapo_rescan", true).apply();
                // historie ze zásuvky (hodinová energie za 7 dní): jednou denně a hned, když se zásuvka znovu objeví
                sendPlugHistories(email, pass, plugs, idIp);
                if (plugs.length() > 0) o.put("tp", plugs);
                sum.append(", zásuvky ").append(ok).append('/').append(total);
                if (off > 0) sum.append(" (").append(off).append(" vypnuté)");
            }

            // 2b) jednou denně: hodinová historie spotřeby zásuvky za měničem (pro ukazatel zdraví baterie)
            if (!email.isEmpty()) sendPlugHistory(email, pass);

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
            }

            o.put("av", appVersion());
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
            return sum.toString() + (sentOld > 0 ? " · +" + sentOld + " z fronty" : "");
        } catch (Exception e) {
            String m = "Chyba: " + e.getMessage();
            Prefs.log(ctx, m);
            return m;
        }
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
                }
            }
            p.put("n", names.containsKey(ip) ? names.get(ip) : ip);
            String model = models.containsKey(ip) ? models.get(ip) : "";
            p.put("m", model);
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
            try {
                if (!p.has("n") && names.containsKey(ip)) p.put("n", names.get(ip));
                if (unreachable) p.put("off", 1); else p.put("err", msg);
            } catch (Exception ignored) {}
            note(ip, unreachable ? "off" : "err", unreachable ? "nedostupná (vypnutá / bez napájení)" : msg);
        }
        return p;
    }

    /**
     * Zásuvka si energii pamatuje sama (hodinově). Hlídač podle toho zpětně opraví denní součty i běhy generátoru,
     * i když Flip zásuvku zrovna nezachytil. Posílá do <topic>-tp-hist: {"id":"3","h":{"2026-10-14":[24× Wh]}}.
     */
    private void sendPlugHistories(String email, String pass, JSONArray plugs, Map<String, String> idIp) {
        String topic = Prefs.s(ctx, Prefs.NTFY_TOPIC);
        if (topic.isEmpty()) return;
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
                    JSONObject r = new JSONObject(t.call("get_energy_data",
                            "{\"start_timestamp\":" + start + ",\"end_timestamp\":" + (start + 86400 - 1) + ",\"interval\":60}"));
                    JSONObject res = r.optJSONObject("result");
                    if (r.optInt("error_code", 0) != 0 || res == null) break;
                    JSONArray data = res.optJSONArray("data");
                    if (data == null) continue;
                    JSONArray h = new JSONArray();
                    for (int i = 0; i < 24; i++) h.put(data.optInt(i, -1));
                    days.put(df.format(d.getTime()), h);
                }
                if (days.length() > 0) {
                    post("https://ntfy.sh/" + topic + "-tp-hist", new JSONObject().put("id", id).put("h", days).toString());
                    Prefs.get(ctx).edit().putString(key, today).apply();
                    Prefs.log(ctx, "Historie zásuvky (" + id + ") odeslána: " + days.length() + " dní");
                }
            } catch (Exception e) {
                Prefs.log(ctx, "Historie zásuvky (" + id + "): " + e.getMessage());
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
        boolean want = m.isEmpty() ? age > 3 * 60_000L : age > 6 * 3600_000L || (sp.getBoolean("tapo_rescan", false) && age > 30 * 60_000L);
        if (!want) return m;
        Map<String, JSONObject> found = TapoScan.scan(ctx, email, pass);
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
                Prefs.log(ctx, "Zásuvka " + ip + " " + (on ? "ZAPNUTA" : "VYPNUTA") + " (" + last.optString("why", "povel") + ")");
            } else {
                Prefs.log(ctx, "Povel pro " + ip + " selhal: " + r);
            }
        } catch (Exception e) {
            Prefs.log(ctx, "Povely: " + e.getMessage());
        }
    }

    /** Najde zásuvku za měničem (název obsahuje „měnič“, „220“ …) a pošle hodinovou spotřebu za posledních 30 dní. */
    private void sendPlugHistory(String email, String pass) {
        String today = new java.text.SimpleDateFormat("yyyy-MM-dd", Locale.US).format(new java.util.Date());
        if (today.equals(Prefs.get(ctx).getString("hist_sent", ""))) return;
        String ip = null;
        for (Map.Entry<String, String> e : names.entrySet()) {
            if (e.getValue().toLowerCase(Locale.ROOT).matches(".*(m[eě]ni[cč]|inverter|220|230).*")) { ip = e.getKey(); break; }
        }
        if (ip == null) return;
        try {
            TapoKlap t = tapo.get(ip);
            if (t == null) { t = new TapoKlap(ip, email, pass); tapo.put(ip, t); }
            JSONObject days = new JSONObject();
            java.util.Calendar cal = java.util.Calendar.getInstance();
            cal.set(java.util.Calendar.HOUR_OF_DAY, 0); cal.set(java.util.Calendar.MINUTE, 0);
            cal.set(java.util.Calendar.SECOND, 0); cal.set(java.util.Calendar.MILLISECOND, 0);
            java.text.SimpleDateFormat df = new java.text.SimpleDateFormat("yyyy-MM-dd", Locale.US);
            int okDays = 0;
            for (int back = 1; back <= 30; back++) {
                java.util.Calendar d = (java.util.Calendar) cal.clone();
                d.add(java.util.Calendar.DAY_OF_MONTH, -back);
                long start = d.getTimeInMillis() / 1000;
                String par = "{\"start_timestamp\":" + start + ",\"end_timestamp\":" + (start + 86400 - 1) + ",\"interval\":60}";
                JSONObject r = new JSONObject(t.call("get_energy_data", par));
                JSONObject res = r.optJSONObject("result");
                if (r.optInt("error_code", 0) != 0 || res == null) break;
                JSONArray data = res.optJSONArray("data");
                if (data == null || data.length() < 24) continue;
                JSONArray h = new JSONArray();
                for (int i = 0; i < 24; i++) h.put(data.optInt(i, -1));
                days.put(df.format(d.getTime()), h);
                okDays++;
            }
            if (okDays > 0) {
                String topic = Prefs.s(ctx, Prefs.NTFY_TOPIC);
                post("https://ntfy.sh/" + topic + "-menic-hist", new JSONObject().put("d", days).toString());
                Prefs.log(ctx, "Historie zásuvky za měničem odeslána: " + okDays + " dní");
            }
            Prefs.get(ctx).edit().putString("hist_sent", today).apply();
        } catch (Exception e) {
            Prefs.log(ctx, "Historie zásuvky: " + e.getMessage());
        }
    }

    /** Do záznamu jen změny stavu zásuvky. */
    private void note(String ip, String state, String msg) {
        String prev = lastState.put(ip, state);
        if (state.equals(prev)) return;
        if (msg != null) Prefs.log(ctx, "Zásuvka " + ip + ": " + msg);
        else if (prev != null) Prefs.log(ctx, "Zásuvka " + ip + ": zase dostupná");
    }

    /** Po hodině se znovu načtou názvy zásuvek (kdyby se přejmenovaly). */
    public void forgetNames() { names.clear(); models.clear(); }

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
        c.disconnect();
        if (code >= 300) throw new Exception("ntfy HTTP " + code);
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
