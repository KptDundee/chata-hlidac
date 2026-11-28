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

    LightWatch(Context c) { ctx = c.getApplicationContext(); }

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
            try {
                JSONObject info = new JSONObject(klap(ip).call("get_device_info")).optJSONObject("result");
                if (info == null || !info.has("device_on")) continue;
                boolean on = info.optBoolean("device_on");
                arr.put(new JSONObject().put("n", n).put("ip", ip.substring(ip.lastIndexOf('.') + 1)).put("on", on ? 1 : 0));
                st.append(n).append('=').append(on ? 1 : 0).append(';');
            } catch (Exception e) {
                tapo.remove(ip);                                   // příště nové přihlášení
                err("Světla: " + n + " nejde přečíst (" + e.getClass().getSimpleName() + " " + e.getMessage() + ")");
            }
        }
        if (arr.length() == 0) { err("Světla: žádné nepřečteno (seznam: " + m.length() + ")"); return; }
        String s = st.toString();
        if (!force && s.equals(lastState)) return;
        String r = post(new JSONObject().put("t", System.currentTimeMillis() / 1000).put("lt", arr));
        if (r == null) { lastState = s; lastErr = ""; Prefs.log(ctx, "Světla → web: " + s.replace(";", " ").trim()); }
        else err("Světla → web: nepovedlo se odeslat (" + r + ")");
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
            if (r.optInt("error_code", -1) == 0) Prefs.log(ctx, "Světlo " + name + " " + (on ? "ROZSVÍCENO" : "ZHASNUTO") + " (z webu)");
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
            return code == 200 ? null : "HTTP " + code;
        } catch (Exception e) {
            return e.getClass().getSimpleName() + " " + e.getMessage();
        } finally { if (c != null) c.disconnect(); }
    }
}
