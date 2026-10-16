package cz.petr.chatahodinky;

import android.content.ComponentName;
import android.content.Context;
import android.content.SharedPreferences;

import androidx.wear.tiles.TileService;
import androidx.wear.watchface.complications.datasource.ComplicationDataSourceUpdateRequester;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.Locale;

/** Data z hlídače: poslední zpráva v ntfy kanálu <téma>-hodinky (posílá ji hlídač každých 10 min). */
final class Data {
    private static final String PREFS = "chata";
    static final Locale CS = new Locale("cs", "CZ");

    static SharedPreferences prefs(Context c) {
        return c.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    static String topic(Context c) {
        return prefs(c).getString("topic", "").trim();
    }

    static void setTopic(Context c, String t) {
        prefs(c).edit().putString("topic", t.trim()).apply();
    }

    /** Poslední uložená data (i bez spojení). */
    static JSONObject cached(Context c) {
        try {
            String s = prefs(c).getString("json", null);
            return s == null ? null : new JSONObject(s);
        } catch (Exception e) {
            return null;
        }
    }

    /** Stáhne nejnovější zprávu; při chybě vrátí null (uložená data zůstanou). */
    static JSONObject fetch(Context c) {
        String topic = topic(c);
        if (topic.isEmpty()) return null;
        HttpURLConnection con = null;
        try {
            URL u = new URL("https://ntfy.sh/" + topic + "-hodinky/json?poll=1&since=3h");
            con = (HttpURLConnection) u.openConnection();
            con.setConnectTimeout(8000);
            con.setReadTimeout(8000);
            JSONObject last = null;
            try (BufferedReader r = new BufferedReader(new InputStreamReader(con.getInputStream(), StandardCharsets.UTF_8))) {
                String ln;
                while ((ln = r.readLine()) != null) {
                    if (ln.isEmpty()) continue;
                    JSONObject m = new JSONObject(ln);
                    if ("message".equals(m.optString("event"))) last = m;
                }
            }
            if (last == null) return null;
            JSONObject d = new JSONObject(last.optString("message", "{}"));
            prefs(c).edit().putString("json", d.toString()).putLong("fetched", System.currentTimeMillis()).apply();
            return d;
        } catch (Exception e) {
            return null;
        } finally {
            if (con != null) con.disconnect();
        }
    }

    /** Ťuknutí na dlaždici: požádá Flip o měření hned (ntfy <téma>-wake); Flip pak spustí hlídače.
     *  Nejvýš jednou za 2 min. Čerstvá data dorazí zhruba za 2–3 min. */
    static void wake(Context c) {
        String topic = topic(c);
        long now = System.currentTimeMillis();
        if (topic.isEmpty() || now - prefs(c).getLong("wake_t", 0) < 120_000) return;
        prefs(c).edit().putLong("wake_t", now).apply();
        HttpURLConnection con = null;
        try {
            con = (HttpURLConnection) new URL("https://ntfy.sh/" + topic + "-wake").openConnection();
            con.setConnectTimeout(8000);
            con.setReadTimeout(8000);
            con.setRequestMethod("POST");
            con.setDoOutput(true);
            con.setRequestProperty("Priority", "1");
            try (java.io.OutputStream o = con.getOutputStream()) { o.write("hodinky".getBytes(StandardCharsets.UTF_8)); }
            con.getResponseCode();
        } catch (Exception ignored) {
        } finally {
            if (con != null) con.disconnect();
        }
    }

    /** Čeká se na data po ťuknutí? (do 5 min, dokud nepřijde novější souhrn) */
    static boolean waiting(Context c, JSONObject d) {
        long w = prefs(c).getLong("wake_t", 0);
        return System.currentTimeMillis() - w < 5 * 60_000 && (d == null || d.optLong("t", 0) * 1000 < w);
    }

    /** Čerstvá data, když to jde (nejvýš jednou za minutu), jinak uložená. */
    static JSONObject fresh(Context c) {
        long last = prefs(c).getLong("fetched", 0);
        long gap = System.currentTimeMillis() - prefs(c).getLong("wake_t", 0) < 5 * 60_000 ? 20_000 : 60_000;   // po ťuknutí častěji
        if (System.currentTimeMillis() - last > gap) {
            JSONObject d = fetch(c);
            if (d != null) return d;
        }
        return cached(c);
    }

    static String volt(double v) {
        return String.format(CS, "%.2f", v);
    }

    /** Stáří dat v minutách (podle času, kdy je hlídač poslal). */
    static long ageMin(JSONObject d) {
        long t = d.optLong("t", 0);
        return t == 0 ? 9999 : (System.currentTimeMillis() / 1000 - t) / 60;
    }

    static String ageText(JSONObject d) {
        long m = ageMin(d);
        if (m < 1) return "teď";
        if (m < 60) return "před " + m + " min";
        if (m < 48 * 60) return "před " + (m / 60) + " h";
        return "stará data";
    }

    /** Barva podle stavu: 0 v pořádku, 1 slábne, 2 kritické. */
    static int color(int lvl) {
        return lvl >= 2 ? 0xFFFF5A4E : lvl == 1 ? 0xFFFFB020 : 0xFF4CD964;
    }

    /** Po stažení nových dat obnovit dlaždici i komplikaci. */
    static void requestUpdates(Context c) {
        try {
            TileService.getUpdater(c).requestUpdate(ChataTile.class);
        } catch (Exception ignored) { }
        try {
            ComplicationDataSourceUpdateRequester.create(c, new ComponentName(c, VoltComplication.class)).requestUpdateAll();
        } catch (Exception ignored) { }
        try {
            ComplicationDataSourceUpdateRequester.create(c, new ComponentName(c, SunComplication.class)).requestUpdateAll();
        } catch (Exception ignored) { }
        try {
            ComplicationDataSourceUpdateRequester.create(c, new ComponentName(c, TempComplication.class)).requestUpdateAll();
        } catch (Exception ignored) { }
    }
}
