package cz.petr.chatabrana;

import android.content.Context;
import android.os.SystemClock;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;

/**
 * 1.9.22 (Petr: „živě to celé“): kromě světel i zásuvky (zap/vyp, W), Victron (W, V), teploměry a baterie Flipu.
 * Posílá se jen při podstatné změně – světlo / zásuvka zap/vyp hned (kontrola po 20 s), výkon zásuvky nebo Victronu
 * o 15 W a zároveň o 20 % a víc nejvýš 1× za minutu;
 * teploty a baterie jen jako doplněk. Spojení s ntfy zůstává otevřené (bez opakovaného navazování – méně dat).
 * 1.9.20 (Petr: světla živě a zapínání z webu). Světla Tapo (L900…) se po Wi‑Fi chaty kontrolují každých 20 s
 * (mobilní data to nestojí); když se některé rozsvítí nebo zhasne, pošle se jejich stav (pár set bajtů) do ntfy
 * <téma>-lt – web ho má hned. Povel z webu přijde přes <téma>-ltc (poslouchá ho trvalé spojení v GatewayService):
 * {"n":"(S4) terasa","on":true} → světlo se přepne a hned se pošle nový stav.
 * Seznam světel (jméno → IP) si průběžně ukládá Collector při každém měření.
 */
final class LightWatch {
    static final long PERIOD_MS = 20_000L;
    private final Context ctx;
    private volatile Thread th;
    private final Map<String, TapoKlap> tapo = new HashMap<>();
    private String lastState = "", lastErr = "";
    private long lastSend = 0;
    private long noPowerSince = 0;                                 // 1.9.22: chata bez 230 V od (elapsedRealtime)
    private boolean noPowerSent = false;
    private String vicAlarm = "";
    private boolean fromRiver = false;                              // 1.9.23: naposledy měla chata 230 V z River
    private final BleListener ble;
    private final Map<String, Double> sentW = new HashMap<>();   // naposledy poslané W (zásuvky, „~v“ = Victron)
    // 1.9.24 (Petr: „světlo se rozsvítí do 5 s, ale web stav nedostane“): nedostupné zařízení (jiná Wi‑Fi, bez proudu)
    // zdržovalo každé čtení o vypršení spojení → po chybě se 60 s přeskakuje; po povelu z webu jde stav světel hned.
    private final Map<String, Long> down = new HashMap<>();
    private final Map<String, Integer> lastLt = new java.util.TreeMap<>();
    static final long DOWN_MS = 60_000L;
    static final double DW = 15.0;

    LightWatch(Context c, BleListener b) { ctx = c.getApplicationContext(); ble = b; }

    /** Collector: zásuvka „jméno“ je na IP; meas = měří výkon. */
    static synchronized void rememberPlug(Context c, String name, String ip, boolean meas) {
        try {
            JSONObject m = new JSONObject(Prefs.get(c).getString("pl_map", "{}"));
            String v = ip + (meas ? "|1" : "|0");
            if (v.equals(m.optString(name))) return;
            m.put(name, v);
            Prefs.get(c).edit().putString("pl_map", m.toString()).apply();
        } catch (Exception ignored) {}
    }

    /** Collector: světlo „jméno“ je teď na IP adrese ip. */
    static synchronized void remember(Context c, String name, String ip) {
        try {
            JSONObject m = new JSONObject(Prefs.get(c).getString("lt_map", "{}"));
            if (ip.equals(m.optString(name))) return;
            m.put(name, ip);
            Prefs.get(c).edit().putString("lt_map", m.toString()).apply();
        } catch (Exception ignored) {}
    }

    void start() {
        if (th != null && th.isAlive()) return;
        Thread t = new Thread(() -> {
            while (th == Thread.currentThread()) {
                try { poll(false); } catch (Exception ignored) {}
                SystemClock.sleep(PERIOD_MS);
            }
        }, "lights");
        t.setDaemon(true);
        th = t;
        t.start();
    }

    void stop() { Thread t = th; th = null; if (t != null) t.interrupt(); }

    private TapoKlap klap(String ip) {
        TapoKlap t = tapo.get(ip);
        if (t == null) {
            t = new TapoKlap(ip, Prefs.s(ctx, Prefs.TAPO_EMAIL), Prefs.s(ctx, Prefs.TAPO_PASSWORD));
            tapo.put(ip, t);
        }
        return t;
    }

    /** Přečte všechna světla; při změně (nebo force) pošle stav do ntfy. */
    synchronized void poll(boolean force) throws Exception {
        if (Prefs.s(ctx, Prefs.TAPO_EMAIL).isEmpty()) return;
        JSONObject m = new JSONObject(Prefs.get(ctx).getString("lt_map", "{}"));
        List<String> names = new ArrayList<>();
        for (Iterator<String> it = m.keys(); it.hasNext(); ) names.add(it.next());
        Collections.sort(names);
        JSONArray arr = new JSONArray();
        StringBuilder st = new StringBuilder();
        for (String n : names) {
            String ip = m.optString(n);
            if (ip.isEmpty()) continue;
            Long dn = down.get(ip);
            if (dn != null && SystemClock.elapsedRealtime() < dn) continue;
            try {
                JSONObject info = new JSONObject(klap(ip).call("get_device_info")).optJSONObject("result");
                if (info == null || !info.has("device_on")) continue;
                boolean on = info.optBoolean("device_on");
                lastLt.put(n, on ? 1 : 0); down.remove(ip);
                arr.put(new JSONObject().put("n", n).put("ip", ip.substring(ip.lastIndexOf('.') + 1)).put("on", on ? 1 : 0));
                st.append(n).append('=').append(on ? 1 : 0).append(';');
            } catch (Exception e) {
                tapo.remove(ip);                                   // příště nové přihlášení
                down.put(ip, SystemClock.elapsedRealtime() + DOWN_MS);
                err("Světla: " + n + " nejde přečíst (" + e.getClass().getSimpleName() + " " + e.getMessage() + ")");
            }
        }
        if (arr.length() == 0 && m.length() > 0) err("Světla: žádné nepřečteno (seznam: " + m.length() + ")");
        // 1.9.22: zásuvky
        JSONObject pm = new JSONObject(Prefs.get(ctx).getString("pl_map", "{}"));
        JSONArray tp = new JSONArray();
        Map<String, Double> nowW = new HashMap<>();
        List<String> reach = new ArrayList<>();
        List<String> pn = new ArrayList<>();
        for (Iterator<String> it = pm.keys(); it.hasNext(); ) pn.add(it.next());
        Collections.sort(pn);
        for (String n : pn) {
            String[] v = pm.optString(n).split("\\|");
            String ip = v[0];
            if (ip.isEmpty()) continue;
            Long dn = down.get(ip);
            if (dn != null && SystemClock.elapsedRealtime() < dn) continue;
            try {
                JSONObject x = new JSONObject().put("n", n);
                JSONObject info = new JSONObject(klap(ip).call("get_device_info")).optJSONObject("result");
                if (info != null && info.has("device_on")) {
                    boolean on = info.optBoolean("device_on");
                    x.put("on", on ? 1 : 0);
                    st.append(n).append('=').append(on ? 1 : 0).append(';');
                    reach.add(n);                                       // 1.9.23: odpověděla = má proud
                }
                if (v.length > 1 && "1".equals(v[1])) {
                    JSONObject e = new JSONObject(klap(ip).call("get_energy_usage")).optJSONObject("result");
                    if (e != null && e.has("current_power")) {
                        double w = Math.round(e.getDouble("current_power") / 100.0) / 10.0;
                        x.put("w", w);
                        nowW.put(n, w);
                    }
                }
                tp.put(x);
                down.remove(ip);
            } catch (Exception e) {
                tapo.remove(ip);
                down.put(ip, SystemClock.elapsedRealtime() + DOWN_MS);
            }
        }
        // Victron (Bluetooth – co Flip právě zachytil)
        JSONObject vic = null;
        VictronParser.Inverter iv = ble != null ? ble.peekVictron() : null;
        if (iv != null) {
            vic = new JSONObject();
            if (iv.acVa != null) { vic.put("w", iv.acVa); nowW.put("~v", (double) iv.acVa); }
            if (iv.batteryV != null) vic.put("v", iv.batteryV);
        }
        alerts(iv, nowW, reach, arr.length() > 0);
        if (arr.length() == 0 && tp.length() == 0 && vic == null) return;
        String s = st.toString();
        boolean big = false;                                        // výkon se změnil o 15 W a víc
        for (Map.Entry<String, Double> e : nowW.entrySet()) {
            Double was = sentW.get(e.getKey());
            double d = Math.abs((was == null ? 0 : was) - e.getValue());
            if (was == null || (d >= DW && d >= 0.2 * Math.max(Math.abs(was), Math.abs(e.getValue())))) { big = true; break; }
        }
        if (!force && s.equals(lastState) && !big) return;
        // jen změna výkonu (nic se nezaplo / nevyplo) → nejvýš 1× za minutu (šetří data)
        if (!force && s.equals(lastState) && SystemClock.elapsedRealtime() - lastSend < 60_000) return;
        JSONObject o = new JSONObject().put("t", System.currentTimeMillis() / 1000).put("lt", arr);
        if (tp.length() > 0) o.put("tp", tp);
        if (vic != null) o.put("v", vic);
        try {                                                       // doplněk: teploty a baterie Flipu
            JSONArray th = new JSONArray();
            if (ble != null) for (BleListener.Thermo t : ble.thermo()) {
                if (t.ageSec < 0 || t.ageSec > 1800 || t.t == null) continue;
                JSONObject x = new JSONObject().put("n", t.name).put("t", t.t);
                if (t.h != null) x.put("h", t.h);
                th.put(x);
            }
            if (th.length() > 0) o.put("th", th);
            android.os.BatteryManager bm = ctx.getSystemService(android.os.BatteryManager.class);
            if (bm != null) o.put("ph", new JSONObject().put("b", bm.getIntProperty(android.os.BatteryManager.BATTERY_PROPERTY_CAPACITY))
                    .put("c", bm.isCharging() ? 1 : 0));
        } catch (Exception ignored) {}
        String r = post(o);
        if (r == null) {
            boolean lightChg = !lightPart(s).equals(lightPart(lastState));
            lastState = s; lastErr = ""; sentW.clear(); sentW.putAll(nowW); lastSend = SystemClock.elapsedRealtime();
            if (lightChg) Prefs.log(ctx, "Světla → web: " + lightPart(s).replace(";", " ").trim());
        }
        else err("Živé hodnoty → web: nepovedlo se odeslat (" + r + ")");
    }

    /**
     * 1.9.22 (Petr): okamžitá upozornění přímo z Flipu (nečekají na hlídače):
     * • chata bez 230 V déle než 1 min (přepínání zdroje trvá kratší chvíli) – 230 V je, když měnič měří
     *   (INVERTING / LOW_POWER), některá zásuvka River → chata (čísla posílá hlídač v -fc „rv“) dává aspoň 5 W, nebo
 *   odpovídá světlo či zásuvka v okruhu chaty (ne River, ne generátor) – bez proudu by neodpověděla (1.9.23);
     *   bez 230 V = River do chaty nic nedává a měnič neměří (slyším ho), nebo chata naposledy jela z River (měnič bývá
 *   vypnutý a neslyšet). Když chata jela z měniče a ten teď neslyším – nevíme, nic (1.9.23).
     * • měnič hlásí alarm / poruchu (hned, a když skončí).
     */
    private void alerts(VictronParser.Inverter iv, Map<String, Double> nowW, List<String> reach, boolean lightUp) {
        String rv = Prefs.get(ctx).getString("rv_ids", ""), gp = Prefs.get(ctx).getString("gp_id", "7");
        boolean circuit = lightUp;                                   // 1.9.23: světlo nebo zásuvka v okruhu chaty odpovídá = proud je
        for (String n : reach) {
            java.util.regex.Matcher mm = java.util.regex.Pattern.compile("^\\s*\\((\\d+)\\)").matcher(n);
            if (mm.find() && !rv.contains("," + mm.group(1) + ",") && !mm.group(1).equals(gp)) { circuit = true; break; }
        }
        double rvW = 0;
        for (Map.Entry<String, Double> e : nowW.entrySet()) {
            java.util.regex.Matcher mm = java.util.regex.Pattern.compile("^\\s*\\((\\d+)\\)").matcher(e.getKey());
            if (mm.find() && rv.contains("," + mm.group(1) + ",")) rvW += e.getValue();
        }
        if (rv.isEmpty()) err("230 V: hlídač zatím neposlal čísla zásuvek River – hlídání 230 V čeká");
        Boolean powered = null;
        if (iv != null && (iv.state == 9 || iv.state == 1)) { powered = true; fromRiver = false; }
        else if (circuit) powered = true;
        else if (rvW >= 5) { powered = true; fromRiver = true; }
        // 1.9.23 (Petr: vypnutá zásuvka River, ze které jela chata – nic nepřišlo): když chata jela z River, měnič bývá
        // vypnutý a neslyšet – pak stačí, že River do chaty přestala dávat. Jinak bez 230 V jen, když měnič slyším a neměří.
        else if (!rv.isEmpty() && (iv != null || fromRiver)) powered = false;
        long now = SystemClock.elapsedRealtime();
        if (Boolean.FALSE.equals(powered)) {
            if (noPowerSince == 0) noPowerSince = now;
            if (!noPowerSent && now - noPowerSince >= 60_000) {
                if (push("⚡ Chata je bez 230 V", "Už přes minutu: měnič " + (iv != null ? iv.stateName() : "neslyším (vypnutý)") + ", River do chaty 0 W. Lednice nejede – zkontroluj zdroj chaty.", 5, "zap,warning"))
                    noPowerSent = true;
            }
        } else if (Boolean.TRUE.equals(powered)) {
            if (noPowerSent && push("✓ Chata má zase 230 V", iv != null && (iv.state == 9 || iv.state == 1) ? "Z měniče." : "Z River (" + Math.round(rvW) + " W).", 3, "white_check_mark"))
                noPowerSent = false;
            noPowerSince = 0;
        } else noPowerSince = 0;
        if (iv != null) {
            String al = iv.alarm != 0 ? iv.alarmName() : iv.state == 2 ? "FAULT" : "";
            if (!al.equals(vicAlarm)) {
                boolean ok = al.isEmpty()
                        ? push("✓ Měnič už alarm nehlásí", "Victron: " + iv.stateName(), 3, "white_check_mark")
                        : push("⚠️ Měnič hlásí alarm: " + al, "Victron: " + al + " (stav " + iv.stateName() + ")" + (iv.batteryV != null ? ", baterie " + String.format(java.util.Locale.US, "%.2f", iv.batteryV).replace('.', ',') + " V" : "") + ".", 5, "warning");
                if (ok) vicAlarm = al;
            }
        }
    }

    /** Upozornění do hlavního tématu ntfy (stejné jako upozornění hlídače). JSON kvůli diakritice v nadpisu. */
    private boolean push(String title, String msg, int prio, String tags) {
        String topic = Prefs.s(ctx, Prefs.NTFY_TOPIC).trim();
        if (topic.isEmpty()) return false;
        HttpURLConnection c = null;
        try {
            JSONObject o = new JSONObject().put("topic", topic).put("title", title).put("message", msg).put("priority", prio)
                    .put("tags", new JSONArray(java.util.Arrays.asList(tags.split(","))));
            c = (HttpURLConnection) new URL("https://ntfy.sh/").openConnection();
            c.setConnectTimeout(15000); c.setReadTimeout(15000);
            c.setRequestMethod("POST"); c.setDoOutput(true);
            c.setRequestProperty("Content-Type", "application/json");
            try (OutputStream out = c.getOutputStream()) { out.write(o.toString().getBytes(StandardCharsets.UTF_8)); }
            int code = c.getResponseCode();
            Prefs.log(ctx, "Upozornění z Flipu: " + title + (code == 200 ? "" : " – HTTP " + code));
            return code == 200;
        } catch (Exception e) {
            Prefs.log(ctx, "Upozornění z Flipu nešlo poslat: " + e.getMessage());
            return false;
        } finally { if (c != null) c.disconnect(); }
    }

    /** Část stavu jen se světly (do Deníku jen změny světel, ne každou zásuvku). */
    private String lightPart(String s) {
        StringBuilder b = new StringBuilder();
        try {
            JSONObject m = new JSONObject(Prefs.get(ctx).getString("lt_map", "{}"));
            for (String x : s.split(";")) { int i = x.indexOf('='); if (i > 0 && m.has(x.substring(0, i))) b.append(x).append(';'); }
        } catch (Exception ignored) {}
        return b.toString();
    }

    /** 1.9.21: chybu zapsat do Deníku jen jednou (ne každých 20 s). */
    private void err(String e) {
        if (e.equals(lastErr)) return;
        lastErr = e;
        Prefs.log(ctx, e);
    }

    /** Povel z webu: světlo podle jména zapnout / vypnout, pak hned poslat nový stav. */
    synchronized void command(String name, boolean on) {
        try {
            JSONObject m = new JSONObject(Prefs.get(ctx).getString("lt_map", "{}"));
            String ip = m.optString(name);
            if (ip.isEmpty()) { Prefs.log(ctx, "Světlo z webu: „" + name + "“ neznám"); return; }
            JSONObject r = new JSONObject(klap(ip).call("set_device_info", "{\"device_on\":" + on + "}"));
            if (r.optInt("error_code", -1) == 0) {
                Prefs.log(ctx, "Světlo " + name + " " + (on ? "ROZSVÍCENO" : "ZHASNUTO") + " (z webu)");
                lastLt.put(name, on ? 1 : 0);
                // 1.9.24: hned stav světel (z paměti + tohle), ať web nečeká na čtení všech zásuvek
                JSONArray arr = new JSONArray();
                for (Map.Entry<String, Integer> e : lastLt.entrySet()) {
                    String ip2 = m.optString(e.getKey());
                    arr.put(new JSONObject().put("n", e.getKey()).put("ip", ip2.substring(ip2.lastIndexOf('.') + 1)).put("on", e.getValue()));
                }
                String pr = post(new JSONObject().put("t", System.currentTimeMillis() / 1000).put("lt", arr));
                if (pr != null) err("Světla → web (hned po povelu): nepovedlo se odeslat (" + pr + ")");
            }
            else Prefs.log(ctx, "Světlo " + name + " z webu: selhalo " + r);
            SystemClock.sleep(600);
            poll(true);
        } catch (Exception e) {
            tapo.clear();
            Prefs.log(ctx, "Světlo z webu: " + e.getMessage());
        }
    }

    /** null = odesláno, jinak důvod chyby. */
    private String post(JSONObject o) {
        String topic = Prefs.s(ctx, Prefs.NTFY_TOPIC).trim();
        if (topic.isEmpty()) return "chybí téma ntfy";
        HttpURLConnection c = null;
        try {
            c = (HttpURLConnection) new URL("https://ntfy.sh/" + topic + "-lt").openConnection();
            c.setConnectTimeout(15000); c.setReadTimeout(15000);
            c.setRequestMethod("POST"); c.setDoOutput(true);
            try (OutputStream out = c.getOutputStream()) { out.write(o.toString().getBytes(StandardCharsets.UTF_8)); }
            int code = c.getResponseCode();
            try (java.io.InputStream in = code < 400 ? c.getInputStream() : c.getErrorStream()) {   // dočíst → spojení se znovu použije
                if (in != null) { byte[] b = new byte[1024]; while (in.read(b) > 0) { } }
            }
            return code == 200 ? null : "HTTP " + code;
        } catch (Exception e) {
            if (c != null) c.disconnect();
            return e.getClass().getSimpleName() + " " + e.getMessage();
        }
    }
}
