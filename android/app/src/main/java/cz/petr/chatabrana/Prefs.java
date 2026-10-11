package cz.petr.chatabrana;

import android.content.Context;
import android.content.SharedPreferences;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;

/** Nastavení a krátký log – vše jen v tomhle telefonu. */
public final class Prefs {
    public static final String NTFY_TOPIC = "ntfy_topic";
    public static final String VICTRON_MAC = "victron_mac";
    public static final String VICTRON_KEY = "victron_key";
    public static final String TAPO_EMAIL = "tapo_email";
    public static final String TAPO_PASSWORD = "tapo_password";
    public static final String TAPO_IPS = "tapo_ips";
    public static final String RUNNING = "running";
    public static final String LAST_SENT = "last_sent";

    private Prefs() {}

    public static SharedPreferences get(Context c) {
        return c.getSharedPreferences("chata_brana", Context.MODE_PRIVATE);
    }

    public static String s(Context c, String k) { return get(c).getString(k, "").trim(); }

    public static List<String> tapoIps(Context c) {
        List<String> out = new ArrayList<>();
        for (String p : s(c, TAPO_IPS).split("[,;\\s]+")) {
            p = p.trim();
            if (p.isEmpty()) continue;
            if (p.matches("\\d+")) p = "192.168.0." + p;        // stačí napsat jen konec adresy, např. 185
            out.add(p);
        }
        return out;
    }

    public static synchronized void log(Context c, String msg) {
        String line = new SimpleDateFormat("d.M. HH:mm:ss", Locale.getDefault()).format(new Date()) + "  " + msg;
        String old = get(c).getString("log", "");
        String[] lines = old.isEmpty() ? new String[0] : old.split("\n");
        StringBuilder sb = new StringBuilder(line);
        for (int i = 0; i < Math.min(lines.length, 40); i++) sb.append('\n').append(lines[i]);
        get(c).edit().putString("log", sb.toString()).apply();
    }

    public static String log(Context c) { return get(c).getString("log", ""); }
}
